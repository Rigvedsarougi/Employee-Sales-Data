import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time
import pytz
import requests
import time
from geopy.geocoders import Nominatim

# Initialize Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Load Google Maps API key from secrets
google_maps_api_key = st.secrets["google_maps"]["google_maps_api_key"]

# Constants for attendance sheet
ATTENDANCE_SHEET_COLUMNS = [
    "Attendance ID",
    "Employee Name",
    "Employee Code",
    "Designation",
    "Date",
    "Status",
    "Check-in Time",
    "Check-out Time",
    "Location Coordinates",
    "Location Address",
    "Location Timestamp",
    "Duration (minutes)"
]

# Hide Streamlit default UI elements
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

def get_ist_time():
    """Get current time in Indian Standard Time (IST)"""
    utc_now = datetime.now(pytz.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.astimezone(ist)

def display_login_header():
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <h1 style='margin-bottom: 0;'>Employee Portal</h1>
            <h2 style='margin-top: 0; color: #555;'>Login</h2>
        </div>
        """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_gsheet_data():
    """Load all required data from Google Sheets"""
    try:
        # Load data from Google Sheets
        Person = conn.read(worksheet="Person", ttl=5)
        Person = Person.dropna(how='all')
        return Person
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame()

def authenticate_employee(employee_name, passkey):
    try:
        employee_row = Person[Person['Employee Name'] == employee_name]
        if not employee_row.empty:
            employee_code = employee_row['Employee Code'].values[0]
            return str(passkey) == str(employee_code)
        return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False

def get_location_address(lat, lng):
    """Get human-readable address from coordinates using Geocoding API"""
    try:
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.reverse(f"{lat}, {lng}")
        return location.address if location else "Address not available"
    except Exception as e:
        st.error(f"Error getting address: {e}")
        return "Address lookup failed"

def generate_attendance_id():
    return f"ATT-{get_ist_time().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

def log_attendance_to_gsheet(conn, attendance_data):
    try:
        existing_data = conn.read(worksheet="Attendance", ttl=5)
        existing_data = existing_data.dropna(how='all')
        
        attendance_df = pd.DataFrame([attendance_data], columns=ATTENDANCE_SHEET_COLUMNS)
        
        updated_data = pd.concat([existing_data, attendance_df], ignore_index=True)
        conn.update(worksheet="Attendance", data=updated_data)
        return True, None
    except Exception as e:
        return False, str(e)

def check_existing_attendance(employee_name):
    try:
        existing_data = conn.read(worksheet="Attendance", ttl=5)
        existing_data = existing_data.dropna(how='all')
        
        if existing_data.empty:
            return False
        
        current_date = get_ist_time().strftime("%d-%m-%Y")
        employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
        
        existing_records = existing_data[
            (existing_data['Employee Code'] == employee_code) & 
            (existing_data['Date'] == current_date)
        ]
        
        return not existing_records.empty
        
    except Exception as e:
        st.error(f"Error checking existing attendance: {str(e)}")
        return False

def record_attendance(employee_name, status, location_coords=None, check_out=False):
    try:
        employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
        designation = Person[Person['Employee Name'] == employee_name]['Designation'].values[0]
        current_date = get_ist_time().strftime("%d-%m-%Y")
        current_time = get_ist_time().strftime("%H:%M:%S")
        timestamp = get_ist_time().strftime("%d-%m-%Y %H:%M:%S")
        
        # Get address from coordinates if available
        location_address = ""
        if location_coords:
            lat, lng = location_coords
            location_address = get_location_address(lat, lng)
        
        if check_out:
            # Update existing attendance record for check-out
            existing_data = conn.read(worksheet="Attendance", ttl=5)
            existing_data = existing_data.dropna(how='all')
            
            # Find today's check-in record for this employee
            mask = "
                (existing_data['Employee Code'] == employee_code) & 
                (existing_data['Date'] == current_date) & 
                (existing_data['Check-out Time'].isna()"
            
            if not existing_data[mask].empty:
                # Calculate duration
                check_in_time = datetime.strptime(existing_data[mask].iloc[0]['Check-in Time'], "%H:%M:%S").time()
                check_out_time = datetime.strptime(current_time, "%H:%M:%S").time()
                
                check_in_dt = datetime.combine(datetime.today(), check_in_time)
                check_out_dt = datetime.combine(datetime.today(), check_out_time)
                duration = (check_out_dt - check_in_dt).total_seconds() / 60
                
                # Update the record
                existing_data.loc[mask, 'Check-out Time'] = current_time
                existing_data.loc[mask, 'Duration (minutes)'] = round(duration, 2)
                
                # Write back to Google Sheets
                conn.update(worksheet="Attendance", data=existing_data)
                return True, None
            else:
                return False, "No check-in record found for today"
        else:
            # Create new check-in record
            attendance_id = generate_attendance_id()
            
            attendance_data = {
                "Attendance ID": attendance_id,
                "Employee Name": employee_name,
                "Employee Code": employee_code,
                "Designation": designation,
                "Date": current_date,
                "Status": status,
                "Check-in Time": current_time,
                "Check-out Time": "",
                "Location Coordinates": f"{location_coords[0]}, {location_coords[1]}" if location_coords else "",
                "Location Address": location_address,
                "Location Timestamp": timestamp,
                "Duration (minutes)": ""
            }
            
            return log_attendance_to_gsheet(conn, attendance_data)
            
    except Exception as e:
        return False, f"Error creating attendance record: {str(e)}"

def get_current_location():
    """Get current location using browser's geolocation API through Streamlit"""
    try:
        # This will show a button to request location access
        location = st.session_state.get('location', None)
        
        if location:
            return (location['latitude'], location['longitude'])
        else:
            return None
    except Exception as e:
        st.error(f"Error getting location: {e}")
        return None

def location_tracking_page():
    st.title("Employee Location Tracking")
    selected_employee = st.session_state.employee_name
    
    # Check if already checked in today
    checked_in = check_existing_attendance(selected_employee)
    
    if checked_in:
        st.warning("You have already checked in today.")
        
        # Check if already checked out
        existing_data = conn.read(worksheet="Attendance", ttl=5)
        existing_data = existing_data.dropna(how='all')
        
        current_date = get_ist_time().strftime("%d-%m-%Y")
        employee_code = Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0]
        
        today_record = existing_data[
            (existing_data['Employee Code'] == employee_code) & 
            (existing_data['Date'] == current_date)
        ].iloc[0]
        
        if pd.isna(today_record['Check-out Time']):
            # Employee can check out
            if st.button("Check Out", key="check_out_button"):
                # Get current location for check-out
                st.write("Please allow location access for check-out...")
                location = get_current_location()
                
                if location:
                    success, error = record_attendance(
                        selected_employee,
                        "Present",  # Status remains the same
                        location_coords=location,
                        check_out=True
                    )
                    
                    if success:
                        st.success("Checked out successfully! Your location has been recorded.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"Error checking out: {error}")
                else:
                    st.error("Could not get your current location. Please try again.")
        else:
            st.info(f"You checked out at {today_record['Check-out Time']}")
            
        # Show today's attendance record
        st.subheader("Today's Attendance Record")
        st.json({
            "Check-in Time": today_record['Check-in Time'],
            "Check-out Time": today_record['Check-out Time'] if not pd.isna(today_record['Check-out Time']) else "Not checked out yet",
            "Location": today_record['Location Address'],
            "Duration": f"{today_record['Duration (minutes)']} minutes" if not pd.isna(today_record['Duration (minutes)']) else "N/A"
        })
        
    else:
        # Employee needs to check in
        st.info("Please check in to record your attendance and location")
        
        if st.button("Check In", key="check_in_button"):
            # Get current location
            st.write("Please allow location access for check-in...")
            location = get_current_location()
            
            if location:
                success, error = record_attendance(
                    selected_employee,
                    "Present",
                    location_coords=location
                )
                
                if success:
                    st.success("Checked in successfully! Your location has been recorded.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"Error checking in: {error}")
            else:
                st.error("Could not get your current location. Please try again.")
    
    # Display attendance history
    st.subheader("Your Attendance History")
    try:
        attendance_data = conn.read(worksheet="Attendance", ttl=5)
        attendance_data = attendance_data.dropna(how='all')
        
        employee_code = Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0]
        employee_data = attendance_data[attendance_data['Employee Code'] == employee_code]
        
        if not employee_data.empty:
            # Sort by date descending
            employee_data = employee_data.sort_values('Date', ascending=False)
            
            # Display only relevant columns
            display_cols = [
                'Date', 'Check-in Time', 'Check-out Time', 
                'Duration (minutes)', 'Location Address', 'Status'
            ]
            st.dataframe(
                employee_data[display_cols],
                hide_index=True,
                use_container_width=True
            )
            
            # Add download button
            csv = employee_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Attendance History",
                csv,
                "attendance_history.csv",
                "text/csv",
                key='download-attendance-csv'
            )
        else:
            st.info("No attendance records found for your account")
    except Exception as e:
        st.error(f"Error loading attendance history: {e}")

