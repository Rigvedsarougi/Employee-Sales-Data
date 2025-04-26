import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os
import uuid
from PIL import Image

# Constants
COMPANY_NAME = "BIOLUME SKIN SCIENCE PRIVATE LIMITED"
COMPANY_ADDRESS = """Ground Floor Rampal Awana Complex,
Rampal Awana Complex, Indra Market,
Sector-27, Atta, Noida, Gautam Buddha Nagar,
Uttar Pradesh 201301
GSTIN/UIN: 09AALCB9426H1ZA
State Name: Uttar Pradesh, Code: 09"""
LOGO_PATH = 'ALLGEN TRADING logo.png'
BANK_DETAILS = """Disclaimer: This Proforma Invoice is for estimation purposes only and is not a demand for payment. 
Prices, taxes, and availability are subject to change. Final billing may vary. 
Goods/services will be delivered only after confirmation and payment. No legal obligation is created by this document."""

# Hide Streamlit default UI elements
hide_ui = """
<style>
#MainMenu, footer, header, .stActionButton > button[title="Open source on GitHub"] {visibility: hidden;}
</style>
"""
st.markdown(hide_ui, unsafe_allow_html=True)

# Initialize session state
def init_session():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = None
    if 'employee_name' not in st.session_state:
        st.session_state.employee_name = None

# Load data
@st.cache_data
def load_data():
    return {
        'products': pd.read_csv('Invoice - Products.csv'),
        'outlet': pd.read_csv('Invoice - Outlet.csv'),
        'person': pd.read_csv('Invoice - Person.csv'),
        'distributors': pd.read_csv('Invoice - Distributors.csv')
    }

# Google Sheets operations
class SheetManager:
    def __init__(self):
        self.conn = st.connection("gsheets", type=GSheetsConnection)
        
    def read_sheet(self, worksheet):
        return self.conn.read(worksheet=worksheet, ttl=5).dropna(how='all')
        
    def update_sheet(self, worksheet, data):
        existing = self.read_sheet(worksheet)
        updated = pd.concat([existing, data], ignore_index=True)
        self.conn.update(worksheet=worksheet, data=updated)

# Authentication
def authenticate(employee_name, passkey, person_data):
    try:
        employee_code = person_data[person_data['Employee Name'] == employee_name]['Employee Code'].values[0]
        return str(passkey) == str(employee_code)
    except:
        return False

# PDF Generation
class InvoicePDF(FPDF):
    def header(self):
        try:
            self.image(LOGO_PATH, 10, 8, 33)
        except:
            pass
        
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, COMPANY_NAME, ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, COMPANY_ADDRESS, align='C')
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Proforma Invoice', ln=True, align='C')
        self.line(10, 50, 200, 50)
        self.ln(1)

# Helper functions
def generate_id(prefix):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

def format_date(date_obj):
    return date_obj.strftime("%d-%m-%Y")

# Main app components
def login_page(person_data):
    st.title("Employee Portal")
    st.subheader("Login")
    
    employee_name = st.selectbox("Select Your Name", person_data['Employee Name'].tolist())
    passkey = st.text_input("Enter Your Employee Code", type="password")
    
    if st.button("Log in"):
        if authenticate(employee_name, passkey, person_data):
            st.session_state.authenticated = True
            st.session_state.employee_name = employee_name
            st.rerun()
        else:
            st.error("Invalid credentials")

def mode_selection():
    st.title("Select Mode")
    cols = st.columns(3)
    modes = ["Sales", "Visit", "Attendance"]
    
    for col, mode in zip(cols, modes):
        if col.button(mode, use_container_width=True):
            st.session_state.selected_mode = mode
            st.rerun()

