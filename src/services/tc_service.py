"""
Tropical Cyclone Tracker service.
Loads BoM TC advisory JSON files, extracts track/forecast data, and provides
analysis functions for location impacts and system summaries.
"""
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.utils.constants import (
    TC_CATEGORY_THRESHOLDS,
    TC_CATEGORY_COLORS,
    TC_MAJOR_LOCATIONS,
    TC_THREAT_LEVELS,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "tc_data"
CONFIG_DIR = BASE_DIR / "data" / "tc_config"

# In-memory cache
_systems_cache: Dict[str, dict] = {}
_advisories_index: Dict[str, List[dict]] = {}


# =============================================================================
# DATA LOADING
# =============================================================================


def _load_json(filepath: Path) -> Optional[dict]:
    """Load and parse a single TC JSON file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", filepath.name, e)
        return None


def load_all_systems() -> Tuple[Dict[str, dict], List[dict]]:
    """
    Scan data/tc_data/ for all JSON files.

    Returns:
        (systems_dict, dropdown_options)
    """
    global _systems_cache, _advisories_index

    if not DATA_DIR.exists():
        logger.warning("TC data directory not found: %s", DATA_DIR)
        return {}, []

    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        logger.warning("No TC JSON files found in %s", DATA_DIR)
        return {}, []

    systems: Dict[str, dict] = {}
    grouped: Dict[str, List[dict]] = defaultdict(list)

    for fp in json_files:
        data = _load_json(fp)
        if not data:
            continue
        data["_filename"] = fp.name
        systems[fp.stem] = data

        dist_id = data.get("disturbanceId", fp.stem)
        grouped[dist_id].append({
            "filename": fp.stem,
            "disturbanceId": dist_id,
            "issueTime": data.get("issueTime", ""),
            "cycloneFullName": data.get("cycloneFullName") or data.get("cycloneName") or dist_id,
            "cycloneStatus": data.get("cycloneStatus", ""),
            "finalIssue": data.get("finalIssue", False),
        })

    # Sort advisories within each system by issueTime (newest first)
    for dist_id in grouped:
        grouped[dist_id].sort(key=lambda a: a["issueTime"], reverse=True)

    _systems_cache = systems
    _advisories_index = dict(grouped)

    # Build dropdown options
    options = []
    for dist_id, advisories in sorted(grouped.items()):
        latest = advisories[0]
        label = latest["cycloneFullName"]
        if latest["finalIssue"]:
            label += " (Final)"
        options.append({"label": label, "value": dist_id})

    logger.info("Loaded %d TC files across %d systems", len(systems), len(grouped))
    return systems, options


def get_system_options() -> List[dict]:
    """Return dropdown options for system selection."""
    if not _advisories_index:
        load_all_systems()
    options = []
    for dist_id, advisories in sorted(_advisories_index.items()):
        latest = advisories[0]
        label = latest["cycloneFullName"]
        if latest["finalIssue"]:
            label += " (Final)"
        options.append({"label": label, "value": dist_id})
    return options


def get_advisories_for_system(disturbance_id: str) -> List[dict]:
    """Return all advisory files for a system, sorted newest first."""
    if not _advisories_index:
        load_all_systems()

    advisories = _advisories_index.get(disturbance_id, [])
    result = []
    for adv in advisories:
        try:
            dt = datetime.fromisoformat(adv["issueTime"].replace("Z", "+00:00"))
            label = dt.strftime("%d %b %H:%M UTC")
        except Exception:
            label = adv["issueTime"][:16] if adv["issueTime"] else adv["filename"]
        result.append({"label": label, "value": adv["filename"]})
    return result


def get_system_data(filename_stem: str) -> Optional[dict]:
    """Return parsed JSON for a specific advisory file."""
    if not _systems_cache:
        load_all_systems()
    return _systems_cache.get(filename_stem)


def get_latest_advisory(disturbance_id: str) -> Optional[dict]:
    """Return the latest advisory data for a system."""
    if not _advisories_index:
        load_all_systems()
    advisories = _advisories_index.get(disturbance_id, [])
    if not advisories:
        return None
    return get_system_data(advisories[0]["filename"])


def get_latest_advisory_filename(disturbance_id: str) -> Optional[str]:
    """Return the filename_stem of the latest advisory for a system."""
    if not _advisories_index:
        load_all_systems()
    advisories = _advisories_index.get(disturbance_id, [])
    return advisories[0]["filename"] if advisories else None


# =============================================================================
# DATA EXTRACTION
# =============================================================================


def determine_category(max_wind: Optional[float]) -> str:
    """Map maximum wind speed (kt) to Australian TC category."""
    if max_wind is None:
        return "TL"
    for cat, (low, high) in TC_CATEGORY_THRESHOLDS.items():
        if low <= max_wind <= high:
            return cat
    return "TL"


def extract_fix_points(data: dict) -> List[dict]:
    """Extract position history from fixData GeoJSON."""
    fix_data = data.get("fixData", {})
    features = fix_data.get("features", [])
    points = []

    for feat in features:
        geom = feat.get("geometry", {})
        props = feat.get("properties", {})
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]
        max_wind = props.get("maxMeanWind")
        category = determine_category(max_wind)

        points.append({
            "lat": lat,
            "lon": lon,
            "time": props.get("time", ""),
            "type": props.get("type", "Analysis"),
            "maxWind": max_wind,
            "maxGust": props.get("maxWindGust"),
            "pressure": props.get("centralPressure"),
            "category": category,
            "uncertainty": props.get("uncertainty"),
            "offsetHours": props.get("offsetFromReferenceTime"),
            "windRadiiGaleNW": props.get("windRadiiGaleNW"),
            "windRadiiGaleNE": props.get("windRadiiGaleNE"),
            "windRadiiGaleSW": props.get("windRadiiGaleSW"),
            "windRadiiGaleSE": props.get("windRadiiGaleSE"),
            "windRadiiStormNW": props.get("windRadiiStormNW"),
            "windRadiiStormNE": props.get("windRadiiStormNE"),
            "windRadiiStormSW": props.get("windRadiiStormSW"),
            "windRadiiStormSE": props.get("windRadiiStormSE"),
            "windRadiiHurricaneNW": props.get("windRadiiHurricaneNW"),
            "windRadiiHurricaneNE": props.get("windRadiiHurricaneNE"),
            "windRadiiHurricaneSW": props.get("windRadiiHurricaneSW"),
            "windRadiiHurricaneSE": props.get("windRadiiHurricaneSE"),
        })

    return points


def extract_summary(data: dict) -> dict:
    """Extract key system summary information."""
    fix_points = extract_fix_points(data)
    latest = fix_points[-1] if fix_points else {}
    analysis_points = [p for p in fix_points if p.get("type") == "Analysis"]
    latest_analysis = analysis_points[-1] if analysis_points else latest

    return {
        "name": data.get("cycloneFullName") or data.get("cycloneName") or "Unknown",
        "disturbanceId": data.get("disturbanceId", ""),
        "status": data.get("cycloneStatus", "Unknown"),
        "category": latest_analysis.get("category", "TL"),
        "maxWind": latest_analysis.get("maxWind"),
        "maxGust": latest_analysis.get("maxGust"),
        "pressure": latest_analysis.get("pressure"),
        "lat": latest_analysis.get("lat"),
        "lon": latest_analysis.get("lon"),
        "position_time": latest_analysis.get("time", ""),
        "issueTime": data.get("issueTime", ""),
        "nextIssueTime": data.get("nextIssueTime"),
        "finalIssue": data.get("finalIssue", False),
        "fixCount": len(fix_points),
        "analysisCount": len(analysis_points),
        "forecastCount": len(fix_points) - len(analysis_points),
    }


def extract_advisory_text(data: dict) -> dict:
    """Extract forecast text and discussion."""
    text = data.get("text", {})
    seven_day = text.get("sevenDayForecast", {})
    track = text.get("trackForecast", {})

    return {
        "sevenDay": {
            "headline": seven_day.get("headline"),
            "points": seven_day.get("points", []),
        },
        "track": {
            "headline": track.get("headline"),
            "discussion": track.get("discussion"),
            "upperBound": track.get("discussionUpperBound"),
        },
    }


def extract_probability_timeline(data: dict) -> List[dict]:
    """Extract TC development probability timeline."""
    raw = data.get("probabilityOfTcData", [])
    result = []
    for entry in raw:
        try:
            dt = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
            label = dt.strftime("%d %b %H:%M")
        except Exception:
            label = entry.get("time", "")[:16]
        result.append({
            "time": entry.get("time", ""),
            "label": label,
            "probability": entry.get("probabilityOfTc"),
            "rating": entry.get("probabilityOfTcRating", "None"),
        })
    return result


# =============================================================================
# GEOSPATIAL ANALYSIS
# =============================================================================


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two points."""
    R = 6371.0
    try:
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    except Exception:
        return float("inf")


def calculate_location_impacts(
    data: dict,
    extra_locations: Optional[List[dict]] = None,
) -> List[dict]:
    """
    Calculate distance from TC's latest analysis position to locations.
    Returns sorted list of impacts with threat level classification.
    """
    fix_points = extract_fix_points(data)
    analysis_pts = [p for p in fix_points if p.get("type") == "Analysis"]
    if not analysis_pts:
        return []

    latest = analysis_pts[-1]
    tc_lat, tc_lon = latest["lat"], latest["lon"]
    tc_cat = latest.get("category", "TL")

    locations = list(TC_MAJOR_LOCATIONS)
    if extra_locations:
        locations.extend(extra_locations)

    impacts = []
    for loc in locations:
        dist = haversine(tc_lat, tc_lon, loc["lat"], loc["lon"])

        # Determine threat level
        custom_thresh = loc.get(f"{tc_cat.lower()}_threshold") or loc.get("cat1_threshold")
        if custom_thresh:
            threat = "MINIMAL"
            if dist < custom_thresh * 0.33:
                threat = "EXTREME"
            elif dist < custom_thresh:
                threat = "HIGH"
            elif dist < custom_thresh * 1.67:
                threat = "MODERATE"
            elif dist < custom_thresh * 3.3:
                threat = "LOW"
        else:
            threat = "MINIMAL"
            for level, info in TC_THREAT_LEVELS.items():
                if dist < info["max_km"]:
                    threat = level
                    break

        impacts.append({
            "name": loc["name"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "distance_km": round(dist, 1),
            "threat": threat,
            "type": loc.get("type", "city"),
            "color": TC_THREAT_LEVELS.get(threat, TC_THREAT_LEVELS["MINIMAL"])["color"],
        })

    impacts.sort(key=lambda x: x["distance_km"])
    return impacts[:20]


def calculate_movement_speed(fix_points: List[dict]) -> List[dict]:
    """Calculate movement speed between consecutive analysis positions."""
    analysis = [p for p in fix_points if p.get("type") == "Analysis"]
    speeds = []

    for i in range(1, len(analysis)):
        prev, curr = analysis[i - 1], analysis[i]
        try:
            t1 = datetime.fromisoformat(prev["time"].replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(curr["time"].replace("Z", "+00:00"))
            hours = (t2 - t1).total_seconds() / 3600.0
            if hours <= 0:
                continue
            dist = haversine(prev["lat"], prev["lon"], curr["lat"], curr["lon"])
            speeds.append({
                "time": curr["time"],
                "distance_km": round(dist, 1),
                "hours": round(hours, 1),
                "speed_kmh": round(dist / hours, 1),
            })
        except Exception:
            continue

    return speeds


def compute_map_center_zoom(data: dict) -> Tuple[List[float], int]:
    """Compute optimal map center and zoom from fix points."""
    fix_points = extract_fix_points(data)
    if not fix_points:
        return [-15.0, 130.0], 5

    lats = [p["lat"] for p in fix_points]
    lons = [p["lon"] for p in fix_points]

    center = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]

    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)
    extent = max(lat_range, lon_range)

    if extent < 3:
        zoom = 7
    elif extent < 8:
        zoom = 6
    elif extent < 15:
        zoom = 5
    else:
        zoom = 4

    return center, zoom


def compute_map_center_zoom_multi(data_list: List[dict]) -> Tuple[List[float], int]:
    """Compute optimal map center and zoom across multiple TC systems."""
    all_lats: List[float] = []
    all_lons: List[float] = []
    for data in data_list:
        for p in extract_fix_points(data):
            all_lats.append(p["lat"])
            all_lons.append(p["lon"])

    if not all_lats:
        return [-15.0, 130.0], 5

    center = [(min(all_lats) + max(all_lats)) / 2, (min(all_lons) + max(all_lons)) / 2]
    extent = max(max(all_lats) - min(all_lats), max(all_lons) - min(all_lons))

    if extent < 3:
        zoom = 7
    elif extent < 8:
        zoom = 6
    elif extent < 15:
        zoom = 5
    else:
        zoom = 4

    return center, zoom


# =============================================================================
# GEOJSON BUILDERS
# =============================================================================


def build_track_geojson(data: dict) -> dict:
    """Build GeoJSON FeatureCollection with track line + point markers."""
    fix_points = extract_fix_points(data)
    if not fix_points:
        return {"type": "FeatureCollection", "features": []}

    features = []

    analysis_pts = [p for p in fix_points if p["type"] == "Analysis"]
    forecast_pts = [p for p in fix_points if p["type"] != "Analysis"]

    if len(analysis_pts) >= 2:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[p["lon"], p["lat"]] for p in analysis_pts],
            },
            "properties": {"lineType": "analysis"},
        })

    if forecast_pts and analysis_pts:
        connector = [analysis_pts[-1]] + forecast_pts
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[p["lon"], p["lat"]] for p in connector],
            },
            "properties": {"lineType": "forecast"},
        })

    for i, p in enumerate(fix_points):
        is_current = (
            p["type"] == "Analysis" and i == len(analysis_pts) - 1
        ) if analysis_pts else (i == len(fix_points) - 1)

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [p["lon"], p["lat"]],
            },
            "properties": {
                "time": p["time"],
                "type": p["type"],
                "category": p["category"],
                "maxWind": p["maxWind"],
                "pressure": p["pressure"],
                "isCurrent": is_current,
                "index": i,
            },
        })

    return {"type": "FeatureCollection", "features": features}


