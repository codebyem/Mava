# Mava

A self-hosted Strava analytics dashboard for triathletes and cyclists.  
Built with Flask + Python. Connects to your Strava account via OAuth.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Dashboard** — distance, time, elevation at a glance
- **Activities** — filterable list by sport (swim / bike / run) with power and HR data
- **Activity Detail** — route map, power + HR chart, elevation profile, lap splits, power best efforts, power zone distribution
- **Analytics** — Performance Management Chart (CTL / ATL / TSB), weekly volume, year-over-year comparison, cycling power trend
- **Records** — personal best progression over time for each sport and distance/duration
- **Settings** — FTP and body weight for power zone and W/kg calculations

---

## Requirements

- Python 3.10+
- A Strava account with activities
- A Strava API application (free)

---

## Setup

### 1. Create a Strava API App

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an application — set **Authorization Callback Domain** to `localhost`
3. Note your **Client ID** and **Client Secret**

### 2. Clone & install

```bash
git clone https://github.com/your-username/mava.git
cd mava
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://localhost:5000/callback
FLASK_SECRET_KEY=your-random-secret   # see note below
```

> **Generating a secret key:**
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

### 4. Configure user settings

```bash
cp settings.example.json settings.json
```

Edit `settings.json` and add your FTP (watts) and body weight (kg):

```json
{
  "ftp": 280,
  "weight": 72.0
}
```

Both values are optional — the app works without them, but power zones and W/kg metrics won't be available.

### 5. Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) and connect with Strava.

---

## Notes

- **Records / Cycling power durations** — fetching power best efforts (5min, 10min, etc.) requires downloading stream data for each qualifying ride. This can take 20–30 seconds depending on how many rides you have.
- **Token refresh** — access tokens are refreshed automatically when they expire. No need to re-login.
- **Data window** — Analytics uses the last 24 months; Records uses the last 36 months.

---

## Tech Stack

- **Backend** — Python, Flask
- **Frontend** — Jinja2 templates, vanilla CSS (emma. Design System), Chart.js, Leaflet.js
- **Fonts** — DM Sans, DM Mono (self-hosted)
- **Icons** — Material Symbols Rounded (self-hosted)
- **Maps** — OpenStreetMap via Leaflet (no API key required)

---

## License

MIT
