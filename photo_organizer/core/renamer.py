"""File renaming logic for unified naming convention."""

from datetime import datetime
from pathlib import Path
from typing import Optional
import re

from .models import PhotoMetadata


def generate_new_filename(
    metadata: PhotoMetadata,
    idx: int = 0,
    target_ext: Optional[str] = None
) -> str:
    """
    Generate unified filename: {YYYYMMDD}_{HHMMSS}_{idx}_{imagesource}.{ext}
    
    Example: 20260612_031722_0_iPhone15P.jpg
    """
    if metadata.date_taken:
        date_part = metadata.date_taken.strftime("%Y%m%d")
        time_part = metadata.date_taken.strftime("%H%M%S")
    else:
        # Fallback to file modification time
        stat = metadata.file_path.stat()
        dt = datetime.fromtimestamp(stat.st_mtime)
        date_part = dt.strftime("%Y%m%d")
        time_part = dt.strftime("%H%M%S")

    source = metadata.image_source or "Unknown"
    ext = target_ext or metadata.file_path.suffix.lower()

    return f"{date_part}_{time_part}_{idx}_{source}{ext}"


def should_rename(file_path: Path, new_filename: str) -> bool:
    """Check if file needs renaming."""
    return file_path.name != new_filename


def extract_existing_date_from_filename(filename: str) -> Optional[datetime]:
    """Try to extract date from common filename patterns (e.g., IMG_20230101_123456.jpg)."""
    patterns = [
        r"(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})",  # 20230101_123456
        r"IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})",  # IMG_20230101_123456
        r"(\d{4})-(\d{2})-(\d{2})[ _](\d{2})-(\d{2})-(\d{2})",  # 2023-01-01 12-34-56
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                y, m, d, h, mi, s = match.groups()
                return datetime(int(y), int(m), int(d), int(h), int(mi), int(s))
            except ValueError:
                continue
    return None