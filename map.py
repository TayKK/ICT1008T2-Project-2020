import osmnx as ox
import folium as fo
import geopandas as gpd

# Estimated Punggol Coordinates
punggol = (1.406434, 103.905499)

# Initialise Folium Map
pm = fo.Map(location=punggol, zoom_start=15, control_scale=True)

# style_buildings = {"color": "#AA0000", "weight": "2"}
# loc = ox.footprints.footprints_from_point(punggol, 2000)
# locp = ox.project_gdf(loc)

# buildingGeoJson = fo.GeoJson(
#     locp, style_function=lambda x: style_buildings, name="buildings (display)")
# buildingGeoJson.add_to(pm)

# Using osmnx to find all road (n = nodes on every intersection, e = links for roads)
style_roads = {"color": "#003366", "weight": "1"}
G = ox.graph_from_point(punggol, distance=2000,
                        truncate_by_edge=True, network_type="walk")
n, e = ox.graph_to_gdfs(G)

roadGeoJson = fo.GeoJson(e, style_function=lambda x: style_roads, name="road")
roadGeoJson.add_to(pm)


# Read GeoJson file for bus stop and apply as a new folium layer
busstop = gpd.read_file("geojson/busstop.geojson")
busstopGeoJson = fo.GeoJson(busstop, name="busstop")
busstopGeoJson.add_to(pm)


mrt = gpd.read_file("geojson/MRT.geojson")
mrtGeoJson = fo.GeoJson(mrt, name="mrt")
mrtGeoJson.add_to(pm)



# Read GeoJson file for HDB and apply as a new folium layer
hdb = gpd.read_file("geojson/hdb.geojson")
hdbGeoJson = fo.GeoJson(hdb, name="hdb")
hdbGeoJson.add_to(pm)

# Read GeoJson file for Rail and apply as a new folium layer
rail = gpd.read_file("geojson/rail.geojson")
railGeoJson = fo.GeoJson(rail, name="rail")
railGeoJson.add_to(pm)

# Save the folium map as html
fo.LayerControl().add_to(pm)
pm.save("test.html")
