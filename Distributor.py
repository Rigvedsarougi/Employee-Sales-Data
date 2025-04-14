import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import math
from fpdf import FPDF
from datetime import datetime

# Display Title and Description
st.title("Biolume Skin Science Sales Management System")

# Constants
SALES_SHEET_COLUMNS = [
    "Invoice Date",
    "Firm Name",
    "Distributor ID",
    "Discount Category",
    "Point of Sales",
    "Type",
    "Territory",
    "State",
    "Email ID",
    "Contact Person",
    "Contact Number",
    "Address",
    "Sales Person",
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
    "Transaction Type"  # New column for Sold, Return, Add On, Damage, Expired
]

# Establishing a Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Load data
Products = pd.read_csv('Invoice - Products.csv')
Outlet = pd.read_csv('Invoice - Outlet.csv')
Distributor = pd.read_csv('Invoice - Distributors.csv')

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
Bank Name: Example Bank
Account Number: 1234567890
IFSC Code: EXMP0001234
Branch: Noida Branch
"""

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

# Generate Invoice
def generate_invoice(customer_name, gst_number, contact_number, address, selected_products, quantities, discount_category, firm_name, transaction_type):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    current_date = datetime.now().strftime("%d-%m-%Y")

    # Firm Name
    pdf.ln(0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Firm Name: {firm_name}", ln=True, align='L')
    pdf.ln(0)

    # Transaction Type (only for non-"Sold" transactions)
    if transaction_type != "Sold":
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, f"Transaction Type: {transaction_type}", ln=True, align='L')
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

        item_total_price = unit_price * quantity

        pdf.cell(10, 8, str(idx + 1), border=1)
        pdf.cell(70, 8, product, border=1)
        pdf.cell(20, 8, "3304", border=1, align='C')
        pdf.cell(20, 8, "18%", border=1, align='C')
        pdf.cell(20, 8, str(quantity), border=1, align='C')
        pdf.cell(25, 8, f"{unit_price:.2f}", border=1, align='R')
        pdf.cell(25, 8, f"{item_total_price:.2f}", border=1, align='R')
        total_price += item_total_price
        pdf.ln()

        # Prepare sales data for logging
        sales_data.append({
            "Invoice Date": current_date,
            "Firm Name": firm_name,
            "Distributor ID": Distributor[Distributor['Firm Name'] == firm_name]['Distributor ID'].values[0],
            "Discount Category": discount_category,
            "Point of Sales": Distributor[Distributor['Firm Name'] == firm_name]['Point of Sales'].values[0],
            "Type": Distributor[Distributor['Firm Name'] == firm_name]['Type'].values[0],
            "Territory": Distributor[Distributor['Firm Name'] == firm_name]['Territory'].values[0],
            "State": Distributor[Distributor['Firm Name'] == firm_name]['State'].values[0],
            "Email ID": Distributor[Distributor['Firm Name'] == firm_name]['Email ID'].values[0],
            "Contact Person": Distributor[Distributor['Firm Name'] == firm_name]['Contact Person'].values[0],
            "Contact Number": Distributor[Distributor['Firm Name'] == firm_name]['Contact Number'].values[0],
            "Address": Distributor[Distributor['Firm Name'] == firm_name]['Address'].values[0],
            "Sales Person": Distributor[Distributor['Firm Name'] == firm_name]['Sales Person'].values[0],
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
            "Transaction Type": transaction_type
        })

    # Tax and Grand Total (only for "Sold" transactions)
    if transaction_type == "Sold":
        pdf.ln(10)
        tax_rate = 0.18
        tax_amount = total_price * tax_rate
        grand_total = math.ceil(total_price + tax_amount)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(160, 10, "Subtotal", border=0, align='R')
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
        pdf.ln(20)
    else:
        # For non-"Sold" transactions, display a message
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Transaction Type: {transaction_type}", ln=True, align='C')
        pdf.ln(10)

    # Log sales data to Google Sheets
    sales_df = pd.DataFrame(sales_data)
    log_sales_to_gsheet(conn, sales_df)

    return pdf

# Streamlit UI
st.title(" ")

# Firm Name Selection
st.subheader("Distributor Details")
firm_names = Distributor['Firm Name'].tolist()
selected_firm = st.selectbox("Select Firm Name", firm_names)

# Passkey System
distributor_id = st.text_input("Enter Your Password")
done_button = st.button("Log In")

# Initialize session state for ID validation
if 'id_validated' not in st.session_state:
    st.session_state.id_validated = False

# Validate Distributor ID
if done_button:
    if distributor_id == Distributor[Distributor['Firm Name'] == selected_firm]['Distributor ID'].values[0]:
        st.session_state.id_validated = True
        st.success("Distributor ID verified!")
    else:
        st.error("Invalid Password")
        st.session_state.id_validated = False

# Only show the rest of the form if the ID is validated
if st.session_state.id_validated:
    # Fetch Distributor Details
    distributor_details = Distributor[Distributor['Firm Name'] == selected_firm].iloc[0]

    # Transaction Type
    transaction_type = st.selectbox("Transaction Type", ["Sold", "Return", "Add On", "Damage", "Expired"])

    # Product Selection
    st.subheader("Product Details")
    product_names = Products['Product Name'].tolist()

    # Create a dictionary to store quantities for each product
    quantities = {}

    # Display each product with a quantity input field
    for product in product_names:
        quantities[product] = st.number_input(f"Quantity for {product}", min_value=0, value=0, step=1)

    # Filter out products with zero quantity
    selected_products = [product for product, qty in quantities.items() if qty > 0]
    quantities = [quantities[product] for product in selected_products]

    # Outlet Selection
    st.subheader("Outlet Details")
    outlet_names = Outlet['Shop Name'].tolist()
    selected_outlet = st.selectbox("Select Outlet", outlet_names)

    # Fetch Outlet Details
    outlet_details = Outlet[Outlet['Shop Name'] == selected_outlet].iloc[0]

    # Generate Invoice button
    if st.button("Generate Invoice"):
        if selected_firm and selected_products and selected_outlet:
            customer_name = selected_outlet
            gst_number = outlet_details['GST']
            contact_number = outlet_details['Contact']
            address = outlet_details['Address']

            pdf = generate_invoice(customer_name, gst_number, contact_number, address, selected_products, quantities, distributor_details['Discount Category'], selected_firm, transaction_type)
            pdf_file = f"invoice_{customer_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            pdf.output(pdf_file)
            with open(pdf_file, "rb") as f:
                st.download_button("Download Invoice", f, file_name=pdf_file)
        else:
            st.error("Please fill all fields and select products.")
