import osmnx as ox
import folium as fo
import geopandas as gpd
import heapq as hq
import pandas as pd
import json as js
import networkx as nx
import numpy as np
import geopandas as gpd
from pandas.io.json import json_normalize
import json
# mrt = pd.read_json("mrt.json")

# for lrt in array:
#     print(mrt[lrt])
with open('./MRT.geojson') as f:
    d = json.load(f)
mrt = json_normalize(d['features'])

# mrt = pd.read_json("MRT.geojson")
# mrt =

mrt = mrt["geometry.coordinates"].values

# for station in mrt[0]:
#     print(station)







punggol = gpd.read_file('geojson/polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

centreCoordinate = (1.407937, 103.901702)

df= pd.mrt_punggol = [('punggol', 1.4051810703851584, 103.90249013900757),
('samkee', 1.4097076,103.904874),
('coral edge',1.3939318,103.9125723),
('Riviera', 1.394538,103.9161538),
('punggol point', 1.4168814,103.9066298),
('oasis', 1.4022823,103.9127329),
('Merdirian', 1.4118877,103.9003304),
('Kadaloor', 1.399601,103.9164448),
('Cove', 1.3994603,103.9058059),
('samudera', 1.4159537,103.9021398),
('sooteck', 1.4053014,103.8972748),
('sumang', 1.4085322,103.8985342),
('damai', 1.4052320170304229,103.90855461359024)]





# start_coordinate = (1.39907,103.91092)
# end_coordinate = (1.40289,103.90501)
start_coordinate = (1.4053124590996222, 103.90225678682326)
end_coordinate = (1.4022823,103.9127329)
a= list (start_coordinate)
visited=[]
for station in mrt[1]:
    if station[0] == a[1] and station[1] == a[0]:
        visited.append (station)
        print (visited)








print (a[1])
print (station[1])
pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)
# fo.Marker([1.39907,103.91092]).add_to(pm)
# fo.Marker([1.40289,103.90501]).add_to(pm)
fo.Marker(start_coordinate).add_to(pm)#punggol
#fo.Marker([1.4097076,103.904874]).add_to(pm) #samkee
#fo.Marker([1.3939318,103.9125723]).add_to(pm) #coral edge
#fo.Marker([1.394538,103.9161538]).add_to(pm) # Riviera
#fo.Marker([1.4168814,103.9066298]).add_to(pm)#punggol point
fo.Marker(end_coordinate).add_to(pm)#oasis
#fo.Marker([1.4118877,103.9003304]).add_to(pm)#Nibong
#fo.Marker([1.3969357,103.9088889]).add_to(pm) # Merdirian 
#fo.Marker([1.399601,103.9164448]).add_to(pm)#Kadaloor
#fo.Marker([1.3994603,103.9058059]).add_to(pm) #Cove
#fo.Marker([1.4159537,103.9021398]).add_to(pm)#samudera
#fo.Marker([1.4053014,103.8972748]).add_to(pm)#sooteck
#fo.Marker([1.4085322,103.8985342]).add_to(pm)#sumang
#fo.Marker([1.4052320170304229,103.90855461359024]).add_to(pm)#damai

graph = {"Punggol": ["damai", "Cove", "Soo Teck", "Sam Kee"],
          "damai": ["Punggol", "Oasis"],
          "Oasis" : ["damai", "Kadaloor"],
          "Kadaloor" : ["Oasis", "Riviera"],
          "Riviera" : ["Kadaloor", "Coral Edge"],
          "Coral Edge" : ["Riviera", "Meridian"],
          "Meridian" : ["Coral Edge", "Cove"],
          "Cove" : ["Meridian", "Punggol"],
          "Soo Teck" : ["Punggol", "Sumang"],
          "Sumang" : ["Soo Teck", "Nibong"],
          "Nibong" : ["Sumang", "Samudera"],
          "Samudera" : ["Nibong", "Punggol Point"],
          "Punggol Point" : ["Samudera", "Teck Lee"],
          "Teck Lee" : ["Punggol Point", "Sam Kee"],
          "Sam Kee" : ["Teck Lee", "Punggol"]
        }



def bfs_shortest_path(graph, start, end):

    visited = []
    queue = [[start]]
 
    if start == end:
        return "Same Station"
 
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

    return "So sorry, but a connecting path doesn't exist :("

#print (bfs_shortest_path(graph, 'Punggol', "Punggol Point"))
#print (bfs_shortest_path(graph, 'Punggol', "Punggol"))
#print (bfs_shortest_path(graph, 'Punggol', "Kadaloor"))
print (bfs_shortest_path(graph, 'Coral Edge', "Punggol Point"))
#print (bfs_shortest_path(graph, 'Cove', "whahahaha"))



fo.LayerControl().add_to(pm)
pm.save("mrt.html")





