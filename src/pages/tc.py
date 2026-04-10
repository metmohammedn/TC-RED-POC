"""
Tropical Cyclone Tracker page — standalone version.
No auth, no sidebar, registered at root path.
"""
import logging
from datetime import datetime

import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx, ALL
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.utils.constants import (
    TC_CATEGORY_COLORS,
    TC_SYSTEM_COLORS,
    TC_THREAT_LEVELS,
    TIMEZONE_OPTIONS,
    MAP_TILE_OPTIONS,
)

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/",
    name="TC Dashboard",
    title="TC Dashboard",
)

_INPUT_STYLE = {
    "input": {"backgroundColor": "#0d1320", "border": "1px solid #1e293b"},
}
_COMBOBOX_PORTAL = {"withinPortal": True, "zIndex": 1000}


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _threat_badge(threat: str) -> dmc.Badge:
    color_map = {
        "EXTREME": "red",
        "HIGH": "orange",
        "MODERATE": "yellow",
        "LOW": "lime",
        "MINIMAL": "green",
    }
    return dmc.Badge(
        threat,
        color=color_map.get(threat, "gray"),
        variant="filled",
        size="sm",
    )


def _category_badge(category: str) -> dmc.Badge:
    color_hex = TC_CATEGORY_COLORS.get(category, "#888")
    return dmc.Badge(
        category,
        size="lg",
        variant="filled",
        style={"backgroundColor": color_hex, "color": "#fff"},
    )


def _gale_arrival_section(impact: dict, issue_time_utc: str = "") -> list:
    """Build gale arrival display elements for a location card."""
    ga = impact.get("gale_arrival")
    ring_km = impact.get("range_ring_km", 0)

    if ga is None:
        return [dmc.Text("Gales: not forecast to reach", size="xs", c="#64748b", fs="italic")]

    from src.services.tc_service import convert_utc_to_local

    if ga.get("already_inside"):
        return [
            dmc.Divider(color="dark.5", my=4),
            dmc.Badge("GALES ALREADY WITHIN RANGE", color="red", variant="filled", size="xs"),
            *(
                [dmc.Text(f"at {ring_km:.0f} km range ring", size="xs", c="#94a3b8")]
                if ring_km > 0 else []
            ),
        ]

    local = convert_utc_to_local(ga["arrival_utc"], impact.get("lon"), impact.get("lat"))
    arrival_str = f"{local['formatted']} {local['timezone']}"

    # Countdown from issue time
    countdown_str = ""
    try:
        arrival_dt = datetime.fromisoformat(ga["arrival_utc"].replace("Z", "+00:00"))
        if issue_time_utc:
            ref_dt = datetime.fromisoformat(issue_time_utc.replace("Z", "+00:00"))
            hours_away = (arrival_dt - ref_dt).total_seconds() / 3600.0
            if hours_away >= 0:
                countdown_str = f"~{hours_away:.0f} hours from advisory time"
    except Exception:
        pass

    elements = [
        dmc.Divider(color="dark.5", my=4),
        dmc.Text("Est. Gale Arrival", size="xs", fw=600, c="#ef4444"),
        dmc.Text(arrival_str, size="xs", fw=600, c="white"),
    ]

    if countdown_str:
        elements.append(dmc.Text(countdown_str, size="xs", fw=500, c="#f59e0b"))

    if ring_km > 0:
        elements.append(
            dmc.Text(f"at {ring_km:.0f} km range ring", size="xs", c="#94a3b8")
        )

    if ga.get("interpolated"):
        b1 = convert_utc_to_local(ga["bracket_before_utc"], impact.get("lon"), impact.get("lat"))
        b2 = convert_utc_to_local(ga["bracket_after_utc"], impact.get("lon"), impact.get("lat"))
        elements.append(
            dmc.Text(
                f"Interpolated between {b1['time_only']} and {b2['time_only']}",
                size="xs", c="#64748b", fs="italic",
            )
        )

    return elements


def _location_impact_card(impact: dict, index: int, issue_time_utc: str = "") -> dmc.UnstyledButton:
    card_children = [
        dmc.Group(
            gap="xs",
            justify="space-between",
            children=[
                dmc.Text(impact["name"], size="sm", fw=600, c="white"),
                DashIconify(icon="tabler:chevron-right", width=14, color="#64748b"),
            ],
        ),
        dmc.Group(
            gap="xs",
            justify="space-between",
            children=[
                dmc.Text(
                    f"{impact['distance_km']:.0f} km",
                    size="lg", fw=700, c="white",
                ),
                dmc.Badge(
                    impact.get("type", "city"),
                    size="xs", variant="outline", color="gray",
                ),
            ],
        ),
        _threat_badge(impact["threat"]),
        *_gale_arrival_section(impact, issue_time_utc=issue_time_utc),
    ]

    card = dmc.Paper(
        shadow="sm",
        p="sm",
        radius="md",
        style={
            "backgroundColor": "#111827",
            "borderLeft": f"4px solid {impact['color']}",
            "minWidth": "160px",
            "transition": "background-color 0.15s, border-color 0.15s",
        },
        children=dmc.Stack(gap=4, children=card_children),
    )
    return dmc.UnstyledButton(
        id={"type": "cyclone-location-btn", "index": index},
        children=card,
        style={"width": "100%"},
    )


def _build_wind_radii_dict(fix_point: dict) -> dict:
    return {
        "gale": {
            "nw": fix_point.get("windRadiiGaleNW"),
            "ne": fix_point.get("windRadiiGaleNE"),
            "sw": fix_point.get("windRadiiGaleSW"),
            "se": fix_point.get("windRadiiGaleSE"),
        },
        "storm": {
            "nw": fix_point.get("windRadiiStormNW"),
            "ne": fix_point.get("windRadiiStormNE"),
            "sw": fix_point.get("windRadiiStormSW"),
            "se": fix_point.get("windRadiiStormSE"),
        },
        "hurricane": {
            "nw": fix_point.get("windRadiiHurricaneNW"),
            "ne": fix_point.get("windRadiiHurricaneNE"),
            "sw": fix_point.get("windRadiiHurricaneSW"),
            "se": fix_point.get("windRadiiHurricaneSE"),
        },
    }


