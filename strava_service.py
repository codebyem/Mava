"""
Strava Data Service
Alle Methoden um Strava-Daten zu laden und aufzubereiten.
"""

import math
import requests
from datetime import datetime, timedelta
from collections import defaultdict

class StravaService:

    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://www.strava.com/api/v3"
        self.headers = {'Authorization': f'Bearer {self.access_token}'}

    def _get(self, url, params=None):
        """Make a GET request."""
        response = requests.get(url, headers=self.headers, params=params)
        return response

    # ============================================================
    # ATHLETEN METHODEN
    # ============================================================

    def get_athlete_info(self):
        """
        Returns: dict mit firstname, lastname, profile, city, country, etc.
        """
        url = f"{self.base_url}/athlete"
        response = self._get(url)
        return response.json() if response.status_code == 200 else {}

    def get_athlete_stats(self):
        """
        Returns: All-time Statistiken vom Athleten
        """
        athlete_id = self.get_athlete_info().get('id')
        if not athlete_id:
            return {}
        url = f"{self.base_url}/athlete/{athlete_id}/stats"
        response = self._get(url)
        return response.json() if response.status_code == 200 else {}

    # ============================================================
    # ACTIVITY METHODEN
    # ============================================================

    def get_activities(self, per_page=30, page=1, after=None):
        """
        Args:
            per_page: Anzahl (max 200)
            page: Seitenzahl
            after: Unix-Timestamp, nur Aktivitäten danach

        Returns: Liste von Aktivitäten
        """
        url = f"{self.base_url}/athlete/activities"
        params = {'per_page': per_page, 'page': page}
        if after:
            params['after'] = after
        response = self._get(url, params=params)
        return response.json() if response.status_code == 200 else []

    def get_recent_activities(self, count=5):
        return self.get_activities(per_page=count, page=1)

    def get_activity_by_id(self, activity_id):
        """
        Returns: Detaillierte Daten einer Aktivität (inkl. splits, best efforts)
        """
        url = f"{self.base_url}/activities/{activity_id}"
        response = self._get(url)
        return response.json() if response.status_code == 200 else {}

    def get_bulk_activities(self, months=6):
        """
        Lädt alle Aktivitäten der letzten N Monate (mit Paginierung).
        Returns: Liste aller Aktivitäten
        """
        after = int((datetime.now() - timedelta(days=months * 30)).timestamp())
        all_activities = []
        page = 1
        while True:
            batch = self.get_activities(per_page=200, page=page, after=after)
            if not batch:
                break
            all_activities.extend(batch)
            if len(batch) < 200:
                break
            page += 1
        return all_activities

    def get_activity_streams(self, activity_id):
        """
        Lädt Zeitreihen-Daten (Watt, HR, Höhe, Geschwindigkeit, Distanz).
        Returns: Dict mit Streamdaten pro Typ
        """
        url = f"{self.base_url}/activities/{activity_id}/streams"
        params = {
            'keys': 'time,watts,heartrate,altitude,velocity_smooth,distance,latlng',
            'key_by_type': 'true'
        }
        response = self._get(url, params=params)
        return response.json() if response.status_code == 200 else {}

    def get_activity_laps(self, activity_id):
        """
        Returns: Liste der Runden/Splits einer Aktivität
        """
        url = f"{self.base_url}/activities/{activity_id}/laps"
        response = self._get(url)
        return response.json() if response.status_code == 200 else []

    # ============================================================
    # STATISTISCHE METHODEN
    # ============================================================

    def get_sport_type(self, activity):
        """Normalisiert Strava-Sporttyp auf swim/bike/run/other"""
        sport = activity.get('sport_type') or activity.get('type', '')
        if sport in {'Swim'}:
            return 'swim'
        elif sport in {'Ride', 'VirtualRide', 'EBikeRide', 'GravelRide', 'MountainBikeRide'}:
            return 'bike'
        elif sport in {'Run', 'VirtualRun', 'TrailRun'}:
            return 'run'
        return 'other'

    def calculate_stats(self, activities):
        """
        Berechnet Gesamtstatistiken für eine Liste von Aktivitäten.
        Returns: dict mit total_distance, activity_count, total_time, avg_speed, total_elevation
        """
        if not activities:
            return {
                'total_distance': 0,
                'activity_count': 0,
                'total_time': 0,
                'avg_speed': 0,
                'total_elevation': 0
            }

        total_distance = sum(a.get('distance', 0) for a in activities) / 1000
        total_time = sum(a.get('moving_time', 0) for a in activities) / 3600
        total_elevation = sum(a.get('total_elevation_gain', 0) for a in activities)
        avg_speed = (total_distance / total_time) if total_time > 0 else 0

        return {
            'total_distance': round(total_distance, 1),
            'activity_count': len(activities),
            'total_time': round(total_time, 1),
            'avg_speed': round(avg_speed, 1),
            'total_elevation': round(total_elevation, 0)
        }

    def calculate_pmc_data(self, activities, days=180, ftp=None):
        """
        Berechnet den Performance Management Chart (PMC).
        Für Radeinheiten mit NP + FTP wird echter Power-TSS berechnet,
        sonst suffer_score als Proxy.

        TSS (Power) = duration_s × (NP/FTP)² / 36

        Returns: Liste von {date, tss, ctl, atl, tsb, tss_source}
            - CTL = Chronic Training Load (Fitness, τ=42 Tage)
            - ATL = Acute Training Load (Ermüdung, τ=7 Tage)
            - TSB = Training Stress Balance (Form = CTL - ATL)
        """
        daily_tss = defaultdict(float)
        power_tss_count = 0
        for activity in activities:
            date_str = activity.get('start_date', '')[:10]
            if not date_str:
                continue
            np_watts = activity.get('weighted_average_watts')
            duration = activity.get('moving_time', 0)
            sport = self.get_sport_type(activity)
            if ftp and sport == 'bike' and np_watts and duration:
                if_factor = np_watts / ftp
                tss = duration * if_factor ** 2 / 36
                power_tss_count += 1
            else:
                tss = activity.get('suffer_score') or 0
            daily_tss[date_str] += tss

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        ctl = 0.0
        atl = 0.0
        pmc_data = []
        current = start_date

        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            tss = daily_tss.get(date_str, 0)
            ctl = ctl + (tss - ctl) * (1 - math.exp(-1 / 42))
            atl = atl + (tss - atl) * (1 - math.exp(-1 / 7))
            tsb = ctl - atl
            pmc_data.append({
                'date': date_str,
                'tss': round(tss, 1),
                'ctl': round(ctl, 1),
                'atl': round(atl, 1),
                'tsb': round(tsb, 1)
            })
            current += timedelta(days=1)

        return {'data': pmc_data, 'power_tss_count': power_tss_count}

    def get_weekly_volume_by_sport(self, activities):
        """
        Berechnet wöchentliches Trainingsvolumen (km) nach Sportart.
        Returns: Liste von {week, swim, bike, run, other} (sortiert nach Datum)
        """
        weekly_data = defaultdict(lambda: {'swim': 0.0, 'bike': 0.0, 'run': 0.0, 'other': 0.0})

        for activity in activities:
            date_str = activity.get('start_date', '')[:10]
            if not date_str:
                continue
            date = datetime.strptime(date_str, '%Y-%m-%d')
            week_start = date - timedelta(days=date.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            sport = self.get_sport_type(activity)
            distance_km = activity.get('distance', 0) / 1000
            weekly_data[week_key][sport] += distance_km

        sorted_weeks = sorted(weekly_data.items())
        return [
            {
                'week': k,
                'swim': round(v['swim'], 1),
                'bike': round(v['bike'], 1),
                'run': round(v['run'], 1),
                'other': round(v['other'], 1)
            }
            for k, v in sorted_weeks
        ]

    # ============================================================
    # JAHRESVERGLEICH & TRAININGSTAGE
    # ============================================================

    def get_year_comparison(self, activities):
        """
        Durchschnittliche Wochenkilometer pro Sportart, gruppiert nach Jahr.
        Returns: [{year, swim_avg, bike_avg, run_avg, swim_total, bike_total, run_total}]
        """
        yearly = defaultdict(lambda: {'swim': 0.0, 'bike': 0.0, 'run': 0.0})
        current_year = datetime.now().year

        for a in activities:
            date_str = a.get('start_date', '')[:10]
            if not date_str:
                continue
            year = int(date_str[:4])
            sport = self.get_sport_type(a)
            distance_km = a.get('distance', 0) / 1000
            if sport in ('swim', 'bike', 'run'):
                yearly[year][sport] += distance_km

        result = []
        for year in sorted(yearly.keys()):
            data = yearly[year]
            if year == current_year:
                start_of_year = datetime(year, 1, 1)
                weeks = max(1, (datetime.now() - start_of_year).days / 7)
            else:
                weeks = 52
            result.append({
                'year': year,
                'swim_avg': round(data['swim'] / weeks, 1),
                'bike_avg': round(data['bike'] / weeks, 1),
                'run_avg':  round(data['run']  / weeks, 1),
                'swim_total': int(data['swim']),
                'bike_total': int(data['bike']),
                'run_total':  int(data['run']),
            })
        return result

    def get_training_day_stats(self, activities):
        """
        Trainingstage-Statistik für das aktuelle Jahr.
        Returns: {days_elapsed, training_days, rest_days, training_pct,
                  double_day_count, double_days [{date, count, names}]}
        """
        current_year = datetime.now().year
        today = datetime.now().date()
        start_of_year = datetime(current_year, 1, 1).date()
        days_elapsed = (today - start_of_year).days + 1

        year_activities = [
            a for a in activities
            if a.get('start_date', '').startswith(str(current_year))
        ]

        day_map = defaultdict(list)
        for a in year_activities:
            date_str = a.get('start_date', '')[:10]
            day_map[date_str].append(a.get('name', 'Activity'))

        training_days = len(day_map)
        rest_days = days_elapsed - training_days
        training_pct = round(100 * training_days / days_elapsed, 1) if days_elapsed > 0 else 0

        double_days = sorted(
            [{'date': d, 'count': len(names), 'names': names}
             for d, names in day_map.items() if len(names) >= 2],
            key=lambda x: x['date'],
            reverse=True
        )

        return {
            'days_elapsed': days_elapsed,
            'training_days': training_days,
            'rest_days': rest_days,
            'training_pct': training_pct,
            'double_day_count': len(double_days),
            'double_days': double_days[:10],
            'year': current_year,
        }

    # ============================================================
    # POWER ANALYSE METHODEN
    # ============================================================

    @staticmethod
    def calculate_power_zones(watts_stream, ftp):
        """
        Bins each second of a watts stream into a power zone.
        Returns list of {name, label, color, seconds, minutes, percent}
        """
        zones = [
            {'name': 'Z1 Recovery',  'label': 'Z1', 'color': '#94A3B8', 'min': 0,    'max': 0.55},
            {'name': 'Z2 Endurance', 'label': 'Z2', 'color': '#60A5FA', 'min': 0.55, 'max': 0.75},
            {'name': 'Z3 Tempo',     'label': 'Z3', 'color': '#4ADE80', 'min': 0.75, 'max': 0.90},
            {'name': 'Z4 Threshold', 'label': 'Z4', 'color': '#FBBF24', 'min': 0.90, 'max': 1.05},
            {'name': 'Z5 VO2max',    'label': 'Z5', 'color': '#F87171', 'min': 1.05, 'max': 1.20},
            {'name': 'Z6 Anaerobic', 'label': 'Z6', 'color': '#C084FC', 'min': 1.20, 'max': float('inf')},
        ]
        counts = [0] * 6
        total = 0
        for w in watts_stream:
            if w is None:
                continue
            pct = w / ftp
            total += 1
            for i, z in enumerate(zones):
                if pct < z['max']:
                    counts[i] += 1
                    break

        result = []
        for i, z in enumerate(zones):
            secs = counts[i]
            result.append({
                'name': z['name'],
                'label': z['label'],
                'color': z['color'],
                'seconds': secs,
                'minutes': round(secs / 60, 1),
                'percent': round(100 * secs / total, 1) if total > 0 else 0,
            })
        return result

    @staticmethod
    def calculate_best_efforts(watts_stream):
        """
        Sliding window max over fixed durations (~1 Hz stream).
        Returns list of {duration, label, watts}
        """
        durations = [
            (5,    '5 sec'),
            (10,   '10 sec'),
            (30,   '30 sec'),
            (60,   '1 min'),
            (120,  '2 min'),
            (300,  '5 min'),
            (600,  '10 min'),
            (1200, '20 min'),
        ]
        clean = [w for w in watts_stream if w is not None]
        n = len(clean)
        result = []
        for dur, label in durations:
            if n < dur:
                continue
            # sliding window sum → max
            window_sum = sum(clean[:dur])
            best = window_sum
            for i in range(1, n - dur + 1):
                window_sum += clean[i + dur - 1] - clean[i - 1]
                if window_sum > best:
                    best = window_sum
            result.append({
                'duration': dur,
                'label': label,
                'watts': round(best / dur),
            })
        return result

    def get_power_trend(self, activities):
        """
        Returns power data for bike rides that have power.
        [{date, name, np, avg_watts, distance_km}]
        """
        trend = []
        bike_acts = [a for a in activities if self.get_sport_type(a) == 'bike']
        bike_acts = sorted(bike_acts, key=lambda a: a.get('start_date', ''))
        for a in bike_acts:
            np_val = a.get('weighted_average_watts')
            avg = a.get('average_watts')
            if not np_val and not avg:
                continue
            trend.append({
                'date': a.get('start_date', '')[:10],
                'name': a.get('name', 'Ride'),
                'np': np_val or avg,
                'avg_watts': avg,
                'distance_km': round(a.get('distance', 0) / 1000, 1),
            })
        return trend

    # ============================================================
    # RECORDS METHODEN
    # ============================================================

    @staticmethod
    def _best_effort_watts(watts_stream, duration_seconds):
        """Sliding window max average power for a given duration."""
        clean = [w for w in watts_stream if w is not None]
        n = len(clean)
        if n < duration_seconds:
            return None
        window = sum(clean[:duration_seconds])
        best = window
        for i in range(1, n - duration_seconds + 1):
            window += clean[i + duration_seconds - 1] - clean[i - 1]
            if window > best:
                best = window
        return round(best / duration_seconds)

    def get_power_records(self, activities, duration_seconds):
        """
        Record progression for a specific power duration (bike only).
        Fetches watts streams for qualifying activities (sorted chronologically).
        Returns: {records: [{date, watts, name, id}], analyzed: int, current_best: int|None}
        """
        bike_acts = [
            a for a in activities
            if self.get_sport_type(a) == 'bike'
            and a.get('moving_time', 0) >= duration_seconds
        ]
        bike_acts = sorted(bike_acts, key=lambda a: a.get('start_date', ''))

        records = []
        current_best = 0

        for activity in bike_acts:
            url = f"{self.base_url}/activities/{activity['id']}/streams"
            resp = self._get(url, params={'keys': 'watts', 'key_by_type': 'true'})
            if resp.status_code != 200:
                continue
            watts = resp.json().get('watts', {}).get('data', [])
            if not watts:
                continue
            best = self._best_effort_watts(watts, duration_seconds)
            if best and best > current_best:
                current_best = best
                records.append({
                    'date': activity.get('start_date', '')[:10],
                    'watts': best,
                    'name': activity.get('name', 'Ride'),
                    'id': activity.get('id'),
                })

        return {
            'records': records,
            'analyzed': len(bike_acts),
            'current_best': current_best if current_best > 0 else None,
        }

    def get_pace_records(self, activities, sport, distance_km):
        """
        Record progression for run/swim over a target distance.
        Uses activity-level data only — no stream fetches needed.
        Matches activities within ±15% of the target distance.
        Returns: {records: [...], analyzed, current_best (sec/km), current_best_formatted}
        """
        margin = 0.15
        min_m = distance_km * (1 - margin) * 1000
        max_m = distance_km * (1 + margin) * 1000

        qualifying = [
            a for a in activities
            if self.get_sport_type(a) == sport
            and min_m <= a.get('distance', 0) <= max_m
            and a.get('average_speed', 0) > 0
        ]
        qualifying = sorted(qualifying, key=lambda a: a.get('start_date', ''))

        records = []
        best_pace = float('inf')

        for activity in qualifying:
            pace = 1000 / activity['average_speed']  # sec/km
            if pace < best_pace:
                best_pace = pace
                records.append({
                    'date': activity.get('start_date', '')[:10],
                    'pace_seconds': round(pace),
                    'pace_formatted': f"{int(pace // 60)}:{int(pace % 60):02d}",
                    'name': activity.get('name', 'Activity'),
                    'id': activity.get('id'),
                    'distance_km': round(activity.get('distance', 0) / 1000, 2),
                })

        best_fmt = (f"{int(best_pace // 60)}:{int(best_pace % 60):02d}"
                    if best_pace != float('inf') else None)
        return {
            'records': records,
            'analyzed': len(qualifying),
            'current_best': round(best_pace) if best_pace != float('inf') else None,
            'current_best_formatted': best_fmt,
        }

    # ============================================================
    # HELFER METHODEN
    # ============================================================

    def format_activity_for_display(self, activity):
        """
        Formatiert eine Aktivität zur Anzeige.
        Returns: Aufbereitetes dict mit allen relevanten Feldern
        """
        sport_type = self.get_sport_type(activity)
        distance = activity.get('distance', 0)
        moving_time = activity.get('moving_time', 0)
        avg_speed = activity.get('average_speed', 0)

        # Pace (min/km) für Laufen und Schwimmen
        pace_min_km = None
        if sport_type in ('run', 'swim') and avg_speed > 0:
            pace_sec_km = 1000 / avg_speed
            pace_min_km = f"{int(pace_sec_km // 60)}:{int(pace_sec_km % 60):02d}"

        hours = moving_time // 3600
        minutes = (moving_time % 3600) // 60
        duration_formatted = f"{hours}:{minutes:02d}h" if hours > 0 else f"{minutes} min"

        return {
            'id': activity.get('id'),
            'name': activity.get('name', 'Unnamed Activity'),
            'description': activity.get('description', ''),
            'sport_type': sport_type,
            'raw_type': activity.get('sport_type') or activity.get('type', ''),
            'distance_km': round(distance / 1000, 2),
            'moving_time_seconds': moving_time,
            'duration_formatted': duration_formatted,
            'average_speed_kmh': round(avg_speed * 3.6, 1),
            'pace_min_km': pace_min_km,
            'elevation_gain': round(activity.get('total_elevation_gain', 0), 0),
            'average_watts': activity.get('average_watts'),
            'weighted_average_watts': activity.get('weighted_average_watts'),
            'average_heartrate': activity.get('average_heartrate'),
            'max_heartrate': activity.get('max_heartrate'),
            'suffer_score': activity.get('suffer_score'),
            'kilojoules': activity.get('kilojoules'),
            'start_date': activity.get('start_date', ''),
            'start_date_short': activity.get('start_date', '')[:10],
        }
