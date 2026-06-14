"""Existing target folder structure scanner and date-range based photo placement.

Priority Logic:
1. Scan target folder for existing folders matching the naming pattern
2. Extract date ranges from folder names (ignore location part)
3. Map photos to existing folders based on date range (highest priority)
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .models import PhotoMetadata


@dataclass
class ExistingFolderRange:
    """Represents an existing folder's date range for photo placement."""
    folder_path: Path
    folder_name: str
    start_date: datetime
    end_date: datetime
    # Original folder name components (for reference)
    original_date_part: str
    original_location: Optional[str] = None
    original_postfix: Optional[str] = None


# Pattern to match folder names like: 20190628_서울_여행, 20190628_0706_일본_여행, 20200101_20200315_독일_프랑스_여행
# We extract only the date part (first component before first underscore after date)
FOLDER_NAME_PATTERN = re.compile(
    r'^(?P<start>\d{8})(?:_(?P<end>\d{4,8}))?_(?P<rest>.+)$'
)


def parse_date_range_from_folder_name(folder_name: str) -> Optional[Tuple[datetime, datetime]]:
    """
    Parse date range from folder name.
    
    Examples:
        "20190628_서울_여행" → (2019-06-28, 2019-06-28)
        "20190628_0706_일본_여행" → (2019-06-28, 2019-07-06)
        "20190628_20200101_독일_여행" → (2019-06-28, 2020-01-01)
    
    Returns:
        Tuple of (start_date, end_date) or None if pattern doesn't match
    """
    match = FOLDER_NAME_PATTERN.match(folder_name)
    if not match:
        return None
    
    start_str = match.group('start')
    end_str = match.group('end')
    
    try:
        start_date = datetime.strptime(start_str, "%Y%m%d")
        
        if end_str:
            # Determine end date format based on length
            if len(end_str) == 8:
                # Full year format: 20200101
                end_date = datetime.strptime(end_str, "%Y%m%d")
            elif len(end_str) == 4:
                # Same month: 0706 (month+day only)
                end_date = datetime.strptime(
                    f"{start_date.year}{end_str}", "%Y%m%d"
                )
            else:
                return None
        else:
            end_date = start_date
        
        return (start_date, end_date)
    except ValueError:
        return None


def scan_existing_folders(target_path: Path) -> List[ExistingFolderRange]:
    """
    Scan target folder and extract date ranges from existing folders.
    
    Only folders matching the naming pattern are considered.
    Location and postfix parts are ignored for date-based matching.
    
    Args:
        target_path: Path to target directory
        
    Returns:
        List of ExistingFolderRange sorted by start_date
    """
    if not target_path.exists() or not target_path.is_dir():
        return []
    
    ranges = []
    
    for item in target_path.iterdir():
        if not item.is_dir():
            continue
        
        date_range = parse_date_range_from_folder_name(item.name)
        if date_range is None:
            continue
        
        start_date, end_date = date_range
        
        # Parse additional info from folder name for reference
        match = FOLDER_NAME_PATTERN.match(item.name)
        location = None
        postfix = None
        
        if match:
            rest = match.group('rest')
            # Split rest by underscore to separate location and postfix
            parts = rest.split('_')
            if len(parts) >= 2:
                location = parts[0]
                postfix = parts[-1]
            elif len(parts) == 1:
                location = parts[0]
        
        ranges.append(ExistingFolderRange(
            folder_path=item,
            folder_name=item.name,
            start_date=start_date,
            end_date=end_date,
            original_date_part=match.group('start') if match else start_str,
            original_location=location,
            original_postfix=postfix
        ))
    
    # Sort by start_date for efficient matching
    ranges.sort(key=lambda r: r.start_date)
    return ranges


def find_matching_existing_folder(
    photo_date: datetime,
    existing_ranges: List[ExistingFolderRange]
) -> Optional[ExistingFolderRange]:
    """
    Find an existing folder whose date range contains the photo date.
    
    This is the highest priority placement logic.
    
    Args:
        photo_date: Date of the photo to place
        existing_ranges: List of existing folder date ranges
        
    Returns:
        Matching ExistingFolderRange or None
    """
    for folder_range in existing_ranges:
        if folder_range.start_date <= photo_date <= folder_range.end_date:
            return folder_range
    return None


def group_photos_by_existing_structure(
    photos: List[PhotoMetadata],
    target_path: Path
) -> Dict[Path, List[PhotoMetadata]]:
    """
    Group photos into existing folders based on date range matching.
    
    This function has the HIGHEST PRIORITY in the placement workflow.
    Photos matched here should be placed directly without further grouping.
    
    Args:
        photos: List of photos to place
        target_path: Target directory to scan for existing folders
        
    Returns:
        Dictionary mapping folder_path -> list of photos to place there
    """
    existing_ranges = scan_existing_folders(target_path)
    
    if not existing_ranges:
        return {}
    
    placement: Dict[Path, List[PhotoMetadata]] = {}
    
    for photo in photos:
        if not photo.date_taken:
            continue
        
        match = find_matching_existing_folder(photo.date_taken, existing_ranges)
        if match:
            if match.folder_path not in placement:
                placement[match.folder_path] = []
            placement[match.folder_path].append(photo)
    
    return placement
