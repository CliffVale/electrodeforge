# ElectrodeForge ⚡

**Parametric Electrode Generator** — Fabrication-ready DXF, SVG & G-code output for screen printing, laser cutting, and CNC.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/9-electrode%20types-purple" alt="Types">
  <img src="https://img.shields.io/badge/formats-DXF%20%7C%20SVG%20%7C%20G--code-orange" alt="Formats">
</p>

## What It Does

Describe your electrode → get a fabrication-ready file. No CAD skills needed.

| Input | Output |
|---|---|
| "10 finger pairs, 0.5mm width, 0.3mm gap" | `.DXF` for laser cutter (LIG on Kapton) |
| "3-electrode system, WE=3mm, CE=4mm" | `.SVG` for Cricut (screen printing stencil) |
| "5-turn spiral, r=0.5-10mm" | `.G-code` for CNC laser / pen plotter |

## 🔌 Electrode Types

| Type | Description | Use Case |
|---|---|---|
| `ide` | Interdigitated electrode (comb-finger array) | Electrochemical sensors, biosensors |
| `three` | Three-electrode system (WE/CE/RE) | Voltammetry, impedance spectroscopy |
| `serpentine` | Zigzag trace | Stretchable electronics, heaters |
| `ringdisk` | Ring-disk electrode | Collection-mode experiments |
| `array` | Uniform electrode grid | High-throughput screening |
| `meander` | Spring-like serpentine with sine waves | Wearable/flexible sensors |
| `carray` | Circular/radial electrode array | Radial electrochemistry |
| `spiral` | Archimedean spiral | Impedance sensors, inductors |
| `polygon` | Custom shape from vertex list | Any custom geometry |

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/electrodeforge.git
cd electrodeforge
python -m venv .venv && source .venv/bin/activate
pip install ezdxf svgwrite flask

# Generate from command line
python electrode_generator.py --type ide --fingers 10 --finger-w 0.5 --gap 0.3 \
    --finger-l 15 --format both --output my_electrode

# Or use the web UI
python app.py
# Open http://localhost:5000
```

## 📋 Output Formats

| Format | Extension | For | Software |
|---|---|---|---|
| **DXF** | `.dxf` | Laser cutting, LIG | LightBurn, LaserGRBL, RDWorks |
| **SVG** | `.svg` | Cricut, screen printing | Cricut Design Space, Inkscape |
| **G-code** | `.gcode` | CNC, pen plotter | GRBL, K40 Whisperer, Marlin |

## 🖥️ CLI Usage

```bash
# List available layers for a type
python electrode_generator.py --type ide --list-layers

# Generate DXF for laser cutting
python electrode_generator.py --type ide --fingers 10 --finger-w 0.5 --gap 0.3 \
    --finger-l 15 --format dxf --output output/my_ide

# Generate SVG for Cricut
python electrode_generator.py --type three --we-d 3 --ce-d 4 --re-d 2 \
    --format svg --output output/my_3electrode

# Generate G-code with custom settings
python electrode_generator.py --type spiral --turns 5 --r-start 0.5 --r-end 10 \
    --format gcode --feed-rate 800 --laser-power 500 --output output/my_spiral

# Export all three formats at once
python electrode_generator.py --type meander --format all --output output/my_meander

# Multi-layer export (separate file per layer)
python electrode_generator.py --type ide --layers ELECTRODE_A ELECTRODE_B \
    --format dxf --output output/my_ide_layers
```

## 🌐 Web UI

The Flask web app provides a visual interface with:
- **9 electrode types** with dynamic parameter forms
- **Live SVG preview** — changes update as you adjust sliders
- **Download DXF / SVG / G-code** with one click
- **Multi-layer export** — export each layer as a separate file
- **Dark theme** — clean, professional interface

```bash
python app.py
# Open http://localhost:5000
```

## 🏗️ Architecture

```
electrode_generator.py   Core parametric engine (pure Python)
├── 9 generator functions (generate_ide, generate_three, ...)
├── 3 writer classes (DXFWriter, SVGWriter, GCodeWriter)
├── LayerCollector for multi-layer export
└── CLI interface (argparse)

app.py                   Flask web server
├── POST /preview        Live SVG preview
├── POST /download       Generate & download files
├── POST /layers         List available layers
├── POST /download_layers Per-layer file export
└── GET  /schema         Parameter schema
```

## 🧪 Supported Fabrication Methods

| Method | File | Min Feature | Notes |
|---|---|---|---|
| **Laser cutting (LIG)** | DXF, G-code | ~0.1mm | Cut polyimide (Kapton) to make laser-induced graphene |
| **Cricut vinyl stencil** | SVG | ~0.5mm | Cut vinyl mask → screen print conductive ink |
| **CNC milling** | G-code | ~0.2mm | Mill copper-clad PCB |
| **Pen plotter** | G-code | ~0.3mm | Plot with conductive ink pen |

## 📄 License

MIT License — use freely for research and commercial projects.

## 🙏 Acknowledgments

- [ezdxf](https://ezdxf.readthedocs.io/) — DXF file generation
- [svgwrite](https://svgwrite.readthedocs.io/) — SVG file generation
- Built for the open-source electrochemistry community
