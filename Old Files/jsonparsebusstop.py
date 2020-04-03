import json
import folium as fo
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

punggol = gpd.read_file('polygon-punggol.geojson')
polygon = punggol['geometry'].iloc[0]

with open("B3.json") as f:
    data = json.load(f)

df = pd.DataFrame(columns=['id', 'x', 'y', 'direction', 'geometry','bus'])
busRoute = []
for i in range(2):
    try:
        datajson = data[str(i+1)]
        for busstop in datajson:
            x = float(busstop["Latitude"])
            y = float(busstop["Longitude"])
            bus = int(busstop['BusStopCode'])
            geometry = Point(y,x)
            if geometry.within(polygon):
                    data_df = pd.DataFrame({'id': int(str(bus)+str(i+1)), 'x': x, 'y': y, 'direction': i+1, 'geometry': [geometry], 'bus':bus})
                    df = df.append(data_df, ignore_index=True)
                    busRoute.append(tuple([x, y]))
    except:
        pass