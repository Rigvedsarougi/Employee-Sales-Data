import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pytz

# Initialize Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Set page config
st.set_page_config(page_title="Admin Dashboard", layout="wide")

# Authentication
def authenticate_admin(username, password):
    # Replace with your actual admin credentials
    ADMIN_CREDENTIALS = {
        "admin": "admin123",
        "manager": "manager123"
    }
    return username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password

# Login page
def show_login():
    st.title("Admin Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if authenticate_admin(username, password):
                st.session_state.authenticated = True
                st.session_state.admin_username = username
                st.rerun()
            else:
                st.error("Invalid credentials")

# Helper functions
def get_ist_time():
    """Get current time in Indian Standard Time (IST)"""
    utc_now = datetime.now(pytz.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.astimezone(ist)

def load_data(worksheet_name, date_column=None):
    """Load data from Google Sheets with caching"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl=5)
        df = df.dropna(how='all')
        
        if date_column and date_column in df.columns:
            try:
                df[date_column] = pd.to_datetime(df[date_column], dayfirst=True, errors='coerce')
            except:
                df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading {worksheet_name} data: {str(e)}")
        return pd.DataFrame()

def filter_data(df, filters):
    """Apply filters to dataframe"""
    filtered = df.copy()
    
    for column, value in filters.items():
        if value and column in filtered.columns:
            if isinstance(value, list):
                filtered = filtered[filtered[column].isin(value)]
            else:
                filtered = filtered[filtered[column].astype(str).str.contains(str(value), case=False)]
    
    return filtered

# Dashboard pages
def dashboard_page():
    st.title("📊 Admin Dashboard")
    st.markdown("---")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", 
                                 value=get_ist_time().date() - timedelta(days=30),
                                 key="dashboard_start_date")
    with col2:
        end_date = st.date_input("End Date", 
                               value=get_ist_time().date(),
                               key="dashboard_end_date")
    
    # Convert to string for filtering
    start_date_str = start_date.strftime("%d-%m-%Y")
    end_date_str = end_date.strftime("%d-%m-%Y")
    
    # Load all data
    sales_data = load_data("Sales", "Invoice Date")
    visits_data = load_data("Visits", "Visit Date")
    attendance_data = load_data("Attendance", "Date")
    demo_data = load_data("Demos", "Demo Date")
    
    # Filter data by date range
    if not sales_data.empty:
        sales_data = sales_data[(sales_data['Invoice Date'].dt.date >= start_date) & 
                              (sales_data['Invoice Date'].dt.date <= end_date)]
    
    if not visits_data.empty:
        visits_data = visits_data[(visits_data['Visit Date'].dt.date >= start_date) & 
                                (visits_data['Visit Date'].dt.date <= end_date)]
    
    if not attendance_data.empty:
        attendance_data = attendance_data[(attendance_data['Date'].dt.date >= start_date) & 
                                        (attendance_data['Date'].dt.date <= end_date)]
    
    if not demo_data.empty:
        demo_data = demo_data[(demo_data['Demo Date'].dt.date >= start_date) & 
                            (demo_data['Demo Date'].dt.date <= end_date)]
    
    # Overall Metrics
    st.subheader("📈 Overall Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_sales = sales_data['Grand Total'].sum() if not sales_data.empty else 0
        st.metric("Total Sales", f"₹{total_sales:,.2f}")
    with col2:
        total_visits = len(visits_data) if not visits_data.empty else 0
        st.metric("Total Visits", total_visits)
    with col3:
        total_demos = len(demo_data) if not demo_data.empty else 0
        st.metric("Total Demos", total_demos)
    with col4:
        attendance_present = len(attendance_data[attendance_data['Status'] == 'Present']) if not attendance_data.empty else 0
        st.metric("Present Employees", attendance_present)
    
    # Sales Trends
    st.subheader("💰 Sales Trends")
    if not sales_data.empty:
        sales_by_date = sales_data.groupby(sales_data['Invoice Date'].dt.date)['Grand Total'].sum().reset_index()
        fig = px.line(sales_by_date, x="Invoice Date", y="Grand Total", 
                     title="Daily Sales Trend", labels={"Grand Total": "Amount (₹)"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sales data available for the selected period")
    
    # Employee Activity
    st.subheader("👥 Employee Activity")
    
    if not sales_data.empty and not visits_data.empty:
        col1, col2 = st.columns(2)
        with col1:
            sales_by_employee = sales_data.groupby('Employee Name')['Grand Total'].sum().nlargest(10).reset_index()
            fig = px.bar(sales_by_employee, x='Employee Name', y='Grand Total',
                         title="Top 10 Employees by Sales", labels={"Grand Total": "Amount (₹)"})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            visits_by_employee = visits_data['Employee Name'].value_counts().nlargest(10).reset_index()
            fig = px.bar(visits_by_employee, x='Employee Name', y='count',
                         title="Top 10 Employees by Visits", labels={"count": "Number of Visits"})
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Insufficient data to display employee activity metrics")

def sales_analytics_page():
    st.title("💰 Sales Analytics")
    st.markdown("---")
    
    # Filters
    with st.expander("🔍 Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=get_ist_time().date() - timedelta(days=30),
                                     key="sales_start_date")
            states = st.multiselect("Filter by State", 
                                  options=sorted(conn.read(worksheet="Sales")['Outlet State'].unique()) 
        with col2:
            end_date = st.date_input("End Date", 
                                   value=get_ist_time().date(),
                                   key="sales_end_date")
            cities = st.multiselect("Filter by City", 
                                  options=sorted(conn.read(worksheet="Sales")['Outlet City'].unique())
    
    # Load and filter data
    sales_data = load_data("Sales", "Invoice Date")
    if not sales_data.empty:
        sales_data = sales_data[(sales_data['Invoice Date'].dt.date >= start_date) & 
                               (sales_data['Invoice Date'].dt.date <= end_date)]
        
        if states:
            sales_data = sales_data[sales_data['Outlet State'].isin(states)]
        if cities:
            sales_data = sales_data[sales_data['Outlet City'].isin(cities)]
    
    # Display metrics
    if not sales_data.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            total_sales = sales_data['Grand Total'].sum()
            st.metric("Total Sales", f"₹{total_sales:,.2f}")
        with col2:
            avg_sale = sales_data['Grand Total'].mean()
            st.metric("Average Sale", f"₹{avg_sale:,.2f}")
        with col3:
            unique_outlets = sales_data['Outlet Name'].nunique()
            st.metric("Unique Outlets", unique_outlets)
        
        # Sales by State
        st.subheader("Sales by State")
        sales_by_state = sales_data.groupby('Outlet State')['Grand Total'].sum().reset_index()
        fig = px.bar(sales_by_state, x='Outlet State', y='Grand Total',
                    title="Sales by State", labels={"Grand Total": "Amount (₹)"})
        st.plotly_chart(fig, use_container_width=True)
        
        # Top Products
        st.subheader("Top Selling Products")
        top_products = sales_data.groupby('Product Name')['Quantity'].sum().nlargest(10).reset_index()
        fig = px.bar(top_products, x='Product Name', y='Quantity',
                    title="Top 10 Products by Quantity Sold")
        st.plotly_chart(fig, use_container_width=True)
        
        # Raw data
        st.subheader("Sales Data")
        st.dataframe(sales_data, use_container_width=True)
    else:
        st.warning("No sales data available for the selected filters")

def visit_analytics_page():
    st.title("📍 Visit Analytics")
    st.markdown("---")
    
    # Filters
    with st.expander("🔍 Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=get_ist_time().date() - timedelta(days=30),
                                     key="visit_start_date")
            employee_filter = st.multiselect("Filter by Employee", 
                                           options=sorted(conn.read(worksheet="Visits")['Employee Name'].unique())
        with col2:
            end_date = st.date_input("End Date", 
                                   value=get_ist_time().date(),
                                   key="visit_end_date")
            purpose_filter = st.multiselect("Filter by Purpose", 
                                          options=sorted(conn.read(worksheet="Visits")['Visit Purpose'].unique())
    
    # Load and filter data
    visits_data = load_data("Visits", "Visit Date")
    if not visits_data.empty:
        visits_data = visits_data[(visits_data['Visit Date'].dt.date >= start_date) & 
                                (visits_data['Visit Date'].dt.date <= end_date)]
        
        if employee_filter:
            visits_data = visits_data[visits_data['Employee Name'].isin(employee_filter)]
        if purpose_filter:
            visits_data = visits_data[visits_data['Visit Purpose'].isin(purpose_filter)]
    
    # Display metrics
    if not visits_data.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            total_visits = len(visits_data)
            st.metric("Total Visits", total_visits)
        with col2:
            avg_duration = visits_data['Visit Duration (minutes)'].mean()
            st.metric("Average Duration", f"{avg_duration:.1f} minutes")
        with col3:
            unique_outlets = visits_data['Outlet Name'].nunique()
            st.metric("Unique Outlets", unique_outlets)
        
        # Visits by Employee
        st.subheader("Visits by Employee")
        visits_by_employee = visits_data['Employee Name'].value_counts().reset_index()
        fig = px.bar(visits_by_employee, x='Employee Name', y='count',
                    title="Visits by Employee", labels={"count": "Number of Visits"})
        st.plotly_chart(fig, use_container_width=True)
        
        # Visit Purpose Distribution
        st.subheader("Visit Purpose Distribution")
        purpose_dist = visits_data['Visit Purpose'].value_counts().reset_index()
        fig = px.pie(purpose_dist, values='count', names='Visit Purpose',
                    title="Visit Purpose Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Raw data
        st.subheader("Visit Data")
        st.dataframe(visits_data, use_container_width=True)
    else:
        st.warning("No visit data available for the selected filters")

def demo_analytics_page():
    st.title("🎤 Demo Analytics")
    st.markdown("---")
    
    # Filters
    with st.expander("🔍 Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=get_ist_time().date() - timedelta(days=30),
                                     key="demo_start_date")
            employee_filter = st.multiselect("Filter by Employee", 
                                           options=sorted(conn.read(worksheet="Demos")['Employee Name'].unique())
        with col2:
            end_date = st.date_input("End Date", 
                                   value=get_ist_time().date(),
                                   key="demo_end_date")
            outlet_filter = st.multiselect("Filter by Outlet", 
                                         options=sorted(conn.read(worksheet="Demos")['Outlet Name'].unique())
    
    # Load and filter data
    demo_data = load_data("Demos", "Demo Date")
    if not demo_data.empty:
        demo_data = demo_data[(demo_data['Demo Date'].dt.date >= start_date) & 
                            (demo_data['Demo Date'].dt.date <= end_date)]
        
        if employee_filter:
            demo_data = demo_data[demo_data['Employee Name'].isin(employee_filter)]
        if outlet_filter:
            demo_data = demo_data[demo_data['Outlet Name'].isin(outlet_filter)]
    
    # Display metrics
    if not demo_data.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            total_demos = len(demo_data)
            st.metric("Total Demos", total_demos)
        with col2:
            avg_duration = demo_data['Duration (minutes)'].mean()
            st.metric("Average Duration", f"{avg_duration:.1f} minutes")
        with col3:
            unique_outlets = demo_data['Outlet Name'].nunique()
            st.metric("Unique Outlets", unique_outlets)
        
        # Demos by Employee
        st.subheader("Demos by Employee")
        demos_by_employee = demo_data['Employee Name'].value_counts().reset_index()
        fig = px.bar(demos_by_employee, x='Employee Name', y='count',
                    title="Demos by Employee", labels={"count": "Number of Demos"})
        st.plotly_chart(fig, use_container_width=True)
        
        # Outlet Review Distribution
        st.subheader("Outlet Review Distribution")
        review_dist = demo_data['Outlet Review'].value_counts().reset_index()
        fig = px.pie(review_dist, values='count', names='Outlet Review',
                    title="Outlet Review Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Raw data
        st.subheader("Demo Data")
        st.dataframe(demo_data, use_container_width=True)
    else:
        st.warning("No demo data available for the selected filters")

def attendance_analytics_page():
    st.title("⏱ Attendance Analytics")
    st.markdown("---")
    
    # Filters
    with st.expander("🔍 Filters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=get_ist_time().date() - timedelta(days=30),
                                     key="attendance_start_date")
            employee_filter = st.multiselect("Filter by Employee", 
                                           options=sorted(conn.read(worksheet="Attendance")['Employee Name'].unique())
        with col2:
            end_date = st.date_input("End Date", 
                                   value=get_ist_time().date(),
                                   key="attendance_end_date")
            status_filter = st.multiselect("Filter by Status", 
                                          options=sorted(conn.read(worksheet="Attendance")['Status'].unique())
    
    # Load and filter data
    attendance_data = load_data("Attendance", "Date")
    if not attendance_data.empty:
        attendance_data = attendance_data[(attendance_data['Date'].dt.date >= start_date) & 
                                        (attendance_data['Date'].dt.date <= end_date)]
        
        if employee_filter:
            attendance_data = attendance_data[attendance_data['Employee Name'].isin(employee_filter)]
        if status_filter:
            attendance_data = attendance_data[attendance_data['Status'].isin(status_filter)]
    
    # Display metrics
    if not attendance_data.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            total_records = len(attendance_data)
            st.metric("Total Records", total_records)
        with col2:
            present_count = len(attendance_data[attendance_data['Status'] == 'Present'])
            st.metric("Present Count", present_count)
        with col3:
            leave_count = len(attendance_data[attendance_data['Status'] == 'Leave'])
            st.metric("Leave Count", leave_count)
        
        # Attendance by Day
        st.subheader("Daily Attendance")
        daily_attendance = attendance_data.groupby('Date')['Status'].value_counts().unstack().fillna(0)
        fig = px.bar(daily_attendance, barmode='group',
                    title="Daily Attendance Breakdown")
        st.plotly_chart(fig, use_container_width=True)
        
        # Status Distribution
        st.subheader("Attendance Status Distribution")
        status_dist = attendance_data['Status'].value_counts().reset_index()
        fig = px.pie(status_dist, values='count', names='Status',
                    title="Attendance Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
        # Raw data
        st.subheader("Attendance Data")
        st.dataframe(attendance_data, use_container_width=True)
    else:
        st.warning("No attendance data available for the selected filters")

def employee_dashboard_page():
    st.title("👤 Employee Dashboard")
    st.markdown("---")
    
    # Employee selection
    employee_list = sorted(conn.read(worksheet="Attendance")['Employee Name'].unique())
    selected_employee = st.selectbox("Select Employee", employee_list)
    
    if not selected_employee:
        st.warning("Please select an employee")
        return
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", 
                                 value=get_ist_time().date() - timedelta(days=30),
                                 key="emp_start_date")
    with col2:
        end_date = st.date_input("End Date", 
                               value=get_ist_time().date(),
                               key="emp_end_date")
    
    # Load all data for selected employee
    sales_data = load_data("Sales", "Invoice Date")
    visits_data = load_data("Visits", "Visit Date")
    attendance_data = load_data("Attendance", "Date")
    demo_data = load_data("Demos", "Demo Date")
    
    # Filter data by employee and date range
    employee_code = conn.read(worksheet="Attendance")[
        conn.read(worksheet="Attendance")['Employee Name'] == selected_employee
    ]['Employee Code'].values[0]
    
    if not sales_data.empty:
        emp_sales = sales_data[
            (sales_data['Employee Code'] == employee_code) & 
            (sales_data['Invoice Date'].dt.date >= start_date) & 
            (sales_data['Invoice Date'].dt.date <= end_date)
        ]
    else:
        emp_sales = pd.DataFrame()
    
    if not visits_data.empty:
        emp_visits = visits_data[
            (visits_data['Employee Name'] == selected_employee) & 
            (visits_data['Visit Date'].dt.date >= start_date) & 
            (visits_data['Visit Date'].dt.date <= end_date)
        ]
    else:
        emp_visits = pd.DataFrame()
    
    if not attendance_data.empty:
        emp_attendance = attendance_data[
            (attendance_data['Employee Name'] == selected_employee) & 
            (attendance_data['Date'].dt.date >= start_date) & 
            (attendance_data['Date'].dt.date <= end_date)
        ]
    else:
        emp_attendance = pd.DataFrame()
    
    if not demo_data.empty:
        emp_demos = demo_data[
            (demo_data['Employee Name'] == selected_employee) & 
            (demo_data['Demo Date'].dt.date >= start_date) & 
            (demo_data['Demo Date'].dt.date <= end_date)
        ]
    else:
        emp_demos = pd.DataFrame()
    
    # Employee Summary
    st.subheader(f"📊 {selected_employee} Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_sales = emp_sales['Grand Total'].sum() if not emp_sales.empty else 0
        st.metric("Total Sales", f"₹{total_sales:,.2f}")
    with col2:
        total_visits = len(emp_visits) if not emp_visits.empty else 0
        st.metric("Total Visits", total_visits)
    with col3:
        total_demos = len(emp_demos) if not emp_demos.empty else 0
        st.metric("Total Demos", total_demos)
    with col4:
        present_days = len(emp_attendance[emp_attendance['Status'] == 'Present']) if not emp_attendance.empty else 0
        st.metric("Present Days", present_days)
    
    # Tabs for different data types
    tab1, tab2, tab3, tab4 = st.tabs(["Sales", "Visits", "Demos", "Attendance"])
    
    with tab1:
        if not emp_sales.empty:
            # Sales Trend
            st.subheader("Sales Trend")
            sales_by_date = emp_sales.groupby(emp_sales['Invoice Date'].dt.date)['Grand Total'].sum().reset_index()
            fig = px.line(sales_by_date, x="Invoice Date", y="Grand Total", 
                         title="Daily Sales Trend", labels={"Grand Total": "Amount (₹)"})
            st.plotly_chart(fig, use_container_width=True)
            
            # Top Products
            st.subheader("Top Products")
            top_products = emp_sales.groupby('Product Name')['Quantity'].sum().nlargest(5).reset_index()
            fig = px.bar(top_products, x='Product Name', y='Quantity',
                        title="Top 5 Products Sold")
            st.plotly_chart(fig, use_container_width=True)
            
            # Raw data
            st.subheader("Sales Data")
            st.dataframe(emp_sales, use_container_width=True)
        else:
            st.warning("No sales data available for this employee")
    
    with tab2:
        if not emp_visits.empty:
            # Visits by Purpose
            st.subheader("Visits by Purpose")
            visits_by_purpose = emp_visits['Visit Purpose'].value_counts().reset_index()
            fig = px.pie(visits_by_purpose, values='count', names='Visit Purpose',
                        title="Visit Purpose Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Visit Duration
            st.subheader("Visit Duration")
            fig = px.histogram(emp_visits, x='Visit Duration (minutes)',
                             title="Visit Duration Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Raw data
            st.subheader("Visit Data")
            st.dataframe(emp_visits, use_container_width=True)
        else:
            st.warning("No visit data available for this employee")
    
    with tab3:
        if not emp_demos.empty:
            # Demos by Outlet
            st.subheader("Demos by Outlet")
            demos_by_outlet = emp_demos['Outlet Name'].value_counts().nlargest(5).reset_index()
            fig = px.bar(demos_by_outlet, x='Outlet Name', y='count',
                        title="Top 5 Outlets for Demos")
            st.plotly_chart(fig, use_container_width=True)
            
            # Outlet Reviews
            st.subheader("Outlet Reviews")
            review_dist = emp_demos['Outlet Review'].value_counts().reset_index()
            fig = px.pie(review_dist, values='count', names='Outlet Review',
                        title="Outlet Review Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Raw data
            st.subheader("Demo Data")
            st.dataframe(emp_demos, use_container_width=True)
        else:
            st.warning("No demo data available for this employee")
    
    with tab4:
        if not emp_attendance.empty:
            # Attendance Status
            st.subheader("Attendance Status")
            status_dist = emp_attendance['Status'].value_counts().reset_index()
            fig = px.pie(status_dist, values='count', names='Status',
                        title="Attendance Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Check-in Times
            st.subheader("Check-in Times")
            emp_attendance['Check-in Hour'] = pd.to_datetime(emp_attendance['Check-in Time']).dt.hour
            checkin_dist = emp_attendance['Check-in Hour'].value_counts().sort_index().reset_index()
            fig = px.bar(checkin_dist, x='Check-in Hour', y='count',
                        title="Check-in Time Distribution")
            st.plotly_chart(fig, use_container_width=True)
            
            # Raw data
            st.subheader("Attendance Data")
            st.dataframe(emp_attendance, use_container_width=True)
        else:
            st.warning("No attendance data available for this employee")

# Main app
def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        show_login()
    else:
        st.sidebar.title("Navigation")
        app_mode = st.sidebar.radio("Go to", 
                                   ["Dashboard", "Sales Analytics", "Visit Analytics", 
                                    "Demo Analytics", "Attendance Analytics", "Employee Dashboard"])
        
        st.sidebar.markdown("---")
        st.sidebar.write(f"Logged in as: **{st.session_state.admin_username}**")
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.admin_username = None
            st.rerun()
        
        if app_mode == "Dashboard":
            dashboard_page()
        elif app_mode == "Sales Analytics":
            sales_analytics_page()
        elif app_mode == "Visit Analytics":
            visit_analytics_page()
        elif app_mode == "Demo Analytics":
            demo_analytics_page()
        elif app_mode == "Attendance Analytics":
            attendance_analytics_page()
        elif app_mode == "Employee Dashboard":
            employee_dashboard_page()

if __name__ == "__main__":
    main()
