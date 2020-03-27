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


df_east = pd.read_csv('MRT/MRT-EAST.csv')
df_east['geometry'] = df_east['geometry'].apply(shapely.wkt.loads)
geo_df_east = gpd.GeoDataFrame(df_east, crs="EPSG:4326", geometry='geometry')

df_west = pd.read_csv('MRT/MRT-WEST.csv')
df_west['geometry'] = df_west['geometry'].apply(shapely.wkt.loads)
geo_df_west = gpd.GeoDataFrame(df_west, crs="EPSG:4326", geometry='geometry')


start_coordinate = (1.412545, 103.903250)
end_coordinate = (1.401224, 103.916334)
centreCoordinate = (1.407937, 103.901702)
pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
fo.Marker(start_coordinate, popup="start", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)
fo.Marker(end_coordinate, popup="end", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)


punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

mrt_station_response = ox.core.osm_net_download(
    polygon, infrastructure='node["railway"="station"]')
mrt_station_Graph = ox.core.create_graph(mrt_station_response, retain_all=True)
mrt_station_Node, mrt_station_Edge = ox.graph_to_gdfs(mrt_station_Graph)


mrt_west_stations = {1840734606: 'Sam Kee', 1840734600: 'Punggol Point', 1840734607: 'Samudera',
                     1840734598: 'Nibong', 1840734610: 'Sumang', 1840734608: 'Soo Teck', 213085056: 'Punggol'}
mrt_east_stations = {1840734592: 'Cove', 1840734597: 'Meridian', 1840734578: 'Coral Edge',
                     1840734604: 'Riviera', 1840734594: 'Kadaloor', 1840734599: 'Oasis', 1840734593: 'Damai', 213085056: 'Punggol'}

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

mrt_start_osmid = ox.geo_utils.get_nearest_node(
    mrt_station_Graph, start_coordinate)
mrt_end_osmid = ox.geo_utils.get_nearest_node(
    mrt_station_Graph, end_coordinate)


def bfs_shortest_path(graph, start, end):

    visited = []
    queue = [[start]]

    if start == end:
        return 0

    while queue:
        path = queue.pop(0)
        node = path[-1]
        if node not in visited:
            neighbours = graph[node]

            for neighbour in neighbours:
                short_route = list(path)
                short_route.append(neighbour)
                queue.append(short_route)

                if neighbour == end:
                    return short_route

            visited.append(node)

    return 0


def mrt_station_display(osm_df, east, west, route):
    for station in route:
        if station in west:
            current_coord_lat = float(
                osm_df[osm_df['osmid'] == station]['y'].values[0])
            current_coord_long = float(
                osm_df[osm_df['osmid'] == station]['x'].values[0])
            print(west[station])
            fo.Marker([current_coord_lat, current_coord_long], popup=west[station], icon=fo.Icon(
                color='blue', icon='info-sign')).add_to(pm)
        else:
            current_coord_lat = float(
                osm_df[osm_df['osmid'] == station]['y'].values[0])
            current_coord_long = float(
                osm_df[osm_df['osmid'] == station]['x'].values[0])
            fo.Marker([current_coord_lat, current_coord_long], popup=east[station], icon=fo.Icon(
                color='blue', icon='info-sign')).add_to(pm)
            print(east[station])


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
    fo.GeoJson(result_geo_df, style_function=lambda x: {
               "color": "blue", "weight": "3"}, name="MRT").add_to(fo_map)


route = bfs_shortest_path(graph, mrt_start_osmid, mrt_end_osmid)

if route != 0:
    print(route)
    mrt_station_display(mrt_station_Node, mrt_east_stations,
                        mrt_west_stations, route)
    mrt_route_display(mrt_east_stations, geo_df_east,
                      mrt_west_stations, geo_df_west, route, pm)
else:
    print("MRT is not needed!")


pm.save("mrt.html")
