import json
from flask import Flask, request, jsonify, send_from_directory
from app.config import load_config
from app.database import init_db, get_item_count
from app.search import hybrid_search, filter_by_category, browse_all, list_categories

cfg = load_config()
app = Flask(__name__, static_folder=cfg["_static_dir"], static_url_path="/static")


@app.before_request
def _strip():
    pass


@app.route("/")
def index():
    return send_from_directory(cfg["_static_dir"], "index.html")


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", cfg["search"]["results_per_page"])), 200)
    offset = int(request.args.get("offset", 0))

    tw = cfg["search"]["text_weight"]
    vw = cfg["search"]["visual_weight"]

    if query:
        items = hybrid_search(query, text_weight=tw, visual_weight=vw, limit=limit)
    else:
        items = browse_all(limit=limit, offset=offset)

    for item in items:
        item.pop("embedding", None)
        if item.get("extra_data"):
            try:
                item["extra"] = json.loads(item["extra_data"])
            except (json.JSONDecodeError, TypeError):
                item["extra"] = {}
        else:
            item["extra"] = {}
        item.pop("extra_data", None)

    return jsonify({"items": items, "total": get_item_count()})


@app.route("/api/categories")
def api_categories():
    return jsonify({"categories": list_categories()})


@app.route("/api/category/<category>")
def api_category(category):
    limit = min(int(request.args.get("limit", 60)), 200)
    items = filter_by_category(category, limit=limit)
    for item in items:
        item.pop("embedding", None)
        if item.get("extra_data"):
            try:
                item["extra"] = json.loads(item["extra_data"])
            except (json.JSONDecodeError, TypeError):
                item["extra"] = {}
        else:
            item["extra"] = {}
        item.pop("extra_data", None)
    return jsonify({"items": items})


@app.route("/thumbnails/<path:filename>")
def serve_thumbnail(filename):
    return send_from_directory(cfg["_thumb_dir"], filename)


def create_app():
    init_db(cfg["_db_path"])
    return app
