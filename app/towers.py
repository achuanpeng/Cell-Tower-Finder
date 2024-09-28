import os
import pandas as pd
import numpy as np
from geopy.distance import great_circle
import multiprocessing
import logging
import argparse
import re
from .utils import calculate_signal_quality

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache to store loaded data per country
cell_tower_data_cache = {}

def normalize_string(s):
    """
    Normalize a string by removing non-alphanumeric characters and converting to lowercase.
    """
    return re.sub(r'[^a-z0-9]', '', s.lower())

def load_cell_towers(country_code_alpha3):
    """
    Load cell tower data for the specified country using its alpha-3 code.

    Parameters:
    - country_code_alpha3 (str): Alpha-3 country code (e.g., 'USA')

    Returns:
    - pd.DataFrame or None: DataFrame containing cell tower data if successful, else None.
    """
    global cell_tower_data_cache

    if not country_code_alpha3 or not isinstance(country_code_alpha3, str):
        logging.error("Invalid country code provided.")
        return None

    country_code_alpha3 = country_code_alpha3.upper()

    if country_code_alpha3 in cell_tower_data_cache:
        logging.info(f"Using cached data for country code '{country_code_alpha3}'.")
        return cell_tower_data_cache[country_code_alpha3]

    # Determine the path to the 'databases/towers' directory
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Path to 'app' directory
    project_root = os.path.dirname(script_dir)               # Path to project root
    towers_dir = os.path.join(project_root, 'databases', 'towers')

    if not os.path.isdir(towers_dir):
        logging.error(f"Towers directory not found at {towers_dir}.")
        return None

    # Construct the expected file name
    file_name = f"{country_code_alpha3}.csv.gz"
    file_path = os.path.join(towers_dir, file_name)

    if not os.path.isfile(file_path):
        logging.error(f"No .gz file found for country code '{country_code_alpha3}' at {file_path}.")
        available_files = [f for f in os.listdir(towers_dir) if f.lower().endswith('.csv.gz')]
        logging.error(f"Available countries (alpha-3 codes): {', '.join([os.path.splitext(f)[0] for f in available_files])}.")
        return None

    logging.info(f"Attempting to load cell tower data for country code '{country_code_alpha3}' from {file_path}")
   
    try:
        # Read CSV with specified data types to optimize memory usage
        cell_tower_data = pd.read_csv(file_path, compression='gzip', dtype={
            'lat': 'float32',
            'lon': 'float32',
            'radio': 'category',
            'range': 'float32'
        }, usecols=['lat', 'lon', 'radio', 'range'])  # Load only necessary columns
        logging.info(f"Successfully loaded {len(cell_tower_data)} rows of data for country code '{country_code_alpha3}'.")
        cell_tower_data_cache[country_code_alpha3] = cell_tower_data
        return cell_tower_data
    except Exception as e:
        logging.error(f"Failed to load data from {file_path}: {e}")
        return None

def prefilter_towers(df, lat, lon, max_distance_km=50):
    """
    Quickly filter towers within a rough latitude and longitude range to reduce dataset size.

    Parameters:
    - df (pd.DataFrame): DataFrame containing cell tower data.
    - lat (float): Latitude of the user location.
    - lon (float): Longitude of the user location.
    - max_distance_km (float): Maximum distance in kilometers for prefiltering.

    Returns:
    - pd.DataFrame: Filtered DataFrame.
    """
    lat_diff = 50 / 111  # Approximate degree difference for latitude
    lon_diff = 50 / (111 * np.cos(np.radians(lat)))  # Adjust for longitude based on latitude
    df_filtered = df[
        (df['lat'] >= lat - lat_diff) & (df['lat'] <= lat + lat_diff) &
        (df['lon'] >= lon - lon_diff) & (df['lon'] <= lon + lon_diff)
    ]
    logging.info(f"Prefiltered towers to {len(df_filtered)} entries based on geographic bounds.")
    return df_filtered

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points on the Earth using the Haversine formula.
    Vectorized implementation using numpy.

    Parameters:
    - lon1, lat1: Scalars representing the longitude and latitude of the first point.
    - lon2, lat2: Arrays representing the longitude and latitude of the second points.

    Returns:
    - distances in meters as a numpy array.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km * 1000  # Convert to meters

