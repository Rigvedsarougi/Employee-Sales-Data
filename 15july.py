import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import pytz

# Set page config
st.set_page_config(page_title="Admin Dashboard", layout="wide")

# Hide Streamlit style
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stActionButton > button[title="Open source on GitHub"] {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Constants
SHEET_NAMES = ["Sales", "Visits", "Attendance", "Demos", "Tickets", "TravelHotelRequests"]

# Establish Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

def get_ist_time():
    """Get current time in Indian Standard Time (IST)"""
    utc_now = datetime.now(pytz.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.astimezone(ist)

@st.cache_data(ttl=300)
def load_data(sheet_name):
    """Load data from Google Sheets with caching"""
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        df = df.dropna(how='all')
        
        # Convert date columns to datetime
        if sheet_name == "Sales":
            df['Invoice Date'] = pd.to_datetime(df['Invoice Date'], dayfirst=True, errors='coerce')
        elif sheet_name == "Visits":
            df['Visit Date'] = pd.to_datetime(df['Visit Date'], dayfirst=True, errors='coerce')
        elif sheet_name == "Attendance":
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df['Check-in Date Time'] = pd.to_datetime(df['Check-in Date Time'], dayfirst=True, errors='coerce')
        elif sheet_name == "Demos":
            df['Demo Date'] = pd.to_datetime(df['Demo Date'], dayfirst=True, errors='coerce')
            df['Check-in Date Time'] = pd.to_datetime(df['Check-in Date Time'], dayfirst=True, errors='coerce')
        elif sheet_name == "Tickets":
            df['Date Raised'] = pd.to_datetime(df['Date Raised'], dayfirst=True, errors='coerce')
            df['Date Resolved'] = pd.to_datetime(df['Date Resolved'], dayfirst=True, errors='coerce')
        elif sheet_name == "TravelHotelRequests":
            df['Date Requested'] = pd.to_datetime(df['Date Requested'], dayfirst=True, errors='coerce')
            df['Check In Date'] = pd.to_datetime(df['Check In Date'], dayfirst=True, errors='coerce')
            df['Check Out Date'] = pd.to_datetime(df['Check Out Date'], dayfirst=True, errors='coerce')
            df['Booking Date'] = pd.to_datetime(df['Booking Date'], dayfirst=True, errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"Error loading {sheet_name} data: {str(e)}")
        return pd.DataFrame()

def apply_filters(df, sheet_name, start_date, end_date, state_filter, city_filter, employee_filter):
    """Apply filters to the dataframe based on sheet type"""
    filtered_df = df.copy()
    
    # Date filter
    if sheet_name == "Sales":
        date_col = 'Invoice Date'
    elif sheet_name == "Visits":
        date_col = 'Visit Date'
    elif sheet_name == "Attendance":
        date_col = 'Date'
    elif sheet_name == "Demos":
        date_col = 'Demo Date'
    elif sheet_name == "Tickets":
        date_col = 'Date Raised'
    elif sheet_name == "TravelHotelRequests":
        date_col = 'Date Requested'
    
    if date_col in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df[date_col] >= pd.to_datetime(start_date)) & 
                                 (filtered_df[date_col] <= pd.to_datetime(end_date) + timedelta(days=1))]
    
    # State filter
    if state_filter and state_filter != "All":
        if sheet_name == "Sales":
            filtered_df = filtered_df[filtered_df['Outlet State'] == state_filter]
        elif sheet_name in ["Visits", "Demos"]:
            filtered_df = filtered_df[filtered_df['Outlet State'] == state_filter]
    
    # City filter
    if city_filter and city_filter != "All":
        if sheet_name == "Sales":
            filtered_df = filtered_df[filtered_df['Outlet City'] == city_filter]
        elif sheet_name in ["Visits", "Demos"]:
            filtered_df = filtered_df[filtered_df['Outlet City'] == city_filter]
    
    # Employee filter
    if employee_filter and employee_filter != "All":
        filtered_df = filtered_df[filtered_df['Employee Name'] == employee_filter]
    
    return filtered_df

