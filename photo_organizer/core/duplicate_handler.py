"""Duplicate file handling: move to _duplicates folder, rename, etc."""

import shutil
from pathlib import Path
from typing import List
from collections import defaultdict

from .models import DuplicateMatch


def organize_duplicates(
    duplicates: List[DuplicateMatch],
    duplicates_dir: Path,
    dry_run: bool = False
) -> int:
    """
    Move duplicate files to a separate folder for review.
    
    Returns the number of files moved.
    """
    if not duplicates:
        return 0

    duplicates_dir.mkdir(parents=True, exist_ok=True)
    moved = 0

    # Group duplicates by original to avoid moving the same file multiple times
    seen = set()

    for match in duplicates:
        dup_path = match.duplicate

        if dup_path in seen or not dup_path.exists():
            continue

        # Create a safe filename in _duplicates folder
        dest = duplicates_dir / dup_path.name

        # Handle name collision
        counter = 1
        while dest.exists():
            stem = dup_path.stem
            suffix = dup_path.suffix
            dest = duplicates_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        if dry_run:
            print(f"  [DRY-RUN] Would move: {dup_path.name} -> _duplicates/")
        else:
            try:
                shutil.move(str(dup_path), str(dest))
                moved += 1
                if moved % 5 == 0:
                    print(f"  {moved}개 중복 파일 정리 완료...")
            except Exception as e:
                print(f"  [ERROR] {dup_path.name} 이동 실패: {e}")

        seen.add(dup_path)

    return moved


def remove_duplicates(
    duplicates: List[DuplicateMatch],
    dry_run: bool = False
) -> int:
    """
    Permanently delete duplicate files.
    Use with caution!
    """
    if not duplicates:
        return 0

    deleted = 0
    seen = set()

    for match in duplicates:
        dup_path = match.duplicate
        if dup_path in seen or not dup_path.exists():
            continue

        if dry_run:
            print(f"  [DRY-RUN] Would delete: {dup_path.name}")
        else:
            try:
                dup_path.unlink()
                deleted += 1
            except Exception as e:
                print(f"  [ERROR] {dup_path.name} 삭제 실패: {e}")

        seen.add(dup_path)

    return deleted


def get_duplicate_summary(duplicates: List[DuplicateMatch]) -> str:
    """Generate a human-readable summary of duplicates."""
    if not duplicates:
        return "중복 파일 없음"

    by_type = defaultdict(int)
    for d in duplicates:
        by_type[d.match_type] += 1

    parts = [f"{v}개 ({k})" for k, v in by_type.items()]
    return f"총 {len(duplicates)}쌍 - {', '.join(parts)}"