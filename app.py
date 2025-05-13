import requests
import pandas as pd
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import os
import logging

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
logging.basicConfig(level=logging.DEBUG)

GULF_COUNTRIES = [
    'Saudi Arabia', 'United Arab Emirates', 'Oman', 'Qatar', 'Bahrain', 'Kuwait'
]
API_URL = "https://opensky-network.org/api/states/all"
FIELDS = [
    'tail_number', 'callsign', 'origin_country', 'time_position', 'last_contact',
    'longitude', 'latitude', 'baro_altitude', 'on_ground', 'velocity',
    'heading', 'vertical_rate'
]

def fetch_aircraft_data():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        states = response.json().get('states', [])
        app.logger.debug(f"Fetched {len(states)} states")
        return states
    except requests.RequestException as e:
        app.logger.error(f"Error fetching data: {e}")
        return []

def filter_gulf_aircraft(states, selected_country=None, location_filter=None):
    filtered = []
    for state in states:
        origin_country = state[2].strip() if state[2] else ''
        callsign = state[1].strip() if state[1] else ''
        if origin_country in GULF_COUNTRIES:
            if selected_country is None or origin_country == selected_country:
                on_ground = state[8] if state[8] is not None else False
                if location_filter is None or \
                   (location_filter == 'sky' and not on_ground) or \
                   (location_filter == 'ground' and on_ground):
                    app.logger.debug(f"Matched aircraft: {callsign}, Country: {origin_country}, On Ground: {on_ground}")
                    aircraft_data = {
                        'tail_number': state[0],  # icao24 as tail number
                        'callsign': state[1],
                        'origin_country': state[2],
                        'time_position': state[3],
                        'last_contact': state[4],
                        'longitude': state[5],
                        'latitude': state[6],
                        'baro_altitude': state[7],
                        'on_ground': state[8],
                        'velocity': state[9],
                        'heading': state[10],
                        'vertical_rate': state[11]
                    }
                    filtered.append(aircraft_data)
    app.logger.debug(f"Filtered {len(filtered)} aircraft for country: {selected_country or 'All'}, location: {location_filter or 'All'}")
    return filtered

def save_to_excel(data, filename="gulf_jets.xlsx"):
    try:
        df = pd.DataFrame(data)
        if df.empty:
            app.logger.debug("No data to save to Excel")
            df = pd.DataFrame(columns=FIELDS)
        df.to_excel(filename, index=False)
        app.logger.debug(f"Saved Excel file: {filename}")
        return filename
    except Exception as e:
        app.logger.error(f"Error saving Excel: {e}")
        return None

@app.route('/api/aircraft', methods=['GET'])
def get_aircraft():
    country = request.args.get('country')
    location_filter = request.args.get('location')  # sky, ground, or None
    if country and country not in GULF_COUNTRIES:
        return jsonify({"message": f"Invalid country: {country}. Choose from {', '.join(GULF_COUNTRIES)}", "data": []}), 400
    if location_filter and location_filter not in ['sky', 'ground']:
        return jsonify({"message": "Invalid location filter: choose 'sky' or 'ground'", "data": []}), 400
    states = fetch_aircraft_data()
    filtered_data = filter_gulf_aircraft(states, country, location_filter)
    if not filtered_data:
        message = f"No aircraft found for {country or 'Gulf countries'} in {location_filter or 'all locations'}"
        return jsonify({"message": message, "data": []})
    return jsonify(filtered_data)

@app.route('/api/download', methods=['GET'])
def download_excel():
    country = request.args.get('country')
    location_filter = request.args.get('location')
    if country and country not in GULF_COUNTRIES:
        return jsonify({"message": f"Invalid country: {country}. Choose from {', '.join(GULF_COUNTRIES)}", "data": []}), 400
    if location_filter and location_filter not in ['sky', 'ground']:
        return jsonify({"message": "Invalid location filter: choose 'sky' or 'ground'", "data": []}), 400
    states = fetch_aircraft_data()
    filtered_data = filter_gulf_aircraft(states, country, location_filter)
    excel_file = save_to_excel(filtered_data)
    if excel_file and os.path.exists(excel_file):
        return send_file(excel_file, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

@app.route('/')
def serve_react():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)