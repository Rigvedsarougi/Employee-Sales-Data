import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from fpdf import FPDF
from datetime import datetime, time
import os
import uuid
from PIL import Image

# Hide Streamlit footer and GitHub/Fork icons
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
st.title("Biolume: Sales & Visit Management System")

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
    "Total Price",
    "GST Rate",
    "CGST Amount",
    "SGST Amount",
    "Grand Total",
    "Overall Discount (%)",
    "Amount Discount (INR)",
    "Discounted Price",
    "Payment Status",
    "Amount Paid",
    "Payment Receipt Path",
    "Employee Selfie Path",
    "Invoice PDF Path"
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
    "Visit Status"
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
        # Read existing data
        existing_data = conn.read(worksheet="Attendance", usecols=list(range(len(ATTENDANCE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how="all")
        
        # Combine with new data
        updated_data = pd.concat([existing_data, attendance_data], ignore_index=True)
        
        # Update the sheet
        conn.update(worksheet="Attendance", data=updated_data)
        return True, None
    except Exception as e:
        return False, str(e)

def generate_invoice(customer_name, gst_number, contact_number, address, state, city, selected_products, quantities, 
                    discount_category, employee_name, overall_discount, amount_discount, 
                    payment_status, amount_paid, employee_selfie_path, payment_receipt_path, invoice_number,
                    transaction_type, distributor_firm_name="", distributor_id="", distributor_contact_person="",
                    distributor_contact_number="", distributor_email="", distributor_territory=""):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    current_date = datetime.now().strftime("%d-%m-%Y")

    # Transaction Type
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Transaction Type: {transaction_type.upper()}", ln=True)
    
    # Sales Person
    pdf.ln(0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Sales Person: {employee_name}", ln=True, align='L')
    
    # Distributor details if available
    if distributor_firm_name:
        pdf.cell(0, 10, f"Distributor: {distributor_firm_name} ({distributor_id})", ln=True, align='L')
        pdf.cell(0, 10, f"Contact: {distributor_contact_person} | {distributor_contact_number}", ln=True, align='L')
        pdf.cell(0, 10, f"Territory: {distributor_territory}", ln=True, align='L')
    
    pdf.ln(5)

    # Customer details
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Bill To:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 6, f"Name: {customer_name}")
    pdf.cell(90, 6, f"Date: {current_date}", ln=True, align='R')
    pdf.cell(100, 6, f"GSTIN/UN: {gst_number}")
    pdf.cell(90, 6, f"Contact: {contact_number}", ln=True, align='R')
    pdf.cell(100, 6, "Address: ", ln=True)
    pdf.multi_cell(0, 6, address)
    pdf.ln(1)
    
    # Invoice number
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Invoice Number: {invoice_number}", ln=True)
    pdf.ln(5)
    
    # Table header
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 10, "S.No", border=1, align='C', fill=True)
    pdf.cell(70, 10, "Product Name", border=1, align='C', fill=True)
    pdf.cell(20, 10, "HSN/SAC", border=1, align='C', fill=True)
    pdf.cell(20, 10, "GST Rate", border=1, align='C', fill=True)
    pdf.cell(20, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(25, 10, "Rate (INR)", border=1, align='C', fill=True)
    pdf.cell(25, 10, "Amount (INR)", border=1, align='C', fill=True)
    pdf.ln()

    # Table rows
    pdf.set_font("Arial", '', 10)
    sales_data = []
    tax_rate = 0.18  # 18% GST
    
    # Calculate subtotal before any discounts
    subtotal = 0
    for idx, (product, quantity) in enumerate(zip(selected_products, quantities)):
        product_data = Products[Products['Product Name'] == product].iloc[0]
        
        if discount_category in product_data:
            unit_price = float(product_data[discount_category])
        else:
            unit_price = float(product_data['Price'])
        
        item_total = unit_price * quantity
        subtotal += item_total
        
        pdf.cell(10, 8, str(idx + 1), border=1)
        pdf.cell(70, 8, product, border=1)
        pdf.cell(20, 8, "3304", border=1, align='C')
        pdf.cell(20, 8, "18%", border=1, align='C')
        pdf.cell(20, 8, str(quantity), border=1, align='C')
        pdf.cell(25, 8, f"{unit_price:.2f}", border=1, align='R')
        pdf.cell(25, 8, f"{item_total:.2f}", border=1, align='R')
        pdf.ln()

    # Apply percentage discount
    if overall_discount > 0:
        discount_amount = subtotal * (overall_discount / 100)
        discounted_subtotal = subtotal - discount_amount
    else:
        discounted_subtotal = subtotal
    
    # Apply amount discount
    taxable_amount = max(discounted_subtotal - amount_discount, 0)
    
    # Calculate taxes
    tax_amount = taxable_amount * tax_rate
    cgst_amount = tax_amount / 2
    sgst_amount = tax_amount / 2
    grand_total = taxable_amount + tax_amount

    # Display totals
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(160, 10, "Subtotal", border=0, align='R')
    pdf.cell(30, 10, f"{subtotal:.2f}", border=1, align='R')
    pdf.ln()
    
    if overall_discount > 0:
        pdf.cell(160, 10, f"Discount ({overall_discount}%)", border=0, align='R')
        pdf.cell(30, 10, f"-{discount_amount:.2f}", border=1, align='R')
        pdf.ln()
    
    if amount_discount > 0:
        pdf.cell(160, 10, "Amount Discount", border=0, align='R')
        pdf.cell(30, 10, f"-{amount_discount:.2f}", border=1, align='R')
        pdf.ln()
    
    pdf.cell(160, 10, "Taxable Amount", border=0, align='R')
    pdf.cell(30, 10, f"{taxable_amount:.2f}", border=1, align='R')
    pdf.ln()
    
    pdf.cell(160, 10, "CGST (9%)", border=0, align='R')
    pdf.cell(30, 10, f"{cgst_amount:.2f}", border=1, align='R')
    pdf.ln()
    
    pdf.cell(160, 10, "SGST (9%)", border=0, align='R')
    pdf.cell(30, 10, f"{sgst_amount:.2f}", border=1, align='R')
    pdf.ln()
    
    pdf.cell(160, 10, "Grand Total", border=0, align='R')
    pdf.cell(30, 10, f"{grand_total:.2f} INR", border=1, align='R', fill=True)
    pdf.ln(10)
    
    # Payment Status
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Payment Status: {payment_status.upper()}", ln=True)
    if payment_status in ["paid", "partial paid"]:
        pdf.cell(0, 10, f"Amount Paid: {amount_paid} INR", ln=True)
    pdf.ln(10)
    
    # Details
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Details:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 5, bank_details)
    
    # Attachments
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Attachments", ln=True)
    pdf.ln(10)
    
    if employee_selfie_path:
        try:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Employee Selfie:", ln=True)
            img = Image.open(employee_selfie_path)
            img.thumbnail((150, 150))
            temp_path = f"temp_{os.path.basename(employee_selfie_path)}"
            img.save(temp_path)
            pdf.image(temp_path, x=10, y=pdf.get_y(), w=50)
            pdf.ln(60)
            os.remove(temp_path)
        except Exception as e:
            st.error(f"Error adding employee selfie: {e}")
    
    if payment_receipt_path and payment_status in ["paid", "partial paid"]:
        try:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Payment Receipt:", ln=True)
            img = Image.open(payment_receipt_path)
            img.thumbnail((150, 150))
            temp_path = f"temp_{os.path.basename(payment_receipt_path)}"
            img.save(temp_path)
            pdf.image(temp_path, x=10, y=pdf.get_y(), w=50)
            pdf.ln(60)
            os.remove(temp_path)
        except Exception as e:
            st.error(f"Error adding payment receipt: {e}")

    # Prepare sales data for logging
    for idx, (product, quantity) in enumerate(zip(selected_products, quantities)):
        product_data = Products[Products['Product Name'] == product].iloc[0]
        
        if discount_category in product_data:
            unit_price = float(product_data[discount_category])
        else:
            unit_price = float(product_data['Price'])
            
        item_total = unit_price * quantity
        item_taxable = item_total * (1 - overall_discount / 100) - (amount_discount * (item_total / subtotal))
        item_tax = item_taxable * tax_rate
        
        sales_data.append({
            "Invoice Number": invoice_number,
            "Invoice Date": current_date,
            "Employee Name": employee_name,
            "Employee Code": Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0],
            "Designation": Person[Person['Employee Name'] == employee_name]['Designation'].values[0],
            "Discount Category": discount_category,
            "Transaction Type": transaction_type,
            "Outlet Name": customer_name,
            "Outlet Contact": contact_number,
            "Outlet Address": address,
            "Outlet State": state,
            "Outlet City": city,
            "Distributor Firm Name": distributor_firm_name,
            "Distributor ID": distributor_id,
            "Distributor Contact Person": distributor_contact_person,
            "Distributor Contact Number": distributor_contact_number,
            "Distributor Email": distributor_email,
            "Distributor Territory": distributor_territory,
            "Product ID": product_data['Product ID'],
            "Product Name": product,
            "Product Category": product_data['Product Category'],
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Total Price": item_total,
            "GST Rate": "18%",
            "CGST Amount": item_tax / 2,
            "SGST Amount": item_tax / 2,
            "Grand Total": item_taxable + item_tax,
            "Overall Discount (%)": overall_discount,
            "Amount Discount (INR)": amount_discount * (item_total / subtotal),
            "Discounted Price": unit_price * (1 - overall_discount / 100),
            "Payment Status": payment_status,
            "Amount Paid": amount_paid if payment_status in ["paid", "partial paid"] else 0,
            "Payment Receipt Path": payment_receipt_path if payment_status in ["paid", "partial paid"] else "",
            "Employee Selfie Path": employee_selfie_path,
            "Invoice PDF Path": f"invoices/{invoice_number}.pdf"
        })

    # Save the PDF
    pdf_path = f"invoices/{invoice_number}.pdf"
    pdf.output(pdf_path)
    
    # Log sales data to Google Sheets
    sales_df = pd.DataFrame(sales_data)
    log_sales_to_gsheet(conn, sales_df)

    return pdf, pdf_path

def record_visit(employee_name, outlet_name, outlet_contact, outlet_address, outlet_state, outlet_city, 
                 visit_purpose, visit_notes, visit_selfie_path, entry_time, exit_time):
    visit_id = generate_visit_id()
    visit_date = datetime.now().strftime("%d-%m-%Y")
    
    duration = (exit_time - entry_time).total_seconds() / 60
    
    visit_data = {
        "Visit ID": visit_id,
        "Employee Name": employee_name,
        "Employee Code": Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0],
        "Designation": Person[Person['Employee Name'] == employee_name]['Designation'].values[0],
        "Outlet Name": outlet_name,
        "Outlet Contact": outlet_contact,
        "Outlet Address": outlet_address,
        "Outlet State": outlet_state,
        "Outlet City": outlet_city,
        "Visit Date": visit_date,
        "Entry Time": entry_time.strftime("%H:%M:%S"),
        "Exit Time": exit_time.strftime("%H:%M:%S"),
        "Visit Duration (minutes)": round(duration, 2),
        "Visit Purpose": visit_purpose,
        "Visit Notes": visit_notes,
        "Visit Selfie Path": visit_selfie_path,
        "Visit Status": "completed"
    }
    
    visit_df = pd.DataFrame([visit_data])
    log_visit_to_gsheet(conn, visit_df)
    
    return visit_id

