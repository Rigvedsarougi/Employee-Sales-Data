import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

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

def get_date_range():
    today = datetime.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    last_quarter = today - timedelta(days=90)
    return today, last_week, last_month, last_quarter

def generate_pdf_report(data, title, context=None):
    """Generate professional PDF report with proper formatting"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1, fontSize=12, spaceAfter=12))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    styles.add(ParagraphStyle(name='Bold', fontName='Helvetica-Bold', fontSize=10))
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"<b>{title}</b>", styles['Heading1']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Context information
    if context:
        for key, value in context.items():
            elements.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
    
    elements.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*inch))
    
    # Add content based on data type
    if isinstance(data, pd.DataFrame):
        # Format numeric columns
        df = data.copy()
        for col in df.select_dtypes(include=[np.number]).columns:
            if any(word in col.lower() for word in ['amount', 'price', 'total', 'sales']):
                df[col] = df[col].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else '')
            elif '%' in col or 'percentage' in col.lower():
                df[col] = df[col].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else '')
            elif 'duration' in col.lower():
                df[col] = df[col].apply(lambda x: f"{x:.1f} mins" if pd.notnull(x) else '')
            else:
                df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) and x == int(x) else f"{x:,.2f}" if pd.notnull(x) else '')
        
        # Prepare table data
        table_data = [df.columns.tolist()] + df.values.tolist()
        
        # Create table
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#D9E1F2')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
    
    elif isinstance(data, dict):
        # For metrics display
        for section, metrics in data.items():
            elements.append(Paragraph(f"<b>{section}</b>", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))
            
            metric_data = []
            for name, value in metrics.items():
                if isinstance(value, (int, float)):
                    if any(word in name.lower() for word in ['amount', 'price', 'total', 'sales']):
                        display_value = f"₹{value:,.2f}"
                    elif '%' in name or 'percentage' in name.lower():
                        display_value = f"{value:.1f}%"
                    elif 'duration' in name.lower():
                        display_value = f"{value:.1f} mins"
                    else:
                        display_value = f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
                else:
                    display_value = str(value)
                
                metric_data.append([Paragraph(f"<b>{name}</b>", styles['Bold']), display_value])
            
            metric_table = Table(metric_data, colWidths=[3*inch, 2*inch], hAlign='LEFT')
            metric_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            
            elements.append(metric_table)
            elements.append(Spacer(1, 0.25*inch))
    
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph("End of Report", styles['Center']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

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
                if username == "admin" and password == "admin123":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return
    
    # Load all data
    with st.spinner("Loading data..."):
        sales_data = load_data("Sales", SALES_SHEET_COLUMNS)
        visits_data = load_data("Visits", VISIT_SHEET_COLUMNS)
        attendance_data = load_data("Attendance", ATTENDANCE_SHEET_COLUMNS)
    
    # Convert date columns
    if not sales_data.empty:
        sales_data['Invoice Date'] = pd.to_datetime(sales_data['Invoice Date'], dayfirst=True, errors='coerce')
    if not visits_data.empty:
        visits_data['Visit Date'] = pd.to_datetime(visits_data['Visit Date'], dayfirst=True, errors='coerce')
    if not attendance_data.empty:
        attendance_data['Date'] = pd.to_datetime(attendance_data['Date'], dayfirst=True, errors='coerce')
    
    # Date filters
    today, last_week, last_month, last_quarter = get_date_range()
    
    st.sidebar.header("Filters")
    time_period = st.sidebar.selectbox(
        "Time Period",
        ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
        index=2
    )
    
    if time_period == "Today":
        start_date = today
    elif time_period == "Last 7 Days":
        start_date = last_week
    elif time_period == "Last 30 Days":
        start_date = last_month
    elif time_period == "Last 90 Days":
        start_date = last_quarter
    else:
        start_date = None
    
    # Filter data based on date range
    if start_date:
        if not sales_data.empty:
            sales_data = sales_data[sales_data['Invoice Date'].dt.date >= start_date]
        if not visits_data.empty:
            visits_data = visits_data[visits_data['Visit Date'].dt.date >= start_date]
        if not attendance_data.empty:
            attendance_data = attendance_data[attendance_data['Date'].dt.date >= start_date]
    
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
        
        if not attendance_data.empty:
            today_attendance = attendance_data[attendance_data['Date'].dt.date == datetime.now().date()]
            present_count = len(today_attendance[today_attendance['Status'] == 'Present'])
            leave_count = len(today_attendance[today_attendance['Status'] == 'Leave'])
        else:
            present_count = 0
            leave_count = 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sales", format_currency(total_sales))
        with col2:
            st.metric("Total Invoices", total_invoices)
        with col3:
            st.metric("Avg. Sale/Invoice", format_currency(avg_sale_per_invoice))
        with col4:
            st.metric("Payment Completion", format_percentage(payment_completion))
        
        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("Total Visits", total_visits)
        with col6:
            st.metric("Avg. Visit Duration", f"{avg_visit_duration:.1f} mins")
        with col7:
            st.metric("Present Today", present_count)
        
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
            
            if not visits_data.empty:
                visits_summary = visits_data.groupby('Employee Name').agg({
                    'Visit ID': 'count',
                    'Visit Duration (minutes)': 'mean'
                }).reset_index()
                visits_summary.columns = ['Employee Name', 'Total Visits', 'Avg. Visit Duration']
                employee_performance = pd.merge(employee_performance, visits_summary, on='Employee Name', how='left')
            
            st.dataframe(
                employee_performance.sort_values('Total Sales', ascending=False),
                column_config={
                    "Total Sales": st.column_config.NumberColumn(format="₹%.2f"),
                    "Avg. Visit Duration": st.column_config.NumberColumn(format="%.1f mins")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # PDF Export for Overview
            if st.button("📥 Download Overview Report (PDF)"):
                report_data = {
                    "Key Metrics": {
                        "Total Sales": total_sales,
                        "Total Invoices": total_invoices,
                        "Average Sale per Invoice": avg_sale_per_invoice,
                        "Payment Completion": payment_completion,
                        "Total Visits": total_visits,
                        "Average Visit Duration (mins)": avg_visit_duration,
                        "Employees Present Today": present_count
                    }
                }
                
                pdf_buffer = generate_pdf_report(
                    employee_performance.head(10),
                    "Business Overview Report",
                    context={
                        "Time Period": time_period,
                        "Employee Filter": selected_employee
                    }
                )
                
                st.download_button(
                    "⬇️ Download PDF Report",
                    pdf_buffer,
                    file_name="business_overview_report.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("No performance data available for the selected period")
    
    with tab2:
        st.header("Employee Performance Analysis")
        
        if selected_employee == "All Employees":
            st.warning("Please select an employee from the sidebar to view detailed performance")
        else:
            st.subheader(f"Performance Report: {selected_employee}")
            
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
                
                # PDF Export for Employee Performance
                if st.button("📥 Download Performance Report (PDF)"):
                    report_data = {
                        "Employee Information": {
                            "Name": selected_employee,
                            "Employee Code": employee_details['Employee Code'],
                            "Designation": employee_details['Designation'],
                            "Discount Category": employee_details['Discount Category']
                        },
                        "Sales Performance": {
                            "Total Sales": total_sales,
                            "Total Invoices": total_invoices,
                            "Average Sale per Invoice": avg_sale_per_invoice,
                            "Payment Completion": payment_completion
                        }
                    }
                    
                    if not visits_data.empty:
                        report_data["Visit Performance"] = {
                            "Total Visits": total_visits,
                            "Average Visit Duration (mins)": avg_visit_duration
                        }
                    
                    if not attendance_data.empty:
                        report_data["Attendance"] = {
                            "Present Days": present_days,
                            "Leave Days": leave_days
                        }
                    
                    pdf_buffer = generate_pdf_report(
                        report_data,
                        f"Employee Performance Report - {selected_employee}",
                        context={
                            "Time Period": time_period,
                            "Report Date": datetime.now().strftime('%Y-%m-%d')
                        }
                    )
                    
                    st.download_button(
                        "⬇️ Download PDF Report",
                        pdf_buffer,
                        file_name=f"employee_performance_{selected_employee}.pdf",
                        mime="application/pdf"
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
            
            # Attendance performance
            st.subheader("Attendance Record")
            if not attendance_data.empty:
                employee_attendance = attendance_data[attendance_data['Employee Name'] == selected_employee]
                present_days = len(employee_attendance[employee_attendance['Status'] == 'Present'])
                leave_days = len(employee_attendance[employee_attendance['Status'] == 'Leave'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Present Days", present_days)
                with col2:
                    st.metric("Leave Days", leave_days)
            else:
                st.warning("No attendance data available for this employee")
    
    with tab3:
        st.header("Detailed Records")
        
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
                "Export Sales Data (CSV)",
                csv,
                "sales_records.csv",
                "text/csv",
                key='download-sales-csv'
            )
            
            # PDF Export
            if st.button("Export Sales Data (PDF)"):
                pdf_buffer = generate_pdf_report(
                    sales_data.head(100),
                    "Detailed Sales Records",
                    context={
                        "Time Period": time_period,
                        "Employee Filter": selected_employee,
                        "Total Records": len(sales_data)
                    }
                )
                
                st.download_button(
                    "⬇️ Download PDF Report",
                    pdf_buffer,
                    file_name="detailed_sales_records.pdf",
                    mime="application/pdf"
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
                "Export Visit Data (CSV)",
                csv,
                "visit_records.csv",
                "text/csv",
                key='download-visit-csv'
            )
            
            # PDF Export
            if st.button("Export Visit Data (PDF)"):
                pdf_buffer = generate_pdf_report(
                    visits_data.head(100),
                    "Detailed Visit Records",
                    context={
                        "Time Period": time_period,
                        "Employee Filter": selected_employee,
                        "Total Records": len(visits_data)
                    }
                )
                
                st.download_button(
                    "⬇️ Download PDF Report",
                    pdf_buffer,
                    file_name="detailed_visit_records.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("No visit data available for the selected period")
        
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
                "Export Attendance Data (CSV)",
                csv,
                "attendance_records.csv",
                "text/csv",
                key='download-attendance-csv'
            )
            
            # PDF Export
            if st.button("Export Attendance Data (PDF)"):
                pdf_buffer = generate_pdf_report(
                    attendance_data.head(100),
                    "Detailed Attendance Records",
                    context={
                        "Time Period": time_period,
                        "Employee Filter": selected_employee,
                        "Total Records": len(attendance_data)
                    }
                )
                
                st.download_button(
                    "⬇️ Download PDF Report",
                    pdf_buffer,
                    file_name="detailed_attendance_records.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("No attendance data available for the selected period")

if __name__ == "__main__":
    main()
