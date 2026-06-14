"""EXIF extraction utilities."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
from PIL.ExifTags import TAGS
import exifread

from .models import PhotoMetadata
from .gps_utils import extract_gps_from_exif, get_cached_location


# Device alias mapping (can be overridden by config)
DEVICE_ALIAS = {
    "Apple": {"iPhone": "iPhone", "iPad": "iPad"},
    "Canon": {"EOS": "Canon"},
    "NIKON": {"NIKON": "Nikon"},
    "SONY": {"ILCE": "Sony", "DSC": "Sony"},
    "FUJIFILM": {"X-": "Fujifilm", "GFX": "Fujifilm"},
}


def extract_exif_pillow(file_path: Path) -> dict:
    """Extract EXIF using Pillow (primary method)."""
    try:
        with Image.open(file_path) as img:
            exif = img._getexif()
            if not exif:
                return {}
            return {TAGS.get(k, k): v for k, v in exif.items()}
    except Exception:
        return {}


def extract_exif_exifread(file_path: Path) -> dict:
    """Extract EXIF using exifread (fallback for more formats)."""
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal")
            return {str(k): str(v) for k, v in tags.items()}
    except Exception:
        return {}


def parse_date_taken(exif_data: dict) -> Optional[datetime]:
    """Parse DateTimeOriginal from various EXIF formats."""
    # Pillow format
    for key in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
        if key in exif_data:
            try:
                return datetime.strptime(exif_data[key], "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue

    # exifread format
    for key in ["EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"]:
        if key in exif_data:
            try:
                val = exif_data[key]
                return datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue

    return None


def normalize_image_source(make: Optional[str], model: Optional[str]) -> str:
    """Convert camera make/model to normalized source name."""
    if not make and not model:
        return "Unknown"

    make = (make or "").strip()
    model = (model or "").strip()

    # Check alias mapping
    for brand, aliases in DEVICE_ALIAS.items():
        if brand.lower() in make.lower():
            for prefix, alias in aliases.items():
                if prefix.lower() in model.lower():
                    return alias

    # Fallback: use first 4 chars of model or make
    if model:
        return model[:6].replace(" ", "").upper()
    if make:
        return make[:6].replace(" ", "").upper()

    return "Unknown"


def extract_photo_metadata(file_path: Path) -> Optional[PhotoMetadata]:
    """Main entry point: extract all metadata from a photo file."""
    if not file_path.exists() or not file_path.is_file():
        return None

    # Try Pillow first, then exifread
    exif_data = extract_exif_pillow(file_path)
    if not exif_data:
        exif_data = extract_exif_exifread(file_path)

    date_taken = parse_date_taken(exif_data)
    make = exif_data.get("Make") or exif_data.get("EXIF Make")
    model = exif_data.get("Model") or exif_data.get("EXIF Model")

    image_source = normalize_image_source(make, model)

    stat = file_path.stat()

    # GPS extraction (coordinates only, reverse geocoding is done later for performance)
    gps_lat = None
    gps_lon = None
    country = None
    gps = extract_gps_from_exif(exif_data)
    if gps:
        gps_lat, gps_lon = gps

    return PhotoMetadata(
        file_path=file_path,
        file_size=stat.st_size,
        date_taken=date_taken,
        camera_make=make,
        camera_model=model,
        image_source=image_source,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        country=country,
    )