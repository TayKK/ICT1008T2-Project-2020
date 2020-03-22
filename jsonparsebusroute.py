import json
import folium as fo
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

punggol = gpd.read_file('polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

with open('3.json') as f:
    data = json.load(f)

busRoute = []
df = pd.DataFrame(columns=['id', 'x', 'y', 'direction', 'geometry'])
for i in range(2):
    try:
        datajson = data[str(i+1)]['route']
        for coord in range(len(datajson)):
            way = datajson[coord].split(",")[::-1]
            x = float(way[0])
            y = float(way[1])
            geometry = Point(y,x)
            if geometry.within(polygon):
                data_df = pd.DataFrame({'id': int(str(coord+1)+str(i+1)), 'x': x, 'y': y, 'direction': i+1, 'geometry': [geometry]})
                df = df.append(data_df, ignore_index=True)
                busRoute.append(tuple([x, y]))
    except:
        pass