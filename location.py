import streamlit as st
import requests
import geocoder
from typing import Optional, Tuple

def get_location_geocoder() -> Tuple[Optional[float], Optional[float]]:
    """
    Get location using geocoder library
    """
    g = geocoder.ip('me')
    if g.ok:
        return g.latlng[0], g.latlng[1]
    return None, None

def get_location_ipapi() -> Tuple[Optional[float], Optional[float]]:
    """
    Fallback method using ipapi.co service
    """
    try:
        response = requests.get('https://ipapi.co/json/')
        if response.status_code == 200:
            data = response.json()
            lat = data.get('latitude')
            lon = data.get('longitude')
            
            if lat is not None and lon is not None:
                # Store additional location data in session state
                st.session_state.location_data = {
                    'city': data.get('city'),
                    'region': data.get('region'),
                    'country': data.get('country_name'),
                    'ip': data.get('ip')
                }
                return lat, lon
    except requests.RequestException as e:
        st.error(f"Error retrieving location from ipapi.co: {str(e)}")
    return None, None

def get_location() -> Tuple[Optional[float], Optional[float]]:
    """
    Tries to get location first using geocoder, then falls back to ipapi.co
    """
    # Try geocoder first
    lat, lon = get_location_geocoder()
    
    # If geocoder fails, try ipapi
    if lat is None:
        st.info("Primary geolocation method unsuccessful, trying alternative...")
        lat, lon = get_location_ipapi()
    
    return lat, lon

def show_location_details():
    """
    Displays the additional location details if available
    """
    if 'location_data' in st.session_state:
        data = st.session_state.location_data
        st.write("Location Details:")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("📍 City:", data['city'])
            st.write("🏘️ Region:", data['region'])
        
        with col2:
            st.write("🌍 Country:", data['country'])
            st.write("🔍 IP:", data['ip'])

def main():
    st.title("IP Geolocation Demo")
    st.write("This app will attempt to detect your location using IP geolocation.")
    
    if st.button("Get My Location", type="primary"):
        with st.spinner("Retrieving your location..."):
            lat, lon = get_location()
            
            if lat is not None and lon is not None:
                st.success("Location retrieved successfully!")
                
                # Create two columns for coordinates
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Latitude", f"{lat:.4f}")
                with col2:
                    st.metric("Longitude", f"{lon:.4f}")
                
                # Show additional location details if available
                show_location_details()
                
                # Display location on a map
                st.write("📍 Location on Map:")
                st.map(data={'lat': [lat], 'lon': [lon]}, zoom=10)
            else:
                st.error("Could not determine your location. Please check your internet connection and try again.")
                
if __name__ == "__main__":
    main()
