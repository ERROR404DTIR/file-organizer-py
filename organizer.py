#!/usr/bin/env python3
"""
file-organizer-py — مرتب‌ساز فایل‌ها (بدون نیاز به pip install)

نمونه استفاده:
    python organizer.py ~/Downloads                # مرتب‌سازی بر اساس نوع فایل
    python organizer.py ~/Downloads --dry-run      # فقط پیش‌نمایش، بدون جابه‌جایی
    python organizer.py ~/Downloads --by date      # مرتب‌سازی بر اساس ماه/سال
    python organizer.py ~/Downloads --undo         # برگرداندن آخرین مرتب‌سازی
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

LOG_NAME = ".organizer_log.json"

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".heic", ".tiff", ".ico"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md", ".epub", ".ppt", ".pptx"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods", ".tsv"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".c", ".cpp", ".java", ".go", ".rs", ".sh", ".sql", ".yml", ".yaml"},
    "Programs": {".exe", ".msi", ".apk", ".dmg", ".deb", ".rpm", ".appimage"},
}

EXT_TO_CAT = {ext: cat for cat, exts in CATEGORIES.items() for ext in exts}


def category_for(path: Path) -> str:
    return EXT_TO_CAT.get(path.suffix.lower(), "Others")


def date_folder_for(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime)
    return ts.strftime("%Y/%Y-%m")


def unique_target(target: Path) -> Path:
    """اگر فایلی با همین نام وجود داشت، یک شماره به آخر نام اضافه می‌کند."""
    if not target.exists():
        return target
    i = 1
    while True:
        candidate = target.with_name(f"{target.stem} ({i}){target.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def organize(folder: Path, mode: str, dry_run: bool) -> int:
    moves = []
    for item in sorted(folder.iterdir()):
        if not item.is_file() or item.name.startswith(".") or item.name == Path(__file__).name:
            continue
        sub = category_for(item) if mode == "type" else date_folder_for(item)
        target = unique_target(folder / sub / item.name)
        moves.append((item, target))

    if not moves:
        print("فایلی برای مرتب‌سازی پیدا نشد.")
        return 0

    done = []
    for src, dst in moves:
        rel = dst.relative_to(folder)
        print(f"{'[پیش‌نمایش] ' if dry_run else ''}{src.name}  ->  {rel}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            done.append({"from": str(src), "to": str(dst)})

    if not dry_run:
        log = {"time": datetime.now().isoformat(timespec="seconds"), "moves": done}
        (folder / LOG_NAME).write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{len(done)} فایل جابه‌جا شد. برای برگرداندن: python organizer.py \"{folder}\" --undo")
    else:
        print(f"\n{len(moves)} فایل جابه‌جا می‌شد (dry-run).")
    return len(moves)


def undo(folder: Path) -> None:
    log_path = folder / LOG_NAME
    if not log_path.exists():
        print("لاگی برای Undo پیدا نشد.")
        return
    log = json.loads(log_path.read_text(encoding="utf-8"))
    restored = 0
    for m in reversed(log["moves"]):
        src, dst = Path(m["to"]), Path(m["from"])
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(unique_target(dst)))
            restored += 1
    # حذف پوشه‌های خالی
    for d in sorted((p for p in folder.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    log_path.unlink()
    print(f"{restored} فایل به جای اولش برگشت.")


def main() -> None:
    p = argparse.ArgumentParser(description="مرتب‌سازی فایل‌های یک پوشه")
    p.add_argument("folder", nargs="?", default=".", help="مسیر پوشه (پیش‌فرض: پوشه فعلی)")
    p.add_argument("--by", choices=["type", "date"], default="type", help="مرتب‌سازی بر اساس نوع یا تاریخ")
    p.add_argument("--dry-run", action="store_true", help="فقط نمایش بدون جابه‌جایی")
    p.add_argument("--undo", action="store_true", help="برگرداندن آخرین مرتب‌سازی")
    args = p.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        sys.exit(f"پوشه پیدا نشد: {folder}")

    if args.undo:
        undo(folder)
    else:
        organize(folder, args.by, args.dry_run)


if __name__ == "__main__":
    main()
