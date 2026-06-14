"""Event grouping logic based on photo timestamps and GPS location.

New Strategy:
1. GPS-based grouping (location change triggers new group)
2. Time-based grouping (for photos without GPS)
3. Filtering (exclude home area Daegu dongs, groups < 30 photos)
4. Naming rules (Korea: City/Dong, Overseas: Country, Postfix: 여행/나들이/구경)
"""

from datetime import datetime, timedelta
from typing import List, Optional, Set
from collections import defaultdict

from .models import PhotoMetadata, PhotoGroup
from .gps_utils import get_cached_location


def group_photos_by_time(
    photos: List[PhotoMetadata],
    time_gap_hours: int = 18
) -> List[PhotoGroup]:
    """
    Hierarchical Grouping:
    1. Determine Stable Key (Country for small overseas like Singapore, City/District for Korea).
    2. Group by Stable Key first.
    3. If key is same, merge by time gap.
    """
    if not photos:
        return []

    dated_photos = [p for p in photos if p.date_taken]
    dated_photos.sort(key=lambda p: p.date_taken)

    if not dated_photos:
        group = PhotoGroup(photos=photos)
        return [group]

    groups = []
    current_group = PhotoGroup()
    last_date = None
    last_stable_key = None # (is_korea, location_key)

    for photo in dated_photos:
        stable_key = None
        is_korea = False
        if photo.gps_lat and photo.gps_lon:
            info = get_cached_location(photo.gps_lat, photo.gps_lon)
            if info:
                country = info.get("country")
                if country == "South Korea" or country == "대한민국":
                    is_korea = True
                    # Korean: Use District (Dong) if available, else City
                    stable_key = info.get("district") or info.get("city")
                else:
                    # Overseas: Use Country ONLY for small countries like Singapore to keep them together
                    # Use City if available for large countries (e.g., USA states)
                    stable_key = country 
        
        if last_date is None:
            current_group.add_photo(photo)
            last_date = photo.date_taken
            last_stable_key = (is_korea, stable_key)
        else:
            gap = photo.date_taken - last_date
            location_changed = False
            
            current_key = (is_korea, stable_key)
            if current_key != last_stable_key:
                location_changed = True
            
            if gap <= timedelta(hours=time_gap_hours) and not location_changed:
                current_group.add_photo(photo)
            else:
                if current_group.photos:
                    groups.append(current_group)
                current_group = PhotoGroup(photos=[photo])
            
            last_date = photo.date_taken
            last_stable_key = current_key

    if current_group.photos:
        groups.append(current_group)

    return groups


# --- New Naming Logic ---

HOME_DONGS = {"유천동", "대천동", "진천동", "월성동", "상인동"} # Daegu home area


def _get_postfix(days: int) -> str:
    if days >= 3:
        return "여행"
    elif days == 2:
        return "나들"
    else:
        return "구경"


def _format_date_range(start: datetime, end: datetime) -> str:
    """Format date range based on requirements."""
    if start.date() == end.date():
        return start.strftime("%Y%m%d")
    
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%m%d") # Default: MMDD
    
    if start.year != end.year:
        end_str = end.strftime("%Y%m%d")
    elif start.month != end.month:
        end_str = end.strftime("%m%d")
        
    return f"{start_str}_{end_str}"


def assign_event_names(groups: List[PhotoGroup], default_name: str = "event") -> None:
    """
    Assigns names based on strict rules. If rules cannot be met, event_name becomes None (unclassified).
    """
    for group in groups:
        # Reset name to ensure clean state
        group.event_name = None 
        
        gps_photos = [p for p in group.photos if p.gps_lat and p.gps_lon]
        
        # Rule 1 & 2: Filtering (Size < 30 or No GPS)
        if len(group.photos) < 30 or not gps_photos:
            continue # Remains None, goes to '미분류'

        # Rule 3: Determine Location Name
        location_name = None
        is_korea = False
        countries = set()
        
        for photo in gps_photos:
            info = get_cached_location(photo.gps_lat, photo.gps_lon)
            if not info: continue
            
            if info.get("country"):
                countries.add(info["country"])
            
            # Check for Korean home area exclusion
            if info.get("district") in HOME_DONGS:
                # Home area, remains None
                return 
            
            # Priority: Dong > City > Name
            if info.get("district"):
                location_name = info["district"]
                is_korea = True
                break
            elif info.get("city"):
                location_name = info["city"]
                is_korea = True
                break
            elif info.get("name"):
                if info.get("country") == "South Korea" or info.get("country") == "대한민국":
                    is_korea = True
                location_name = info["name"]
                break
        
        if not location_name:
            # Cannot resolve name, remains None
            continue

        # Rule 4: Postfix
        days = (group.end_date.date() - group.start_date.date()).days + 1
        postfix = _get_postfix(days)
        
        # Rule 5: Date Format
        date_str = _format_date_range(group.start_date, group.end_date)
        
        # Assemble Name
        if is_korea:
            group.event_name = f"{date_str}_{location_name}_{postfix}"
        else:
            country_list = sorted(list(countries))
            if len(country_list) > 1:
                short_names = [c.split()[-1] for c in country_list]
                loc_part = "_".join(short_names)
            else:
                loc_part = country_list[0] if country_list else location_name
            
            group.event_name = f"{date_str}_{loc_part}_{postfix}"


def get_folder_name(group: PhotoGroup) -> str:
    """Generate final folder name for a group."""
    return group.folder_name
