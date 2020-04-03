from walk import *
from mrt import *
from bus import *
import osmnx as ox
import folium as fo
import geopandas as gpd
import heapq
import pandas as pd
import math
import sys


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth in kilometers is 6371
    m = 6371 * c
    return m*1000


# Load every json/csv into a graph
# Punggol Polygon
punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]
# Centre of Punggol
centreCoordinate = (1.396978, 103.908901)

# Creation of Punggol map with folium


# Random coordinates to try on before UI is up
# (x1, y1) =  start coordinate
# x1 = 1.4052585
# y1 = 103.9023302
x1 = float(sys.argv[1])
y1 = float(sys.argv[2])

# (x2,y2) = end coordinate
# x2 = 1.392949
# y2 = 103.912034
x2 = float(sys.argv[3])
y2 = float(sys.argv[4])

start_coordinate = (x1, y1)
end_coordinate = (x2, y2)


distance = haversine(x1, y1, x2, y2)
# At the start only
# Map Creation and Start/End Coordinate plotting
pm = fo.Map(location=centreCoordinate, zoom_start=17,
            control_scale=True, tiles='OpenStreetMap')
pm.save("./templates/clean.html")


mrts = [(1.4052585, 103.9023302), (1.4053014, 103.8972748),
        (1.4085322, 103.8985342), (1.4118877, 103.9003304),
        (1.4159537, 103.9021398), (1.4168814, 103.9066298),
        (1.4097076, 103.904874), (1.4052523, 103.9085982),
        (1.4022823, 103.9127329), (1.399601, 103.9164448),
        (1.394538, 103.9161538), (1.3939318, 103.9125723),
        (1.3969357, 103.9088889), (1.3994603, 103.9058059)]

# mrt algo
mrt = Mrt()
walk = Walk()
bus = Bus()

# If start point is MRT
if start_coordinate in mrts:
    mrtpm = mrt.MrtAlgo(x1, y1, x2, y2)
    fo.Marker([x1, y1], popup="start", icon=fo.Icon(
        color='red', icon='info-sign')).add_to(mrtpm)

    fo.Marker([mrt.getLastx(), mrt.getLasty()]).add_to(mrtpm)
    dist = haversine(mrt.getLastx(), mrt.getLasty(), x2, y2)
    if dist < 200:
        # If distance is less than 400m, user will walk to destination
        # MW
        try:
            mrtpm.add_child(walk.walkAlgo(
                mrt.getLastx(), mrt.getLasty(), x2, y2))
        except:
            pass
        fo.Marker([mrt.getLastx(), mrt.getLasty()]).add_to(mrtpm)
        fo.Marker([x2, y2], popup="end", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(mrtpm)
        mrtpm.save("./templates/transport.html")
    else:
        # MWBW
        # Reaches this else if distance between Terminal LRT Station and End Coord is > 400m apart
        # Bus to nearest bus stop to End Point
        # mrtpm.add_child(bus.busAlgo(mrt.getLastx(), mrt.getLasty(), x2, y2))
        mrtpm.add_child(bus.busAlgo(mrt.getLastx(), mrt.getLasty(), x2, y2))

        # Add marker for Start-End for this map
        fo.Marker([bus.getFirstx(), bus.getFirsty()], popup="First Bus Stop",
                  icon=fo.Icon(color='green', icon="info-sign")).add_to(mrtpm)
        fo.Marker([bus.getLastx(), bus.getLasty()], popup="Last Bus Stop",
                  icon=fo.Icon(color='green', icon="info-sign")).add_to(mrtpm)

        # Walk from Terminal LRT to Bus Stop
        # mrtpm.add_child(walk.walkAlgo(mrt.getLastx(), mrt.getLasty(), bus.getFirstx(), bus.getFirsty()))

        # Add marker for Start-End for this map
        fo.Marker([mrt.getLastx(), mrt.getLasty()], popup="Last Train Station",
                  icon=fo.Icon(color='purple', icon='info-sign')).add_to(mrtpm)
        # fo.Marker([bus.getFirstx(), bus.getFirsty()]).add_to(mrtpm)

        # Finally walk from bus stop to end point
        try:
            mrtpm.add_child(walk.walkAlgo(
                bus.getLastx(), bus.getLasty(), x2, y2))
        except:
            pass

        # Add marker for Start-End for this map
        # fo.Marker([bus.getLastx(), bus.getLasty()]).add_to(mrtpm)
        fo.Marker([x2, y2], popup="End", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(mrtpm)
        mrtpm.save("./templates/transport.html")
else:
    dist = haversine(x1, x2, y1, y2)
    # WMW
    # If distance greater than 600, user will take MRT first before walking to his/her destination
    if dist > 600:
        mrtpm = mrt.MrtAlgo(x1, y1, x2, y2)
        mrtpm.add_child(walk.walkAlgo(
            x1, y1, mrt.getFirstx(), mrt.getFirsty()))
        try:
            mrtpm.add_child(walk.walkAlgo(
                mrt.getLastx(), mrt.getLasty(), x2, y2))
        except:
            pass
        fo.Marker([mrt.getFirstx(), mrt.getFirsty()]).add_to(mrtpm)
        fo.Marker([x2, y2]).add_to(mrtpm)
        fo.Marker([x1, y1]).add_to(mrtpm)
        fo.Marker([mrt.getFirstx(), mrt.getFirsty()]).add_to(mrtpm)
        fo.Marker([mrt.getLastx(), mrt.getLasty()]).add_to(mrtpm)
        fo.Marker([x2, y2], popup="End", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(mrtpm)
        mrtpm.save("./templates/transport.html")
    elif dist > 400:
        # WBW
        # If distance greater than 400, user will take Bus first before walking to his/her destination
        buspm = bus.busAlgo(x1, y1, x2, y2)
        try:
            buspm.add_child(walk.walkAlgo(
                x1, y1, bus.getFirstx(), bus.getFirsty()))
        except:
            pass
        try:
            buspm.add_child(walk.walkAlgo(
                bus.getLastx(), bus.getLasty(), x2, y2))
        except:
            pass
        fo.Marker([bus.getFirstx(), bus.getFirsty()]).add_to(buspm)
        fo.Marker([x2, y2]).add_to(buspm)
        fo.Marker([x1, y1]).add_to(buspm)
        fo.Marker([bus.getFirstx(), bus.getFirsty()]).add_to(buspm)
        fo.Marker([bus.getLastx(), bus.getLasty()]).add_to(buspm)
        fo.Marker([x2, y2], popup="End", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(buspm)
        buspm.save("./templates/transport.html")
    else:
        # W
        # If distance is < 400, user can just walk over to his/her destination
        walkpm = walk.walkAlgo(x1, x2, y1, y2)
        fo.Marker([x1, y1], popup="start", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(mrtpm)
        fo.Marker([x1, y1], popup="End", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(mrtpm)
        walkpm.save("./templates/transport.html")
