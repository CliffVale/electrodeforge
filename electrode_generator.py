#!/usr/bin/env python3
"""
Parametric Electrode Generator
===============================
Generates fabrication-ready DXF (laser cutting) and SVG (Cricut) files
for common electrode geometries used in electrochemical sensors.

Supported electrode types:
  - ide        Interdigitated electrode (comb-finger array)
  - three      Three-electrode system (WE/CE/RE)
  - serpentine Serpentine / zigzag trace
  - ringdisk   Ring-disk electrode
  - array      Uniform electrode array (grid)
  - meander    Spring-like serpentine (each segment has sinusoidal waves)
  - carray     Circular/radial electrode array
  - spiral     Archimedean spiral electrode
  - polygon    Custom polygon electrode from vertex list

Usage:
  python electrode_generator.py --type ide --fingers 10 --width 25 --height 25 \
      --finger-w 0.5 --gap 0.3 --finger-l 15 --pad-size 3 \
      --format both --output my_electrode

All dimensions in millimetres unless stated otherwise.
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import ezdxf
from ezdxf import units
import svgwrite


# ─────────────────────────────────────────────────────────────────────
# Data classes for electrode parameters
# ─────────────────────────────────────────────────────────────────────

@dataclass
class BaseParams:
    """Parameters shared by all electrode types."""
    width_mm: float = 25.0
    height_mm: float = 25.0
    output: str = "electrode"
    fmt: str = "both"
    dxf_version: str = "R2010"
    svg_precision: int = 4
    trace_color: str = "#000000"
    fill_color: str = "#000000"
    substrate_color: str = "#FFFFFF"


@dataclass
class IDEParams(BaseParams):
    """Interdigitated electrode (IDE) parameters.

    Design rules (from literature):
    - Finger width: 0.1-2mm (screen print), 1-100μm (photolithography)
    - Gap: ≤ finger width for optimal redox cycling (NIH PMC9741053)
    - Finger length: 5-20mm typical for screen-printed sensors
    - Number of pairs: 10-50 for adequate signal; more = higher sensitivity
    - Bus bar width: ≥ 2× finger width for low resistance
    - Pad size: ≥ 2mm for reliable wire bonding / crocodile clip contact

    References:
    - Kosri et al., Nanomaterials 2022, 12, 4171 (PMC9741053)
    - PotentioLab IDE Sensors Guide, 2026
    """
    fingers: int = 10          # 10-50 pairs typical
    finger_w_mm: float = 1.0   # 0.5-2mm for screen printing; 25μm for micro
    gap_mm: float = 1.0        # ≤ finger_w for redox cycling; 1mm safe for screen print
    finger_l_mm: float = 10.0  # 5-20mm; shorter = faster response
    pad_size_mm: float = 3.0   # ≥ 2mm for reliable contact
    bus_w_mm: float = 2.0      # ≥ 2× finger_w for low resistance
    margin_mm: float = 3.0     # Edge clearance from substrate


@dataclass
class ThreeElectrodeParams(BaseParams):
    """Three-electrode system parameters.

    Design rules (from Ossila & electrochemistry literature):
    - WE diameter: 1-6mm (3mm is most common for CV/EIS)
    - CE area: MUST be ≥ 10× WE area (the "10:1 rule" — Ossila)
    - RE diameter: 1-3mm (Ag/AgCl standard)
    - WE-RE spacing: 2-5mm (closer = less iR drop, but avoid shielding)
    - CE can be same size or larger than WE; ring shape maximises area
    - Materials: WE = GC/Pt/Au, CE = Pt wire/coil, RE = Ag/AgCl

    References:
    - Ossila, "Choosing Working, Reference and Counter Electrodes"
    - Harris et al., J. Electrochem. Soc. 2023 (PMC10141359)
    """
    we_d_mm: float = 3.0       # 1-6mm; 3mm is standard
    ce_d_mm: float = 6.0       # ≥ 10× WE area; for disk CE: ≥ √10 × WE_d ≈ 9.5mm
    re_d_mm: float = 2.0       # 1-3mm; Ag/AgCl typical
    spacing_mm: float = 3.0    # 2-5mm WE-to-RE center distance
    pad_size_mm: float = 3.0   # ≥ 2mm for contact
    trace_w_mm: float = 0.5    # Trace to pad
    we_fill: str = "solid"


@dataclass
class SerpentineParams(BaseParams):
    """Serpentine / zigzag electrode parameters.

    Design rules (from stretchable electronics literature):
    - Trace width: 0.5-1mm (screen print); 50-100μm (lithography)
    - Segment aspect ratio (L/H): 1.5-3:1 for good stretchability
    - Segment height: 0.5-3mm; affects bend radius
    - More segments = more stretchability but higher resistance
    - For screen printing: min trace 0.5mm, min gap 0.5mm

    References:
    - Suhaimi et al., Results in Physics 2022 (screen printed Ag serpentine)
    - ACS Applied Materials 2025 (printable stretchable serpentine)
    """
    trace_w_mm: float = 1.0    # 0.5-1mm for screen printing
    segments: int = 8          # 6-15 typical
    seg_l_mm: float = 3.0      # 2-5mm; L/H ratio 1.5-3:1
    seg_h_mm: float = 2.0      # 1-3mm
    pad_size_mm: float = 3.0   # ≥ 2mm
    margin_mm: float = 3.0


@dataclass
class RingDiskParams(BaseParams):
    """Ring-disk electrode parameters.

    Design rules (from RRDE literature):
    - Disk diameter: 3-6mm (5mm standard for Pine Research RRDE)
    - Gap: 375μm (0.375mm) is the industry standard for RRDE
    - Ring width: 1-2mm (must be wide enough for measurable collection)
    - Collection efficiency N depends on geometry (N≈0.256 for standard)
    - Smaller gap = higher collection efficiency but harder to fabricate
    - For screen printing: gap ≥ 0.3mm is practical minimum

    References:
    - Pine Research, "Rotating Ring Disk Electrode Fundamentals"
    - Frumkin & Nekrasov, 1959 (original RRDE theory)
    - BioLogic, "RRDE Introduction"
    """
    disk_d_mm: float = 5.0     # 3-6mm; 5mm is Pine Research standard
    gap_mm: float = 0.5        # 0.375mm standard; ≥0.3mm for screen print
    ring_w_mm: float = 1.5     # 1-2mm; wide enough for signal collection
    pad_size_mm: float = 3.0   # ≥ 2mm
    trace_w_mm: float = 0.5


@dataclass
class ArrayParams(BaseParams):
    """Uniform electrode array parameters.

    Design rules (from array literature):
    - Electrode diameter: 1-5mm (2mm common for screen print)
    - Pitch: ≥ 3× electrode diameter to minimise crosstalk
    - Minimum inter-electrode gap: ≥ 1mm for screen printing
    - Bus bar connects all electrodes; width ≥ 1.5mm
    - Pad size: ≥ 2mm for external contact
    - More electrodes = higher throughput but more complex wiring

    References:
    - Liu et al., Frontiers in Chemistry 2020 (Micro/Nano Electrode Array Sensors)
    - Zimmer Peacock, "Designing Screen Printed Electrodes"
    """
    rows: int = 4              # 2-10 typical
    cols: int = 4              # 2-10 typical
    electrode_d_mm: float = 2.0  # 1-5mm
    pitch_x_mm: float = 6.0    # ≥ 3× diameter = 6mm for 2mm electrodes
    pitch_y_mm: float = 6.0    # ≥ 3× diameter
    trace_w_mm: float = 0.5    # 0.3-1mm
    pad_size_mm: float = 3.0   # ≥ 2mm


@dataclass
class MeanderParams(BaseParams):
    """Spring-like serpentine (sinusoidal meander on each segment).

    Design rules (from wearable electronics literature):
    - Trace width: 0.5-1mm for screen printing
    - Meander amplitude: ≤ segment_height / 2 (avoids overlap)
    - Waves per segment: 4-12; more waves = more stretchability
    - Segment L/H ratio: 1.5-3:1 (same as plain serpentine)
    - Total meander height = seg_h + 2× amplitude must fit in substrate

    References:
    - Suhaimi et al., Results in Physics 2022
    - ACS Applied Materials 2025 (stretchable serpentine)
    """
    trace_w_mm: float = 1.0    # 0.5-1mm for screen printing
    segments: int = 6          # 4-10 typical
    seg_l_mm: float = 4.0      # 3-6mm; L/H ratio 1.5-3:1
    seg_h_mm: float = 2.5      # 1.5-3mm; amplitude must be ≤ seg_h/2
    meander_n: int = 6         # 4-12 waves per segment
    meander_amp_mm: float = 1.0  # ≤ seg_h/2 = 1.25mm max
    pad_size_mm: float = 3.0   # ≥ 2mm
    margin_mm: float = 3.0


@dataclass
class CircularArrayParams(BaseParams):
    """Circular/radial electrode array parameters.

    Design rules:
    - Ring spacing: ≥ electrode diameter to avoid field overlap
    - Electrodes per ring: 6-12 (outer rings can have more)
    - Electrode diameter: 1-3mm for screen printing
    - Centre electrode connects radially to all ring electrodes
    - Pad at edge for external connection

    References:
    - MDPI Sensors 2026, 26, 541 (spiral/embracing IDE)
    """
    rings: int = 3             # 2-5 typical
    electrodes_per_ring: int = 8  # 6-12; outer ring
    electrode_d_mm: float = 2.0  # 1-3mm
    ring_spacing_mm: float = 5.0  # ≥ electrode_d
    pad_size_mm: float = 3.0   # ≥ 2mm
    trace_w_mm: float = 0.5    # 0.3-1mm


@dataclass
class SpiralParams(BaseParams):
    """Archimedean spiral electrode parameters.

    Design rules (from impedance spectroscopy literature):
    - Turn spacing: ≥ trace width (no overlap); 0.5-2mm typical
    - Trace width: 0.3-1mm for screen printing
    - Number of turns: 3-10; more turns = higher inductance/capacitance
    - Outer radius: should fill ~80% of substrate for max sensitivity
    - Inner radius: ≥ 0.5mm (minimum for screen printing)
    - Uniform turn spacing for consistent impedance response

    References:
    - MDPI Micromachines 2020, 11, 333 (spiral electrode biosensor)
    - Nature Scientific Reports 2024 (spiral-interdigital electrode)
    - Springer 2021 (Archimedean spiral IDE, 50-150μm gaps)
    """
    turns: int = 5             # 3-10 typical
    r_start_mm: float = 1.0    # ≥ 0.5mm; inner clearance
    r_end_mm: float = 10.0     # ~80% of substrate width/2
    trace_w_mm: float = 0.8    # 0.3-1mm; spacing must be ≥ trace_w
    n_points: int = 200        # Resolution
    pad_size_mm: float = 3.0   # ≥ 2mm


@dataclass
class PolygonParams(BaseParams):
    """Custom polygon electrode parameters.

    Design rules:
    - Vertices define the electrode outline (minimum 3 for closed polygon)
    - Coordinates are in mm; auto-scaled to fit substrate
    - Trace width: 0.3-1mm for screen printing
    - Pad connects to nearest vertex for external contact
    - Common shapes: triangle, hexagon, diamond, custom
    """
    vertices: str = "5,0;10,8.66;0,8.66"  # Equilateral triangle (mm)
    trace_w_mm: float = 0.8    # 0.3-1mm
    pad_size_mm: float = 3.0   # ≥ 2mm
    pad_x_mm: float = -1.0    # Pad X position (-1 = auto left)
    pad_y_mm: float = -1.0    # Pad Y position (-1 = auto centre)


# ─────────────────────────────────────────────────────────────────────
# Fabrication constraints & design validation
# ─────────────────────────────────────────────────────────────────────

# Minimum feature sizes by fabrication method (mm)
FAB_CONSTRAINTS = {
    "screen_print": {"min_trace": 0.2, "min_gap": 0.2, "min_pad": 1.5},
    "cricut_vinyl": {"min_trace": 0.5, "min_gap": 0.5, "min_pad": 2.0},
    "laser_co2":    {"min_trace": 0.2, "min_gap": 0.2, "min_pad": 1.0},
    "laser_lig":    {"min_trace": 0.5, "min_gap": 0.5, "min_pad": 2.0},  # beam diameter limit
    "cnc_mill":     {"min_trace": 0.3, "min_gap": 0.3, "min_pad": 1.0},
}


def validate_design(params, fab_method="screen_print"):
    """Validate electrode design against fabrication constraints.

    Returns list of warnings (empty = all good).
    """
    warnings = []
    fc = FAB_CONSTRAINTS.get(fab_method, FAB_CONSTRAINTS["screen_print"])

    # Common checks
    if hasattr(params, "trace_w_mm") and params.trace_w_mm < fc["min_trace"]:
        warnings.append(
            f"Trace width {params.trace_w_mm}mm < {fc['min_trace']}mm "
            f"minimum for {fab_method}"
        )
    if hasattr(params, "pad_size_mm") and params.pad_size_mm < fc["min_pad"]:
        warnings.append(
            f"Pad size {params.pad_size_mm}mm < {fc['min_pad']}mm "
            f"minimum for reliable contact"
        )

    # IDE-specific checks
    if isinstance(params, IDEParams):
        if params.gap_mm > params.finger_w_mm:
            warnings.append(
                f"Gap ({params.gap_mm}mm) > finger width ({params.finger_w_mm}mm). "
                f"For optimal redox cycling, gap should be ≤ finger width."
            )
        if params.gap_mm < fc["min_gap"]:
            warnings.append(
                f"Gap {params.gap_mm}mm < {fc['min_gap']}mm minimum for {fab_method}"
            )
        if params.bus_w_mm < 2 * params.finger_w_mm:
            warnings.append(
                f"Bus bar ({params.bus_w_mm}mm) should be ≥ 2× finger width "
                f"({2*params.finger_w_mm}mm) for low resistance"
            )

    # Three-electrode: CE must be ≥ 10× WE area
    if isinstance(params, ThreeElectrodeParams):
        we_area = math.pi * (params.we_d_mm / 2) ** 2
        ce_area = math.pi * (params.ce_d_mm / 2) ** 2
        if ce_area < 10 * we_area:
            min_ce_d = params.we_d_mm * math.sqrt(10)
            warnings.append(
                f"CE area ({ce_area:.1f}mm²) < 10× WE area ({we_area:.1f}mm²). "
                f"The 10:1 rule requires CE diameter ≥ {min_ce_d:.1f}mm."
            )

    # Ring-disk: gap and ring width checks
    if isinstance(params, RingDiskParams):
        if params.gap_mm < 0.3:
            warnings.append(
                f"Gap {params.gap_mm}mm is very tight. Standard RRDE gap is 0.375mm. "
                f"Difficult to fabricate with screen printing."
            )

    # Array: pitch must be ≥ 3× diameter to avoid crosstalk
    if isinstance(params, ArrayParams):
        min_pitch = 3 * params.electrode_d_mm
        if params.pitch_x_mm < min_pitch or params.pitch_y_mm < min_pitch:
            warnings.append(
                f"Pitch ({params.pitch_x_mm}×{params.pitch_y_mm}mm) < 3× electrode "
                f"diameter ({min_pitch}mm). May cause electrochemical crosstalk."
            )

    # Serpentine/Meander: amplitude vs segment height
    if isinstance(params, (SerpentineParams, MeanderParams)):
        if hasattr(params, "meander_amp_mm") and hasattr(params, "seg_h_mm"):
            if params.meander_amp_mm > params.seg_h_mm / 2:
                warnings.append(
                    f"Meander amplitude ({params.meander_amp_mm}mm) > seg_h/2 "
                    f"({params.seg_h_mm/2}mm). Waves will overlap!"
                )

    # Spiral: trace width vs spacing
    if isinstance(params, SpiralParams):
        spacing = (params.r_end_mm - params.r_start_mm) / params.turns if params.turns > 0 else 0
        if params.trace_w_mm > spacing and spacing > 0:
            warnings.append(
                f"Trace width ({params.trace_w_mm}mm) > turn spacing "
                f"({spacing:.2f}mm). Spiral turns will overlap!"
            )

    return warnings


def print_design_info(elec_type, params):
    """Print helpful design information for the electrode type."""
    info = {
        "ide": (
            "Interdigitated Electrode (IDE)\n"
            "  Use: Amperometric/impedimetric biosensors, humidity sensors\n"
            "  Principle: Two interlocking combs; analyte changes impedance between fingers\n"
            "  Key rule: Gap ≤ finger width for optimal redox cycling\n"
            "  Typical materials: Au, Pt, C on glass/PET/Kapton"
        ),
        "three": (
            "Three-Electrode System\n"
            "  Use: Cyclic voltammetry, impedance spectroscopy, battery testing\n"
            "  WE: Where reaction happens | CE: Completes circuit | RE: Stable potential\n"
            "  Key rule: CE area ≥ 10× WE area (prevents CE from limiting current)\n"
            "  Typical materials: WE=GC/Pt/Au, CE=Pt, RE=Ag/AgCl"
        ),
        "serpentine": (
            "Serpentine Electrode\n"
            "  Use: Stretchable/wearable electronics, resistive heaters\n"
            "  Principle: Zigzag trace accommodates mechanical strain\n"
            "  Key rule: L/H ratio 1.5-3:1 for optimal stretchability\n"
            "  Typical materials: Ag ink, Cu on TPU/PDMS"
        ),
        "ringdisk": (
            "Ring-Disk Electrode\n"
            "  Use: Generator-collector experiments, ORR studies\n"
            "  Principle: Disk generates product; ring collects it\n"
            "  Key rule: Gap controls collection efficiency (N≈0.256 standard)\n"
            "  Typical materials: GC disk, Pt ring"
        ),
        "array": (
            "Electrode Array\n"
            "  Use: High-throughput screening, multiplexed sensing\n"
            "  Principle: Multiple electrodes share a common bus bar\n"
            "  Key rule: Pitch ≥ 3× electrode diameter to avoid crosstalk\n"
            "  Typical materials: Carbon, Au, Ag on PET/alumina"
        ),
        "meander": (
            "Meander (Spring Serpentine) Electrode\n"
            "  Use: Wearable sensors, stretchable interconnects\n"
            "  Principle: Sinusoidal waves on each segment add stretchability\n"
            "  Key rule: Amplitude ≤ seg_h/2 to prevent overlap\n"
            "  Typical materials: Ag/Cu ink on TPU/PDMS"
        ),
        "carray": (
            "Circular/Radial Array\n"
            "  Use: Radial electrochemistry, multi-analyte detection\n"
            "  Principle: Concentric rings with radial traces to centre pad\n"
            "  Key rule: Ring spacing ≥ electrode diameter\n"
            "  Typical materials: Au, C on glass/PET"
        ),
        "spiral": (
            "Spiral Electrode\n"
            "  Use: Impedance sensors, inductors, heating elements\n"
            "  Principle: Archimedean spiral; uniform turn spacing\n"
            "  Key rule: Turn spacing ≥ trace width; 3-10 turns typical\n"
            "  Typical materials: Au, Ag, C on glass/PET/Kapton"
        ),
        "polygon": (
            "Custom Polygon Electrode\n"
            "  Use: Any custom geometry (hexagons, diamonds, etc.)\n"
            "  Principle: Define vertices; auto-scale to fit substrate\n"
            "  Key rule: Minimum 3 vertices for closed shape\n"
            "  Typical materials: Any conductive material on any substrate"
        ),
    }
    if elec_type in info:
        print(f"\n  📋 {info[elec_type]}")


# ─────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────

def rect_points(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def circle_points(cx, cy, r, n=64):
    pts = []
    for i in range(n + 1):
        angle = 2 * math.pi * i / n
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


# ─────────────────────────────────────────────────────────────────────
# DXF writer
# ─────────────────────────────────────────────────────────────────────

class DXFWriter:
    def __init__(self, version="R2010"):
        self.doc = ezdxf.new(dxfversion=version)
        self.msp = self.doc.modelspace()
        self.doc.units = units.MM

    def add_layer(self, name, color=7):
        self.doc.layers.add(name, color=color)

    def polyline(self, points, layer="0", closed=True):
        self.msp.add_lwpolyline(points, dxfattribs={"layer": layer}, close=closed)

    def circle(self, cx, cy, r, layer="0"):
        self.msp.add_circle((cx, cy), r, dxfattribs={"layer": layer})

    def line(self, x1, y1, x2, y2, layer="0"):
        self.msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})

    def rectangle(self, x, y, w, h, layer="0"):
        self.polyline(rect_points(x, y, w, h), layer=layer, closed=True)

    def text(self, content, x, y, layer="0", height=0.8):
        self.msp.add_text(content, dxfattribs={"layer": layer, "height": height, "insert": (x, y)})

    def save(self, path):
        self.doc.saveas(path)
        print(f"  DXF saved: {path}")


# ─────────────────────────────────────────────────────────────────────
# SVG writer
# ─────────────────────────────────────────────────────────────────────

class GCodeWriter:
    """G-code writer for CNC laser cutters and pen plotters.

    Generates standard G-code with:
    - G21 (mm units), G90 (absolute positioning)
    - G0 (rapid move, laser off)
    - G1 (linear move, laser on) with feed rate
    - M3/M5 (laser/pen on/off)
    - Arc interpolation (G2/G3) for circles where supported
    """

    def __init__(self, feed_rate=1000, laser_power=1000, rapid_rate=3000,
                 flip_y=False):
        """
        Args:
            feed_rate: Cutting feed rate in mm/min
            laser_power: Laser power (0-1000 for GRBL, 0-255 for some controllers)
            rapid_rate: Rapid move feed rate
            flip_y: If True, mirror Y axis (some machines have Y=0 at top)
        """
        self.feed = feed_rate
        self.power = laser_power
        self.rapid = rapid_rate
        self.flip_y = flip_y
        self.lines = []
        self._current_x = None
        self._current_y = None
        self._laser_on = False

    def _y(self, y):
        """Flip Y if needed."""
        return -y if self.flip_y else y

    def _fmt(self, v):
        return f"{v:.3f}"

    def header(self, width_mm=25, height_mm=25):
        """Write G-code header."""
        self.lines.append("; ── Generated by Electrode Generator ──")
        self.lines.append(f"; Substrate: {self._fmt(width_mm)} x {self._fmt(height_mm)} mm")
        self.lines.append(f"; Feed rate: {self.feed} mm/min")
        self.lines.append(f"; Laser power: {self.power}")
        self.lines.append("")
        self.lines.append("G21          ; Set units to mm")
        self.lines.append("G90          ; Absolute positioning")
        self.lines.append("G92 X0 Y0    ; Set current position as origin")
        self.lines.append("M5           ; Laser off (safety)")
        self.lines.append("")

    def footer(self):
        """Write G-code footer."""
        self.laser_off()
        self.lines.append("")
        self.lines.append("G0 X0 Y0     ; Return to origin")
        self.lines.append("M5           ; Laser off")
        self.lines.append("M2           ; End program")
        self.lines.append("")

    def laser_on(self):
        if not self._laser_on:
            self.lines.append(f"M3 S{self.power}    ; Laser on")
            self._laser_on = True

    def laser_off(self):
        if self._laser_on:
            self.lines.append("M5            ; Laser off")
            self._laser_on = False

    def rapid_move(self, x, y):
        """Rapid move with laser off."""
        self.laser_off()
        self.lines.append(f"G0 X{self._fmt(x)} Y{self._fmt(self._y(y))}")
        self._current_x = x
        self._current_y = y

    def cut_move(self, x, y):
        """Linear cut move with laser on."""
        self.laser_on()
        self.lines.append(f"G1 X{self._fmt(x)} Y{self._fmt(self._y(y))} F{self.feed}")
        self._current_x = x
        self._current_y = y

    def comment(self, text):
        self.lines.append(f"; {text}")

    # ── Shape primitives ──────────────────────────────────────────

    def polyline(self, points, closed=True):
        """Cut a polyline path."""
        if not points:
            return
        # Rapid to start
        self.rapid_move(points[0][0], points[0][1])
        # Cut along path
        for x, y in points[1:]:
            self.cut_move(x, y)
        if closed and len(points) > 2:
            # Close back to start
            self.cut_move(points[0][0], points[0][1])
        self.laser_off()

    def circle(self, cx, cy, r, n=64):
        """Cut a circle as a polygon approximation."""
        pts = []
        for i in range(n + 1):
            angle = 2 * math.pi * i / n
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        self.polyline(pts, closed=True)

    def rectangle(self, x, y, w, h):
        """Cut a rectangle."""
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        self.polyline(pts, closed=True)

    def line(self, x1, y1, x2, y2):
        """Cut a single line."""
        self.rapid_move(x1, y1)
        self.cut_move(x2, y2)
        self.laser_off()

    # ── DXF-compatible API (so generators work unchanged) ──────────

    def add_layer(self, name, color=7):
        """No-op for DXF compatibility; G-code doesn't use layers."""
        pass

    def text(self, content, x, y, layer="0", height=0.8):
        """Add a comment instead of text."""
        self.comment(content)

    def save(self, path):
        """Save G-code to file."""
        with open(path, 'w') as f:
            f.write('\n'.join(self.lines))
        print(f"  G-code saved: {path}")

    def get_string(self):
        """Return G-code as string."""
        return '\n'.join(self.lines)


