import json
import time
from flask import Flask, render_template, request, redirect, url_for, session
import requests

from config import Config
from strava_service import StravaService

app = Flask(__name__)
app.config.from_object(Config)


def logged_in():
    return 'access_token' in session


def _refresh_token_if_needed():
    """Refresh the Strava access token if it has expired."""
    if session.get('expires_at', 0) > time.time() + 60:
        return  # still valid (with 60s buffer)

    response = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': app.config['STRAVA_CLIENT_ID'],
        'client_secret': app.config['STRAVA_CLIENT_SECRET'],
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token'],
    })

    if response.status_code == 200:
        data = response.json()
        session['access_token'] = data['access_token']
        session['refresh_token'] = data['refresh_token']
        session['expires_at'] = data['expires_at']
    else:
        session.clear()


def get_strava():
    """Return a StravaService instance, refreshing the token first if needed."""
    _refresh_token_if_needed()
    return StravaService(session['access_token'])


def load_settings():
    try:
        with open('settings.json') as f:
            return json.load(f)
    except Exception:
        return {'ftp': None, 'weight': None}


def save_settings(data):
    with open('settings.json', 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================
# AUTH
# ============================================================

@app.route("/")
def index():
    if logged_in():
        return redirect(url_for('home'))
    return render_template("login.html")


@app.route("/login")
def login():
    params = {
        'client_id': app.config['STRAVA_CLIENT_ID'],
        'redirect_uri': app.config['STRAVA_REDIRECT_URI'],
        'response_type': 'code',
        'scope': 'activity:read_all,profile:read_all',
    }
    auth_url = "https://www.strava.com/oauth/authorize?" + "&".join(f"{k}={v}" for k, v in params.items())
    return redirect(auth_url)


@app.route("/callback")
def callback():
    try:
        code = request.args.get('code')
        print("CODE:", code)

        if not code:
            return "No code received"

        response = requests.post("https://www.strava.com/oauth/token", data={
            'client_id': app.config['STRAVA_CLIENT_ID'],
            'client_secret': app.config['STRAVA_CLIENT_SECRET'],
            'code': code,
            'grant_type': 'authorization_code',
        })

        print("STATUS:", response.status_code)
        print("TEXT:", response.text)

        if response.status_code != 200:
            return f"Error from Strava: {response.text}"

        data = response.json()

        session['access_token'] = data['access_token']
        session['refresh_token'] = data['refresh_token']
        session['expires_at'] = data['expires_at']

        print("SESSION SET")

        return redirect(url_for('home'))

    except Exception as e:
        print("ERROR:", e)
        return f"Exception: {e}"


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))


# ============================================================
# ROUTES
# ============================================================

@app.route("/home")
def home():
    if not logged_in():
        return redirect(url_for('index'))

    strava = get_strava()
    athlete = strava.get_athlete_info()
    activities = strava.get_activities(per_page=30)
    stats = strava.calculate_stats(activities)
    recent_activities = [strava.format_activity_for_display(a) for a in activities[:5]]
    print("SESSION:", dict(session))
    return render_template(
        "home.html",
        athlete=athlete,
        activities=recent_activities,
        stats=stats
    )


@app.route("/activities")
def activities():
    if not logged_in():
        return redirect(url_for('index'))

    strava = get_strava()
    sport_filter = request.args.get('sport', 'all')
    raw_activities = strava.get_activities(per_page=100)
    formatted = [strava.format_activity_for_display(a) for a in raw_activities]

    if sport_filter != 'all':
        formatted = [a for a in formatted if a['sport_type'] == sport_filter]

    counts = {
        'all': len(raw_activities),
        'swim': sum(1 for a in raw_activities if strava.get_sport_type(a) == 'swim'),
        'bike': sum(1 for a in raw_activities if strava.get_sport_type(a) == 'bike'),
        'run': sum(1 for a in raw_activities if strava.get_sport_type(a) == 'run'),
    }

    return render_template(
        "activities.html",
        activities=formatted,
        sport_filter=sport_filter,
        counts=counts
    )


@app.route("/activity/<int:activity_id>")
def activity_detail(activity_id):
    if not logged_in():
        return redirect(url_for('index'))

    strava = get_strava()
    settings = load_settings()
    ftp = settings.get('ftp')
    weight = settings.get('weight')

    raw = strava.get_activity_by_id(activity_id)
    activity = strava.format_activity_for_display(raw)
    streams = strava.get_activity_streams(activity_id)
    laps = strava.get_activity_laps(activity_id)

    chart_data = _prepare_stream_chart(streams)
    formatted_laps = [_format_lap(lap, activity['sport_type']) for lap in laps]

    watts_stream = streams.get('watts', {}).get('data', [])
    best_efforts = []
    power_zones = []
    if watts_stream:
        best_efforts = strava.calculate_best_efforts(watts_stream)
        if ftp:
            power_zones = strava.calculate_power_zones(watts_stream, int(ftp))

    return render_template(
        "activity_detail.html",
        activity=activity,
        chart_data=chart_data,
        laps=formatted_laps,
        best_efforts=best_efforts,
        power_zones=power_zones,
        ftp=ftp,
        weight=weight,
    )


