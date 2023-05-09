from shapely.geometry import Point, Polygon
import numpy as np
import geog
import geopandas as gpd
import pandas as pd
import os


def circle(row, object_name):
    row['alt_m'] = 0
    p = Point([row[f'{object_name}_lng'], row[f'{object_name}_lat'], row['alt_m']])
    n_points = 20
    diameter = row[f'{object_name}_diameter_ft']
    d_m = diameter
    angles = np.linspace(0, 360, n_points)
    coords = np.array([p.x, p.y, p.z])  # Extract the coordinates from the Point object
    polygon = geog.propagate(coords, angles, d_m)  # Pass the coordinates instead of the Point object
    # polygon = geog.propagate(p, angles, d_m)
    return Polygon(polygon)


def circle_column(df, object_name):
    return df.apply(lambda row: circle(row, object_name), axis=1)


def create_vertiport_layout_layer_for_unfolded(df1, df2, df3, height, fato='fato', park='parking_pad', inters='inters'):
    df1 = circle_column(df=df1, object_name=fato)
    df2 = circle_column(df=df2, object_name=park)
    df3 = circle_column(df=df3, object_name=inters)

    # Store elevation data in the DataFrames
    # df1['elevation'] = height
    # df2['elevation'] = height
    # df3['elevation'] = height 

    concatenated_frame = pd.concat([df1, df2, df3]).reset_index()
    concatenated_frame.rename(columns={"index": "object", 0: "polygon"}, inplace=True)
    concatenated_frame['elevation'] = height
    return concatenated_frame


def save_vertiport_layout_layer_for_unfolded(df1, df2, df3, height, layout_type):
    concatenated_frame = create_vertiport_layout_layer_for_unfolded(df1, df2, df3, height)
    gdp = gpd.GeoDataFrame(concatenated_frame, geometry='polygon')
    os.makedirs('output', exist_ok=True)
    layout_path = f'output/{layout_type}.json'
    file_path = os.path.join(os.getcwd(), layout_path)
    if not os.path.exists(file_path):

        # print(f"removed {file_path}")
        gdp.to_file(filename=f'output/{layout_type}.json', driver="GeoJSON")
    # print(f"Saved {layout_path}")