def get_forecast_cones(data: dict) -> Optional[dict]:
    """Return forecastConfidenceCones GeoJSON if it has features."""
    cones = data.get("forecastConfidenceCones", {})
    if cones.get("features"):
        return cones
    return None


def get_confidence_areas(data: dict) -> Optional[dict]:
    """Return forecastConfidenceAreas GeoJSON if it has features."""
    areas = data.get("forecastConfidenceAreas", {})
    if areas.get("features"):
        return areas
    return None


# =============================================================================
# CLIENT CONFIGURATION
# =============================================================================


def load_client_registry() -> List[dict]:
    """Load the client registry and return dropdown options."""
    registry_path = CONFIG_DIR / "users_registry.json"
    if not registry_path.exists():
        return []

    try:
        with open(registry_path, encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        logger.warning("Failed to load client registry: %s", e)
        return []

    options = [{"label": "None (Major Cities Only)", "value": "none"}]
    for user in registry.get("users", []):
        if not user.get("active", True):
            continue
        if user.get("is_super_user"):
            continue
        options.append({
            "label": user.get("display_name", user.get("username", "")),
            "value": user.get("config_file", ""),
        })
    return options


def load_client_locations(config_file: str) -> List[dict]:
    """Load a client's custom locations from their config file."""
    if not config_file or config_file == "none":
        return []

    config_path = CONFIG_DIR / config_file
    if not config_path.exists():
        logger.warning("Client config not found: %s", config_path)
        return []

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.warning("Failed to load client config %s: %s", config_file, e)
        return []

    return config.get("locations", [])


# =============================================================================
# OVERVIEW / ACTIVE SYSTEMS
# =============================================================================


def get_active_system_count() -> int:
    """Count non-final-issue systems."""
    if not _advisories_index:
        load_all_systems()
    count = 0
    for advisories in _advisories_index.values():
        if advisories and not advisories[0].get("finalIssue", True):
            count += 1
    return count


def get_active_alerts() -> List[dict]:
    """Return active systems that are Cat1+."""
    if not _advisories_index:
        load_all_systems()
    alerts = []
    for dist_id, advisories in _advisories_index.items():
        if not advisories or advisories[0].get("finalIssue", True):
            continue
        data = get_system_data(advisories[0]["filename"])
        if not data:
            continue
        summary = extract_summary(data)
        if summary["category"] != "TL":
            alerts.append(summary)
    return alerts


# =============================================================================
# BEARING & TIMEZONE
# =============================================================================


def calculate_bearing(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> Tuple[Optional[float], Optional[str]]:
    """Calculate bearing between two points. Returns (degrees, cardinal)."""
    try:
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlon_r = math.radians(lon2 - lon1)

        x = math.sin(dlon_r) * math.cos(lat2_r)
        y = (
            math.cos(lat1_r) * math.sin(lat2_r)
            - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r)
        )
        bearing = (math.degrees(math.atan2(x, y)) + 360) % 360

        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
        ]
        cardinal = directions[round(bearing / 22.5) % 16]
        return bearing, cardinal
    except Exception:
        return None, None


