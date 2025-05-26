import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
from datetime import datetime, time
import os
import uuid
from PIL import Image
from datetime import datetime, time, timedelta
import pytz

import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime
import pytz
import time
import pandas as pd

def log_location_history(conn, employee_name, lat, lng):
    employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
    designation = Person[Person['Employee Name'] == employee_name]['Designation'].values[0]
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%H:%M")
    gmaps_link = f"https://maps.google.com/?q={lat},{lng}"
    entry = {
        "Employee Name": employee_name,
        "Employee Code": employee_code,
        "Designation": designation,
        "Date": date_str,
        "Time": time_str,
        "Latitude": lat,
        "Longitude": lng,
        "Google Maps Link": gmaps_link
    }
    try:
        existing = conn.read(worksheet="LocationHistory", usecols=list(range(len(LOCATION_HISTORY_COLUMNS))), ttl=5)
        existing = existing.dropna(how="all")
        new_df = pd.DataFrame([entry], columns=LOCATION_HISTORY_COLUMNS)
        updated = pd.concat([existing, new_df], ignore_index=True)
        conn.update(worksheet="LocationHistory", data=updated)
        return True, None
    except Exception as e:
        return False, str(e)

def hourly_location_auto_log(conn, selected_employee):
    if not selected_employee:
        return
    result = streamlit_js_eval(
        js_expressions="""
            new Promise((resolve) => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        pos => resolve({latitude: pos.coords.latitude, longitude: pos.coords.longitude, ts: Date.now()}),
                        err => resolve({latitude: null, longitude: null, ts: Date.now()})
                    );
                } else {
                    resolve({latitude: null, longitude: null, ts: Date.now()});
                }
            });
        """,
        key=f"geo_hourly_{int(time.time() // 3600)}"
    ) or {}

    lat = result.get("latitude")
    lng = result.get("longitude")

    if lat and lng:
        current_hour = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H")
        logged_key = f"hourly_logged_{selected_employee}_{current_hour}"
        if not st.session_state.get(logged_key, False):
            success, error = log_location_history(conn, selected_employee, lat, lng)
            if success:
                st.session_state[logged_key] = True

st.set_page_config(page_title="Location Logger", layout="centered")

def get_ist_time():
    """Get current time in Indian Standard Time (IST)"""
    utc_now = datetime.now(pytz.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.astimezone(ist)

def display_login_header():
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        try:
            logo = Image.open("logo.png")
            st.image(logo, use_container_width=True)
        except FileNotFoundError:
            st.warning("Logo image not found. Please ensure 'logo.png' exists in the same directory.")
        except Exception as e:
            st.warning(f"Could not load logo: {str(e)}")
        
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <h1 style='margin-bottom: 0;'>Employee Portal</h1>
            <h2 style='margin-top: 0; color: #555;'>Login</h2>
        </div>
        """, unsafe_allow_html=True)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stActionButton > button[title="Open source on GitHub"] {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

hide_footer_style = """
    <style>
    footer {
        visibility: hidden;
    }
    footer:after {
        content: '';
        display: none;
    }
    .css-15tx938.e8zbici2 {  /* This class targets the footer in some Streamlit builds */
        display: none !important;
    }
    </style>
"""

st.markdown(hide_footer_style, unsafe_allow_html=True)

def validate_data_before_write(df, expected_columns):
    """Validate data structure before writing to Google Sheets"""
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Data must be a pandas DataFrame")
    
    missing_cols = set(expected_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    if df.empty:
        raise ValueError("Cannot write empty dataframe")
    
    return True

def backup_sheet(conn, worksheet_name):
    """Create a timestamped backup of the worksheet"""
    try:
        data = conn.read(worksheet=worksheet_name, ttl=1)
        timestamp = get_ist_time().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{worksheet_name}_backup_{timestamp}"
        conn.update(worksheet=backup_name, data=data)
    except Exception as e:
        st.error(f"Warning: Failed to create backup - {str(e)}")

def attempt_data_recovery(conn, worksheet_name):
    """Attempt to recover from the most recent backup"""
    try:
        # Get list of all worksheets
        all_sheets = conn.list_worksheets()
        backups = [s for s in all_sheets if s.startswith(f"{worksheet_name}_backup")]
        
        if backups:
            # Sort backups by timestamp (newest first)
            backups.sort(reverse=True)
            latest_backup = backups[0]
            
            # Restore from backup
            backup_data = conn.read(worksheet=latest_backup)
            conn.update(worksheet=worksheet_name, data=backup_data)
            return True
        return False
    except Exception as e:
        st.error(f"Recovery failed: {str(e)}")
        return False

def safe_sheet_operation(operation, *args, **kwargs):
    """Wrapper for safe sheet operations with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"Operation failed after {max_retries} attempts: {str(e)}")
                if "Attendance" in str(args):
                    worksheet_name = [a for a in args if isinstance(a, str) and "Attendance" in a][0]
                    if attempt_data_recovery(conn, worksheet_name):
                        st.success("Data recovery attempted from backup")
                raise
            time.sleep(1 * (attempt + 1))  # Exponential backoff

