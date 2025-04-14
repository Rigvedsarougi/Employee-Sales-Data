import streamlit as st
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
from datetime import datetime, time
import os
import uuid
from PIL import Image

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stActionButton > button[title="Open source on GitHub"] {visibility: hidden;}
    header {visibility: hidden;}
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

# Display Title and Description
st.title("Biolume: Management System")

# Constants
SALES_SHEET_COLUMNS = [
    "Invoice Number",
    "Invoice Date",
    "Employee Name",
    "Employee Code",
    "Designation",
    "Discount Category",
    "Transaction Type",
    "Outlet Name",
    "Outlet Contact",
    "Outlet Address",
    "Outlet State",
    "Outlet City",
    "Distributor Firm Name",
    "Distributor ID",
    "Distributor Contact Person",
    "Distributor Contact Number",
    "Distributor Email",
    "Distributor Territory",
    "Product ID",
    "Product Name",
    "Product Category",
    "Quantity",
    "Unit Price",
    "Product Discount (%)",
    "Discounted Unit Price",
    "Total Price",
    "GST Rate",
    "CGST Amount",
    "SGST Amount",
    "Grand Total",
    "Overall Discount (%)",
    "Amount Discount (INR)",
    "Payment Status",
    "Amount Paid",
    "Payment Receipt Path",
    "Employee Selfie Path",
    "Invoice PDF Path",
    "Location"  # Added Location Column for Sales
]

VISIT_SHEET_COLUMNS = [
    "Visit ID",
    "Employee Name",
    "Employee Code",
    "Designation",
    "Outlet Name",
    "Outlet Contact",
    "Outlet Address",
    "Outlet State",
    "Outlet City",
    "Visit Date",
    "Entry Time",
    "Exit Time",
    "Visit Duration (minutes)",
    "Visit Purpose",
    "Visit Notes",
    "Visit Selfie Path",
    "Visit Status",
    "Location"  # Added Location Column for Visits
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
Products = pd.read_csv('Invoice - Products.csv')
Outlet = pd.read_csv('Invoice - Outlet.csv')
Person = pd.read_csv('Invoice - Person.csv')
Distributors = pd.read_csv('Invoice - Distributors.csv')

# Company Details
company_name = "BIOLUME SKIN SCIENCE PRIVATE LIMITED"
company_address = """Ground Floor Rampal Awana Complex,
Rampal Awana Complex, Indra Market,
Sector-27, Atta, Noida, Gautam Buddha Nagar,
Uttar Pradesh 201301
GSTIN/UIN: 09AALCB9426H1ZA
State Name: Uttar Pradesh, Code: 09
"""
company_logo = 'ALLGEN TRADING logo.png'
bank_details = """
Disclaimer: This Proforma Invoice is for estimation purposes only and is not a demand for payment. 
Prices, taxes, and availability are subject to change. Final billing may vary. 
Goods/services will be delivered only after confirmation and payment. No legal obligation is created by this document.
"""

# Create directories for storing uploads
os.makedirs("employee_selfies", exist_ok=True)
os.makedirs("payment_receipts", exist_ok=True)
os.makedirs("invoices", exist_ok=True)
os.makedirs("visit_selfies", exist_ok=True)

# Custom PDF class
class PDF(FPDF):
    def header(self):
        if company_logo:
            self.image(company_logo, 10, 8, 33)
        
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, company_name, ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, company_address, align='C')
        
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Proforma Invoice', ln=True, align='C')
        self.line(10, 50, 200, 50)
        self.ln(1)

def generate_invoice_number():
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def generate_visit_id():
    return f"VISIT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def generate_attendance_id():
    return f"ATT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"

