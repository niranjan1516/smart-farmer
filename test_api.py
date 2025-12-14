import requests
import json

def audit_weather_api(city_name="Nagpur"):
    print(f"--- 1. SEARCHING LOCATION FOR: {city_name} ---")
    
    # Geocoding API (Find Lat/Lon)
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1"
    geo_res = requests.get(geo_url)
    geo_data = geo_res.json()
    
    if 'results' not in geo_data:
        print("Error: City not found.")
        return

    lat = geo_data['results'][0]['latitude']
    lon = geo_data['results'][0]['longitude']
    print(f"Found Coordinates: Lat {lat}, Lon {lon}")

    # ---------------------------------------------------------
    # 2. FETCHING REAL WEATHER DATA
    # We add '&daily=precipitation_sum' to get actual rain volume
    # ---------------------------------------------------------
    print(f"\n--- 2. FETCHING LIVE DATA FROM OPEN-METEO ---")
    
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"current_weather=true&"
        f"daily=precipitation_sum&" # <--- THIS IS KEY for Rain
        f"timezone=auto"
    )
    
    response = requests.get(weather_url)
    data = response.json()

    # Pretty print the Raw JSON so you can see it
    # print(json.dumps(data, indent=2)) 

    # ---------------------------------------------------------
    # 3. THE VERDICT
    # ---------------------------------------------------------
    current_temp = data['current_weather']['temperature']
    
    # Get rain for TODAY (Index 0)
    rain_today = data['daily']['precipitation_sum'][0]

    print(f"\n--- REAL DATA RECEIVED ---")
    print(f"Temperature Now: {current_temp} °C")
    print(f"Rainfall Today : {rain_today} mm")
    
    if rain_today == 0.0:
        print("\n✅ API IS CORRECT: It is Winter, so Rain is 0mm.")
    else:
        print(f"\nℹ️ API SAYS: There is {rain_today}mm rain today.")

# Run the test
if __name__ == "__main__":
    # You can change this to your city
    audit_weather_api("Pune")