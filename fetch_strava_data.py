import os
import requests
from dotenv import load_dotenv
from pprint import pprint

#Hier laden wir die Tokens aus der env Datei
load_dotenv()
access_token = os.getenv('STRAVA_ACCESS_TOKEN')

# URL von der Strava API
url = "https://www.strava.com/api/v3/athlete/activities"
headers = {
    'Authorization': f'Bearer {access_token}'
}
params = {
    'per_page': 5,  # Anzahl an Aktivitäten die wir erstmal holen wollen
    'page': 1
}

try:
    response = requests.get(url, headers=headers, params=params)
    # prüfen obs geklappt hat
    if response.status_code == 200:
        activities = response.json()

        if not activities:
            print("Nix gefunden :(")
        else:
            print(f"\nFound {len(activities)} activities:\n")
            print("=" * 80)

            for i, activity in enumerate(activities, 1):
                print(f"\n{i}. {activity.get('name', 'Unnamed Activity')}")
                print(f"   Type: {activity.get('type', 'N/A')}")
                print(f"   Date: {activity.get('start_date', 'N/A')}")
                print(f"   Distance: {activity.get('distance', 0) / 1000:.2f} km")
                print(f"   Moving Time: {activity.get('moving_time', 0) // 60} minutes")
                print(f"   Elevation Gain: {activity.get('total_elevation_gain', 0):.0f} m")
                print(f"   Average Speed: {activity.get('average_speed', 0) * 3.6:.2f} km/h")
                print(f"   Activity ID: {activity.get('id', 'N/A')}")

            print("\n" + "=" * 80)
            print("\nFull data structure of first activity:")
            print("=" * 80)
            pprint(activities[0])

    elif response.status_code == 401:
        print("Net so gut wenn diese Fehlermeldung kommt")
    else:
        print(f"Auch nicht gut: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Das hier wäre auch schlecht, wenn das passiert: {e}")