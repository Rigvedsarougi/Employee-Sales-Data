import streamlit as st
from streamlit_browser_location import get_location
import pandas as pd

def show_location_details(loc):
    """
    Displays location details from the GPS-based response.
    """
    st.write("### 📍 Location Coordinates:")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Latitude", f"{loc['latitude']:.6f}")
    with col2:
        st.metric("Longitude", f"{loc['longitude']:.6f}")

    # Show accuracy and timestamp if available
    st.write("### ℹ️ Additional Info")
    st.write(f"**Accuracy:** {loc.get('accuracy', 'N/A')} meters")
    st.write(f"**Timestamp:** {loc.get('timestamp', 'N/A')}")

    # Show location on a map
    st.write("### 🗺️ Location on Map:")
    st.map(pd.DataFrame({'lat': [loc['latitude']], 'lon': [loc['longitude']]}), zoom=13)


def main():
    st.set_page_config(page_title="Accurate Location Finder", page_icon="📍", layout="centered")
    st.title("📍 Accurate GPS Location using Streamlit")
    st.write("Click the button below and allow location access to retrieve your current position using your browser.")

    loc = get_location()

    if loc:
        st.success("Location retrieved successfully!")
        show_location_details(loc)
    else:
        st.info("Waiting for you to allow location access in your browser...")

if __name__ == "__main__":
    main()
