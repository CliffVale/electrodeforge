#!/usr/bin/env python3
"""
IDE Variants Generator — 5 interdigitated electrode designs
=============================================================
All share: 20mm × 10mm overlapping zone, same metallization ratio.
Gap varies (0.5–2.5mm); pitch scales proportionally to maintain ratio.

Design rules:
- Metallization ratio = 0.5 (constant) → finger_w = gap (since ratio = fw/(fw+gap) = 0.5)
- Pitch = finger_w + gap = 2 × gap
- Number of fingers adjusts to fill the 20mm width
- Finger length = 6mm (for 10mm overlap with 2mm bus bars)
- Bus bar height = 2mm
- Contact pads = 3mm × 3mm
- Substrate = 25mm × 20mm

Output: DXF files ready for 3-axis laser cutting (GRBL/LightBurn/K40).
"""

import os
import ezdxf
from ezdxf import units

# ── Design constants ──
METALLIZATION_RATIO = 0.5   # Constant across all variants
FINGER_L_MM = 6.0           # Finger length (vertical, into overlap)
BUS_H_MM = 2.0              # Bus bar height
PAD_SIZE_MM = 3.0           # Contact pad size
SUBSTRATE_W = 25.0          # Substrate width
SUBSTRATE_H = 20.0          # Substrate height
MARGIN = 2.5                # Edge margin
OVERLAP_W = 20.0            # Overlap zone width
OVERLAP_H = 10.0            # Overlap zone height

# 5 gap variants
GAPS = [0.5, 1.0, 1.5, 2.0, 2.5]  # mm

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "output", "ide_variants")


def create_ide_dxf(gap_mm, variant_name):
    """Create a single IDE variant DXF file."""
    # With fixed metallization ratio 0.5: finger_w = gap
    fw = gap_mm
    pitch = fw + gap_mm  # = 2 × gap
    metallization = fw / pitch

    # How many fingers fit in 20mm?
    n_fingers = int(OVERLAP_W / pitch)
    actual_width = n_fingers * pitch

    # Centre on substrate
    x0 = (SUBSTRATE_W - actual_width) / 2

    # Vertical layout
    bus_top_y = MARGIN + FINGER_L_MM + BUS_H_MM
    bus_bot_y = MARGIN

    doc = ezdxf.new(dxfversion="R2010")
    doc.units = units.MM
    msp = doc.modelspace()

    # Layers
    doc.layers.add("SUBSTRATE", color=8)
    doc.layers.add("ELECTRODE_A", color=1)
    doc.layers.add("ELECTRODE_B", color=5)
    doc.layers.add("PAD", color=3)
    doc.layers.add("BUS", color=6)
    doc.layers.add("DIMENSION", color=7)

    def add_rect(x, y, w, h, layer):
        msp.add_lwpolyline(
            [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)],
            dxfattribs={"layer": layer}, close=True
        )

    # Substrate
    add_rect(0, 0, SUBSTRATE_W, SUBSTRATE_H, "SUBSTRATE")

    # Bus bar A (top)
    bus_a_x = x0 - 1.0
    bus_a_w = actual_width + 2.0
    add_rect(bus_a_x, bus_top_y, bus_a_w, BUS_H_MM, "BUS")

    # Bus bar B (bottom)
    bus_b_x = x0 - 1.0
    bus_b_w = actual_width + 2.0
    add_rect(bus_b_x, bus_bot_y - BUS_H_MM, bus_b_w, BUS_H_MM, "BUS")

    # Fingers — alternating from top and bottom bus
    for i in range(n_fingers):
        fx = x0 + i * pitch
        if i % 2 == 0:
            # From bus A (top) — hangs down
            fy = bus_top_y - FINGER_L_MM
            add_rect(fx, fy, fw, FINGER_L_MM, "ELECTRODE_A")
        else:
            # From bus B (bottom) — rises up
            fy = bus_bot_y
            add_rect(fx, fy, fw, FINGER_L_MM, "ELECTRODE_B")

    # Contact pad A (left)
    pad_a_x = bus_a_x - PAD_SIZE_MM - 1.0
    pad_a_y = bus_top_y + (BUS_H_MM - PAD_SIZE_MM) / 2
    add_rect(pad_a_x, pad_a_y, PAD_SIZE_MM, PAD_SIZE_MM, "PAD")
    msp.add_line(
        (pad_a_x + PAD_SIZE_MM, pad_a_y + PAD_SIZE_MM / 2),
        (bus_a_x, bus_top_y + BUS_H_MM / 2),
        dxfattribs={"layer": "PAD"}
    )

    # Contact pad B (right)
    pad_b_x = bus_b_x + bus_b_w + 1.0
    pad_b_y = bus_bot_y - BUS_H_MM + (BUS_H_MM - PAD_SIZE_MM) / 2
    add_rect(pad_b_x, pad_b_y, PAD_SIZE_MM, PAD_SIZE_MM, "PAD")
    msp.add_line(
        (pad_b_x, pad_b_y + PAD_SIZE_MM / 2),
        (bus_b_x + bus_b_w, bus_bot_y - BUS_H_MM / 2),
        dxfattribs={"layer": "PAD"}
    )

    # Dimension annotation
    msp.add_text(
        f"Gap={gap_mm}mm  FW={fw}mm  Pitch={pitch}mm  "
        f"Met={metallization:.2f}  N={n_fingers}  L={FINGER_L_MM}mm",
        dxfattribs={"layer": "DIMENSION", "height": 0.6,
                     "insert": (0.5, SUBSTRATE_H - 1.0)}
    )
    msp.add_text(
        f"Overlap: {OVERLAP_W}x{OVERLAP_H}mm | Substrate: {SUBSTRATE_W}x{SUBSTRATE_H}mm | "
        f"Bus: {BUS_H_MM}mm | Pad: {PAD_SIZE_MM}mm | Ratio: {METALLIZATION_RATIO}",
        dxfattribs={"layer": "DIMENSION", "height": 0.5,
                     "insert": (0.5, SUBSTRATE_H - 1.8)}
    )

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{variant_name}.dxf")
    doc.saveas(path)
    return path, {
        "gap": gap_mm, "finger_w": fw, "pitch": pitch,
        "metallization": metallization, "n_fingers": n_fingers,
        "finger_l": FINGER_L_MM, "bus_h": BUS_H_MM,
        "substrate": f"{SUBSTRATE_W}x{SUBSTRATE_H}",
    }


