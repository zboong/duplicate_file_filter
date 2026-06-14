import time
import requests
from typing import Optional, Tuple, Dict
from pathlib import Path

from .models import PhotoMetadata


def extract_gps_from_exif(exif_data: dict) -> Optional[Tuple[float, float]]:
    """
    Extract GPS coordinates from EXIF data.
    Returns (latitude, longitude) or None.
    """
    # Pillow format
    gps_info = exif_data.get("GPSInfo")
    if gps_info:
        try:
            lat = _convert_to_degrees(gps_info.get(2), gps_info.get(1))
            lon = _convert_to_degrees(gps_info.get(4), gps_info.get(3))
            if lat is not None and lon is not None:
                return (lat, lon)
        except Exception:
            pass

    # exifread format
    lat_tag = exif_data.get("GPS GPSLatitude")
    lat_ref = exif_data.get("GPS GPSLatitudeRef")
    lon_tag = exif_data.get("GPS GPSLongitude")
    lon_ref = exif_data.get("GPS GPSLongitudeRef")

    if lat_tag and lon_tag:
        try:
            lat = _parse_exifread_gps(str(lat_tag), str(lat_ref))
            lon = _parse_exifread_gps(str(lon_tag), str(lon_ref))
            if lat is not None and lon is not None:
                return (lat, lon)
        except Exception:
            pass

    return None


def _convert_to_degrees(value, ref) -> Optional[float]:
    """Convert GPS coordinates from EXIF format to decimal degrees."""
    if not value:
        return None
    try:
        d, m, s = value
        degrees = float(d) + float(m) / 60.0 + float(s) / 3600.0
        if ref in ["S", "W"]:
            degrees = -degrees
        return degrees
    except Exception:
        return None


def _parse_exifread_gps(gps_str: str, ref: str) -> Optional[float]:
    """Parse exifread GPS string format."""
    try:
        parts = gps_str.replace("[", "").replace("]", "").split(",")
        if len(parts) >= 3:
            d = float(parts[0].strip())
            m = float(parts[1].strip())
            s = float(parts[2].strip().replace("'", ""))
            degrees = d + m / 60.0 + s / 3600.0
            if ref in ["S", "W"]:
                degrees = -degrees
            return degrees
    except Exception:
        pass
    return None


def _is_daegu_area(lat: float, lon: float) -> bool:
    """Check if coordinates are roughly in Daegu area."""
    # Daegu approximate bounding box
    return (35.7 <= lat <= 36.0) and (128.4 <= lon <= 128.7)


def reverse_geocode(lat: float, lon: float, timeout: int = 5) -> Optional[Dict]:
    """
    Convert latitude/longitude to location info (name + country).
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    
    is_daegu = _is_daegu_area(lat, lon)
    zoom = 18 if is_daegu else 12
    
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "zoom": zoom,
        "accept-language": "ko"
    }
    headers = {
        "User-Agent": "PhotoOrganizer/1.0 (personal use)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            address = data.get("address", {})
            
            result = {"name": None, "country": None, "city": None, "district": None}
            
            # Extract country (Normalize Singapore)
            if "country" in address:
                country_name = address["country"]
                if "Singapore" in country_name:
                    result["country"] = "Singapore"
                else:
                    result["country"] = country_name
            
            # Extract city (for Korean cities)
            city_candidate = address.get("city") or address.get("state") or address.get("county")
            if city_candidate:
                if "특별시" in city_candidate:
                    result["city"] = city_candidate.replace("특별시", "")
                elif "광역시" in city_candidate:
                    result["city"] = city_candidate.replace("광역시", "")
                elif "특별자치도" in city_candidate:
                    result["city"] = city_candidate.replace("특별자치도", "")
                else:
                    result["city"] = city_candidate
            
            # Extract location name (dong for Daegu, city for others)
            if is_daegu:
                for key in ["suburb", "neighbourhood", "quarter", "residential"]:
                    if key in address and address[key]:
                        name = address[key].strip()
                        if 2 <= len(name) <= 12:
                            result["name"] = name
                            result["district"] = name
                            break
            else:
                for key in ["city", "town", "county", "borough", "district"]:
                    if key in address:
                        name = address[key]
                        if "특별시" in name:
                            result["name"] = name.replace("특별시", "")
                            break
                        if "광역시" in name:
                            result["name"] = name.replace("광역시", "")
                            break
                        result["name"] = name
                        break
            
            if result["name"] or result["country"]:
                return result
            
            # Fallback
            display = data.get("display_name", "")
            if display:
                result["name"] = display.split(",")[0][:12].strip()
                return result
    except Exception:
        pass

    return None


def get_location_name(photo: PhotoMetadata) -> Optional[str]:
    """Placeholder for future use."""
    return None


# Cache for location info
# Key: (rounded_lat, rounded_lon), Value: {"name": str, "country": str}
_location_cache: Dict[Tuple[float, float], Dict] = {}

def clear_location_cache():
    """Clear the Nominatim reverse geocoding cache."""
    global _location_cache
    _location_cache.clear()
    print("[INFO] GPS location cache cleared.")


def _find_similar_cached_location(lat: float, lon: float, tolerance: float = 0.01) -> Optional[Dict]:
    """
    Find a cached location within a certain tolerance.
    This helps avoid API calls when photos are taken at nearly the same location.
    """
    for (cached_lat, cached_lon), info in _location_cache.items():
        if abs(cached_lat - lat) <= tolerance and abs(cached_lon - lon) <= tolerance:
            return info
    return None


def get_cached_location(lat: float, lon: float) -> Optional[Dict]:
    """
    Get location info with smart caching.
    Returns dict {"name": str, "country": str} or None.
    """
    key = (round(lat, 4), round(lon, 4))
    if key in _location_cache:
        return _location_cache[key]
    
    similar = _find_similar_cached_location(lat, lon, tolerance=0.01)
    if similar:
        _location_cache[key] = similar
        return similar
    
    time.sleep(1.0)
    info = reverse_geocode(lat, lon)
    if info:
        _location_cache[key] = info
        return info
    
    return None