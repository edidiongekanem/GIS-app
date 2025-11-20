# =========================================================
#                      PARCEL PLOTTER
# =========================================================
elif tool == "Parcel Plotter":
    st.header("📐 Parcel Boundary Plotter (UTM Coordinates)")
    st.write("Enter UTM Easting/Northing (Zone 32N, meters).")

    projected_crs = "EPSG:32632"
    transformer = Transformer.from_crs(projected_crs, "EPSG:4326", always_xy=True)

    num_points = st.number_input("Number of beacons:", min_value=3, step=1)

    utm_coords = []
    if num_points > 0:
        for i in range(num_points):
            col1, col2 = st.columns(2)
            e = col1.number_input(f"Point {i+1} → Easting (m)", key=f"e{i}", format="%.2f")
            n = col2.number_input(f"Point {i+1} → Northing (m)", key=f"n{i}", format="%.2f")
            utm_coords.append((e, n))

    if st.button("Plot Parcel"):

        try:
            if utm_coords[0] != utm_coords[-1]:
                utm_coords.append(utm_coords[0])

            polygon = Polygon(utm_coords)

            if not polygon.is_valid:
                st.error("❌ Invalid boundary shape. Check point sequence.")
            else:
                area = polygon.area
                st.success("✅ Parcel plotted successfully!")
                st.write(f"### Area: **{area:,.2f} m²**")

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

                # --- Auto-zoom ---
                lons, lats = zip(*ll_coords)
                lon_center = sum(lons)/len(lons)
                lat_center = sum(lats)/len(lats)
                lon_range = max(lons) - min(lons)
                lat_range = max(lats) - min(lats)
                max_range = max(lon_range, lat_range)
                import math
                zoom_level = 8 if max_range == 0 else min(17, 8 - math.log2(max_range/360))

                tile_layer = pdk.Layer(
                    "TileLayer",
                    "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
                    min_zoom=0,
                    max_zoom=19,
                    tile_size=256,
                    render_sub_layers=True,
                    pickable=False,
                )

                st.pydeck_chart(
                    pdk.Deck(
                        layers=[tile_layer, polygon_layer, point_layer],
                        initial_view_state=pdk.ViewState(
                            longitude=lon_center,
                            latitude=lat_center,
                            zoom=zoom_level,
                            pitch=0,
                        )
                    )
                )

                # --- PDF Sketch Download (Clean Layout Template) ---
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib import colors
                from io import BytesIO

                buffer = BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                # --- Title Block (Top-right) ---
                c.setFont("Helvetica-Bold", 12)
                title_y = height - 50
                line_spacing = 24  # double spacing (~2)
                lines = ["PLAN SHEWING LANDED PROPERTY", "OF", "----------------------------------",
                         "AT", "-----------------------------------", "-----------------------------------",
                         "-----------------------------------", "------------------------------------"]
                for i, line in enumerate(lines):
                    c.drawRightString(width - 40, title_y - i * line_spacing, line)  # 40pt margin from right

                # --- Scale & Center Polygon ---
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                parcel_width = max_lon - min_lon
                parcel_height = max_lat - min_lat
                scale_factor = 0.6

                page_width, page_height = width - 100, height - 200
                scale_x = page_width / parcel_width if parcel_width != 0 else 1
                scale_y = page_height / parcel_height if parcel_height != 0 else 1
                scale = scale_factor * min(scale_x, scale_y)

                center_x = (min_lon + max_lon)/2
                center_y = (min_lat + max_lat)/2
                page_center_x = width/2
                page_center_y = height/2 - 30

                def transform_point(lon, lat):
                    x = (lon - center_x) * scale + page_center_x
                    y = (lat - center_y) * scale + page_center_y
                    return x, y

                scaled_points = [transform_point(lon, lat) for lon, lat in ll_coords]

                # --- Draw black polygon ---
                c.setLineWidth(2)
                c.setStrokeColor(colors.black)
                x_points = [x for x, y in scaled_points]
                y_points = [y for x, y in scaled_points]
                c.lines(list(zip(x_points, y_points, x_points[1:] + [x_points[0]], y_points[1:] + [y_points[0]])))

                # --- Draw red points and labels ---
                c.setFillColor(colors.red)
                c.setFont("Helvetica", 10)
                for idx, (x, y) in enumerate(scaled_points, start=1):
                    c.circle(x, y, 3, fill=1)
                    c.setFillColor(colors.black)
                    c.drawString(x + 5, y + 2, f"P{idx}")
                    c.setFillColor(colors.red)

                # --- True North Symbol (above Point 1) ---
                x1, y1 = scaled_points[0]
                north_len = 70  # vertical offset from point 1
                c.setStrokeColor(colors.black)
                c.setLineWidth(1.5)
                c.line(x1, y1, x1, y1 + north_len)
                c.line(x1, y1 + north_len, x1 - 5, y1 + north_len - 10)
                c.line(x1, y1 + north_len, x1 + 5, y1 + north_len - 10)
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(x1, y1 + north_len + 10, "N")

                # --- Scale bar at bottom ---
                scale_bar_width = 100
                c.setStrokeColor(colors.black)
                c.line(width/2 - scale_bar_width/2, 50, width/2 + scale_bar_width/2, 50)
                c.drawCentredString(width/2, 35, "SCALE: 1:X (INSERT)")

                # --- Origin & Area ---
                c.setFont("Helvetica", 10)
                c.drawString(50, 20, "ORIGIN: UTM ZONE 32N")
                c.setFont("Helvetica-Bold", 12)
                c.setFillColor(colors.red)
                c.drawString(250, 20, f"AREA = {area:,.2f} m²")
                c.setFillColor(colors.black)

                c.showPage()
                c.save()
                buffer.seek(0)

                st.download_button(
                    label="💾 Download Parcel PDF",
                    data=buffer,
                    file_name="parcel_sketch_clean.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error: {e}")
