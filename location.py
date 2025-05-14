import streamlit as st
import json
from geopy.geocoders import GoogleV3
import requests
import streamlit.components.v1 as components


# Set page config
st.set_page_config(page_title="Live Location Tracker", layout="wide")

# Title
st.title("Live Location Tracker")

# Sidebar for API key input
with st.sidebar:
    st.header("API Configuration")
    google_maps_api_key = st.text_input("Enter Google Maps API Key", type="password")
    st.info("You need both Maps JavaScript API and Geocoding API enabled")

# Check if API key is provided
if not google_maps_api_key:
    st.warning("Please enter your Google Maps API key in the sidebar")
    st.stop()

# Initialize geocoder
geolocator = GoogleV3(api_key=google_maps_api_key)

# HTML and JavaScript for getting live location
html_code = f"""
<div id="map" style="height: 600px; width: 100%;"></div>
<script>
function initMap() {{
    // Create a map centered at (0,0) initially
    const map = new google.maps.Map(document.getElementById("map"), {{
        zoom: 15,
        center: {{lat: 0, lng: 0}},
    }});
    
    // Try to get the user's current location
    if (navigator.geolocation) {{
        navigator.geolocation.watchPosition(
            function(position) {{
                const userLocation = {{
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                }};
                
                // Center the map on the user's location
                map.setCenter(userLocation);
                
                // Add a marker at the user's location
                new google.maps.Marker({{
                    position: userLocation,
                    map: map,
                    title: "Your Location"
                }});
                
                // Send the coordinates back to Streamlit
                const data = {{
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                }};
                
                // Use Streamlit's custom component communication
                window.parent.postMessage(data, "*");
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

# Display the map
components.html(html_code, height=600)

# Placeholder for location data
if 'location_data' not in st.session_state:
    st.session_state.location_data = None

# JavaScript to Python communication
def update_location():
    # This function will be called when we receive location data from JavaScript
    try:
        # Get the arguments from JavaScript
        args = st.session_state.get('location_args')
        if args:
            st.session_state.location_data = args
    except Exception as e:
        st.error(f"Error updating location: {e}")

# Display location information when available
if st.session_state.location_data:
    loc_data = st.session_state.location_data
    lat, lng = loc_data['latitude'], loc_data['longitude']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Location Coordinates")
        st.write(f"Latitude: {lat:.6f}")
        st.write(f"Longitude: {lng:.6f}")
        st.write(f"Accuracy: ±{loc_data['accuracy']:.0f} meters")
        
        # Reverse geocoding to get address
        try:
            location = geolocator.reverse(f"{lat}, {lng}")
            if location:
                st.subheader("Address")
                st.write(location.address)
        except Exception as e:
            st.error(f"Could not get address: {e}")
    
    with col2:
        st.subheader("Map Data")
        st.json(loc_data)
else:
    st.info("Waiting for location data... Please allow location access in your browser.")

# Custom component to handle JavaScript communication
try:
    from streamlit.components.v1 import html, declare_component
    
    # This script listens for messages from the iframe and updates Streamlit
    comm_script = """
    <script>
    window.addEventListener('message', function(event) {
        // Only accept messages from the same origin
        if (event.origin !== window.location.origin) return;
        
        // Send data to Streamlit
        if (window.parent && window.parent.streamlitAPI) {
            window.parent.streamlitAPI.updateLocation(event.data);
        }
    });
    </script>
    """
    
    # Register the custom component
    declare_component("location_receiver", path=comm_script)
    
except ImportError:
    st.warning("Could not import components. Some features may not work.")
