#!/usr/bin/env python3
"""
Electrode Generator Web UI
===========================
Flask app that provides a visual interface for the parametric electrode generator.
Run: python app.py
Then open: http://localhost:5000
"""

import io
import os
import sys
import uuid
import tempfile

from flask import Flask, render_template, request, send_file, jsonify, Response

# Import the generator
from electrode_generator import (
    DXFWriter, SVGWriter, GCodeWriter, LayerCollector,
    IDEParams, ThreeElectrodeParams, SerpentineParams,
    RingDiskParams, ArrayParams, MeanderParams,
    CircularArrayParams, SpiralParams, PolygonParams,
    generate_ide, generate_three, generate_serpentine,
    generate_ringdisk, generate_array, generate_meander,
    generate_circular_array, generate_spiral, generate_polygon,
    export_layers, LAYER_NAMES,
)

app = Flask(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Parameter schema for each electrode type ────────────────────────
TYPE_SCHEMA = {
    "ide": {
        "label": "Interdigitated Electrode (IDE)",
        "description": "Comb-finger array for electrochemical sensors. Two interlocking combs with alternating fingers.",
        "params": [
            {"name": "fingers", "label": "Finger Pairs", "type": "int", "default": 10, "min": 2, "max": 100, "step": 1},
            {"name": "finger_w", "label": "Finger Width (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 5, "step": 0.1},
            {"name": "gap", "label": "Gap Between Fingers (mm)", "type": "float", "default": 0.3, "min": 0.1, "max": 5, "step": 0.1},
            {"name": "finger_l", "label": "Finger Length (mm)", "type": "float", "default": 15.0, "min": 1, "max": 50, "step": 0.5},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
            {"name": "bus_w", "label": "Bus Bar Width (mm)", "type": "float", "default": 1.0, "min": 0.5, "max": 5, "step": 0.1},
            {"name": "margin", "label": "Margin (mm)", "type": "float", "default": 2.0, "min": 0.5, "max": 10, "step": 0.5},
        ]
    },
    "three": {
        "label": "Three-Electrode System",
        "description": "WE (centre disk), CE (ring), RE (adjacent disk) — standard for voltammetry.",
        "params": [
            {"name": "we_d", "label": "WE Diameter (mm)", "type": "float", "default": 3.0, "min": 0.5, "max": 15, "step": 0.5},
            {"name": "ce_d", "label": "CE Diameter (mm)", "type": "float", "default": 4.0, "min": 0.5, "max": 15, "step": 0.5},
            {"name": "re_d", "label": "RE Diameter (mm)", "type": "float", "default": 2.0, "min": 0.5, "max": 15, "step": 0.5},
            {"name": "spacing", "label": "Centre Spacing (mm)", "type": "float", "default": 5.0, "min": 2, "max": 20, "step": 0.5},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
    "serpentine": {
        "label": "Serpentine Trace",
        "description": "Zigzag trace for stretchable electronics and resistive heating.",
        "params": [
            {"name": "trace_w", "label": "Trace Width (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 3, "step": 0.1},
            {"name": "segments", "label": "Segments", "type": "int", "default": 10, "min": 2, "max": 50, "step": 1},
            {"name": "seg_l", "label": "Segment Length (mm)", "type": "float", "default": 2.0, "min": 0.5, "max": 10, "step": 0.5},
            {"name": "seg_h", "label": "Segment Height (mm)", "type": "float", "default": 1.5, "min": 0.5, "max": 5, "step": 0.1},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
    "ringdisk": {
        "label": "Ring-Disk Electrode",
        "description": "Concentric disk and ring for collection-mode experiments.",
        "params": [
            {"name": "disk_d", "label": "Disk Diameter (mm)", "type": "float", "default": 3.0, "min": 0.5, "max": 15, "step": 0.5},
            {"name": "gap", "label": "Gap (mm)", "type": "float", "default": 0.2, "min": 0.05, "max": 2, "step": 0.05},
            {"name": "ring_w", "label": "Ring Width (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 3, "step": 0.1},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
    "array": {
        "label": "Electrode Array (Grid)",
        "description": "Uniform grid of circular electrodes with common bus bar.",
        "params": [
            {"name": "rows", "label": "Rows", "type": "int", "default": 4, "min": 1, "max": 20, "step": 1},
            {"name": "cols", "label": "Columns", "type": "int", "default": 4, "min": 1, "max": 20, "step": 1},
            {"name": "electrode_d", "label": "Electrode Diameter (mm)", "type": "float", "default": 2.0, "min": 0.5, "max": 10, "step": 0.5},
            {"name": "pitch_x", "label": "Horizontal Pitch (mm)", "type": "float", "default": 5.0, "min": 1, "max": 20, "step": 0.5},
            {"name": "pitch_y", "label": "Vertical Pitch (mm)", "type": "float", "default": 5.0, "min": 1, "max": 20, "step": 0.5},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 2.0, "min": 0.5, "max": 10, "step": 0.5},
        ]
    },
    "meander": {
        "label": "Meander (Spring Serpentine)",
        "description": "Each segment has sinusoidal waves — stretches more than plain serpentine.",
        "params": [
            {"name": "trace_w", "label": "Trace Width (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 3, "step": 0.1},
            {"name": "segments", "label": "Segments", "type": "int", "default": 6, "min": 2, "max": 30, "step": 1},
            {"name": "seg_l", "label": "Segment Length (mm)", "type": "float", "default": 3.0, "min": 0.5, "max": 10, "step": 0.5},
            {"name": "seg_h", "label": "Segment Height (mm)", "type": "float", "default": 2.0, "min": 0.5, "max": 5, "step": 0.1},
            {"name": "meander_n", "label": "Waves Per Segment", "type": "int", "default": 8, "min": 1, "max": 30, "step": 1},
            {"name": "meander_amp", "label": "Wave Amplitude (mm)", "type": "float", "default": 0.8, "min": 0.1, "max": 3, "step": 0.1},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
    "carray": {
        "label": "Circular Array",
        "description": "Electrodes in concentric rings with radial traces to centre pad.",
        "params": [
            {"name": "rings", "label": "Rings", "type": "int", "default": 3, "min": 1, "max": 10, "step": 1},
            {"name": "epr", "label": "Electrodes Per Ring (outer)", "type": "int", "default": 8, "min": 4, "max": 36, "step": 1},
            {"name": "electrode_d", "label": "Electrode Diameter (mm)", "type": "float", "default": 1.5, "min": 0.5, "max": 5, "step": 0.1},
            {"name": "ring_spacing", "label": "Ring Spacing (mm)", "type": "float", "default": 4.0, "min": 1, "max": 10, "step": 0.5},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
    "spiral": {
        "label": "Spiral Electrode",
        "description": "Archimedean spiral — r = a + b*theta. Common in impedance sensors.",
        "params": [
            {"name": "turns", "label": "Turns", "type": "int", "default": 5, "min": 1, "max": 20, "step": 1},
            {"name": "r_start", "label": "Start Radius (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 5, "step": 0.1},
            {"name": "r_end", "label": "End Radius (mm)", "type": "float", "default": 10.0, "min": 2, "max": 20, "step": 0.5},
            {"name": "trace_w", "label": "Trace Width (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 3, "step": 0.1},
            {"name": "spiral_pts", "label": "Resolution (points)", "type": "int", "default": 200, "min": 50, "max": 1000, "step": 50},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
    "polygon": {
        "label": "Custom Polygon",
        "description": "Define any closed shape by listing its vertices (x,y pairs).",
        "params": [
            {"name": "vertices", "label": "Vertices (x1,y1;x2,y2;...)", "type": "text", "default": "0,0;5,0;2.5,4.33", "placeholder": "0,0;5,0;2.5,4.33"},
            {"name": "trace_w", "label": "Trace Width (mm)", "type": "float", "default": 0.5, "min": 0.1, "max": 3, "step": 0.1},
            {"name": "pad_size", "label": "Pad Size (mm)", "type": "float", "default": 3.0, "min": 1, "max": 10, "step": 0.5},
        ]
    },
}


def build_params(elec_type, form):
    """Build the correct Params dataclass from form data."""
    w = float(form.get("width", 25))
    h = float(form.get("height", 25))
    fmt = form.get("fmt", "svg")

    def _f(name, default):
        v = form.get(name, default)
        try:
            return type(default)(v)
        except (ValueError, TypeError):
            return default

    if elec_type == "ide":
        return IDEParams(width_mm=w, height_mm=h, fingers=_f("fingers", 10),
                         finger_w_mm=_f("finger_w", 0.5), gap_mm=_f("gap", 0.3),
                         finger_l_mm=_f("finger_l", 15.0), pad_size_mm=_f("pad_size", 3.0),
                         bus_w_mm=_f("bus_w", 1.0), margin_mm=_f("margin", 2.0))
    elif elec_type == "three":
        return ThreeElectrodeParams(width_mm=w, height_mm=h,
                                    we_d_mm=_f("we_d", 3.0), ce_d_mm=_f("ce_d", 4.0),
                                    re_d_mm=_f("re_d", 2.0), spacing_mm=_f("spacing", 5.0),
                                    pad_size_mm=_f("pad_size", 3.0))
    elif elec_type == "serpentine":
        return SerpentineParams(width_mm=w, height_mm=h, trace_w_mm=_f("trace_w", 0.5),
                                segments=_f("segments", 10), seg_l_mm=_f("seg_l", 2.0),
                                seg_h_mm=_f("seg_h", 1.5), pad_size_mm=_f("pad_size", 3.0))
    elif elec_type == "ringdisk":
        return RingDiskParams(width_mm=w, height_mm=h, disk_d_mm=_f("disk_d", 3.0),
                              gap_mm=_f("gap", 0.2), ring_w_mm=_f("ring_w", 0.5),
                              pad_size_mm=_f("pad_size", 3.0))
    elif elec_type == "array":
        return ArrayParams(width_mm=w, height_mm=h, rows=_f("rows", 4), cols=_f("cols", 4),
                           electrode_d_mm=_f("electrode_d", 2.0), pitch_x_mm=_f("pitch_x", 5.0),
                           pitch_y_mm=_f("pitch_y", 5.0), pad_size_mm=_f("pad_size", 2.0))
    elif elec_type == "meander":
        return MeanderParams(width_mm=w, height_mm=h, trace_w_mm=_f("trace_w", 0.5),
                             segments=_f("segments", 6), seg_l_mm=_f("seg_l", 3.0),
                             seg_h_mm=_f("seg_h", 2.0), meander_n=_f("meander_n", 8),
                             meander_amp_mm=_f("meander_amp", 0.8), pad_size_mm=_f("pad_size", 3.0))
    elif elec_type == "carray":
        return CircularArrayParams(width_mm=w, height_mm=h, rings=_f("rings", 3),
                                   electrodes_per_ring=_f("epr", 8),
                                   electrode_d_mm=_f("electrode_d", 1.5),
                                   ring_spacing_mm=_f("ring_spacing", 4.0),
                                   pad_size_mm=_f("pad_size", 3.0))
    elif elec_type == "spiral":
        return SpiralParams(width_mm=w, height_mm=h, turns=_f("turns", 5),
                            r_start_mm=_f("r_start", 0.5), r_end_mm=_f("r_end", 10.0),
                            trace_w_mm=_f("trace_w", 0.5), n_points=_f("spiral_pts", 200),
                            pad_size_mm=_f("pad_size", 3.0))
    elif elec_type == "polygon":
        return PolygonParams(width_mm=w, height_mm=h,
                             vertices=form.get("vertices", "0,0;5,0;2.5,4.33"),
                             trace_w_mm=_f("trace_w", 0.5), pad_size_mm=_f("pad_size", 3.0))
    return None


GENERATORS = {
    "ide": generate_ide,
    "three": generate_three,
    "serpentine": generate_serpentine,
    "ringdisk": generate_ringdisk,
    "array": generate_array,
    "meander": generate_meander,
    "carray": generate_circular_array,
    "spiral": generate_spiral,
    "polygon": generate_polygon,
}


# ─── Routes ──────────────────────────────────────────────────────────

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/app")
def index():
    return render_template("index.html", schema=TYPE_SCHEMA)


@app.route("/preview", methods=["POST"])
def preview():
    """Generate SVG in-memory and return it for live preview."""
    data = request.json
    elec_type = data.get("type", "ide")
    form = data.get("params", {})
    form["width"] = data.get("width", 25)
    form["height"] = data.get("height", 25)

    params = build_params(elec_type, form)
    if params is None:
        return jsonify({"error": "Invalid electrode type"}), 400

    svg_writer = SVGWriter(params.width_mm, params.height_mm)
    gen_func = GENERATORS.get(elec_type)
    if gen_func is None:
        return jsonify({"error": "Unknown type"}), 400

    gen_func(params, None, svg_writer)

    # Capture SVG string
    svg_buffer = io.StringIO()
    svg_writer.dwg.write(svg_buffer)
    svg_string = svg_buffer.getvalue()

    return Response(svg_string, mimetype="image/svg+xml")


@app.route("/download", methods=["POST"])
def download():
    """Generate and download DXF and/or SVG files."""
    data = request.json
    elec_type = data.get("type", "ide")
    form = data.get("params", {})
    form["width"] = data.get("width", 25)
    form["height"] = data.get("height", 25)
    fmt = data.get("fmt", "both")

    params = build_params(elec_type, form)
    if params is None:
        return jsonify({"error": "Invalid electrode type"}), 400

    gen_func = GENERATORS.get(elec_type)
    if gen_func is None:
        return jsonify({"error": "Unknown type"}), 400

    uid = uuid.uuid4().hex[:8]
    base_name = f"{elec_type}_{uid}"

    feed_rate = int(data.get("feed_rate", 1000))
    laser_power = int(data.get("laser_power", 1000))
    flip_y = bool(data.get("flip_y", False))

    results = {}

    if fmt in ("dxf", "both"):
        dxf_path = os.path.join(OUTPUT_DIR, f"{base_name}.dxf")
        dxf_writer = DXFWriter()
        gen_func(params, dxf_writer, None, None)
        dxf_writer.save(dxf_path)
        results["dxf"] = f"{base_name}.dxf"

    if fmt in ("svg", "both"):
        svg_path = os.path.join(OUTPUT_DIR, f"{base_name}.svg")
        svg_writer = SVGWriter(params.width_mm, params.height_mm)
        gen_func(params, None, svg_writer, None)
        svg_writer.save(svg_path)
        results["svg"] = f"{base_name}.svg"

    if fmt in ("gcode", "all"):
        gc_path = os.path.join(OUTPUT_DIR, f"{base_name}.gcode")
        gc_writer = GCodeWriter(feed_rate=feed_rate, laser_power=laser_power, flip_y=flip_y)
        gc_writer.header(params.width_mm, params.height_mm)
        gen_func(params, None, None, gc_writer)
        gc_writer.footer()
        gc_writer.save(gc_path)
        results["gcode"] = f"{base_name}.gcode"

    if fmt == "all":
        # Also generate DXF and SVG for 'all' format
        if "dxf" not in results:
            dxf_path = os.path.join(OUTPUT_DIR, f"{base_name}.dxf")
            dxf_writer = DXFWriter()
            gen_func(params, dxf_writer, None, None)
            dxf_writer.save(dxf_path)
            results["dxf"] = f"{base_name}.dxf"
        if "svg" not in results:
            svg_path = os.path.join(OUTPUT_DIR, f"{base_name}.svg")
            svg_writer = SVGWriter(params.width_mm, params.height_mm)
            gen_func(params, None, svg_writer, None)
            svg_writer.save(svg_path)
            results["svg"] = f"{base_name}.svg"

    return jsonify(results)


@app.route("/download_file/<filename>")
def download_file(filename):
    """Serve a generated file for download."""
    # Sanitize filename
    safe_name = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(filepath):
        return "File not found", 404
    return send_file(filepath, as_attachment=True)


@app.route("/layers", methods=["POST"])
def layers():
    """Return available layers for an electrode type."""
    data = request.json
    elec_type = data.get("type", "ide")
    available = LAYER_NAMES.get(elec_type, [])
    return jsonify({"layers": available, "type": elec_type})


@app.route("/download_layers", methods=["POST"])
def download_layers():
    """Generate per-layer DXF/SVG/GCode files and return download links."""
    data = request.json
    elec_type = data.get("type", "ide")
    form = data.get("params", {})
    form["width"] = data.get("width", 25)
    form["height"] = data.get("height", 25)
    fmt = data.get("fmt", "dxf")
    selected_layers = data.get("layers", [])
    feed_rate = int(data.get("feed_rate", 1000))
    laser_power = int(data.get("laser_power", 1000))
    flip_y = bool(data.get("flip_y", False))

    params = build_params(elec_type, form)
    if params is None:
        return jsonify({"error": "Invalid electrode type"}), 400

    gen_func = GENERATORS.get(elec_type)
    if gen_func is None:
        return jsonify({"error": "Unknown type"}), 400

    uid = uuid.uuid4().hex[:8]
    base_name = f"{elec_type}_layer_{uid}"
    base_path = os.path.join(OUTPUT_DIR, base_name)

    # Use LayerCollector to gather all shapes
    collector = LayerCollector(params.width_mm, params.height_mm)
    gen_func(params, collector, None, None)

    # Export per-layer files
    export_layers(collector, base_path, fmt,
                  layers_filter=selected_layers if selected_layers else None,
                  feed_rate=feed_rate, laser_power=laser_power, flip_y=flip_y)

    # Build download links
    results = {}
    layer_names = [n for n in collector.get_layer_names() if n in collector.get_layers()]
    if selected_layers:
        layer_names = [n for n in layer_names if n in selected_layers]

    for name in layer_names:
        safe = name.lower().replace(" ", "_")
        key = f"{safe}"
        results[key] = []
        if fmt in ("dxf", "both", "all"):
            results[key].append({"fmt": "DXF", "file": f"{base_name}_{safe}.dxf"})
        if fmt in ("svg", "both", "all"):
            results[key].append({"fmt": "SVG", "file": f"{base_name}_{safe}.svg"})
        if fmt in ("gcode", "all"):
            results[key].append({"fmt": "GCode", "file": f"{base_name}_{safe}.gcode"})

    return jsonify(results)


@app.route("/schema")
def schema():
    """Return the parameter schema as JSON."""
    return jsonify(TYPE_SCHEMA)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Electrode Generator Web UI")
    print("  Open: http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
