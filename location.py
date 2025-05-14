import streamlit as st
from bokeh.models import Button as BokehButton
from bokeh.models import CustomJS
from bokeh.layouts import column
from streamlit_bokeh_events import streamlit_bokeh_events
import pandas as pd

st.set_page_config(page_title="GPS Locator", page_icon="📍", layout="centered")
st.title("📍 Real-Time GPS Location")

st.write("Click below to get your current location using your browser's GPS.")

# Streamlit fake trigger button
show_bokeh = st.button("👉 Click Here to Get My Location")

if show_bokeh:
    st.write("Now click the green button below and allow browser permission to get location.")

    # Real Bokeh location button
    bokeh_button = BokehButton(label="📍 Get Location", button_type="success", width=200)
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

    # Listen to the JS location event
    result = streamlit_bokeh_events(
        column(bokeh_button),
        events="GET_LOCATION",
        key="get_location_event",
        refresh_on_update=False,
        debounce_time=0,
        override_height=100,
    )

    # Show results
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

            st.write("### 🗺️ Your Location on Map")
            st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=13)
