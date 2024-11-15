from flask import Flask, request, jsonify, render_template
from flask_cors import CORS  # Import Flask-CORS
import requests
from geopy.distance import geodesic  # To calculate distance between coordinates

app = Flask(__name__)
CORS(app)  # Enable CORS

# API Keys and URLs
API_KEY = "661e2033ec8846dd8ff7aa506ac5ba6c"
GEOCODING_URL = "https://api.opencagedata.com/geocode/v1/json"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_FLOOD_URL = "https://api.open-meteo.com/v1/alerts"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weather', methods=['POST'])
def get_weather():
    if request.content_type != 'application/json':
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.get_json()

    if not data or 'city' not in data or 'zip_code' not in data:
        return jsonify({'error': 'Missing city or zip_code parameter'}), 400

    city = data['city']
    zip_code = data['zip_code']

    # Geocoding
    geocode_url = f"{GEOCODING_URL}?q={city}+{zip_code}&key={API_KEY}"
    try:
        response = requests.get(geocode_url)
        geocode_data = response.json()

        if geocode_data['status']['code'] != 200:
            return jsonify({'error': 'Geocoding request failed', 'message': geocode_data['status']['message']}), 500

        results = geocode_data.get('results', [])
        if not results:
            return jsonify({'error': 'No geocoding results found'}), 404

        lat = results[0]['geometry']['lat']
        lon = results[0]['geometry']['lng']

        # Weather Data
        weather_url = f"{WEATHER_URL}?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        if 'daily' not in weather_data:
            return jsonify({'error': 'Failed to fetch weather data'}), 500

        # Extract weather data
        daily_weather = weather_data['daily']
        max_temp_c = daily_weather.get('temperature_2m_max', [])
        min_temp_c = daily_weather.get('temperature_2m_min', [])
        precipitation = daily_weather.get('precipitation_sum', [])

        # Convert temperatures to Fahrenheit
        max_temp_f = [(c * 9/5) + 32 for c in max_temp_c]
        min_temp_f = [(c * 9/5) + 32 for c in min_temp_c]

        # Fetch Flood Alerts from Open-Meteo API
        flood_alerts = get_open_meteo_flood_alerts(lat, lon)

        return jsonify({
            'latitude': lat,
            'longitude': lon,
            'city': city,
            'zip_code': zip_code,
            'weather': {
                'temperature_2m_max': max_temp_f,
                'temperature_2m_min': min_temp_f,
                'precipitation_sum': precipitation
            },
            'flood_alerts': flood_alerts if flood_alerts else "No active flood alerts"
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to contact external APIs', 'message': str(e)}), 500


def get_open_meteo_flood_alerts(lat, lon):
    try:
        # Get flood alerts from Open-Meteo
        response = requests.get(OPEN_METEO_FLOOD_URL, params={
            'latitude': lat,
            'longitude': lon,
            'alert_type': 'flood',  # Specify flood alert type
            'timezone': 'auto'  # Use auto timezone
        })
        alerts = response.json()

        if 'alerts' not in alerts:
            return {'error': 'No flood alerts found'}

        flood_alerts = []
        for alert in alerts.get('alerts', []):
            if alert and isinstance(alert, dict):
                # You can expand this with more details from the alert data if needed
                event = alert.get('event', '').lower()
                if 'flood' in event:
                    flood_alerts.append(alert)

        return flood_alerts
    except requests.exceptions.RequestException as e:
        return {'error': 'Failed to fetch flood alerts', 'message': str(e)}

if __name__ == '__main__':
    app.run(debug=True)
