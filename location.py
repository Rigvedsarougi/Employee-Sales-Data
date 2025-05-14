import streamlit as st
from bokeh.models.widgets import Button as BokehButton
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
import pandas as pd

st.set_page_config(page_title="Location Access", page_icon="📍", layout="centered")
st.title("📍 Real-Time Location Finder")

# Info to user
st.write("Click the green button below to get your current location using your browser's GPS. Allow permission when prompted.")

# Actual visible button with spacing
st.markdown("### ")
st.markdown("### ")

# Create a styled Bokeh button that visually looks distinct
loc_button = BokehButton(label="📍 Get My Location", button_type="success", width=250)
loc_button.js_on_event("button_click", CustomJS(code="""
    navigator.geolocation.getCurrentPosition(
        (loc) => {
            document.dispatchEvent(new CustomEvent("GET_LOCATION", {
                detail: {
                    lat: loc.coords.latitude,
                    lon: loc.coords.longitude,
                    accuracy: loc.coords.accuracy
                }
            }))
        },
        (err) => {
            document.dispatchEvent(new CustomEvent("GET_LOCATION", {
                detail: {
                    error: err.message
                }
            }))
        }
    )
"""))

# Streamlit-Bokeh event binding
result = streamlit_bokeh_events(
    loc_button,
    events="GET_LOCATION",
    key="get_location_event",
    refresh_on_update=False,
    override_height=100,
    debounce_time=0
)

# Handle result
if result and "GET_LOCATION" in result:
    details = result["GET_LOCATION"]

    if "error" in details:
        st.error(f"❌ Error: {details['error']}")
    else:
        lat = details["lat"]
        lon = details["lon"]
        accuracy = details.get("accuracy", "N/A")

        st.success("✅ Location successfully retrieved!")

        col1, col2 = st.columns(2)
        col1.metric("Latitude", f"{lat:.6f}")
        col2.metric("Longitude", f"{lon:.6f}")
        st.write(f"📏 Accuracy: {accuracy} meters")

        st.write("### 🗺️ Map:")
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=13)
