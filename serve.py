"""
Start the Inventory Lookup web server.
Usage:
    python serve.py           (development)
    gunicorn serve:app        (production / Azure)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import load_config
from app.server import create_app
from app.search import _load_embeddings

cfg = load_config()
flask_app = create_app()

try:
    from app.clip_engine import init_clip
    print("Loading CLIP model...")
    init_clip()
    print("Loading image embeddings into memory...")
    _load_embeddings()
except ImportError:
    print("CLIP not available — running text search only.")

app = flask_app


def main():
    import os
    host = cfg["server"]["host"]
    port = int(os.environ.get("PORT", cfg["server"]["port"]))
    print(f"\nServer running at http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")
    flask_app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
