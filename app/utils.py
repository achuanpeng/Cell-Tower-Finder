import os
import logging
from logging import StreamHandler

def setup_logging(app):
    # Set up logging with environment-based log level
    is_production = os.getenv('FLASK_ENV') == 'production'
    log_level = logging.ERROR if is_production else logging.INFO

    # Assuming the log file is in the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    log_file = os.path.join(project_root, 'log.txt')

    # Configure logging
    handlers = [StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def calculate_signal_quality(distance_km, range_m, k=2.5):
    """
    Calculate signal quality using Q = e^(-k * (d/R)) and convert to percentage.
    Ensures consistent units (meters) for both distance and range.
    :param distance_km: Distance in kilometers
    :param range_m: Range in meters
    :param k: Decay constant, default is 2.5
    :return: Signal quality as a percentage
    """
    import math
    distance_m = distance_km * 1000  # Convert distance from kilometers to meters
    if range_m == 0:  # To prevent division by zero
        return 0
    signal_quality = math.exp(-k * (distance_m / range_m)) * 100
    return round(signal_quality, 2)
