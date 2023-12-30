"""Utilities for Tesla plugin."""

def get_addres(lat, long):
    """returns the address string for given latitude and longitude"""
    return "this is not working yet"
    
def get_google_url(lat, long):
    googlelocation = 'href="http://www.google.com/maps/search/?api=1&query=' + str(lat) + ',' + str(long) + '">'
    return googlelocation
