"""
dash-leaflet map builder for TC track visualization.
"""
import dash_leaflet as dl
from dash import html

from src.utils.constants import (
    MAP_TILES,
    TC_CATEGORY_COLORS,
)


def _tile_layer(style: str = "dark"):
    """Return a tile layer for the given style key."""
    url = MAP_TILES.get(style, MAP_TILES["dark"])
    return dl.TileLayer(
        url=url,
        attribution='&copy; <a href="https://carto.com/">CARTO</a>',
    )


def create_cyclone_track_map(
    systems: list = None,
    client_locations: list = None,
    location_impacts: list = None,
    show_track: bool = True,
    show_cones: bool = True,
    show_areas: bool = False,
    show_danger_zone: bool = False,
    show_wind_radii: bool = False,
    center: list = None,
    zoom: int = 5,
    map_id: str = "cyclone-track-map",
    height: str = "clamp(300px, 55vh, 550px)",
    tile_style: str = "dark",
    # Legacy single-system params
    track_geojson: dict = None,
    forecast_cones: dict = None,
    confidence_areas: dict = None,
    tc_current_position: dict = None,
    wind_radii_data: dict = None,
    system_name: str = "System",
) -> dl.Map:
    """
    Create a dash-leaflet TC track map with overlays.

    Supports multi-system display via the ``systems`` parameter.
    """
    # Normalise to systems list
    if systems is None:
        systems = [{
            "track_geojson": track_geojson,
            "forecast_cones": forecast_cones,
            "confidence_areas": confidence_areas,
            "tc_current_position": tc_current_position,
            "wind_radii_data": wind_radii_data,
            "system_name": system_name,
            "system_color": "#e2e8f0",
        }]

    if center is None:
        center = [-15.0, 130.0]

    multi = len(systems) > 1
    children = [_tile_layer(tile_style)]

    # Per-system layers
    for sys in systems:
        s_track = sys.get("track_geojson")
        s_cones = sys.get("forecast_cones")
        s_areas = sys.get("confidence_areas")
        s_pos = sys.get("tc_current_position")
        s_wind = sys.get("wind_radii_data")
        s_name = sys.get("system_name", "System")
        s_color = sys.get("system_color", "#e2e8f0")

        # Confidence areas
        if show_areas and s_areas and s_areas.get("features"):
            children.append(
                dl.GeoJSON(
                    data=s_areas,
                    options=dict(
                        style=dict(
                            color="#ef4444",
                            weight=1,
                            fillColor="#ef4444",
                            fillOpacity=0.08,
                            opacity=0.3,
                        )
                    ),
                )
            )

        # Forecast cones
        if show_cones and s_cones and s_cones.get("features"):
            for feat in s_cones["features"]:
                conf = feat.get("properties", {}).get("confidenceLevel", 70)
                if conf >= 70:
                    cone_color, fill_opacity = "#f59e0b", 0.15
                else:
                    cone_color, fill_opacity = "#ef4444", 0.10

                children.append(
                    dl.GeoJSON(
                        data={"type": "FeatureCollection", "features": [feat]},
                        options=dict(
                            style=dict(
                                color=cone_color,
                                weight=2,
                                fillColor=cone_color,
                                fillOpacity=fill_opacity,
                                dashArray="5 5",
                            )
                        ),
                    )
                )

        # Track lines and markers
        if show_track and s_track and s_track.get("features"):
            lines = [f for f in s_track["features"] if f["geometry"]["type"] == "LineString"]
            points = [f for f in s_track["features"] if f["geometry"]["type"] == "Point"]

            for line_feat in lines:
                line_type = line_feat.get("properties", {}).get("lineType", "analysis")
                coords = line_feat["geometry"]["coordinates"]
                positions = [[c[1], c[0]] for c in coords]

                if line_type == "forecast":
                    children.append(
                        dl.Polyline(
                            positions=positions,
                            pathOptions=dict(
                                color=s_color if multi else "#94a3b8",
                                weight=2,
                                opacity=0.4 if multi else 0.6,
                                dashArray="8 6",
                            ),
                        )
                    )
                else:
                    children.append(
                        dl.Polyline(
                            positions=positions,
                            pathOptions=dict(
                                color=s_color if multi else "#e2e8f0",
                                weight=2.5,
                                opacity=0.8,
                            ),
                        )
                    )

            # Point markers
            markers = []
            for feat in points:
                props = feat.get("properties", {})
                coords = feat["geometry"]["coordinates"]
                lat, lon = coords[1], coords[0]
                cat = props.get("category", "TL")
                is_current = props.get("isCurrent", False)
                is_forecast = props.get("type") != "Analysis"
                color = TC_CATEGORY_COLORS.get(cat, "#888888")

                radius = 10 if is_current else 5
                fill_opacity = 0.5 if is_forecast else 0.9
                weight = 3 if is_current else 1
                border_color = "#ffffff" if is_current else color

                time_str = props.get("time", "")[:16].replace("T", " ")
                wind_str = f"{props['maxWind']:.0f} kt" if props.get("maxWind") else "N/A"
                press_str = f"{props['pressure']:.0f} hPa" if props.get("pressure") else ""
                prefix = f"{s_name} | " if multi else ""
                tip_text = f"{prefix}{time_str} | {cat} | {wind_str}"
                if press_str:
                    tip_text += f" | {press_str}"
                if is_forecast:
                    tip_text += " (Forecast)"

                markers.append(
                    dl.CircleMarker(
                        center=[lat, lon],
                        radius=radius,
                        color=border_color,
                        fillColor=color,
                        fillOpacity=fill_opacity,
                        weight=weight,
                        children=dl.Tooltip(tip_text),
                    )
                )

            if markers:
                children.append(dl.LayerGroup(children=markers))

        # 250km Danger Zone circle
        if show_danger_zone and s_pos:
            tc_lat = s_pos.get("lat")
            tc_lon = s_pos.get("lon")
            if tc_lat is not None and tc_lon is not None:
                children.append(
                    dl.Circle(
                        center=[tc_lat, tc_lon],
                        radius=250_000,
                        pathOptions=dict(
                            color="#FF1493",
                            fillColor="#FF69B4",
                            fillOpacity=0.12,
                            weight=2,
                            dashArray="10 10",
                        ),
                        children=dl.Tooltip(f"250 km Danger Zone — {s_name}"),
                    )
                )

        # Wind radii circles
        if show_wind_radii and s_wind and s_pos:
            tc_lat = s_pos.get("lat")
            tc_lon = s_pos.get("lon")
            if tc_lat is not None and tc_lon is not None:
                _wind_types = [
                    ("gale",      "#F7B32B", "Gale Force (34-47 kt)",    2),
                    ("storm",     "#FF6B35", "Storm Force (48-63 kt)",   2),
                    ("hurricane", "#9B1C31", "Hurricane Force (>64 kt)", 3),
                ]
                for wtype, wcolor, label, wweight in _wind_types:
                    radii = s_wind.get(wtype, {})
                    valid = [v for v in radii.values() if v is not None and v > 0]
                    if valid:
                        max_nm = max(valid)
                        max_km = max_nm * 1.852
                        children.append(
                            dl.Circle(
                                center=[tc_lat, tc_lon],
                                radius=max_km * 1000,
                                pathOptions=dict(
                                    color=wcolor,
                                    fillColor=wcolor,
                                    fillOpacity=0.10,
                                    weight=wweight,
                                    dashArray="5 5",
                                ),
                                children=dl.Tooltip(
                                    f"{s_name} — {label}: {max_nm:.0f} nm ({max_km:.0f} km)"
                                ),
                            )
                        )

    # Shared layers — client locations with range rings
    if client_locations:
        loc_markers = []
        for loc in client_locations:
            lat, lon = loc.get("lat"), loc.get("lon")
            if lat is None or lon is None:
                continue

            is_offshore = loc.get("type") == "offshore"
            color = "#06b6d4" if is_offshore else "#a78bfa"

            loc_markers.append(
                dl.CircleMarker(
                    center=[lat, lon],
                    radius=7,
                    color=color,
                    fillColor=color,
                    fillOpacity=0.8,
                    weight=2,
                    children=dl.Tooltip(
                        f"{loc['name']} ({'Offshore' if is_offshore else 'Onshore'})"
                    ),
                )
            )

            for ring_km in loc.get("range_rings", []):
                loc_markers.append(
                    dl.Circle(
                        center=[lat, lon],
                        radius=ring_km * 1000,
                        pathOptions=dict(
                            color=color, weight=1, opacity=0.4,
                            fillColor=color, fillOpacity=0.03,
                            dashArray="4 4",
                        ),
                        children=dl.Tooltip(f"{loc['name']} — {ring_km:.0f} km ring"),
                    )
                )

        if loc_markers:
            children.append(dl.LayerGroup(children=loc_markers))

    # Major location markers with distance labels
    if location_impacts:
        _threat_colors = {
            "EXTREME": "#dc2626", "HIGH": "#ef4444",
            "MODERATE": "#f59e0b", "LOW": "#eab308", "MINIMAL": "#22c55e",
        }
        city_markers = []
        for imp in location_impacts:
            lat, lon = imp.get("lat"), imp.get("lon")
            if lat is None or lon is None:
                continue
            threat = imp.get("threat", "MINIMAL")
            color = _threat_colors.get(threat, "#22c55e")
            dist_km = imp.get("distance_km", 0)
            loc_type = imp.get("type", "city")

            marker_radius = 5 if loc_type == "city" else 6

            city_markers.append(
                dl.CircleMarker(
                    center=[lat, lon],
                    radius=marker_radius,
                    color="#ffffff",
                    fillColor=color,
                    fillOpacity=0.9,
                    weight=1.5,
                    children=dl.Tooltip(
                        f"{imp['name']} — {dist_km:.0f} km ({threat})",
                    ),
                )
            )

            city_markers.append(
                dl.Marker(
                    position=[lat, lon],
                    icon=dict(
                        iconUrl="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
                        iconSize=[1, 1],
                        iconAnchor=[0, 0],
                    ),
                    children=dl.Tooltip(
                        imp["name"],
                        permanent=True,
                        direction="right",
                        offset=[8, -2],
                        className="city-name-label",
                    ),
                )
            )
        if city_markers:
            children.append(dl.LayerGroup(children=city_markers))

    # Legend
    legend_items = []

    if multi:
        for sys in systems:
            legend_items.append(
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "4px"},
                    children=[
                        html.Div(style={
                            "width": "16px", "height": "3px",
                            "backgroundColor": sys.get("system_color", "#e2e8f0"),
                        }),
                        html.Span(
                            sys.get("system_name", ""),
                            style={"fontSize": "11px", "color": "#cbd5e1"},
                        ),
                    ],
                )
            )
        legend_items.append(
            html.Hr(style={"border": "none", "borderTop": "1px solid #334155", "margin": "4px 0"}),
        )

    for cat, color in TC_CATEGORY_COLORS.items():
        legend_items.append(
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "4px"},
                children=[
                    html.Div(style={
                        "width": "10px", "height": "10px",
                        "borderRadius": "50%", "backgroundColor": color,
                    }),
                    html.Span(cat, style={"fontSize": "11px", "color": "#cbd5e1"}),
                ],
            )
        )

    legend = html.Div(
        style={
            "position": "absolute", "bottom": "20px", "left": "10px",
            "zIndex": 1000, "backgroundColor": "rgba(17,24,39,0.85)",
            "padding": "8px 10px", "borderRadius": "6px",
            "border": "1px solid #1e293b",
        },
        children=[
            html.Div("TC Category", style={
                "fontSize": "10px", "fontWeight": 600, "color": "#94a3b8",
                "marginBottom": "4px", "textTransform": "uppercase",
            }),
            *legend_items,
        ],
    )

    return html.Div(
        style={"position": "relative"},
        children=[
            dl.Map(
                id=map_id,
                center=center,
                zoom=zoom,
                style={"height": height, "borderRadius": "8px"},
                children=children,
            ),
            legend,
        ],
    )
