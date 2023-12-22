import logging
import teslapy
import TeslaDevice

class teslaVehicle():
    def __init__(self,vehicle):
        self.vehicle=vehicle

    def __read_data(self, vehicle_data):
        self.__charging_state = vehicle_data["charge_state"]["charging_state"]
        self.__vin = vehicle_data["vin"]
        self.__name = vehicle_data['display_name'] 
        self.__cartype = TeslaDevice.VEHICLE_TYPE[vehicle_data["vehicle_config"]["car_type"]]
        logging.debug("vehicle created: " + self.__name)
        return
    
    @property
    def car_type(self):
        return self.__cartype

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
    def name(self):
        return self.__name
        
    @property 
    def vin(self):
        return self.__vin
        
    def set_attribute(self, stringetje):
        logging.debug("setting attribute: " + stringetje)
        return

    def get_vehicle_data(self):
        local_data = self.vehicle.get_vehicle_data()
        self.__read_data(local_data)
        return local_data