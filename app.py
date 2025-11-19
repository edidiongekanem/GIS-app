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
st.title("🗺️ Nigeria LGA Finder")
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
        name_cols = [c for c in match.columns if "NAME" in c.upper()]
        lga_name = match.iloc[0][name_cols[0]] if name_cols else "Unknown"

        st.success(f"✅ The coordinate is in **{lga_name} LGA**.")

        # ------------------------
        # Prepare polygon data for Pydeck
        # ------------------------
        geojson_dict = json.loads(match.to_json())
        polygon_data = []
        for feature in geojson_dict["features"]:
            geom_type = feature["geometry"]["type"]
            coords = feature["geometry"]["coordinates"]
            if geom_type == "Polygon":
                polygon_data.append({"coordinates": coords})
            elif geom_type == "MultiPolygon":
                for poly in coords:
                    polygon_data.append({"coordinates": poly})

        # ------------------------
        # Create Pydeck layers
        # ------------------------
        polygon_layer = pdk.Layer(
            "PolygonLayer",
            polygon_data,
            get_polygon="coordinates",
            get_fill_color="[0, 100, 255, 60]",
            get_line_color="[0, 50, 200]",
            pickable=False,
            extruded=False,
            stroked=True,
        )

        point_layer = pdk.Layer(
            "ScatterplotLayer",
            [{"lon": lon, "lat": lat}],
            get_position="[lon, lat]",
            get_color="[255, 0, 0]",
            get_radius=300,
        )

        view_state = pdk.ViewState(
            longitude=lon,
            latitude=lat,
            zoom=8,
            pitch=0,
        )

        st.subheader("📍 LGA Boundary Map")
        st.pydeck_chart(
            pdk.Deck(
                layers=[polygon_layer, point_layer],
                initial_view_state=view_state,
                map_style=None  # Offline-ready
            )
        )

    else:
        st.error("❌ No LGA found for this coordinate.")


