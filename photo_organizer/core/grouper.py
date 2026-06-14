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
    핵심:
    - 그룹 내에 해외 GPS가 하나라도 있으면, 그 그룹은 해외 여행.
    - 해외 여행 그룹은 72시간 gap까지 허용.
    - 한국 GPS만 있는 그룹은 18시간 gap.
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
    overseas_countries = set()
    has_overseas_gps = False  # 이 그룹에 해외 GPS가 있는지

    for photo in dated_photos:
        is_overseas_gps = False
        current_country = None

        if photo.gps_lat and photo.gps_lon:
            info = get_cached_location(photo.gps_lat, photo.gps_lon)
            if info:
                country = info.get("country")
                if country != "South Korea" and country != "대한민국":
                    is_overseas_gps = True
                    current_country = country

        # 해외 국가 수집
        if is_overseas_gps and current_country:
            overseas_countries.add(current_country)

        if last_date is None:
            current_group.add_photo(photo)
            last_date = photo.date_taken
            if is_overseas_gps:
                has_overseas_gps = True
        else:
            gap = photo.date_taken - last_date
            gap_hours = gap.total_seconds() / 3600.0

            # 허용 간격 결정
            if has_overseas_gps:
                allowed = 72
            else:
                allowed = time_gap_hours

            if gap_hours <= allowed:
                current_group.add_photo(photo)
                if is_overseas_gps:
                    has_overseas_gps = True
            else:
                # 그룹 종료
                if current_group.photos:
                    current_group.overseas_countries = overseas_countries
                    groups.append(current_group)
                current_group = PhotoGroup(photos=[photo])
                overseas_countries = set()
                has_overseas_gps = is_overseas_gps
                if current_country:
                    overseas_countries.add(current_country)

            last_date = photo.date_taken

    if current_group.photos:
        current_group.overseas_countries = overseas_countries
        groups.append(current_group)

    return groups


# --- New Naming Logic ---

HOME_DONGS = {"유천동", "대천동", "진천동", "월성동", "상인동"} # Daegu home area


def _get_postfix(days: int, is_overseas: bool = False) -> str:
    if days >= 3 or is_overseas:
        return "여행"
    elif days == 2:
        return "나들이"
    else:
        return "구경"


def _format_date_range(start: datetime, end: datetime) -> str:
    """Format date range based on requirements.
    
    Rules:
    - Same day: 20190628
    - Multi-day, same month: 20190628_29
    - Month crosses: 20190628_0705
    - Year crosses: 20190628_20200101
    """
    if start.date() == end.date():
        return start.strftime("%Y%m%d")
    
    start_str = start.strftime("%Y%m%d")
    
    if start.year != end.year:
        end_str = end.strftime("%Y%m%d")
    elif start.month != end.month:
        end_str = end.strftime("%m%d")
    else:
        # Same month: use month+day (e.g., 0706)
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
        
        # group_photos_by_time()에서 수집한 해외 국가를 우선 사용
        countries = group.overseas_countries.copy() if group.overseas_countries else set()
        
        for photo in gps_photos:
            info = get_cached_location(photo.gps_lat, photo.gps_lon)
            if not info: continue
            
            if info.get("country"):
                countries.add(info["country"])
        
        # 해외 국가가 있으면: 한국 지역(district/city)은 무시하고 해외 국가만 사용
        overseas_in_countries = [c for c in countries if c != "South Korea" and c != "대한민국"]
        if overseas_in_countries:
            is_korea = False
            location_name = overseas_in_countries[0]
        else:
            # 한국만 있는 경우에만 한국 지역 사용
            for photo in gps_photos:
                info = get_cached_location(photo.gps_lat, photo.gps_lon)
                if not info: continue
                
                if info.get("district") in HOME_DONGS:
                    group.event_name = None
                    continue 
                
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
        is_overseas = len(countries) > 0 or not is_korea
        postfix = _get_postfix(days, is_overseas)
        
        # Rule 5: Date Format (항상 전체 날짜: 20190628_0706)
        start_str = group.start_date.strftime("%Y%m%d")
        end_str = group.end_date.strftime("%m%d") if group.start_date.month == group.end_date.month else group.end_date.strftime("%m%d")
        if group.start_date.year != group.end_date.year:
            end_str = group.end_date.strftime("%Y%m%d")
        date_str = f"{start_str}_{end_str}"
        
        # Assemble Name
        if is_korea:
            group.event_name = f"{date_str}_{location_name}_{postfix}"
        else:
            # 다중 국가 지원: 한국은 제외하고 해외 국가만 _로 연결
            overseas_only = [c for c in countries if c != "South Korea" and c != "대한민국"]
            country_list = sorted(overseas_only)
            if len(country_list) > 1:
                short_names = [c.split()[-1] for c in country_list]
                loc_part = "_".join(short_names)
            else:
                loc_part = country_list[0] if country_list else location_name
            
            group.event_name = f"{date_str}_{loc_part}_{postfix}"


def get_folder_name(group: PhotoGroup) -> str:
    """Generate final folder name for a group."""
    return group.folder_name
