import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client_id = os.getenv('STRAVA_CLIENT_ID')
client_secret = os.getenv('STRAVA_CLIENT_SECRET')
refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')

if not refresh_token:
    print("Error: No refresh token found. Please run strava_auth.py first.")
    exit(1)

# Request a new access token using the refresh token
token_url = "https://www.strava.com/oauth/token"
payload = {
    'client_id': client_id,
    'client_secret': client_secret,
    'refresh_token': refresh_token,
    'grant_type': 'refresh_token'
}

print("Refreshing Strava access token...")

try:
    response = requests.post(token_url, data=payload)

    if response.status_code == 200:
        token_data = response.json()

        new_access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token')
        expires_at = token_data.get('expires_at')

        print("\n" + "=" * 80)
        print("SUCCESS! New tokens received:")
        print("=" * 80)
        print(f"New Access Token: {new_access_token}")
        print(f"New Refresh Token: {new_refresh_token}")
        print(f"Expires At: {expires_at}")
        print("=" * 80)

        # Update .env file
        print("\nUpdating .env file...")

        env_path = '.env'
        with open(env_path, 'r') as f:
            lines = f.readlines()

        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('STRAVA_ACCESS_TOKEN='):
                    f.write(f'STRAVA_ACCESS_TOKEN={new_access_token}\n')
                elif line.startswith('STRAVA_REFRESH_TOKEN='):
                    f.write(f'STRAVA_REFRESH_TOKEN={new_refresh_token}\n')
                else:
                    f.write(line)

        print("✓ .env file updated with new tokens!")
        print("\nYou can now run: python fetch_strava_data.py")

    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")