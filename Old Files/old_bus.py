import json as js
import folium as fo
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import shapely
import math
import os
import random
import itertools
import heapq
from shapely.geometry import Point, LineString, Polygon

#import the punggol map 
punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]
#Define the start coordinates of the map that is being displayed in the webpage
centreCoordinate = (1.40565, 103.90665000000001)

unique_osmid_list = list(range(1, 999999))
random.shuffle(unique_osmid_list)
# define the Start and end cordinates for the bus route 
start_coord = (1.399366, 103.911890)
end_coord = (1.404336, 103.902684)

#Plot Icon of the start and end coordinates on the map and plot the map in folium. 
pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
fo.Marker(start_coord, popup="start", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)
fo.Marker(end_coord, popup="end", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)


def get_node(element):
    """
    Convert an OSM node element into the format for a networkx node.
    Parameters
    ----------
    element : dict
        an OSM node element
    Returns
    -------
    dict
    """
    useful_tags_node = ['ref', 'highway', 'route_ref', 'name', 'asset_ref']
    node = {}
    node['y'] = element['lat']
    node['x'] = element['lon']
    node['osmid'] = element['id']

    if 'tags' in element:
        for useful_tag in useful_tags_node:
            if useful_tag in element['tags']:
                node[useful_tag] = element['tags'][useful_tag]
    return node


def parse_osm_nodes_paths(osm_data):
    """
    Construct dicts of nodes and paths with key=osmid and value=dict of
    attributes.
    Parameters
    ----------
    osm_data : dict
        JSON response from from the Overpass API
    Returns
    -------
    nodes, paths : tuple
    """

    nodes = {}
    paths = {}
    for element in osm_data['elements']:
        if element['type'] == 'node':
            key = element['id']
            nodes[key] = get_node(element)
        elif element['type'] == 'way':  # osm calls network paths 'ways'
            key = element['id']
            paths[key] = ox.get_path(element)

    return nodes, paths


def create_graph(response_jsons, name='unnamed', retain_all=True, bidirectional=False):
    """
    Create a networkx graph from Overpass API HTTP response objects.
    Parameters
    ----------
    response_jsons : list
        list of dicts of JSON responses from from the Overpass API
    name : string
        the name of the graph
    retain_all : bool
        if True, return the entire graph even if it is not connected
    bidirectional : bool
        if True, create bidirectional edges for one-way streets
    Returns
    -------
    networkx multidigraph
    """

    # make sure we got data back from the server requests
    elements = []

    elements.extend(response_jsons['elements'])
    if len(elements) < 1:
        raise ox.EmptyOverpassResponse(
            'There are no data elements in the response JSON objects')

    # create the graph as a MultiDiGraph and set the original CRS to default_crs
    G = nx.MultiDiGraph(name=name, crs=ox.settings.default_crs)

    # extract nodes and paths from the downloaded osm data
    nodes = {}
    paths = {}

    nodes_temp, paths_temp = parse_osm_nodes_paths(response_jsons)
    for key, value in nodes_temp.items():
        nodes[key] = value
    for key, value in paths_temp.items():
        paths[key] = value

    # add each osm node to the graph
    for node, data in nodes.items():
        G.add_node(node, **data)

    # add each osm way (aka, path) to the graph
    G = ox.add_paths(G, paths, bidirectional=bidirectional)

    # retain only the largest connected component, if caller did not
    # set retain_all=True
    if not retain_all:
        G = ox.get_largest_component(G)

    # add length (great circle distance between nodes) attribute to each edge to
    # use as weight
    if len(G.edges) > 0:
        G = ox.add_edge_lengths(G)

    return G


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    m = 6371 * c * 1000
    return m


busstop_Query = '[out:json];(node["highway"="bus_stop"](1.3891,103.8872,1.4222,103.9261);>;);out;'
responsejson_Busstop = ox.overpass_request(
    data={'data': busstop_Query}, timeout=180)
busstop_Graph = create_graph(responsejson_Busstop)
busstop_Graph = ox.truncate_graph_polygon(
    busstop_Graph, polygon, truncate_by_edge=True,  retain_all=True)

osm_node, rubbish = ox.graph_to_gdfs(busstop_Graph)

