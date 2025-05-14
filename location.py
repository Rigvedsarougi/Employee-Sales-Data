import streamlit as st
from bokeh.models import Button as BokehButton
from bokeh.models import CustomJS
from bokeh.layouts import column
from streamlit_bokeh_events import streamlit_bokeh_events
import pandas as pd

st.set_page_config(page_title="Real-Time GPS", page_icon="📍", layout="centered")
st.title("📍 Real-Time Location with Browser GPS")

st.write("Click the button below and allow location access in your browser when prompted.")

# Create a Bokeh button that actually shows up
bokeh_button = BokehButton(label="📍 Get My Location", button_type="success", width=200)

# Attach JS code to button
bokeh_button.js_on_event("button_click", CustomJS(code="""
    navigator.geolocation.getCurrentPosition(
        (loc) => {
            document.dispatchEvent(new CustomEvent("GET_LOCATION", {
                detail: {
                    lat: loc.coords.latitude,
                    lon: loc.coords.longitude,
                    accuracy: loc.coords.accuracy
                }
            }));
        },
        (err) => {
            document.dispatchEvent(new CustomEvent("GET_LOCATION", {
                detail: {
                    error: err.message
                }
            }));
        }
    );
"""))

# Display the button and listen for events
result = streamlit_bokeh_events(
    column(bokeh_button),
    events="GET_LOCATION",
    key="get_location_key",
    refresh_on_update=False,
    debounce_time=0,
    override_height=100,
)

# Handle and display result
if result and "GET_LOCATION" in result:
    loc = result["GET_LOCATION"]
    if "error" in loc:
        st.error(f"❌ Error: {loc['error']}")
    else:
        lat, lon = loc["lat"], loc["lon"]
        accuracy = loc.get("accuracy", "N/A")

        st.success("✅ Location retrieved successfully!")
        col1, col2 = st.columns(2)
        col1.metric("Latitude", f"{lat:.6f}")
        col2.metric("Longitude", f"{lon:.6f}")
        st.write(f"📏 Accuracy: {accuracy} meters")

        # Show on map
        st.write("### 🗺️ Your Location on Map")
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=13)
