from walk import *
from mrt import *
from bus import *
import osmnx as ox
import folium as fo
import geopandas as gpd
import heapq
import pandas as pd
import math

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
x1 = 1.402235
y1 = 103.905384
# (x2,y2) = end coordinate
x2 = 1.392949
y2 = 103.912034
start_coordinate = (x1, y1)
end_coordinate = (x2, y2)

distance = haversine(x1, y1, x2, y2)

# Map Creation and Start/End Coordinate plotting
pm = fo.Map(location=centreCoordinate, zoom_start=17, control_scale=True, tiles='OpenStreetMap')
fo.Marker([x1, y1]).add_to(pm)
fo.Marker([x2, y2]).add_to(pm)
fo.LayerControl().add_to(pm)

mrts = ['1.4052585,103.9023302', '1.4053014,103.8972748',
        '1.4085322,103.8985342', '1.4118877,103.9003304',
        '1.4159537,103.9021398', '1.4168814,103.9066298',
        '1.4097076,103.904874', '1.4052523,103.9085982',
        '1.4022823,103.9127329', '1.399601,103.9164448',
        '1.394538,103.9161538', '1.3939318,103.9125723',
        '1.3969357,103.9088889', '1.3994603,103.9058059']

# mrt algo
mrt = Mrt()
walk = Walk()
bus = Bus()

if start_coordinate in mrts:
    mrtpm = mrt.MrtAlgo(x1,y1,x2,y2)
    # fo.TileLayer('Rail').add_to(pm)

    # mrtpm.add_to(pm)
    mlastx = mrt.getLastx()
    mlasty = mrt.getLasty()
    #[ find nearest bus service with mrt's end coordinate ]
    #if got bus:
    buspm = bus.busAlgo(mlastx,mlasty, x2,y2)
    if (bus.getRoute()):
        blastx = bus.getLastx()
        blasty = bus.getLasty()
        fo.TileLayer('Bus').add_to(pm)
        walkpm = walk.walkAlgo(blastx,blasty, x2, y2)
        # walkpm.add_to(pm)
        # fo.LayerControl().add_to(pm)
    # Walk(bus stop end coordinate, end_coordinate)
    else:
        blastx = bus.getLastx()
        blasty = bus.getLasty()
        walkpm = walk.walkAlgo(blastx,blasty, x2, y2)
        # walkpm.add_to(pm)
        # fo.TileLayer('Walk').add_to(pm)
else:
    buspm = bus.busAlgo(x1,y1,x2,y2)
    fo.Marker([bus.getFirstx(), bus.getFirsty()]).add_to(buspm)
    fo.Marker([x2, y2]).add_to(buspm)
    buspm.save("2.html")

    walkpm1 = walk.walkAlgo(x1,y1,bus.getFirstx(),bus.getFirsty())
    fo.Marker([x1, y1]).add_to(walkpm1)
    fo.Marker([bus.getFirstx(), bus.getFirsty()]).add_to(walkpm1)
    walkpm1.save("1.html")

    walkpm2 = walk.walkAlgo(bus.getLastx(), bus.getLasty(), x2, y2)
    fo.Marker([bus.getLastx(), bus.getLasty()]).add_to(walkpm2)
    fo.Marker([x2, y2]).add_to(walkpm2)
    walkpm2.save("3.html")

    # pm.save("test123.html")
    #walkpm.save("walktest.html")
    #buspm.add_to(pm)
    #pm.save("test123.html")



# pm.save("test111.html")