busstop_start_osm = ox.geo_utils.get_nearest_node(busstop_Graph, start_coord)
busstop_end_osm = ox.geo_utils.get_nearest_node(busstop_Graph, end_coord)


def get_busstop_coord_osm(df):
    busCode_to_coord = {}
    for i in df.index:
        busCode = df.loc[i]['asset_ref']
        x = df.loc[i]['y']
        y = df.loc[i]['x']
        busCode_to_coord[busCode] = [x, y]
    return busCode_to_coord


osm_busstop_coord = get_busstop_coord_osm(osm_node)

start_busstop = int(osm_node[osm_node['osmid'] ==
                             busstop_end_osm]["asset_ref"].values[0])
end_busstop = int(osm_node[osm_node['osmid'] ==
                           busstop_start_osm]["asset_ref"].values[0])


def node_to_graph(gdf_nodes):
    """
    Convert node and edge GeoDataFrames into a graph
    Parameters
    ----------
    gdf_nodes : GeoDataFrame
    gdf_edges : GeoDataFrame
    Returns
    -------
    networkx multidigraph
    """

    G = nx.MultiDiGraph()
    G.graph['crs'] = "EPSG:4326"
    G.graph['name'] = "unnamed"

    # add the nodes and their attributes to the graph
    G.add_nodes_from(gdf_nodes.index)
    attributes = gdf_nodes.to_dict()
    for attribute_name in gdf_nodes.columns:
        # only add this attribute to nodes which have a non-null value for it
        attribute_values = {
            k: v for k, v in attributes[attribute_name].items() if pd.notnull(v)}
        nx.set_node_attributes(G, name=attribute_name, values=attribute_values)
    return G


def bus_route_json_clean(data, name, polygon):
    key_df = name.strip("R")
    df = gpd.GeoDataFrame(columns=['osmid', 'x', 'y', 'direction', 'geometry'])
    df.name = name
    df.crs = "EPSG:4326"
    df.set_geometry('geometry')
    for i in range(len(data)):
        datajson = data[i]
        for coord in range(len(datajson)):
            x = float(datajson[coord][0])
            y = float(datajson[coord][1])
            geometry = Point(x, y)
            if geometry.within(polygon):
                data_df = gpd.GeoDataFrame({'osmid': random.sample(
                    unique_osmid_list, 1), 'x': x, 'y': y, 'direction': i+1, 'geometry': [geometry]})
                df = df.append(data_df, ignore_index=True)
#                 busRoute.append(tuple([x, y]))
    return key_df, df


bus_route_ST_df = {}
bus_route_ST_g = {}

with os.scandir('BUS/ROUTE') as data_route:
    for data_route_json in data_route:
        try:
            data_route_filename = (data_route_json.name.strip(".json"))
            with open(data_route_json) as br:
                data_route = js.load(br)
            route_key, route_geodf = bus_route_json_clean(
                data_route, data_route_filename, polygon)
            bus_route_ST_df[route_key] = route_geodf
            route_graph = node_to_graph(route_geodf)
            bus_route_ST_g[route_key] = route_graph
        except:
            raise SystemExit(
                "Reading Bus Route Json File Error", data_route_filename)
print("Bus route loaded successfully")


def bus_stop_json_clean(data, name, polygon, bus_stop_ST_code):
    key_df = name.strip("B")
    df = gpd.GeoDataFrame(
        columns=['osmid', 'x', 'y', 'direction', 'geometry', 'busCode', 'description'])
    df.name = name
    df.crs = "EPSG:4326"
    df.set_geometry('geometry')
    for i in range(len(data)):
        datajson = data[str(i+1)]
        for busstop in range(len(datajson)):
            x = float(datajson[busstop]["Longitude"])
            y = float(datajson[busstop]["Latitude"])
            stopname = str(datajson[busstop]["Description"])
            bus = int(datajson[busstop]['BusStopCode'])
            geometry = Point(x, y)
            if geometry.within(polygon):
                data_df = gpd.GeoDataFrame({'osmid': random.sample(unique_osmid_list, 1), 'x': x, 'y': y,
                                            'direction': i+1, 'geometry': [geometry], 'busCode': bus, 'description': stopname})
                df = df.append(data_df, ignore_index=True)
                if bus not in bus_stop_ST_code:
                    bus_stop_ST_code[bus] = [str(key_df)]
                else:
                    temp = bus_stop_ST_code[bus]
                    if key_df not in temp:
                        temp.append(key_df)
                        bus_stop_ST_code[bus] = temp
