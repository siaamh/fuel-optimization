# ⛽ Fuel Route Optimizer

A Django REST API that computes the most **cost-effective fueling strategy** for a road trip across the USA. Given a start and finish location, it returns the optimal fuel stops along the driving route to minimize total spend — factoring in fuel prices, tank capacity, and vehicle range.

---

## 🚀 Features

- 📍 **Geocoding** — Resolves plain-text US locations to coordinates via [Nominatim](https://nominatim.org/)
- 🗺️ **Route Planning** — Gets driving routes (distance, duration, geometry) via [OpenRouteService](https://openrouteservice.org/)
- ⛽ **Smart Fueling Algorithm** — Greedy look-ahead strategy: buy cheap now, defer when a cheaper station is reachable ahead
- 💰 **Total Cost Calculation** — Returns exact spend based on 10 MPG and per-gallon prices
- 🗃️ **1,500+ Fuel Stations** — Loaded from a real OPIS truckstop price dataset, geocoded and stored in MySQL

---

## 🧠 How the Optimization Works

> Vehicle assumptions: **500-mile max range**, **10 MPG**, **50-gallon tank**

The algorithm walks stations in order along the route:

1. **Can a cheaper station be reached ahead on the current tank?**
   - **Yes** → Buy just enough fuel to reach that cheaper station
   - **No** → This is the best price reachable — fill up the tank

This greedy look-ahead avoids overpaying at expensive stations when a cheaper one is within range.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 6.1 + Django REST Framework |
| Database | MySQL |
| Routing API | OpenRouteService (ORS) |
| Geocoding | Nominatim (OpenStreetMap) |
| Station Geocoding | Geoapify |
| Distance Math | Pure-Python Haversine (no PostGIS needed) |

---

## 📦 Setup

### 1. Clone & create virtual environment

```bash
git clone https://github.com/your-username/fuel-optimization.git
cd fuel-optimization
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
pip install mysqlclient
```

### 2. Create MySQL database

```sql
CREATE DATABASE fuel_optimization CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
ORS_API_KEY=your_openrouteservice_api_key
GEOAPIFY_API_KEY=your_geoapify_api_key

DB_NAME=fuel_optimization
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

ROUTE_BUFFER_MILES=5
```

Get a free ORS API key at [openrouteservice.org](https://openrouteservice.org/dev/#/signup).

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Load fuel station data

```bash
python manage.py load_stations --csv fuel_stations_geocoded.csv
```

> Loads ~1,500 geocoded truckstops with retail fuel prices into MySQL.

### 6. Start the server

```bash
python manage.py runserver
```

---

## 📡 API Reference

### `POST /api/optimize/`

Find the optimal fuel stops between two US locations.

**Request**

```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA"
}
```

**Response**

```json
{
  "fuel_stops": [
    {
      "station_id": 5,
      "name": "ACI TRUCK STOP",
      "price_per_gallon": 3.079,
      "gallons": 7.058,
      "cost": 21.73,
      "distance_from_start_miles": 70.58,
      "latitude": 40.9262077,
      "longitude": -75.0926763
    },
    ...
  ],
  "total_fuel_cost": 847.89,
  "stations_checked": 114
}
```

**Error Response** (invalid location)

```json
{
  "error": "Could not compute a route for the given locations. Check that both locations are valid US addresses."
}
```

---

## 🧪 Example

```bash
curl -X POST http://127.0.0.1:8000/api/optimize/ \
  -H "Content-Type: application/json" \
  -d '{"start": "New York, NY", "finish": "Los Angeles, CA"}'
```

**New York → Los Angeles result:**

| Stop | Station | $/gal | Gallons | Cost | Mile |
|------|---------|-------|---------|------|------|
| 1 | ACI Truck Stop, PA | $3.08 | 7.1 | $21.73 | 71 |
| 2 | Truck World Truckstop, OH | $3.26 | 31.8 | $103.49 | 388 |
| 3 | Petro Stopping Center, IN | $3.25 | 37.6 | $122.32 | 765 |
| 4 | Underwood Truck Stop I-80, NE | $3.00 | 45.9 | $137.86 | 1,224 |
| ... | ... | ... | ... | ... | ... |
| **Total** | | | | **$847.89** | 2,790 mi |

---

## 📂 Project Structure

```
fuel-optimization/
├── api/
│   ├── management/
│   │   └── commands/
│   │       ├── geocode_stations.py   # Geocode raw CSV via Geoapify
│   │       └── load_stations.py      # Seed MySQL from geocoded CSV
│   ├── migrations/
│   ├── services/
│   │   ├── routing.py       # ORS route + Nominatim geocoding
│   │   ├── stations.py      # Haversine route-buffer station filter
│   │   └── optimizer.py     # Greedy look-ahead fueling algorithm
│   ├── models.py            # FuelStation model
│   ├── serializers.py       # Request validation
│   └── views.py             # Orchestration: route → stations → optimize
├── config/
│   ├── settings.py
│   └── urls.py
├── fuel_stations_geocoded.csv
├── requirements.txt
└── .env
```

---

## ⚙️ Management Commands

| Command | Description |
|---------|-------------|
| `python manage.py geocode_stations` | Geocode raw OPIS CSV via Geoapify → `fuel_stations_geocoded.csv` |
| `python manage.py load_stations --csv <path>` | Load geocoded CSV into MySQL (idempotent) |

---

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ROUTE_BUFFER_MILES` | `5` | Max distance from route a station can be to be considered |
| `ORS_API_KEY` | — | OpenRouteService API key (required) |
| `GEOAPIFY_API_KEY` | — | Only needed to re-run geocoding |

---

## 📋 Requirements

- Python 3.12+
- MySQL 8.0+
- Free [OpenRouteService](https://openrouteservice.org/dev/#/signup) API key

---

## 📄 License

MIT
