"""
Centralized constants for the TC Dashboard.
"""

# =============================================================================
# TROPICAL CYCLONE TRACKER
# =============================================================================

TC_CATEGORY_THRESHOLDS = {
    "TL":   (0,   33),
    "Cat1": (34,  47),
    "Cat2": (48,  63),
    "Cat3": (64,  85),
    "Cat4": (86,  107),
    "Cat5": (108, 999),
}

TC_CATEGORY_COLORS = {
    "TL":   "#f0c300",
    "Cat1": "#22c55e",
    "Cat2": "#3b82f6",
    "Cat3": "#f59e0b",
    "Cat4": "#ef4444",
    "Cat5": "#9333ea",
}

TC_STATUS_COLORS = {
    "Tropical Low":              "#f0c300",
    "Tropical Cyclone":          "#ff4500",
    "Severe Tropical Cyclone":   "#8B0000",
}

TC_SYSTEM_COLORS = [
    "#4ECDC4",  # Teal
    "#FF6B6B",  # Coral red
    "#A8E6CF",  # Mint green
    "#FFD93D",  # Gold yellow
    "#6C5CE7",  # Purple
    "#00B894",  # Emerald
    "#FD79A8",  # Pink
    "#FDCB6E",  # Orange yellow
]

TC_THREAT_LEVELS = {
    "EXTREME":  {"max_km": 100,  "color": "#dc2626"},
    "HIGH":     {"max_km": 300,  "color": "#ef4444"},
    "MODERATE": {"max_km": 500,  "color": "#f59e0b"},
    "LOW":      {"max_km": 1000, "color": "#eab308"},
    "MINIMAL":  {"max_km": 9999, "color": "#22c55e"},
}

TC_MAJOR_LOCATIONS = [
    {"name": "Darwin",       "lat": -12.46, "lon": 130.84},
    {"name": "Broome",       "lat": -17.96, "lon": 122.23},
    {"name": "Port Hedland", "lat": -20.31, "lon": 118.58},
    {"name": "Karratha",     "lat": -20.74, "lon": 116.85},
    {"name": "Exmouth",      "lat": -21.93, "lon": 114.13},
    {"name": "Carnarvon",    "lat": -24.88, "lon": 113.66},
    {"name": "Geraldton",    "lat": -28.77, "lon": 114.62},
    {"name": "Perth",        "lat": -31.95, "lon": 115.86},
    {"name": "Cairns",       "lat": -16.92, "lon": 145.77},
    {"name": "Townsville",   "lat": -19.25, "lon": 146.82},
    {"name": "Mackay",       "lat": -21.14, "lon": 149.19},
    {"name": "Rockhampton",  "lat": -23.38, "lon": 150.51},
    {"name": "Bundaberg",    "lat": -24.87, "lon": 152.35},
    {"name": "Brisbane",     "lat": -27.47, "lon": 153.03},
]

TC_ICON_MAP = {
    "TL":   "/assets/icons/Tropical_Low.png",
    "Cat1": "/assets/icons/Aus_1_icon.png",
    "Cat2": "/assets/icons/Aus_2_icon.png",
    "Cat3": "/assets/icons/Aus_3_icon.png",
    "Cat4": "/assets/icons/Aus_4_icon.png",
    "Cat5": "/assets/icons/Aus_5_icon.png",
}

# =============================================================================
# TIMEZONE OPTIONS
# =============================================================================

TIMEZONE_OPTIONS = [
    {"label": "UTC", "value": "UTC"},
    {"label": "Australia/Brisbane (AEST)", "value": "Australia/Brisbane"},
    {"label": "Australia/Sydney (AEST/AEDT)", "value": "Australia/Sydney"},
    {"label": "Australia/Melbourne (AEST/AEDT)", "value": "Australia/Melbourne"},
    {"label": "Australia/Perth (AWST)", "value": "Australia/Perth"},
    {"label": "Australia/Adelaide (ACST/ACDT)", "value": "Australia/Adelaide"},
    {"label": "Australia/Darwin (ACST)", "value": "Australia/Darwin"},
    {"label": "Australia/Hobart (AEST/AEDT)", "value": "Australia/Hobart"},
]

# =============================================================================
# UI THEME TOKENS
# =============================================================================

THEME_COLORS = {
    "bg_primary": "#080c14",
    "bg_secondary": "#0d1320",
    "bg_panel": "#111827",
    "bg_panel_hover": "#1a2332",
    "border": "#1e293b",
    "border_active": "#f59e0b",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "accent": "#f59e0b",
    "accent_dim": "rgba(245,158,11,0.15)",
    "danger": "#ef4444",
    "success": "#22c55e",
    "info": "#3b82f6",
    "warning": "#f59e0b",
}

# Chart layout defaults (dark theme)
PLOTLY_LAYOUT_DEFAULTS = {
    "template": "plotly_dark",
    "paper_bgcolor": "#111827",
    "plot_bgcolor": "#0d1320",
    "font": {"family": "DM Sans, sans-serif", "color": "#f1f5f9", "size": 12},
    "margin": {"l": 50, "r": 30, "t": 40, "b": 80},
    "hovermode": "x unified",
    "legend": {
        "orientation": "h",
        "yanchor": "top",
        "y": -0.30,
        "xanchor": "left",
        "x": 0,
        "font": {"size": 10},
    },
}

# Map tile URLs
MAP_TILES = {
    "dark": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    "voyager": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    "esri-topo": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    "osm": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
}

MAP_TILE_OPTIONS = [
    {"label": "Dark", "value": "dark"},
    {"label": "Voyager", "value": "voyager"},
    {"label": "Esri Topo", "value": "esri-topo"},
    {"label": "OpenStreetMap", "value": "osm"},
]

# Australia center for default map view
AUSTRALIA_CENTER = [-15.0, 130.0]
AUSTRALIA_ZOOM = 5