def get_australian_timezone(lon: Optional[float], lat: Optional[float]) -> dict:
    """Determine Australian timezone from longitude."""
    if lon is None or lat is None:
        return {"name": "Australian Western Standard Time", "abbrev": "AWST",
                "offset_hours": 8, "offset_minutes": 0}
    if lon < 129.0:
        return {"name": "Australian Western Standard Time", "abbrev": "AWST",
                "offset_hours": 8, "offset_minutes": 0}
    elif lon < 141.0:
        return {"name": "Australian Central Standard Time", "abbrev": "ACST",
                "offset_hours": 9, "offset_minutes": 30}
    else:
        return {"name": "Australian Eastern Standard Time", "abbrev": "AEST",
                "offset_hours": 10, "offset_minutes": 0}


def convert_utc_to_local(
    utc_time_str: str, lon: Optional[float], lat: Optional[float]
) -> dict:
    """Convert UTC ISO time string to local Australian time based on longitude."""
    if not utc_time_str:
        return {"formatted": "Unknown", "timezone": "N/A", "raw": None}
    try:
        utc_dt = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
        tz = get_australian_timezone(lon, lat)
        offset = timedelta(hours=tz["offset_hours"], minutes=tz["offset_minutes"])
        local_dt = utc_dt + offset
        return {
            "formatted": local_dt.strftime("%d %b %Y, %I:%M %p"),
            "timezone": tz["abbrev"],
            "timezone_name": tz["name"],
            "raw": local_dt,
            "date_only": local_dt.strftime("%d %b %Y"),
            "time_only": local_dt.strftime("%I:%M %p"),
            "datetime_short": local_dt.strftime("%d/%m %I:%M %p"),
        }
    except Exception as e:
        logger.warning("Error converting time %s: %s", utc_time_str, e)
        return {"formatted": utc_time_str, "timezone": "UTC", "raw": None}


