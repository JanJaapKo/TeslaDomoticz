import json
import teslapy
from TeslaDevice import VEHICLE_TYPE
with teslapy.Tesla('elon.musk@tesla.com') as tesla:
    vehicles = tesla.vehicle_list()
    print("vehicles = "+ str(vehicles))
    vehicles[0].sync_wake_up()
    vehicles[0].get_vehicle_data()
    print('authenticated your ' + VEHICLE_TYPE[vehicles[0]["vehicle_config"]["car_type"]] + ' called ' + vehicles[0]['display_name']  +' at ' + str(vehicles[0]['charge_state']['battery_level']) + '% SoC')
    #print(json.dumps(vehicles[0], sort_keys = True, indent=4))