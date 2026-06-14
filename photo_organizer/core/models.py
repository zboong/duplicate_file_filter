"""Data models for photo organizer."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List


@dataclass
class PhotoMetadata:
    """Extracted metadata from a photo file."""
    file_path: Path
    file_size: int
    date_taken: Optional[datetime] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    image_source: Optional[str] = None  # Normalized device name (e.g., iPhone15, R5)
    width: Optional[int] = None
    height: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    location_name: Optional[str] = None   # e.g., "제주도", "서울", "범어동"
    country: Optional[str] = None           # e.g., "Germany", "France", "South Korea"
    city: Optional[str] = None              # e.g., "Seoul", "Busan", "Daegu"
    district: Optional[str] = None          # e.g., "Suseong-gu" (for Daegu Dong logic)

    @property
    def has_date(self) -> bool:
        return self.date_taken is not None


@dataclass
class PhotoGroup:
    """A group of photos belonging to the same event."""
    photos: List[PhotoMetadata] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_name: Optional[str] = None  # User-provided or auto-generated

    def add_photo(self, photo: PhotoMetadata):
        self.photos.append(photo)
        self._update_date_range()

    def _update_date_range(self):
        dates = [p.date_taken for p in self.photos if p.date_taken]
        if dates:
            self.start_date = min(dates)
            self.end_date = max(dates)

    @property
    def folder_name(self) -> str:
        """Generate folder name like 231119_이월드나들이 or 20220504_20220506_서울나들이"""
        if not self.start_date:
            return "unknown_date"

        start_str = self.start_date.strftime("%y%m%d")
        
        if self.end_date and self.end_date.date() != self.start_date.date():
            end_str = self.end_date.strftime("%Y%m%d")
            base = f"{start_str}_{end_str}"
        else:
            base = start_str

        # Use location-based name if available
        name_part = self.event_name or 'event'
        return f"{base}_{name_part}"


@dataclass
class DuplicateMatch:
    """Represents a duplicate file match."""
    original: Path
    duplicate: Path
    match_type: str  # 'hash', 'exif_size', 'perceptual'
    confidence: float  # 0.0 ~ 1.0
    suggested_action: str = "move_to_duplicates"  # or 'delete', 'keep_both'