# =============================================================================
# FORECAST TIMELINE
# =============================================================================


def _get_cyclone_category_number(fix_point: dict) -> int:
    """Extract numeric category from a fix point."""
    cat = fix_point.get("category", "TL")
    if cat == "TL":
        return 0
    try:
        return int("".join(filter(str.isdigit, cat)))
    except ValueError:
        return 1


def calculate_forecast_timeline(
    data: dict,
    location_name: str,
    location_lat: float,
    location_lon: float,
    location_config: Optional[dict] = None,
) -> Optional[dict]:
    """Calculate when a location enters/exits threat ranges along the forecast track."""
    fix_points = extract_fix_points(data)
    if not fix_points:
        return None

    analysis_pts = [p for p in fix_points if p.get("type") == "Analysis"]
    current_fix = analysis_pts[-1] if analysis_pts else fix_points[0]

    current_distance = haversine(
        current_fix["lat"], current_fix["lon"], location_lat, location_lon
    )

    def _threshold_for_category(cat_num: int) -> float:
        if location_config:
            key_map = {5: "cat5_threshold", 4: "cat4_threshold",
                       3: "cat3_threshold", 2: "cat2_threshold",
                       1: "cat1_threshold", 0: "cat1_threshold"}
            return location_config.get(key_map.get(cat_num, "cat1_threshold"),
                                       500 if cat_num >= 3 else 300)
        return 500 if cat_num >= 3 else 300

    def _threat_level(dist: float, fix: dict) -> str:
        threshold = _threshold_for_category(_get_cyclone_category_number(fix))
        if dist < threshold * 0.2:
            return "EXTREME"
        if dist < threshold * 0.4:
            return "HIGH"
        if dist < threshold * 0.7:
            return "MODERATE"
        if dist < threshold:
            return "LOW"
        return "MINIMAL"

    current_threat = _threat_level(current_distance, current_fix)

    forecast_positions = [f for f in fix_points if f.get("type") == "Forecast"]
    if not forecast_positions:
        return {
            "current_distance": current_distance,
            "current_threat": current_threat,
            "forecast_events": [],
            "min_distance": None,
            "has_forecast": False,
        }

    events = []
    min_dist = current_distance
    min_dist_time = current_fix["time"]
    min_dist_fix = current_fix
    last_threat = current_threat

    for fix in forecast_positions:
        dist = haversine(fix["lat"], fix["lon"], location_lat, location_lon)
        threat = _threat_level(dist, fix)

        if dist < min_dist:
            min_dist = dist
            min_dist_time = fix["time"]
            min_dist_fix = fix

        if threat != last_threat:
            events.append({
                "time": fix["time"],
                "threat": threat,
                "from_threat": last_threat,
                "distance": dist,
                "wind": fix.get("maxWind"),
                "category": fix.get("category", "TL"),
                "lon": fix.get("lon"),
                "lat": fix.get("lat"),
            })
            last_threat = threat

    return {
        "current_distance": current_distance,
        "current_threat": current_threat,
        "forecast_events": events,
        "min_distance": {
            "distance": min_dist,
            "time": min_dist_time,
            "threat": _threat_level(min_dist, min_dist_fix),
            "wind": min_dist_fix.get("maxWind"),
            "category": min_dist_fix.get("category", "TL"),
            "lon": min_dist_fix.get("lon"),
            "lat": min_dist_fix.get("lat"),
        },
        "has_forecast": True,
    }