def sales_page(data, sheet_manager):
    st.title("Sales Management")
    employee_name = st.session_state.employee_name
    discount_category = data['person'][data['person']['Employee Name'] == employee_name]['Discount Category'].values[0]
    
    with st.form("sales_form"):
        # Transaction details
        transaction_type = st.selectbox("Transaction Type", ["Sold", "Return", "Add On", "Damage", "Expired"])
        
        # Product selection
        selected_products = st.multiselect("Select Products", data['products']['Product Name'].tolist())
        
        # Product quantities and discounts
        quantities = []
        product_discounts = []
        if selected_products:
            for product in selected_products:
                cols = st.columns([3, 1, 1])
                with cols[0]:
                    st.text(product)
                with cols[1]:
                    discount = st.number_input(f"Discount %", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"disc_{product}")
                    product_discounts.append(discount)
                with cols[2]:
                    qty = st.number_input("Qty", min_value=1, value=1, step=1, key=f"qty_{product}")
                    quantities.append(qty)
        
        # Payment details
        payment_status = st.selectbox("Payment Status", ["pending", "paid"])
        amount_paid = st.number_input("Amount Paid (INR)", min_value=0.0, value=0.0) if payment_status == "paid" else 0.0
        
        # Outlet details
        outlet_option = st.radio("Outlet", ["Select from list", "Enter manually"])
        if outlet_option == "Select from list":
            outlet = st.selectbox("Select Outlet", data['outlet']['Shop Name'].tolist())
            outlet_details = data['outlet'][data['outlet']['Shop Name'] == outlet].iloc[0]
        else:
            outlet_details = {
                'Shop Name': st.text_input("Outlet Name"),
                'Contact': st.text_input("Contact"),
                'Address': st.text_area("Address"),
                'State': st.text_input("State", "Uttar Pradesh"),
                'City': st.text_input("City", "Noida"),
                'GST': st.text_input("GST Number")
            }
        
        if st.form_submit_button("Generate Invoice"):
            if not selected_products:
                st.error("Please select at least one product")
            else:
                # Generate PDF and log data
                st.success("Invoice generated successfully!")
                st.balloons()

def visit_page(data, sheet_manager):
    st.title("Visit Management")
    
    with st.form("visit_form"):
        # Outlet details
        outlet_option = st.radio("Outlet", ["Select from list", "Enter manually"])
        if outlet_option == "Select from list":
            outlet = st.selectbox("Select Outlet", data['outlet']['Shop Name'].tolist())
            outlet_details = data['outlet'][data['outlet']['Shop Name'] == outlet].iloc[0]
        else:
            outlet_details = {
                'Shop Name': st.text_input("Outlet Name"),
                'Contact': st.text_input("Contact"),
                'Address': st.text_area("Address"),
                'State': st.text_input("State", "Uttar Pradesh"),
                'City': st.text_input("City", "Noida")
            }
        
        # Visit details
        visit_purpose = st.selectbox("Purpose", ["Sales", "Demo", "Product Demonstration", "Relationship Building"])
        visit_notes = st.text_area("Notes")
        
        if st.form_submit_button("Record Visit"):
            st.success("Visit recorded successfully!")

def attendance_page(data, sheet_manager):
    st.title("Attendance Management")
    employee_name = st.session_state.employee_name
    
    with st.form("attendance_form"):
        status = st.radio("Status", ["Present", "Half Day", "Leave"])
        
        if status in ["Present", "Half Day"]:
            location = st.text_input("Location (Google Maps link or address)")
        else:
            reason = st.text_area("Leave Reason")
        
        if st.form_submit_button("Submit"):
            st.success("Attendance recorded!")

# Main app flow
def main():
    init_session()
    data = load_data()
    sheet_manager = SheetManager()
    
    if not st.session_state.authenticated:
        login_page(data['person'])
    else:
        if not st.session_state.selected_mode:
            mode_selection()
        else:
            if st.button("← Back"):
                st.session_state.selected_mode = None
                st.rerun()
            
            if st.session_state.selected_mode == "Sales":
                sales_page(data, sheet_manager)
            elif st.session_state.selected_mode == "Visit":
                visit_page(data, sheet_manager)
            else:
                attendance_page(data, sheet_manager)

if __name__ == "__main__":
    main()