def record_attendance(employee_name, status, location_link="", leave_reason=""):
    try:
        # Get employee details
        employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
        designation = Person[Person['Employee Name'] == employee_name]['Designation'].values[0]
        current_date = datetime.now().strftime("%d-%m-%Y")
        current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        check_in_time = datetime.now().strftime("%H:%M:%S")
        
        # Generate attendance ID
        attendance_id = generate_attendance_id()
        
        # Create attendance record
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
        
        # Convert to DataFrame
        attendance_df = pd.DataFrame([attendance_data])
        
        # Log to Google Sheets
        success, error = log_attendance_to_gsheet(conn, attendance_df)
        
        if success:
            return attendance_id, None
        else:
            return None, error
            
    except Exception as e:
        return None, f"Error creating attendance record: {str(e)}"

def check_existing_attendance(employee_name):
    try:
        # Read existing attendance data
        existing_data = conn.read(worksheet="Attendance", usecols=list(range(len(ATTENDANCE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how="all")
        
        if existing_data.empty:
            return False
        
        current_date = datetime.now().strftime("%d-%m-%Y")
        employee_code = Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0]
        
        # Check if attendance exists for today
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

def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = None
    if 'employee_name' not in st.session_state:
        st.session_state.employee_name = None

    if not st.session_state.authenticated:
        st.title("Employee Authentication")
        
        mode = st.radio("Select Mode", ["Sales", "Visit", "Attendance"], key="mode_selection")
        employee_names = Person['Employee Name'].tolist()
        employee_name = st.selectbox("Select Your Name", employee_names, key="employee_select")
        passkey = st.text_input("Enter Your Employee Code", type="password", key="passkey_input")
        
        if st.button("Log in"):
            if authenticate_employee(employee_name, passkey):
                st.session_state.authenticated = True
                st.session_state.selected_mode = mode
                st.session_state.employee_name = employee_name
                st.rerun()
            else:
                st.error("Invalid Employee Code. Please try again.")
    else:
        if st.session_state.selected_mode == "Sales":
            sales_page()
        elif st.session_state.selected_mode == "Visit":
            visit_page()
        else:
            attendance_page()

def sales_page():
    st.title("Sales Management")
    selected_employee = st.session_state.employee_name
    
    # Add tabs for new sale and sales history
    tab1, tab2 = st.tabs(["New Sale", "Sales History"])
    
    with tab1:
        st.subheader("Employee Verification")
        employee_selfie = st.file_uploader("Upload Employee Selfie", type=["jpg", "jpeg", "png"])

        discount_category = Person[Person['Employee Name'] == selected_employee]['Discount Category'].values[0]

        st.subheader("Transaction Details")
        transaction_type = st.selectbox("Transaction Type", ["Sold", "Return", "Add On", "Damage", "Expired"])

        st.subheader("Product Details")
        product_names = Products['Product Name'].tolist()
        selected_products = st.multiselect("Select Products", product_names)

        quantities = []
        if selected_products:
            for product in selected_products:
                qty = st.number_input(f"Quantity for {product}", min_value=1, value=1, step=1)
                quantities.append(qty)

        st.subheader("Discount Options")
        col1, col2 = st.columns(2)
        with col1:
            overall_discount = st.number_input("Percentage Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
        with col2:
            amount_discount = st.number_input("Amount Discount (INR)", min_value=0.0, value=0.0, step=1.0)

        st.subheader("Payment Details")
        payment_status = st.selectbox("Payment Status", ["pending", "paid", "partial paid"])

        amount_paid = 0.0
        payment_receipt = None

        if payment_status == "partial paid":
            amount_paid = st.number_input("Amount Paid (INR)", min_value=0.0, value=0.0, step=1.0)
            payment_receipt = st.file_uploader("Upload Payment Receipt", type=["jpg", "jpeg", "png", "pdf"])
        elif payment_status == "paid":
            amount_paid = st.number_input("Amount Paid (INR)", min_value=0.0, value=0.0, step=1.0)
            payment_receipt = st.file_uploader("Upload Payment Receipt", type=["jpg", "jpeg", "png", "pdf"])

        st.subheader("Distributor Details")
        distributor_option = st.radio("Distributor Selection", ["Select from list", "None"])
        
        distributor_firm_name = ""
        distributor_id = ""
        distributor_contact_person = ""
        distributor_contact_number = ""
        distributor_email = ""
        distributor_territory = ""
        
        if distributor_option == "Select from list":
            distributor_names = Distributors['Firm Name'].tolist()
            selected_distributor = st.selectbox("Select Distributor", distributor_names)
            distributor_details = Distributors[Distributors['Firm Name'] == selected_distributor].iloc[0]
            
            distributor_firm_name = selected_distributor
            distributor_id = distributor_details['Distributor ID']
            distributor_contact_person = distributor_details['Contact Person']
            distributor_contact_number = distributor_details['Contact Number']
            distributor_email = distributor_details['Email ID']
            distributor_territory = distributor_details['Territory']
            
            st.text_input("Distributor ID", value=distributor_id, disabled=True)
            st.text_input("Contact Person", value=distributor_contact_person, disabled=True)
            st.text_input("Contact Number", value=distributor_contact_number, disabled=True)
            st.text_input("Email", value=distributor_email, disabled=True)
            st.text_input("Territory", value=distributor_territory, disabled=True)

        st.subheader("Outlet Details")
        outlet_option = st.radio("Outlet Selection", ["Select from list", "Enter manually"])
        
        if outlet_option == "Select from list":
            outlet_names = Outlet['Shop Name'].tolist()
            selected_outlet = st.selectbox("Select Outlet", outlet_names)
            outlet_details = Outlet[Outlet['Shop Name'] == selected_outlet].iloc[0]
            
            customer_name = selected_outlet
            gst_number = outlet_details['GST']
            contact_number = outlet_details['Contact']
            address = outlet_details['Address']
            state = outlet_details['State']
            city = outlet_details['City']
        else:
            customer_name = st.text_input("Outlet Name")
            gst_number = st.text_input("GST Number")
            contact_number = st.text_input("Contact Number")
            address = st.text_area("Address")
            state = st.text_input("State", "Uttar Pradesh")
            city = st.text_input("City", "Noida")

        if st.button("Generate Invoice"):
            if selected_products and customer_name:
                invoice_number = generate_invoice_number()
                
                employee_selfie_path = save_uploaded_file(employee_selfie, "employee_selfies") if employee_selfie else None
                payment_receipt_path = save_uploaded_file(payment_receipt, "payment_receipts") if payment_receipt else None
                
                pdf, pdf_path = generate_invoice(
                    customer_name, gst_number, contact_number, address, state, city,
                    selected_products, quantities, discount_category, 
                    selected_employee, overall_discount, amount_discount,
                    payment_status, amount_paid, employee_selfie_path, 
                    payment_receipt_path, invoice_number, transaction_type,
                    distributor_firm_name, distributor_id, distributor_contact_person,
                    distributor_contact_number, distributor_email, distributor_territory
                )
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download Invoice", 
                        f, 
                        file_name=f"{invoice_number}.pdf",
                        mime="application/pdf"
                    )
                
                st.success(f"Invoice {invoice_number} generated successfully!")
            else:
                st.error("Please fill all required fields and select products.")
    
    with tab2:
        st.subheader("Lookup Previous Sales")
        col1, col2, col3 = st.columns(3)
        with col1:
            invoice_number_search = st.text_input("Invoice Number")
        with col2:
            invoice_date_search = st.date_input("Invoice Date")
        with col3:
            outlet_name_search = st.text_input("Outlet Name")
            
        if st.button("Search Sales"):
            try:
                sales_data = conn.read(worksheet="Sales", usecols=list(range(len(SALES_SHEET_COLUMNS))), ttl=5)
                sales_data = sales_data.dropna(how="all")
                
                # Filter by employee first
                employee_code = Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0]
                filtered_data = sales_data[sales_data['Employee Code'] == employee_code]
                
                # Apply additional filters if provided
                if invoice_number_search:
                    filtered_data = filtered_data[filtered_data['Invoice Number'].str.contains(invoice_number_search, case=False)]
                if invoice_date_search:
                    date_str = invoice_date_search.strftime("%d-%m-%Y")
                    filtered_data = filtered_data[filtered_data['Invoice Date'] == date_str]
                if outlet_name_search:
                    filtered_data = filtered_data[filtered_data['Outlet Name'].str.contains(outlet_name_search, case=False)]
                
                if not filtered_data.empty:
                    st.dataframe(filtered_data[['Invoice Number', 'Invoice Date', 'Outlet Name', 'Product Name', 'Quantity', 'Grand Total']])
                    
                    # Option to download as CSV
                    csv = filtered_data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download as CSV",
                        csv,
                        "sales_history.csv",
                        "text/csv",
                        key='download-csv'
                    )
                else:
                    st.warning("No matching sales records found")
            except Exception as e:
                st.error(f"Error retrieving sales data: {e}")