# =============================================================================
# GALE ARRIVAL TIME
# =============================================================================

NM_TO_KM = 1.852


def _max_gale_radius_km(fix_point: dict) -> float:
    """Return the maximum gale-force wind radius (km) from all four quadrants.

    Radii in the JSON are in nautical miles; convert to km.
    Returns 0.0 if no gale radii are present.
    """
    vals = [
        fix_point.get(f"windRadiiGale{q}")
        for q in ("NW", "NE", "SW", "SE")
    ]
    valid = [v for v in vals if v is not None and v > 0]
    return max(valid) * NM_TO_KM if valid else 0.0


def _outermost_range_ring_km(location: dict) -> float:
    """Return the outermost range ring (km) for a location, or 0.0 if none."""
    rings = location.get("range_rings", [])
    return max(rings) if rings else 0.0


def calculate_gale_arrival(
    data: dict,
    location_lat: float,
    location_lon: float,
    range_ring_km: float = 0.0,
) -> Optional[dict]:
    """Estimate when TC gale-force winds will reach a location's trigger boundary.

    The trigger boundary is the outermost range ring of the location (or the
    location itself when no range rings are defined).  Gales "arrive" when::

        distance(TC, location) - max_gale_radius(TC) <= range_ring_km

    If arrival falls between two forecast positions, a linear interpolation
    produces a best-estimate time, with both bounding official forecast times
    reported alongside it.

    Returns
    -------
    dict or None
        None if gales are never forecast to reach the trigger boundary.
        Otherwise a dict with keys:
        - ``arrival_utc``: ISO datetime string of estimated arrival
        - ``interpolated``: bool — True if the time is interpolated
        - ``bracket_before_utc``: ISO time of the forecast step before arrival
        - ``bracket_after_utc``: ISO time of the forecast step at/after arrival
        - ``already_inside``: bool — True if gales are already within boundary
    """
    fix_points = extract_fix_points(data)
    if not fix_points:
        return None

    # Build timeline of (datetime, gap_km) where gap = dist - gale_radius - ring
    timeline: List[Tuple[datetime, float, dict]] = []
    for fp in fix_points:
        gale_r = _max_gale_radius_km(fp)
        dist = haversine(fp["lat"], fp["lon"], location_lat, location_lon)
        gap = dist - gale_r - range_ring_km
        try:
            dt = datetime.fromisoformat(fp["time"].replace("Z", "+00:00"))
        except Exception:
            continue
        timeline.append((dt, gap, fp))

    if not timeline:
        return None

    # Check if gales are already inside at the first (current) position
    if timeline[0][1] <= 0:
        return {
            "arrival_utc": timeline[0][2]["time"],
            "interpolated": False,
            "bracket_before_utc": timeline[0][2]["time"],
            "bracket_after_utc": timeline[0][2]["time"],
            "already_inside": True,
        }

    # Walk forward through the timeline looking for the first crossing
    for i in range(1, len(timeline)):
        prev_dt, prev_gap, prev_fp = timeline[i - 1]
        curr_dt, curr_gap, curr_fp = timeline[i]

        if curr_gap <= 0:
            # Gales have reached the boundary at or before this step
            if prev_gap <= 0:
                # Already inside at previous step too — shouldn't happen
                # given the check above, but handle gracefully
                arrival_dt = curr_dt
                interpolated = False
            else:
                # Interpolate: find the fraction between prev and curr
                # where gap crosses zero
                total_change = prev_gap - curr_gap  # positive (gap is decreasing)
                if total_change > 0:
                    frac = prev_gap / total_change
                    delta = (curr_dt - prev_dt) * frac
                    arrival_dt = prev_dt + delta
                    interpolated = True
                else:
                    arrival_dt = curr_dt
                    interpolated = False

            return {
                "arrival_utc": arrival_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "interpolated": interpolated,
                "bracket_before_utc": prev_fp["time"],
                "bracket_after_utc": curr_fp["time"],
                "already_inside": False,
            }

    # Gales never reach the trigger boundary in the forecast period
    return None


