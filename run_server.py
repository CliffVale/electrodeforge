"""Production server for ElectrodeForge — works locally and on Render."""
import os
from waitress import serve
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 60)
    print("  ElectrodeForge — Production Server")
    print(f"  http://localhost:{port}")
    print("=" * 60)
    serve(app, host=host, port=port, threads=4)
