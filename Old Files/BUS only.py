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
from shapely.geometry import Point, LineString, Polygon


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


def get_busstop_coord_osm(df):
    busCode_to_coord = {}
    for i in df.index:
        busCode = df.loc[i]['asset_ref']
        x = df.loc[i]['y']
        y = df.loc[i]['x']
        busCode_to_coord[busCode] = [x, y]
    return busCode_to_coord


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
    return key_df, df


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
    return key_df, df, bus_stop_ST_code


def get_samebus_route(df, start_busstop, end_busstop):
    bus_route_list = []
    try:
        start_index = df.index[df['busCode'] == start_busstop].values[0]
        end_index = df.index[df['busCode'] == end_busstop].values[0]
        for i in range(start_index, end_index+1):
            bus_route_list.append(df.loc[i, 'busCode'])
        if bus_route_list == []:
            return None
        else:
            return bus_route_list
    except:
        return None


def compare_final_route(final_route):
    sorted_final_route = {k: v for k, v in sorted(
        final_route.items(), key=lambda item: len(item[1]))}
    final_stop, final_route = next(iter(sorted_final_route)), next(
        iter(sorted_final_route.values()))
    return [final_stop, final_route]


def get_diffbus_route(bus_stop_ST_df, start_busCode, end_busCode, bus_stop_ST_code):
    final_route = []
    start_busCode_busService = bus_stop_ST_code[start_busCode]
    end_busCode_busService = bus_stop_ST_code[end_busCode]
    for busService in itertools.product(start_busCode_busService, end_busCode_busService):
        route = {}
        start_busstop = busService[0]
        end_busstop = busService[1]
        start_index_start_busstop = bus_stop_ST_df[start_busstop][bus_stop_ST_df[start_busstop]
                                                                  ['busCode'] == start_busCode].index.values[0]
        filtered_start_busstop_df = bus_stop_ST_df[start_busstop].loc[start_index_start_busstop:]
        end_index_start_busstop = bus_stop_ST_df[start_busstop].index.stop
        for i in range(start_index_start_busstop, end_index_start_busstop):
            try:
                start_row = bus_stop_ST_df[start_busstop].loc[i].at['busCode']
                if start_busstop not in route:
                    route[start_busstop] = [start_row]
                else:
                    temp = route[start_busstop]
                    temp.append(start_row)
                    route[start_busstop] = temp
                if start_row in bus_stop_ST_df[end_busstop].values:
                    start_index_end_busstop = bus_stop_ST_df[end_busstop][bus_stop_ST_df[end_busstop]
                                                                          ['busCode'] == start_row].index.values[0]
                    filtered_end_busstop_df = bus_stop_ST_df[end_busstop].loc[start_index_end_busstop:]
                    end_index_end_busstop = bus_stop_ST_df[end_busstop].index.stop
                    for x in range(start_index_end_busstop, end_index_end_busstop):
                        end_row = bus_stop_ST_df[end_busstop].loc[x].at['busCode']
                        if end_busstop not in route:
                            route[end_busstop] = [end_row]
                        else:
                            temp_row = route[end_busstop]
                            temp_row.append(end_row)
                            route[end_busstop] = temp_row
                        try:
                            lat1_to_start = float(
                                osm_busstop_coord[str(start_row)][0])
                            lon1_to_start = float(
                                osm_busstop_coord[str(start_row)][1])
                            lat2_to_start = float(
                                osm_busstop_coord[str(start_busCode)][0])
                            lon2_to_start = float(
                                osm_busstop_coord[str(start_busCode)][1])
                        except:
                            pass
                        try:
                            lat1_to_end = float(
                                osm_busstop_coord[str(end_row)][0])
                            lon1_to_end = float(
                                osm_busstop_coord[str(end_row)][1])
                            lat2_to_end = float(
                                osm_busstop_coord[str(end_busCode)][0])
                            lon2_to_end = float(
                                osm_busstop_coord[str(end_busCode)][1])
                        except:
                            pass
                        if end_row == end_busCode or haversine(lat1_to_end, lon1_to_end, lat2_to_end, lon2_to_end) < 0.3 or haversine(lat1_to_start, lon1_to_start, lat2_to_start, lon2_to_start) < 0.1:
                            final_route.append(route)
                            return final_route
            except:
                del final_route[len(final_route)-1]
    return final_route


def display_busstop(fo_map, key, value, df):
    for bus_code in value:
        try:
            y = float(osm_busstop_coord[str(bus_code)][1])
            x = float(osm_busstop_coord[str(bus_code)][0])
        except:
            y = float(df[df['busCode'] == bus_code]['x'].values[0])
            x = float(df[df['busCode'] == bus_code]['y'].values[0])
        description = str(df[df['busCode'] == bus_code]
                          ['description'].values[0])
        fo.Marker([x, y], popup="[Bus:"+str(key)+", Code:"+str(bus_code)+"]\n" +
                  description, icon=fo.Icon(color='green', icon='info-sign')).add_to(fo_map)