def calculate_gale_arrivals_for_impacts(
    data: dict,
    impacts: List[dict],
    client_locations: List[dict],
) -> List[dict]:
    """Enrich a list of location impacts with gale arrival information.

    Matches each impact to its client location config (if any) to find the
    outermost range ring.  Mutates nothing — returns a new list of dicts
    with an extra ``gale_arrival`` key added to each impact.
    """
    # Build a quick lookup: location name → client config
    client_lookup: Dict[str, dict] = {}
    for loc in client_locations:
        client_lookup[loc["name"]] = loc

    enriched = []
    for imp in impacts:
        loc_config = client_lookup.get(imp["name"], {})
        ring_km = _outermost_range_ring_km(loc_config)

        arrival = calculate_gale_arrival(
            data,
            imp["lat"],
            imp["lon"],
            range_ring_km=ring_km,
        )

        enriched.append({
            **imp,
            "gale_arrival": arrival,
            "range_ring_km": ring_km,
        })

    return enriched


# =============================================================================
# CONFIDENCE AREA TIME FILTERING
# =============================================================================


def get_confidence_area_times(data: dict) -> List[dict]:
    """Extract unique time steps from forecastConfidenceAreas."""
    areas = data.get("forecastConfidenceAreas", {})
    features = areas.get("features", [])
    ref_time_str = data.get("referenceTime")
    if not features or not ref_time_str:
        return []

    try:
        ref_dt = datetime.fromisoformat(ref_time_str.replace("Z", "+00:00"))
    except Exception:
        return []

    seen = set()
    steps = []
    for feat in features:
        t = feat.get("properties", {}).get("time")
        if not t or t in seen:
            continue
        seen.add(t)
        try:
            feat_dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            offset_h = (feat_dt - ref_dt).total_seconds() / 3600.0
            day_label = feat_dt.strftime("%a %d %b, %H:%M UTC")
            steps.append({
                "time": t,
                "label": f"{day_label} (+{int(offset_h)}h)",
                "offset_hours": offset_h,
            })
        except Exception:
            continue

    steps.sort(key=lambda s: s["offset_hours"])
    return steps