def visit_page():
    st.title("Visit Management")
    selected_employee = st.session_state.employee_name

    st.subheader("Outlet Details")
    outlet_option = st.radio("Outlet Selection", ["Select from list", "Enter manually"])
    
    if outlet_option == "Select from list":
        outlet_names = Outlet['Shop Name'].tolist()
        selected_outlet = st.selectbox("Select Outlet", outlet_names)
        outlet_details = Outlet[Outlet['Shop Name'] == selected_outlet].iloc[0]
        
        outlet_name = selected_outlet
        outlet_contact = outlet_details['Contact']
        outlet_address = outlet_details['Address']
        outlet_state = outlet_details['State']
        outlet_city = outlet_details['City']
    else:
        outlet_name = st.text_input("Outlet Name")
        outlet_contact = st.text_input("Outlet Contact")
        outlet_address = st.text_area("Outlet Address")
        outlet_state = st.text_input("Outlet State", "Uttar Pradesh")
        outlet_city = st.text_input("Outlet City", "Noida")

    st.subheader("Visit Details")
    visit_purpose = st.selectbox("Visit Purpose", ["Sales", "Product Demonstration", "Relationship Building", "Issue Resolution", "Other"])
    visit_notes = st.text_area("Visit Notes")
    
    st.subheader("Visit Verification")
    visit_selfie = st.file_uploader("Upload Visit Selfie", type=["jpg", "jpeg", "png"])

    st.subheader("Time Tracking")
    col1, col2 = st.columns(2)
    with col1:
        # Use None as default to force user selection
        entry_time = st.time_input("Entry Time", value=None, key="entry_time")
    with col2:
        # Use None as default to force user selection
        exit_time = st.time_input("Exit Time", value=None, key="exit_time")

    if st.button("Record Visit"):
        if outlet_name:
            today = datetime.now().date()
            
            # Set default times if user didn't select
            if entry_time is None:
                entry_time = datetime.now().time()
            if exit_time is None:
                exit_time = datetime.now().time()
                
            entry_datetime = datetime.combine(today, entry_time)
            exit_datetime = datetime.combine(today, exit_time)
            
            visit_selfie_path = save_uploaded_file(visit_selfie, "visit_selfies") if visit_selfie else None
            
            visit_id = record_visit(
                selected_employee, outlet_name, outlet_contact, outlet_address,
                outlet_state, outlet_city, visit_purpose, visit_notes, 
                visit_selfie_path, entry_datetime, exit_datetime
            )
            
            st.success(f"Visit {visit_id} recorded successfully!")
        else:
            st.error("Please fill all required fields.")

