import os
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config():
    config_path = os.path.join(BASE_DIR, "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["_base_dir"] = BASE_DIR
    cfg["_db_path"] = os.path.join(BASE_DIR, "data", "inventory.db")
    cfg["_thumb_dir"] = os.path.join(BASE_DIR, "thumbnails")
    cfg["_static_dir"] = os.path.join(BASE_DIR, "static")

    if not os.path.isabs(cfg.get("spreadsheet", "")):
        cfg["spreadsheet"] = os.path.join(BASE_DIR, cfg["spreadsheet"])

    return cfg