# Constants
LOCATION_HISTORY_COLUMNS = [
    "Employee Name",
    "Employee Code",
    "Designation",
    "Date",
    "Time",
    "Latitude",
    "Longitude",
    "Google Maps Link"
]

ATTENDANCE_SHEET_COLUMNS = [
    "Attendance ID",
    "Employee Name",
    "Employee Code",
    "Designation",
    "Date",
    "Status",
    "Location Link",
    "Leave Reason",
    "Check-in Time",
    "Check-in Date Time"
]

# Establishing a Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Load data
Person = pd.read_csv('Invoice - Person.csv')

# Company Details with ALLGEN TRADING logo
company_name = "BIOLUME SKIN SCIENCE PRIVATE LIMITED"
company_address = """Ground Floor Rampal Awana Complex,
Rampal Awana Complex, Indra Market,
Sector-27, Atta, Noida, Gautam Buddha Nagar,
Uttar Pradesh 201301
GSTIN/UIN: 09AALCB9426H1ZA
State Name: Uttar Pradesh, Code: 09
"""
company_logo = 'ALLGEN TRADING logo.png'

def generate_attendance_id():
    return f"ATT-{get_ist_time().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

def record_attendance(employee_name, status, location_link="", leave_reason=""):
    try:
        employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
        designation = Person[Person['Employee Name'] == employee_name]['Designation'].values[0]
        current_date = get_ist_time().strftime("%d-%m-%Y")
        current_datetime = get_ist_time().strftime("%d-%m-%Y %H:%M:%S")
        check_in_time = get_ist_time().strftime("%H:%M:%S")
        
        attendance_id = generate_attendance_id()
        
        attendance_data = {
            "Attendance ID": attendance_id,
            "Employee Name": employee_name,
            "Employee Code": employee_code,
            "Designation": designation,
            "Date": current_date,
            "Status": status,
            "Location Link": location_link,
            "Leave Reason": leave_reason,
            "Check-in Time": check_in_time,
            "Check-in Date Time": current_datetime
        }
        
        attendance_df = pd.DataFrame([attendance_data])
        
        success, error = log_attendance_to_gsheet(conn, attendance_df)
        
        if success:
            return attendance_id, None
        else:
            return None, error
            
    except Exception as e:
        return None, f"Error creating attendance record: {str(e)}"

