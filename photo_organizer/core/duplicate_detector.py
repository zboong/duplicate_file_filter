"""Hierarchical duplicate detection logic."""

import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from collections import defaultdict

try:
    import imagehash
    from PIL import Image
    HAS_PERCEPTUAL = True
except ImportError:
    HAS_PERCEPTUAL = False

from .models import PhotoMetadata, DuplicateMatch


def compute_partial_hash(file_path: Path, chunk_size: int = 4096) -> str:
    """Compute SHA256 of first and last N bytes for fast comparison."""
    h = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            # First chunk
            h.update(f.read(chunk_size))
            # Last chunk
            f.seek(-chunk_size, 2)
            h.update(f.read(chunk_size))
    except Exception:
        return ""
    return h.hexdigest()


def compute_full_hash(file_path: Path) -> str:
    """Compute full file SHA256."""
    h = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def find_duplicates_by_size_and_hash(
    photos: List[PhotoMetadata]
) -> List[DuplicateMatch]:
    """
    Stage 1: Group by size, then partial hash, then full hash.
    Fast and accurate for exact duplicates.
    """
    # Group by size first
    size_groups = defaultdict(list)
    for photo in photos:
        size_groups[photo.file_size].append(photo)

    matches = []
    for size, group in size_groups.items():
        if len(group) < 2:
            continue

        # Partial hash grouping
        partial_groups = defaultdict(list)
        for photo in group:
            ph = compute_partial_hash(photo.file_path)
            if ph:
                partial_groups[ph].append(photo)

        for phash, pgroup in partial_groups.items():
            if len(pgroup) < 2:
                continue

            # Full hash for final verification
            hash_groups = defaultdict(list)
            for photo in pgroup:
                fh = compute_full_hash(photo.file_path)
                if fh:
                    hash_groups[fh].append(photo)

            for fhash, fgroup in hash_groups.items():
                if len(fgroup) < 2:
                    continue

                # Create match pairs
                for i in range(len(fgroup)):
                    for j in range(i + 1, len(fgroup)):
                        matches.append(DuplicateMatch(
                            original=fgroup[i].file_path,
                            duplicate=fgroup[j].file_path,
                            match_type="hash",
                            confidence=1.0
                        ))

    return matches


def find_duplicates_by_exif(
    photos: List[PhotoMetadata]
) -> List[DuplicateMatch]:
    """
    Stage 2: Group by EXIF DateTime + file size (for files with different metadata).
    """
    key_groups = defaultdict(list)
    for photo in photos:
        if photo.date_taken:
            key = (photo.date_taken, photo.file_size)
            key_groups[key].append(photo)

    matches = []
    for key, group in key_groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                matches.append(DuplicateMatch(
                    original=group[i].file_path,
                    duplicate=group[j].file_path,
                    match_type="exif_size",
                    confidence=0.85
                ))

    return matches


def detect_all_duplicates(
    photos: List[PhotoMetadata],
    use_perceptual: bool = False
) -> List[DuplicateMatch]:
    """
    Run hierarchical duplicate detection.
    Stage 1 (hash) → Stage 2 (exif) → Stage 3 (perceptual, optional)
    """
    all_matches = []

    # Stage 1: Exact hash match
    hash_matches = find_duplicates_by_size_and_hash(photos)
    all_matches.extend(hash_matches)

    # Stage 2: EXIF-based match
    exif_matches = find_duplicates_by_exif(photos)
    all_matches.extend(exif_matches)

    # Stage 3: Perceptual hash (optional, slower but catches edited duplicates)
    if use_perceptual and HAS_PERCEPTUAL:
        perceptual_matches = find_duplicates_by_perceptual(photos)
        all_matches.extend(perceptual_matches)

    return all_matches


def find_duplicates_by_perceptual(
    photos: List[PhotoMetadata],
    threshold: int = 5
) -> List[DuplicateMatch]:
    """
    Stage 3: Use perceptual hash (pHash) to find visually similar images.
    threshold: lower = more strict (0 = identical)
    """
    if not HAS_PERCEPTUAL:
        return []

    matches = []
    hashes = {}

    for photo in photos:
        try:
            with Image.open(photo.file_path) as img:
                phash = imagehash.phash(img)
                hashes[photo] = phash
        except Exception:
            continue

    # Compare all pairs
    photo_list = list(hashes.keys())
    for i in range(len(photo_list)):
        for j in range(i + 1, len(photo_list)):
            p1, p2 = photo_list[i], photo_list[j]
            dist = hashes[p1] - hashes[p2]
            if dist <= threshold:
                matches.append(DuplicateMatch(
                    original=p1.file_path,
                    duplicate=p2.file_path,
                    match_type="perceptual",
                    confidence=max(0.5, 1.0 - (dist / 20.0))
                ))

    return matches