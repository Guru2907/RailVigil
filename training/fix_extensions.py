"""Repair image files saved with a wrong extension (one-off: early Commons
downloads kept URL tracking text in the suffix). Renames each file to the
extension of its real format and updates the manifest.

    python training/fix_extensions.py
"""

import rvdata as rv
from PIL import Image

EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def main() -> None:
    rows = rv.read_manifest()
    fixed = 0
    for r in rows:
        path = rv.DATASETS / r["file"]
        if path.suffix.lower() in rv.IMAGE_EXTENSIONS or not path.is_file():
            continue
        with Image.open(path) as img:
            ext = EXT.get(img.format, ".jpg")
        target = path.with_name(f"{r['image_id']}{ext}")
        path.rename(target)
        r["file"] = f"images/{target.name}"
        fixed += 1
    rv.write_manifest(rows)
    print(f"Renamed {fixed} file(s).")


if __name__ == "__main__":
    main()
