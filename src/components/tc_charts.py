"""
TC chart factory functions — intensity, probability, and movement charts.
"""
from datetime import datetime
from typing import List

import plotly.graph_objs as go

from src.utils.constants import (
    PLOTLY_LAYOUT_DEFAULTS,
    TC_CATEGORY_COLORS,
)


def _base_layout(**overrides) -> dict:
    """Merge custom overrides onto the global dark theme layout defaults."""
    layout = dict(PLOTLY_LAYOUT_DEFAULTS)
    layout.update(overrides)
    return layout


def empty_chart(message: str = "Select a system to view data") -> go.Figure:
    """Create an empty placeholder chart with a message."""
    fig = go.Figure()
    fig.update_layout(**_base_layout(
        height=450,
        annotations=[{
            "text": message,
            "xref": "paper", "yref": "paper",
            "x": 0.5, "y": 0.5,
            "showarrow": False,
            "font": {"size": 16, "color": "#64748b"},
        }],
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
    ))
    return fig


def create_tc_intensity_chart(
    fix_points: List[dict],
    system_name: str = "System",
) -> go.Figure:
    """
    Dual-axis time series: Wind speed (kt, left) + Central pressure (hPa, right, inverted).
    Category boundary lines and analysis/forecast region shading.
    """
    fig = go.Figure()

    if not fix_points:
        return empty_chart("No intensity data available")

    times, winds, pressures, categories, types = [], [], [], [], []
    for p in fix_points:
        try:
            t = datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
        except Exception:
            continue
        times.append(t)
        winds.append(p.get("maxWind"))
        pressures.append(p.get("pressure"))
        categories.append(p.get("category", "TL"))
        types.append(p.get("type", "Analysis"))

    if not times:
        return empty_chart("No intensity data available")

    # Wind speed trace
    wind_vals = [w if w is not None else None for w in winds]
    fig.add_trace(go.Scatter(
        x=times,
        y=wind_vals,
        mode="lines+markers",
        name="Max Wind (kt)",
        line=dict(color="#f59e0b", width=2.5),
        marker=dict(
            size=8,
            color=[TC_CATEGORY_COLORS.get(c, "#888") for c in categories],
            line=dict(width=1, color="#1e293b"),
        ),
        hovertemplate="<b>%{x}</b><br>Wind: %{y} kt<extra></extra>",
        yaxis="y",
    ))

    # Pressure trace (secondary y-axis)
    pressure_vals = [p if p is not None else None for p in pressures]
    if any(v is not None for v in pressure_vals):
        fig.add_trace(go.Scatter(
            x=times,
            y=pressure_vals,
            mode="lines+markers",
            name="Pressure (hPa)",
            line=dict(color="#3b82f6", width=2, dash="dot"),
            marker=dict(size=6, color="#3b82f6"),
            hovertemplate="<b>%{x}</b><br>Pressure: %{y} hPa<extra></extra>",
            yaxis="y2",
        ))

    # Category boundary lines
    cat_boundaries = [
        (34, "Cat 1", "#22c55e"),
        (48, "Cat 2", "#3b82f6"),
        (64, "Cat 3", "#f59e0b"),
        (86, "Cat 4", "#ef4444"),
        (108, "Cat 5", "#9333ea"),
    ]
    for val, label, color in cat_boundaries:
        fig.add_shape(
            type="line", x0=times[0], x1=times[-1], y0=val, y1=val,
            line=dict(color=color, width=1, dash="dash"),
            opacity=0.5,
        )
        fig.add_annotation(
            x=times[-1], y=val, text=label, showarrow=False,
            font=dict(color=color, size=9), xanchor="left", xshift=5,
            bgcolor="#111827", borderpad=2,
        )

    # Analysis / Forecast divider
    analysis_times = [t for t, tp in zip(times, types) if tp == "Analysis"]
    if analysis_times:
        last_analysis = max(analysis_times)
        fig.add_shape(
            type="line", x0=last_analysis, x1=last_analysis, y0=0, y1=1,
            yref="paper", line=dict(color="#64748b", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=last_analysis, y=1.02, yref="paper",
            text="Analysis | Forecast", showarrow=False,
            font=dict(color="#94a3b8", size=9), xanchor="center",
        )

    valid_winds = [w for w in wind_vals if w is not None]
    wind_max = max(valid_winds) if valid_winds else 50
    wind_y_max = max(wind_max + 20, 60)

    layout_opts = _base_layout(
        title=dict(
            text=f"Intensity Timeline — {system_name}",
            y=0.95, yanchor="top", x=0.5, xanchor="center",
            font=dict(size=14, color="#e2e8f0"),
        ),
        height=420,
        margin=dict(l=50, r=60, t=80, b=50),
        yaxis=dict(
            title=dict(text="Wind Speed (kt)", font=dict(color="#f59e0b")),
            tickfont=dict(color="#f59e0b"),
            range=[0, wind_y_max],
            gridcolor="#1e293b",
        ),
        yaxis2=dict(
            title=dict(text="Central Pressure (hPa)", font=dict(color="#3b82f6")),
            tickfont=dict(color="#3b82f6"),
            overlaying="y",
            side="right",
            autorange="reversed",
            showgrid=False,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center",
            font=dict(size=11),
        ),
    )
    fig.update_layout(**layout_opts)
    return fig


def create_tc_probability_chart(
    probability_data: List[dict],
    system_name: str = "System",
) -> go.Figure:
    """Bar chart of TC development probability over time."""
    fig = go.Figure()

    if not probability_data:
        return empty_chart("No probability data available")

    rating_colors = {
        "High": "#ef4444",
        "Moderate": "#f59e0b",
        "Low": "#eab308",
        "None": "#64748b",
    }

    labels = [p.get("label", "") for p in probability_data]
    probs = [p.get("probability") or 0 for p in probability_data]
    ratings = [p.get("rating", "None") for p in probability_data]
    colors = [rating_colors.get(r, "#64748b") for r in ratings]

    fig.add_trace(go.Bar(
        x=labels,
        y=probs,
        marker_color=colors,
        text=[f"{p}%" if p else "" for p in probs],
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=10),
        hovertemplate="<b>%{x}</b><br>Probability: %{y}%<br>Rating: %{customdata}<extra></extra>",
        customdata=ratings,
    ))

    fig.update_layout(**_base_layout(
        title=dict(
            text=f"TC Development Probability — {system_name}",
            y=0.95, yanchor="top", x=0.5, xanchor="center",
            font=dict(size=14, color="#e2e8f0"),
        ),
        yaxis_title="Probability (%)",
        yaxis=dict(range=[0, 115]),
        height=390,
        margin=dict(l=50, r=30, t=70, b=70),
        xaxis=dict(tickangle=-45),
        showlegend=False,
    ))
    return fig