#                 busRoute.append(tuple([x, y]))
    return key_df, df, bus_stop_ST_code


bus_stop_ST_df = {}
bus_stop_ST_g = {}
bus_stop_ST_code = {}

with os.scandir('BUS/STOP') as data_stop:
    for data_stop_json in data_stop:
        try:
            data_stop_filename = (data_stop_json.name.strip(".json"))
            with open(data_stop_json) as bs:
                data_stop = js.load(bs)
            stop_key, stop_geodf, bus_stop_ST_code = bus_stop_json_clean(
                data_stop, data_stop_filename, polygon, bus_stop_ST_code)
            bus_stop_ST_df[stop_key] = stop_geodf
            stop_graph = node_to_graph(stop_geodf)
            bus_stop_ST_g[stop_key] = stop_graph
        except:
            raise SystemExit(
                "Reading Bus Stop Json File Error", data_stop_filename)
print("Bus stop loaded successfully")


def create_busCode_Adj(stop_df, osm_df, bus_dict):
    adj_dict = {}
    for key in stop_df:
        current_df = (stop_df[key])
        for i in range(current_df.index.stop-1):
            current_busCode, next_busCode = current_df.loc[i]['busCode'], current_df.loc[i+1]['busCode']
            if current_busCode not in adj_dict:
                try:
                    current_busCode_lat = osm_df[osm_df["asset_ref"] == str(
                        current_busCode)]['y'].values[0]
                    current_busCode_lon = osm_df[osm_df["asset_ref"] == str(
                        current_busCode)]['x'].values[0]
                    next_busCode_lat = osm_df[osm_df["asset_ref"] == str(
                        next_busCode)]['y'].values[0]
                    next_busCode_lon = osm_df[osm_df["asset_ref"] == str(
                        next_busCode)]['x'].values[0]
                except:
                    current_busCode_lat = current_df[current_df["busCode"]
                                                     == current_busCode]['y'].values[0]
                    current_busCode_lon = current_df[current_df["busCode"]
                                                     == current_busCode]['x'].values[0]
                    next_busCode_lat = current_df[current_df["busCode"]
                                                  == next_busCode]['y'].values[0]
                    next_busCode_lon = current_df[current_df["busCode"]
                                                  == next_busCode]['x'].values[0]
                distance = haversine(
                    current_busCode_lat, current_busCode_lon, next_busCode_lat, next_busCode_lon)
                current_buscode_buslist = bus_dict[current_busCode]
                next_buscode_buslist = bus_dict[next_busCode]
                common_buslist = list(
                    set(current_buscode_buslist) & set(next_buscode_buslist))
                if distance != 0:
                    for busService in common_buslist:
                        adj_dict[current_busCode] = {
                            (next_busCode, busService): distance}
            else:
                try:
                    neightbour_dict = adj_dict[current_busCode]
                    current_busCode_lat = osm_df[osm_df["asset_ref"] == str(
                        current_busCode)]['y'].values[0]
                    current_busCode_lon = osm_df[osm_df["asset_ref"] == str(
                        current_busCode)]['x'].values[0]
                    next_busCode_lat = osm_df[osm_df["asset_ref"] == str(
                        next_busCode)]['y'].values[0]
                    next_busCode_lon = osm_df[osm_df["asset_ref"] == str(
                        next_busCode)]['x'].values[0]
                except:
                    current_busCode_lat = current_df[current_df["busCode"]
                                                     == current_busCode]['y'].values[0]
                    current_busCode_lon = current_df[current_df["busCode"]
                                                     == current_busCode]['x'].values[0]
                    next_busCode_lat = current_df[current_df["busCode"]
                                                  == next_busCode]['y'].values[0]
                    next_busCode_lon = current_df[current_df["busCode"]
                                                  == next_busCode]['x'].values[0]
                distance = haversine(
                    current_busCode_lat, current_busCode_lon, next_busCode_lat, next_busCode_lon)
                current_buscode_buslist = bus_dict[current_busCode]
                next_buscode_buslist = bus_dict[next_busCode]
                common_buslist = list(
                    set(current_buscode_buslist) & set(next_buscode_buslist))
                if distance != 0:
                    for busService in common_buslist:
                        neightbour_dict[(next_busCode, busService)] = distance

    return adj_dict