def save_uploaded_file(uploaded_file, folder):
    if uploaded_file is not None:
        file_ext = os.path.splitext(uploaded_file.name)[1]
        file_path = os.path.join(folder, f"{str(uuid.uuid4())}{file_ext}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def log_sales_to_gsheet(conn, sales_data):
    try:
        existing_sales_data = conn.read(worksheet="Sales", usecols=list(range(len(SALES_SHEET_COLUMNS))), ttl=5)
        existing_sales_data = existing_sales_data.dropna(how="all")
        updated_sales_data = pd.concat([existing_sales_data, sales_data], ignore_index=True)
        conn.update(worksheet="Sales", data=updated_sales_data)
        st.success("Sales data successfully logged to Google Sheets!")
    except Exception as e:
        st.error(f"Error logging sales data: {e}")

def log_visit_to_gsheet(conn, visit_data):
    try:
        existing_visit_data = conn.read(worksheet="Visits", usecols=list(range(len(VISIT_SHEET_COLUMNS))), ttl=5)
        existing_visit_data = existing_visit_data.dropna(how="all")
        updated_visit_data = pd.concat([existing_visit_data, visit_data], ignore_index=True)
        conn.update(worksheet="Visits", data=updated_visit_data)
        st.success("Visit data successfully logged to Google Sheets!")
    except Exception as e:
        st.error(f"Error logging visit data: {e}")

def log_attendance_to_gsheet(conn, attendance_data):
    try:
        existing_data = conn.read(worksheet="Attendance", usecols=list(range(len(ATTENDANCE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how="all")
        updated_data = pd.concat([existing_data, attendance_data], ignore_index=True)
        conn.update(worksheet="Attendance", data=updated_data)
        return True, None
    except Exception as e:
        return False, str(e)

# Collect the location through JavaScript
def get_current_location():
    components.html("""
    <script>
        navigator.geolocation.getCurrentPosition(function(position) {
            var latitude = position.coords.latitude;
            var longitude = position.coords.longitude;
            var location = "https://www.google.com/maps?q=" + latitude + "," + longitude;
            window.parent.postMessage(location, "*");
        });
    </script>
    """, height=0)

# Sales Page Update with Location Button
def sales_page():
    st.title("Sales Management")
    selected_employee = st.session_state.employee_name
    
    tab1, tab2 = st.tabs(["New Sale", "Sales History"])
    
    with tab1:
        st.subheader("Employee Verification")
        employee_selfie = st.file_uploader("Upload Employee Selfie", type=["jpg", "jpeg", "png"], key="employee_selfie")

        # Add a button to collect the current location for the invoice
        get_location_button = st.button("Get Current Location for Invoice", key="get_invoice_location_button")
        
        if get_location_button:
            # Get current location
            get_current_location()

            # Collect the location from JavaScript
            location = st.experimental_get_query_params().get("location", [""])[0]
            if location:
                st.text_input("Your Location", value=location, disabled=True)

        # After collecting the location, it can be passed as part of the invoice generation
        if st.button("Generate Invoice", key="generate_invoice_button"):
            if selected_products and customer_name:
                invoice_number = generate_invoice_number()
                
                employee_selfie_path = save_uploaded_file(employee_selfie, "employee_selfies") if employee_selfie else None
                payment_receipt_path = save_uploaded_file(payment_receipt, "payment_receipts") if payment_receipt else None
                
                pdf, pdf_path = generate_invoice(
                    customer_name, gst_number, contact_number, address, state, city,
                    selected_products, quantities, product_discounts, discount_category, 
                    selected_employee, overall_discount, amount_discount,
                    payment_status, amount_paid, employee_selfie_path, 
                    payment_receipt_path, invoice_number, transaction_type,
                    distributor_firm_name, distributor_id, distributor_contact_person,
                    distributor_contact_number, distributor_email, distributor_territory, 
                    location  # Add location to the invoice data
                )
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download Invoice", 
                        f, 
                        file_name=f"{invoice_number}.pdf",
                        mime="application/pdf",
                        key=f"download_{invoice_number}"
                    )
                
                st.success(f"Invoice {invoice_number} generated successfully!")
            else:
                st.error("Please fill all required fields and select products.")
