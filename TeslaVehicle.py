import logging
import teslapy

class teslaVehicle():
    def __init__(self, vehicle_data):
        self.__charging_state = vehicle_data["charge_state"]["charging_state"]
        self.__vin = vehicle_data["vin"]
        self.__name = vehicle_data['display_name'] 
        logging.debug("vehicle created: " + self.__name)
        return
    
    @property
    def charging(self):
        return self.__charging_state
        
    @property
    def is_charging(self):
        charging_states["Charging","Complete"]
        if self.__charging_state in charging_states:
            return True
        else:
            return False

    @property 
    def vin(self):
        return self.__vin
        