class LayerCollector:
    """Collects shapes with layer names for multi-layer export.

    Mimics the DXFWriter/SVGWriter API so generators can use it directly.
    Stores all shapes with their layer name, then exports per-layer files.
    """

    def __init__(self, width_mm=25, height_mm=25):
        self.width = width_mm
        self.height = height_mm
        self.shapes = []  # list of (layer_name, shape_type, args, kwargs)
        self._layers = {}  # layer_name -> color

    def add_layer(self, name, color=7):
        self._layers[name] = color

    def polyline(self, points, layer="0", closed=True):
        self.shapes.append((layer, "polyline", points, {"closed": closed}))

    def circle(self, cx, cy, r, layer="0"):
        self.shapes.append((layer, "circle", (cx, cy, r), {}))

    def line(self, x1, y1, x2, y2, layer="0"):
        self.shapes.append((layer, "line", (x1, y1, x2, y2), {}))

    def rectangle(self, x, y, w, h, layer="0"):
        self.shapes.append((layer, "rectangle", (x, y, w, h), {}))

    def text(self, content, x, y, layer="0", height=0.8):
        pass  # Skip text in layer export

    def get_layers(self):
        """Return dict of layer_name -> list of shapes."""
        layers = {}
        for layer, stype, args, kwargs in self.shapes:
            if layer not in layers:
                layers[layer] = []
            layers[layer].append((stype, args, kwargs))
        return layers

    def get_layer_names(self):
        """Return ordered list of unique layer names."""
        seen = []
        for layer, *_ in self.shapes:
            if layer not in seen:
                seen.append(layer)
        return seen


