#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photo Organizer CLI - V1
Scans source folder, extracts EXIF, groups events, renames, and copies to target.
"""

import argparse
import sys
import shutil
from pathlib import Path
from typing import List
from datetime import datetime

# Add parent to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import PhotoMetadata, PhotoGroup
from core.exif_utils import extract_photo_metadata
from core.renamer import generate_new_filename
from core.grouper import group_photos_by_time, assign_event_names
from core.gps_utils import clear_location_cache
from core.duplicate_detector import detect_all_duplicates, DuplicateMatch
from core.duplicate_handler import organize_duplicates, get_duplicate_summary
from core.config import load_config, Config



def scan_photos(source_dir: Path, recursive: bool = True) -> List[PhotoMetadata]:
    """Scan directory and extract metadata from all supported images."""
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.tiff', '.heic', '.raw', '.cr2', '.nef'}
    
    photos = []
    pattern = '**/*' if recursive else '*'
    
    for file_path in source_dir.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTS:
            meta = extract_photo_metadata(file_path)
            if meta:
                photos.append(meta)
    
    return photos


def copy_with_confirmation(
    photos: List[PhotoMetadata],
    groups: List[PhotoGroup],
    target_dir: Path,
    dry_run: bool = False
) -> None:
    """
    Copy photos to target directory with year-based folder structure.
    """
    print("\n=== 정리 계획 미리보기 ===")
    total = 0
    for group in groups:
        folder_name = group.folder_name
        print(f"\n📁 {folder_name}/ ({len(group.photos)}장)")
        for i, photo in enumerate(group.photos[:3]):
            new_name = generate_new_filename(photo, idx=i)
            print(f"   {photo.file_path.name} -> {new_name}")
        if len(group.photos) > 3:
            print(f"   ... 외 {len(group.photos)-3}장")
        total += len(group.photos)
    
    print(f"\n총 {len(groups)}개 이벤트, {total}장 사진")
    if dry_run:
        print("\n[DRY-RUN] 실제 복사는 수행되지 않습니다.")
        return
    
    answer = input("\n이대로 Target에 복사할까요? (y/N): ").strip().lower()
    if answer != 'y':
        print("취소되었습니다.")
        return
    
    # Actual copy (Year-based structure)
    print("\n=== 복사 시작 (년도별 구조) ===")
    copied = 0
    from collections import defaultdict
    
    # 1. Classified Groups (Year -> Event Folder)
    classified = [g for g in groups if g.event_name and g.start_date]
    for group in classified:
        year = group.start_date.year
        year_dir = target_dir / str(year)
        event_dir = year_dir / group.folder_name
        event_dir.mkdir(parents=True, exist_ok=True)
        
        for i, photo in enumerate(group.photos):
            new_name = generate_new_filename(photo, idx=i)
            dest = event_dir / new_name
            try:
                shutil.copy2(photo.file_path, dest)
                copied += 1
            except Exception as e:
                print(f"  [ERROR] {photo.file_path.name}: {e}")
    
    # 2. Unclassified Photos (Year -> 미분류)
    unclassified = []
    for g in groups:
        if not g.event_name or not g.start_date:
            unclassified.extend(g.photos)
    
    unclassified_by_year = defaultdict(list)
    for p in unclassified:
        y = p.date_taken.year if p.date_taken else datetime.fromtimestamp(p.file_path.stat().st_mtime).year
        unclassified_by_year[y].append(p)
    
    for year, photos in unclassified_by_year.items():
        year_dir = target_dir / str(year) / "미분류"
        year_dir.mkdir(parents=True, exist_ok=True)
        for p in photos:
            dest = year_dir / p.file_path.name
            try:
                shutil.copy2(p.file_path, dest)
                copied += 1
            except Exception as e:
                print(f"  [ERROR] {p.file_path.name}: {e}")
    
    print(f"\n✅ {copied}장 복사 완료")
    
def main():
    parser = argparse.ArgumentParser(
        description="Photo Organizer - EXIF-based event grouping and renaming"
    )
    parser.add_argument(
        "source", type=Path, nargs='?', default=None,
        help="Source directory containing photos"
    )
    parser.add_argument(
        "target", type=Path, nargs='?', default=None,
        help="Target directory for organized photos"
    )
    parser.add_argument(
        "--dry-run", action="store_true", 
        help="Show what would be done without actually copying"
    )
    parser.add_argument(
        "--recursive", action="store_true", default=True,
        help="Scan subdirectories recursively"
    )
    parser.add_argument(
        "--time-gap", type=int, default=None,
        help="Hours gap to consider same event (default: from config)"
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to config.yaml"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command line arguments if provided
    source = args.source or config.paths.source
    target = args.target or config.paths.target
    time_gap = args.time_gap if args.time_gap is not None else config.grouping.time_gap_hours
    
    print(f"[INFO] Config loaded")
    clear_location_cache() # Clear cache for fresh GPS data
    print(f"[INFO] Scanning {source}...")
    photos = scan_photos(source, args.recursive)
    print(f"[INFO] Found {len(photos)} photos with valid metadata")
    
    if not photos:
        print("[WARN] No photos found.")
        return
    
    # Group into events
    print(f"[INFO] Grouping photos (time gap: {time_gap}h)...")
    groups = group_photos_by_time(photos, time_gap_hours=time_gap)
    assign_event_names(groups, default_name=config.grouping.default_event_name)
    print(f"[INFO] Created {len(groups)} event groups")
    
    # Duplicate detection
    use_perceptual = config.duplicate.use_perceptual_hash
    print("[INFO] Detecting duplicates...")
    duplicates = detect_all_duplicates(photos, use_perceptual=use_perceptual)
    if duplicates:
        print(f"[INFO] Found {get_duplicate_summary(duplicates)}")
        
        dup_dir = target / "_duplicates"
        answer = input(f"\n중복 파일 {len(duplicates)}쌍을 _duplicates 폴더로 이동할까요? (Y/n): ").strip().lower()
        if answer != 'n':
            moved = organize_duplicates(duplicates, dup_dir, dry_run=args.dry_run)
            print(f"  -> {moved}개 파일 이동 완료")
    
    # Copy with confirmation
    copy_with_confirmation(photos, groups, target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()