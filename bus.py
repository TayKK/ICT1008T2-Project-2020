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


def get_node(element):
    """
    Edited Original OSMNX function to include singapore bus stop code
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
    Edited Original OSMNX function to include singapore bus stop code
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
    Edited Original OSMNX function to include singapore bus stop code
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
    General formula to calculate the great circle distance between two points 
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


def node_to_graph(gdf_nodes):
    """
    Edited Original OSMNX function to save node only to graph
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
    """
    Read bus route json file,
    Append the row which is within the Punggol Polygon into current Bus Service Pandas DataFrame
    Return Bus Service, Bus Service GeoPandas DataFrame
    """
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
    return key_df, df


def bus_stop_json_clean(data, name, polygon, bus_stop_ST_code):
    """
    Read bus stop json file,
    Append the row which is within the Punggol Polygon into current Bus Service Pandas DataFrame
    Return Bus Service, Bus Service GeoPandas DataFrame, A Dictionary of Bus Service for each bus stop code
    """
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
    return key_df, df, bus_stop_ST_code


def create_busCode_Adj(stop_df, osm_df, bus_dict):
    """
    Create a Bus Stop Adjacency Dictionary for each relations between each bus stops
    X & Y Coordinates are retrieved from OSMNX data as it is more accurate, on error, coordinates from json file is retrieved instead
    Returns a Dictionary of Relations (Graph)
    """
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


def dijkstras(graph, start, end, bus_stop_dict, leastxfer=False):
    """
    Main Algorithm for bus search
    Using bus stop adjacency list, find the shortest distance travelled through bus codes using dijkstra
    If leastxfer is True as a heuristic, a similar entry will be pushed with a lesser distance to prioritise least transfer for bus
    Return a list of route
    """
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


def clean_bus_route(route, bus_code):
    """
    Convert a final route from dijkstra to dictionary for plotting of route on display
    Returns route dictionary
    """
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


def get_nearestedge_node(osm_id, rG, bG):
    """
    Using OMSNX data, 
    get the coordinates from bus stop,
    get the nearest edge on the road,
    return the node of either end which is nearer to bus stop
    """
    temp_y = bG.nodes.get(osm_id).get('y')
    temp_x = bG.nodes.get(osm_id).get('x')
    temp_nearest_edge = ox.get_nearest_edge(rG, (temp_y, temp_x))
    temp_1 = temp_nearest_edge[0].coords[0]
    temp_2 = temp_nearest_edge[0].coords[1]
    temp1_x = temp_1[0]
    temp1_y = temp_1[1]
    temp_1_distance = haversine(temp1_y, temp1_x, temp_y, temp_x)

    temp2_x = temp_2[0]
    temp2_y = temp_2[1]
    temp_2_distance = haversine(temp2_y, temp2_x, temp_y, temp_x)
    if temp_1_distance < temp_2_distance:
        return temp_nearest_edge[1]
    else:
        return temp_nearest_edge[2]


def display_busstop(fo_map, key, value, stop_df, osm_df, prev_coord):
    """
    Get Coordinates from OSMNX Data or PandasDataFrame and plot bus stop marker
    Return the last bus stop code for next function call to complete the full route
    """
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
                      description, icon=fo.Icon(color='green', icon='flag')).add_to(fo_map)
            bus_route_display_list.append(tuple([x, y]))
        except:
            pass
    prev_coord = value[len(value)-1]
    return prev_coord


def display_busroute(fo_map, key, value, stop_df, osm_df, driveG, drive_df, busG):
    """
    Get Coordinates from OSMNX Data and plot bus stop route based on start and end bus stop
    """
    temp_df = pd.DataFrame(columns=drive_df.columns)
    for i in range(len(value)-1):
        current_busstop_osmid = osm_df[osm_df['asset_ref'] == str(
            value[i])]['osmid'].values[0]
        next_busstop_osmid = osm_df[osm_df['asset_ref'] == str(
            value[i+1])]['osmid'].values[0]
        current_busroute_osmid = get_nearestedge_node(
            current_busstop_osmid, driveG, busG)
        next_busroute_osmid = get_nearestedge_node(
            next_busstop_osmid, driveG, busG)
        current_busroute_next_busroute_list = nx.shortest_path(
            driveG, source=current_busroute_osmid, target=next_busroute_osmid)
        for j in range(len(current_busroute_next_busroute_list)-1):
            current_busroute_id, next_busroute_id = current_busroute_next_busroute_list[
                j], current_busroute_next_busroute_list[j+1]
            temp_df = temp_df.append(drive_df[(drive_df["u"] == current_busroute_id) & (
                drive_df["v"] == next_busroute_id)])
    temp_gdf = gpd.GeoDataFrame(temp_df, crs="EPSG:4326", geometry='geometry')
    fo.GeoJson(temp_gdf, style_function=lambda x: {
               "color": "green", "weight": "3"}, name="BUS").add_to(fo_map)


# Common startup
punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

centreCoordinate = (1.40565, 103.90665000000001)

unique_osmid_list = list(range(1, 999999))
random.shuffle(unique_osmid_list)

start_coord = (1.404130, 103.909584)
end_coord = (1.397352, 103.909050)


pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
fo.Marker(start_coord, popup="start", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)
fo.Marker(end_coord, popup="end", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)

# Query
driveGraph = ox.core.graph_from_polygon(
    polygon, truncate_by_edge=True,  retain_all=True, network_type="drive")
drive_Node, drive_Edge = ox.graph_to_gdfs(driveGraph)

busstop_Query = '[out:json];(node["highway"="bus_stop"](1.3891,103.8872,1.4222,103.9261);>;);out;'
responsejson_Busstop = ox.overpass_request(
    data={'data': busstop_Query}, timeout=180)
busstop_Graph = create_graph(responsejson_Busstop)
busstop_Graph = ox.truncate_graph_polygon(
    busstop_Graph, polygon, truncate_by_edge=True,  retain_all=True)

osm_node, notused = ox.graph_to_gdfs(busstop_Graph)

# Local files

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

# Code starts

busstop_start_osm = ox.geo_utils.get_nearest_node(busstop_Graph, start_coord)
busstop_end_osm = ox.geo_utils.get_nearest_node(busstop_Graph, end_coord)

start_busstop = int(osm_node[osm_node['osmid'] ==
                             busstop_end_osm]["asset_ref"].values[0])
end_busstop = int(osm_node[osm_node['osmid'] ==
                           busstop_start_osm]["asset_ref"].values[0])

bus_stop_ST_Adj = create_busCode_Adj(
    bus_stop_ST_df, osm_node, bus_stop_ST_code)

route = dijkstras(bus_stop_ST_Adj, start_busstop, end_busstop,
                  bus_stop_ST_code, leastxfer=False)

route_display = clean_bus_route(route, bus_stop_ST_code)

prev_coord = None
for bus in route_display:
    prev_coord = display_busstop(
        pm, bus, route_display[bus], bus_stop_ST_df[str(bus)], osm_node, prev_coord)
    display_busroute(pm, bus, route_display[bus], bus_stop_ST_df[str(
        bus)], osm_node, driveGraph, drive_Edge, busstop_Graph)
    print(bus, route_display[bus])


pm.save("bus.html")