def attendance_page():
    st.title("Attendance Management")
    selected_employee = st.session_state.employee_name
    
    # Check if attendance already marked for today
    if check_existing_attendance(selected_employee):
        st.warning("You have already marked your attendance for today.")
        return
    
    st.subheader("Attendance Status")
    status = st.radio("Select Status", ["Present", "Leave"], index=0)
    
    if status == "Present":
        st.subheader("Location Verification")
        live_location = st.text_input("Enter your current location (Google Maps link or address)", 
                                    help="Please share your live location for verification")
        
        if st.button("Mark Attendance"):
            if not live_location:
                st.error("Please provide your location")
            else:
                with st.spinner("Recording attendance..."):
                    attendance_id, error = record_attendance(
                        selected_employee,
                        "Present",
                        location_link=live_location
                    )
                    
                    if error:
                        st.error(f"Failed to record attendance: {error}")
                    else:
                        st.success(f"Attendance recorded successfully! ID: {attendance_id}")
                        st.balloons()
    
    else:  # Leave status
        st.subheader("Leave Details")
        leave_types = ["Sick Leave", "Personal Leave", "Vacation", "Other"]
        leave_type = st.selectbox("Leave Type", leave_types)
        leave_reason = st.text_area("Reason for Leave", 
                                   placeholder="Please provide details about your leave")
        
        if st.button("Submit Leave Request"):
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

if __name__ == "__main__":
    main()
