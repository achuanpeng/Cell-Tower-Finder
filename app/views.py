# app/views.py

from flask import Blueprint, request, jsonify, render_template
from .geolocation import get_coordinates_from_location, get_country_code_from_coordinates
from .towers import load_cell_towers, filter_towers_by_radius, filter_towers_within_range
from .utils import calculate_signal_quality
import logging

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('map.html')

@main.route('/geocode-location', methods=['POST'])
def geocode_location():
    data = request.json
    location = data.get('location')

    if not location:
        return jsonify({'error': 'Location name is required'}), 400

    logging.info(f"Geocoding location: {location}")
    coordinates = get_coordinates_from_location(location)

    if coordinates:
        return jsonify({'lat': coordinates[0], 'lon': coordinates[1]})
    else:
        logging.error(f"Coordinates not found for location: {location}")
        return jsonify({'error': 'Location not found'}), 404

@main.route('/filter-towers', methods=['POST'])
def filter_towers():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    carrier = data.get('carrier')  # Ensure carrier is handled if necessary

    if lat is None or lon is None:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    logging.info(f"Fetching closest towers for lat: {lat}, lon: {lon}...")

    # Get country alpha-3 code from coordinates
    country_code_alpha3 = get_country_code_from_coordinates(lat, lon)

    if not country_code_alpha3:
        logging.error("Could not determine country code from the provided coordinates.")
        return jsonify({"error": "Could not determine country from the provided location."}), 400

    df = load_cell_towers(country_code_alpha3)
    if df is None:
        logging.error(f"Failed to load cell tower data for country code '{country_code_alpha3}'.")
        return jsonify({"error": f"Failed to load cell tower data for country code '{country_code_alpha3}'."}), 500

    closest_towers = filter_towers_by_radius(df, lat, lon)

    logging.info("Successfully fetched closest towers.")

    tower_details = []
    for tower_type, details in closest_towers.items():
        distance = details['distance']
        range_m = details['range']

        # Calculate signal quality
        signal_quality = calculate_signal_quality(distance / 1000, range_m)  # distance in km

        tower_details.append({
            'type': tower_type,
            'lat': details['lat'],
            'lon': details['lon'],
            'range': details['range'],
            'color': details['color'],
            'distance': details['distance'],
            'signal_quality': signal_quality  # Add signal quality to details
        })

    return jsonify(tower_details)

@main.route('/broad-area-search', methods=['POST'])
def broad_area_search():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')

    if lat is None or lon is None:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    logging.info(f"Fetching all towers within range for lat: {lat}, lon: {lon}...")

    # Get country alpha-3 code from coordinates
    country_code_alpha3 = get_country_code_from_coordinates(lat, lon)

    if not country_code_alpha3:
        logging.error("Could not determine country code from the provided coordinates.")
        return jsonify({"error": "Could not determine country from the provided location."}), 400

    df = load_cell_towers(country_code_alpha3)
    if df is None:
        logging.error(f"Failed to load cell tower data for country code '{country_code_alpha3}'.")
        return jsonify({"error": f"Failed to load cell tower data for country code '{country_code_alpha3}'."}), 500

    all_towers_in_range = filter_towers_within_range(df, lat, lon)

    logging.info("Successfully fetched towers in range.")

    tower_details = []
    for tower in all_towers_in_range:
        tower_details.append({
            'type': tower['radio'],  # Correct reference
            'lat': tower['lat'],
            'lon': tower['lon'],
            'range': tower['range'],
            'color': tower['color'],
            'distance': tower['distance'],
            'signal_quality': tower['signal_quality']
        })

    return jsonify(tower_details)