def display_sales_dashboard(filtered_sales):
    """Display sales dashboard with metrics and visualizations"""
    st.subheader("Sales Overview")
    
    if filtered_sales.empty:
        st.warning("No sales data found for the selected filters")
        return
    
    # Calculate metrics
    total_sales = filtered_sales['Grand Total'].sum()
    total_invoices = filtered_sales['Invoice Number'].nunique()
    avg_sale_per_invoice = total_sales / total_invoices if total_invoices > 0 else 0
    total_products_sold = filtered_sales['Quantity'].sum()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"₹{total_sales:,.2f}")
    col2.metric("Total Invoices", total_invoices)
    col3.metric("Avg. Sale per Invoice", f"₹{avg_sale_per_invoice:,.2f}")
    col4.metric("Total Products Sold", total_products_sold)
    
    # Sales by date
    st.subheader("Sales Trend")
    sales_by_date = filtered_sales.groupby(filtered_sales['Invoice Date'].dt.date)['Grand Total'].sum().reset_index()
    fig = px.line(sales_by_date, x='Invoice Date', y='Grand Total', 
                  title="Daily Sales Trend", labels={'Grand Total': 'Total Sales (₹)'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Sales by employee
    st.subheader("Sales by Employee")
    sales_by_employee = filtered_sales.groupby('Employee Name')['Grand Total'].sum().reset_index().sort_values('Grand Total', ascending=False)
    fig = px.bar(sales_by_employee, x='Employee Name', y='Grand Total', 
                 title="Sales by Employee", labels={'Grand Total': 'Total Sales (₹)'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Sales by product
    st.subheader("Top Selling Products")
    sales_by_product = filtered_sales.groupby('Product Name')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(10)
    fig = px.bar(sales_by_product, x='Product Name', y='Quantity', 
                 title="Top Selling Products", labels={'Quantity': 'Units Sold'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Sales by outlet
    st.subheader("Top Outlets")
    sales_by_outlet = filtered_sales.groupby('Outlet Name')['Grand Total'].sum().reset_index().sort_values('Grand Total', ascending=False).head(10)
    fig = px.bar(sales_by_outlet, x='Outlet Name', y='Grand Total', 
                 title="Top Outlets by Sales", labels={'Grand Total': 'Total Sales (₹)'})
    st.plotly_chart(fig, use_container_width=True)

def display_visits_dashboard(filtered_visits):
    """Display visits dashboard with metrics and visualizations"""
    st.subheader("Visits Overview")
    
    if filtered_visits.empty:
        st.warning("No visit data found for the selected filters")
        return
    
    # Calculate metrics
    total_visits = len(filtered_visits)
    unique_outlets = filtered_visits['Outlet Name'].nunique()
    avg_visit_duration = filtered_visits['Visit Duration (minutes)'].mean()
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Visits", total_visits)
    col2.metric("Unique Outlets Visited", unique_outlets)
    col3.metric("Avg. Visit Duration (min)", f"{avg_visit_duration:.1f}")
    
    # Visits by date
    st.subheader("Visits Trend")
    visits_by_date = filtered_visits.groupby(filtered_visits['Visit Date'].dt.date).size().reset_index(name='Count')
    fig = px.line(visits_by_date, x='Visit Date', y='Count', 
                  title="Daily Visits Trend", labels={'Count': 'Number of Visits'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Visits by employee
    st.subheader("Visits by Employee")
    visits_by_employee = filtered_visits.groupby('Employee Name').size().reset_index(name='Count').sort_values('Count', ascending=False)
    fig = px.bar(visits_by_employee, x='Employee Name', y='Count', 
                 title="Visits by Employee", labels={'Count': 'Number of Visits'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Visits by purpose
    st.subheader("Visits by Purpose")
    visits_by_purpose = filtered_visits.groupby('Visit Purpose').size().reset_index(name='Count').sort_values('Count', ascending=False)
    fig = px.pie(visits_by_purpose, names='Visit Purpose', values='Count', 
                 title="Visit Purpose Distribution")
    st.plotly_chart(fig, use_container_width=True)

def display_attendance_dashboard(filtered_attendance):
    """Display attendance dashboard with metrics and visualizations"""
    st.subheader("Attendance Overview")
    
    if filtered_attendance.empty:
        st.warning("No attendance data found for the selected filters")
        return
    
    # Calculate metrics
    total_records = len(filtered_attendance)
    present_count = len(filtered_attendance[filtered_attendance['Status'].str.lower() == 'present'])
    half_day_count = len(filtered_attendance[filtered_attendance['Status'].str.lower() == 'half day'])
    leave_count = len(filtered_attendance[filtered_attendance['Status'].str.lower() == 'leave'])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", total_records)
    col2.metric("Present", present_count)
    col3.metric("Half Day", half_day_count)
    col4.metric("Leave", leave_count)
    
    # Attendance by date
    st.subheader("Daily Attendance")
    attendance_by_date = filtered_attendance.groupby(['Date', 'Status']).size().reset_index(name='Count')
    fig = px.bar(attendance_by_date, x='Date', y='Count', color='Status',
                 title="Daily Attendance by Status", barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    
    # Attendance by employee
    st.subheader("Attendance Summary by Employee")
    attendance_by_employee = filtered_attendance.groupby(['Employee Name', 'Status']).size().reset_index(name='Count')
    fig = px.bar(attendance_by_employee, x='Employee Name', y='Count', color='Status',
                 title="Employee Attendance Summary", barmode='stack')
    st.plotly_chart(fig, use_container_width=True)
    
    # Check-in time distribution
    st.subheader("Check-in Time Distribution")
    filtered_attendance['Check-in Time'] = pd.to_datetime(filtered_attendance['Check-in Time'], errors='coerce').dt.time
    filtered_attendance['Hour'] = filtered_attendance['Check-in Time'].apply(lambda x: x.hour if x else None)
    checkin_by_hour = filtered_attendance.groupby('Hour').size().reset_index(name='Count')
    fig = px.bar(checkin_by_hour, x='Hour', y='Count', 
                 title="Check-in Time Distribution by Hour")
    st.plotly_chart(fig, use_container_width=True)

def display_demos_dashboard(filtered_demos):
    """Display demos dashboard with metrics and visualizations"""
    st.subheader("Demos Overview")
    
    if filtered_demos.empty:
        st.warning("No demo data found for the selected filters")
        return
    
    # Calculate metrics
    total_demos = len(filtered_demos)
    unique_outlets = filtered_demos['Outlet Name'].nunique()
    avg_demo_duration = filtered_demos['Duration (minutes)'].mean()
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Demos", total_demos)
    col2.metric("Unique Outlets", unique_outlets)
    col3.metric("Avg. Duration (min)", f"{avg_demo_duration:.1f}")
    
    # Demos by date
    st.subheader("Demos Trend")
    demos_by_date = filtered_demos.groupby(filtered_demos['Demo Date'].dt.date).size().reset_index(name='Count')
    fig = px.line(demos_by_date, x='Demo Date', y='Count', 
                  title="Daily Demos Trend", labels={'Count': 'Number of Demos'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Demos by employee
    st.subheader("Demos by Employee")
    demos_by_employee = filtered_demos.groupby('Employee Name').size().reset_index(name='Count').sort_values('Count', ascending=False)
    fig = px.bar(demos_by_employee, x='Employee Name', y='Count', 
                 title="Demos Conducted by Employee", labels={'Count': 'Number of Demos'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Outlet reviews
    st.subheader("Outlet Reviews")
    outlet_reviews = filtered_demos.groupby('Outlet Review').size().reset_index(name='Count')
    fig = px.pie(outlet_reviews, names='Outlet Review', values='Count', 
                 title="Outlet Review Distribution")
    st.plotly_chart(fig, use_container_width=True)

def display_tickets_dashboard(filtered_tickets):
    """Display support tickets dashboard with metrics and visualizations"""
    st.subheader("Support Tickets Overview")
    
    if filtered_tickets.empty:
        st.warning("No ticket data found for the selected filters")
        return
    
    # Calculate metrics
    total_tickets = len(filtered_tickets)
    open_tickets = len(filtered_tickets[filtered_tickets['Status'].str.lower() == 'open'])
    resolved_tickets = len(filtered_tickets[filtered_tickets['Status'].str.lower() == 'resolved'])
    avg_resolution_time = None
    
    # Calculate average resolution time if there are resolved tickets
    if resolved_tickets > 0:
        resolved_df = filtered_tickets[filtered_tickets['Status'].str.lower() == 'resolved']
        resolved_df = resolved_df.dropna(subset=['Date Raised', 'Date Resolved'])
        resolved_df['Resolution Time'] = (resolved_df['Date Resolved'] - resolved_df['Date Raised']).dt.days
        avg_resolution_time = resolved_df['Resolution Time'].mean()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Open Tickets", open_tickets)
    col3.metric("Resolved Tickets", resolved_tickets)
    if avg_resolution_time is not None:
        col4.metric("Avg. Resolution (days)", f"{avg_resolution_time:.1f}")
    else:
        col4.metric("Avg. Resolution (days)", "N/A")
    
    # Tickets by date
    st.subheader("Tickets Trend")
    tickets_by_date = filtered_tickets.groupby(filtered_tickets['Date Raised'].dt.date).size().reset_index(name='Count')
    fig = px.line(tickets_by_date, x='Date Raised', y='Count', 
                  title="Daily Tickets Trend", labels={'Count': 'Number of Tickets'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Tickets by category
    st.subheader("Tickets by Category")
    tickets_by_category = filtered_tickets.groupby('Category').size().reset_index(name='Count').sort_values('Count', ascending=False)
    fig = px.bar(tickets_by_category, x='Category', y='Count', 
                 title="Tickets by Category", labels={'Count': 'Number of Tickets'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Tickets by priority
    st.subheader("Tickets by Priority")
    tickets_by_priority = filtered_tickets.groupby('Priority').size().reset_index(name='Count')
    fig = px.pie(tickets_by_priority, names='Priority', values='Count', 
                 title="Ticket Priority Distribution")
    st.plotly_chart(fig, use_container_width=True)

def display_travel_hotel_dashboard(filtered_requests):
    """Display travel/hotel requests dashboard with metrics and visualizations"""
    st.subheader("Travel & Hotel Requests Overview")
    
    if filtered_requests.empty:
        st.warning("No travel/hotel request data found for the selected filters")
        return
    
    # Calculate metrics
    total_requests = len(filtered_requests)
    pending_requests = len(filtered_requests[filtered_requests['Status'].str.lower() == 'pending'])
    approved_requests = len(filtered_requests[filtered_requests['Status'].str.lower() == 'approved'])
    rejected_requests = len(filtered_requests[filtered_requests['Status'].str.lower() == 'rejected'])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Requests", total_requests)
    col2.metric("Pending", pending_requests)
    col3.metric("Approved", approved_requests)
    col4.metric("Rejected", rejected_requests)
    
    # Requests by date
    st.subheader("Requests Trend")
    requests_by_date = filtered_requests.groupby(filtered_requests['Date Requested'].dt.date).size().reset_index(name='Count')
    fig = px.line(requests_by_date, x='Date Requested', y='Count', 
                  title="Daily Requests Trend", labels={'Count': 'Number of Requests'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Requests by type
    st.subheader("Requests by Type")
    requests_by_type = filtered_requests.groupby('Request Type').size().reset_index(name='Count')
    fig = px.pie(requests_by_type, names='Request Type', values='Count', 
                 title="Request Type Distribution")
    st.plotly_chart(fig, use_container_width=True)
    
    # Requests by status
    st.subheader("Requests by Status")
    requests_by_status = filtered_requests.groupby('Status').size().reset_index(name='Count')
    fig = px.bar(requests_by_status, x='Status', y='Count', 
                 title="Request Status Distribution")
    st.plotly_chart(fig, use_container_width=True)

def display_employee_dashboard(employee_name, sales_data, visits_data, attendance_data, demos_data, tickets_data, travel_data):
    """Display detailed dashboard for a specific employee"""
    st.title(f"Employee Dashboard: {employee_name}")
    
    # Filter data for the selected employee
    emp_sales = sales_data[sales_data['Employee Name'] == employee_name]
    emp_visits = visits_data[visits_data['Employee Name'] == employee_name]
    emp_attendance = attendance_data[attendance_data['Employee Name'] == employee_name]
    emp_demos = demos_data[demos_data['Employee Name'] == employee_name]
    emp_tickets = tickets_data[tickets_data['Raised By (Employee Name)'] == employee_name]
    emp_travel = travel_data[travel_data['Employee Name'] == employee_name]
    
    # Display summary metrics
    st.subheader("Performance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"₹{emp_sales['Grand Total'].sum():,.2f}" if not emp_sales.empty else "₹0")
    col2.metric("Total Visits", len(emp_visits))
    col3.metric("Present Days", len(emp_attendance[emp_attendance['Status'].str.lower() == 'present']))
    col4.metric("Demos Conducted", len(emp_demos))
    
    # Sales performance
    st.subheader("Sales Performance")
    if not emp_sales.empty:
        # Sales trend
        sales_trend = emp_sales.groupby(emp_sales['Invoice Date'].dt.date)['Grand Total'].sum().reset_index()
        fig = px.line(sales_trend, x='Invoice Date', y='Grand Total', 
                      title="Sales Trend", labels={'Grand Total': 'Total Sales (₹)'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Top products sold
        top_products = emp_sales.groupby('Product Name')['Quantity'].sum().reset_index().sort_values('Quantity', ascending=False).head(5)
        fig = px.bar(top_products, x='Product Name', y='Quantity', 
                     title="Top Products Sold", labels={'Quantity': 'Units Sold'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sales data found for this employee")
    
    # Visit performance
    st.subheader("Visit Performance")
    if not emp_visits.empty:
        # Visit trend
        visit_trend = emp_visits.groupby(emp_visits['Visit Date'].dt.date).size().reset_index(name='Count')
        fig = px.line(visit_trend, x='Visit Date', y='Count', 
                      title="Visit Trend", labels={'Count': 'Number of Visits'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Visit purpose distribution
        visit_purpose = emp_visits.groupby('Visit Purpose').size().reset_index(name='Count')
        fig = px.pie(visit_purpose, names='Visit Purpose', values='Count', 
                     title="Visit Purpose Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No visit data found for this employee")
    
    # Attendance record
    st.subheader("Attendance Record")
    if not emp_attendance.empty:
        # Attendance status
        attendance_status = emp_attendance.groupby('Status').size().reset_index(name='Count')
        fig = px.pie(attendance_status, names='Status', values='Count', 
                     title="Attendance Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Check-in time distribution
        emp_attendance['Check-in Time'] = pd.to_datetime(emp_attendance['Check-in Time'], errors='coerce').dt.time
        emp_attendance['Hour'] = emp_attendance['Check-in Time'].apply(lambda x: x.hour if x else None)
        checkin_by_hour = emp_attendance.groupby('Hour').size().reset_index(name='Count')
        fig = px.bar(checkin_by_hour, x='Hour', y='Count', 
                     title="Check-in Time Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No attendance data found for this employee")
    
    # Demo performance
    st.subheader("Demo Performance")
    if not emp_demos.empty:
        # Demo trend
        demo_trend = emp_demos.groupby(emp_demos['Demo Date'].dt.date).size().reset_index(name='Count')
        fig = px.line(demo_trend, x='Demo Date', y='Count', 
                      title="Demo Trend", labels={'Count': 'Number of Demos'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Outlet reviews
        outlet_reviews = emp_demos.groupby('Outlet Review').size().reset_index(name='Count')
        fig = px.pie(outlet_reviews, names='Outlet Review', values='Count', 
                     title="Outlet Review Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No demo data found for this employee")

def main():
    st.title("Admin Dashboard")
    
    # Load all data
    sales_data = load_data("Sales")
    visits_data = load_data("Visits")
    attendance_data = load_data("Attendance")
    demos_data = load_data("Demos")
    tickets_data = load_data("Tickets")
    travel_data = load_data("TravelHotelRequests")
    
    # Get unique values for filters
    all_employees = sorted(list(set(
        list(sales_data['Employee Name'].unique()) + 
        list(visits_data['Employee Name'].unique()) + 
        list(attendance_data['Employee Name'].unique()) + 
        list(demos_data['Employee Name'].unique()) + 
        list(tickets_data['Raised By (Employee Name)'].unique()) + 
        list(travel_data['Employee Name'].unique())
    )))
    
    all_states = sorted(list(set(
        list(sales_data['Outlet State'].unique()) + 
        list(visits_data['Outlet State'].unique()) + 
        list(demos_data['Outlet State'].unique())
    )))
    
    all_cities = sorted(list(set(
        list(sales_data['Outlet City'].unique()) + 
        list(visits_data['Outlet City'].unique()) + 
        list(demos_data['Outlet City'].unique())
    )))
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    min_date = min(
        sales_data['Invoice Date'].min() if not sales_data.empty else get_ist_time().date(),
        visits_data['Visit Date'].min() if not visits_data.empty else get_ist_time().date(),
        attendance_data['Date'].min() if not attendance_data.empty else get_ist_time().date(),
        demos_data['Demo Date'].min() if not demos_data.empty else get_ist_time().date(),
        tickets_data['Date Raised'].min() if not tickets_data.empty else get_ist_time().date(),
        travel_data['Date Requested'].min() if not travel_data.empty else get_ist_time().date()
    )
    
    max_date = max(
        sales_data['Invoice Date'].max() if not sales_data.empty else get_ist_time().date(),
        visits_data['Visit Date'].max() if not visits_data.empty else get_ist_time().date(),
        attendance_data['Date'].max() if not attendance_data.empty else get_ist_time().date(),
        demos_data['Demo Date'].max() if not demos_data.empty else get_ist_time().date(),
        tickets_data['Date Raised'].max() if not tickets_data.empty else get_ist_time().date(),
        travel_data['Date Requested'].max() if not travel_data.empty else get_ist_time().date()
    )
    
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # State filter
    state_filter = st.sidebar.selectbox("State", ["All"] + all_states)
    
    # City filter (dynamic based on state selection)
    if state_filter != "All":
        cities_in_state = sorted(list(set(
            list(sales_data[sales_data['Outlet State'] == state_filter]['Outlet City'].unique()) + 
            list(visits_data[visits_data['Outlet State'] == state_filter]['Outlet City'].unique()) + 
            list(demos_data[demos_data['Outlet State'] == state_filter]['Outlet City'].unique())
        ))
    else:
        cities_in_state = all_cities
    
    city_filter = st.sidebar.selectbox("City", ["All"] + cities_in_state)
    
    # Employee filter
    employee_filter = st.sidebar.selectbox("Employee", ["All"] + all_employees)
    
    # Dashboard selection
    dashboard_type = st.sidebar.radio("Dashboard Type", ["Overall", "Employee"])
    
    if dashboard_type == "Overall":
        # Overall dashboard tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Sales", "Visits", "Attendance", "Demos", "Support Tickets", "Travel/Hotel"])
        
        with tab1:
            filtered_sales = apply_filters(sales_data, "Sales", start_date, end_date, state_filter, city_filter, employee_filter)
            display_sales_dashboard(filtered_sales)
            
            # Raw data
            with st.expander("View Raw Sales Data"):
                st.dataframe(filtered_sales)
        
        with tab2:
            filtered_visits = apply_filters(visits_data, "Visits", start_date, end_date, state_filter, city_filter, employee_filter)
            display_visits_dashboard(filtered_visits)
            
            # Raw data
            with st.expander("View Raw Visits Data"):
                st.dataframe(filtered_visits)
        
        with tab3:
            filtered_attendance = apply_filters(attendance_data, "Attendance", start_date, end_date, state_filter, city_filter, employee_filter)
            display_attendance_dashboard(filtered_attendance)
            
            # Raw data
            with st.expander("View Raw Attendance Data"):
                st.dataframe(filtered_attendance)
        
        with tab4:
            filtered_demos = apply_filters(demos_data, "Demos", start_date, end_date, state_filter, city_filter, employee_filter)
            display_demos_dashboard(filtered_demos)
            
            # Raw data
            with st.expander("View Raw Demo Data"):
                st.dataframe(filtered_demos)
        
        with tab5:
            filtered_tickets = apply_filters(tickets_data, "Tickets", start_date, end_date, state_filter, city_filter, employee_filter)
            display_tickets_dashboard(filtered_tickets)
            
            # Raw data
            with st.expander("View Raw Ticket Data"):
                st.dataframe(filtered_tickets)
        
        with tab6:
            filtered_travel = apply_filters(travel_data, "TravelHotelRequests", start_date, end_date, state_filter, city_filter, employee_filter)
            display_travel_hotel_dashboard(filtered_travel)
            
            # Raw data
            with st.expander("View Raw Travel/Hotel Data"):
                st.dataframe(filtered_travel)
    
    else:
        # Employee dashboard
        if employee_filter == "All":
            st.warning("Please select an employee from the filters")
        else:
            display_employee_dashboard(
                employee_filter,
                apply_filters(sales_data, "Sales", start_date, end_date, state_filter, city_filter, employee_filter),
                apply_filters(visits_data, "Visits", start_date, end_date, state_filter, city_filter, employee_filter),
                apply_filters(attendance_data, "Attendance", start_date, end_date, state_filter, city_filter, employee_filter),
                apply_filters(demos_data, "Demos", start_date, end_date, state_filter, city_filter, employee_filter),
                apply_filters(tickets_data, "Tickets", start_date, end_date, state_filter, city_filter, employee_filter),
                apply_filters(travel_data, "TravelHotelRequests", start_date, end_date, state_filter, city_filter, employee_filter)
            )

if __name__ == "__main__":
    main()
