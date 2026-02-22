"""
Import inventory data from an Excel spreadsheet into the search database.

Usage:
    python import_data.py
    python import_data.py --clear   (wipe existing data first)
"""

import os
import sys
import re
import json
import argparse
from difflib import SequenceMatcher

import pandas as pd
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import load_config
from app.database import init_db, clear_items, insert_item

_clip_available = False
try:
    from app.clip_engine import init_clip, encode_image
    _clip_available = True
except ImportError:
    pass

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


def normalize_name(s):
    s = s.lower().strip()
    s = s.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r'["\'/\\,\.\(\)&]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def build_image_index(image_folder):
    """Scan the image folder and return (exact_dict, norm_dict, norm_list)."""
    exact = {}
    normalized = {}
    norm_list = []

    for f in os.listdir(image_folder):
        full = os.path.join(image_folder, f)
        if not os.path.isfile(full):
            continue
        _, ext = os.path.splitext(f)
        if ext.lower() not in IMAGE_EXTENSIONS:
            continue
        base = os.path.splitext(f)[0]
        exact[base.lower().strip()] = full
        norm_key = normalize_name(base)
        normalized[norm_key] = full
        norm_list.append((norm_key, full))

    return exact, normalized, norm_list


def prematch_all(df, name_col, exact_idx, norm_idx, norm_list):
    """
    Pre-compute product-name -> image-path mapping for all rows.
    Does exact, normalized, then fuzzy matching in bulk.
    """
    match_map = {}
    needs_fuzzy = []

    for idx, row in df.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue

        lower = name.lower().strip()
        if lower in exact_idx:
            match_map[idx] = exact_idx[lower]
            continue

        norm = normalize_name(name)
        if norm in norm_idx:
            match_map[idx] = norm_idx[norm]
            continue

        needs_fuzzy.append((idx, norm))

    if needs_fuzzy and norm_list:
        print(f"  Running fuzzy match for {len(needs_fuzzy)} remaining items...")
        for i, (idx, norm) in enumerate(needs_fuzzy):
            best_score = 0
            best_path = None
            for img_norm, img_path in norm_list:
                score = SequenceMatcher(None, norm, img_norm, autojunk=False).ratio()
                if score > best_score:
                    best_score = score
                    best_path = img_path
            if best_score >= 0.88:
                match_map[idx] = best_path
            if (i + 1) % 100 == 0:
                print(f"    {i + 1}/{len(needs_fuzzy)} fuzzy matches done...")

    return match_map


def make_thumbnail(image_path, thumb_dir, thumb_width=300, quality=85):
    basename = os.path.basename(image_path)
    name, _ = os.path.splitext(basename)
    thumb_name = f"{name}_thumb.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_name)

    if os.path.exists(thumb_path):
        return thumb_name

    try:
        img = Image.open(image_path).convert("RGB")
        ratio = thumb_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((thumb_width, new_height), Image.LANCZOS)
        img.save(thumb_path, "JPEG", quality=quality)
        return thumb_name
    except Exception as e:
        print(f"  Warning: thumbnail failed for {basename}: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Import inventory data")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before importing")
    args = parser.parse_args()

    cfg = load_config()
    spreadsheet = cfg["spreadsheet"]
    image_folder = cfg["image_folder"]
    col_map = cfg["columns"]
    thumb_cfg = cfg.get("thumbnails", {})
    thumb_width = thumb_cfg.get("width", 300)
    thumb_quality = thumb_cfg.get("quality", 85)
    thumb_dir = cfg["_thumb_dir"]
    db_path = cfg["_db_path"]

    print(f"Spreadsheet : {spreadsheet}")
    print(f"Image folder: {image_folder}")
    print()

    if not os.path.isfile(spreadsheet):
        print(f"ERROR: Spreadsheet not found: {spreadsheet}")
        sys.exit(1)

    has_images = os.path.isdir(image_folder)
    if not has_images:
        print("WARNING: Image folder not found. Text-only import.")
        print()

    print("Reading spreadsheet...")
    df = pd.read_excel(spreadsheet)
    print(f"Found {len(df)} rows")
    print()

    name_col = col_map.get("name", "Product Name")
    extra_col_names = col_map.get("extra", [])

    if name_col not in df.columns:
        print(f"ERROR: Column '{name_col}' not found.")
        sys.exit(1)

    init_db(db_path)
    if args.clear:
        print("Clearing existing data...")
        clear_items()

    match_map = {}
    if has_images:
        print("Indexing image folder...")
        exact_idx, norm_idx, norm_list = build_image_index(image_folder)
        print(f"Found {len(norm_list)} image files")
        print()

        print("Matching product names to images...")
        match_map = prematch_all(df, name_col, exact_idx, norm_idx, norm_list)
        print(f"Matched {len(match_map)} / {len(df)} products to images")
        print()

        if _clip_available:
            print("Initializing CLIP model...")
            init_clip()
            print("CLIP ready.")
        else:
            print("CLIP not installed -- thumbnails only, no visual search.")
    print()

    os.makedirs(thumb_dir, exist_ok=True)

    print("Importing items...")
    imported = 0
    skipped = 0

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Importing"):
        name = str(row.get(name_col, "")).strip()
        if not name:
            skipped += 1
            continue

        extra = {}
        for ec in extra_col_names:
            if ec in df.columns:
                val = row.get(ec)
                if pd.notna(val):
                    extra[ec] = str(val).strip()
        product_id = row.get("Product Id")
        if pd.notna(product_id):
            extra["Product Id"] = str(int(product_id))
        part_num = row.get("Part #")
        if pd.notna(part_num):
            extra["Part #"] = str(part_num)
        extra_json = json.dumps(extra) if extra else ""

        image_path = match_map.get(idx)

        thumb_file = ""
        embedding = None

        if image_path:
            thumb_file = make_thumbnail(image_path, thumb_dir, thumb_width, thumb_quality)
            if _clip_available:
                try:
                    embedding = encode_image(image_path)
                except Exception as e:
                    print(f"  Warning: CLIP failed for {name}: {e}")

        insert_item(name, "", extra_json, name, thumb_file, embedding)
        imported += 1

    print()
    print(f"Done! Imported {imported} items, skipped {skipped} empty rows.")
    if has_images:
        print(f"Images matched: {len(match_map)} / {imported}")
    print(f"Database: {db_path}")
    print(f"Run 'python serve.py' to start the search server.")


if __name__ == "__main__":
    main()
