import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import os
import uuid
from PIL import Image
from datetime import datetime
import pytz
import base64
from io import BytesIO
import time

# Set page config
st.set_page_config(page_title="Document Management System", layout="centered")

# Constants
EXPENSE_SHEET_COLUMNS = [
    "Expense ID",
    "Employee Name",
    "Employee Code",
    "Designation",
    "Expense Name",
    "Amount",
    "Date",
    "Category",
    "Description",
    "Document",
    "Status",
    "Submission Date"
]

EXPENSE_CATEGORIES = [
    "Travel",
    "Food",
    "Accommodation",
    "Office Supplies",
    "Client Entertainment",
    "Transportation",
    "Other"
]

INVOICE_SHEET_COLUMNS = [
    "Invoice ID",
    "Employee Name",
    "Employee Code",
    "Designation",
    "Invoice Number",
    "Amount",
    "Date",
    "Vendor Name",
    "Description",
    "Document",
    "Status",
    "Submission Date"
]

# Initialize Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Load employee data
@st.cache_data(ttl=3600)
def load_employee_data():
    try:
        Person = pd.read_csv('Invoice - Person.csv')
        return Person['Employee Name'].tolist()
    except:
        return []

def get_ist_time():
    utc_now = datetime.now(pytz.utc)
    ist = pytz.timezone('Asia/Kolkata')
    return utc_now.astimezone(ist)

