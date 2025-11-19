import streamlit as st
import geopandas as gpd
from shapely.geometry import Point, Polygon
from pyproj import Transformer
import pydeck as pdk
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from math import atan2, degrees, sqrt
import io

st.set_page_config(page_title="Geo Tools Suite", layout="centered")

st.title("🌍 Geo Tools Suite")

tool = st.sidebar.selectbox(
    "Select a Tool",
    ["🏠 Home", "Nigeria LGA Finder", "Parcel Plotter"]
)

if tool == "🏠 Home":
    st.header("Welcome!")
    st.write("""
    Select any of the tools from the sidebar:

    ### 🗺️ Nigeria LGA Finder  
    Enter Easting/Northing and find which LGA the point belongs to.

    ### 📐 Parcel Plotter  
    Input coordinates, plot a parcel boundary and calculate the area.
    """)

elif tool == "Parcel Plotter":

    if "parcel_plotted" not in st.session_state:
        st.session_state.parcel_plotted = False
    if "parcel_area" not in st.session_state:
        st.session_state.parcel_area = 0

    st.header("📐 Parcel Boundary Plotter (UTM Coordinates)")

    num_points = st.number_input("Number of beacons:", min_value=3, step=1)

    utm_coords = []
    if num_points > 0:
        for i in range(num_points):
            col1, col2 = st.columns(2)
            e = col1.number_input(f"Point {i+1} → Easting (m)", key=f"e{i}", format="%.2f")
            n = col2.number_input(f"Point {i+1} → Northing (m)", key=f"n{i}", format="%.2f")
            utm_coords.append((e, n))

    if st.button("Plot Parcel"):
        if utm_coords[0] != utm_coords[-1]:
            utm_coords.append(utm_coords[0])
        st.session_state.parcel_plotted = True
        st.session_state.utm_coords = utm_coords

        polygon = Polygon(utm_coords)
        if not polygon.is_valid:
            st.error("❌ Invalid boundary shape. Check point sequence.")
        else:
            st.session_state.parcel_area = polygon.area
            st.success(f"✅ Parcel plotted successfully! Area: {st.session_state.parcel_area:,.2f} m²")

            transformer = Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)
            ll_coords = [transformer.transform(x, y) for x, y in utm_coords]

            polygon_data = [{"coordinates": [ll_coords]}]

            polygon_layer = pdk.Layer(
                "PolygonLayer",
                polygon_data,
                get_polygon="coordinates",
                get_fill_color="[0, 150, 255, 80]",
                get_line_color="[0, 50, 200]",
                stroked=True,
            )

            point_layer = pdk.Layer(
                "ScatterplotLayer",
                [{"lon": lon, "lat": lat} for lon, lat in ll_coords],
                get_position="[lon, lat]",
                get_color="[255, 0, 0]",
                radius_scale=1,
                radius_min_pixels=3,
                radius_max_pixels=30,
            )

            centroid_lon, centroid_lat = transformer.transform(polygon.centroid.x, polygon.centroid.y)

            st.pydeck_chart(
                pdk.Deck(
                    layers=[polygon_layer, point_layer],
                    initial_view_state=pdk.ViewState(
                        longitude=centroid_lon,
                        latitude=centroid_lat,
                        zoom=17
                    ),
                    map_style=None
                )
            )

    if st.session_state.parcel_plotted:
        col1, col2 = st.columns(2)

        # Sketch Plan PDF
        sketch_buffer = io.BytesIO()
        story = [Paragraph("<b>Parcel Sketch Plan</b>", getSampleStyleSheet()['Title']), Spacer(1, 12), Paragraph("(Sketch will be drawn in PDF)", getSampleStyleSheet()['Normal'])]
        SimpleDocTemplate(sketch_buffer, pagesize=A4).build(story)
        sketch_buffer.seek(0)
        col1.download_button("📄 Print Sketch Plan", data=sketch_buffer.getvalue(), file_name="parcel_sketch_plan.pdf", mime="application/pdf")

        # Computation Sheet PDF
        comp_buffer = io.BytesIO()
        story = [Paragraph("<b>Parcel Computation Sheet</b>", getSampleStyleSheet()['Title']), Spacer(1, 12), Paragraph(f"<b>Total Area:</b> {st.session_state.parcel_area:,.2f} m²", getSampleStyleSheet()['Normal']), Spacer(1, 12)]

        coords = st.session_state.utm_coords
        if coords and len(coords) > 1:
            table_data = [["Point ID", "Easting", "Northing", "Distance (m)", "Bearing (°)", "Angle (°)"]]

            def compute_distance(p1, p2):
                return sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

            def compute_bearing(p1, p2):
                angle = degrees(atan2(p2[0]-p1[0], p2[1]-p1[1]))
                return (angle + 360) % 360

            n = len(coords) - 1
            bearings = []
            for i in range(n):
                p1 = coords[i]
                p2 = coords[i+1]
                dist = compute_distance(p1, p2)
                bearing = compute_bearing(p1, p2)
                bearings.append(bearing)
                table_data.append([str(i+1), f"{p1[0]:.2f}", f"{p1[1]:.2f}", f"{dist:.2f}", f"{bearing:.2f}", ""])

            for i in range(1, n):
                table_data[i][5] = f"{(bearings[i] - bearings[i-1]) % 360:.2f}"

            coord_table = Table(table_data, colWidths=[50, 90, 90, 80, 80, 60])
            coord_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER')
            ]))
            story.append(coord_table)
            story.append(Spacer(1, 20))

        SimpleDocTemplate(comp_buffer, pagesize=A4).build(story)
        comp_buffer.seek(0)
        col2.download_button("📄 Print Computation Sheet", data=comp_buffer.getvalue(), file_name="parcel_computation_sheet.pdf", mime="application/pdf")