def write_layer_dxf(collector, path, layer_name):
    """Write a single layer to a DXF file."""
    dxf = DXFWriter()
    dxf.add_layer(layer_name, color=collector._layers.get(layer_name, 7))
    for stype, args, kwargs in collector.get_layers().get(layer_name, []):
        if stype == "polyline":
            dxf.polyline(args, layer=layer_name, **kwargs)
        elif stype == "circle":
            dxf.circle(*args, layer=layer_name)
        elif stype == "line":
            dxf.line(*args, layer=layer_name)
        elif stype == "rectangle":
            dxf.rectangle(*args, layer=layer_name)
    dxf.save(path)


def write_layer_svg(collector, path, layer_name, color="#000000"):
    """Write a single layer to an SVG file."""
    svg = SVGWriter(collector.width, collector.height)
    layer_group = svg.add_layer(layer_name, color=color)
    for stype, args, kwargs in collector.get_layers().get(layer_name, []):
        if stype == "polyline":
            svg.polyline(args, layer_group, **kwargs)
        elif stype == "circle":
            svg.circle(*args, layer=layer_group)
        elif stype == "line":
            svg.line(*args, layer=layer_group)
        elif stype == "rectangle":
            svg.rectangle(*args, layer=layer_group)
    svg.save(path)


def write_layer_gcode(collector, path, layer_name, feed_rate=1000,
                       laser_power=1000, flip_y=False):
    """Write a single layer to a G-code file."""
    gc = GCodeWriter(feed_rate=feed_rate, laser_power=laser_power, flip_y=flip_y)
    gc.header(collector.width, collector.height)
    gc.comment(f"Layer: {layer_name}")
    for stype, args, kwargs in collector.get_layers().get(layer_name, []):
        if stype == "polyline":
            gc.polyline(args, **kwargs)
        elif stype == "circle":
            gc.circle(*args)
        elif stype == "line":
            gc.line(*args)
        elif stype == "rectangle":
            gc.rectangle(*args)
    gc.footer()
    gc.save(path)


def export_layers(collector, base_path, fmt, layers_filter=None,
                   feed_rate=1000, laser_power=1000, flip_y=False):
    """Export collected layers to per-layer files.

    Args:
        collector: LayerCollector with shapes
        base_path: Output path without extension
        fmt: 'dxf', 'svg', 'gcode', 'both', or 'all'
        layers_filter: list of layer names to export (None = all)
        feed_rate, laser_power, flip_y: G-code parameters
    """
    all_layers = collector.get_layers()
    layer_names = [n for n in collector.get_layer_names() if n in all_layers]

    if layers_filter:
        layer_names = [n for n in layer_names if n in layers_filter]

    if not layer_names:
        print("  No layers to export")
        return

    # Color map for SVG layers
    color_map = {
        "SUBSTRATE": "#AAAAAA", "ELECTRODE_A": "#CC0000",
        "ELECTRODE_B": "#0000CC", "PAD": "#00AA00",
        "WE": "#CC0000", "CE": "#0000CC", "RE": "#00AA00",
        "TRACE": "#888888", "DISK": "#CC0000", "RING": "#0000CC",
        "BUS": "#0000CC", "ELECTRODES": "#CC0000",
        "CENTRE": "#0000CC", "SPIRAL": "#CC0000", "POLYGON": "#CC0000",
    }

    print(f"  Multi-layer export: {len(layer_names)} layers")
    for name in layer_names:
        safe = name.lower().replace(" ", "_")
        if fmt in ("dxf", "both", "all"):
            write_layer_dxf(collector, f"{base_path}_{safe}.dxf", name)
        if fmt in ("svg", "both", "all"):
            color = color_map.get(name, "#000000")
            write_layer_svg(collector, f"{base_path}_{safe}.svg", name, color=color)
        if fmt in ("gcode", "all"):
            write_layer_gcode(collector, f"{base_path}_{safe}.gcode", name,
                              feed_rate=feed_rate, laser_power=laser_power, flip_y=flip_y)