def _overview_row(label: str, value: str, icon: str) -> dmc.Group:
    return dmc.Group(
        gap="sm",
        justify="space-between",
        children=[
            dmc.Group(
                gap="xs",
                children=[
                    DashIconify(icon=icon, width=16, color="#64748b"),
                    dmc.Text(label, size="xs", c="dimmed"),
                ],
            ),
            dmc.Text(value, size="sm", fw=500, c="white"),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────


def layout():
    from src.services.tc_service import (
        get_recent_and_archived_options,
        load_client_registry,
    )

    recent_options, archived_options = get_recent_and_archived_options()
    client_options = load_client_registry()
    default_system = recent_options[0]["value"] if recent_options else None

    return dmc.Stack(
        gap="md",
        style={"padding": "16px"},
        children=[
            # Hidden stores
            dcc.Store(id="cyclone-impacts-store", data=[]),
            dcc.Store(id="cyclone-area-times-store", data=[]),
            dcc.Store(id="cyclone-zoom-target", data=None),
            dcc.Store(id="cyclone-modal-location", data=None),
            dcc.Download(id="cyclone-download-csv"),
            dcc.Interval(id="cyclone-autoplay-interval", interval=2000, disabled=True),
            # Archive Warning Banner
            html.Div(id="cyclone-archive-banner"),
            # POC Banner
            dmc.Alert(
                title="Proof of Concept",
                color="yellow",
                variant="light",
                icon=DashIconify(icon="tabler:info-circle"),
                children=(
                    "TC data is from archived BoM advisories. "
                    "Production version will connect to live advisory feeds."
                ),
            ),
            # Controls Bar
            dmc.Paper(
                shadow="sm",
                p="md",
                radius="md",
                style={
                    "backgroundColor": "#111827",
                    "border": "1px solid #1e293b",
                    "overflow": "visible",
                },
                children=dmc.Stack(
                    gap="sm",
                    children=[
                        dmc.Group(
                            gap="lg",
                            wrap="wrap",
                            children=[
                                dmc.MultiSelect(
                                    id="cyclone-system-select",
                                    label="Recent Systems",
                                    data=recent_options,
                                    value=[default_system] if default_system else [],
                                    w={"base": "100%", "sm": 350},
                                    leftSection=DashIconify(icon="tabler:tornado"),
                                    searchable=True,
                                    styles=_INPUT_STYLE,
                                    comboboxProps=_COMBOBOX_PORTAL,
                                    clearable=True,
                                    placeholder="Select systems...",
                                ),
                                dmc.Select(
                                    id="cyclone-archived-select",
                                    label="Archived Systems",
                                    data=archived_options,
                                    value=None,
                                    w={"base": "100%", "sm": 280},
                                    leftSection=DashIconify(icon="tabler:archive"),
                                    searchable=True,
                                    placeholder="Select archived system...",
                                    clearable=True,
                                    styles=_INPUT_STYLE,
                                    comboboxProps=_COMBOBOX_PORTAL,
                                    style={"display": "block"} if archived_options else {"display": "none"},
                                ),
                                dmc.Select(
                                    id="cyclone-advisory-select",
                                    label="Advisory",
                                    data=[],
                                    value=None,
                                    w={"base": "100%", "xs": 220},
                                    leftSection=DashIconify(icon="tabler:clock"),
                                    styles=_INPUT_STYLE,
                                    comboboxProps=_COMBOBOX_PORTAL,
                                ),
                                dmc.Select(
                                    id="cyclone-client-select",
                                    label="Client",
                                    data=client_options,
                                    value="none",
                                    w={"base": "100%", "xs": 220},
                                    leftSection=DashIconify(icon="tabler:building"),
                                    styles=_INPUT_STYLE,
                                    comboboxProps=_COMBOBOX_PORTAL,
                                ),
                                dmc.Select(
                                    id="cyclone-tz-select",
                                    label="Timezone",
                                    data=TIMEZONE_OPTIONS,
                                    value="Australia/Perth",
                                    w={"base": "100%", "xs": 200},
                                    leftSection=DashIconify(icon="tabler:clock"),
                                    styles=_INPUT_STYLE,
                                    comboboxProps=_COMBOBOX_PORTAL,
                                ),
                                dmc.Select(
                                    id="cyclone-map-tile-select",
                                    label="Map Style",
                                    data=MAP_TILE_OPTIONS,
                                    value="dark",
                                    w={"base": "100%", "xs": 160},
                                    leftSection=DashIconify(icon="tabler:map"),
                                    styles=_INPUT_STYLE,
                                    comboboxProps=_COMBOBOX_PORTAL,
                                ),
                                dmc.Group(
                                    gap="md",
                                    children=[
                                        dmc.Switch(id="cyclone-show-track", label="Track", checked=True, color="orange", size="sm"),
                                        dmc.Switch(id="cyclone-show-cones", label="Forecast Cones", checked=True, color="orange", size="sm"),
                                        dmc.Switch(id="cyclone-show-areas", label="Confidence Areas", checked=False, color="orange", size="sm"),
                                        dmc.Switch(id="cyclone-show-danger-zone", label="Danger Zone", checked=False, color="red", size="sm"),
                                        dmc.Switch(id="cyclone-show-wind-radii", label="Wind Radii", checked=False, color="grape", size="sm"),
                                        dmc.Tooltip(
                                            label="Reset map to default view",
                                            position="bottom",
                                            children=dmc.ActionIcon(
                                                DashIconify(icon="tabler:focus-centered", width=18),
                                                id="cyclone-reset-view-btn",
                                                variant="light", color="blue", size="md", n_clicks=0,
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        # Time Slider (shown when Confidence Areas ON)
                        html.Div(
                            id="cyclone-time-slider-container",
                            style={"display": "none"},
                            children=dmc.Paper(
                                p="sm",
                                radius="sm",
                                style={"backgroundColor": "#0d1320", "border": "1px solid #1e293b"},
                                children=dmc.Group(
                                    gap="sm",
                                    wrap="nowrap",
                                    style={"alignItems": "center"},
                                    children=[
                                        dmc.Text("Outlook Time:", size="xs", fw=600, c="dimmed", style={"whiteSpace": "nowrap"}),
                                        dmc.ActionIcon(DashIconify(icon="tabler:player-skip-back", width=16), id="cyclone-time-prev", variant="subtle", color="orange", size="md", n_clicks=0),
                                        dmc.ActionIcon(DashIconify(icon="tabler:player-play", width=16), id="cyclone-time-play", variant="subtle", color="orange", size="md", n_clicks=0),
                                        dmc.ActionIcon(DashIconify(icon="tabler:player-skip-forward", width=16), id="cyclone-time-next", variant="subtle", color="orange", size="md", n_clicks=0),
                                        html.Div(
                                            style={"flex": "1"},
                                            children=dmc.Slider(id="cyclone-time-slider", min=0, max=20, step=1, value=0, color="orange", size="sm", marks=[]),
                                        ),
                                        dmc.Text(id="cyclone-time-label", size="xs", c="white", fw=600, style={"minWidth": "80px", "textAlign": "right"}, children="All times"),
                                    ],
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            # Forecast Timeline Modal
            dmc.Modal(
                id="cyclone-forecast-modal",
                title="Forecast Timeline",
                size="lg",
                centered=True,
                opened=False,
                styles={
                    "header": {"backgroundColor": "#111827", "borderBottom": "1px solid #1e293b"},
                    "body": {"backgroundColor": "#111827"},
                    "title": {"color": "#e2e8f0", "fontWeight": 700},
                    "close": {"color": "#94a3b8"},
                    "content": {"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                },
                children=html.Div(id="cyclone-forecast-modal-body"),
            ),
            # Map + Overview Grid
            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(
                        span={"base": 12, "lg": 8},
                        children=dmc.Paper(
                            shadow="sm", p="sm", radius="md",
                            style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                            children=[
                                html.Div(
                                    id="cyclone-map-container",
                                    children=html.Div(
                                        "Select a system to view track map",
                                        className="wid-chart-lg",
                                        style={"display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#64748b"},
                                    ),
                                ),
                            ],
                        ),
                    ),
                    dmc.GridCol(
                        span={"base": 12, "lg": 4},
                        children=dmc.Stack(
                            gap="md",
                            children=[
                                dmc.Paper(
                                    shadow="sm", p="md", radius="md",
                                    style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                                    children=html.Div(id="cyclone-overview-panel", children=dmc.Text("Select a system", c="dimmed", ta="center")),
                                ),
                                dmc.Paper(
                                    shadow="sm", p="md", radius="md",
                                    style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                                    children=[
                                        dmc.Text("Click Map Info", size="sm", fw=600, c="dimmed", mb="xs"),
                                        html.Div(id="cyclone-click-info", children=dmc.Text("Click on the map to measure distance from TC", size="xs", c="dimmed")),
                                    ],
                                ),
                            ],
                        ),
                    ),
                ],
            ),
            # Charts Row
            dmc.Grid(
                gutter="md",
                children=[
                    dmc.GridCol(
                        span={"base": 12, "lg": 6},
                        children=dmc.Paper(
                            shadow="sm", p="sm", radius="md",
                            style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                            children=dcc.Graph(id="cyclone-intensity-chart", config={"displayModeBar": "hover", "displaylogo": False}, className="wid-chart-md"),
                        ),
                    ),
                    dmc.GridCol(
                        span={"base": 12, "lg": 6},
                        children=dmc.Paper(
                            shadow="sm", p="sm", radius="md",
                            style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                            children=dcc.Graph(id="cyclone-probability-chart", config={"displayModeBar": "hover", "displaylogo": False}, className="wid-chart-sm"),
                        ),
                    ),
                ],
            ),
            # Advisory Accordion
            dmc.Paper(
                shadow="sm", p="md", radius="md",
                style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                children=[
                    dmc.Text("Advisory Information", size="sm", fw=600, c="dimmed", mb="sm"),
                    html.Div(id="cyclone-advisory-panel"),
                ],
            ),
            # Location Impacts
            dmc.Paper(
                shadow="sm", p="md", radius="md",
                style={"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                children=[
                    dmc.Group(
                        justify="space-between",
                        mb="sm",
                        children=[
                            dmc.Text("Distance to Locations", size="sm", fw=600, c="dimmed"),
                            dmc.Button(
                                "Export CSV",
                                id="cyclone-export-csv-btn",
                                size="xs", variant="subtle", color="gray",
                                leftSection=DashIconify(icon="tabler:download", width=14),
                                n_clicks=0,
                            ),
                        ],
                    ),
                    html.Div(id="cyclone-impacts-container"),
                ],
            ),
            # About Gale Arrival Times
            dmc.Accordion(
                variant="separated",
                styles={
                    "item": {"backgroundColor": "#111827", "border": "1px solid #1e293b"},
                    "control": {"color": "#e2e8f0"},
                    "panel": {"color": "#cbd5e1"},
                },
                children=[
                    dmc.AccordionItem(
                        value="about-gales",
                        children=[
                            dmc.AccordionControl(
                                dmc.Group(gap="xs", children=[
                                    DashIconify(icon="tabler:info-circle", width=16, color="#64748b"),
                                    dmc.Text("About Gale Arrival Times", size="sm", fw=600),
                                ]),
                            ),
                            dmc.AccordionPanel(
                                dmc.Stack(
                                    gap="sm",
                                    children=[
                                        dmc.Text(
                                            "The estimated gale arrival time shown on each location card "
                                            "indicates when tropical cyclone gale-force winds (34+ knots) "
                                            "are forecast to reach a location's trigger boundary.",
                                            size="sm",
                                        ),
                                        dmc.Text("How it is calculated", size="sm", fw=700, c="white"),
                                        dmc.List(
                                            size="sm",
                                            spacing="xs",
                                            children=[
                                                dmc.ListItem(
                                                    "At each forecast position, the Bureau of Meteorology provides "
                                                    "gale-force wind radii in four quadrants (NW, NE, SW, SE) "
                                                    "measured in nautical miles from the TC centre."
                                                ),
                                                dmc.ListItem(
                                                    "We use the maximum radius across all four quadrants at each "
                                                    "time step. This is the most conservative approach — it errs "
                                                    "on the side of caution by assuming gales extend to their "
                                                    "greatest reach in every direction."
                                                ),
                                                dmc.ListItem(
                                                    "For locations with range rings (client-configured alert "
                                                    "boundaries), the outermost range ring is used as the trigger "
                                                    "boundary. Gales are considered to have \"arrived\" when the "
                                                    "TC's gale radius overlaps with this ring."
                                                ),
                                                dmc.ListItem(
                                                    "For locations without range rings, the trigger boundary is "
                                                    "the location itself (i.e., when gales reach the site directly)."
                                                ),
                                            ],
                                        ),
                                        dmc.Text("Interpolation", size="sm", fw=700, c="white"),
                                        dmc.Text(
                                            "Official BoM forecast positions are typically issued at 6-hour "
                                            "intervals. When the gale arrival falls between two forecast "
                                            "positions, we use linear interpolation to estimate a more precise "
                                            "time. In these cases, the card will note \"Interpolated between\" "
                                            "with the two bounding official forecast times, so you can see "
                                            "that the arrival time is our best estimate between known data points.",
                                            size="sm",
                                        ),
                                        dmc.Text("Key terms", size="sm", fw=700, c="white"),
                                        dmc.List(
                                            size="sm",
                                            spacing="xs",
                                            children=[
                                                dmc.ListItem([
                                                    dmc.Text("Est. Gale Arrival", size="sm", fw=600, c="#ef4444", span=True),
                                                    " — the estimated local date and time when gales will reach "
                                                    "the trigger boundary, with a countdown in hours from the advisory issue time.",
                                                ]),
                                                dmc.ListItem([
                                                    dmc.Text("GALES ALREADY WITHIN RANGE", size="sm", fw=600, c="#ef4444", span=True),
                                                    " — the TC's gale-force wind field already overlaps "
                                                    "with the location's trigger boundary at the current analysis position.",
                                                ]),
                                                dmc.ListItem([
                                                    dmc.Text("Gales: not forecast to reach", size="sm", fw=600, c="#64748b", span=True),
                                                    " — gale-force winds are not forecast to reach this location's "
                                                    "trigger boundary within the forecast period.",
                                                ]),
                                            ],
                                        ),
                                        dmc.Alert(
                                            color="yellow",
                                            variant="light",
                                            children=(
                                                "These times are estimates based on forecast data which carries "
                                                "inherent uncertainty. Actual gale arrival may differ. Always "
                                                "refer to the latest official BoM advisory and your organisation's "
                                                "emergency action plans."
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────


@callback(
    Output("cyclone-advisory-select", "data"),
    Output("cyclone-advisory-select", "value"),
    Output("cyclone-advisory-select", "disabled"),
    Output("cyclone-system-select", "value", allow_duplicate=True),
    Output("cyclone-archived-select", "value", allow_duplicate=True),
    Input("cyclone-system-select", "value"),
    Input("cyclone-archived-select", "value"),
    prevent_initial_call="initial_duplicate",
)
def update_advisory_dropdown(recent_systems, archived_system):
    from src.services.tc_service import get_advisories_for_system

    trigger = ctx.triggered_id
    if recent_systems is None:
        recent_systems = []

    if trigger == "cyclone-archived-select":
        system_id = archived_system
        clear_recent = [] if archived_system else no_update
        clear_archive = no_update
    else:
        clear_recent = no_update
        clear_archive = None if recent_systems else no_update

        if len(recent_systems) == 1:
            system_id = recent_systems[0]
        elif len(recent_systems) > 1:
            return [], None, True, clear_recent, clear_archive
        else:
            system_id = None

    if not system_id:
        return [], None, False, clear_recent, clear_archive

    advisories = get_advisories_for_system(system_id)
    if not advisories:
        return [], None, False, clear_recent, clear_archive

    options = [{"label": a["label"], "value": a["value"]} for a in advisories]
    return options, options[0]["value"], False, clear_recent, clear_archive


@callback(
    Output("cyclone-map-container", "children"),
    Output("cyclone-overview-panel", "children"),
    Output("cyclone-intensity-chart", "figure"),
    Output("cyclone-probability-chart", "figure"),
    Output("cyclone-advisory-panel", "children"),
    Output("cyclone-impacts-container", "children"),
    Output("cyclone-archive-banner", "children"),
    Output("cyclone-impacts-store", "data"),
    Output("cyclone-area-times-store", "data"),
    Output("cyclone-time-slider", "max"),
    Output("cyclone-time-slider", "marks"),
    Input("cyclone-advisory-select", "value"),
    Input("cyclone-show-track", "checked"),
    Input("cyclone-show-cones", "checked"),
    Input("cyclone-show-areas", "checked"),
    Input("cyclone-show-danger-zone", "checked"),
    Input("cyclone-show-wind-radii", "checked"),
    Input("cyclone-time-slider", "value"),
    Input("cyclone-client-select", "value"),
    Input("cyclone-zoom-target", "data"),
    Input("cyclone-system-select", "value"),
    Input("cyclone-map-tile-select", "value"),
)
def update_cyclone_page(
    advisory_filename, show_track, show_cones, show_areas,
    show_danger_zone, show_wind_radii, time_slider_value,
    client_config, zoom_target, system_ids, tile_style,
):
    from src.services.tc_service import (
        get_system_data, extract_fix_points, extract_summary,
        extract_advisory_text, extract_probability_timeline,
        calculate_location_impacts, calculate_movement_speed,
        calculate_bearing, calculate_gale_arrivals_for_impacts,
        convert_utc_to_local, build_track_geojson,
        get_forecast_cones, get_confidence_areas,
        load_client_locations, is_latest_advisory,
        get_confidence_area_times, filter_confidence_areas_by_time,
        get_confidence_area_style, get_latest_advisory_filename,
        compute_map_center_zoom, compute_map_center_zoom_multi,
    )
    from src.components.map_components import create_cyclone_track_map
    from src.components.tc_charts import (
        create_tc_intensity_chart, create_tc_probability_chart, empty_chart,
    )

    _empty_slider_marks = []
    if system_ids is None:
        system_ids = []
    multi_mode = len(system_ids) > 1

    # Nothing selected
    if not advisory_filename and not multi_mode:
        placeholder = dmc.Text("Select a system", c="dimmed", ta="center")
        empty = empty_chart("Select a system to view data")
        return (
            html.Div("Select a system to view track map", className="wid-chart-lg",
                     style={"display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#64748b"}),
            placeholder, empty, empty, placeholder, placeholder,
            None, [], [], 0, _empty_slider_marks,
        )

    # Resolve per-system data
    if multi_mode:
        systems_render = []
        all_data = []
        for i, sid in enumerate(system_ids):
            fn = get_latest_advisory_filename(sid)
            if not fn:
                continue
            d = get_system_data(fn)
            if not d:
                continue
            all_data.append(d)

            fp = extract_fix_points(d)
            analysis_pts = [p for p in fp if p.get("type") == "Analysis"]
            tc_pos = None
            wr_data = None
            if analysis_pts:
                lpt = analysis_pts[-1]
                tc_pos = {"lat": lpt["lat"], "lon": lpt["lon"]}
                wr_data = _build_wind_radii_dict(lpt)

            s_name = d.get("cycloneFullName") or d.get("cycloneName") or sid
            s_color = TC_SYSTEM_COLORS[i % len(TC_SYSTEM_COLORS)]

            systems_render.append({
                "track_geojson": build_track_geojson(d),
                "forecast_cones": get_forecast_cones(d),
                "confidence_areas": get_confidence_areas(d),
                "tc_current_position": tc_pos,
                "wind_radii_data": wr_data,
                "system_name": s_name,
                "system_color": s_color,
            })

        if not systems_render:
            placeholder = dmc.Text("No data for selected systems", c="red", ta="center")
            empty = empty_chart("No data")
            return (
                html.Div("No data", className="wid-chart-lg", style={"color": "#64748b"}),
                placeholder, empty, empty, placeholder, placeholder,
                None, [], [], 0, _empty_slider_marks,
            )

        data = all_data[0]
        center, zoom = compute_map_center_zoom_multi(all_data)
    else:
        data = get_system_data(advisory_filename)
        if not data:
            placeholder = dmc.Text("Failed to load advisory data", c="red", ta="center")
            empty = empty_chart("No data")
            return (
                html.Div("No data", className="wid-chart-lg", style={"color": "#64748b"}),
                placeholder, empty, empty, placeholder, placeholder,
                None, [], [], 0, _empty_slider_marks,
            )
        center, zoom = compute_map_center_zoom(data)
        systems_render = None

    summary = extract_summary(data)
    fix_points = extract_fix_points(data)
    advisory_text_data = extract_advisory_text(data)
    probability_data = extract_probability_timeline(data)
    forecast_cones = get_forecast_cones(data)
    confidence_areas = get_confidence_areas(data)

    client_locs = load_client_locations(client_config) if client_config and client_config != "none" else []

    if multi_mode:
        impacts = []
    else:
        raw_impacts = calculate_location_impacts(data, extra_locations=client_locs)
        impacts = calculate_gale_arrivals_for_impacts(data, raw_impacts, client_locs)

    # Archive banner
    archive_banner = None
    if not multi_mode and advisory_filename and not is_latest_advisory(advisory_filename):
        issue_str = ""
        if data.get("issueTime"):
            try:
                dt = datetime.fromisoformat(data["issueTime"].replace("Z", "+00:00"))
                issue_str = dt.strftime("%d %B %Y at %H:%M UTC")
            except Exception:
                issue_str = data["issueTime"][:19]
        archive_banner = dmc.Alert(
            title="Viewing Archived Forecast",
            color="orange", variant="light",
            icon=DashIconify(icon="tabler:alert-triangle"),
            children=(
                f"This is an older forecast for {summary['name']}, "
                f"issued on {issue_str}. "
                "This is NOT the current forecast — use for historical comparison only."
            ),
        )

    # Confidence area time steps
    area_times = get_confidence_area_times(data)
    slider_max = max(len(area_times) - 1, 0)
    slider_marks = []
    for i, step in enumerate(area_times):
        if i == 0 or i == len(area_times) - 1 or i % 4 == 0:
            # Short label for slider tick marks; full label shown in time_label text
            short_label = f"+{int(step['offset_hours'])}h"
            slider_marks.append({"value": i, "label": short_label})

    filtered_areas = confidence_areas
    if not multi_mode and show_areas and area_times and time_slider_value and time_slider_value > 0:
        idx = min(time_slider_value, len(area_times) - 1)
        selected_step = area_times[idx]
        ref_time = data.get("referenceTime", "")
        filtered_areas = filter_confidence_areas_by_time(
            confidence_areas, ref_time, selected_step["offset_hours"]
        )
        if filtered_areas and filtered_areas.get("features"):
            styled_features = []
            for feat in filtered_areas["features"]:
                conf = feat.get("properties", {}).get("confidenceLevel")
                style = get_confidence_area_style(conf)
                new_feat = dict(feat)
                new_props = dict(feat.get("properties", {}))
                new_props["_style"] = style
                new_feat["properties"] = new_props
                styled_features.append(new_feat)
            filtered_areas = {"type": "FeatureCollection", "features": styled_features}

    # Danger zone / wind radii (single-system)
    tc_current_position = None
    wind_radii_data_map = None
    if not multi_mode:
        analysis_pts = [p for p in fix_points if p.get("type") == "Analysis"]
        if analysis_pts:
            latest_pt = analysis_pts[-1]
            tc_current_position = {"lat": latest_pt["lat"], "lon": latest_pt["lon"]}
            wind_radii_data_map = _build_wind_radii_dict(latest_pt)

    # Zoom target override
    if zoom_target and isinstance(zoom_target, dict):
        zt_lat = zoom_target.get("lat")
        zt_lon = zoom_target.get("lon")
        if zt_lat is not None and zt_lon is not None:
            center = [zt_lat, zt_lon]
            zoom = 8

    # Map
    if multi_mode:
        track_map = create_cyclone_track_map(
            systems=systems_render,
            client_locations=client_locs,
            location_impacts=None,
            show_track=show_track, show_cones=show_cones,
            show_areas=show_areas, show_danger_zone=show_danger_zone,
            show_wind_radii=show_wind_radii,
            center=center, zoom=zoom,
            tile_style=tile_style or "dark",
        )
    else:
        track_geojson = build_track_geojson(data)
        track_map = create_cyclone_track_map(
            track_geojson=track_geojson,
            forecast_cones=forecast_cones,
            confidence_areas=filtered_areas,
            show_track=show_track, show_cones=show_cones,
            show_areas=show_areas, show_danger_zone=show_danger_zone,
            tc_current_position=tc_current_position,
            show_wind_radii=show_wind_radii,
            wind_radii_data=wind_radii_data_map,
            system_name=summary["name"],
            client_locations=client_locs,
            location_impacts=impacts,
            center=center, zoom=zoom,
            tile_style=tile_style or "dark",
        )

    # Overview panel
    status_color = "red" if "Severe" in summary.get("status", "") else (
        "orange" if "Cyclone" in summary.get("status", "") else "yellow"
    )

    pos_str = ""
    if summary.get("lat") is not None and summary.get("lon") is not None:
        lat_dir = "S" if summary["lat"] < 0 else "N"
        lon_dir = "E" if summary["lon"] > 0 else "W"
        pos_str = f"{abs(summary['lat']):.1f}{lat_dir} {abs(summary['lon']):.1f}{lon_dir}"

    issue_str = ""
    if summary.get("issueTime"):
        try:
            dt = datetime.fromisoformat(summary["issueTime"].replace("Z", "+00:00"))
            issue_str = dt.strftime("%d %b %Y %H:%M UTC")
        except Exception:
            issue_str = summary["issueTime"][:19]

    overview_children = [
        dmc.Group(gap="sm", children=[
            dmc.Text(summary["name"], size="lg", fw=700, c="white"),
            _category_badge(summary["category"]),
        ]),
    ]
    if multi_mode:
        overview_children.append(
            dmc.Badge(f"{len(system_ids)} systems selected", color="blue", variant="light", size="sm")
        )
    # Calculate movement speed and direction
    movement_str = "—"
    speeds = calculate_movement_speed(fix_points)
    if speeds:
        latest_speed = speeds[-1]
        speed_kmh = latest_speed["speed_kmh"]
        speed_kn = speed_kmh / 1.852
        analysis_pts_for_bearing = [p for p in fix_points if p.get("type") == "Analysis"]
        if len(analysis_pts_for_bearing) >= 2:
            p1, p2 = analysis_pts_for_bearing[-2], analysis_pts_for_bearing[-1]
            _, cardinal = calculate_bearing(p1["lat"], p1["lon"], p2["lat"], p2["lon"])
            movement_str = f"{speed_kmh:.0f} km/h ({speed_kn:.0f} kt) towards {cardinal or '—'}"
        else:
            movement_str = f"{speed_kmh:.0f} km/h ({speed_kn:.0f} kt)"

    overview_children.extend([
        dmc.Badge(summary.get("status", "Unknown"), color=status_color, variant="light", size="lg"),
        dmc.Divider(color="dark.5"),
        _overview_row("Wind", f"{summary.get('maxWind') or '—'} kt", "tabler:wind"),
        _overview_row("Gusts", f"{summary.get('maxGust') or '—'} kt", "tabler:wind"),
        _overview_row("Pressure", f"{summary.get('pressure') or '—'} hPa", "tabler:gauge"),
        _overview_row("Position", pos_str or "—", "tabler:map-pin"),
        _overview_row("Movement", movement_str, "tabler:arrows-move"),
        dmc.Divider(color="dark.5"),
        _overview_row("Issued", issue_str or "—", "tabler:clock"),
        _overview_row("Positions", f"{summary.get('analysisCount', 0)} analysis + {summary.get('forecastCount', 0)} forecast", "tabler:route"),
        dmc.Badge(
            "Final Issue" if summary.get("finalIssue") else "Active",
            color="gray" if summary.get("finalIssue") else "green",
            variant="light", size="sm",
        ),
    ])
    overview_panel = dmc.Stack(gap="sm", children=overview_children)

    # Charts
    intensity_fig = create_tc_intensity_chart(fix_points, summary["name"])
    probability_fig = create_tc_probability_chart(probability_data, summary["name"])

    # Advisory text
    advisory_items = []
    seven_day = advisory_text_data.get("sevenDay", {})
    if seven_day.get("headline") or seven_day.get("points"):
        points_content = []
        if seven_day.get("headline"):
            points_content.append(dmc.Text(seven_day["headline"], size="sm", fw=600, c="white", mb="xs"))
        for pt in seven_day.get("points", []):
            points_content.append(dmc.Text(f"• {pt}", size="xs", c="#cbd5e1", mb=4))
        advisory_items.append(
            dmc.AccordionItem(value="seven-day", children=[
                dmc.AccordionControl("7-Day Forecast"),
                dmc.AccordionPanel(dmc.Stack(gap=4, children=points_content)),
            ])
        )

    track_text = advisory_text_data.get("track", {})
    if track_text.get("discussion"):
        track_content = []
        if track_text.get("headline"):
            track_content.append(dmc.Text(track_text["headline"], size="sm", fw=600, c="white", mb="xs"))
        track_content.append(dmc.Text(track_text["discussion"], size="xs", c="#cbd5e1"))
        if track_text.get("upperBound"):
            track_content.append(dmc.Divider(color="dark.5", my="xs"))
            track_content.append(dmc.Text("Upper Bound Scenario", size="xs", fw=600, c="#f59e0b", mb=4))
            track_content.append(dmc.Text(track_text["upperBound"], size="xs", c="#cbd5e1"))
        advisory_items.append(
            dmc.AccordionItem(value="track", children=[
                dmc.AccordionControl("Track Discussion"),
                dmc.AccordionPanel(dmc.Stack(gap=4, children=track_content)),
            ])
        )

    if advisory_items:
        advisory_panel = dmc.Accordion(
            variant="separated", children=advisory_items,
            styles={
                "item": {"backgroundColor": "#0d1320", "border": "1px solid #1e293b"},
                "control": {"color": "#e2e8f0"},
                "panel": {"color": "#cbd5e1"},
            },
        )
    else:
        advisory_panel = dmc.Text("No advisory text available", c="dimmed", size="sm")

    # Location impacts
    if multi_mode:
        impacts_grid = dmc.Alert(
            title="Multiple systems selected", color="blue", variant="light",
            icon=DashIconify(icon="tabler:info-circle"),
            children="Select a single system to view location impacts and forecast timelines.",
        )
        impacts_serialized = []
    elif impacts:
        impacts_grid = dmc.SimpleGrid(
            cols={"base": 2, "sm": 3, "md": 4, "lg": 5}, spacing="sm",
            children=[_location_impact_card(imp, i, issue_time_utc=summary.get("issueTime", "")) for i, imp in enumerate(impacts)],
        )
        impacts_serialized = [
            {"name": imp["name"], "lat": imp["lat"], "lon": imp["lon"],
             "distance_km": imp["distance_km"], "threat": imp["threat"], "type": imp.get("type", "city")}
            for imp in impacts
        ]
    else:
        impacts_grid = dmc.Text("No location data", c="dimmed", size="sm")
        impacts_serialized = []

    return (
        track_map, overview_panel, intensity_fig, probability_fig,
        advisory_panel, impacts_grid, archive_banner,
        impacts_serialized, area_times, slider_max, slider_marks,
    )


# Map click callback
@callback(
    Output("cyclone-click-info", "children"),
    Input("cyclone-track-map", "click_lat_lng"),
    State("cyclone-advisory-select", "value"),
    prevent_initial_call=True,
)
def handle_map_click(click_lat_lng, advisory_filename):
    if not click_lat_lng or not advisory_filename:
        return no_update

    from src.services.tc_service import get_system_data, extract_fix_points, haversine

    data = get_system_data(advisory_filename)
    if not data:
        return no_update

    fix_points = extract_fix_points(data)
    analysis_pts = [p for p in fix_points if p.get("type") == "Analysis"]
    if not analysis_pts:
        return no_update

    latest = analysis_pts[-1]
    click_lat, click_lon = click_lat_lng
    dist = haversine(latest["lat"], latest["lon"], click_lat, click_lon)

    lat_dir = "S" if click_lat < 0 else "N"
    lon_dir = "E" if click_lon > 0 else "W"

    return dmc.Stack(gap=4, children=[
        dmc.Text(f"Clicked: {abs(click_lat):.2f}{lat_dir} {abs(click_lon):.2f}{lon_dir}", size="sm", c="white"),
        dmc.Text(f"Distance from TC: {dist:.0f} km", size="lg", fw=700, c="#f59e0b"),
    ])


# Time slider show/hide
@callback(
    Output("cyclone-time-slider-container", "style"),
    Input("cyclone-show-areas", "checked"),
)
def toggle_time_slider_visibility(areas_checked):
    if areas_checked:
        return {"display": "block"}
    return {"display": "none"}


# Time slider controls
@callback(
    Output("cyclone-time-slider", "value"),
    Output("cyclone-autoplay-interval", "disabled"),
    Input("cyclone-time-prev", "n_clicks"),
    Input("cyclone-time-next", "n_clicks"),
    Input("cyclone-time-play", "n_clicks"),
    Input("cyclone-autoplay-interval", "n_intervals"),
    State("cyclone-time-slider", "value"),
    State("cyclone-time-slider", "max"),
    State("cyclone-autoplay-interval", "disabled"),
    prevent_initial_call=True,
)
def time_slider_controls(prev_n, next_n, play_n, interval_n, current_val, slider_max, autoplay_disabled):
    trigger = ctx.triggered_id
    if not trigger:
        return no_update, no_update

    if trigger == "cyclone-time-prev":
        return max(0, (current_val or 0) - 1), True
    if trigger == "cyclone-time-next":
        return min(slider_max or 0, (current_val or 0) + 1), True
    if trigger == "cyclone-time-play":
        return no_update, not autoplay_disabled
    if trigger == "cyclone-autoplay-interval":
        return ((current_val or 0) + 1) % ((slider_max or 0) + 1), no_update

    return no_update, no_update


# Time label
@callback(
    Output("cyclone-time-label", "children"),
    Input("cyclone-time-slider", "value"),
    State("cyclone-area-times-store", "data"),
)
def update_time_label(slider_value, area_times):
    if not area_times or slider_value is None or slider_value == 0:
        return "All times"
    idx = min(slider_value, len(area_times) - 1)
    return area_times[idx].get("label", f"+{slider_value}")


# CSV export
@callback(
    Output("cyclone-download-csv", "data"),
    Input("cyclone-export-csv-btn", "n_clicks"),
    State("cyclone-advisory-select", "value"),
    State("cyclone-client-select", "value"),
    prevent_initial_call=True,
)
def export_locations_csv(n_clicks, advisory_filename, client_config):
    if not n_clicks or not advisory_filename:
        return no_update

    from src.services.tc_service import get_system_data, calculate_location_impacts, load_client_locations

    data = get_system_data(advisory_filename)
    if not data:
        return no_update

    client_locs = load_client_locations(client_config) if client_config and client_config != "none" else []
    impacts = calculate_location_impacts(data, extra_locations=client_locs)
    if not impacts:
        return no_update

    system_name = (
        data.get("cycloneFullName") or data.get("cycloneName") or data.get("disturbanceId", "Unknown")
    ).replace(" ", "_")
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = ["Location Name,Distance (km),Distance (nm),Threat Level,Latitude,Longitude"]
    for imp in impacts:
        dist_nm = imp["distance_km"] / 1.852
        lines.append(f"{imp['name']},{imp['distance_km']:.1f},{dist_nm:.1f},{imp['threat']},{imp['lat']},{imp['lon']}")

    return dict(content="\n".join(lines), filename=f"TC_{system_name}_Locations_{date_str}.csv")


# Forecast timeline modal
@callback(
    Output("cyclone-forecast-modal", "opened"),
    Output("cyclone-forecast-modal", "title"),
    Output("cyclone-forecast-modal-body", "children"),
    Output("cyclone-modal-location", "data"),
    Input({"type": "cyclone-location-btn", "index": ALL}, "n_clicks"),
    Input("cyclone-forecast-modal", "opened"),
    State("cyclone-advisory-select", "value"),
    State("cyclone-impacts-store", "data"),
    prevent_initial_call=True,
)
def show_forecast_timeline(location_clicks, modal_opened, advisory_filename, impacts_store):
    from src.services.tc_service import (
        get_system_data, calculate_forecast_timeline,
        convert_utc_to_local, load_client_locations,
    )
    from src.utils.constants import TC_MAJOR_LOCATIONS

    trigger = ctx.triggered_id

    if trigger == "cyclone-forecast-modal":
        if not modal_opened:
            return False, no_update, no_update, no_update
        return no_update, no_update, no_update, no_update

    if not isinstance(trigger, dict) or trigger.get("type") != "cyclone-location-btn":
        return no_update, no_update, no_update, no_update

    if not any(c for c in (location_clicks or []) if c):
        return no_update, no_update, no_update, no_update

    index = trigger.get("index", 0)
    if not advisory_filename or not impacts_store or index >= len(impacts_store):
        return no_update, no_update, no_update, no_update

    location = impacts_store[index]
    data = get_system_data(advisory_filename)
    if not data:
        return no_update, no_update, no_update, no_update

    loc_config = None
    for loc in TC_MAJOR_LOCATIONS:
        if loc["name"] == location["name"]:
            loc_config = loc
            break

    timeline = calculate_forecast_timeline(
        data, location["name"], location["lat"], location["lon"],
        location_config=loc_config,
    )

    zoom_coords = {"lat": location["lat"], "lon": location["lon"], "name": location["name"]}

    if not timeline:
        body = dmc.Text("No forecast data available.", c="dimmed", size="sm")
        return True, f"Forecast Timeline: {location['name']}", body, None

    content_children = []

    # Current Status
    dist_km = timeline["current_distance"]
    dist_nm = dist_km / 1.852
    content_children.append(dmc.Stack(gap="xs", children=[
        dmc.Text("Current Status", size="md", fw=700, c="#4ECDC4"),
        dmc.Group(gap="sm", children=[
            dmc.Text("Distance:", size="sm", c="dimmed"),
            dmc.Text(f"{dist_km:.0f} km ({dist_nm:.0f} nm)", size="sm", fw=600, c="white"),
        ]),
        dmc.Group(gap="sm", children=[
            dmc.Text("Threat Level:", size="sm", c="dimmed"),
            _threat_badge(timeline["current_threat"]),
        ]),
    ]))
    content_children.append(dmc.Divider(color="dark.5", my="sm"))

    # Closest Approach
    if timeline.get("has_forecast") and timeline.get("min_distance"):
        min_d = timeline["min_distance"]
        local_time = convert_utc_to_local(min_d["time"], min_d.get("lon", location["lon"]), min_d.get("lat", location["lat"]))
        time_str = f"{local_time['formatted']} {local_time['timezone']}"
        wind_str = f"{min_d['wind']:.0f} kt" if min_d.get("wind") else "N/A"
        ca_km = min_d["distance"]
        ca_nm = ca_km / 1.852

        content_children.append(dmc.Paper(
            p="sm", radius="sm",
            style={"backgroundColor": "#0d1320", "border": "1px solid #1e293b"},
            children=dmc.Stack(gap="xs", children=[
                dmc.Text("Closest Approach", size="md", fw=700, c="#FF6B35"),
                dmc.Group(gap="sm", children=[dmc.Text("Time:", size="sm", c="dimmed"), dmc.Text(time_str, size="sm", fw=500, c="white")]),
                dmc.Group(gap="sm", children=[dmc.Text("Distance:", size="sm", c="dimmed"), dmc.Text(f"{ca_km:.0f} km ({ca_nm:.0f} nm)", size="sm", fw=500, c="white")]),
                dmc.Group(gap="sm", children=[dmc.Text("Intensity:", size="sm", c="dimmed"), dmc.Text(f"{min_d['category']}, {wind_str}", size="sm", fw=500, c="white")]),
                dmc.Group(gap="sm", children=[dmc.Text("Threat Level:", size="sm", c="dimmed"), _threat_badge(min_d["threat"])]),
            ]),
        ))
        content_children.append(dmc.Divider(color="dark.5", my="sm"))

    # Forecast Threat Changes
    if timeline.get("has_forecast"):
        events = timeline.get("forecast_events", [])
        content_children.append(dmc.Text("Forecast Threat Changes", size="md", fw=700, c="#4ECDC4"))
        if events:
            for evt in events:
                local_t = convert_utc_to_local(evt["time"], evt.get("lon", location["lon"]), evt.get("lat", location["lat"]))
                evt_time_str = f"{local_t['formatted']} {local_t['timezone']}"
                wind_str = f"{evt['wind']:.0f} kt" if evt.get("wind") else "N/A"
                evt_km = evt["distance"]
                evt_nm = evt_km / 1.852

                content_children.append(dmc.Paper(
                    p="xs", radius="sm", mb="xs",
                    style={"backgroundColor": "#0d1320", "border": "1px solid #1e293b"},
                    children=dmc.Stack(gap=2, children=[
                        dmc.Group(gap="xs", children=[
                            dmc.Text(evt_time_str, size="sm", fw=600, c="white"),
                            dmc.Text(f"— {evt['category']}, {wind_str}", size="xs", c="dimmed"),
                        ]),
                        dmc.Group(gap="xs", children=[
                            dmc.Text(f"{evt_km:.0f} km ({evt_nm:.0f} nm)", size="xs", c="dimmed"),
                            _threat_badge(evt["from_threat"]),
                            DashIconify(icon="tabler:arrow-right", width=12, color="#64748b"),
                            _threat_badge(evt["threat"]),
                        ]),
                    ]),
                ))
        else:
            content_children.append(
                dmc.Text("No threat level changes forecast for this location.", size="sm", c="dimmed", fs="italic")
            )

    content_children.append(dmc.Divider(color="dark.5", my="sm"))
    content_children.append(
        dmc.Button("Zoom to Location", id="cyclone-zoom-to-loc-btn",
                   leftSection=DashIconify(icon="tabler:map-pin", width=16),
                   color="teal", variant="filled", size="sm", n_clicks=0)
    )

    body = dmc.Stack(gap="sm", children=content_children)
    return True, f"Forecast Timeline: {location['name']}", body, zoom_coords


# Zoom to location
@callback(
    Output("cyclone-zoom-target", "data", allow_duplicate=True),
    Output("cyclone-forecast-modal", "opened", allow_duplicate=True),
    Input("cyclone-zoom-to-loc-btn", "n_clicks"),
    State("cyclone-modal-location", "data"),
    prevent_initial_call=True,
)
def zoom_to_location(n_clicks, modal_location):
    if not n_clicks or not modal_location:
        return no_update, no_update
    return modal_location, False


# Reset map view
@callback(
    Output("cyclone-zoom-target", "data", allow_duplicate=True),
    Input("cyclone-reset-view-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_map_view(n_clicks):
    if not n_clicks:
        return no_update
    return None
