from flask import Flask, render_template

from strava_service import StravaService

app = Flask(__name__)

strava = StravaService()
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/home")
def home():
    """
    Übersichtsseite
    """
    athlete = strava.get_athlete_info()
    activities = strava.get_activities(per_page=30)
    stats = strava.calculate_stats(activities)
    recent_activities = activities[:5]

    return render_template(
        "home.html",
        athlete=athlete,
        activities=recent_activities,
        stats=stats
    )

# ============================================================
# TESTSEITEN - Zum rumprobieren
# ============================================================


@app.route("/emmatest")
def emma_test():
    """
    Available data to use in template:
    - athlete: Full athlete info
    - all_activities: List of 50 recent activities
    - stats: Calculated statistics
    """
    athlete = strava.get_athlete_info()
    all_activities = strava.get_activities(per_page=50)
    stats = strava.calculate_stats(all_activities)
    formatted_activities = [
        strava.format_activity_for_display(a) for a in all_activities
    ]

    return render_template(
        "emmatest.html",
        athlete=athlete,
        all_activities=formatted_activities,
        stats=stats
    )


@app.route("/clemenstest")
def clemens_test():
    """
    TODO Clemi:
    1. Schau dir die Daten an die wir schon haben (athlete, activities, stats)
    2. home.html kannst du als Refereenz nehmen
    3. Ersetze die Testdaten durch echte mit der Syntax {{ variable_name }}
    4. Mach hübsch mit Tailwind-Vorlagen

    Daten die wir schon haben:
    - athlete:
        - athlete.firstname
        - athlete.lastname
        - athlete.profile

    - activities:
        - activity.name
        - activity.distance_km
        - activity.moving_time_minutes
        - activity.average_speed_kmh
        - activity.start_date_short

    - stats:
        - stats.total_distance
        - stats.activity_count
        - stats.total_time
        - stats.avg_speed
    """
    athlete = strava.get_athlete_info()
    all_activities = strava.get_activities(per_page=20)
    stats = strava.calculate_stats(all_activities)
    formatted_activities = [
        strava.format_activity_for_display(a) for a in all_activities[:10]
    ]

    return render_template(
        "clemenstest.html",
        athlete=athlete,
        activities=formatted_activities,
        stats=stats
    )


if __name__ == "__main__":
    app.run(debug=True)
