import streamlit as st
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import pydeck as pdk
import json

# ------------------------
# Streamlit page config
# ------------------------
st.set_page_config(page_title="Offline Nigeria LGA Finder", layout="centered")

# ------------------------
# Load GeoJSON data
# ------------------------
@st.cache_resource
def load_lga_data():
    gdf = gpd.read_file("NGA_LGA_Boundaries_2_-2954311847614747693.geojson")
    return gdf

lga_gdf = load_lga_data()

# ------------------------
# App header
# ------------------------
st.title("🗺️ Nigeria LGA Finder (Offline)")
st.write("Enter **Easting/Northing (meters)** in your projected CRS to find the LGA.")

# ------------------------
# User input
# ------------------------
E = st.number_input("Easting (m)", format="%.2f")
N = st.number_input("Northing (m)", format="%.2f")

# ------------------------
# CRS transformation
# ------------------------
projected_crs = "EPSG:32632"  # Replace with your CRS
transformer = Transformer.from_crs(projected_crs, "EPSG:4326", always_xy=True)

# ------------------------
# Main functionality
# ------------------------
if st.button("Find LGA"):
    # Convert meters to lat/lon
    lon, lat = transformer.transform(E, N)
    point = Point(lon, lat)

    # Find which LGA contains the point
    match = lga_gdf[lga_gdf.contains(point)]

    if not match.empty:
        # Get LGA name (first column containing "NAME")
        name_cols = [c for c in match.columns if "NAM]()_
v