def check_existing_attendance(employee_name):
    try:
        existing_data = conn.read(worksheet="Attendance", usecols=list(range(len(ATTENDANCE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how="all")
        
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

def authenticate_employee(employee_name, passkey):
    try:
        employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
        return str(passkey) == str(employee_code)
    except:
        return False

def resources_page():
    hourly_location_auto_log(conn, st.session_state.employee_name)
    st.title("Company Resources")
    st.markdown("Download important company documents and product catalogs.")
    
    # Define the resources
    resources = [
        {
            "name": "Product Catalogue",
            "description": "Complete list of all available products with specifications",
            "file_path": "Biolume Salon Prices Catalogue.pdf"
        },
        {
            "name": "Employee Handbook",
            "description": "Company policies, procedures, and guidelines for employees",
            "file_path": "Biolume Employee Handbook.pdf"
        },
        {
            "name": "Facial Treatment Catalogue",
            "description": "Complete list of all Facial products with specifications",
            "file_path": "Biolume's Facial Treatment Catalogue.pdf"
        }
    ]
    
    # Display each resource in a card-like format
    for resource in resources:
        with st.container():
            st.subheader(resource["name"])
            st.markdown(resource["description"])
            
            # Check if file exists
            if os.path.exists(resource["file_path"]):
                with open(resource["file_path"], "rb") as file:
                    btn = st.download_button(
                        label=f"Download {resource['name']}",
                        data=file,
                        file_name=resource["file_path"],
                        mime="application/pdf",
                        key=f"download_{resource['name']}"
                    )
            else:
                st.error(f"File not found: {resource['file_path']}")
            
            st.markdown("---")  # Divider between resources

def add_back_button():
    st.markdown("""
    <style>
    .back-button {
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 1000;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("← logout", key="back_button"):
        st.session_state.authenticated = False
        st.session_state.selected_mode = None
        st.rerun()

def log_attendance_to_gsheet(conn, attendance_data):
    try:
        existing_data = conn.read(worksheet="Attendance", usecols=list(range(len(ATTENDANCE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how="all")
        
        attendance_data = attendance_data.reindex(columns=ATTENDANCE_SHEET_COLUMNS)
        
        updated_data = pd.concat([existing_data, attendance_data], ignore_index=True)
        updated_data = updated_data.drop_duplicates(subset=["Attendance ID"], keep="last")
        
        conn.update(worksheet="Attendance", data=updated_data)
        return True, None
    except Exception as e:
        return False, str(e)

def attendance_page():
    hourly_location_auto_log(conn, st.session_state.employee_name)
    st.title("Attendance Management")
    selected_employee = st.session_state.employee_name

    if check_existing_attendance(selected_employee):
        st.warning("You have already marked your attendance for today.")
        return

    st.subheader("Attendance Status")
    status = st.radio("Select Status", ["Present", "Half Day", "Leave"], index=0, key="attendance_status")

    if status in ["Present", "Half Day"]:
        st.subheader("Location Verification (Auto)")

        result = streamlit_js_eval(
            js_expressions="""
                new Promise((resolve) => {
                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(
                            pos => resolve({latitude: pos.coords.latitude, longitude: pos.coords.longitude}),
                            err => resolve({latitude: null, longitude: null})
                        );
                    } else {
                        resolve({latitude: null, longitude: null});
                    }
                });
            """,
            key="geo"
        ) or {}

        lat = result.get("latitude")
        lng = result.get("longitude")

        if lat and lng:
            gmaps_link = f"https://maps.google.com/?q={lat},{lng}"
            st.success(f"Fetched Location: [View on Google Maps]({gmaps_link})")
        else:
            gmaps_link = ""
            st.info("Waiting for location permission...")

        if lat and lng and st.button("Mark Attendance", key="mark_attendance_button"):
            with st.spinner("Recording attendance..."):
                attendance_id, error = record_attendance(
                    selected_employee,
                    status,
                    location_link=gmaps_link
                )
                if error:
                    st.error(f"Failed to record attendance: {error}")
                else:
                    st.success(f"Attendance recorded successfully! ID: {attendance_id}")
                    st.balloons()

    else:
        st.subheader("Leave Details")
        leave_types = ["Sick Leave", "Personal Leave", "Vacation", "Other"]
        leave_type = st.selectbox("Leave Type", leave_types, key="leave_type")
        leave_reason = st.text_area("Reason for Leave",
                                   placeholder="Please provide details about your leave",
                                   key="leave_reason")
        if st.button("Submit Leave Request", key="submit_leave_button"):
            if not leave_reason:
                st.error("Please provide a reason for your leave")
            else:
                full_reason = f"{leave_type}: {leave_reason}"
                with st.spinner("Submitting leave request..."):
                    attendance_id, error = record_attendance(
                        selected_employee,
                        "Leave",
                        leave_reason=full_reason
                    )
                    if error:
                        st.error(f"Failed to submit leave request: {error}")
                    else:
                        st.success(f"Leave request submitted successfully! ID: {attendance_id}")

def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = None
    if 'employee_name' not in st.session_state:
        st.session_state.employee_name = None

    if not st.session_state.authenticated:
        # Display the centered logo and heading
        display_login_header()

        employee_names = Person['Employee Name'].tolist()

        # Create centered form
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
                        # Immediately fetch and log location after login
                        result = streamlit_js_eval(
                            js_expressions="""
                                new Promise((resolve) => {
                                    if (navigator.geolocation) {
                                        navigator.geolocation.getCurrentPosition(
                                            pos => resolve({latitude: pos.coords.latitude, longitude: pos.coords.longitude}),
                                            err => resolve({latitude: null, longitude: null})
                                        );
                                    } else {
                                        resolve({latitude: null, longitude: null});
                                    }
                                });
                            """,
                            key=f"geo_login_{employee_name}_{int(time.time())}"
                        ) or {}

                        lat = result.get("latitude")
                        lng = result.get("longitude")
                        if lat and lng:
                            log_location_history(conn, employee_name, lat, lng)
                            gmaps_link = f"https://maps.google.com/?q={lat},{lng}"
                            st.success(f"Login location logged: [View on Google Maps]({gmaps_link})")
                            # Brief pause for user to see the message
                            time.sleep(1.5)
                        st.session_state.authenticated = True
                        st.session_state.employee_name = employee_name
                        st.rerun()
                    else:
                        st.error("Invalid Password. Please try again.")
    else:
        # Show option boxes after login
        st.title("Select Mode")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Attendance", use_container_width=True, key="attendance_mode"):
                st.session_state.selected_mode = "Attendance"
                st.rerun()

        with col2:
            if st.button("Resources", use_container_width=True, key="resources_mode"):
                st.session_state.selected_mode = "Resources"
                st.rerun()

        if st.session_state.selected_mode:
            add_back_button()

            if st.session_state.selected_mode == "Attendance":
                attendance_page()
            elif st.session_state.selected_mode == "Resources":
                resources_page()

if __name__ == "__main__":
    main()
