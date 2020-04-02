import osmnx as ox
import folium as fo
import geopandas as gpd
import heapq as hq
import pandas as pd
import json as js
import networkx as nx
import numpy as np
import geopandas as gpd
from pandas import json_normalize
import json
import os
import shapely

#read the csv the csv file to get all the station name and coordinates in the east loop 
df_east = pd.read_csv('MRT/MRT-EAST.csv')
df_east['geometry'] = df_east['geometry'].apply(shapely.wkt.loads)
geo_df_east = gpd.GeoDataFrame(df_east, crs="EPSG:4326", geometry='geometry')
#read the csv the csv file to get all the station name and coordinates in the west loop 
df_west = pd.read_csv('MRT/MRT-WEST.csv')
df_west['geometry'] = df_west['geometry'].apply(shapely.wkt.loads)
geo_df_west = gpd.GeoDataFrame(df_west, crs="EPSG:4326", geometry='geometry')

class Mrt:
    def __init__(self):
        start_x = None
        start_y = None
        end_x = None
        end_y = None
        lastx = None
        lasty = None

    def MrtAlgo(self, x1, y1, x2, y2):
        self.start_x = x1
        self.start_y = y1
        self.end_x = x2
        self.end_y = y2

        start_coordinate = (self.start_x, self.start_y)
        end_coordinate = (self.end_x,self.end_y)


        #Define the cordinates where the map will point to in folium.
        centreCoordinate = (1.407937, 103.901702)
        pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
        #plot the Start point and end point on the map with folium icon
        fo.Marker(start_coordinate, popup="start", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(pm)
        fo.Marker(end_coordinate, popup="end", icon=fo.Icon(
            color='red', icon='info-sign')).add_to(pm)

        #Read the punggol map
        punggol = gpd.read_file('geojson/polygon-punggol.geojson')
        polygon = punggol['geometry'].iloc[0]

        #using Osmnx ro create a graph with nodes.
        mrt_station_response = ox.core.osm_net_download(
            polygon, infrastructure='node["railway"="station"]')
        mrt_station_Graph = ox.core.create_graph(mrt_station_response, retain_all=True)
        mrt_station_Node, mrt_station_Edge = ox.graph_to_gdfs(mrt_station_Graph)

        #Define the name and osm id of the mrt station west and East Loop
        mrt_west_stations = {1840734606: 'Sam Kee', 1840734600: 'Punggol Point', 1840734607: 'Samudera',
                             1840734598: 'Nibong', 1840734610: 'Sumang', 1840734608: 'Soo Teck', 213085056: 'Punggol'}
        mrt_east_stations = {1840734592: 'Cove', 1840734597: 'Meridian', 1840734578: 'Coral Edge',
                             1840734604: 'Riviera', 1840734594: 'Kadaloor', 1840734599: 'Oasis', 1840734593: 'Damai', 213085056: 'Punggol'}

        #Define Graph of the station with its osm id
        graph = {213085056: [1840734593, 1840734592, 1840734608, 1840734606],
                 1840734593: [213085056, 1840734599],
                 1840734599: [1840734593, 1840734594],
                 1840734594: [1840734599, 1840734604],
                 1840734604: [1840734594, 1840734578],
                 1840734578: [1840734604, 1840734597],
                 1840734597: [1840734578, 1840734592],
                 1840734592: [1840734597, 213085056],
                 1840734608: [213085056, 1840734610],
                 1840734610: [1840734608, 1840734598],
                 1840734598: [1840734610, 1840734607],
                 1840734607: [1840734598, 1840734600],
                 1840734600: [1840734607, 1840734606],
                 1840734606: [1840734600, 213085056]
                 }
        #using Osmnx to get the nearest nodes from the start and end cordinates
        mrt_start_osmid = ox.geo_utils.get_nearest_node(
            mrt_station_Graph, start_coordinate)
        mrt_end_osmid = ox.geo_utils.get_nearest_node(
            mrt_station_Graph, end_coordinate)

        # using BFD algorithm to find the shortest MRT path that the user can take
        def bfs_shortest_path(graph, start, end):

            visited = []
            queue = [[start]]

            if start == end:
                return 0
            #traverse throug the graph and find its neighbour
            while queue:
                path = queue.pop(0)
                node = path[-1]
                if node not in visited:
                    neighbours = graph[node]
                    # if node neighbour is visited it will be marked as visited and it will be appended to the queue
                    for neighbour in neighbours:
                        short_route = list(path)
                        short_route.append(neighbour)
                        queue.append(short_route)
                        # stop when end of graph
                        if neighbour == end:
                            return short_route

                    visited.append(node)

            return 0

        # Displaying the station information and mark all the station in the route
        def mrt_station_display(osm_df, east, west, route):
            for station in route:
                # with the use of OSMID to get the latitude and longtitude of the west LTR line
                if station in west:
                    current_coord_lat = float(
                        osm_df[osm_df['osmid'] == station]['y'].values[0])
                    current_coord_long = float(
                        osm_df[osm_df['osmid'] == station]['x'].values[0])
                    print(west[station])
                     #plot the path of the MRt on the map with blue lines
                    fo.Marker([current_coord_lat, current_coord_long], popup=west[station], icon=fo.Icon(
                        color='blue', icon='info-sign')).add_to(pm)
                else:
                    #if staion not in the west loop it will search the value from the east loop
                    # with the use of OSMID to get the latitude and longtitude of the west LTR line
                    current_coord_lat = float(
                        osm_df[osm_df['osmid'] == station]['y'].values[0])
                    current_coord_long = float(
                        osm_df[osm_df['osmid'] == station]['x'].values[0])
                    #plot the path of the MRt on the map with blue lines
                    fo.Marker([current_coord_lat, current_coord_long], popup=east[station], icon=fo.Icon(
                        color='blue', icon='info-sign')).add_to(pm)
                    print(east[station])

        # loop throught the csv file and get allt he cordinatates that is needed to plot the graph from station to station
        def mrt_route_display(east, east_geo, west, west_geo, route, fo_map):
            result_df = pd.DataFrame(columns=west_geo.columns)
            for i in range(len(route) - 1):
                current_station, next_station = route[i], route[i + 1]
                if current_station in west and next_station in west:
                    if ((west_geo['u'] == current_station) & (west_geo['v'] == next_station)).any():
                        row = west_geo[(west_geo['u'] == current_station)
                                       & (west_geo['v'] == next_station)]
                    else:
                        row = west_geo[(west_geo['v'] == current_station)
                                       & (west_geo['u'] == next_station)]
                else:
                    if ((east_geo['u'] == current_station) & (east_geo['v'] == next_station)).any():
                        row = east_geo[(east_geo['u'] == current_station)
                                       & (east_geo['v'] == next_station)]
                    else:
                        row = east_geo[(east_geo['v'] == current_station)
                                       & (east_geo['u'] == next_station)]
                result_df = result_df.append(row)
            result_geo_df = gpd.GeoDataFrame(
                result_df, crs="EPSG:4326", geometry='geometry')
            # print the route connectiong the star node and the end nodes
            fo.GeoJson(result_geo_df, style_function=lambda x: {
                       "color": "blue", "weight": "3"}, name="MRT").add_to(fo_map)


        route = bfs_shortest_path(graph, mrt_start_osmid, mrt_end_osmid)

        #if the mrt station start and end at the same staion show user that MRT is not needed
        if route != 0:
            print(route)
            mrt_station_display(mrt_station_Node, mrt_east_stations,
                                mrt_west_stations, route)
            mrt_route_display(mrt_east_stations, geo_df_east,
                              mrt_west_stations, geo_df_west, route, pm)
            # if start station is the same as the end station, print MRT not needed
        else:
            print("MRT is not needed!")
        # OSMID of Station
        osmid = int(route[-1])
        self.lasty = mrt_station_Node[mrt_station_Node["osmid"]==osmid]['x'].values[0]
        self.lastx =  mrt_station_Node[mrt_station_Node["osmid"] == osmid]['y'].values[0]
        return pm
        # self.last = (lastlong, lastlat)
        # self.last = int(route[-1])

    def getLastx(self):
        return self.lastx
    def getLasty(self):
        return self.lasty




#mrt = Mrt()

#x1 = 1.412545
#y1 = 103.903250
#x2 = 1.401224
#y2 = 103.916334

# mrt.MrtAlgo(x1, y1, x2, y2)
# print(mrt.getLastx(),mrt.getLasty())