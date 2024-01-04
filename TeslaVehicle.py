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
        if 'battery_level' in self.__local_data['charge_state']:
            return self.__local_data["charge_state"]["battery_level"]
        else:
            return False

    @property
    def battery_range(self):
        if 'battery_range' in self.__local_data['charge_state']:
            if self.__metric:
                return get_km_from_miles(self.__local_data['charge_state']['battery_range'])
            else:
                return self.__local_data['charge_state']['battery_range']
        else:
            return False

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
        if "active_route_latitude" in self.__local_data["drive_state"]:
            return 'href="http://www.google.com/maps/search/?api=1&query=' + str(self.__local_data["drive_state"]["active_route_latitude"]) + ',' + str(self.__local_data["drive_state"]["active_route_longitude"]) + '">'
        else:
            return False

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
        driving_states = ["D","R"]
        self.__driving_state = self.__local_data["drive_state"]["shift_state"]
        if self.__driving_state in driving_states:
            return True
        else:
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
        if 'odometer' in self.__local_data['vehicle_state']:
            if self.__metric:
                return round(get_km_from_miles(self.__local_data['vehicle_state']['odometer']))
            else:
                return round(self.__local_data['vehicle_state']['odometer'])
        else:
            return False

    @property
    def speed(self):
        if 'speed' in self.__local_data['drive_state']:
            if self.__local_data['drive_state']['speed'] is None:
                self.__speed = 0
            elif self.__metric:
                self.__speed = str(round(get_km_from_miles(self.__local_data['drive_state']['speed'])))+" km/h"
            else:
                self.__speed = str(round(self.__local_data['drive_state']['speed']))+" m/h"
            return self.__speed
        else:
            return False
            
    @property 
    def vin(self):
        return self.__vin
        
    def get_vehicle_data(self):
        self.__local_data = self.vehicle.get_vehicle_data()
        logging.debug("vehicle data from server: " + str(self.__local_data))
        self.__read_data(self.__local_data)
        self.__last_poll_time = datetime.now()
        return self.__local_data
