"""
Strava Data Service
In dieser Datei lagern wir alle Methoden um die Strava daten zu ziehen.
Ich hab jeweils bei den Methoden geschrieben, was sie zurückgeben.
Die kannst du in den Views nutzen um Daten zu bekommen :)
"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

class StravaService:

    def __init__(self):
        self.access_token = os.getenv('STRAVA_ACCESS_TOKEN')
        self.base_url = "https://www.strava.com/api/v3"
        self.headers = {'Authorization': f'Bearer {self.access_token}'}

    # ============================================================
    # ATHLETEN METHODEN - Daten über den eingeloggten Nutzer
    # ============================================================


    def get_athlete_info(self):
        """
        Zieht Basisinformationen
        Returns: Quasi kleinen Steckbrief zum Athleten (name, photo, location, etc.)
        """
        url = f"{self.base_url}/athlete"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else {}

    def get_athlete_stats(self):
        """
        Zieht Statistiken (All-time Daten, etc.)
        Returns: Statistiken
        """
        athlete_id = self.get_athlete_info().get('id')
        if not athlete_id:
            return {}
        url = f"{self.base_url}/athlete/{athlete_id}/stats"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else {}

    # ============================================================
    # ACTIVITY METHODEN - Daten zu den spezifischen Aktivitäten
    # ============================================================


    def get_activities(self, per_page=30, page=1):
        """
        Zieht Liste von Aktivitäten
        Args:
            per_page: Anzahl der aktivitäten (max 200)
            page: Seitenzahl

        Returns: Liste von Aktivitätsentitäten
        """
        url = f"{self.base_url}/athlete/activities"
        params = {'per_page': per_page, 'page': page}
        response = requests.get(url, headers=self.headers, params=params)
        return response.json() if response.status_code == 200 else []

    def get_recent_activities(self, count=5):
        """
        Zieht die aktuellsten Aktivitäten
        Args:
            count: Anzahl

        Returns: Liste von Aktivitätsentitäten
        """
        return self.get_activities(per_page=count, page=1)

    def get_activity_by_id(self, activity_id):
        """
        Zieht daten zu einer spezifischen Aktivität.

        Args:
            activity_id: Strava ID

        Returns: Detaillierte Daten zu der Aktivität
        """
        url = f"{self.base_url}/activities/{activity_id}"
        response = requests.get(url, headers=self.headers)
        return response.json() if response.status_code == 200 else {}

    # ============================================================
    # STATISTISCHE METHODEN - Berechnen von bestimmten Daten
    # ============================================================

    def calculate_stats(self, activities):
        """
        Berechnet Statistiken zu einer Anzahl von Aktivitäten

        Args:
            activities: Liste von aktivitäten

        Returns: Berechnete Daten
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
            'total_distance': round(total_distance, 2),
            'activity_count': len(activities),
            'total_time': round(total_time, 2),
            'avg_speed': round(avg_speed, 2),
            'total_elevation': round(total_elevation, 0)
        }

    # ============================================================
    # HELFER METHODEN - Hilfsfunktionen
    # ============================================================

    def format_activity_for_display(self, activity):
        """
        Formatiert Aktivitäten zum einfahcen darstellen

        Args:
            activity: Rohdaten einer Aktivität von Strava

        Returns: Formatierte Aktivität
        """
        return {
            'id': activity.get('id'),
            'name': activity.get('name', 'Unnamed Activity'),
            'type': activity.get('type', 'Unknown'),
            'distance_km': round(activity.get('distance', 0) / 1000, 2),
            'moving_time_minutes': activity.get('moving_time', 0) // 60,
            'average_speed_kmh': round(activity.get('average_speed', 0) * 3.6, 2),
            'elevation_gain': round(activity.get('total_elevation_gain', 0), 0),
            'start_date': activity.get('start_date', ''),
            'start_date_short': activity.get('start_date', '')[:10]
        }