bus_stop_ST_Adj = create_busCode_Adj(
    bus_stop_ST_df, osm_node, bus_stop_ST_code)

# implementation fo dijksta algorithm to find the shortest path. 
def dijkstras(graph, start, end, bus_stop_dict, leastxfer=False):
    heapqueue = []
    seen = {}
    final_route = []
    next_distance = 0
    heapq.heappush(heapqueue, [0, None, start, None])
    while True:
        temp_list = heapq.heappop(heapqueue)
        temp_distance, temp_prev, temp_curr, temp_bus = temp_list[
            0], temp_list[1], temp_list[2], temp_list[3]
        if temp_curr == end:
            final_route.append([temp_curr, temp_bus])
            bus_code = [temp_prev, temp_bus]
            while bus_code != [None, None]:
                final_route.append(bus_code)
                bus_code = seen[bus_code[0]]
            final_route = final_route[::-1]
            break
        if temp_curr in seen:
            continue
        seen[temp_curr] = [temp_prev, temp_bus]
        try:
            for next_stop in graph[temp_curr]:
                temp_distance += graph[temp_curr][next_stop]
                heapq.heappush(
                    heapqueue, [temp_distance, temp_curr, next_stop[0], next_stop[1]])
                if leastxfer:
                    if next_stop[1] == temp_bus:
                        temp_distance -= 99999
                    temp_distance += graph[temp_curr][next_stop]
                    heapq.heappush(
                        heapqueue, [temp_distance, temp_curr, next_stop[0], next_stop[1]])
        except:
            pass
    return final_route


route = dijkstras(bus_stop_ST_Adj, start_busstop, end_busstop,
                  bus_stop_ST_code, leastxfer=False)


def clean_bus_route(route, bus_code):
    route_dict = {}
    busService = str(route[0][1])
    for i in range(len(route)):
        if busService in bus_code[route[i][0]]:
            if str(busService) not in route_dict:
                route_dict[str(busService)] = [route[i][0]]
            else:
                temp = route_dict[str(busService)]
                temp.append(route[i][0])
        else:
            busService = route[i][1]
    return route_dict


route_display = clean_bus_route(route, bus_stop_ST_code)

# get the all the codinates of the busstop and display the busstop nodes on the map
def display_busstop(fo_map, key, value, stop_df, osm_df, prev_coord):
    if prev_coord is None:
        prev_coord = value[0]
    else:
        if prev_coord not in value:
            value.insert(0, prev_coord)
    bus_route_display_list = []
    for bus_code in value:
        try:
            try:
                y = float(osm_df[osm_df['asset_ref'] ==
                                 str(bus_code)]['x'].values[0])
                x = float(osm_df[osm_df['asset_ref'] ==
                                 str(bus_code)]['y'].values[0])
            except:
                y = float(stop_df[stop_df['busCode']
                                  == bus_code]['x'].values[0])
                x = float(stop_df[stop_df['busCode']
                                  == bus_code]['y'].values[0])
            description = str(
                stop_df[stop_df['busCode'] == bus_code]['description'].values[0])
            fo.Marker([x, y], popup="[Bus:"+str(key)+", Code:"+str(bus_code)+"]\n" +
                      description, icon=fo.Icon(color='green', icon='info-sign')).add_to(fo_map)
            bus_route_display_list.append(tuple([x, y]))
        except:
            pass
    fo.PolyLine(bus_route_display_list, color="green",
                weight=2.5, opacity=1).add_to(fo_map)
    prev_coord = value[len(value)-1]
    return prev_coord

# print out the bus route on the map with the start and end point
prev_coord = None
for bus in route_display:
    print(bus, route_display[bus])
    prev_coord = display_busstop(
        pm, bus, route_display[bus], bus_stop_ST_df[str(bus)], osm_node, prev_coord)

pm.save("bus.html")
