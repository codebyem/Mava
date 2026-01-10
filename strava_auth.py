import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client_id = os.getenv('STRAVA_CLIENT_ID')
client_secret = os.getenv('STRAVA_CLIENT_SECRET')

if not client_id or client_id == 'your_client_id_here':
    print("Error: Please add your STRAVA_CLIENT_ID to the .env file")
    exit(1)

if not client_secret or client_secret == 'your_client_secret_here':
    print("Error: Please add your STRAVA_CLIENT_SECRET to the .env file")
    exit(1)

# Step 1: Generate authorization URL
authorization_url = (
    f"https://www.strava.com/oauth/authorize?"
    f"client_id={client_id}&"
    f"redirect_uri=http://localhost&"
    f"response_type=code&"
    f"scope=activity:read_all"
)

print("=" * 80)
print("STRAVA OAUTH AUTHORIZATION")
print("=" * 80)
print("\nStep 1: Visit this URL in your browser to authorize the app:")
print(f"\n{authorization_url}\n")
print("Step 2: After clicking 'Authorize', you'll be redirected to localhost.")
print("        The URL will look like: http://localhost/?code=XXXXX...")
print("        Copy the entire URL and paste it below.\n")
print("=" * 80)

# Step 2: Get the authorization code from user
redirect_url = input("\nPaste the redirect URL here: ").strip()

# Extract the code from the URL
if "code=" in redirect_url:
    code = redirect_url.split("code=")[1].split("&")[0]
else:
    print("Error: Could not find authorization code in URL")
    exit(1)

print(f"\nExtracted authorization code: {code}")

# Step 3: Exchange authorization code for access token
token_url = "https://www.strava.com/oauth/token"
payload = {
    'client_id': client_id,
    'client_secret': client_secret,
    'code': code,
    'grant_type': 'authorization_code'
}

print("\nExchanging authorization code for access token...")

try:
    response = requests.post(token_url, data=payload)

    if response.status_code == 200:
        token_data = response.json()

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_at = token_data.get('expires_at')

        print("\n" + "=" * 80)
        print("SUCCESS! Tokens received:")
        print("=" * 80)
        print(f"Access Token: {access_token}")
        print(f"Refresh Token: {refresh_token}")
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
                    f.write(f'STRAVA_ACCESS_TOKEN={access_token}\n')
                elif line.startswith('STRAVA_REFRESH_TOKEN='):
                    f.write(f'STRAVA_REFRESH_TOKEN={refresh_token}\n')
                else:
                    f.write(line)

        print("✓ .env file updated successfully!")
        print("\nYou can now run: python fetch_strava_data.py")

    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")