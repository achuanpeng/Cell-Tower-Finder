# app/geolocation.py

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError
import logging
import pycountry

# Initialize geolocator with timeout to handle slow responses
geolocator = Nominatim(user_agent="cell_tower_locator", timeout=10)

def get_coordinates_from_location(location):
    try:
        loc = geolocator.geocode(location)
        if loc:
            return loc.latitude, loc.longitude
        else:
            return None
    except GeocoderServiceError as e:
        logging.error(f"Geocoding service error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error in geocoding: {e}")
        return None

def get_country_code_from_coordinates(lat, lon):
    """
    Perform reverse geocoding to get the country alpha-3 code from latitude and longitude.

    Parameters:
    - lat (float): Latitude
    - lon (float): Longitude

    Returns:
    - str or None: Alpha-3 country code if found, else None
    """
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, language='en')
        if location and 'country_code' in location.raw['address']:
            country_code_alpha2 = location.raw['address']['country_code'].upper()
            # Convert alpha-2 to alpha-3 using pycountry
            country = pycountry.countries.get(alpha_2=country_code_alpha2)
            if country:
                return country.alpha_3
            else:
                logging.error(f"Could not find alpha-3 code for alpha-2 code '{country_code_alpha2}'.")
                return None
        else:
            logging.error("Country code not found in the geocoding result.")
            return None
    except GeocoderServiceError as e:
        logging.error(f"Geocoding service error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error in reverse geocoding: {e}")
        return None