def display_busroute(fo_map, start_bus_code, end_bus_code, bus_stop_df, bus_route_df, bus_route_graph):
    bus_route_display_list = []
    y_start = float(osm_busstop_coord[str(start_bus_code)][1])
    x_start = float(osm_busstop_coord[str(start_bus_code)][0])
    busroute_start_index = ox.geo_utils.get_nearest_node(
        bus_route_graph, tuple([x_start, y_start]))
    y_end = float(osm_busstop_coord[str(end_bus_code)][1])
    x_end = float(osm_busstop_coord[str(end_bus_code)][0])
    busroute_end_index = ox.geo_utils.get_nearest_node(
        bus_route_graph, tuple([x_end, y_end]))
    if busroute_start_index > busroute_end_index:
        try:
            same_df = bus_route_df.loc[busroute_end_index+1:]
            same_x = float(bus_route_df.loc[busroute_end_index]['y'])
            same_y = float(bus_route_df.loc[busroute_end_index]['x'])
            busroute_end_index = same_df[(same_df['y'] == same_x) & (
                same_df['x'] == same_y)].index.values[0]
        except:
            busroute_end_index, busroute_start_index = busroute_start_index, busroute_end_index
    for i in range(busroute_start_index, busroute_end_index+1):
        y_current = float(bus_route_df.loc[i]['x'])
        x_current = float(bus_route_df.loc[i]['y'])
        lat_to_end = float(osm_busstop_coord[str(end_bus_code)][1])
        lon_to_end = float(osm_busstop_coord[str(end_bus_code)][0])
        bus_route_display_list.append(
            tuple([float(x_current), float(y_current)]))
    fo.PolyLine(bus_route_display_list, color="red",
                weight=2.5, opacity=1).add_to(fo_map)


punggol = gpd.read_file('polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

centreCoordinate = (1.40565, 103.90665000000001)

unique_osmid_list = list(range(1, 999999))
random.shuffle(unique_osmid_list)

start_coord = (1.406246, 103.906023)
end_coord = (1.396753, 103.910344)

pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
fo.Marker(start_coord, popup="start", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)
fo.Marker(end_coord, popup="end", icon=fo.Icon(
    color='red', icon='info-sign')).add_to(pm)


busstop_Query = '[out:json];(node["highway"="bus_stop"](1.3891,103.8872,1.4222,103.9261);>;);out;'
responsejson_Busstop = ox.overpass_request(
    data={'data': busstop_Query}, timeout=180)
busstop_Graph = create_graph(responsejson_Busstop)
busstop_Graph = ox.truncate_graph_polygon(
    busstop_Graph, polygon, truncate_by_edge=True,  retain_all=True)

osm_node, rubbish = ox.graph_to_gdfs(busstop_Graph)

busstop_start_osm = ox.geo_utils.get_nearest_node(busstop_Graph, start_coord)
busstop_end_osm = ox.geo_utils.get_nearest_node(busstop_Graph, end_coord)


osm_busstop_coord = get_busstop_coord_osm(osm_node)

start_busstop = int(osm_node[osm_node['osmid'] ==
                             busstop_end_osm]["asset_ref"].values[0])
end_busstop = int(osm_node[osm_node['osmid'] ==
                           busstop_start_osm]["asset_ref"].values[0])

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

start_busstop_buslist = bus_stop_ST_code[start_busstop]
end_busstop_buslist = bus_stop_ST_code[end_busstop]
common_busstop_buslist = list(
    set(start_busstop_buslist) & set(end_busstop_buslist))

final_route = {}
for busService in common_busstop_buslist:
    bus_route_list = get_samebus_route(
        bus_stop_ST_df[str(busService)], start_busstop, end_busstop)
    if bus_route_list is not None:
        final_route[busService] = bus_route_list


if final_route == {}:
    try:
        final_final_route = get_diffbus_route(
            bus_stop_ST_df, start_busstop, end_busstop, bus_stop_ST_code)
        absolute_route = []
        temp_counter = 0
        for i in range(len(final_final_route)):
            temp_list = []
            for k, v in final_final_route[i].items():
                if temp_list == []:
                    temp_list = v
                else:
                    temp_list = temp_list + v
            if temp_counter == 0:
                temp_counter = len(temp_list)
                absolute_route = final_final_route[i]
            elif len(temp_list) < temp_counter:
                temp_counter = len(temp_list)
                absolute_route = final_final_route[i]
        for bus in absolute_route:
            print(bus, absolute_route[bus])
            display_busstop(
                pm, bus, absolute_route[bus], bus_stop_ST_df[str(bus)])
            display_busroute(pm, absolute_route[bus][0], absolute_route[bus][len(
                absolute_route[bus])-1], bus_stop_ST_df[str(bus)], bus_route_ST_df[str(bus)], bus_route_ST_g[str(bus)])
    except:
        raise SystemExit("no bus number")
else:
    final_display_route = compare_final_route(final_route)
    print(final_display_route[0])
    display_busstop(pm, final_display_route[0], final_display_route[1], bus_stop_ST_df[str(
        final_display_route[0])])
    display_busroute(pm, final_display_route[1][0], final_display_route[1][len(final_display_route[1])-1], bus_stop_ST_df[str(
        final_display_route[0])], bus_route_ST_df[str(final_display_route[0])], bus_route_ST_g[str(final_display_route[0])])


pm.save("bus.html")