def process_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return None
    
    try:
        file_content = uploaded_file.getvalue()
        
        if uploaded_file.type.startswith('image/'):
            img = Image.open(uploaded_file)
            output = BytesIO()
            
            if uploaded_file.type == 'image/png':
                img.save(output, format='PNG', optimize=True)
            else:
                img.save(output, format='JPEG', quality=70)
                
            processed_content = output.getvalue()
        else:
            processed_content = file_content
        
        return base64.b64encode(processed_content).decode('utf-8')
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def log_expense_to_gsheet(conn, expense_data):
    try:
        existing_data = conn.read(worksheet="Expenses", usecols=list(range(len(EXPENSE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how='all')
        
        expense_data = expense_data.reindex(columns=EXPENSE_SHEET_COLUMNS)
        
        updated_data = pd.concat([existing_data, expense_data], ignore_index=True)
        updated_data = updated_data.drop_duplicates(subset=["Expense ID"], keep="last")
        
        conn.update(worksheet="Expenses", data=updated_data)
        return True, None
    except Exception as e:
        return False, str(e)

def log_invoice_to_gsheet(conn, invoice_data):
    try:
        existing_data = conn.read(worksheet="Invoices", usecols=list(range(len(INVOICE_SHEET_COLUMNS))), ttl=5)
        existing_data = existing_data.dropna(how='all')
        
        invoice_data = invoice_data.reindex(columns=INVOICE_SHEET_COLUMNS)
        
        updated_data = pd.concat([existing_data, invoice_data], ignore_index=True)
        updated_data = updated_data.drop_duplicates(subset=["Invoice ID"], keep="last")
        
        conn.update(worksheet="Invoices", data=updated_data)
        return True, None
    except Exception as e:
        return False, str(e)

def expense_page():
    st.title("Expense Management")
    
    if 'employee_name' not in st.session_state:
        st.warning("Please select your name first")
        return
    
    selected_employee = st.session_state.employee_name
    
    tab1, tab2 = st.tabs(["New Expense", "Expense History"])
    
    with tab1:
        st.subheader("Expense Details")
        with st.form("expense_form"):
            expense_name = st.text_input("Expense Name*", help="Brief description of the expense")
            amount = st.number_input("Amount (INR)*", min_value=0.0, step=1.0)
            expense_date = st.date_input("Expense Date*", value=datetime.now().date())
            category = st.selectbox("Category*", EXPENSE_CATEGORIES)
            description = st.text_area("Description", help="Additional details about the expense")
            
            st.subheader("Document Upload")
            uploaded_file = st.file_uploader(
                "Upload Receipt (JPEG, PNG, PDF)",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                help="Upload clear photo or scan of your receipt"
            )
            
            st.markdown("<small>*Required fields</small>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Submit Expense")
            
            if submitted:
                if not expense_name or amount <= 0:
                    st.error("Please fill all required fields")
                else:
                    with st.spinner("Processing your expense..."):
                        expense_id = f"EXP-{get_ist_time().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                        submission_date = get_ist_time().strftime("%d-%m-%Y %H:%M:%S")
                        
                        document_data = process_uploaded_file(uploaded_file) if uploaded_file else None
                        
                        expense_data = {
                            "Expense ID": expense_id,
                            "Employee Name": selected_employee,
                            "Employee Code": Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0],
                            "Designation": Person[Person['Employee Name'] == selected_employee]['Designation'].values[0],
                            "Expense Name": expense_name,
                            "Amount": amount,
                            "Date": expense_date.strftime("%d-%m-%Y"),
                            "Category": category,
                            "Description": description,
                            "Document": document_data if document_data else "",
                            "Status": "Submitted",
                            "Submission Date": submission_date
                        }
                        
                        expense_df = pd.DataFrame([expense_data])
                        success, error = log_expense_to_gsheet(conn, expense_df)
                        
                        if success:
                            st.success(f"Expense {expense_id} submitted successfully!")
                        else:
                            st.error(f"Failed to submit expense: {error}")
    
    with tab2:
        st.subheader("Your Expense History")
        
        @st.cache_data(ttl=300)
        def load_expense_data():
            try:
                df = conn.read(worksheet="Expenses", ttl=5)
                df = df.dropna(how='all')
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                df['Submission Date'] = pd.to_datetime(df['Submission Date'], dayfirst=True, errors='coerce')
                employee_code = Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0]
                return df[df['Employee Code'] == employee_code].sort_values('Submission Date', ascending=False)
            except Exception as e:
                st.error(f"Error loading expense data: {e}")
                return pd.DataFrame()
        
        expense_data = load_expense_data()
        
        if expense_data.empty:
            st.warning("No expense records found for your account")
            return
            
        with st.expander("🔍 Search Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                expense_id_filter = st.text_input("Expense ID", key="expense_id_search")
            with col2:
                date_filter = st.date_input("Expense Date", key="expense_date_search")
            with col3:
                category_filter = st.selectbox(
                    "Category", 
                    ["All"] + EXPENSE_CATEGORIES,
                    key="expense_category_filter"
                )
            
            if st.button("Apply Filters", key="search_expense_button"):
                st.rerun()
        
        filtered = expense_data.copy()
        if expense_id_filter:
            filtered = filtered[filtered['Expense ID'].str.contains(expense_id_filter, case=False, na=False)]
        if date_filter:
            ds = date_filter.strftime("%d-%m-%Y")
            filtered = filtered[filtered['Date'].dt.strftime('%d-%m-%Y') == ds]
        if category_filter != "All":
            filtered = filtered[filtered['Category'] == category_filter]
        
        if filtered.empty:
            st.warning("No matching records found")
            return
            
        st.write(f"📄 Showing {len(filtered)} of your expenses")
        
        display_cols = ['Expense ID', 'Expense Name', 'Amount', 'Date', 'Category', 'Status']
        st.dataframe(
            filtered[display_cols],
            column_config={
                "Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Date": st.column_config.DateColumn(format="DD/MM/YYYY")
            },
            use_container_width=True,
            hide_index=True
        )
        
        selected_expense = st.selectbox(
            "Select expense to view details", 
            filtered['Expense ID'], 
            key="expense_selection"
        )
        details = filtered[filtered['Expense ID'] == selected_expense].iloc[0]
        
        st.subheader(f"Expense {selected_expense} Details")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Amount", f"₹{details['Amount']:.2f}")
            st.metric("Category", details['Category'])
            st.metric("Status", details['Status'])
        with col2:
            st.metric("Expense Date", details['Date'].strftime('%d-%m-%Y'))
            st.metric("Submitted On", details['Submission Date'].strftime('%d-%m-%Y %H:%M'))
        
        st.subheader("Description")
        st.write(details['Description'] if pd.notna(details['Description']) else "No description provided")
        
        if details.get('Document') and isinstance(details['Document'], str) and len(details['Document']) > 0:
            st.subheader("Receipt")
            try:
                file_bytes = base64.b64decode(details['Document'])
                
                if file_bytes.startswith(b'\xFF\xD8') or file_bytes.startswith(b'\x89PNG'):
                    st.image(file_bytes, use_column_width=True)
                elif file_bytes.startswith(b'%PDF'):
                    st.download_button(
                        "Download PDF Receipt",
                        data=file_bytes,
                        file_name=f"{selected_expense}_receipt.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.download_button(
                        "Download Receipt",
                        data=file_bytes,
                        file_name=f"{selected_expense}_receipt.bin",
                        mime="application/octet-stream"
                    )
            except Exception as e:
                st.error(f"Could not display document: {str(e)}")
        
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Expense History", 
            csv, 
            "expense_history.csv", 
            "text/csv", 
            key='download-expense-csv'
        )

def invoice_page():
    st.title("Invoice Management")
    
    if 'employee_name' not in st.session_state:
        st.warning("Please select your name first")
        return
    
    selected_employee = st.session_state.employee_name
    
    tab1, tab2 = st.tabs(["Upload Invoice", "Invoice History"])
    
    with tab1:
        st.subheader("Invoice Details")
        with st.form("invoice_form"):
            invoice_number = st.text_input("Invoice Number*", help="Vendor's invoice number")
            amount = st.number_input("Amount (INR)*", min_value=0.0, step=1.0)
            invoice_date = st.date_input("Invoice Date*", value=datetime.now().date())
            vendor_name = st.text_input("Vendor Name*", help="Name of the vendor/supplier")
            description = st.text_area("Description", help="Additional details about the invoice")
            
            st.subheader("Document Upload")
            uploaded_file = st.file_uploader(
                "Upload Invoice (JPEG, PNG, PDF)",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                help="Upload clear photo or scan of the invoice"
            )
            
            st.markdown("<small>*Required fields</small>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Submit Invoice")
            
            if submitted:
                if not invoice_number or not amount or not vendor_name:
                    st.error("Please fill all required fields")
                else:
                    with st.spinner("Processing your invoice..."):
                        invoice_id = f"INV-{get_ist_time().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                        submission_date = get_ist_time().strftime("%d-%m-%Y %H:%M:%S")
                        
                        document_data = process_uploaded_file(uploaded_file) if uploaded_file else None
                        
                        invoice_data = {
                            "Invoice ID": invoice_id,
                            "Employee Name": selected_employee,
                            "Employee Code": Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0],
                            "Designation": Person[Person['Employee Name'] == selected_employee]['Designation'].values[0],
                            "Invoice Number": invoice_number,
                            "Amount": amount,
                            "Date": invoice_date.strftime("%d-%m-%Y"),
                            "Vendor Name": vendor_name,
                            "Description": description,
                            "Document": document_data if document_data else "",
                            "Status": "Submitted",
                            "Submission Date": submission_date
                        }
                        
                        invoice_df = pd.DataFrame([invoice_data])
                        success, error = log_invoice_to_gsheet(conn, invoice_df)
                        
                        if success:
                            st.success(f"Invoice {invoice_id} submitted successfully!")
                        else:
                            st.error(f"Failed to submit invoice: {error}")
    
    with tab2:
        st.subheader("Your Invoice History")
        
        @st.cache_data(ttl=300)
        def load_invoice_data():
            try:
                df = conn.read(worksheet="Invoices", ttl=5)
                df = df.dropna(how='all')
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                df['Submission Date'] = pd.to_datetime(df['Submission Date'], dayfirst=True, errors='coerce')
                employee_code = Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0]
                return df[df['Employee Code'] == employee_code].sort_values('Submission Date', ascending=False)
            except Exception as e:
                st.error(f"Error loading invoice data: {e}")
                return pd.DataFrame()
        
        invoice_data = load_invoice_data()
        
        if invoice_data.empty:
            st.warning("No invoice records found for your account")
            return
            
        with st.expander("🔍 Search Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                invoice_id_filter = st.text_input("Invoice ID", key="invoice_id_search")
            with col2:
                date_filter = st.date_input("Invoice Date", key="invoice_date_search")
            with col3:
                vendor_filter = st.text_input("Vendor Name", key="invoice_vendor_search")
            
            if st.button("Apply Filters", key="search_invoice_button"):
                st.rerun()
        
        filtered = invoice_data.copy()
        if invoice_id_filter:
            filtered = filtered[filtered['Invoice ID'].str.contains(invoice_id_filter, case=False, na=False)]
        if date_filter:
            ds = date_filter.strftime("%d-%m-%Y")
            filtered = filtered[filtered['Date'].dt.strftime('%d-%m-%Y') == ds]
        if vendor_filter:
            filtered = filtered[filtered['Vendor Name'].str.contains(vendor_filter, case=False, na=False)]
        
        if filtered.empty:
            st.warning("No matching records found")
            return
            
        st.write(f"📄 Showing {len(filtered)} of your invoices")
        
        display_cols = ['Invoice ID', 'Invoice Number', 'Amount', 'Date', 'Vendor Name', 'Status']
        st.dataframe(
            filtered[display_cols],
            column_config={
                "Amount": st.column_config.NumberColumn(format="₹%.2f"),
                "Date": st.column_config.DateColumn(format="DD/MM/YYYY")
            },
            use_container_width=True,
            hide_index=True
        )
        
        selected_invoice = st.selectbox(
            "Select invoice to view details", 
            filtered['Invoice ID'], 
            key="invoice_selection"
        )
        details = filtered[filtered['Invoice ID'] == selected_invoice].iloc[0]
        
        st.subheader(f"Invoice {selected_invoice} Details")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Amount", f"₹{details['Amount']:.2f}")
            st.metric("Vendor", details['Vendor Name'])
            st.metric("Status", details['Status'])
        with col2:
            st.metric("Invoice Date", details['Date'].strftime('%d-%m-%Y'))
            st.metric("Submitted On", details['Submission Date'].strftime('%d-%m-%Y %H:%M'))
            st.metric("Invoice Number", details['Invoice Number'])
        
        st.subheader("Description")
        st.write(details['Description'] if pd.notna(details['Description']) else "No description provided")
        
        if details.get('Document') and isinstance(details['Document'], str) and len(details['Document']) > 0:
            st.subheader("Invoice Document")
            try:
                file_bytes = base64.b64decode(details['Document'])
                
                if file_bytes.startswith(b'\xFF\xD8') or file_bytes.startswith(b'\x89PNG'):
                    st.image(file_bytes, use_column_width=True)
                elif file_bytes.startswith(b'%PDF'):
                    st.download_button(
                        "Download PDF Invoice",
                        data=file_bytes,
                        file_name=f"{selected_invoice}_document.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.download_button(
                        "Download Invoice",
                        data=file_bytes,
                        file_name=f"{selected_invoice}_document.bin",
                        mime="application/octet-stream"
                    )
            except Exception as e:
                st.error(f"Could not display document: {str(e)}")
        
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Invoice History", 
            csv, 
            "invoice_history.csv", 
            "text/csv", 
            key='download-invoice-csv'
        )

def login_page():
    st.title("Document Management System")
    
    try:
        Person = pd.read_csv('Invoice - Person.csv')
    except:
        st.error("Employee data not found. Please ensure 'Invoice - Person.csv' exists.")
        return
    
    with st.form("login_form"):
        employee_name = st.selectbox(
            "Select Your Name",
            Person['Employee Name'].tolist(), 
            key="employee_select"
        )
        
        if st.form_submit_button("Continue"):
            st.session_state.employee_name = employee_name
            st.session_state.page = "main"
            st.rerun()

def main_page():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Expense Management", "Invoice Management"])
    
    if page == "Expense Management":
        expense_page()
    else:
        invoice_page()

def main():
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    
    if st.session_state.page == "login":
        login_page()
    else:
        main_page()

if __name__ == "__main__":
    main()
