import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
import pandas as pd

# Streamlit App Title
st.set_page_config(page_title="Browser Location Access", page_icon="🌍", layout="centered")
st.title("🌍 Get Your Real-Time Location")
st.write("Click the button below to get your current location using your browser's GPS (HTML5 Geolocation).")

# Bokeh Button for Triggering JS
loc_button = Button(label="📍 Get My Location", button_type="success")
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

# Capture JS event
result = streamlit_bokeh_events(
    loc_button,
    events="GET_LOCATION",
    key="get_location",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0
)

# Handle Result
if result and "GET_LOCATION" in result:
    details = result["GET_LOCATION"]
    
    if "error" in details:
        st.error(f"Error getting location: {details['error']}")
    else:
        lat = details['lat']
        lon = details['lon']
        accuracy = details.get('accuracy', 'N/A')
        
        st.success("✅ Location Retrieved!")
        
        col1, col2 = st.columns(2)
        col1.metric("Latitude", f"{lat:.6f}")
        col2.metric("Longitude", f"{lon:.6f}")
        st.write(f"📏 Accuracy: {accuracy} meters")
        
        # Show map
        st.write("🗺️ Location on Map:")
        st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=13)
