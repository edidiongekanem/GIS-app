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
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.graphics import renderPDF
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

    if st.session_state.parcel_plotted:
        if st.button("📄 Print Sketch Plan"):
            try:
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
                styles = getSampleStyleSheet()
                story = []

                story.append(Paragraph("<b>Parcel Sketch Plan</b>", styles['Title']))
                story.append(Spacer(1, 12))
                story.append(Paragraph(f"<b>Area:</b> {st.session_state.parcel_area:,.2f} m²", styles['Normal']))
                story.append(Spacer(1, 12))

                # Draw the polygon using lines instead of RLPolygon
                drawing = Drawing(400, 400)
                coords = st.session_state.utm_coords

                xs, ys = zip(*coords)
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                scale_x = 350 / (max_x - min_x) if max_x != min_x else 1
                scale_y = 350 / (max_y - min_y) if max_y != min_y else 1
                scale = min(scale_x, scale_y)

                norm_coords = [((x - min_x) * scale + 25, (y - min_y) * scale + 25) for x, y in coords]

                # Draw edges
                for i in range(len(norm_coords)-1):
                    x1, y1 = norm_coords[i]
                    x2, y2 = norm_coords[i+1]
                    drawing.add(Line(x1, y1, x2, y2, strokeColor=colors.blue, strokeWidth=1))

                # Draw beacon points
                for idx, (x, y) in enumerate(norm_coords[:-1]):  # skip last repeated point
                    drawing.add(Line(x-2, y-2, x+2, y+2, strokeColor=colors.red))
                    drawing.add(Line(x-2, y+2, x+2, y-2, strokeColor=colors.red))
                    drawing.add(String(x+3, y+3, str(idx+1), fontSize=8, fillColor=colors.black))

                story.append(drawing)

                # Add coordinate table
                table_data = [["Point", "Easting", "Northing"]]
                for idx, (xe, yn) in enumerate(coords[:-1]):
                    table_data.append([str(idx+1), f"{xe:.2f}", f"{yn:.2f}"])

                coord_table = Table(table_data, colWidths=[60, 120, 120])
                coord_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER')
                ]))

                story.append(Spacer(1, 20))
                story.append(coord_table)

                doc.build(story)
                buffer.seek(0)
                st.download_button("⬇️ Download Sketch Plan", buffer, file_name="parcel_sketch_plan.pdf", mime="application/pdf")

            except Exception as e:
                st.error(f"PDF error: {e}")
