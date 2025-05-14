import streamlit as st
import streamlit.components.v1 as components
from geopy.geocoders import GoogleV3
import json

# Set page config
st.set_page_config(page_title="Live Location Tracker", layout="wide")

# Title
st.title("📍 Live Location Tracker")

# Sidebar for API key input
with st.sidebar:
    st.header("🔑 API Configuration")
    google_maps_api_key = st.text_input("Enter Google Maps API Key", type="password")
    st.info("Enable both Maps JavaScript API and Geocoding API on your key")

# Stop execution if no API key
if not google_maps_api_key:
    st.warning("Please enter your Google Maps API key in the sidebar.")
    st.stop()

# Initialize geocoder
geolocator = GoogleV3(api_key=google_maps_api_key)

# HTML + JS for map and location tracking
html_code = f"""
<div id="map" style="height: 600px; width: 100%;"></div>
<script>
function initMap() {{
    const map = new google.maps.Map(document.getElementById("map"), {{
        zoom: 15,
        center: {{lat: 0, lng: 0}},
    }});

    if (navigator.geolocation) {{
        navigator.geolocation.watchPosition(
            function(position) {{
                const userLocation = {{
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                }};
                map.setCenter(userLocation);

                new google.maps.Marker({{
                    position: userLocation,
                    map: map,
                    title: "Your Location"
                }});

                const data = {{
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }};
                const iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                iframe.name = 'streamlitLocationData';
                document.body.appendChild(iframe);
                const form = document.createElement('form');
                form.method = 'POST';
                form.target = 'streamlitLocationData';
                form.action = window.location.href;
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'location_data';
                input.value = JSON.stringify(data);
                form.appendChild(input);
                document.body.appendChild(form);
                form.submit();
            }},
            function(error) {{
                console.error("Error getting location:", error);
                alert("Error getting your location: " + error.message);
            }},
            {{
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 5000
            }}
        );
    }} else {{
        alert("Geolocation is not supported by this browser.");
    }}
}}
</script>
<script async defer src="https://maps.googleapis.com/maps/api/js?key={google_maps_api_key}&callback=initMap"></script>
"""

# Render the HTML map
components.html(html_code, height=600)

# Placeholder for session data
if "location_data" not in st.session_state:
    st.session_state.location_data = None

# Check for POST data in query params (JS-to-Streamlit workaround)
if "location_data" in st.query_params():
    try:
        loc_json = st.query_params()["location_data"][0]
        loc_data = json.loads(loc_json)
        st.session_state.location_data = loc_data
    except Exception as e:
        st.error(f"Failed to read location data: {e}")

# Display location info
if st.session_state.location_data:
    loc_data = st.session_state.location_data
    lat, lng = loc_data["latitude"], loc_data["longitude"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 Coordinates")
        st.write(f"**Latitude:** {lat:.6f}")
        st.write(f"**Longitude:** {lng:.6f}")
        st.write(f"**Accuracy:** ±{loc_data['accuracy']:.0f} meters")

        try:
            location = geolocator.reverse((lat, lng))
            if location:
                st.subheader("📍 Address")
                st.write(location.address)
        except Exception as e:
            st.error(f"Could not retrieve address: {e}")

    with col2:
        st.subheader("📦 Raw Location Data")
        st.json(loc_data)
else:
    st.info("Waiting for location data... Please allow location access in your browser.")
