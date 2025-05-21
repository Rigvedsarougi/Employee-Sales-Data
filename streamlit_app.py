        st.write(f"📄 Showing {len(invoice_summary)} of your invoices")
        
        # Display the summary table
        st.dataframe(
            invoice_summary,
            column_config={
                "Grand Total": st.column_config.NumberColumn(
                    format="₹%.2f",
                    help="Sum of all products in the invoice including taxes"
                ),
                "Invoice Date": st.column_config.DateColumn(
                    format="DD/MM/YYYY",
                    help="Date when invoice was generated"
                )
            },
            use_container_width=True,
            hide_index=True
        )
        
        selected_invoice = st.selectbox(
            "Select invoice to view details",
            invoice_summary['Invoice Number'],
            key="invoice_selection"
        )
        
        # Delivery Status Section
        st.subheader("Delivery Status Management")
        
        # Get all products for the selected invoice
        invoice_details = filtered_data[filtered_data['Invoice Number'] == selected_invoice]
        
        if not invoice_details.empty:
            # Create a form for delivery status updates
            with st.form(key='delivery_status_form'):
                # Get current status for the invoice
                current_status = invoice_details.iloc[0].get('Delivery Status', 'Pending')
                
                # Display status selection
                new_status = st.selectbox(
                    "Update Delivery Status",
                    ["Pending", "Order Done", "Delivery Done"],
                    index=["Pending", "Order Done", "Delivery Done"].index(current_status) 
                    if current_status in ["Pending", "Order Done", "Delivery Done"] else 0,
                    key=f"status_{selected_invoice}"
                )
                
                # Submit button for the form
                submitted = st.form_submit_button("Update Status")
                
                if submitted:
                    with st.spinner("Updating delivery status..."):
                        try:
                            # Get all sales data
                            ws = get_worksheet("Sales")
                            all_sales_data = pd.DataFrame(ws.get_all_records())
                            
                            # Update the status for all rows with this invoice number
                            mask = all_sales_data['Invoice Number'] == selected_invoice
                            all_sales_data.loc[mask, 'Delivery Status'] = new_status
                            
                            # Clear and rewrite the worksheet
                            ws.clear()
                            ws.append_row(SALES_SHEET_COLUMNS)  # Add headers
                            ws.append_rows(all_sales_data.values.tolist())  # Add data
                            
                            st.success(f"Delivery status updated to '{new_status}' for invoice {selected_invoice}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating delivery status: {e}")
        
        # Display invoice details
        if not invoice_details.empty:
            invoice_data = invoice_details.iloc[0]
            original_invoice_date = invoice_data['Invoice Date'].strftime('%d-%m-%Y')
            
            st.subheader(f"Invoice {selected_invoice}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Date", original_invoice_date)
                st.metric("Outlet", str(invoice_data['Outlet Name']))
                st.metric("Contact", str(invoice_data['Outlet Contact']))
            with col2:
                # Calculate correct total for this invoice
                invoice_total = invoice_details['Grand Total'].sum()
                st.metric("Total Amount", f"₹{invoice_total:.2f}")
                st.metric("Payment Status", str(invoice_data['Payment Status']).capitalize())
                st.metric("Delivery Status", str(invoice_data.get('Delivery Status', 'Pending')).capitalize())
            
            st.subheader("Products")
            product_display = invoice_details[[
                'Product Name', 
                'Quantity', 
                'Unit Price', 
                'Product Discount (%)', 
                'Total Price', 
                'Grand Total'
            ]].copy()
            
            # Format display
            product_display['Product Name'] = product_display['Product Name'].astype(str)
            product_display['Quantity'] = product_display['Quantity'].astype(int)
            
            st.dataframe(
                product_display,
                column_config={
                    "Unit Price": st.column_config.NumberColumn(format="₹%.2f"),
                    "Total Price": st.column_config.NumberColumn(format="₹%.2f"),
                    "Grand Total": st.column_config.NumberColumn(format="₹%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("🔄 Regenerate Invoice", key=f"regenerate_btn_{selected_invoice}"):
                with st.spinner("Regenerating invoice..."):
                    try:
                        pdf, pdf_path = generate_invoice(
                            str(invoice_data['Outlet Name']),
                            str(invoice_data.get('GST Number', '')),
                            str(invoice_data['Outlet Contact']),
                            str(invoice_data['Outlet Address']),
                            str(invoice_data['Outlet State']),
                            str(invoice_data['Outlet City']),
                            invoice_details['Product Name'].astype(str).tolist(),
                            invoice_details['Quantity'].tolist(),
                            invoice_details['Product Discount (%)'].tolist(),
                            str(invoice_data['Discount Category']),
                            str(invoice_data['Employee Name']),
                            str(invoice_data['Payment Status']),
                            float(invoice_data['Amount Paid']),
                            None,
                            None,
                            str(selected_invoice),
                            str(invoice_data['Transaction Type']),
                            str(invoice_data.get('Distributor Firm Name', '')),
                            str(invoice_data.get('Distributor ID', '')),
                            str(invoice_data.get('Distributor Contact Person', '')),
                            str(invoice_data.get('Distributor Contact Number', '')),
                            str(invoice_data.get('Distributor Email', '')),
                            str(invoice_data.get('Distributor Territory', '')),
                            str(invoice_data.get('Remarks', '')),
                            original_invoice_date 
                        )
                        
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                "📥 Download Regenerated Invoice", 
                                f, 
                                file_name=f"{selected_invoice}.pdf",
                                mime="application/pdf",
                                key=f"download_regenerated_{selected_invoice}"
                            )
                        
                        st.success("Invoice regenerated successfully with original date!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error regenerating invoice: {e}")

def visit_page():
    st.title("Visit Management")
    selected_employee = st.session_state.employee_name

    # Empty remarks since we removed the location input
    visit_remarks = ""

    tab1, tab2 = st.tabs(["New Visit", "Visit History"])
    
    with tab1:
        st.subheader("Outlet Details")
        outlet_option = st.radio("Outlet Selection", ["Enter manually", "Select from list"], key="visit_outlet_option")
        
        if outlet_option == "Select from list":
            outlet_names = Outlet['Shop Name'].tolist()
            selected_outlet = st.selectbox("Select Outlet", outlet_names, key="visit_outlet_select")
            outlet_details = Outlet[Outlet['Shop Name'] == selected_outlet].iloc[0]
            
            outlet_name = selected_outlet
            outlet_contact = outlet_details['Contact']
            outlet_address = outlet_details['Address']
            outlet_state = outlet_details['State']
            outlet_city = outlet_details['City']
            
            # Show outlet details like distributor details
            st.text_input("Outlet Contact", value=outlet_contact, disabled=True, key="outlet_contact_display")
            st.text_input("Outlet Address", value=outlet_address, disabled=True, key="outlet_address_display")
            st.text_input("Outlet State", value=outlet_state, disabled=True, key="outlet_state_display")
            st.text_input("Outlet City", value=outlet_city, disabled=True, key="outlet_city_display")
        else:
            outlet_name = st.text_input("Outlet Name", key="visit_outlet_name")
            outlet_contact = st.text_input("Outlet Contact", key="visit_outlet_contact")
            outlet_address = st.text_area("Outlet Address", key="visit_outlet_address")
            outlet_state = st.text_input("Outlet State", "", key="visit_outlet_state")
            outlet_city = st.text_input("Outlet City", "", key="visit_outlet_city")

        st.subheader("Visit Details")
        visit_purpose = st.selectbox("Visit Purpose", ["Sales", "Demo", "Product Demonstration", "Relationship Building", "Issue Resolution", "Other"], key="visit_purpose")
        visit_notes = st.text_area("Visit Notes", key="visit_notes")
        
        st.subheader("Time Tracking")
        col1, col2 = st.columns(2)
        with col1:
            entry_time = st.time_input("Entry Time", value=None, key="visit_entry_time")
        with col2:
            exit_time = st.time_input("Exit Time", value=None, key="visit_exit_time")

        if st.button("Record Visit", key="record_visit_button"):
            if outlet_name:
                today = get_ist_time().date()
                
                if entry_time is None:
                    entry_time = get_ist_time().time()
                if exit_time is None:
                    exit_time = get_ist_time().time()
                    
                entry_datetime = datetime.combine(today, entry_time)
                exit_datetime = datetime.combine(today, exit_time)
                
                # No visit selfie upload
                visit_selfie_path = None
                
                visit_id = record_visit(
                    selected_employee, outlet_name, outlet_contact, outlet_address,
                    outlet_state, outlet_city, visit_purpose, visit_notes, 
                    visit_selfie_path, entry_datetime, exit_datetime,
                    visit_remarks
                )
                
                st.success(f"Visit {visit_id} recorded successfully!")
            else:
                st.error("Please fill all required fields.")
    
    with tab2:
        st.subheader("Previous Visits")
        col1, col2, col3 = st.columns(3)
        with col1:
            visit_id_search = st.text_input("Visit ID", key="visit_id_search")
        with col2:
            visit_date_search = st.date_input("Visit Date", key="visit_date_search")
        with col3:
            outlet_name_search = st.text_input("Outlet Name", key="visit_outlet_search")
            
        if st.button("Search Visits", key="search_visits_button"):
            try:
                ws = get_worksheet("Visits")
                visit_data = pd.DataFrame(ws.get_all_records())
                visit_data = visit_data.dropna(how="all")
                
                employee_code = Person[Person['Employee Name'] == selected_employee]['Employee Code'].values[0]
                filtered_data = visit_data[visit_data['Employee Code'] == employee_code]
                
                if visit_id_search:
                    filtered_data = filtered_data[filtered_data['Visit ID'].str.contains(visit_id_search, case=False)]
                if visit_date_search:
                    date_str = visit_date_search.strftime("%d-%m-%Y")
                    filtered_data = filtered_data[filtered_data['Visit Date'] == date_str]
                if outlet_name_search:
                    filtered_data = filtered_data[filtered_data['Outlet Name'].str.contains(outlet_name_search, case=False)]
                
                if not filtered_data.empty:
                    # Display only the most relevant columns
                    display_columns = [
                        'Visit ID', 'Visit Date', 'Outlet Name', 'Visit Purpose', 'Visit Notes',
                        'Entry Time', 'Exit Time', 'Visit Duration (minutes)', 'Remarks'
                    ]
                    st.dataframe(filtered_data[display_columns])
                    
                    # Add download option
                    csv = filtered_data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download as CSV",
                        csv,
                        "visit_history.csv",
                        "text/csv",
                        key='download-visit-csv'
                    )
                else:
                    st.warning("No matching visit records found")
            except Exception as e:
                st.error(f"Error retrieving visit data: {e}")

def attendance_page():
    st.title("Attendance Management")
    selected_employee = st.session_state.employee_name
    
    if check_existing_attendance(selected_employee):
        st.warning("You have already marked your attendance for today.")
        return
    
    st.subheader("Attendance Status")
    status = st.radio("Select Status", ["Present", "Half Day", "Leave"], index=0, key="attendance_status")
    
    if status in ["Present", "Half Day"]:
        st.subheader("Location Verification")
        col1, col2 = st.columns([3, 1])
        with col1:
            live_location = st.text_input("Enter your current location (Google Maps link or address)", 
                                        help="Please share your live location for verification",
                                        key="location_input")

        
        if st.button("Mark Attendance", key="mark_attendance_button"):
            if not live_location:
                st.error("Please provide your location")
            else:
                with st.spinner("Recording attendance..."):
                    attendance_id, error = record_attendance(
                        selected_employee,
                        status,  # Will be "Present" or "Half Day"
                        location_link=live_location
                    )
                    
                    if error:
                        st.error(f"Failed to record attendance: {error}")
                    else:
                        st.success(f"Attendance recorded successfully! ID: {attendance_id}")
                        st.balloons()
    
    else:
        st.subheader("Leave Details")
        leave_types = ["Sick Leave", "Personal Leave", "Vacation", "Other"]
        leave_type = st.selectbox("Leave Type", leave_types, key="leave_type")
        leave_reason = st.text_area("Reason for Leave", 
                                 placeholder="Please provide details about your leave",
                                 key="leave_reason")
        
        if st.button("Submit Leave Request", key="submit_leave_button"):
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

def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = None
    if 'employee_name' not in st.session_state:
        st.session_state.employee_name = None

    if not st.session_state.authenticated:
        # Display the centered logo and heading
        display_login_header()
        
        employee_names = Person['Employee Name'].tolist()
        
        # Create centered form
        form_col1, form_col2, form_col3 = st.columns([1, 2, 1])
        
        with form_col2:
            with st.container():
                employee_name = st.selectbox(
                    "Select Your Name", 
                    employee_names, 
                    key="employee_select"
                )
                passkey = st.text_input(
                    "Enter Your Employee Code", 
                    type="password", 
                    key="passkey_input"
                )
                
                login_button = st.button(
                    "Log in", 
                    key="login_button",
                    use_container_width=True
                )
                
                if login_button:
                    if authenticate_employee(employee_name, passkey):
                        st.session_state.authenticated = True
                        st.session_state.employee_name = employee_name
                        st.rerun()
                    else:
                        st.error("Invalid Password. Please try again.")
    else:
        # Show option boxes after login
        st.title("Select Mode")
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        
        with col1:
            if st.button("Sales", use_container_width=True, key="sales_mode"):
                st.session_state.selected_mode = "Sales"
                st.rerun()
        
        with col2:
            if st.button("Visit", use_container_width=True, key="visit_mode"):
                st.session_state.selected_mode = "Visit"
                st.rerun()
        
        with col3:
            if st.button("Attendance", use_container_width=True, key="attendance_mode"):
                st.session_state.selected_mode = "Attendance"
                st.rerun()
                
        with col4:
            if st.button("Resources", use_container_width=True, key="resources_mode"):
                st.session_state.selected_mode = "Resources"
                st.rerun()
                
        with col5:
            if st.button("Support Ticket", use_container_width=True, key="ticket_mode"):
                st.session_state.selected_mode = "Support Ticket"
                st.rerun()
                
        with col6:
            if st.button("Travel/Hotel", use_container_width=True, key="travel_mode"):
                st.session_state.selected_mode = "Travel/Hotel"
                st.rerun()
                
        with col7:
            if st.button("Demo", use_container_width=True, key="demo_mode"):
                st.session_state.selected_mode = "Demo"
                st.rerun()
        
        if st.session_state.selected_mode:
            add_back_button()
            
            if st.session_state.selected_mode == "Sales":
                sales_page()
            elif st.session_state.selected_mode == "Visit":
                visit_page()
            elif st.session_state.selected_mode == "Attendance":
                attendance_page()
            elif st.session_state.selected_mode == "Resources":
                resources_page()
            elif st.session_state.selected_mode == "Support Ticket":
                support_ticket_page()
            elif st.session_state.selected_mode == "Travel/Hotel":
                travel_hotel_page()
            elif st.session_state.selected_mode == "Demo":
                demo_page()

if __name__ == "__main__":
    main()
