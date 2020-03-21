import osmnx as ox
import folium as fo
import geopandas as gpd
import heapq as hq
import pandas as pd
import json as js
import networkx as nx
import numpy as np

import math
import shapely


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
    km = 6371 * c
    return km


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
    useful_tags_node = ['ref', 'highway', 'route_ref', 'name']
    node = {}
    node['y'] = element['lat']
    node['x'] = element['lon']
    node['osmid'] = element['id']

    if 'tags' in element:
        for useful_tag in useful_tags_node:
            if useful_tag in element['tags']:
                node[useful_tag] = element['tags'][useful_tag]
    return node


def get_relation(element):
    useful_tags_node = ['ref']
    relations = {}
    relations['members'] = element['members']
    if 'tags' in element:
        for useful_tag in useful_tags_node:
            if useful_tag in element['tags']:
                relations[useful_tag] = element['tags'][useful_tag]
    return relations


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
    relations = {}
    for element in osm_data['elements']:
        if element['type'] == 'node':
            key = element['id']
            nodes[key] = get_node(element)
        elif element['type'] == 'way':  # osm calls network paths 'ways'
            key = element['id']
            paths[key] = ox.get_path(element)
        elif element['type'] == 'relation':
            key = element['id']
            relations[key] = get_relation(element)

    return nodes, paths, relations


def create_graph(response_jsons, name='unnamed', retain_all=True, bidirectional=False, bus=False):
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

    # extract nodes, paths and relations from the downloaded osm data
    nodes = {}
    paths = {}
    relations = {}

    nodes_temp, paths_temp, relations_temp = parse_osm_nodes_paths(
        response_jsons)
    for key, value in nodes_temp.items():
        nodes[key] = value
    for key, value in paths_temp.items():
        paths[key] = value
    for key, value in relations_temp.items():
        relations[key] = value

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

    if bus:
        return G, relations
    else:
        return G


def get_nearest_route(df, osmid):
    df = df[df['osmid'] == osmid]
    for row in df.itertuples(index=True, name='Pandas'):
        x, y = (getattr(row, 'y')), (getattr(row, 'x'))
    return x, y


def get_node_edge(graph):
    node, edge = ox.graph_to_gdfs(graph)
    node, edge = node.fillna("NA"), edge.fillna("NA")
    return node, edge


def check_busRelations(relations, bus_edge):
    new_df = pd.DataFrame(columns=bus_edge.columns)
    new_df = new_df.assign(busService="")
    index = 0
    for relationid in relations:
        if 'members' in relations[relationid]:
            memberList = relations[relationid]['members']
            busService = relations[relationid]['ref']
            osmidList = []
            for member in memberList:
                if member['type'] == 'way':
                    osmidList.append(member['ref'])
            for osmid in osmidList:
                if bus_edge["osmid"].isin([osmid]).any():
                    row = bus_edge[bus_edge['osmid'] == osmid]
                    new_df = new_df.append(row, ignore_index=True)
            if index <= new_df.index.stop:
                new_df.iloc[index:new_df.index.stop,
                            new_df.columns.get_loc('busService')] = busService
                index = new_df.index.stop
    return new_df


def get_busstop_coord(busstop_Node, osmid):
    x = busroute_Node[busroute_Node['osmid'] == osmid].loc[:, 'y'].values[0]
    y = busroute_Node[busroute_Node['osmid'] == osmid].loc[:, 'x'].values[0]
    return x, y


def get_bus_route_df(test, busstop_Node, service, busroute_start_u, busroute_end_v, busstop_end):
    checkDict = {}
    checkDict[busroute_start_u] = None
    df2 = pd.DataFrame(columns=test.columns)
    current_osmid = busroute_start_u
    temp = current_osmid
    while current_osmid != busroute_end_v:
        try:
            next_osmid = test[(test['busService'] == service) & (
                test['u'] == current_osmid)].loc[:, 'v'].values[0]
            if next_osmid == temp:
                print("loop has occured")
                return df2, "error"
            temp = next_osmid
            if next_osmid in checkDict:
                continue
            checkDict[next_osmid] = current_osmid
            #busroute.append(test[(test['busService']==service) & (test['u']==current_osmid)].loc[:,'v'].values[0])
            df2 = df2.append(test[(test['busService'] == service) & (
                test['u'] == current_osmid)], ignore_index=True)
            linestring = list(
                test[test['u'] == current_osmid].iloc[0, 11].coords)
            x1, y1 = list(linestring[len(linestring)-1]
                          )[1], list(linestring[len(linestring)-1])[0]
            x2, y2 = get_busstop_coord(busstop_Node, busstop_end)
            if haversine(x1, y1, x2, y2) < 0.04:
                print("shorter route")
                return df2, "ok"
            current_osmid = next_osmid
        except:
            print("! ERROR")
            break
    return df2, "ok"


punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

centreCoordinate = (1.407937, 103.901702)

# start_coordinate = (1.39907,103.91092)
# end_coordinate = (1.40289,103.90501)
start_coordinate = (1.40289, 103.90501)
end_coordinate = (1.39907, 103.91092)

pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
# fo.Marker([1.39907,103.91092]).add_to(pm)
# fo.Marker([1.40289,103.90501]).add_to(pm)
fo.Marker([1.40289, 103.90501]).add_to(pm)
fo.Marker([1.39907, 103.91092]).add_to(pm)

busroute_Query = '[out:json];(relation["type"="route"]["route"="bus"](1.3891,103.8872,1.4222,103.9261);>;);out;'
responsejson_Busroute = ox.overpass_request(
    data={'data': busroute_Query}, timeout=180)
busroute_Graph, relations = create_graph(
    responsejson_Busroute, retain_all=True, bus=True)
busroute_Graph = ox.truncate_graph_polygon(
    busroute_Graph, polygon, truncate_by_edge=True,  retain_all=True)

busstop_Query = '[out:json];(node["highway"="bus_stop"](1.3891,103.8872,1.4222,103.9261);>;);out;'
responsejson_Busstop = ox.overpass_request(
    data={'data': busstop_Query}, timeout=180)
busstop_Graph = create_graph(responsejson_Busstop)
busstop_Graph = ox.truncate_graph_polygon(
    busstop_Graph, polygon, truncate_by_edge=True,  retain_all=True)

busstop_start = ox.geo_utils.get_nearest_node(busstop_Graph, start_coordinate)
busstop_end = ox.geo_utils.get_nearest_node(busstop_Graph, end_coordinate)

busstop_Node, temp = ox.graph_to_gdfs(busstop_Graph)

x_start, y_start = get_nearest_route(busstop_Node, busstop_start)
x_end, y_end = get_nearest_route(busstop_Node, busstop_end)

busroute_start_u, busroute_start_v = ox.geo_utils.get_nearest_edge(busroute_Graph, (x_start, y_start))[
    1], ox.geo_utils.get_nearest_edge(busroute_Graph, (x_start, y_start))[2]
busroute_end_u, busroute_end_v = ox.geo_utils.get_nearest_edge(busroute_Graph, (x_end, y_end))[
    1], ox.geo_utils.get_nearest_edge(busroute_Graph, (x_end, y_end))[2]


busroute_Node, busroute_Edge = get_node_edge(busroute_Graph)
test = check_busRelations(relations, busroute_Edge)


busstop_start_service = busstop_Node.at[busstop_start, 'route_ref'].split(';')
busstop_end_service = busstop_Node.at[busstop_end, 'route_ref'].split(';')
busstop_common_service = list(
    set(busstop_start_service).intersection(busstop_end_service))

print(busstop_common_service)


df2 = {}

for service in busstop_common_service:
    df2[service], status = get_bus_route_df(
        test, busstop_Node, service, busroute_start_u, busroute_end_v, busstop_end)
    if len(df2[service]) == 0:
        del df2[service]
    if status == "error":
        del df2[service]

busNumber = None
if len(df2) == 0:
    raise SystemExit("no route")
elif len(df2) == 1:
    for key, value in df2.items():
        busNumber = key
        print("1 bus service", key)
else:
    shortest = 99999
    for key, value in df2.items():
        if (len(value) - 1) < shortest:
            shortest = len(value)
            busNumber = key
    if busNumber == None:
        raise SystemExit("no bus number")
    print(len(df2), "bus services - >", busNumber)

if busNumber == None:
    raise SystemExit("no bus number")

gdf = gpd.GeoDataFrame(df2[busNumber])
gdf.crs = "EPSG:4326"

style_roads = {"color": "#FF0000", "weight": "3"}

walkEdgeLayer = fo.GeoJson(
    gdf, style_function=lambda x: style_roads, name="BUS Edge")
walkEdgeLayer.add_to(pm)

layer = fo.GeoJson(gdf, name="BUS ROUTE")
layer.add_to(pm)

fo.LayerControl().add_to(pm)
pm.save("bus.html")
