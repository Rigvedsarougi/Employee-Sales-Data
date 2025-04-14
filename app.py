import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import math
from fpdf import FPDF
from datetime import datetime
import os
import uuid
from PIL import Image

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
    "Outlet Name",
    "Outlet Contact",
    "Outlet Address",
    "Outlet State",
    "Outlet City",
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

# Establishing a Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Load data
Products = pd.read_csv('Invoice - Products.csv')
Outlet = pd.read_csv('Invoice - Outlet.csv')
Person = pd.read_csv('Invoice - Person.csv')

# Company Details
company_name = "BIOLUME SKIN SCIENCE PRIVATE LIMITED"
company_address = """Ground Floor Rampal Awana Complex,
Rampal Awana Complex, Indra Market,
Sector-27, Atta, Noida, Gautam Buddha Nagar,
Uttar Pradesh 201301
GSTIN/UIN: 09AALCB9426H1ZA
State Name: Uttar Pradesh, Code: 09
"""
company_logo = 'ALLGEN TRADING logo.png'  # Ensure the logo file is in the same directory
bank_details = """
Disclaimer: This Proforma Invoice is for estimation purposes only and is not a demand for payment. 
Prices, taxes, and availability are subject to change. Final billing may vary. 
Goods/services will be delivered only after confirmation and payment. No legal obligation is created by this document.
"""

# Create directories for storing uploads if they don't exist
os.makedirs("employee_selfies", exist_ok=True)
os.makedirs("payment_receipts", exist_ok=True)
os.makedirs("invoices", exist_ok=True)
os.makedirs("visit_selfies", exist_ok=True)

# Custom PDF class
class PDF(FPDF):
    def header(self):
        # Add company logo
        if company_logo:
            self.image(company_logo, 10, 8, 33)
        
        # Company name and address
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, company_name, ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, company_address, align='C')
        
        # Invoice title
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Proforma Invoice', ln=True, align='C')
        self.line(10, 50, 200, 50)  # Horizontal line
        self.ln(1)

# Function to generate unique invoice number
def generate_invoice_number():
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

# Function to generate unique visit ID
def generate_visit_id():
    return f"VISIT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