class SVGWriter:
    def __init__(self, width_mm, height_mm, precision=4):
        self.p = precision
        self.dwg = svgwrite.Drawing(
            size=(f"{width_mm}mm", f"{height_mm}mm"),
            viewBox=f"0 0 {width_mm} {height_mm}",
        )
        self.dwg.add(self.dwg.rect(insert=(0, 0), size=(width_mm, height_mm),
                                    fill="#FFFFFF", stroke="none"))

    def _fmt(self, v):
        return f"{v:.{self.p}f}"

    def add_layer(self, name, color="#000000"):
        g = self.dwg.g(id=name, stroke=color, fill=color,
                       stroke_width="0.01", fill_rule="evenodd")
        self.dwg.add(g)
        return g

    def polyline(self, points, layer, closed=True):
        d_parts = [f"M {self._fmt(points[0][0])} {self._fmt(points[0][1])}"]
        for px, py in points[1:]:
            d_parts.append(f"L {self._fmt(px)} {self._fmt(py)}")
        if closed:
            d_parts.append("Z")
        path = self.dwg.path(d=" ".join(d_parts))
        layer.add(path)

    def circle(self, cx, cy, r, layer):
        c = self.dwg.circle(center=(self._fmt(cx), self._fmt(cy)), r=self._fmt(r))
        layer.add(c)

    def rectangle(self, x, y, w, h, layer):
        r = self.dwg.rect(insert=(self._fmt(x), self._fmt(y)),
                          size=(self._fmt(w), self._fmt(h)))
        layer.add(r)

    def save(self, path):
        self.dwg.saveas(path)
        print(f"  SVG saved: {path}")


# Layer definitions for each electrode type
LAYER_NAMES = {
    "ide": ["SUBSTRATE", "ELECTRODE_A", "ELECTRODE_B", "PAD"],
    "three": ["SUBSTRATE", "WE", "CE", "RE", "PAD", "TRACE"],
    "serpentine": ["SUBSTRATE", "TRACE", "PAD"],
    "ringdisk": ["SUBSTRATE", "DISK", "RING", "PAD", "TRACE"],
    "array": ["SUBSTRATE", "ELECTRODES", "BUS", "PAD", "TRACE"],
    "meander": ["SUBSTRATE", "TRACE", "PAD"],
    "carray": ["SUBSTRATE", "ELECTRODES", "CENTRE", "TRACE"],
    "spiral": ["SUBSTRATE", "SPIRAL", "PAD", "TRACE"],
    "polygon": ["SUBSTRATE", "POLYGON", "PAD", "TRACE"],
}

# ─────────────────────────────────────────────────────────────────────
# Electrode generators
# ─────────────────────────────────────────────────────────────────────

def generate_ide(p, dxf, svg, gcode=None):
    """Generate interdigitated electrode (comb-finger array)."""
    n = p.fingers
    fw = p.finger_w_mm
    gap = p.gap_mm
    fl = p.finger_l_mm
    ps = p.pad_size_mm
    bw = p.bus_w_mm
    margin = p.margin_mm

    total_fingers_w = n * fw + (n - 1) * gap
    x0 = (p.width_mm - total_fingers_w) / 2
    bus_top_y = margin + fl + bw
    bus_bot_y = margin

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("ELECTRODE_A", color=1)
        dxf.add_layer("ELECTRODE_B", color=5)
        dxf.add_layer("PAD", color=3)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_a = svg.add_layer("ELECTRODE_A", color="#CC0000")
        l_b = svg.add_layer("ELECTRODE_B", color="#0000CC")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)

    if gcode:
        gcode.comment(f"IDE: {n} pairs, fw={fw}mm, gap={gap}mm, fl={fl}mm")

    # Electrode A: bus at top, fingers hang down
    bus_a_x = x0 - bw
    bus_a_y = bus_top_y
    bus_a_w = total_fingers_w + 2 * bw
    pad_a_x = x0 - bw - ps - 1.0
    pad_a_y = bus_top_y + (bw - ps) / 2

    # Electrode B: bus at bottom, fingers rise up
    bus_b_x = x0 - bw
    bus_b_y = bus_bot_y - bw
    bus_b_w = total_fingers_w + 2 * bw
    pad_b_x = x0 + total_fingers_w + bw + 1.0
    pad_b_y = bus_bot_y - bw + (bw - ps) / 2

    # --- Electrode A ---
    if dxf:
        dxf.rectangle(pad_a_x, pad_a_y, ps, ps, layer="PAD")
        dxf.rectangle(bus_a_x, bus_a_y, bus_a_w, bw, layer="ELECTRODE_A")
        for i in range(n):
            fx = x0 + i * (fw + gap)
            fy = bus_top_y - fl
            dxf.rectangle(fx, fy, fw, fl, layer="ELECTRODE_A")
        dxf.polyline([(pad_a_x + ps, pad_a_y + ps / 2), (bus_a_x, bus_a_y + bw / 2)],
                     layer="ELECTRODE_A", closed=False)

    if svg:
        svg.rectangle(pad_a_x, pad_a_y, ps, ps, l_pad)
        svg.rectangle(bus_a_x, bus_a_y, bus_a_w, bw, l_a)
        for i in range(n):
            fx = x0 + i * (fw + gap)
            fy = bus_top_y - fl
            svg.rectangle(fx, fy, fw, fl, l_a)
        svg.polyline([(pad_a_x + ps, pad_a_y + ps / 2), (bus_a_x, bus_a_y + bw / 2)],
                     l_a, closed=False)

    if gcode:
        gcode.rectangle(pad_a_x, pad_a_y, ps, ps)
        gcode.rectangle(bus_a_x, bus_a_y, bus_a_w, bw)
        for i in range(n):
            fx = x0 + i * (fw + gap)
            fy = bus_top_y - fl
            gcode.rectangle(fx, fy, fw, fl)
        gcode.line(pad_a_x + ps, pad_a_y + ps / 2, bus_a_x, bus_a_y + bw / 2)

    # --- Electrode B ---
    if dxf:
        dxf.rectangle(pad_b_x, pad_b_y, ps, ps, layer="PAD")
        dxf.rectangle(bus_b_x, bus_b_y, bus_b_w, bw, layer="ELECTRODE_B")
        offset = fw / 2 + gap / 2
        for i in range(n):
            fx = x0 + i * (fw + gap) + offset
            fy = bus_bot_y
            dxf.rectangle(fx, fy, fw, fl, layer="ELECTRODE_B")
        dxf.polyline([(pad_b_x, pad_b_y + ps / 2), (bus_b_x + bus_b_w, bus_b_y + bw / 2)],
                     layer="ELECTRODE_B", closed=False)

    if svg:
        svg.rectangle(pad_b_x, pad_b_y, ps, ps, l_pad)
        svg.rectangle(bus_b_x, bus_b_y, bus_b_w, bw, l_b)
        offset = fw / 2 + gap / 2
        for i in range(n):
            fx = x0 + i * (fw + gap) + offset
            fy = bus_bot_y
            svg.rectangle(fx, fy, fw, fl, l_b)
        svg.polyline([(pad_b_x, pad_b_y + ps / 2), (bus_b_x + bus_b_w, bus_b_y + bw / 2)],
                     l_b, closed=False)

    if gcode:
        gcode.rectangle(pad_b_x, pad_b_y, ps, ps)
        gcode.rectangle(bus_b_x, bus_b_y, bus_b_w, bw)
        offset = fw / 2 + gap / 2
        for i in range(n):
            fx = x0 + i * (fw + gap) + offset
            fy = bus_bot_y
            gcode.rectangle(fx, fy, fw, fl)
        gcode.line(pad_b_x, pad_b_y + ps / 2, bus_b_x + bus_b_w, bus_b_y + bw / 2)

    if dxf:
        dxf.text(f"IDE: {n} pairs, fw={fw}mm, gap={gap}mm, fl={fl}mm",
                 margin, p.height_mm - margin / 2, layer="SUBSTRATE")

    print(f"  IDE generated: {n} finger pairs, {fw}mm wide, {gap}mm gap")


