import logging
import teslapy
import os

VEHICLE_TYPE = {
    "model3": 'Model Y',
    "models": 'Model Y',
    "modelx": 'Model Y',
    "modely": 'Model Y',
}

class TeslaAnyDevice():
    """generic class to interface device data with Tesla server"""
    def __init__(self,email):
        self.email = email
        self.initialized = False
        
    def initialize(self):
        """initialize the connection if when cache file found"""
        cache_file = self._get_cachefile_location("cache.json")
        if cache_file == "":
            return False
        self.tesla = teslapy.Tesla(self.email, cache_file = cache_file)
        self.initialized = True
        return True
        
    def get_devices(self):
        if self.initialized:
            vehicles = self.tesla.vehicle_list()
            return vehicles
        else:
            return False

    def _get_cachefile_location(self, filename):
        """search for the cache file as created by tesla_prepare and return its file path"""
        cache_file = ""

        # determine the cache file location
        # non-docker location
        BASE_LOC = "plugins//TeslaDomoticz//"
        try:
            loc_to_try = ".//" + BASE_LOC + filename
            with open(loc_to_try, 'r'):
                cache_file = loc_to_try
                logging.info("cache file found in non-docker location.")
        except IOError:
            # Synology NAS location
            try:
                loc_to_try = ".//var//" + BASE_LOC + filename
                with open(loc_to_try, 'r'):
                    cache_file = loc_to_try
                    logging.info("cache file found in Synology NAS location.")
            except IOError:
                # docker location
                try:
                    loc_to_try = ".//userdata//" + BASE_LOC + filename
                    with open(loc_to_try, 'r'):
                        cache_file = loc_to_try
                        logging.info("cache file found in docker location.")
                except IOError:
                    try:
                        loc_to_try = filename
                        with open(loc_to_try, 'r'):
                            cache_file = loc_to_try
                            logging.info("cache file found in default location.")
                    except IOError:
                        logging.error(f"cache file not found!")

        return cache_file
