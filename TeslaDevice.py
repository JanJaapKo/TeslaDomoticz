import teslapy
import os

class TeslaAnyDevice():
    """generic class to interface device data with Tesla server"""
    def initialize(self):
        """initialize the connection if no cache file found"""
        try:
            cacheFile = open("cache.json")
        except FileNotFoundError:
            return False
            
        cacheFile.close()
        return True