def generate_three(p, dxf, svg, gcode=None):
    """Generate three-electrode system (WE centre, CE ring, RE adjacent)."""
    cx = p.width_mm / 2
    cy = p.height_mm / 2
    we_r = p.we_d_mm / 2
    ce_gap = 0.3
    ce_r_inner = we_r + ce_gap
    ce_r_outer = ce_r_inner + p.ce_d_mm / 2
    re_r = p.re_d_mm / 2
    re_cx = cx - p.spacing_mm
    re_cy = cy

    # Compute pad positions (shared across dxf/svg/gcode)
    ps = p.pad_size_mm
    we_pad_x = cx + ce_r_outer + 2
    we_pad_y = cy - ps / 2
    ce_pad_x = cx - ps / 2
    ce_pad_y = cy + ce_r_outer + 2
    re_pad_x = re_cx - re_r - 2 - ps
    re_pad_y = re_cy - ps / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("WE", color=1)
        dxf.add_layer("CE", color=5)
        dxf.add_layer("RE", color=3)
        dxf.add_layer("PAD", color=7)
        dxf.add_layer("TRACE", color=6)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.circle(cx, cy, we_r, layer="WE")
        dxf.circle(cx, cy, ce_r_outer, layer="CE")
        dxf.circle(cx, cy, ce_r_inner, layer="CE")
        dxf.circle(re_cx, re_cy, re_r, layer="RE")
        dxf.rectangle(we_pad_x, we_pad_y, ps, ps, layer="PAD")
        dxf.polyline([(cx + we_r, cy), (we_pad_x, we_pad_y + ps / 2)], layer="TRACE", closed=False)
        dxf.rectangle(ce_pad_x, ce_pad_y, ps, ps, layer="PAD")
        dxf.polyline([(cx, cy + ce_r_outer), (cx, ce_pad_y)], layer="TRACE", closed=False)
        dxf.rectangle(re_pad_x, re_pad_y, ps, ps, layer="PAD")
        dxf.polyline([(re_cx - re_r, re_cy), (re_pad_x + ps, re_pad_y + ps / 2)],
                     layer="TRACE", closed=False)
        dxf.text("WE", cx - 0.5, cy - 0.3, layer="WE")
        dxf.text("CE", cx - 0.5, cy + ce_r_outer + 0.5, layer="CE")
        dxf.text("RE", re_cx - 0.5, re_cy - 0.3, layer="RE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_we = svg.add_layer("WE", color="#CC0000")
        l_ce = svg.add_layer("CE", color="#0000CC")
        l_re = svg.add_layer("RE", color="#00AA00")
        l_pad = svg.add_layer("PAD", color="#888888")
        l_trace = svg.add_layer("TRACE", color="#888888")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.circle(cx, cy, we_r, l_we)
        svg.circle(cx, cy, ce_r_outer, l_ce)
        svg.circle(cx, cy, ce_r_inner, l_ce)
        svg.circle(re_cx, re_cy, re_r, l_re)
        svg.rectangle(we_pad_x, we_pad_y, ps, ps, l_pad)
        svg.polyline([(cx + we_r, cy), (we_pad_x, we_pad_y + ps / 2)], l_trace, closed=False)
        svg.rectangle(ce_pad_x, ce_pad_y, ps, ps, l_pad)
        svg.polyline([(cx, cy + ce_r_outer), (cx, ce_pad_y)], l_trace, closed=False)
        svg.rectangle(re_pad_x, re_pad_y, ps, ps, l_pad)
        svg.polyline([(re_cx - re_r, re_cy), (re_pad_x + ps, re_pad_y + ps / 2)],
                     l_trace, closed=False)

    if gcode:
        gcode.comment(f"Three-electrode: WE={p.we_d_mm}mm, CE={p.ce_d_mm}mm, RE={p.re_d_mm}mm")
        gcode.circle(cx, cy, we_r)
        gcode.circle(cx, cy, ce_r_outer)
        gcode.circle(cx, cy, ce_r_inner)
        gcode.circle(re_cx, re_cy, re_r)
        gcode.rectangle(we_pad_x, we_pad_y, ps, ps)
        gcode.line(cx + we_r, cy, we_pad_x, we_pad_y + ps / 2)
        gcode.rectangle(ce_pad_x, ce_pad_y, ps, ps)
        gcode.line(cx, cy + ce_r_outer, cx, ce_pad_y)
        gcode.rectangle(re_pad_x, re_pad_y, ps, ps)
        gcode.line(re_cx - re_r, re_cy, re_pad_x + ps, re_pad_y + ps / 2)

    print(f"  Three-electrode generated: WE={p.we_d_mm}mm, CE={p.ce_d_mm}mm, RE={p.re_d_mm}mm")


def generate_serpentine(p, dxf, svg, gcode=None):
    """Generate serpentine / zigzag electrode trace."""
    tw = p.trace_w_mm
    n = p.segments
    sl = p.seg_l_mm
    sh = p.seg_h_mm
    ps = p.pad_size_mm
    margin = p.margin_mm

    total_h = n * sh
    x0 = (p.width_mm - sl) / 2
    y0 = (p.height_mm - total_h) / 2

    path = []
    y = y0
    for i in range(n):
        if i % 2 == 0:
            path.append((x0, y))
            path.append((x0 + sl, y))
            y += sh
            path.append((x0 + sl, y))
        else:
            path.append((x0 + sl, y))
            path.append((x0, y))
            y += sh
            path.append((x0, y))

    pad_x = x0 - ps - 1
    pad_y = y0 + sh / 2 - ps / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("TRACE", color=1)
        dxf.add_layer("PAD", color=3)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.rectangle(pad_x, pad_y, ps, ps, layer="PAD")
        dxf.polyline([(pad_x + ps, pad_y + ps / 2), (x0, y0)], layer="TRACE", closed=False)
        dxf.polyline(path, layer="TRACE", closed=False)
        dxf.text(f"Serpentine: {n} segments, {sl}x{sh}mm, w={tw}mm",
                 margin, p.height_mm - margin / 2, layer="SUBSTRATE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_trace = svg.add_layer("TRACE", color="#CC0000")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.rectangle(pad_x, pad_y, ps, ps, l_pad)
        svg.polyline([(pad_x + ps, pad_y + ps / 2), (x0, y0)], l_trace, closed=False)
        # Filled polygon for proper thickness
        half_t = tw / 2
        filled_pts = []
        for i, (px, py) in enumerate(path):
            if i < len(path) - 1:
                dx = path[i + 1][0] - px
                dy = path[i + 1][1] - py
            else:
                dx = px - path[i - 1][0]
                dy = py - path[i - 1][1]
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                nx, ny = 0, 1
            else:
                nx, ny = -dy / length, dx / length
            filled_pts.append((px + nx * half_t, py + ny * half_t))
        for i in range(len(path) - 1, -1, -1):
            px, py = path[i]
            if i < len(path) - 1:
                dx = path[i + 1][0] - px
                dy = path[i + 1][1] - py
            else:
                dx = px - path[i - 1][0]
                dy = py - path[i - 1][1]
            length = math.sqrt(dx * dx + dy * dy)
            if length == 0:
                nx, ny = 0, 1
            else:
                nx, ny = -dy / length, dx / length
            filled_pts.append((px - nx * half_t, py - ny * half_t))
        filled_pts.append(filled_pts[0])
        svg.polyline(filled_pts, l_trace, closed=True)

    if gcode:
        gcode.comment(f"Serpentine: {n} segments, {sl}x{sh}mm, w={tw}mm")
        gcode.rectangle(pad_x, pad_y, ps, ps)
        gcode.line(pad_x + ps, pad_y + ps / 2, x0, y0)
        gcode.polyline(path, closed=False)

    print(f"  Serpentine generated: {n} segments, {sl}x{sh}mm each")


def generate_ringdisk(p, dxf, svg, gcode=None):
    """Generate ring-disk electrode."""
    cx = p.width_mm / 2
    cy = p.height_mm / 2
    disk_r = p.disk_d_mm / 2
    ring_gap = p.gap_mm
    ring_w = p.ring_w_mm
    ring_r_inner = disk_r + ring_gap
    ring_r_outer = ring_r_inner + ring_w

    ps = p.pad_size_mm
    disk_pad_x = cx - ring_r_outer - 3 - ps
    disk_pad_y = cy - ps / 2
    ring_pad_x = cx + ring_r_outer + 3
    ring_pad_y = cy - ps / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("DISK", color=1)
        dxf.add_layer("RING", color=5)
        dxf.add_layer("PAD", color=3)
        dxf.add_layer("TRACE", color=6)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.circle(cx, cy, disk_r, layer="DISK")
        dxf.circle(cx, cy, ring_r_outer, layer="RING")
        dxf.circle(cx, cy, ring_r_inner, layer="RING")
        dxf.rectangle(disk_pad_x, disk_pad_y, ps, ps, layer="PAD")
        dxf.polyline([(cx - disk_r, cy), (disk_pad_x + ps, cy)], layer="TRACE", closed=False)
        dxf.rectangle(ring_pad_x, ring_pad_y, ps, ps, layer="PAD")
        dxf.polyline([(cx + ring_r_outer, cy), (ring_pad_x, cy)], layer="TRACE", closed=False)
        dxf.text("DISK", cx - 1, cy - 0.2, layer="DISK")
        dxf.text("RING", cx - 1, cy + ring_r_outer + 0.3, layer="RING")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_disk = svg.add_layer("DISK", color="#CC0000")
        l_ring = svg.add_layer("RING", color="#0000CC")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        l_trace = svg.add_layer("TRACE", color="#888888")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.circle(cx, cy, disk_r, l_disk)
        svg.circle(cx, cy, ring_r_outer, l_ring)
        svg.circle(cx, cy, ring_r_inner, l_ring)
        svg.rectangle(disk_pad_x, disk_pad_y, ps, ps, l_pad)
        svg.polyline([(cx - disk_r, cy), (disk_pad_x + ps, cy)], l_trace, closed=False)
        svg.rectangle(ring_pad_x, ring_pad_y, ps, ps, l_pad)
        svg.polyline([(cx + ring_r_outer, cy), (ring_pad_x, cy)], l_trace, closed=False)

    if gcode:
        gcode.comment(f"Ring-disk: disk={p.disk_d_mm}mm, gap={p.gap_mm}mm, ring_w={p.ring_w_mm}mm")
        gcode.circle(cx, cy, disk_r)
        gcode.circle(cx, cy, ring_r_outer)
        gcode.circle(cx, cy, ring_r_inner)
        gcode.rectangle(disk_pad_x, disk_pad_y, ps, ps)
        gcode.line(cx - disk_r, cy, disk_pad_x + ps, cy)
        gcode.rectangle(ring_pad_x, ring_pad_y, ps, ps)
        gcode.line(cx + ring_r_outer, cy, ring_pad_x, cy)

    print(f"  Ring-disk generated: disk={p.disk_d_mm}mm, gap={p.gap_mm}mm, ring_w={p.ring_w_mm}mm")


def generate_array(p, dxf, svg, gcode=None):
    """Generate uniform electrode array (grid of circular electrodes)."""
    rows = p.rows
    cols = p.cols
    ed = p.electrode_d_mm
    px = p.pitch_x_mm
    py = p.pitch_y_mm
    tw = p.trace_w_mm
    ps = p.pad_size_mm

    array_w = (cols - 1) * px
    array_h = (rows - 1) * py
    x0 = (p.width_mm - array_w) / 2
    y0 = (p.height_mm - array_h) / 2

    bus_y = y0 - 3
    bus_x = x0 - 2
    bus_w = array_w + 4
    bus_h = 1.5
    pad_x = bus_x - ps - 1
    pad_y = bus_y + (bus_h - ps) / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("ELECTRODES", color=1)
        dxf.add_layer("BUS", color=5)
        dxf.add_layer("PAD", color=3)
        dxf.add_layer("TRACE", color=6)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.rectangle(bus_x, bus_y, bus_w, bus_h, layer="BUS")
        dxf.rectangle(pad_x, pad_y, ps, ps, layer="PAD")
        dxf.polyline([(pad_x + ps, pad_y + ps / 2), (bus_x, bus_y + bus_h / 2)],
                     layer="TRACE", closed=False)
        for r in range(rows):
            for c in range(cols):
                ex = x0 + c * px
                ey = y0 + r * py
                dxf.circle(ex, ey, ed / 2, layer="ELECTRODES")
                dxf.polyline([(ex, ey - ed / 2), (ex, bus_y + bus_h)], layer="TRACE", closed=False)
        dxf.text(f"Array: {rows}x{cols}, d={ed}mm, pitch={px}x{py}mm",
                 0.5, p.height_mm - 1.5, layer="SUBSTRATE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_el = svg.add_layer("ELECTRODES", color="#CC0000")
        l_bus = svg.add_layer("BUS", color="#0000CC")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        l_trace = svg.add_layer("TRACE", color="#888888")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.rectangle(bus_x, bus_y, bus_w, bus_h, l_bus)
        svg.rectangle(pad_x, pad_y, ps, ps, l_pad)
        svg.polyline([(pad_x + ps, pad_y + ps / 2), (bus_x, bus_y + bus_h / 2)],
                     l_trace, closed=False)
        for r in range(rows):
            for c in range(cols):
                ex = x0 + c * px
                ey = y0 + r * py
                svg.circle(ex, ey, ed / 2, l_el)
                svg.polyline([(ex, ey - ed / 2), (ex, bus_y + bus_h)], l_trace, closed=False)

    if gcode:
        gcode.comment(f"Array: {rows}x{cols}, d={ed}mm, pitch={px}x{py}mm")
        gcode.rectangle(bus_x, bus_y, bus_w, bus_h)
        gcode.rectangle(pad_x, pad_y, ps, ps)
        gcode.line(pad_x + ps, pad_y + ps / 2, bus_x, bus_y + bus_h / 2)
        for r in range(rows):
            for c in range(cols):
                ex = x0 + c * px
                ey = y0 + r * py
                gcode.circle(ex, ey, ed / 2)
                gcode.line(ex, ey - ed / 2, ex, bus_y + bus_h)

    print(f"  Array generated: {rows}x{cols}, d={ed}mm, pitch={px}x{py}mm")


def generate_meander(p, dxf, svg, gcode=None):
    """
    Generate spring-like serpentine with sinusoidal meander on each segment.

    Each horizontal segment has sine-wave oscillation superimposed,
    creating a spring/coil shape that stretches more than plain serpentine.

    Layout:
    ┌────────────────────────────────────┐
    │  ╭─╮╭─╮╭─╮╭─╮  segment 1         │
    │  ╰─╯╰─╯╰─╯╰─╯                    │
    │  ╭─╮╭─╮╭─╮╭─╮  segment 2         │
    │  ╰─╯╰─╯╰─╯╰─╯                    │
    │ [PAD]                              │
    └────────────────────────────────────┘
    """
    tw = p.trace_w_mm
    n = p.segments
    sl = p.seg_l_mm
    sh = p.seg_h_mm
    meander_n = p.meander_n
    amp = p.meander_amp_mm
    ps = p.pad_size_mm
    margin = p.margin_mm

    total_h = n * sh
    x0 = (p.width_mm - sl) / 2
    y0 = (p.height_mm - total_h) / 2

    # Build path: for each segment, generate sine-wave points
    path = []
    seg_pts = max(meander_n * 4, 20)  # points per segment

    for seg_i in range(n):
        seg_y_base = y0 + seg_i * sh
        is_even = seg_i % 2 == 0
        x_start = x0 if is_even else x0 + sl
        x_end = x0 + sl if is_even else x0
        dx = x_end - x_start

        for j in range(seg_pts):
            t = j / (seg_pts - 1)
            # Linear x progression along segment
            px = x_start + dx * t
            # Sine wave perpendicular to segment direction
            sine_val = math.sin(2 * math.pi * meander_n * t)
            py = seg_y_base + sh / 2 + sine_val * amp
            path.append((px, py))

    pad_x = x0 - ps - 1
    pad_y = y0 + sh / 2 - ps / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("TRACE", color=1)
        dxf.add_layer("PAD", color=3)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.rectangle(pad_x, pad_y, ps, ps, layer="PAD")
        dxf.polyline([(pad_x + ps, pad_y + ps / 2), path[0]], layer="TRACE", closed=False)
        dxf.polyline(path, layer="TRACE", closed=False)
        dxf.text(f"Meander: {n} segs, {meander_n} waves/seg, amp={amp}mm",
                 margin, p.height_mm - margin / 2, layer="SUBSTRATE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_trace = svg.add_layer("TRACE", color="#CC0000")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.rectangle(pad_x, pad_y, ps, ps, l_pad)
        svg.polyline([(pad_x + ps, pad_y + ps / 2), path[0]], l_trace, closed=False)
        # Thicken via offset polygon
        half_t = tw / 2
        filled = []
        for i, (px, py) in enumerate(path):
            if i < len(path) - 1:
                ddx = path[i + 1][0] - px
                ddy = path[i + 1][1] - py
            else:
                ddx = px - path[i - 1][0]
                ddy = py - path[i - 1][1]
            length = math.sqrt(ddx * ddx + ddy * ddy)
            if length == 0:
                nx, ny = 0, 1
            else:
                nx, ny = -ddy / length, ddx / length
            filled.append((px + nx * half_t, py + ny * half_t))
        for i in range(len(path) - 1, -1, -1):
            px, py = path[i]
            if i < len(path) - 1:
                ddx = path[i + 1][0] - px
                ddy = path[i + 1][1] - py
            else:
                ddx = px - path[i - 1][0]
                ddy = py - path[i - 1][1]
            length = math.sqrt(ddx * ddx + ddy * ddy)
            if length == 0:
                nx, ny = 0, 1
            else:
                nx, ny = -ddy / length, ddx / length
            filled.append((px - nx * half_t, py - ny * half_t))
        filled.append(filled[0])
        svg.polyline(filled, l_trace, closed=True)

    if gcode:
        gcode.comment(f"Meander: {n} segs, {meander_n} waves/seg, amp={amp}mm")
        gcode.rectangle(pad_x, pad_y, ps, ps)
        gcode.line(pad_x + ps, pad_y + ps / 2, path[0][0], path[0][1])
        gcode.polyline(path, closed=False)

    print(f"  Meander generated: {n} segments, {meander_n} waves/seg, amp={amp}mm")


def generate_circular_array(p, dxf, svg, gcode=None):
    """
    Generate circular/radial electrode array.

    Electrodes arranged in concentric rings around a central electrode.
    Each electrode connects radially inward to a common centre pad.

    Layout:
    ┌────────────────────────────────────┐
    │         ●   ●   ●                │
    │       ●           ●              │
    │      ●     ●●●     ●             │
    │       ●           ●              │
    │         ●   ●   ●                │
    │         [CENTRE PAD]             │
    └────────────────────────────────────┘
    """
    rings = p.rings
    epr = p.electrodes_per_ring
    ed = p.electrode_d_mm
    rs = p.ring_spacing_mm
    ps = p.pad_size_mm
    tw = p.trace_w_mm

    cx = p.width_mm / 2
    cy = p.height_mm / 2
    pad_y = cy + rs * rings + ed + 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("ELECTRODES", color=1)
        dxf.add_layer("CENTRE", color=5)
        dxf.add_layer("TRACE", color=6)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.circle(cx, cy, ed / 2, layer="CENTRE")
        dxf.rectangle(cx - ps / 2, pad_y, ps, ps, layer="CENTRE")
        dxf.polyline([(cx, cy + ed / 2), (cx, pad_y)], layer="TRACE", closed=False)
        # Rings
        for ring_i in range(1, rings + 1):
            r = rs * ring_i
            n_electrodes = max(6, int(epr * ring_i / rings))
            for j in range(n_electrodes):
                angle = 2 * math.pi * j / n_electrodes
                ex = cx + r * math.cos(angle)
                ey = cy + r * math.sin(angle)
                dxf.circle(ex, ey, ed / 2, layer="ELECTRODES")
                # Radial trace to centre
                dxf.polyline([(ex, ey), (cx, cy)], layer="TRACE", closed=False)
        dxf.text(f"Circular array: {rings} rings, {epr} max epr",
                 0.5, p.height_mm - 1.5, layer="SUBSTRATE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_el = svg.add_layer("ELECTRODES", color="#CC0000")
        l_centre = svg.add_layer("CENTRE", color="#0000CC")
        l_trace = svg.add_layer("TRACE", color="#888888")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.circle(cx, cy, ed / 2, l_centre)
        svg.rectangle(cx - ps / 2, pad_y, ps, ps, l_centre)
        svg.polyline([(cx, cy + ed / 2), (cx, pad_y)], l_trace, closed=False)
        for ring_i in range(1, rings + 1):
            r = rs * ring_i
            n_electrodes = max(6, int(epr * ring_i / rings))
            for j in range(n_electrodes):
                angle = 2 * math.pi * j / n_electrodes
                ex = cx + r * math.cos(angle)
                ey = cy + r * math.sin(angle)
                svg.circle(ex, ey, ed / 2, l_el)
                svg.polyline([(ex, ey), (cx, cy)], l_trace, closed=False)

    if gcode:
        gcode.comment(f"Circular array: {rings} rings, {epr} max epr")
        gcode.circle(cx, cy, ed / 2)
        gcode.rectangle(cx - ps / 2, pad_y, ps, ps)
        gcode.line(cx, cy + ed / 2, cx, pad_y)
        for ring_i in range(1, rings + 1):
            r = rs * ring_i
            n_electrodes = max(6, int(epr * ring_i / rings))
            for j in range(n_electrodes):
                angle = 2 * math.pi * j / n_electrodes
                ex = cx + r * math.cos(angle)
                ey = cy + r * math.sin(angle)
                gcode.circle(ex, ey, ed / 2)
                gcode.line(ex, ey, cx, cy)

    print(f"  Circular array generated: {rings} rings, {epr} max electrodes per ring")


def generate_spiral(p, dxf, svg, gcode=None):
    """
    Generate Archimedean spiral electrode.

    r = r_start + (r_end - r_start) * theta / (2*pi*turns)

    Layout:
    ┌────────────────────────────────────┐
    │        ╭───╮                      │
    │       ╭╯   ╰╮                     │
    │      ╭╯  ●  ╰╮                    │
    │      │       │                    │
    │       ╰╮   ╭╯                     │
    │        ╰───╯                      │
    │ [PAD]                              │
    └────────────────────────────────────┘
    """
    turns = p.turns
    r_start = p.r_start_mm
    r_end = p.r_end_mm
    tw = p.trace_w_mm
    n_pts = p.n_points
    ps = p.pad_size_mm

    cx = p.width_mm / 2
    cy = p.height_mm / 2
    total_theta = 2 * math.pi * turns

    # Generate spiral points
    path = []
    for i in range(n_pts + 1):
        theta = total_theta * i / n_pts
        r = r_start + (r_end - r_start) * theta / total_theta if total_theta > 0 else r_start
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        path.append((x, y))

    # Pad at the end of the spiral (outer tip)
    pad_x = path[-1][0] + 1
    pad_y = path[-1][1] - ps / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("SPIRAL", color=1)
        dxf.add_layer("PAD", color=3)
        dxf.add_layer("TRACE", color=6)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.polyline(path, layer="SPIRAL", closed=False)
        # Pad and trace
        dxf.rectangle(pad_x, pad_y, ps, ps, layer="PAD")
        dxf.polyline([path[-1], (pad_x, pad_y + ps / 2)], layer="TRACE", closed=False)
        # Centre dot
        dxf.circle(cx, cy, 0.3, layer="SPIRAL")
        dxf.text(f"Spiral: {turns} turns, r={r_start}-{r_end}mm",
                 0.5, p.height_mm - 1.5, layer="SUBSTRATE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_spiral = svg.add_layer("SPIRAL", color="#CC0000")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        l_trace = svg.add_layer("TRACE", color="#888888")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        # Thicken the spiral
        half_t = tw / 2
        filled = []
        for i, (px, py) in enumerate(path):
            if i < len(path) - 1:
                ddx = path[i + 1][0] - px
                ddy = path[i + 1][1] - py
            else:
                ddx = px - path[i - 2][0]
                ddy = py - path[i - 2][1]
            length = math.sqrt(ddx * ddx + ddy * ddy)
            if length == 0:
                nx, ny = 0, 1
            else:
                nx, ny = -ddy / length, ddx / length
            filled.append((px + nx * half_t, py + ny * half_t))
        for i in range(len(path) - 1, -1, -1):
            px, py = path[i]
            if i < len(path) - 1:
                ddx = path[i + 1][0] - px
                ddy = path[i + 1][1] - py
            else:
                ddx = px - path[i - 2][0]
                ddy = py - path[i - 2][1]
            length = math.sqrt(ddx * ddx + ddy * ddy)
            if length == 0:
                nx, ny = 0, 1
            else:
                nx, ny = -ddy / length, ddx / length
            filled.append((px - nx * half_t, py - ny * half_t))
        filled.append(filled[0])
        svg.polyline(filled, l_spiral, closed=True)
        svg.circle(cx, cy, 0.3, l_spiral)
        svg.rectangle(pad_x, pad_y, ps, ps, l_pad)
        svg.polyline([path[-1], (pad_x, pad_y + ps / 2)], l_trace, closed=False)

    if gcode:
        gcode.comment(f"Spiral: {turns} turns, r={r_start}-{r_end}mm")
        gcode.polyline(path, closed=False)
        gcode.circle(cx, cy, 0.3)
        gcode.rectangle(pad_x, pad_y, ps, ps)
        gcode.line(path[-1][0], path[-1][1], pad_x, pad_y + ps / 2)

    print(f"  Spiral generated: {turns} turns, r={r_start}-{r_end}mm")


def generate_polygon(p, dxf, svg, gcode=None):
    """
    Generate custom polygon electrode from user-specified vertices.

    Vertices are specified as comma-separated x,y pairs.
    The polygon is centred on the substrate and connected to a contact pad.

    Example: --vertices '0,0;5,0;2.5,4.33'  (equilateral triangle)
    """
    tw = p.trace_w_mm
    ps = p.pad_size_mm

    # Parse vertices string: 'x1,y1;x2,y2;...'
    raw_verts = p.vertices.strip().split(';')
    verts = []
    for v in raw_verts:
        parts = v.strip().split(',')
        verts.append((float(parts[0]), float(parts[1])))

    if len(verts) < 3:
        print("  ERROR: polygon needs at least 3 vertices")
        return

    # Compute bounding box and centre
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    v_cx = (min_x + max_x) / 2
    v_cy = (min_y + max_y) / 2
    v_w = max_x - min_x
    v_h = max_y - min_y

    # Centre polygon on substrate with margin
    margin = max(ps + 2, 3.0)
    scale_x = (p.width_mm - 2 * margin) / v_w if v_w > 0 else 1.0
    scale_y = (p.height_mm - 2 * margin) / v_h if v_h > 0 else 1.0
    scale = min(scale_x, scale_y)

    cx = p.width_mm / 2
    cy = p.height_mm / 2

    # Transform vertices: scale and centre
    tverts = []
    for vx, vy in verts:
        tx = cx + (vx - v_cx) * scale
        ty = cy + (vy - v_cy) * scale
        tverts.append((tx, ty))
    # Close the polygon
    tverts.append(tverts[0])

    # Pad position: to the left of the polygon
    pad_x = cx - v_w * scale / 2 - ps - 2
    pad_y = cy - ps / 2

    if dxf:
        dxf.add_layer("SUBSTRATE", color=8)
        dxf.add_layer("POLYGON", color=1)
        dxf.add_layer("PAD", color=3)
        dxf.add_layer("TRACE", color=6)
        dxf.polyline(rect_points(0, 0, p.width_mm, p.height_mm), layer="SUBSTRATE", closed=True)
        dxf.polyline(tverts, layer="POLYGON", closed=True)
        dxf.rectangle(pad_x, pad_y, ps, ps, layer="PAD")
        dxf.polyline([(pad_x + ps, pad_y + ps / 2), tverts[0]], layer="TRACE", closed=False)
        dxf.text(f"Polygon: {len(verts)} vertices",
                 0.5, p.height_mm - 1.5, layer="SUBSTRATE")

    if svg:
        l_sub = svg.add_layer("SUBSTRATE", color="#CCCCCC")
        l_poly = svg.add_layer("POLYGON", color="#CC0000")
        l_pad = svg.add_layer("PAD", color="#00AA00")
        l_trace = svg.add_layer("TRACE", color="#888888")
        svg.rectangle(0, 0, p.width_mm, p.height_mm, l_sub)
        svg.polyline(tverts, l_poly, closed=True)
        svg.rectangle(pad_x, pad_y, ps, ps, l_pad)
        svg.polyline([(pad_x + ps, pad_y + ps / 2), tverts[0]], l_trace, closed=False)

    if gcode:
        gcode.comment(f"Polygon: {len(verts)} vertices, scaled to {v_w*scale:.1f}x{v_h*scale:.1f}mm")
        gcode.polyline(tverts, closed=True)
        gcode.rectangle(pad_x, pad_y, ps, ps)
        gcode.line(pad_x + ps, pad_y + ps / 2, tverts[0][0], tverts[0][1])

    print(f"  Polygon generated: {len(verts)} vertices, scaled to {v_w*scale:.1f}x{v_h*scale:.1f}mm")


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        description="Parametric Electrode Generator — DXF/SVG output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interdigitated electrode
  python electrode_generator.py --type ide --fingers 10 --finger-w 0.5 --gap 0.3 --finger-l 15

  # Three-electrode system
  python electrode_generator.py --type three --we-d 3 --ce-d 4 --re-d 2

  # Serpentine trace
  python electrode_generator.py --type serpentine --segments 8 --seg-l 3 --seg-h 2

  # Ring-disk electrode
  python electrode_generator.py --type ringdisk --disk-d 3 --gap 0.2 --ring-w 0.5

  # Electrode array
  python electrode_generator.py --type array --rows 4 --cols 4 --electrode-d 2 --pitch-x 5
"""
    )
    p.add_argument("--type", required=True,
                   choices=["ide", "three", "serpentine", "ringdisk", "array",
                            "meander", "carray", "spiral", "polygon"],
                   help="Electrode type")
    p.add_argument("--width", type=float, default=25.0, help="Substrate width (mm)")
    p.add_argument("--height", type=float, default=25.0, help="Substrate height (mm)")
    p.add_argument("--format", dest="fmt", default="both",
                   choices=["dxf", "svg", "gcode", "both", "all"],
                   help="Output format (default: both)")
    p.add_argument("--feed-rate", type=int, default=1000,
                   help="G-code feed rate mm/min (default: 1000)")
    p.add_argument("--laser-power", type=int, default=1000,
                   help="G-code laser power 0-1000 (default: 1000)")
    p.add_argument("--flip-y", action="store_true",
                   help="Flip Y axis in G-code output")
    p.add_argument("--output", default="electrode", help="Output filename (no extension)")
    p.add_argument("--dxf-version", default="R2010", help="DXF version (default: R2010)")
    p.add_argument("--layers", nargs="*", default=None,
                   help="Export per-layer files. Optionally specify layers: --layers ELECTRODE_A PAD")
    p.add_argument("--list-layers", action="store_true",
                   help="List available layers for the electrode type and exit")
    p.add_argument("--validate", action="store_true",
                   help="Validate design against fabrication constraints and print warnings")
    p.add_argument("--info", action="store_true",
                   help="Print design guidelines for the electrode type and exit")
    p.add_argument("--fab", default="screen_print",
                   choices=["screen_print", "cricut_vinyl", "laser_co2", "laser_lig", "cnc_mill"],
                   help="Fabrication method for validation (default: screen_print)")

    # IDE
    ide = p.add_argument_group("Interdigitated (IDE) parameters")
    ide.add_argument("--fingers", type=int, default=10)
    ide.add_argument("--finger-w", type=float, default=1.0)
    ide.add_argument("--gap", type=float, default=1.0)
    ide.add_argument("--finger-l", type=float, default=10.0)
    ide.add_argument("--pad-size", type=float, default=3.0)
    ide.add_argument("--bus-w", type=float, default=2.0)
    ide.add_argument("--margin", type=float, default=3.0)

    # Three
    three = p.add_argument_group("Three-electrode parameters")
    three.add_argument("--we-d", type=float, default=3.0)
    three.add_argument("--ce-d", type=float, default=4.0)
    three.add_argument("--re-d", type=float, default=2.0)
    three.add_argument("--spacing", type=float, default=5.0)

    # Serpentine
    serp = p.add_argument_group("Serpentine parameters")
    serp.add_argument("--trace-w", type=float, default=0.5)
    serp.add_argument("--segments", type=int, default=10)
    serp.add_argument("--seg-l", type=float, default=2.0)
    serp.add_argument("--seg-h", type=float, default=1.5)

    # Ring-disk
    rd = p.add_argument_group("Ring-disk parameters")
    rd.add_argument("--disk-d", type=float, default=3.0)
    rd.add_argument("--ring-w", type=float, default=0.5)

    # Array
    arr = p.add_argument_group("Array parameters")
    arr.add_argument("--rows", type=int, default=4)
    arr.add_argument("--cols", type=int, default=4)
    arr.add_argument("--electrode-d", type=float, default=2.0)
    arr.add_argument("--pitch-x", type=float, default=5.0)
    arr.add_argument("--pitch-y", type=float, default=5.0)

    # Meander
    mea = p.add_argument_group("Meander (spring serpentine) parameters")
    mea.add_argument("--meander-n", type=int, default=8,
                     help="Number of sine half-cycles per segment")
    mea.add_argument("--meander-amp", type=float, default=0.8,
                     help="Meander wave amplitude (mm)")

    # Circular array
    ca = p.add_argument_group("Circular array parameters")
    ca.add_argument("--rings", type=int, default=3,
                    help="Number of concentric rings")
    ca.add_argument("--epr", type=int, default=8,
                    help="Electrodes per ring (outermost)")
    ca.add_argument("--ring-spacing", type=float, default=4.0,
                    help="Ring spacing (mm)")

    # Spiral
    sp = p.add_argument_group("Spiral parameters")
    sp.add_argument("--turns", type=int, default=5,
                    help="Number of full turns")
    sp.add_argument("--r-start", type=float, default=0.5,
                    help="Starting radius (mm)")
    sp.add_argument("--r-end", type=float, default=10.0,
                    help="Ending radius (mm)")
    sp.add_argument("--spiral-pts", type=int, default=200,
                    help="Points resolution")

    # Polygon
    poly = p.add_argument_group("Polygon parameters")
    poly.add_argument("--vertices", type=str,
                      default="0,0;5,0;2.5,4.33",
                      help="Semicolon-separated x,y pairs: 'x1,y1;x2,y2;...'")
    poly.add_argument("--pad-x", type=float, default=-1.0,
                      help="Pad X position (-1 = auto)")
    poly.add_argument("--pad-y", type=float, default=-1.0,
                      help="Pad Y position (-1 = auto)")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    out_dir = os.path.dirname(args.output) or "."
    os.makedirs(out_dir, exist_ok=True)

    # Handle --list-layers early (no generator needed)
    if args.list_layers:
        layers = LAYER_NAMES.get(args.type, [])
        print(f"\nAvailable layers for '{args.type}':")
        for i, name in enumerate(layers, 1):
            print(f"  {i}. {name}")
        print(f"\nUse: --layers {layers[1] if len(layers) > 1 else layers[0]}")
        return

    # When --layers is used, skip creating writers here; the layer block handles it
    use_layer_export = args.layers is not None
    dxf = None if use_layer_export else (DXFWriter(version=args.dxf_version) if args.fmt in ("dxf", "both", "all") else None)
    svg = None if use_layer_export else (SVGWriter(args.width, args.height) if args.fmt in ("svg", "both", "all") else None)
    gcode = None if use_layer_export else (GCodeWriter(feed_rate=args.feed_rate, laser_power=args.laser_power,
                        flip_y=args.flip_y) if args.fmt in ("gcode", "all") else None)
    if gcode:
        gcode.header(args.width, args.height)

    print(f"\n{'='*60}")
    print(f"  Electrode Generator")
    print(f"  Type: {args.type}")
    print(f"  Substrate: {args.width} x {args.height} mm")
    print(f"  Format: {args.fmt.upper()}")
    print(f"{'='*60}\n")

    # Build params for the electrode type
    if args.type == "ide":
        p = IDEParams(width_mm=args.width, height_mm=args.height, fingers=args.fingers,
                      finger_w_mm=args.finger_w, gap_mm=args.gap, finger_l_mm=args.finger_l,
                      pad_size_mm=args.pad_size, bus_w_mm=args.bus_w, margin_mm=args.margin)
    elif args.type == "three":
        p = ThreeElectrodeParams(width_mm=args.width, height_mm=args.height,
                                 we_d_mm=args.we_d, ce_d_mm=args.ce_d, re_d_mm=args.re_d,
                                 spacing_mm=args.spacing, pad_size_mm=args.pad_size)
    elif args.type == "serpentine":
        p = SerpentineParams(width_mm=args.width, height_mm=args.height,
                             trace_w_mm=args.trace_w, segments=args.segments,
                             seg_l_mm=args.seg_l, seg_h_mm=args.seg_h,
                             pad_size_mm=args.pad_size)
    elif args.type == "ringdisk":
        p = RingDiskParams(width_mm=args.width, height_mm=args.height,
                           disk_d_mm=args.disk_d, gap_mm=args.gap,
                           ring_w_mm=args.ring_w, pad_size_mm=args.pad_size)
    elif args.type == "array":
        p = ArrayParams(width_mm=args.width, height_mm=args.height,
                        rows=args.rows, cols=args.cols,
                        electrode_d_mm=args.electrode_d,
                        pitch_x_mm=args.pitch_x, pitch_y_mm=args.pitch_y,
                        pad_size_mm=args.pad_size)
    elif args.type == "meander":
        p = MeanderParams(width_mm=args.width, height_mm=args.height,
                          trace_w_mm=args.trace_w, segments=args.segments,
                          seg_l_mm=args.seg_l, seg_h_mm=args.seg_h,
                          meander_n=args.meander_n, meander_amp_mm=args.meander_amp,
                          pad_size_mm=args.pad_size)
    elif args.type == "carray":
        p = CircularArrayParams(width_mm=args.width, height_mm=args.height,
                                rings=args.rings, electrodes_per_ring=args.epr,
                                electrode_d_mm=args.electrode_d,
                                ring_spacing_mm=args.ring_spacing,
                                pad_size_mm=args.pad_size)
    elif args.type == "spiral":
        p = SpiralParams(width_mm=args.width, height_mm=args.height,
                         turns=args.turns, r_start_mm=args.r_start,
                         r_end_mm=args.r_end, trace_w_mm=args.trace_w,
                         n_points=args.spiral_pts, pad_size_mm=args.pad_size)
    elif args.type == "polygon":
        p = PolygonParams(width_mm=args.width, height_mm=args.height,
                          vertices=args.vertices, trace_w_mm=args.trace_w,
                          pad_size_mm=args.pad_size,
                          pad_x_mm=args.pad_x, pad_y_mm=args.pad_y)

    # Handle --info: print design guidelines and exit
    if args.info:
        print_design_info(args.type, p)
        return

    # Handle --validate: check design and print warnings
    if args.validate:
        warnings = validate_design(p, args.fab)
        if warnings:
            print(f"\n⚠️  Design warnings ({args.fab}):")
            for w in warnings:
                print(f"  ⚠  {w}")
        else:
            print(f"\n✅ Design OK for {args.fab} — no warnings")
        print_design_info(args.type, p)
        return

    # Multi-layer export: run with LayerCollector, export per-layer files
    if args.layers is not None:
        collector = LayerCollector(args.width, args.height)
        gen_func = {
            "ide": generate_ide, "three": generate_three,
            "serpentine": generate_serpentine, "ringdisk": generate_ringdisk,
            "array": generate_array, "meander": generate_meander,
            "carray": generate_circular_array, "spiral": generate_spiral,
            "polygon": generate_polygon,
        }[args.type]
        gen_func(p, collector, None, None)
        export_layers(collector, args.output, args.fmt,
                      layers_filter=args.layers if args.layers else None,
                      feed_rate=args.feed_rate, laser_power=args.laser_power,
                      flip_y=args.flip_y)
        print(f"\n{'='*60}")
        print(f"  Multi-layer export complete!")
        print(f"{'='*60}\n")
        return

    # Normal export: run with DXF/SVG/GCode writers
    gen_func = {
        "ide": generate_ide, "three": generate_three,
        "serpentine": generate_serpentine, "ringdisk": generate_ringdisk,
        "array": generate_array, "meander": generate_meander,
        "carray": generate_circular_array, "spiral": generate_spiral,
        "polygon": generate_polygon,
    }[args.type]
    gen_func(p, dxf, svg, gcode)

    if gcode:
        gcode.footer()

    print()
    if dxf:
        dxf.save(f"{args.output}.dxf")
    if svg:
        svg.save(f"{args.output}.svg")
    if gcode:
        gcode.save(f"{args.output}.gcode")

    print(f"\n{'='*60}")
    print(f"  Done! Files saved to: {args.output}.*")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