def filter_confidence_areas_by_time(
    areas_geojson: Optional[dict],
    reference_time: str,
    offset_hours: float,
    window_hours: float = 3.0,
) -> Optional[dict]:
    """Filter forecastConfidenceAreas features to those within window_hours."""
    if not areas_geojson or not areas_geojson.get("features"):
        return None
    try:
        ref_dt = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
    except Exception:
        return None

    target_dt = ref_dt + timedelta(hours=offset_hours)
    window = timedelta(hours=window_hours)
    matched = []

    for feat in areas_geojson["features"]:
        t = feat.get("properties", {}).get("time")
        if not t:
            continue
        try:
            feat_dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            if abs((feat_dt - target_dt).total_seconds()) <= window.total_seconds():
                matched.append(feat)
        except Exception:
            continue

    if not matched:
        return None
    return {"type": "FeatureCollection", "features": matched}


def get_confidence_area_style(confidence_level: Optional[float]) -> dict:
    """Return dash-leaflet style dict for an outlook confidence area."""
    if confidence_level is None:
        confidence_level = 0
    if confidence_level > 50:
        return {"color": "#8B4513", "fillColor": "#A0522D", "fillOpacity": 0.4, "weight": 2}
    if confidence_level >= 20:
        return {"color": "#FF8C00", "fillColor": "#FFA500", "fillOpacity": 0.35, "weight": 2}
    if confidence_level >= 5:
        return {"color": "#FFD700", "fillColor": "#FFED4E", "fillOpacity": 0.3, "weight": 2}
    return {"color": "#FFFFE0", "fillColor": "#FFFACD", "fillOpacity": 0.25, "weight": 2}


