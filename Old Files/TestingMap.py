import osmnx as ox
import folium as fo
import geopandas as gpd

centreCoordinate = (1.407937, 103.901702)
centreDistance = 500

pm = fo.Map(location=centreCoordinate, zoom_start=15, control_scale=True)

# Using osmnx to find all road (n = nodes on every intersection, e = links for walking path)
style_roads = {"color": "#003366", "weight": "1"}
walkGraph = ox.graph_from_point(centreCoordinate, distance=600,truncate_by_edge=True, network_type="walk")
walkNode, walkEdge = ox.graph_to_gdfs(walkGraph)
walkEdgeLayer = fo.GeoJson(walkEdge, style_function=lambda x: style_roads, name="Walk Edge")
walkEdgeLayer.add_to(pm)
walkNodeLayer = fo.GeoJson(walkNode, name="Rail Node")
walkNodeLayer.add_to(pm)

style_rail = {"color": "#000000", "weight": "1"}
railGraph = ox.graph_from_point(centreCoordinate,distance=600,truncate_by_edge=True, infrastructure='way["railway"~"monorail"]')
railNode, railEdge = ox.graph_to_gdfs(railGraph)
railEdgeLayer = fo.GeoJson(railEdge, style_function=lambda x: style_rail, name="Rail Edge")
railEdgeLayer.add_to(pm)
railNodeLayer = fo.GeoJson(railNode, name="Rail Node")
railNodeLayer.add_to(pm)

style_buildings = {'color': '#87CEFA', 'weight': '1'}
 = ox.footprints.footprints_from_point(centreCoordinate, centreDistance)
locp = ox.project_gdf(loc)
folium.GeoJson(locp, style_function=lambda x: style_buildings).add_to(pm)

# Save the folium map as html
fo.LayerControl().add_to(pm)
pm.save("TestingMap.html")