def main():
    print("=" * 70)
    print("  IDE Variants Generator — 5 Designs for 3-Axis Laser Cutting")
    print("=" * 70)
    print(f"\n  Fixed parameters:")
    print(f"    Metallization ratio: {METALLIZATION_RATIO}")
    print(f"    Finger length:       {FINGER_L_MM} mm")
    print(f"    Bus bar height:      {BUS_H_MM} mm")
    print(f"    Contact pad:         {PAD_SIZE_MM}x{PAD_SIZE_MM} mm")
    print(f"    Substrate:           {SUBSTRATE_W}x{SUBSTRATE_H} mm")
    print(f"    Overlap zone:        {OVERLAP_W}x{OVERLAP_H} mm")
    print()

    results = []
    for gap in GAPS:
        name = f"IDE_gap{gap:.1f}mm"
        path, info = create_ide_dxf(gap, name)
        results.append((name, path, info))
        print(f"  ✅ {name}.dxf")
        print(f"     Gap={gap}mm | FW={info['finger_w']}mm | Pitch={info['pitch']}mm | "
              f"Metallization={info['metallization']:.2f} | Fingers={info['n_fingers']}")

    print(f"\n{'=' * 70}")
    print(f"  Summary Table")
    print(f"{'=' * 70}")
    print(f"  {'Variant':<22} {'Gap':>5} {'FW':>5} {'Pitch':>6} {'Met':>5} {'#Fingers':>9} {'FingerL':>8}")
    print(f"  {'-'*65}")
    for name, path, info in results:
        print(f"  {name:<20} {info['gap']:>5.1f} {info['finger_w']:>5.1f} "
              f"{info['pitch']:>6.1f} {info['metallization']:>5.2f} "
              f"{info['n_fingers']:>9} {info['finger_l']:>8.1f}")

    print(f"\n  📁 Files saved to: {OUTPUT_DIR}/")
    print(f"  🔧 Import into LightBurn, LaserGRBL, or K40 Whisperer")
    print(f"  📐 All dimensions in mm, R2010 DXF format")
    print(f"\n  Design notes:")
    print(f"    • Metallization ratio = finger_w / pitch = {METALLIZATION_RATIO} (constant)")
    print(f"    • Pitch = 2 × gap (scales with gap to maintain ratio)")
    print(f"    • Finger count adjusts to fill {OVERLAP_W}mm width")
    print(f"    • Bus bars: {BUS_H_MM}mm tall, adequate for low-resistance connections")
    print(f"    • Contact pads: {PAD_SIZE_MM}mm for wire bonding / crocodile clips")


if __name__ == "__main__":
    main()
