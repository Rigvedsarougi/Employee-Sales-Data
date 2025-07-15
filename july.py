import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import pytz

# Set page config
st.set_page_config(
    page_title="Business Operations Dashboard",
    layout="wide",
    page_icon="📊"
)

# Initialize connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Helper functions
def get_ist_time():
    utc_now = datetime.now(pytz.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.astimezone(ist)

def load_data(worksheet_name):
    try:
        data = conn.read(worksheet=worksheet_name, ttl=300)
        data = data.dropna(how='all')
        return data
    except Exception as e:
        st.error(f"Error loading {worksheet_name} data: {str(e)}")
        return pd.DataFrame()

def convert_to_date(df, column_name):
    try:
        df[column_name] = pd.to_datetime(df[column_name], dayfirst=True, errors='coerce')
    except:
        pass
    return df

# Load all data
@st.cache_data(ttl=3600)
def load_all_data():
    sales_data = load_data("Sales")
    sales_data = convert_to_date(sales_data, "Invoice Date")
    
    visit_data = load_data("Visits")
    visit_data = convert_to_date(visit_data, "Visit Date")
    
    attendance_data = load_data("Attendance")
    attendance_data = convert_to_date(attendance_data, "Date")
    
    demo_data = load_data("Demos")
    demo_data = convert_to_date(demo_data, "Demo Date")
    
    employee_data = load_data("Person")
    
    return {
        "sales": sales_data,
        "visits": visit_data,
        "attendance": attendance_data,
        "demos": demo_data,
        "employees": employee_data
    }

# Date range filter
def date_range_filter(default_days=30):
    today = get_ist_time().date()
    default_start = today - timedelta(days=default_days)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            max_value=today
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=today,
            min_value=start_date,
            max_value=today
        )
    
    return start_date, end_date