def create_tc_movement_chart(
    movement_data: List[dict],
    system_name: str = "System",
) -> go.Figure:
    """Line chart of system movement speed (km/h) over time."""
    fig = go.Figure()

    if not movement_data:
        return empty_chart("No movement data available")

    times = []
    speeds = []
    for m in movement_data:
        try:
            t = datetime.fromisoformat(m["time"].replace("Z", "+00:00"))
        except Exception:
            continue
        times.append(t)
        speeds.append(m.get("speed_kmh", 0))

    if not times:
        return empty_chart("No movement data available")

    fig.add_trace(go.Scatter(
        x=times,
        y=speeds,
        mode="lines+markers",
        name="Movement Speed",
        line=dict(color="#22d3ee", width=2.5),
        marker=dict(size=7, color="#22d3ee", line=dict(width=1, color="#1e293b")),
        fill="tozeroy",
        fillcolor="rgba(34, 211, 238, 0.1)",
        hovertemplate="<b>%{x}</b><br>Speed: %{y:.1f} km/h<extra></extra>",
    ))

    fig.update_layout(**_base_layout(
        title=f"Movement Speed — {system_name}",
        yaxis_title="Speed (km/h)",
        height=340,
        margin=dict(l=50, r=30, t=40, b=50),
        showlegend=False,
    ))
    return fig