@app.route("/analytics")
def analytics():
    if not logged_in():
        return redirect(url_for('index'))

    strava = get_strava()
    settings = load_settings()
    ftp = settings.get('ftp')

    activities = strava.get_bulk_activities(months=24)
    pmc_result = strava.calculate_pmc_data(activities, ftp=int(ftp) if ftp else None)
    pmc_data = pmc_result['data']
    power_tss_count = pmc_result['power_tss_count']
    weekly_volume = strava.get_weekly_volume_by_sport(activities)
    power_trend = strava.get_power_trend(activities)
    year_comparison = strava.get_year_comparison(activities)
    training_days = strava.get_training_day_stats(activities)

    swim_acts = [a for a in activities if strava.get_sport_type(a) == 'swim']
    bike_acts = [a for a in activities if strava.get_sport_type(a) == 'bike']
    run_acts = [a for a in activities if strava.get_sport_type(a) == 'run']

    sport_stats = {
        'swim': strava.calculate_stats(swim_acts),
        'bike': strava.calculate_stats(bike_acts),
        'run': strava.calculate_stats(run_acts),
    }

    current_form = pmc_data[-1] if pmc_data else {'ctl': 0, 'atl': 0, 'tsb': 0}

    return render_template(
        "analytics.html",
        pmc_data=pmc_data,
        power_tss_count=power_tss_count,
        weekly_volume=weekly_volume,
        sport_stats=sport_stats,
        current_form=current_form,
        power_trend=power_trend,
        ftp=ftp,
        year_comparison=year_comparison,
        training_days=training_days,
    )


@app.route("/records")
def records():
    if not logged_in():
        return redirect(url_for('index'))
    return render_template("records.html")


@app.route("/api/records")
def api_records():
    if not logged_in():
        return {'error': 'unauthorized'}, 401

    sport = request.args.get('sport')
    if sport not in ('bike', 'run', 'swim'):
        return {'error': 'invalid sport'}, 400

    strava = get_strava()
    activities = strava.get_bulk_activities(months=36)

    if sport == 'bike':
        duration = int(request.args.get('duration', 1200))
        result = strava.get_power_records(activities, duration)
        result['unit'] = 'W'
    else:
        distance = float(request.args.get('distance', 5))
        result = strava.get_pace_records(activities, sport, distance)
        result['unit'] = 'min/km'

    from flask import jsonify
    return jsonify(result)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not logged_in():
        return redirect(url_for('index'))

    if request.method == "POST":
        ftp_raw = request.form.get('ftp', '').strip()
        weight_raw = request.form.get('weight', '').strip()
        data = {
            'ftp': int(ftp_raw) if ftp_raw.isdigit() else None,
            'weight': float(weight_raw) if weight_raw else None,
        }
        save_settings(data)
        return redirect('/settings')

    current = load_settings()
    return render_template("settings.html", settings=current)


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def _prepare_stream_chart(streams):
    if not streams:
        return None

    distance = streams.get('distance', {}).get('data', [])
    watts = streams.get('watts', {}).get('data', [])
    heartrate = streams.get('heartrate', {}).get('data', [])
    velocity = streams.get('velocity_smooth', {}).get('data', [])
    altitude = streams.get('altitude', {}).get('data', [])
    latlng = streams.get('latlng', {}).get('data', [])

    if not distance:
        return None

    n = len(distance)
    step = max(1, n // 500)
    indices = range(0, n, step)

    def sample(lst):
        if not lst:
            return []
        return [round(lst[i], 2) if i < len(lst) else None for i in indices]

    sampled_latlng = []
    if latlng:
        sampled_latlng = [latlng[i] for i in indices if i < len(latlng)]

    return {
        'distance': [round(d / 1000, 3) for d in sample(distance)],
        'watts': sample(watts) if watts else [],
        'heartrate': sample(heartrate) if heartrate else [],
        'speed': [round(v * 3.6, 1) if v is not None else None for v in sample(velocity)] if velocity else [],
        'altitude': sample(altitude) if altitude else [],
        'latlng': sampled_latlng,
        'has_watts': bool(watts),
        'has_heartrate': bool(heartrate),
    }


def _format_lap(lap, sport_type):
    moving_time = lap.get('moving_time', 0)
    distance = lap.get('distance', 0)
    avg_speed = lap.get('average_speed', 0)

    hours = moving_time // 3600
    minutes = (moving_time % 3600) // 60
    seconds = moving_time % 60
    duration = f"{hours}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes}:{seconds:02d}"

    pace_min_km = None
    if sport_type in ('run', 'swim') and avg_speed > 0:
        pace_sec_km = 1000 / avg_speed
        pace_min_km = f"{int(pace_sec_km // 60)}:{int(pace_sec_km % 60):02d}"

    return {
        'lap_index': lap.get('lap_index', 0),
        'name': lap.get('name', f"Lap {lap.get('lap_index', '')}"),
        'distance_km': round(distance / 1000, 2),
        'duration': duration,
        'average_watts': lap.get('average_watts'),
        'average_heartrate': lap.get('average_heartrate'),
        'average_speed_kmh': round(avg_speed * 3.6, 1),
        'pace_min_km': pace_min_km,
        'elevation_gain': round(lap.get('total_elevation_gain', 0), 0),
    }


if __name__ == "__main__":
    app.run(debug=True)
