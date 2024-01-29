import logging
import teslapy
import os

VEHICLE_TYPE = {
    "model3": 'Model 3',
    "models": 'Model S',
    "modelx": 'Model X',
    "modely": 'Model Y',
}

class TeslaServer():
    """generic class to interface device data with Tesla server"""
    def __init__(self,email):
        self.email = email
        self.initialized = False
        
    def initialize(self):
        """initialize the connection if when cache file found"""
        cache_file = self._get_cachefile_location("cache.json")
        if cache_file == "":
            return False
        major, minor, patch = teslapy.__version__.split('.')
        logging.debug("Current version of TeslaPy is: '" +teslapy.__version__+ "', major '" +str(major)+ "', minor '" +str(minor)+ "', patch '" +str(patch)+ "', needs to be minimal 2.9.0 or higher")
        if int(major) >= 2 and int(minor) > 8:
            self.tesla = teslapy.Tesla(self.email, cache_file = cache_file)
            self.initialized = True
            return True
        logging.error("Current version of TeslaPy is '" +teslapy.__version__+ "', needs to be upgraded to 2.9.0 or higher")
        return False
        
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