# Function to save uploaded file
def save_uploaded_file(uploaded_file, folder):
    if uploaded_file is not None:
        file_ext = os.path.splitext(uploaded_file.name)[1]
        file_path = os.path.join(folder, f"{str(uuid.uuid4())}{file_ext}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

# Function to log sales data to Google Sheets
def log_sales_to_gsheet(conn, sales_data):
    try:
        # Fetch existing data
        existing_sales_data = conn.read(worksheet="Sales", usecols=list(range(len(SALES_SHEET_COLUMNS))), ttl=5)
        existing_sales_data = existing_sales_data.dropna(how="all")
        
        # Combine existing data with new data
        updated_sales_data = pd.concat([existing_sales_data, sales_data], ignore_index=True)
        
        # Update the Google Sheet
        conn.update(worksheet="Sales", data=updated_sales_data)
        st.success("Sales data successfully logged to Google Sheets!")
    except Exception as e:
        st.error(f"Error logging sales data: {e}")

# Function to log visit data to Google Sheets
def log_visit_to_gsheet(conn, visit_data):
    try:
        # Fetch existing data
        existing_visit_data = conn.read(worksheet="Visits", usecols=list(range(len(VISIT_SHEET_COLUMNS))), ttl=5)
        existing_visit_data = existing_visit_data.dropna(how="all")
        
        # Combine existing data with new data
        updated_visit_data = pd.concat([existing_visit_data, visit_data], ignore_index=True)
        
        # Update the Google Sheet
        conn.update(worksheet="Visits", data=updated_visit_data)
        st.success("Visit data successfully logged to Google Sheets!")
    except Exception as e:
        st.error(f"Error logging visit data: {e}")

# Generate Invoice
def generate_invoice(customer_name, gst_number, contact_number, address, selected_products, quantities, 
                    discount_category, employee_name, overall_discount, amount_discount, 
                    payment_status, amount_paid, employee_selfie_path, payment_receipt_path, invoice_number):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    current_date = datetime.now().strftime("%d-%m-%Y")

    # Sales Person
    pdf.ln(0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Sales Person: {employee_name}", ln=True, align='L')
    pdf.ln(0)

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
    total_price = 0
    sales_data = []
    for idx, (product, quantity) in enumerate(zip(selected_products, quantities)):
        product_data = Products[Products['Product Name'] == product].iloc[0]

        if discount_category in product_data:
            unit_price = float(product_data[discount_category])  # Use discount category price
        else:
            unit_price = float(product_data['Price'])

        # Apply overall discount
        discounted_price = unit_price * (1 - overall_discount / 100)
        item_total_price = discounted_price * quantity

        pdf.cell(10, 8, str(idx + 1), border=1)
        pdf.cell(70, 8, product, border=1)
        pdf.cell(20, 8, "3304", border=1, align='C')
        pdf.cell(20, 8, "18%", border=1, align='C')
        pdf.cell(20, 8, str(quantity), border=1, align='C')
        pdf.cell(25, 8, f"{discounted_price:.2f}", border=1, align='R')
        pdf.cell(25, 8, f"{item_total_price:.2f}", border=1, align='R')
        total_price += item_total_price
        pdf.ln()

    # Apply amount discount if any
    if amount_discount > 0:
        total_price -= amount_discount

    # Tax and Grand Total
    pdf.ln(10)
    tax_rate = 0.18
    tax_amount = total_price * tax_rate
    grand_total = math.ceil(total_price + tax_amount)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(160, 10, "Subtotal", border=0, align='R')
    pdf.cell(30, 10, f"{total_price + amount_discount:.2f}", border=1, align='R')
    pdf.ln()
    
    if amount_discount > 0:
        pdf.cell(160, 10, "Amount Discount", border=0, align='R')
        pdf.cell(30, 10, f"-{amount_discount:.2f}", border=1, align='R')
        pdf.ln()
    
    pdf.cell(160, 10, "Taxable Amount", border=0, align='R')
    pdf.cell(30, 10, f"{total_price:.2f}", border=1, align='R')
    pdf.ln()
    
    pdf.cell(160, 10, "CGST (9%)", border=0, align='R')
    pdf.cell(30, 10, f"{tax_amount / 2:.2f}", border=1, align='R')
    pdf.ln()
    
    pdf.cell(160, 10, "SGST (9%)", border=0, align='R')
    pdf.cell(30, 10, f"{tax_amount / 2:.2f}", border=1, align='R')
    pdf.ln()
    
    pdf.cell(160, 10, "Grand Total", border=0, align='R')
    pdf.cell(30, 10, f"{grand_total} INR", border=1, align='R', fill=True)
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
    
    # Add a new page for attachments
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Attachments", ln=True)
    pdf.ln(10)
    
    # Add employee selfie if available
    if employee_selfie_path:
        try:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Employee Selfie:", ln=True)
            # Resize image to fit PDF
            img = Image.open(employee_selfie_path)
            img.thumbnail((150, 150))
            temp_path = f"temp_{os.path.basename(employee_selfie_path)}"
            img.save(temp_path)
            pdf.image(temp_path, x=10, y=pdf.get_y(), w=50)
            pdf.ln(60)
            os.remove(temp_path)
        except Exception as e:
            st.error(f"Error adding employee selfie: {e}")
    
    # Add payment receipt if available
    if payment_receipt_path and payment_status in ["paid", "partial paid"]:
        try:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Payment Receipt:", ln=True)
            # Resize image to fit PDF
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
            
        discounted_price = unit_price * (1 - overall_discount / 100)
        item_total_price = discounted_price * quantity
        
        sales_data.append({
            "Invoice Number": invoice_number,
            "Invoice Date": current_date,
            "Employee Name": employee_name,
            "Employee Code": Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0],
            "Designation": Person[Person['Employee Name'] == employee_name]['Designation'].values[0],
            "Discount Category": discount_category,
            "Outlet Name": customer_name,
            "Outlet Contact": contact_number,
            "Outlet Address": address,
            "Outlet State": Outlet[Outlet['Shop Name'] == customer_name]['State'].values[0],
            "Outlet City": Outlet[Outlet['Shop Name'] == customer_name]['City'].values[0],
            "Product ID": product_data['Product ID'],
            "Product Name": product,
            "Product Category": product_data['Product Category'],
            "Quantity": quantity,
            "Unit Price": unit_price,
            "Total Price": item_total_price,
            "GST Rate": "18%",
            "CGST Amount": item_total_price * 0.09,
            "SGST Amount": item_total_price * 0.09,
            "Grand Total": item_total_price * 1.18,
            "Overall Discount (%)": overall_discount,
            "Amount Discount (INR)": amount_discount,
            "Discounted Price": discounted_price,
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

# Function to record visit
def record_visit(employee_name, outlet_name, visit_purpose, visit_notes, visit_selfie_path, entry_time, exit_time):
    visit_id = generate_visit_id()
    visit_date = datetime.now().strftime("%d-%m-%Y")
    
    # Calculate visit duration in minutes
    duration = (exit_time - entry_time).total_seconds() / 60
    
    # Get outlet details
    outlet_details = Outlet[Outlet['Shop Name'] == outlet_name].iloc[0]
    
    # Prepare visit data
    visit_data = {
        "Visit ID": visit_id,
        "Employee Name": employee_name,
        "Employee Code": Person[Person['Employee Name'] == employee_name]['Employee Code'].values[0],
        "Designation": Person[Person['Employee Name'] == employee_name]['Designation'].values[0],
        "Outlet Name": outlet_name,
        "Outlet Contact": outlet_details['Contact'],
        "Outlet Address": outlet_details['Address'],
        "Outlet State": outlet_details['State'],
        "Outlet City": outlet_details['City'],
        "Visit Date": visit_date,
        "Entry Time": entry_time.strftime("%H:%M:%S"),
        "Exit Time": exit_time.strftime("%H:%M:%S"),
        "Visit Duration (minutes)": round(duration, 2),
        "Visit Purpose": visit_purpose,
        "Visit Notes": visit_notes,
        "Visit Selfie Path": visit_selfie_path,
        "Visit Status": "completed"
    }
    
    # Log visit data to Google Sheets
    visit_df = pd.DataFrame([visit_data])
    log_visit_to_gsheet(conn, visit_df)
    
    return visit_id

# Main App
def main():
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio("Select Mode", ["Sales", "Visit"])

    if app_mode == "Sales":
        sales_page()
    else:
        visit_page()

# Sales Page
def sales_page():
    st.title("Sales Management")
    
    # Employee Selection
    st.subheader("Employee Details")
    employee_names = Person['Employee Name'].tolist()
    selected_employee = st.selectbox("Select Employee", employee_names)

    # Employee Selfie Upload
    st.subheader("Employee Verification")
    employee_selfie = st.file_uploader("Upload Employee Selfie", type=["jpg", "jpeg", "png"])

    # Fetch Discount Category
    discount_category = Person[Person['Employee Name'] == selected_employee]['Discount Category'].values[0]

    # Product Selection
    st.subheader("Product Details")
    product_names = Products['Product Name'].tolist()
    selected_products = st.multiselect("Select Products", product_names)

    # Input Quantities for Each Selected Product
    quantities = []
    if selected_products:
        for product in selected_products:
            qty = st.number_input(f"Quantity for {product}", min_value=1, value=1, step=1)
            quantities.append(qty)

    # Discount Options
    st.subheader("Discount Options")
    col1, col2 = st.columns(2)
    with col1:
        overall_discount = st.number_input("Percentage Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
    with col2:
        amount_discount = st.number_input("Amount Discount (INR)", min_value=0.0, value=0.0, step=1.0)

    # Payment Details
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

    # Outlet Selection
    st.subheader("Outlet Details")
    outlet_names = Outlet['Shop Name'].tolist()
    selected_outlet = st.selectbox("Select Outlet", outlet_names)

    # Fetch Outlet Details
    outlet_details = Outlet[Outlet['Shop Name'] == selected_outlet].iloc[0]

    # Generate Invoice button
    if st.button("Generate Invoice"):
        if selected_employee and selected_products and selected_outlet:
            # Generate invoice number
            invoice_number = generate_invoice_number()
            
            # Save uploaded files
            employee_selfie_path = save_uploaded_file(employee_selfie, "employee_selfies") if employee_selfie else None
            payment_receipt_path = save_uploaded_file(payment_receipt, "payment_receipts") if payment_receipt else None
            
            customer_name = selected_outlet
            gst_number = outlet_details['GST']
            contact_number = outlet_details['Contact']
            address = outlet_details['Address']

            pdf, pdf_path = generate_invoice(
                customer_name, gst_number, contact_number, address, 
                selected_products, quantities, discount_category, 
                selected_employee, overall_discount, amount_discount,
                payment_status, amount_paid, employee_selfie_path, 
                payment_receipt_path, invoice_number
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

# Visit Page
def visit_page():
    st.title("Visit Management")
    
    # Employee Selection
    st.subheader("Employee Details")
    employee_names = Person['Employee Name'].tolist()
    selected_employee = st.selectbox("Select Employee", employee_names)

    # Outlet Selection
    st.subheader("Outlet Details")
    outlet_names = Outlet['Shop Name'].tolist()
    selected_outlet = st.selectbox("Select Outlet", outlet_names)

    # Visit Details
    st.subheader("Visit Details")
    visit_purpose = st.selectbox("Visit Purpose", ["Sales", "Product Demonstration", "Relationship Building", "Issue Resolution", "Other"])
    visit_notes = st.text_area("Visit Notes")
    
    # Visit Selfie Upload
    st.subheader("Visit Verification")
    visit_selfie = st.file_uploader("Upload Visit Selfie", type=["jpg", "jpeg", "png"])

    # Time Tracking
    st.subheader("Time Tracking")
    col1, col2 = st.columns(2)
    with col1:
        entry_time = st.time_input("Entry Time", value=datetime.now().time())
    with col2:
        exit_time = st.time_input("Exit Time", value=datetime.now().time())

    # Record Visit button
    if st.button("Record Visit"):
        if selected_employee and selected_outlet:
            # Combine date and time
            today = datetime.now().date()
            entry_datetime = datetime.combine(today, entry_time)
            exit_datetime = datetime.combine(today, exit_time)
            
            # Save uploaded file
            visit_selfie_path = save_uploaded_file(visit_selfie, "visit_selfies") if visit_selfie else None
            
            visit_id = record_visit(
                selected_employee, selected_outlet, visit_purpose, 
                visit_notes, visit_selfie_path, entry_datetime, exit_datetime
            )
            
            st.success(f"Visit {visit_id} recorded successfully!")
        else:
            st.error("Please fill all required fields.")

if __name__ == "__main__":
    main()
