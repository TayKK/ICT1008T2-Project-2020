import folium as fo
import geopandas as gpd
import math
import itertools
# create a Graph
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import osmnx as ox
from shapely.geometry import Point, LineString, Polygon

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
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    # Radius of earth in kilometers is 6371
    km = 6371* c
    return km

G = nx.Graph(name="haha", crs=ox.settings.default_crs)
for i in range(len(test["geometry"])):
    x = float(test["geometry"][i].split(" ")[2].strip("()"))
    y = float(test["geometry"][i].split(" ")[1].strip("()"))
    nid = test.at[i,"id"]
    G.add_node((x, y))

nx.draw(G)