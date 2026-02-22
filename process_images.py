"""
Clean up product images:
  1. Fix EXIF orientation (rotate to correct direction)
  2. Remove background (AI-powered)
  3. Save as clean PNG with transparent background

Usage:
    python process_images.py
    python process_images.py --white-bg    (white background instead of transparent)
"""

import os
import sys
import argparse
from PIL import Image, ImageOps
from tqdm import tqdm
from rembg import remove, new_session

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images_clean")


def fix_orientation(img):
    """Apply EXIF orientation tag and return corrected image."""
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def process_image(input_path, output_path, session, white_bg=False):
    img = Image.open(input_path)
    img = fix_orientation(img)
    img = img.convert("RGBA")

    result = remove(img, session=session)

    if white_bg:
        background = Image.new("RGBA", result.size, (255, 255, 255, 255))
        background.paste(result, mask=result.split()[3])
        result = background.convert("RGB")
        result.save(output_path, "JPEG", quality=92)
    else:
        result.save(output_path, "PNG")


def main():
    parser = argparse.ArgumentParser(description="Clean up product images")
    parser.add_argument("--white-bg", action="store_true",
                        help="Use white background instead of transparent (saves as JPG)")
    args = parser.parse_args()

    if not os.path.isdir(INPUT_DIR):
        print(f"ERROR: Image folder not found: {INPUT_DIR}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = [f for f in os.listdir(INPUT_DIR)
             if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]
    files.sort()

    already = set(os.listdir(OUTPUT_DIR))
    remaining = []
    for f in files:
        base = os.path.splitext(f)[0]
        out_name = base + (".jpg" if args.white_bg else ".png")
        if out_name not in already:
            remaining.append(f)

    print(f"Total images: {len(files)}")
    print(f"Already processed: {len(files) - len(remaining)}")
    print(f"Remaining: {len(remaining)}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Background: {'white' if args.white_bg else 'transparent'}")
    print()

    if not remaining:
        print("All images already processed!")
        return

    print("Loading background removal model (first run downloads ~170MB)...")
    session = new_session("u2net")
    print("Model ready.")
    print()

    processed = 0
    errors = 0

    for f in tqdm(remaining, desc="Processing"):
        base = os.path.splitext(f)[0]
        out_name = base + (".jpg" if args.white_bg else ".png")
        input_path = os.path.join(INPUT_DIR, f)
        output_path = os.path.join(OUTPUT_DIR, out_name)

        try:
            process_image(input_path, output_path, session, args.white_bg)
            processed += 1
        except Exception as e:
            print(f"\n  Error processing {f}: {e}")
            errors += 1

    print()
    print(f"Done! Processed {processed} images, {errors} errors.")
    print(f"Clean images saved to: {OUTPUT_DIR}")
    print()
    print("Next steps:")
    print("  1. Review the clean images in the output folder")
    print("  2. Update config.yaml: image_folder to point to images_clean")
    print("  3. Delete thumbnails folder contents")
    print("  4. Re-run: python import_data.py --clear")


if __name__ == "__main__":
    main()