# =============================================================================
# ARCHIVE ADVISORY CHECK
# =============================================================================


def get_recent_and_archived_options(max_recent: int = 10) -> Tuple[List[dict], List[dict]]:
    """Categorise systems into recent and archived."""
    if not _advisories_index:
        load_all_systems()

    system_times: List[Tuple[str, str, datetime]] = []
    for dist_id, advisories in _advisories_index.items():
        if not advisories:
            continue
        latest = advisories[0]
        try:
            dt = datetime.fromisoformat(latest["issueTime"].replace("Z", "+00:00"))
        except Exception:
            dt = datetime.min
        system_times.append((dist_id, latest["filename"], dt))

    system_times.sort(key=lambda x: x[2], reverse=True)

    recent_options: List[dict] = []
    archived_options: List[dict] = []

    for idx, (dist_id, latest_file, _dt) in enumerate(system_times):
        latest_adv = _advisories_index[dist_id][0]
        label = latest_adv["cycloneFullName"]
        if latest_adv.get("finalIssue"):
            label += " (Final)"

        if idx < max_recent:
            recent_options.append({"label": label, "value": dist_id})
        else:
            try:
                dt = datetime.fromisoformat(latest_adv["issueTime"].replace("Z", "+00:00"))
                label += f" ({dt.strftime('%d %b %Y %H:%M')})"
            except Exception:
                pass
            archived_options.append({"label": label, "value": dist_id})

    return recent_options, archived_options


def is_latest_advisory(filename_stem: str) -> bool:
    """Return True if filename_stem is the newest advisory for its system."""
    if not _advisories_index:
        load_all_systems()

    data = _systems_cache.get(filename_stem)
    if not data:
        return True

    dist_id = data.get("disturbanceId", "")
    advisories = _advisories_index.get(dist_id, [])
    if not advisories:
        return True
    return advisories[0]["filename"] == filename_stem
