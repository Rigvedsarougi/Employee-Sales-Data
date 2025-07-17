import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from fpdf import FPDF
import os
import uuid
from PIL import Image

# Configuration
st.set_page_config(page_title="Admin Dashboard", layout="wide", page_icon="📊")

# Hide Streamlit style
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stActionButton > button[title="Open source on GitHub"] {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Constants
SALES_SHEET_COLUMNS = [
    "Invoice Number", "Invoice Date", "Employee Name", "Employee Code", "Designation",
    "Discount Category", "Transaction Type", "Outlet Name", "Outlet Contact", "Outlet Address",
    "Outlet State", "Outlet City", "Distributor Firm Name", "Distributor ID", "Distributor Contact Person",
    "Distributor Contact Number", "Distributor Email", "Distributor Territory", "Product ID",
    "Product Name", "Product Category", "Quantity", "Unit Price", "Product Discount (%)",
    "Discounted Unit Price", "Total Price", "GST Rate", "CGST Amount", "SGST Amount",
    "Grand Total", "Overall Discount (%)", "Amount Discount (INR)", "Payment Status",
    "Amount Paid", "Payment Receipt Path", "Employee Selfie Path", "Invoice PDF Path",
    "Remarks", "Delivery Status"
]

VISIT_SHEET_COLUMNS = [
    "Visit ID", "Employee Name", "Employee Code", "Designation", "Outlet Name",
    "Outlet Contact", "Outlet Address", "Outlet State", "Outlet City", "Visit Date",
    "Entry Time", "Exit Time", "Visit Duration (minutes)", "Visit Purpose", "Visit Notes",
    "Visit Selfie Path", "Visit Status", "Remarks"
]

DEMO_SHEET_COLUMNS = [
    "Demo ID", "Employee Name", "Employee Code", "Designation", "Partner Employee",
    "Partner Employee Code", "Outlet Name", "Outlet Contact", "Outlet Address", "Outlet State",
    "Outlet City", "Demo Date", "Check-in Time", "Check-out Time", "Check-in Date Time",
    "Duration (minutes)", "Outlet Review", "Remarks", "Status", "Products", "Quantities"
]

ATTENDANCE_SHEET_COLUMNS = [
    "Attendance ID", "Employee Name", "Employee Code", "Designation", "Date",
    "Status", "Location Link", "Leave Reason", "Check-in Time", "Check-in Date Time"
]

# Establish connections
conn = st.connection("gsheets", type=GSheetsConnection)
Person = pd.read_csv('Invoice - Person.csv')

# Helper functions
def load_data(worksheet_name, columns):
    try:
        data = conn.read(worksheet=worksheet_name, usecols=list(range(len(columns))), ttl=5)
        data = data.dropna(how='all')
        
        # Fix data types for Arrow compatibility
        for col in data.columns:
            if data[col].dtype == 'object':
                data[col] = data[col].astype(str)
            elif pd.api.types.is_numeric_dtype(data[col]):
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        return data
    except Exception as e:
        st.error(f"Error loading {worksheet_name} data: {e}")
        return pd.DataFrame(columns=columns)

def format_currency(amount):
    return f"₹{amount:,.2f}"

def format_percentage(value):
    return f"{value:.1f}%"

def get_default_dates():
    today = datetime.now().date()
    last_month = today - timedelta(days=30)
    return last_month, today

def generate_pdf_report(content, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.ln(10)
    
    # Add content
    pdf.set_font("Arial", size=10)
    for line in content.split('\n'):
        pdf.multi_cell(0, 5, txt=line)
        pdf.ln(5)
    
    # Save to temporary file
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

def get_attendance_counts(attendance_data, start_date, end_date):
    if attendance_data.empty:
        return 0, 0
    
    # Convert dates to datetime.date for comparison
    attendance_data['Date'] = pd.to_datetime(attendance_data['Date']).dt.date
    
    # Filter by date range
    filtered_attendance = attendance_data[
        (attendance_data['Date'] >= start_date) & 
        (attendance_data['Date'] <= end_date)
    ]
    
    # Get today's date
    today = datetime.now().date()
    
    # Count all present/leave records in date range
    total_present = len(filtered_attendance[
        filtered_attendance['Status'].str.strip().str.lower() == 'present'
    ])
    total_leave = len(filtered_attendance[
        filtered_attendance['Status'].str.strip().str.lower() == 'leave'
    ])
    
    # Count today's attendance if today is in range
    today_present = 0
    today_leave = 0
    if start_date <= today <= end_date:
        today_attendance = filtered_attendance[filtered_attendance['Date'] == today]
        today_present = len(today_attendance[
            today_attendance['Status'].str.strip().str.lower() == 'present'
        ])
        today_leave = len(today_attendance[
            today_attendance['Status'].str.strip().str.lower() == 'leave'
        ])
    
    return total_present, total_leave, today_present, today_leave

# Dashboard layout
def main():
    st.title("📊 Employee Portal Admin Dashboard")
    
    # Authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        with st.form("admin_auth"):
            st.subheader("Admin Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                if username == "admin" and password == "admin123":  # Replace with secure auth
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return
    
    # Load all data
    with st.spinner("Loading data..."):
        sales_data = load_data("Sales", SALES_SHEET_COLUMNS)
        visits_data = load_data("Visits", VISIT_SHEET_COLUMNS)
        demo_data = load_data("Demos", DEMO_SHEET_COLUMNS)
        attendance_data = load_data("Attendance", ATTENDANCE_SHEET_COLUMNS)
    
    # Convert date columns
    if not sales_data.empty:
        sales_data['Invoice Date'] = pd.to_datetime(sales_data['Invoice Date'], dayfirst=True, errors='coerce')
    if not visits_data.empty:
        visits_data['Visit Date'] = pd.to_datetime(visits_data['Visit Date'], dayfirst=True, errors='coerce')
    if not demo_data.empty:
        demo_data['Demo Date'] = pd.to_datetime(demo_data['Demo Date'], dayfirst=True, errors='coerce')
    if not attendance_data.empty:
        attendance_data['Date'] = pd.to_datetime(attendance_data['Date'], dayfirst=True, errors='coerce')
    
    # Date filters
    default_start, default_end = get_default_dates()
    
    st.sidebar.header("Filters")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=default_start)
    with col2:
        end_date = st.date_input("End Date", value=default_end)
    
    # Validate date range
    if start_date > end_date:
        st.sidebar.error("End date must be after start date")
    
    # Filter data based on date range
    if not sales_data.empty:
        sales_data = sales_data[
            (sales_data['Invoice Date'].dt.date >= start_date) & 
            (sales_data['Invoice Date'].dt.date <= end_date)
        ]
    if not visits_data.empty:
        visits_data = visits_data[
            (visits_data['Visit Date'].dt.date >= start_date) & 
            (visits_data['Visit Date'].dt.date <= end_date)
        ]
    if not demo_data.empty:
        demo_data = demo_data[
            (demo_data['Demo Date'].dt.date >= start_date) & 
            (demo_data['Demo Date'].dt.date <= end_date)
        ]
    
    # Get attendance counts (both total and today's)
    total_present, total_leave, today_present, today_leave = get_attendance_counts(
        attendance_data, start_date, end_date
    )
    
    # Employee filter
    all_employees = Person['Employee Name'].unique().tolist()
    selected_employee = st.sidebar.selectbox(
        "Employee (All)",
        ["All Employees"] + all_employees
    )
    
    if selected_employee != "All Employees":
        if not sales_data.empty:
            sales_data = sales_data[sales_data['Employee Name'] == selected_employee]
        if not visits_data.empty:
            visits_data = visits_data[visits_data['Employee Name'] == selected_employee]
        if not demo_data.empty:
            demo_data = demo_data[demo_data['Employee Name'] == selected_employee]
        if not attendance_data.empty:
            attendance_data = attendance_data[attendance_data['Employee Name'] == selected_employee]
    
    # Main dashboard
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "👥 Employee Performance", "📋 Detailed Records"])
    
    with tab1:
        st.header("Business Overview")
        
        # KPI Cards
        if not sales_data.empty:
            total_sales = sales_data['Grand Total'].sum()
            total_invoices = sales_data['Invoice Number'].nunique()
            avg_sale_per_invoice = total_sales / total_invoices if total_invoices > 0 else 0
            payment_completion = (sales_data[sales_data['Payment Status'] == 'paid']['Grand Total'].sum() / total_sales * 100) if total_sales > 0 else 0
        else:
            total_sales = 0
            total_invoices = 0
            avg_sale_per_invoice = 0
            payment_completion = 0
        
        if not visits_data.empty:
            total_visits = len(visits_data)
            avg_visit_duration = visits_data['Visit Duration (minutes)'].mean()
        else:
            total_visits = 0
            avg_visit_duration = 0
            
        if not demo_data.empty:
            total_demos = len(demo_data)
            avg_demo_duration = demo_data['Duration (minutes)'].mean()
        else:
            total_demos = 0
            avg_demo_duration = 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sales", format_currency(total_sales))
        with col2:
            st.metric("Total Invoices", total_invoices)
        with col3:
            st.metric("Avg. Sale/Invoice", format_currency(avg_sale_per_invoice))
        with col4:
            st.metric("Payment Completion", format_percentage(payment_completion))
        
        col5, col6 = st.columns(4)
        with col5:
            st.metric("Total Visits", total_visits)
        with col6:
            st.metric("Total Demos", total_demos)
            
        col7, col8 = st.columns(4)
        with col7:
            st.metric("Present Today", today_present)
        with col8:
            st.metric("Leave Today", today_leave)
        
        # Sales Trend Chart
        st.subheader("Sales Trend")
        if not sales_data.empty:
            sales_trend = sales_data.groupby(sales_data['Invoice Date'].dt.date)['Grand Total'].sum().reset_index()
            fig = px.line(
                sales_trend,
                x='Invoice Date',
                y='Grand Total',
                title="Daily Sales Trend",
                labels={'Invoice Date': 'Date', 'Grand Total': 'Total Sales (₹)'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No sales data available for the selected period")
        
        # Employee Performance Grid
        st.subheader("Employee Performance Summary")
        if not sales_data.empty:
            employee_performance = sales_data.groupby(['Employee Name', 'Employee Code', 'Designation']).agg({
                'Grand Total': 'sum',
                'Invoice Number': 'nunique',
                'Product Name': 'count'
            }).reset_index()
            employee_performance.columns = ['Employee Name', 'Employee Code', 'Designation', 'Total Sales', 'Invoices', 'Products Sold']
            
            # Add visit data if available
            if not visits_data.empty:
                visits_summary = visits_data.groupby('Employee Name').agg({
                    'Visit ID': 'count',
                    'Visit Duration (minutes)': 'mean'
                }).reset_index()
                visits_summary.columns = ['Employee Name', 'Total Visits', 'Avg. Visit Duration']
                employee_performance = pd.merge(employee_performance, visits_summary, on='Employee Name', how='left')
                
            # Add demo data if available
            if not demo_data.empty:
                demo_summary = demo_data.groupby('Employee Name').agg({
                    'Demo ID': 'count',
                    'Duration (minutes)': 'mean'
                }).reset_index()
                demo_summary.columns = ['Employee Name', 'Total Demos', 'Avg. Demo Duration']
                employee_performance = pd.merge(employee_performance, demo_summary, on='Employee Name', how='left')
            
            # Add attendance data if available
            if not attendance_data.empty:
                attendance_summary = attendance_data.groupby('Employee Name').agg({
                    'Attendance ID': 'count',
                    'Status': lambda x: (x.str.lower() == 'present').sum()
                }).reset_index()
                attendance_summary.columns = ['Employee Name', 'Total Days', 'Present Days']
                employee_performance = pd.merge(employee_performance, attendance_summary, on='Employee Name', how='left')
            
            st.dataframe(
                employee_performance.sort_values('Total Sales', ascending=False),
                column_config={
                    "Total Sales": st.column_config.NumberColumn(format="₹%.2f"),
                    "Avg. Visit Duration": st.column_config.NumberColumn(format="%.1f mins"),
                    "Avg. Demo Duration": st.column_config.NumberColumn(format="%.1f mins")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # PDF Export for Overview
            overview_content = f"""
            Business Overview Report
            ------------------------
            Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
            
            Key Metrics:
            - Total Sales: {format_currency(total_sales)}
            - Total Invoices: {total_invoices}
            - Average Sale per Invoice: {format_currency(avg_sale_per_invoice)}
            - Payment Completion: {format_percentage(payment_completion)}
            - Total Visits: {total_visits}
            - Average Visit Duration: {avg_visit_duration:.1f} mins
            - Total Demos: {total_demos}
            - Average Demo Duration: {avg_demo_duration:.1f} mins
            - Present Employees Today: {today_present}
            - Total Present in Period: {total_present}
            
            Top Performing Employees:
            {employee_performance[['Employee Name', 'Total Sales', 'Invoices']].head(5).to_string(index=False)}
            """
            
            if st.button("📥 Download Overview Report (PDF)"):
                pdf_file = generate_pdf_report(overview_content, "Business Overview Report")
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        "⬇️ Download Now",
                        f,
                        file_name="business_overview_report.pdf",
                        mime="application/pdf"
                    )
                os.remove(pdf_file)
        else:
            st.warning("No performance data available for the selected period")
    
    with tab2:
        st.header("Employee Performance Analysis")
        
        if selected_employee == "All Employees":
            st.warning("Please select an employee from the sidebar to view detailed performance")
        else:
            st.subheader(f"Performance Report: {selected_employee}")
            st.caption(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Employee details
            employee_details = Person[Person['Employee Name'] == selected_employee].iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Employee Code", employee_details['Employee Code'])
            with col2:
                st.metric("Designation", employee_details['Designation'])
            with col3:
                st.metric("Discount Category", employee_details['Discount Category'])
            
            # Sales performance
            st.subheader("Sales Performance")
            if not sales_data.empty:
                # Sales metrics
                employee_sales = sales_data[sales_data['Employee Name'] == selected_employee]
                total_sales = employee_sales['Grand Total'].sum()
                total_invoices = employee_sales['Invoice Number'].nunique()
                avg_sale_per_invoice = total_sales / total_invoices if total_invoices > 0 else 0
                payment_completion = (employee_sales[employee_sales['Payment Status'] == 'paid']['Grand Total'].sum() / total_sales * 100) if total_sales > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Sales", format_currency(total_sales))
                with col2:
                    st.metric("Total Invoices", total_invoices)
                with col3:
                    st.metric("Avg. Sale/Invoice", format_currency(avg_sale_per_invoice))
                with col4:
                    st.metric("Payment Completion", format_percentage(payment_completion))
                
                # Sales by product category
                st.subheader("Sales by Product Category")
                sales_by_category = employee_sales.groupby('Product Category')['Grand Total'].sum().reset_index()
                fig = px.pie(
                    sales_by_category,
                    values='Grand Total',
                    names='Product Category',
                    title="Sales Distribution by Product Category"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Top products
                st.subheader("Top Selling Products")
                top_products = employee_sales.groupby('Product Name').agg({
                    'Grand Total': 'sum',
                    'Quantity': 'sum'
                }).sort_values('Grand Total', ascending=False).head(10)
                st.dataframe(
                    top_products,
                    column_config={
                        "Grand Total": st.column_config.NumberColumn(format="₹%.2f")
                    },
                    use_container_width=True
                )
            else:
                st.warning("No sales data available for this employee")
            
            # Visit performance
            st.subheader("Visit Performance")
            if not visits_data.empty:
                employee_visits = visits_data[visits_data['Employee Name'] == selected_employee]
                total_visits = len(employee_visits)
                avg_visit_duration = employee_visits['Visit Duration (minutes)'].mean()
                visits_by_purpose = employee_visits['Visit Purpose'].value_counts().reset_index()
                visits_by_purpose.columns = ['Purpose', 'Count']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Visits", total_visits)
                with col2:
                    st.metric("Avg. Visit Duration", f"{avg_visit_duration:.1f} mins")
                
                # Visits by purpose
                fig = px.bar(
                    visits_by_purpose,
                    x='Purpose',
                    y='Count',
                    title="Visits by Purpose"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No visit data available for this employee")
                
            # Demo performance
            st.subheader("Demo Performance")
            if not demo_data.empty:
                employee_demos = demo_data[demo_data['Employee Name'] == selected_employee]
                total_demos = len(employee_demos)
                avg_demo_duration = employee_demos['Duration (minutes)'].mean()
                demos_by_review = employee_demos['Outlet Review'].value_counts().reset_index()
                demos_by_review.columns = ['Review', 'Count']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Demos", total_demos)
                with col2:
                    st.metric("Avg. Demo Duration", f"{avg_demo_duration:.1f} mins")
                
                # Demos by review
                fig = px.pie(
                    demos_by_review,
                    values='Count',
                    names='Review',
                    title="Demos by Outlet Review"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Top demo partners
                st.subheader("Top Demo Partners")
                demo_partners = employee_demos['Partner Employee'].value_counts().reset_index()
                demo_partners.columns = ['Partner', 'Count']
                st.dataframe(
                    demo_partners,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("No demo data available for this employee")
            
            # Attendance performance
            st.subheader("Attendance Record")
            if not attendance_data.empty:
                employee_attendance = attendance_data[attendance_data['Employee Name'] == selected_employee]
                present_days = len(employee_attendance[
                    employee_attendance['Status'].str.strip().str.lower() == 'present'
                ])
                leave_days = len(employee_attendance[
                    employee_attendance['Status'].str.strip().str.lower() == 'leave'
                ])
                
                # Get today's status if today is in range
                today_status = "Not Recorded"
                today = datetime.now().date()
                if start_date <= today <= end_date:
                    today_record = employee_attendance[
                        employee_attendance['Date'].dt.date == today
                    ]
                    if not today_record.empty:
                        today_status = today_record.iloc[0]['Status']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Present Days", present_days)
                with col2:
                    st.metric("Leave Days", leave_days)
                with col3:
                    st.metric("Today's Status", today_status)
                
                # Attendance calendar view
                st.subheader("Attendance Calendar")
                calendar_data = employee_attendance.copy()
                calendar_data['Date'] = calendar_data['Date'].dt.date
                calendar_data['Status'] = calendar_data['Status'].str.capitalize()
                st.dataframe(
                    calendar_data[['Date', 'Status', 'Check-in Time']],
                    column_config={
                        "Date": st.column_config.DateColumn(format="DD/MM/YYYY"),
                        "Status": st.column_config.TextColumn(),
                        "Check-in Time": st.column_config.TimeColumn(format="HH:mm")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("No attendance data available for this employee")
            
            # Generate PDF report for employee performance
            if st.button("📥 Download Performance Report (PDF)"):
                performance_content = f"""
                Employee Performance Report
                ---------------------------
                Employee: {selected_employee}
                Employee Code: {employee_details['Employee Code']}
                Designation: {employee_details['Designation']}
                Report Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
                Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                Sales Performance:
                - Total Sales: {format_currency(total_sales) if not sales_data.empty else 'N/A'}
                - Total Invoices: {total_invoices if not sales_data.empty else 'N/A'}
                - Average Sale per Invoice: {format_currency(avg_sale_per_invoice) if not sales_data.empty else 'N/A'}
                - Payment Completion: {format_percentage(payment_completion) if not sales_data.empty else 'N/A'}
                
                Visit Performance:
                - Total Visits: {total_visits if not visits_data.empty else 'N/A'}
                - Average Visit Duration: {f"{avg_visit_duration:.1f} mins" if not visits_data.empty else 'N/A'}
                
                Demo Performance:
                - Total Demos: {total_demos if not demo_data.empty else 'N/A'}
                - Average Demo Duration: {f"{avg_demo_duration:.1f} mins" if not demo_data.empty else 'N/A'}
                
                Attendance Record:
                - Present Days: {present_days if not attendance_data.empty else 'N/A'}
                - Leave Days: {leave_days if not attendance_data.empty else 'N/A'}
                - Today's Status: {today_status if not attendance_data.empty else 'N/A'}
                """
                
                pdf_file = generate_pdf_report(performance_content, f"Employee Performance Report - {selected_employee}")
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        "⬇️ Download Now",
                        f,
                        file_name=f"employee_performance_{selected_employee}.pdf",
                        mime="application/pdf"
                    )
                os.remove(pdf_file)
    
    with tab3:
        st.header("Detailed Records")
        st.caption(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Sales records
        st.subheader("Sales Records")
        if not sales_data.empty:
            st.dataframe(
                sales_data,
                column_config={
                    "Grand Total": st.column_config.NumberColumn(format="₹%.2f"),
                    "Invoice Date": st.column_config.DateColumn(format="DD/MM/YYYY")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Export options
            csv = sales_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Export Sales Data",
                csv,
                "sales_records.csv",
                "text/csv",
                key='download-sales-csv'
            )
        else:
            st.warning("No sales data available for the selected period")
        
        # Visit records
        st.subheader("Visit Records")
        if not visits_data.empty:
            st.dataframe(
                visits_data,
                column_config={
                    "Visit Date": st.column_config.DateColumn(format="DD/MM/YYYY")
                },
                use_container_width=True,
                hide_index=True
            )
            
            csv = visits_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Export Visit Data",
                csv,
                "visit_records.csv",
                "text/csv",
                key='download-visit-csv'
            )
        else:
            st.warning("No visit data available for the selected period")
            
        # Demo records
        st.subheader("Demo Records")
        if not demo_data.empty:
            st.dataframe(
                demo_data,
                column_config={
                    "Demo Date": st.column_config.DateColumn(format="DD/MM/YYYY")
                },
                use_container_width=True,
                hide_index=True
            )
            
            csv = demo_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Export Demo Data",
                csv,
                "demo_records.csv",
                "text/csv",
                key='download-demo-csv'
            )
        else:
            st.warning("No demo data available for the selected period")
        
        # Attendance records
        st.subheader("Attendance Records")
        if not attendance_data.empty:
            st.dataframe(
                attendance_data,
                column_config={
                    "Date": st.column_config.DateColumn(format="DD/MM/YYYY")
                },
                use_container_width=True,
                hide_index=True
            )
            
            csv = attendance_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Export Attendance Data",
                csv,
                "attendance_records.csv",
                "text/csv",
                key='download-attendance-csv'
            )
        else:
            st.warning("No attendance data available for the selected period")

if __name__ == "__main__":
    main()
