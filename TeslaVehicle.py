import logging
import teslapy
import TeslaDevice
from datetime import datetime
from utils import *

class teslaVehicle():
    def __init__(self,vehicle):
        self.vehicle=vehicle
        #get initial set of vehicle data (no point to init without)
        self.__local_data = self.vehicle.get_vehicle_data()
        self.__read_data(self.__local_data)
        self.__last_poll_time = datetime.now()
        logging.debug("vehicle created: " + self.__name)

    def __read_data(self, vehicle_data):
        self.__charging_state = vehicle_data["charge_state"]["charging_state"]
        self.__vin = vehicle_data["vin"]
        self.__name = vehicle_data['display_name'] 
        self.__cartype = TeslaDevice.VEHICLE_TYPE[vehicle_data["vehicle_config"]["car_type"]]
        if vehicle_data['gui_settings']['gui_distance_units'] == "km/hr":
            self.__metric = True
        else:
            self.__metric = False
        return
    
    @property
    def battery_level(self):
        return self.__local_data["charge_state"]["battery_level"]

    @property
    def battery_range(self):
        if self.__metric:
            return get_km_from_miles(self.__local_data['charge_state']['battery_range'])
        else:
            return self.__local_data['charge_state']['battery_range']

    @property
    def car_type(self):
        return self.__cartype

    @property
    def charging(self):
        return self.__charging_state

    @property
    def get_gps_coords(self):
        """returns latitude and longitude"""
        return self.__local_data["drive_state"]["active_route_latitude"], self.__local_data["drive_state"]["active_route_longitude"]

    @property
    def get_google_url(self):
        """returns URL to current google maps location"""
        return 'href="http://www.google.com/maps/search/?api=1&query=' + str(self.__local_data["drive_state"]["active_route_latitude"]) + ',' + str(self.__local_data["drive_state"]["active_route_longitude"]) + '">'

    @property
    def is_charging(self):
        """returns True when the vehicle is connected to a charger"""
        charging_states = ["Charging","Complete"]
        if self.__charging_state in charging_states:
            return True
        else:
            return False

    @property
    def is_driving(self):
        """returns True if the vehicle is driving. For now, only returns False"""
        return False

    @property
    def last_poll_time(self):
        return self.__last_poll_time

    @last_poll_time.setter
    def last_poll_time(self, date_time):
        self.__last_poll_time = date_time
    
    @property
    def name(self):
        return self.__name

    @property
    def odometer(self):
        if self.__metric:
            return round(get_km_from_miles(self.__local_data['vehicle_state']['odometer']))
        else:
            return round(self.__local_data['vehicle_state']['odometer'])
        
    @property 
    def vin(self):
        return self.__vin
        
    def set_attribute(self, stringetje):
        logging.debug("setting attribute: " + stringetje)
        return

    def get_vehicle_data(self):
        self.__local_data = self.vehicle.get_vehicle_data()
        logging.debug("vehicle data from server: " + str(self.__local_data))
        self.__read_data(self.__local_data)
        self.__last_poll_time = datetime.now()
        return self.__local_data
