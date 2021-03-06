
#This program runs a simulation of a plane taking off, going to some presets points, releasing a cargo and returning to launch to land.

from __future__ import print_function
import time
from dronekit import connect, VehicleMode, LocationGlobalRelative
import math
import pymavlink as mav


from geographiclib.constants import Constants
from geographiclib.geodesic import Geodesic

# Set up option parsing to get connection string
import argparse
parser = argparse.ArgumentParser(description='Commands vehicle using vehicle.simple_goto.')
parser.add_argument('--connect',
                    help="Vehicle connection target string. If not specified, SITL automatically started and used.")
args = parser.parse_args()

connection_string = args.connect
sitl = None



# Start SITL if no connection string specified
if not connection_string:
    import dronekit_sitl
    sitl = dronekit_sitl.start_default(52.780559, -0.707985)
    connection_string = sitl.connection_string()


# Connect to the Vehicle
print('Connecting to vehicle on: %s' % connection_string)
vehicle = connect(connection_string, wait_ready=True)


def arm_and_takeoff(aTargetAltitude):
    """
    Arms vehicle and fly to aTargetAltitude.
    """

    print("Basic pre-arm checks")
    # Don't try to arm until autopilot is ready
    while not vehicle.is_armable:
        print(" Waiting for vehicle to initialise...")
        time.sleep(1)

    print("Arming motors")
    # Copter should arm in GUIDED mode
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True

    # Confirm vehicle armed before attempting to take off
    while not vehicle.armed:
        print(" Waiting for arming...")
        time.sleep(1)

    print("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude)  # Take off to target altitude

    # Wait until the vehicle reaches a safe height before processing the goto
    #  (otherwise the command after Vehicle.simple_takeoff will execute
    #   immediately).
    while True:
        print(" Altitude: ", vehicle.location.global_relative_frame.alt)
    
        # Break and return from function just below target altitude.
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            break
        time.sleep(1)

def get_distance_metres(aLocation1, aLocation2):
    """
    Returns the ground distance in metres between two LocationGlobal objects.
    This method is an approximation, and will not be accurate over large distances and close to the 
    earth's poles. It comes from the ArduPilot test code: 
    https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
    """

    (x1,y1) = aLocation1
    (x2,y2) = aLocation2
    
    dlat = x1 - x2
    dlong = y1 - y2
    
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5

def get_bearing(aLocation1, aLocation2):
    """
    Returns the bearing between the two LocationGlobal objects passed as parameters.

    This method is an approximation, and may not be accurate over large distances and close to the
    earth's poles. It comes from the ArduPilot test code:
    https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
    """

    (x1,y1) = aLocation1
    (x2,y2) = aLocation2
    
    off_x = x1 - x2
    off_y = y1 - y2
    
    bearing = 90.00 + math.atan2(-off_y, off_x) * 57.2957795
    if bearing < 0:
        bearing += 360.00
    return bearing;


def within_range(loc1,loc2):

    dist = get_distance_metres(loc1,loc2)
    if dist > 1:
        return False
    return True

def release_package():

    msg = vehicle.message_factory.command_long_encode(0, 0,  # target_system, target_component
             mav.mavutil.mavlink.MAV_CMD_DO_SET_SERVO,  # command
             0,  # confirmation
             9,  # servo number
             3000, # servo pos between 1000 and 2000
             0, 0, 0, 0, 0)   # Not used (params 3 -7)

    vehicle.send_mavlink(msg)

    time.sleep(5)

    msg = vehicle.message_factory.command_long_encode(0, 0,  # target_system, target_component
             mav.mavutil.mavlink.MAV_CMD_DO_SET_SERVO,  # command
             0,  # confirmation
             9,  # servo number
             700, # servo pos between 1000 and 2000
             0, 0, 0, 0, 0)   # Not used (params 3 -7)

    vehicle.send_mavlink(msg)

def open_servo():

    msg = vehicle.message_factory.command_long_encode(0, 0,  # target_system, target_component
             mav.mavutil.mavlink.MAV_CMD_DO_SET_SERVO,  # command
             0,  # confirmation
             9,  # servo number
             3000, # servo pos between 1000 and 2000
             0, 0, 0, 0, 0)   # Not used (params 3 -7)

    vehicle.send_mavlink(msg)

def close_servo():

    msg = vehicle.message_factory.command_long_encode(0, 0,  # target_system, target_component
             mav.mavutil.mavlink.MAV_CMD_DO_SET_SERVO,  # command
             0,  # confirmation
             9,  # servo number
             700, # servo pos between 1000 and 2000
             0, 0, 0, 0, 0)   # Not used (params 3 -7)

    vehicle.send_mavlink(msg)


def getEndpoint(lat1, lon1, bearing, d):
    geod = Geodesic(Constants.WGS84_a, Constants.WGS84_f)
    d = geod.Direct(lat1, lon1, bearing, d * 1852.0)
    return d['lat2'], d['lon2']

    
#Here the mission starts


aLocation1 = 52.781840, -0.713274
aLocation2 = 52.785341, -0.710237
aLocation3 = 52.786430, -0.712614
aLocation4 = 52.782634, -0.715660



x_FOV = 24.13
y_FOV = 18.14

Direction1 = get_bearing(aLocation1, aLocation4)
Direction2 = get_bearing(aLocation2, aLocation3)


print("Set airspeed to 10")
vehicle.airspeed = 10


Distance1 = get_distance_metres(aLocation1, aLocation2)
Distance2 = get_distance_metres(aLocation1, aLocation4)


n_turns = int(Distance2/x_FOV)

print(Direction1)
print(Distance1)

print(n_turns)

x_coordinates = [52.781840, 52.785341]
y_coordinates = [-0.713274, -0.710237]

new_coords1 = []
new_coords2 = []

for i in range(n_turns):

    distance = ((i+1) * x_FOV)/1000
    
    new_coords1.append(getEndpoint(x_coordinates[0], y_coordinates[0], Direction1, distance))
    new_coords2.append(getEndpoint(x_coordinates[1], y_coordinates[1], Direction2, distance))

print("coords 1")
for i in range(n_turns):
    print(new_coords1[i])

print("coords 2")
for i in range(n_turns):
    print(new_coords2[i])
    
    

    












print("Landing")
while not(vehicle.location.global_relative_frame.alt < 0):
    time.sleep(1);    


# Close vehicle object before exiting script
print("Close vehicle object")
vehicle.close()

# Shut down simulator if it was started.
if sitl:
    sitl.stop()