# Main dashboard function
def dashboard():
    st.title("Business Operations Dashboard")
    
    # Load all data
    data = load_all_data()
    sales_data = data["sales"]
    visit_data = data["visits"]
    attendance_data = data["attendance"]
    demo_data = data["demos"]
    employee_data = data["employees"]
    
    # Check if data is loaded
    if sales_data.empty or visit_data.empty or attendance_data.empty or demo_data.empty:
        st.warning("Some data could not be loaded. Please check the connection.")
        return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    start_date, end_date = date_range_filter()
    
    # Convert dates to string for comparison
    start_str = start_date.strftime("%d-%m-%Y")
    end_str = end_date.strftime("%d-%m-%Y")
    
    # Employee filter
    all_employees = sorted(employee_data['Employee Name'].unique())
    selected_employees = st.sidebar.multiselect(
        "Filter by Employee(s)",
        all_employees,
        default=all_employees
    )
    
    # State filter
    all_states = sorted(sales_data['Outlet State'].dropna().unique())
    selected_states = st.sidebar.multiselect(
        "Filter by State(s)",
        all_states,
        default=all_states
    )
    
    # City filter
    all_cities = sorted(sales_data['Outlet City'].dropna().unique())
    selected_cities = st.sidebar.multiselect(
        "Filter by City(s)",
        all_cities,
        default=all_cities
    )
    
    # Apply filters to all datasets
    def filter_data(df, date_col, employee_col="Employee Name"):
        filtered = df.copy()
        
        # Convert date column to string for comparison if it's datetime
        if pd.api.types.is_datetime64_any_dtype(filtered[date_col]):
            filtered['date_str'] = filtered[date_col].dt.strftime('%d-%m-%Y')
        else:
            filtered['date_str'] = filtered[date_col]
        
        # Apply filters
        filtered = filtered[
            (filtered['date_str'] >= start_str) & 
            (filtered['date_str'] <= end_str)
        ]
        
        if selected_employees:
            filtered = filtered[filtered[employee_col].isin(selected_employees)]
        
        if 'Outlet State' in filtered.columns and selected_states:
            filtered = filtered[filtered['Outlet State'].isin(selected_states)]
        
        if 'Outlet City' in filtered.columns and selected_cities:
            filtered = filtered[filtered['Outlet City'].isin(selected_cities)]
        
        return filtered
    
    filtered_sales = filter_data(sales_data, "Invoice Date")
    filtered_visits = filter_data(visit_data, "Visit Date")
    filtered_attendance = filter_data(attendance_data, "Date")
    filtered_demos = filter_data(demo_data, "Demo Date")
    
    # Dashboard tabs
    tab1, tab2 = st.tabs(["Overall Dashboard", "Employee Dashboard"])
    
    with tab1:
        st.header("Overall Business Performance")
        
        # KPI Metrics
        st.subheader("Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sales = filtered_sales['Grand Total'].sum()
            st.metric("Total Sales (INR)", f"₹{total_sales:,.2f}")
        
        with col2:
            total_visits = len(filtered_visits)
            st.metric("Total Visits", f"{total_visits}")
        
        with col3:
            total_demos = len(filtered_demos)
            st.metric("Total Demos", f"{total_demos}")
        
        with col4:
            avg_attendance = filtered_attendance['Status'].value_counts().to_dict()
            present_count = avg_attendance.get('Present', 0) + avg_attendance.get('Half Day', 0)
            st.metric("Present Employees", f"{present_count}")
        
        # Sales Trends
        st.subheader("Sales Trends")
        
        if not filtered_sales.empty:
            # Daily sales
            daily_sales = filtered_sales.groupby(
                filtered_sales['Invoice Date'].dt.date
            )['Grand Total'].sum().reset_index()
            
            fig = px.line(
                daily_sales,
                x="Invoice Date",
                y="Grand Total",
                title="Daily Sales Trend",
                labels={"Invoice Date": "Date", "Grand Total": "Sales (INR)"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Sales by employee
            sales_by_emp = filtered_sales.groupby('Employee Name')['Grand Total'].sum().reset_index()
            sales_by_emp = sales_by_emp.sort_values('Grand Total', ascending=False)
            
            fig = px.bar(
                sales_by_emp,
                x="Employee Name",
                y="Grand Total",
                title="Sales by Employee",
                labels={"Employee Name": "Employee", "Grand Total": "Sales (INR)"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Sales by product
            sales_by_product = filtered_sales.groupby('Product Name')['Quantity'].sum().reset_index()
            sales_by_product = sales_by_product.sort_values('Quantity', ascending=False).head(10)
            
            fig = px.bar(
                sales_by_product,
                x="Product Name",
                y="Quantity",
                title="Top 10 Products by Quantity Sold",
                labels={"Product Name": "Product", "Quantity": "Units Sold"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No sales data available for the selected filters")
        
        # Visit Analysis
        st.subheader("Visit Analysis")
        
        if not filtered_visits.empty:
            # Visits by employee
            visits_by_emp = filtered_visits['Employee Name'].value_counts().reset_index()
            visits_by_emp.columns = ['Employee Name', 'Visit Count']
            
            fig = px.bar(
                visits_by_emp,
                x="Employee Name",
                y="Visit Count",
                title="Visits by Employee",
                labels={"Employee Name": "Employee", "Visit Count": "Number of Visits"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Visit purpose breakdown
            visit_purpose = filtered_visits['Visit Purpose'].value_counts().reset_index()
            visit_purpose.columns = ['Purpose', 'Count']
            
            fig = px.pie(
                visit_purpose,
                names="Purpose",
                values="Count",
                title="Visit Purpose Breakdown"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No visit data available for the selected filters")
        
        # Demo Analysis
        st.subheader("Demo Analysis")
        
        if not filtered_demos.empty:
            # Demos by employee
            demos_by_emp = filtered_demos['Employee Name'].value_counts().reset_index()
            demos_by_emp.columns = ['Employee Name', 'Demo Count']
            
            fig = px.bar(
                demos_by_emp,
                x="Employee Name",
                y="Demo Count",
                title="Demos by Employee",
                labels={"Employee Name": "Employee", "Demo Count": "Number of Demos"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Demo review ratings
            demo_reviews = filtered_demos['Outlet Review'].value_counts().reset_index()
            demo_reviews.columns = ['Review', 'Count']
            
            fig = px.pie(
                demo_reviews,
                names="Review",
                values="Count",
                title="Demo Review Ratings"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No demo data available for the selected filters")
        
        # Attendance Analysis
        st.subheader("Attendance Analysis")
        
        if not filtered_attendance.empty:
            # Attendance status
            attendance_status = filtered_attendance['Status'].value_counts().reset_index()
            attendance_status.columns = ['Status', 'Count']
            
            fig = px.pie(
                attendance_status,
                names="Status",
                values="Count",
                title="Attendance Status Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Daily attendance trend
            daily_attendance = filtered_attendance.groupby(
                filtered_attendance['Date'].dt.date
            )['Employee Name'].nunique().reset_index()
            daily_attendance.columns = ['Date', 'Employee Count']
            
            fig = px.line(
                daily_attendance,
                x="Date",
                y="Employee Count",
                title="Daily Employee Attendance Trend",
                labels={"Date": "Date", "Employee Count": "Number of Employees"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No attendance data available for the selected filters")
    
    with tab2:
        st.header("Employee Performance Analysis")
        
        if not selected_employees:
            st.warning("Please select at least one employee to view individual performance")
        else:
            # Select employee for detailed view
            selected_emp = st.selectbox(
                "Select Employee for Detailed View",
                selected_employees
            )
            
            # Employee summary
            st.subheader(f"Performance Summary: {selected_emp}")
            
            # Get employee data
            emp_data = employee_data[employee_data['Employee Name'] == selected_emp].iloc[0]
            emp_sales = filtered_sales[filtered_sales['Employee Name'] == selected_emp]
            emp_visits = filtered_visits[filtered_visits['Employee Name'] == selected_emp]
            emp_attendance = filtered_attendance[filtered_attendance['Employee Name'] == selected_emp]
            emp_demos = filtered_demos[filtered_demos['Employee Name'] == selected_emp]
            
            # Employee KPIs
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                emp_sales_total = emp_sales['Grand Total'].sum()
                st.metric("Total Sales", f"₹{emp_sales_total:,.2f}")
            
            with col2:
                avg_sale = emp_sales_total / len(emp_visits) if len(emp_visits) > 0 else 0
                st.metric("Avg. Sale per Visit", f"₹{avg_sale:,.2f}")
            
            with col3:
                visit_count = len(emp_visits)
                st.metric("Total Visits", f"{visit_count}")
            
            with col4:
                demo_count = len(emp_demos)
                st.metric("Total Demos", f"{demo_count}")
            
            # Sales performance
            st.subheader("Sales Performance")
            
            if not emp_sales.empty:
                # Daily sales trend
                daily_sales = emp_sales.groupby(
                    emp_sales['Invoice Date'].dt.date
                )['Grand Total'].sum().reset_index()
                
                fig = px.line(
                    daily_sales,
                    x="Invoice Date",
                    y="Grand Total",
                    title=f"Daily Sales Trend - {selected_emp}",
                    labels={"Invoice Date": "Date", "Grand Total": "Sales (INR)"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Top products sold
                top_products = emp_sales.groupby('Product Name')['Quantity'].sum().reset_index()
                top_products = top_products.sort_values('Quantity', ascending=False).head(10)
                
                fig = px.bar(
                    top_products,
                    x="Product Name",
                    y="Quantity",
                    title=f"Top Products Sold - {selected_emp}",
                    labels={"Product Name": "Product", "Quantity": "Units Sold"}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No sales data available for {selected_emp}")
            
            # Visit performance
            st.subheader("Visit Performance")
            
            if not emp_visits.empty:
                # Visit purpose breakdown
                visit_purpose = emp_visits['Visit Purpose'].value_counts().reset_index()
                visit_purpose.columns = ['Purpose', 'Count']
                
                fig = px.pie(
                    visit_purpose,
                    names="Purpose",
                    values="Count",
                    title=f"Visit Purpose Breakdown - {selected_emp}"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Visit duration analysis
                emp_visits['Visit Duration (minutes)'] = pd.to_numeric(emp_visits['Visit Duration (minutes)'], errors='coerce')
                avg_duration = emp_visits['Visit Duration (minutes)'].mean()
                
                fig = px.histogram(
                    emp_visits,
                    x="Visit Duration (minutes)",
                    title=f"Visit Duration Distribution - {selected_emp}",
                    labels={"Visit Duration (minutes)": "Duration (minutes)"}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No visit data available for {selected_emp}")
            
            # Demo performance
            st.subheader("Demo Performance")
            
            if not emp_demos.empty:
                # Demo review ratings
                demo_reviews = emp_demos['Outlet Review'].value_counts().reset_index()
                demo_reviews.columns = ['Review', 'Count']
                
                fig = px.pie(
                    demo_reviews,
                    names="Review",
                    values="Count",
                    title=f"Demo Review Ratings - {selected_emp}"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Demo duration analysis
                emp_demos['Duration (minutes)'] = pd.to_numeric(emp_demos['Duration (minutes)'], errors='coerce')
                avg_demo_duration = emp_demos['Duration (minutes)'].mean()
                
                fig = px.histogram(
                    emp_demos,
                    x="Duration (minutes)",
                    title=f"Demo Duration Distribution - {selected_emp}",
                    labels={"Duration (minutes)": "Duration (minutes)"}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No demo data available for {selected_emp}")
            
            # Attendance record
            st.subheader("Attendance Record")
            
            if not emp_attendance.empty:
                # Attendance status
                attendance_status = emp_attendance['Status'].value_counts().reset_index()
                attendance_status.columns = ['Status', 'Count']
                
                fig = px.pie(
                    attendance_status,
                    names="Status",
                    values="Count",
                    title=f"Attendance Status - {selected_emp}"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Attendance calendar heatmap
                try:
                    emp_attendance['date'] = pd.to_datetime(emp_attendance['Date'], dayfirst=True)
                    emp_attendance['day_of_week'] = emp_attendance['date'].dt.day_name()
                    emp_attendance['week'] = emp_attendance['date'].dt.isocalendar().week
                    emp_attendance['year'] = emp_attendance['date'].dt.year
                    
                    # Create a pivot table for the heatmap
                    heatmap_data = emp_attendance.pivot_table(
                        index='day_of_week',
                        columns='week',
                        values='Status',
                        aggfunc='count',
                        fill_value=0
                    )
                    
                    # Reorder days of week
                    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    heatmap_data = heatmap_data.reindex(days_order)
                    
                    fig = px.imshow(
                        heatmap_data,
                        labels=dict(x="Week", y="Day of Week", color="Attendance"),
                        title=f"Weekly Attendance Pattern - {selected_emp}",
                        aspect="auto"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not generate attendance heatmap: {str(e)}")
            else:
                st.warning(f"No attendance data available for {selected_emp}")

# Run the dashboard
if __name__ == "__main__":
    dashboard()