def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'employee_name' not in st.session_state:
        st.session_state.employee_name = None
    if 'location' not in st.session_state:
        st.session_state.location = None

    # Load employee data
    global Person
    Person = load_gsheet_data()
    
    if Person.empty:
        st.error("Failed to load employee data. Please check your connection.")
        st.stop()

    if not st.session_state.authenticated:
        display_login_header()
        
        employee_names = Person['Employee Name'].dropna().tolist()
        
        form_col1, form_col2, form_col3 = st.columns([1, 2, 1])
        
        with form_col2:
            with st.container():
                employee_name = st.selectbox(
                    "Select Your Name", 
                    employee_names, 
                    key="employee_select"
                )
                passkey = st.text_input(
                    "Enter Your Employee Code", 
                    type="password", 
                    key="passkey_input"
                )
                
                login_button = st.button(
                    "Log in", 
                    key="login_button",
                    use_container_width=True
                )
                
                if login_button:
                    if authenticate_employee(employee_name, passkey):
                        st.session_state.authenticated = True
                        st.session_state.employee_name = employee_name
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
    else:
        # Add JavaScript for geolocation
        st.markdown("""
        <script>
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(showPosition);
            } else {
                window.alert("Geolocation is not supported by this browser.");
            }
        }
        
        function showPosition(position) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                key: 'location',
                value: {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                }
            }, '*');
        }
        
        // Listen for Streamlit's ready event
        window.addEventListener('load', function() {
            window.parent.postMessage({
                type: 'streamlit:componentReady',
                key: 'location'
            }, '*');
        });
        </script>
        """, unsafe_allow_html=True)
        
        # Button to trigger location access
        if st.button("Get My Current Location"):
            st.markdown("<script>getLocation();</script>", unsafe_allow_html=True)
            st.write("Please allow location access in your browser...")
            
            # Wait for location to be set
            for i in range(5):
                time.sleep(1)
                if st.session_state.get('location'):
                    st.success(f"Location captured: {st.session_state.location}")
                    break
            else:
                st.error("Could not get location. Please try again.")
        
        # Main page content
        st.title(f"Welcome, {st.session_state.employee_name}")
        
        # Navigation
        page_options = ["Location Tracking", "Attendance History"]
        selected_page = st.selectbox("Navigation", page_options)
        
        if selected_page == "Location Tracking":
            location_tracking_page()
        elif selected_page == "Attendance History":
            # This is already included in the location tracking page
            location_tracking_page()

if __name__ == "__main__":
    main()