def filter_towers_by_radius(df, lat, lon):
    """
    Find the closest towers of each type within their respective ranges using vectorized operations.

    Parameters:
    - df (pd.DataFrame): DataFrame containing cell tower data.
    - lat (float): Latitude of the user location.
    - lon (float): Longitude of the user location.

    Returns:
    - dict: Dictionary of closest towers by type.
    """
    user_lat = lat
    user_lon = lon

    # Pre-filter towers to reduce the number of calculations
    df_filtered = prefilter_towers(df, lat, lon, max_distance_km=50)

    logging.info(f"Calculating distances for {len(df_filtered)} towers.")

    # Calculate distances using the Haversine formula
    df_filtered['distance'] = haversine_np(
        user_lon, user_lat,
        df_filtered['lon'].values,
        df_filtered['lat'].values
    )

    logging.info("Completed distance calculations.")

    # Filter towers within their range
    within_range = df_filtered[df_filtered['distance'] <= df_filtered['range']]
    logging.info(f"{len(within_range)} towers within range.")

    # Find the closest tower for each radio type
    if within_range.empty:
        logging.info("No towers found within range.")
        return {}

    closest_towers = within_range.loc[within_range.groupby('radio', observed=True)['distance'].idxmin()]


    # Convert to desired dictionary format
    result = {}
    for _, row in closest_towers.iterrows():
        tower_type = row['radio']
        result[tower_type] = {
            'lat': row['lat'],
            'lon': row['lon'],
            'range': row['range'],
            'distance': row['distance'],
            'signal_quality': calculate_signal_quality(row['distance'] / 1000, row['range']),
            'color': (
                'blue' if tower_type == 'LTE' else
                'green' if tower_type == 'GSM' else
                'orange' if tower_type == 'CDMA' else
                'purple' if tower_type == 'UMTS' else
                'black' if tower_type == 'NR' else 'red'
            )
        }

    logging.info(f"Found closest towers for each type: {result}")
    return result

def filter_towers_within_range(df, lat, lon):
    """
    Find all towers within their respective ranges from the user location using vectorized operations.

    Parameters:
    - df (pd.DataFrame): DataFrame containing cell tower data.
    - lat (float): Latitude of the user location.
    - lon (float): Longitude of the user location.

    Returns:
    - list: List of towers within range.
    """
    user_lat = lat
    user_lon = lon

    # Pre-filter towers to reduce the number of calculations
    df_filtered = prefilter_towers(df, lat, lon, max_distance_km=50)

    logging.info(f"Calculating distances for {len(df_filtered)} towers.")

    # Calculate distances using the Haversine formula
    df_filtered['distance'] = haversine_np(
        user_lon, user_lat,
        df_filtered['lon'].values,
        df_filtered['lat'].values
    )

    logging.info("Completed distance calculations.")

    # Filter towers within their range
    within_range = df_filtered[df_filtered['distance'] <= df_filtered['range']]
    logging.info(f"{len(within_range)} towers within range.")

    # Convert to desired list format
    towers_within_range = within_range.apply(
        lambda row: {
            'radio': row['radio'],
            'lat': row['lat'],
            'lon': row['lon'],
            'range': row['range'],
            'distance': row['distance'],
            'signal_quality': calculate_signal_quality(row['distance'] / 1000, row['range']),
            'color': (
                'blue' if row['radio'] == 'LTE' else
                'green' if row['radio'] == 'GSM' else
                'orange' if row['radio'] == 'CDMA' else
                'purple' if row['radio'] == 'UMTS' else
                'black' if row['radio'] == 'NR' else 'red'
            )
        }, axis=1
    ).tolist()

    logging.info(f"Found towers within range: {towers_within_range}")
    return towers_within_range

def main():
    """
    Main function to handle command-line arguments and execute the appropriate filtering.
    """
    parser = argparse.ArgumentParser(description="Load and process cell tower data for a specified country.")
    parser.add_argument('country', type=str, help='Name of the country to load cell tower data for.')
    parser.add_argument('--lat', type=float, required=True, help='Latitude of the user location.')
    parser.add_argument('--lon', type=float, required=True, help='Longitude of the user location.')
    parser.add_argument('--filter', choices=['closest', 'within'], default='closest', help='Type of filter to apply.')
    args = parser.parse_args()

    country = args.country
    lat = args.lat
    lon = args.lon
    filter_type = args.filter

    logging.info(f"Loading data for country: {country}, lat: {lat}, lon: {lon}, filter: {filter_type}")

    data = load_cell_towers(country)
    if data is not None:
        if filter_type == 'closest':
            result = filter_towers_by_radius(data, lat, lon)
        else:
            result = filter_towers_within_range(data, lat, lon)
        # Example: Print or process the result
        print(result)
    else:
        print(f"Failed to load cell tower data for '{country}'.")

if __name__ == "__main__":
    main()
