import osmnx as ox
import folium as fo
import geopandas as gpd
import heapq
import pandas as pd

# Punggol Polygon
punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]
# Centre of Punggol
centreCoordinate = (1.396978, 103.908901)
#centreCoordinate = (1.407937, 103.901702)


class Walk:
    def __init__(self):
        start_x = None
        start_y = None
        end_x = None
        end_y = None
        layer = None

    def walkAlgo(self, x1, y1, x2, y2):
        self.start_x = x1
        self.start_y = y1
        self.end_x = x2
        self.end_y = y2

        start_coordinate = (self.start_x, self.start_y)
        end_coordinate = (self.end_x, self.end_y)

        # Initialise the map
        pm = fo.Map(location=centreCoordinate, zoom_start=17, control_scale=True)
        # fo.Marker([self.start_x, self.start_y]).add_to(pm)
        # fo.Marker([self.end_x, self.end_y]).add_to(pm)

        # Query route using osmnx (currently using "all" for trying, can change to "walk" or "drive" as needed)
        graph = ox.core.graph_from_polygon(
            polygon, truncate_by_edge=True, network_type="walk")

        # Separate the graph into 2 files (nodes = nodes in the acquired graph, edges = edges in the acquired graph)
        nodes, edges = ox.graph_to_gdfs(graph)

        # Retrieve the nearest osmID based on the acquired graph
        first_node_id = ox.geo_utils.get_nearest_node(graph, start_coordinate)
        end_node_id = ox.geo_utils.get_nearest_node(graph, end_coordinate)

        # Initalise the variables
        prev_Node = None
        curr_Node = first_node_id

        heap = []
        path = {}
        route = []
        temp = 0

        # min-heap element's structure = [distance, previous osmID, current osmID]
        heapq.heappush(heap, [0, None, curr_Node])

        # Main Algo using min-heap (not A* yet)
        while (True):
            # Pop the list based on shortest distance
            temp_list = heapq.heappop(heap)
            # Set current node to current osmID
            curr_Node = temp_list[2]
            # Break condition once destination is reached
            if curr_Node == end_node_id:
                # route is a list containining all osmID = [1234, 2346, 3456]
                route.append(curr_Node)
                n = temp_list[1]
                # while previous osmID is not none, meaning first osmID is reached
                while n != None:
                    route.append(n)
                    n = path[n]
                # Reverse the list as it is appended from end node to start node
                route = route[::-1]
                break
            # Only continue if my current osmID is a valid key in path = {1:None, 2:1, 3:1, ...}
            if curr_Node in path:
                continue
            # Update the value of current key in path dict
            path[curr_Node] = temp_list[1]
            # Save the distance of the popped list
            temp = temp_list[0]
            # Manipulating the data using dataframe(pandas)
            filteredDF = edges[edges['u'] == curr_Node]
            for row in filteredDF.itertuples(index=True, name='Pandas'):
                # For every edge, push it into min heap
                data_list = (getattr(row, "length") + temp,
                             getattr(row, "u"), getattr(row, "v"))
                heapq.heappush(heap, list(data_list))

        # Create another dataframe to print out the route
        df2 = pd.DataFrame(columns=edges.columns)
        for i in range(len(route) - 1):
            current_item, next_item = route[i], route[i + 1]
            pathRow = edges[(edges['u'] == current_item)
                            & (edges['v'] == next_item)]
            df2 = df2.append(pathRow)

        # Transform thie dataframe to geodataframe
        gdf = gpd.GeoDataFrame(df2)
        gdf.crs = {'init': 'epsg:4326'}

        # Style for route
        style_roads = {"color": "#FF0000", "weight": "3"}
        # Adding this geodataframe into map using folium function
        edgesLayer = fo.GeoJson(
            gdf, style_function=lambda x: style_roads, name="Walk Edge")
        edgesLayer.add_to(pm)

        # Save the folium map as html
        fo.LayerControl().add_to(pm)
        return edgesLayer
        # pm.save("walk.html")

# walk = Walk()
#start 1.402235, 103.905384
#end 1.392949, 103.912034
# x1 = 1.402235
# y1 = 103.905384
# x2 = 1.392949
# y2 = 103.912034
#
# walk.walkAlgo(x1, y1, x2, y2)
