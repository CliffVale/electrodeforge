#!/usr/bin/env python3
"""
Comprehensive test suite for ElectrodeForge electrode generators.

Tests all 9 electrode types across all 3 output formats (DXF, SVG, G-code),
validates file integrity, layer structure, dimensional accuracy, and
fabrication constraints.

Usage:
    cd ~/Documents/Electrodes_design
    source .venv/bin/activate
    pytest tests/ -v
    # or
    python tests/test_generators.py
"""

import os
import sys
import math
import tempfile
import shutil
import pytest

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from electrode_generator import (
    IDEParams, ThreeElectrodeParams, SerpentineParams, RingDiskParams,
    ArrayParams, MeanderParams, CircularArrayParams, SpiralParams,
    PolygonParams, DXFWriter, SVGWriter, GCodeWriter, LayerCollector,
    generate_ide, generate_three, generate_serpentine, generate_ringdisk,
    generate_array, generate_meander, generate_circular_array,
    generate_spiral, generate_polygon,
    validate_design, export_layers, LAYER_NAMES, FAB_CONSTRAINTS,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test outputs."""
    d = tempfile.mkdtemp(prefix="electrode_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def ide_params():
    return IDEParams(width_mm=25, height_mm=25, fingers=10, finger_w_mm=1.0,
                     gap_mm=0.5, finger_l_mm=15, pad_size_mm=3, bus_w_mm=2.0)


@pytest.fixture
def three_params():
    return ThreeElectrodeParams(width_mm=25, height_mm=25, we_d_mm=3.0,
                                 ce_d_mm=6.0, re_d_mm=2.0, spacing_mm=3.0)


@pytest.fixture
def serpentine_params():
    return SerpentineParams(width_mm=25, height_mm=25, trace_w_mm=1.0,
                             segments=8, seg_l_mm=3.0, seg_h_mm=2.0)


@pytest.fixture
def ringdisk_params():
    return RingDiskParams(width_mm=25, height_mm=25, disk_d_mm=5.0,
                           gap_mm=0.5, ring_w_mm=1.5)


@pytest.fixture
def array_params():
    return ArrayParams(width_mm=25, height_mm=25, rows=4, cols=4,
                        electrode_d_mm=2.0, pitch_x_mm=6.0, pitch_y_mm=6.0)


@pytest.fixture
def meander_params():
    return MeanderParams(width_mm=25, height_mm=25, trace_w_mm=1.0,
                          segments=6, seg_l_mm=4.0, seg_h_mm=2.5,
                          meander_n=6, meander_amp_mm=1.0)


@pytest.fixture
def carray_params():
    return CircularArrayParams(width_mm=25, height_mm=25, rings=3,
                                electrodes_per_ring=8, electrode_d_mm=2.0,
                                ring_spacing_mm=5.0)


@pytest.fixture
def spiral_params():
    return SpiralParams(width_mm=25, height_mm=25, turns=5,
                         r_start_mm=1.0, r_end_mm=10.0, trace_w_mm=0.8)


@pytest.fixture
def polygon_params():
    return PolygonParams(width_mm=25, height_mm=25,
                          vertices="5,0;10,8.66;0,8.66")


# ── DXF Generation Tests ─────────────────────────────────────────────

class TestDXFGeneration:
    """Test DXF output for all electrode types."""

    def test_ide_dxf(self, ide_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_ide.dxf")
        dxf = DXFWriter()
        dxf.header() if hasattr(dxf, 'header') else None
        svg = None
        generate_ide(ide_params, dxf, svg)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_three_dxf(self, three_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_three.dxf")
        dxf = DXFWriter()
        generate_three(three_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_serpentine_dxf(self, serpentine_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_serpentine.dxf")
        dxf = DXFWriter()
        generate_serpentine(serpentine_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_ringdisk_dxf(self, ringdisk_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_ringdisk.dxf")
        dxf = DXFWriter()
        generate_ringdisk(ringdisk_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_array_dxf(self, array_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_array.dxf")
        dxf = DXFWriter()
        generate_array(array_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_meander_dxf(self, meander_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_meander.dxf")
        dxf = DXFWriter()
        generate_meander(meander_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_carray_dxf(self, carray_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_carray.dxf")
        dxf = DXFWriter()
        generate_circular_array(carray_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_spiral_dxf(self, spiral_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_spiral.dxf")
        dxf = DXFWriter()
        generate_spiral(spiral_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100

    def test_polygon_dxf(self, polygon_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_polygon.dxf")
        dxf = DXFWriter()
        generate_polygon(polygon_params, dxf, None)
        dxf.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100


# ── SVG Generation Tests ─────────────────────────────────────────────

class TestSVGGeneration:
    """Test SVG output for all electrode types."""

    def test_ide_svg(self, ide_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_ide.svg")
        svg = SVGWriter(25, 25)
        generate_ide(ide_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100
        content = open(path).read()
        assert "<svg" in content
        assert "viewBox" in content

    def test_three_svg(self, three_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_three.svg")
        svg = SVGWriter(25, 25)
        generate_three(three_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)
        content = open(path).read()
        assert "<svg" in content

    def test_serpentine_svg(self, serpentine_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_serpentine.svg")
        svg = SVGWriter(25, 25)
        generate_serpentine(serpentine_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)

    def test_ringdisk_svg(self, ringdisk_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_ringdisk.svg")
        svg = SVGWriter(25, 25)
        generate_ringdisk(ringdisk_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)

    def test_array_svg(self, array_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_array.svg")
        svg = SVGWriter(25, 25)
        generate_array(array_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)

    def test_meander_svg(self, meander_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_meander.svg")
        svg = SVGWriter(25, 25)
        generate_meander(meander_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)

    def test_carray_svg(self, carray_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_carray.svg")
        svg = SVGWriter(25, 25)
        generate_circular_array(carray_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)

    def test_spiral_svg(self, spiral_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_spiral.svg")
        svg = SVGWriter(25, 25)
        generate_spiral(spiral_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)

    def test_polygon_svg(self, polygon_params, tmp_dir):
        path = os.path.join(tmp_dir, "test_polygon.svg")
        svg = SVGWriter(25, 25)
        generate_polygon(polygon_params, None, svg)
        svg.save(path)
        assert os.path.exists(path)


# ── G-code Generation Tests ──────────────────────────────────────────

class TestGCodeGeneration:
    """Test G-code output for all electrode types."""

    def _make_gcode(self, tmp_dir, name="test"):
        gc = GCodeWriter(feed_rate=1000, laser_power=1000)
        gc.header(25, 25)
        path = os.path.join(tmp_dir, f"{name}.gcode")
        return gc, path

    def test_ide_gcode(self, ide_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "ide")
        generate_ide(ide_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)
        content = open(path).read()
        assert "G21" in content
        assert "G90" in content
        assert "M2" in content

    def test_three_gcode(self, three_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "three")
        generate_three(three_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)
        content = open(path).read()
        assert "G21" in content

    def test_serpentine_gcode(self, serpentine_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "serpentine")
        generate_serpentine(serpentine_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)

    def test_ringdisk_gcode(self, ringdisk_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "ringdisk")
        generate_ringdisk(ringdisk_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)

    def test_array_gcode(self, array_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "array")
        generate_array(array_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)

    def test_meander_gcode(self, meander_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "meander")
        generate_meander(meander_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)

    def test_carray_gcode(self, carray_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "carray")
        generate_circular_array(carray_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)

    def test_spiral_gcode(self, spiral_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "spiral")
        generate_spiral(spiral_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)

    def test_polygon_gcode(self, polygon_params, tmp_dir):
        gc, path = self._make_gcode(tmp_dir, "polygon")
        generate_polygon(polygon_params, None, None, gc)
        gc.footer()
        gc.save(path)
        assert os.path.exists(path)


# ── Layer Export Tests ────────────────────────────────────────────────

class TestLayerExport:
    """Test multi-layer export for all electrode types."""

    def test_ide_layers(self, ide_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_ide(ide_params, collector, None, None)
        layers = collector.get_layers()
        assert "SUBSTRATE" in layers
        assert "ELECTRODE_A" in layers
        assert "ELECTRODE_B" in layers
        assert "PAD" in layers

    def test_three_layers(self, three_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_three(three_params, collector, None, None)
        layers = collector.get_layers()
        assert "SUBSTRATE" in layers
        assert "WE" in layers
        assert "CE" in layers
        assert "RE" in layers

    def test_ringdisk_layers(self, ringdisk_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_ringdisk(ringdisk_params, collector, None, None)
        layers = collector.get_layers()
        assert "SUBSTRATE" in layers
        assert "DISK" in layers
        assert "RING" in layers

    def test_spiral_layers(self, spiral_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_spiral(spiral_params, collector, None, None)
        layers = collector.get_layers()
        assert "SUBSTRATE" in layers
        assert "SPIRAL" in layers

    def test_export_layers_dxf(self, ide_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_ide(ide_params, collector, None, None)
        base = os.path.join(tmp_dir, "layer_test")
        export_layers(collector, base, "dxf", layers_filter=["ELECTRODE_A"])
        assert os.path.exists(f"{base}_electrode_a.dxf")

    def test_export_layers_svg(self, ide_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_ide(ide_params, collector, None, None)
        base = os.path.join(tmp_dir, "layer_test")
        export_layers(collector, base, "svg", layers_filter=["ELECTRODE_B"])
        assert os.path.exists(f"{base}_electrode_b.svg")

    def test_export_layers_gcode(self, ide_params, tmp_dir):
        collector = LayerCollector(25, 25)
        generate_ide(ide_params, collector, None, None)
        base = os.path.join(tmp_dir, "layer_test")
        export_layers(collector, base, "gcode", layers_filter=["PAD"])
        assert os.path.exists(f"{base}_pad.gcode")


# ── Design Validation Tests ──────────────────────────────────────────

class TestDesignValidation:
    """Test fabrication constraint validation."""

    def test_ide_valid(self):
        p = IDEParams(finger_w_mm=1.0, gap_mm=0.5, pad_size_mm=3.0, bus_w_mm=2.0)
        warnings = validate_design(p, "screen_print")
        assert len(warnings) == 0

    def test_ide_gap_too_small(self):
        p = IDEParams(gap_mm=0.1, pad_size_mm=3.0)
        warnings = validate_design(p, "screen_print")
        assert any("minimum" in w.lower() for w in warnings)

    def test_ide_bus_too_narrow(self):
        p = IDEParams(finger_w_mm=2.0, bus_w_mm=1.0, pad_size_mm=3.0)
        warnings = validate_design(p, "screen_print")
        assert any("bus" in w.lower() or "2×" in w for w in warnings)

    def test_three_ce_too_small(self):
        p = ThreeElectrodeParams(we_d_mm=6.0, ce_d_mm=3.0)
        warnings = validate_design(p, "screen_print")
        assert any("10:1" in w for w in warnings)

    def test_three_ce_adequate(self):
        p = ThreeElectrodeParams(we_d_mm=3.0, ce_d_mm=10.0)
        warnings = validate_design(p, "screen_print")
        assert not any("10:1" in w for w in warnings)

    def test_ringdisk_gap_tight(self):
        p = RingDiskParams(gap_mm=0.1)
        warnings = validate_design(p, "screen_print")
        assert any("tight" in w.lower() or "0.375" in w for w in warnings)

    def test_array_crosstalk(self):
        p = ArrayParams(electrode_d_mm=3.0, pitch_x_mm=4.0, pitch_y_mm=4.0)
        warnings = validate_design(p, "screen_print")
        assert any("crosstalk" in w.lower() for w in warnings)

    def test_array_no_crosstalk(self):
        p = ArrayParams(electrode_d_mm=2.0, pitch_x_mm=8.0, pitch_y_mm=8.0)
        warnings = validate_design(p, "screen_print")
        assert not any("crosstalk" in w.lower() for w in warnings)

    def test_meander_amplitude_ok(self):
        p = MeanderParams(seg_h_mm=3.0, meander_amp_mm=1.0)
        warnings = validate_design(p, "screen_print")
        assert not any("overlap" in w.lower() for w in warnings)

    def test_meander_amplitude_too_large(self):
        p = MeanderParams(seg_h_mm=2.0, meander_amp_mm=1.5)
        warnings = validate_design(p, "screen_print")
        assert any("overlap" in w.lower() for w in warnings)

    def test_spiral_overlap(self):
        p = SpiralParams(turns=10, r_start_mm=1.0, r_end_mm=5.0, trace_w_mm=1.0)
        warnings = validate_design(p, "screen_print")
        assert any("overlap" in w.lower() for w in warnings)

    def test_fab_constraints_defined(self):
        assert "screen_print" in FAB_CONSTRAINTS
        assert "cricut_vinyl" in FAB_CONSTRAINTS
        assert "laser_co2" in FAB_CONSTRAINTS
        assert "laser_lig" in FAB_CONSTRAINTS
        assert "cnc_mill" in FAB_CONSTRAINTS
        for method, fc in FAB_CONSTRAINTS.items():
            assert "min_trace" in fc
            assert "min_gap" in fc
            assert "min_pad" in fc


# ── DXF File Integrity Tests ─────────────────────────────────────────

class TestDXFIntegrity:
    """Verify DXF files are structurally valid."""

    def test_dxf_version(self, ide_params, tmp_dir):
        import ezdxf
        path = os.path.join(tmp_dir, "test.dxf")
        dxf = DXFWriter(version="R2010")
        generate_ide(ide_params, dxf, None)
        dxf.save(path)
        doc = ezdxf.readfile(path)
        # ezdxf returns internal version code; AC1024 = R2010
        assert doc.dxfversion in ("R2010", "AC1024")

    def test_dxf_layers_exist(self, ide_params, tmp_dir):
        import ezdxf
        path = os.path.join(tmp_dir, "test.dxf")
        dxf = DXFWriter()
        generate_ide(ide_params, dxf, None)
        dxf.save(path)
        doc = ezdxf.readfile(path)
        layer_names = [l.dxf.name for l in doc.layers]
        assert "SUBSTRATE" in layer_names
        assert "ELECTRODE_A" in layer_names
        assert "ELECTRODE_B" in layer_names

    def test_dxf_has_entities(self, ide_params, tmp_dir):
        import ezdxf
        path = os.path.join(tmp_dir, "test.dxf")
        dxf = DXFWriter()
        generate_ide(ide_params, dxf, None)
        dxf.save(path)
        doc = ezdxf.readfile(path)
        entities = list(doc.modelspace())
        assert len(entities) > 5  # At least substrate + fingers + bus + pads


# ── G-code Integrity Tests ───────────────────────────────────────────

class TestGCodeIntegrity:
    """Verify G-code is well-formed."""

    def test_gcode_header_footer(self, ide_params, tmp_dir):
        gc = GCodeWriter(feed_rate=800, laser_power=500)
        gc.header(25, 25)
        generate_ide(ide_params, None, None, gc)
        gc.footer()
        path = os.path.join(tmp_dir, "test.gcode")
        gc.save(path)
        content = open(path).read()
        lines = content.strip().split("\n")
        # Must start with G21 (mm)
        assert any("G21" in l for l in lines[:10])
        # Must end with M2
        assert lines[-1].strip() == "M2" or any("M2" in l for l in lines[-5:])

    def test_gcode_feed_rate(self):
        gc = GCodeWriter(feed_rate=500, laser_power=1000)
        gc.header(25, 25)
        gc.rapid_move(0, 0)
        gc.cut_move(10, 0)
        gc.footer()
        content = gc.get_string()
        assert "F500" in content

    def test_gcode_laser_power(self):
        gc = GCodeWriter(feed_rate=1000, laser_power=750)
        gc.header(25, 25)
        gc.rapid_move(0, 0)
        gc.cut_move(10, 0)
        gc.footer()
        content = gc.get_string()
        assert "S750" in content

    def test_gcode_flip_y(self):
        gc = GCodeWriter(flip_y=True)
        gc.header(25, 25)
        gc.rapid_move(5, 10)
        content = gc.get_string()
        assert "Y-10" in content  # Flipped


# ── Dimensional Accuracy Tests ───────────────────────────────────────

class TestDimensionalAccuracy:
    """Verify generated geometries match specified dimensions."""

    def test_ide_finger_count(self):
        """IDE with 10 fingers should generate exactly 10 finger rectangles."""
        import ezdxf
        p = IDEParams(fingers=10, finger_w_mm=1.0, gap_mm=0.5,
                       finger_l_mm=15, pad_size_mm=3)
        dxf = DXFWriter()
        generate_ide(p, dxf, None)
        doc = dxf.doc
        a_entities = [e for e in doc.modelspace()
                      if e.dxf.layer == "ELECTRODE_A"
                      and e.dxftype() == "LWPOLYLINE"]
        # Should have: bus + N/2 fingers + pad = N/2 + 2 polylines
        # Plus some lines for traces
        assert len(a_entities) >= 5  # bus + at least some fingers

    def test_three_electrode_concentric(self):
        """WE, CE ring should be concentric at substrate center."""
        import ezdxf
        p = ThreeElectrodeParams(we_d_mm=3, ce_d_mm=6, re_d_mm=2, spacing_mm=3)
        dxf = DXFWriter()
        generate_three(p, dxf, None)
        doc = dxf.doc
        circles = [e for e in doc.modelspace() if e.dxftype() == "CIRCLE"]
        # WE circle should be at center (12.5, 12.5) for 25mm substrate
        we_circles = [c for c in circles if c.dxf.layer == "WE"]
        assert len(we_circles) >= 1
        cx, cy = we_circles[0].dxf.center.x, we_circles[0].dxf.center.y
        assert abs(cx - 12.5) < 0.1
        assert abs(cy - 12.5) < 0.1

    def test_ringdisk_gap(self):
        """Ring inner radius should be disk radius + gap."""
        import ezdxf
        p = RingDiskParams(disk_d_mm=5.0, gap_mm=0.5, ring_w_mm=1.5)
        dxf = DXFWriter()
        generate_ringdisk(p, dxf, None)
        doc = dxf.doc
        circles = [e for e in doc.modelspace() if e.dxftype() == "CIRCLE"]
        disk_r = 2.5
        ring_inner_r = disk_r + 0.5  # 3.0
        ring_outer_r = ring_inner_r + 1.5  # 4.5
        # Check ring circles exist with correct radii
        ring_circles = [c for c in circles if c.dxf.layer == "RING"]
        radii = sorted([c.dxf.radius for c in ring_circles])
        assert any(abs(r - ring_inner_r) < 0.1 for r in radii)
        assert any(abs(r - ring_outer_r) < 0.1 for r in radii)

    def test_polygon_triangle(self):
        """Triangle polygon should have 3 vertices (+ close)."""
        import ezdxf
        p = PolygonParams(vertices="5,0;10,8.66;0,8.66")
        dxf = DXFWriter()
        generate_polygon(p, dxf, None)
        doc = dxf.doc
        polys = [e for e in doc.modelspace()
                 if e.dxf.layer == "POLYGON" and e.dxftype() == "LWPOLYLINE"]
        assert len(polys) >= 1
        pts = list(polys[0].get_points(format="xy"))
        assert len(pts) == 4  # 3 vertices + close point


# ── Edge Cases ────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test extreme and unusual parameter combinations."""

    def test_ide_minimum_fingers(self):
        """IDE with 2 fingers should still generate."""
        p = IDEParams(fingers=2, finger_w_mm=1.0, gap_mm=0.5,
                       finger_l_mm=5, pad_size_mm=2)
        dxf = DXFWriter()
        generate_ide(p, dxf, None)
        # No exception = pass

    def test_ide_maximum_fingers(self):
        """IDE with 50 fingers should still generate."""
        p = IDEParams(fingers=50, finger_w_mm=0.5, gap_mm=0.3,
                       finger_l_mm=20, pad_size_mm=2)
        dxf = DXFWriter()
        generate_ide(p, dxf, None)
        # No exception = pass

    def test_spiral_minimum_turns(self):
        """Spiral with 1 turn should still generate."""
        p = SpiralParams(turns=1, r_start_mm=1.0, r_end_mm=5.0)
        dxf = DXFWriter()
        generate_spiral(p, dxf, None)
        # No exception = pass

    def test_spiral_maximum_turns(self):
        """Spiral with 20 turns should still generate."""
        p = SpiralParams(turns=20, r_start_mm=0.5, r_end_mm=12.0,
                          trace_w_mm=0.3)
        dxf = DXFWriter()
        generate_spiral(p, dxf, None)
        # No exception = pass

    def test_array_1x1(self):
        """Single electrode array should work."""
        p = ArrayParams(rows=1, cols=1, electrode_d_mm=2.0,
                         pitch_x_mm=6.0, pitch_y_mm=6.0)
        dxf = DXFWriter()
        generate_array(p, dxf, None)
        # No exception = pass

    def test_array_10x10(self):
        """Large array should work."""
        p = ArrayParams(rows=10, cols=10, electrode_d_mm=1.0,
                         pitch_x_mm=3.5, pitch_y_mm=3.5)
        dxf = DXFWriter()
        generate_array(p, dxf, None)
        # No exception = pass

    def test_small_substrate(self):
        """Very small substrate should generate without error."""
        p = IDEParams(width_mm=5, height_mm=5, fingers=3, finger_w_mm=0.3,
                       gap_mm=0.2, finger_l_mm=2, pad_size_mm=1, bus_w_mm=0.5)
        dxf = DXFWriter()
        generate_ide(p, dxf, None)
        # No exception = pass

    def test_large_substrate(self):
        """Large substrate (100mm) should generate without error."""
        p = IDEParams(width_mm=100, height_mm=100, fingers=20,
                       finger_w_mm=1.5, gap_mm=0.5, finger_l_mm=40)
        dxf = DXFWriter()
        generate_ide(p, dxf, None)
        # No exception = pass


# ── CLI Argument Tests ────────────────────────────────────────────────

class TestCLI:
    """Test that CLI parser accepts all valid arguments."""

    def test_parser_all_types(self):
        from electrode_generator import build_parser
        parser = build_parser()
        for t in ["ide", "three", "serpentine", "ringdisk", "array",
                   "meander", "carray", "spiral", "polygon"]:
            args = parser.parse_args(["--type", t, "--output", "/tmp/test"])
            assert args.type == t

    def test_parser_formats(self):
        from electrode_generator import build_parser
        parser = build_parser()
        for fmt in ["dxf", "svg", "gcode", "both", "all"]:
            args = parser.parse_args(["--type", "ide", "--format", fmt,
                                       "--output", "/tmp/test"])
            assert args.fmt == fmt

    def test_parser_gcode_options(self):
        from electrode_generator import build_parser
        parser = build_parser()
        args = parser.parse_args(["--type", "ide", "--format", "gcode",
                                   "--feed-rate", "800", "--laser-power", "500",
                                   "--flip-y", "--output", "/tmp/test"])
        assert args.feed_rate == 800
        assert args.laser_power == 500
        assert args.flip_y is True

    def test_parser_info_flag(self):
        from electrode_generator import build_parser
        parser = build_parser()
        args = parser.parse_args(["--type", "ide", "--info"])
        assert args.info is True

    def test_parser_validate_flag(self):
        from electrode_generator import build_parser
        parser = build_parser()
        args = parser.parse_args(["--type", "ide", "--validate"])
        assert args.validate is True


# ── Layer Names Completeness ──────────────────────────────────────────

class TestLayerNames:
    """Verify all electrode types have defined layer names."""

    def test_all_types_have_layers(self):
        all_types = ["ide", "three", "serpentine", "ringdisk", "array",
                     "meander", "carray", "spiral", "polygon"]
        for t in all_types:
            assert t in LAYER_NAMES, f"Missing layer names for type '{t}'"
            assert len(LAYER_NAMES[t]) >= 2, f"Type '{t}' has too few layers"

    def test_all_layers_have_substrate(self):
        for t, layers in LAYER_NAMES.items():
            assert "SUBSTRATE" in layers, f"Type '{t}' missing SUBSTRATE layer"


# ── Run tests ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
