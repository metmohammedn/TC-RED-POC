# TC-RED: Tropical Cyclone Real-time Event Dashboard

A standalone interactive dashboard for tracking, visualising, and analysing tropical cyclones in the Australian region. Built for energy and resources clients who need real-time situational awareness of TC threats to offshore and onshore assets.

![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Dash](https://img.shields.io/badge/dash-4.0-orange)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-proprietary-red)

## Features

### Interactive Cyclone Tracking Map
- Multi-system display — track several active cyclones simultaneously
- Analysis (observed) and forecast track lines with position markers colour-coded by Australian TC category (TL through Cat 5)
- BoM forecast confidence cones and confidence areas with time-slider playback
- 250 km danger zone overlay around current position
- Wind radii visualisation (gale, storm, hurricane force) by quadrant
- Four map tile styles: CARTO Dark, CARTO Voyager, Esri Topo, OpenStreetMap

### Client Asset Management
- 23 pre-configured energy/resources clients (Santos, Chevron, Woodside, Shell, INPEX, etc.)
- Per-client custom locations (offshore platforms, onshore facilities)
- Category-specific threat distance thresholds
- Configurable range rings for each asset location

### Gale Arrival Time Forecasting
- Estimates when gale-force winds (34+ kt) will reach each client location
- Uses linear interpolation between forecast steps for sub-step accuracy
- Considers maximum gale radius across all four quadrants (conservative approach)
- Accounts for client-defined range ring boundaries as trigger distances

### Analysis Charts
- **Intensity chart** — dual-axis time series of maximum sustained wind (kt) and central pressure (hPa), with category boundary lines and analysis/forecast divider
- **TC probability chart** — development probability over the 7-day outlook, colour-coded by rating
- **Movement speed chart** — track speed (km/h) over time

### Location Impact Assessment
- Distance and bearing from TC to 14 major Australian coastal cities
- Threat level classification (Extreme/High/Moderate/Low/Minimal) based on proximity
- Per-client location impacts with gale arrival countdown

### Additional
- 8 Australian timezone options (UTC, AWST, ACST, AEST, and daylight-saving variants)
- Full advisory text display (7-day forecast + track discussion)
- Optional Redis caching for performance
- Google Analytics 4 integration for usage tracking
- Docker deployment with health checks
- `/health` endpoint for load balancer probes

## Architecture

```
tc-standalone/
├── app.py                  # Dash application entry point
├── config.py               # Environment-driven configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Production container
├── docker-compose.yml      # App + Redis stack
├── .env.example            # Environment variable template
├── src/
│   ├── pages/
│   │   └── tc.py           # Main page layout + callbacks (~1600 lines)
│   ├── components/
│   │   ├── map_components.py   # Dash-Leaflet map builder
│   │   └── tc_charts.py       # Plotly chart factories
│   ├── services/
│   │   └── tc_service.py      # Data loading, geospatial analysis, gale arrival (~900 lines)
│   ├── data/
│   │   └── cache.py           # Redis cache wrapper (graceful degradation)
│   └── utils/
│       └── constants.py       # Categories, colours, thresholds, locations, map tiles
├── data/
│   ├── tc_data/            # BoM advisory JSON files (50 files, 13 systems)
│   └── tc_config/          # Client configuration files (23 clients)
└── assets/
    ├── icons/              # TC category marker icons (Cat 1–5, Tropical Low)
    ├── styles/             # CSS (dark theme: base, layout, components)
    └── scripts/            # GA4 event tracking
```

## Data

The app ships with **50 archived BoM tropical cyclone advisories** covering **13 systems** from the 2024–25 and 2025–26 Australian cyclone seasons:

| System | Name | Peak Status | Advisories |
|--------|------|-------------|------------|
| AU202425_29U | Errol | Severe Tropical Cyclone | 3 |
| AU202526_34U | Narelle | Severe Tropical Cyclone | 8 |
| AU202526_12U | (unnamed) | Ex-Tropical Cyclone | 19 |
| AU202526_11U | Jenna | Ex-Tropical Cyclone | 1 |
| AU202526_02U | (unnamed) | Tropical Cyclone | 3 |
| AU202526_03U | (unnamed) | Tropical Low | 3 |
| AU202526_15U | (unnamed) | Tropical Low | 3 |
| AU202425_30U | (unnamed) | Tropical Low | 3 |
| AU202526_16U | (unnamed) | Tropical Low | 2 |
| AU202526_14U | (unnamed) | Tropical Low | 2 |
| AU202526_13U | (unnamed) | Tropical Low | 1 |
| AU202425_31U | (unnamed) | Tropical Low | 1 |
| AU202526_17U | (unnamed) | Tropical Low | 1 |

> **Note:** This is a proof-of-concept using archived data. The production version will connect to live BoM advisory feeds.

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/metmohammedn/TC-RED-POC.git
cd TC-RED-POC

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config (optional)
cp .env.example .env

# Run the app
python app.py
```

Open [http://localhost:8050](http://localhost:8050) in your browser.

### Docker

```bash
# Copy environment config
cp .env.example .env

# Build and run with Docker Compose (includes Redis)
docker compose up --build
```

The app will be available at [http://localhost:8050](http://localhost:8050).

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable Dash debug mode |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8050` | Server port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL (optional — app runs without it) |
| `GA_MEASUREMENT_ID` | *(empty)* | Google Analytics 4 measurement ID (leave empty to disable) |
| `GUNICORN_WORKERS` | `4` | Number of gunicorn worker processes |
| `GUNICORN_TIMEOUT` | `120` | Gunicorn worker timeout (seconds) |

## Australian TC Category Scale

The dashboard uses the official Bureau of Meteorology tropical cyclone intensity scale:

| Category | Wind Speed (kt) | Colour |
|----------|-----------------|--------|
| Tropical Low | 0–33 | Yellow |
| Category 1 | 34–47 | Green |
| Category 2 | 48–63 | Blue |
| Category 3 | 64–85 | Orange |
| Category 4 | 86–107 | Red |
| Category 5 | 108+ | Purple |

## Client Configuration

Client locations are defined in JSON files under `data/tc_config/`. Each client file specifies:

- Asset locations (lat/lon, onshore/offshore type)
- Category-specific threat distance thresholds (km)
- Range rings for map display (nautical miles)

To add a new client:
1. Create `data/tc_config/{client}_user.json` following the existing format
2. Add an entry to `data/tc_config/users_registry.json`

## Tech Stack

- **Framework:** [Dash](https://dash.plotly.com/) 4.0 (Plotly)
- **UI Components:** [Dash Mantine Components](https://www.dash-mantine-components.com/) 0.14+
- **Maps:** [Dash Leaflet](https://dash-leaflet.com/) with CARTO/Esri/OSM tiles
- **Charts:** [Plotly](https://plotly.com/python/)
- **Data Processing:** Pandas, NumPy
- **Caching:** Redis (optional)
- **Server:** Gunicorn (production), Dash dev server (debug)
- **Container:** Docker with multi-service Compose
- **Analytics:** Google Analytics 4

## Production Deployment

The app is Docker-ready for deployment on AWS ECS Fargate or similar container platforms:

- **Health check:** `GET /health` returns `200 OK` (used by Docker HEALTHCHECK and ALB target groups)
- **Gunicorn:** 4 workers by default, configurable via `GUNICORN_WORKERS`
- **Redis:** Optional sidecar for caching (ElastiCache in production)
- **Stateless:** No local filesystem writes — safe for horizontal scaling

## License

Proprietary. All rights reserved.
