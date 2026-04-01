import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
    STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
    STRAVA_REDIRECT_URI = os.getenv('STRAVA_REDIRECT_URI', 'http://127.0.0.1:5000/callback')
