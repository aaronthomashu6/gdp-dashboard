import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import uuid

# Page configuration
st.set_page_config(
    page_title="Invoice & Warehouse Management",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'deleted_tiles' not in st.session_state:
    st.session_state.deleted_tiles = []

if 'warranty_machines' not in st.session_state:
    st.session_state.warranty_machines = []

if 'out_of_warranty_machines' not in st.session_state:
    st.session_state.out_of_warranty_machines = []

# Helper functions
def process_csv_data(df):
    """Process CSV data and group by DocNo"""
    # Filter only rows with StockCode starting with 'E'
    df_filtered = df[df['StockCode'].astype(str).str.startswith('E', na=False)].copy()
    
    # Convert Date to datetime
    df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], errors='coerce')
    
    # Convert Rate to numeric
    df_filtered['Rate'] = pd.to_numeric(df_filtered['Rate'], errors='coerce')
    
    # Group by DocNo and aggregate
    grouped = df_filtered.groupby('DocNo').agg({
        'Date': 'first',
        'Party': 'first',
        'StockCode': lambda x: ', '.join(x.astype(str)),
        'Description': lambda x: ', '.join(x.astype(str)),
        'Rate': 'sum'
    }).reset_index()
    
    # Add unique ID for each tile
    grouped['tile_id'] = [str(uuid.uuid4()) for _ in range(len(grouped))]
    
    return grouped

def create_tile(row, index):
    """Create a tile for each DocNo"""
    tile_id = row['tile_id']
    
    # Check if tile is deleted
    if tile_id in st.session_state.deleted_tiles:
        return None
    
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"""
            <div style="
                border: 2px solid #e6e6e6;
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                background-color: #f8f9fa;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <h4 style="color: #2c3e50; margin-bottom: 10px;">📄 Doc No: {row['DocNo']}</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div><strong>📅 Date:</strong> {row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'}</div>
                    <div><strong>🏢 Party:</strong> {row['Party']}</div>
                    <div><strong>📦 Stock Codes:</strong> {row['StockCode']}</div>
                    <div style="grid-column: 1 / -1;"><strong>💰 Total Amount:</strong> ₹{row['Rate']:,.2f}</div>
                </div>
                <div style="margin-top: 10px;">
                    <strong>📝 Description:</strong> {row['Description'][:100]}...
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button(f"🗑️ Delete", key=f"delete_{tile_id}"):
                st.session_state.deleted_tiles.append(tile_id)
                st.rerun()
    
    return row

# Main app
st.title("📊 Invoice & Warehouse Management System")

# Create tabs
tab1, tab2 = st.tabs(["📊 Invoice Analysis", "🏭 Machine in Warehouse"])

with tab1:
    st.header("📄 Invoice Data Analysis")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            
            # Display original data info
            st.subheader("📋 Original Data Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                e_stock_count = len(df[df['StockCode'].astype(str).str.startswith('E', na=False)])
                st.metric("E-Stock Items", e_stock_count)
            with col3:
                unique_docs = df['DocNo'].nunique()
                st.metric("Unique Documents", unique_docs)
            
            # Process data
            processed_df = process_csv_data(df)
            
            if len(processed_df) > 0:
                # Filter out deleted tiles for display
                display_df = processed_df[~processed_df['tile_id'].isin(st.session_state.deleted_tiles)]
                
                # Display tiles
                st.subheader("📋 Invoice Tiles")
                st.write(f"Showing {len(display_df)} active tiles out of {len(processed_df)} total")
                
                for index, row in display_df.iterrows():
                    create_tile(row, index)
                
                # Analytics section
                st.subheader("📈 Analytics")
                
                # Date-wise income graph
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📅 Date-wise Income")
                    date_income = display_df.groupby(display_df['Date'].dt.date)['Rate'].sum().reset_index()
                    date_income.columns = ['Date', 'Income']
                    
                    fig_line = px.line(
                        date_income, 
                        x='Date', 
                        y='Income',
                        title='Daily Income Trend',
                        markers=True
                    )
                    fig_line.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Income (₹)"
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
                
                with col2:
                    st.subheader("🥧 DocNo-wise Income Distribution")
                    fig_pie = px.pie(
                        display_df, 
                        values='Rate', 
                        names='DocNo',
                        title='Income by Document Number'
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                # Summary statistics
                st.subheader("📊 Summary Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Income", f"₹{display_df['Rate'].sum():,.2f}")
                with col2:
                    st.metric("Average Invoice", f"₹{display_df['Rate'].mean():,.2f}")
                with col3:
                    st.metric("Highest Invoice", f"₹{display_df['Rate'].max():,.2f}")
                with col4:
                    st.metric("Active Documents", len(display_df))
                
                # Option to reset deleted tiles
                if st.session_state.deleted_tiles:
                    st.warning(f"⚠️ {len(st.session_state.deleted_tiles)} tiles have been deleted")
                    if st.button("🔄 Restore All Deleted Tiles"):
                        st.session_state.deleted_tiles = []
                        st.rerun()
            
            else:
                st.warning("⚠️ No records found with StockCode starting with 'E'")
                
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
    
    else:
        st.info("👆 Please upload a CSV file to begin analysis")

with tab2:
    st.header("🏭 Machine in Warehouse")
    
    # Create sub-tabs for warranty status
    warranty_tab, out_warranty_tab = st.tabs(["✅ Warranty", "❌ Out of Warranty"])
    
    with warranty_tab:
        st.subheader("✅ Machines Under Warranty")
        
        # Form to add warranty machine
        with st.form("warranty_machine_form"):
            st.write("➕ Add New Warranty Machine")
            col1, col2 = st.columns(2)
            
            with col1:
                machine_name = st.text_input("🔧 Machine Name")
                client_name = st.text_input("🏢 Client Name")
                num_machines = st.number_input("🔢 Number of Machines", min_value=1, value=1)
            
            with col2:
                warranty_status = st.selectbox("📋 Warranty Status", ["Active", "Expiring Soon", "Extended"])
                inspected = st.selectbox("🔍 Inspected", ["Yes", "No", "Pending"])
            
            submitted = st.form_submit_button("➕ Add Machine")
            
            if submitted and machine_name and client_name:
                new_machine = {
                    'id': str(uuid.uuid4()),
                    'machine_name': machine_name,
                    'client_name': client_name,
                    'num_machines': num_machines,
                    'warranty_status': warranty_status,
                    'inspected': inspected,
                    'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.warranty_machines.append(new_machine)
                st.success("✅ Machine added successfully!")
                st.rerun()
        
        # Display warranty machines
        if st.session_state.warranty_machines:
            st.write("📋 Current Warranty Machines:")
            
            for i, machine in enumerate(st.session_state.warranty_machines):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    status_color = {"Active": "🟢", "Expiring Soon": "🟡", "Extended": "🔵"}
                    inspect_color = {"Yes": "✅", "No": "❌", "Pending": "⏳"}
                    
                    st.markdown(f"""
                    <div style="
                        border: 2px solid #27ae60;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 10px 0;
                        background-color: #e8f5e8;
                    ">
                        <h5>🔧 {machine['machine_name']}</h5>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div><strong>🏢 Client:</strong> {machine['client_name']}</div>
                            <div><strong>🔢 Quantity:</strong> {machine['num_machines']}</div>
                            <div><strong>📋 Warranty:</strong> {status_color.get(machine['warranty_status'], '⚪')} {machine['warranty_status']}</div>
                            <div><strong>🔍 Inspected:</strong> {inspect_color.get(machine['inspected'], '❓')} {machine['inspected']}</div>
                        </div>
                        <small><strong>📅 Added:</strong> {machine['added_date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"del_warranty_{machine['id']}"):
                        st.session_state.warranty_machines = [m for m in st.session_state.warranty_machines if m['id'] != machine['id']]
                        st.rerun()
        else:
            st.info("📝 No warranty machines added yet.")
    
    with out_warranty_tab:
        st.subheader("❌ Machines Out of Warranty")
        
        # Form to add out-of-warranty machine
        with st.form("out_warranty_machine_form"):
            st.write("➕ Add New Out-of-Warranty Machine")
            col1, col2 = st.columns(2)
            
            with col1:
                ow_machine_name = st.text_input("🔧 Machine Name", key="ow_machine")
                ow_client_name = st.text_input("🏢 Client Name", key="ow_client")
                ow_num_machines = st.number_input("🔢 Number of Machines", min_value=1, value=1, key="ow_num")
            
            with col2:
                ow_inspected = st.selectbox("🔍 Inspected", ["Yes", "No", "Pending"], key="ow_inspected")
                quote_status = st.selectbox("📋 Quote/LPO Status", ["Quote Sent", "LPO Received", "Pending", "Not Required"])
            
            ow_submitted = st.form_submit_button("➕ Add Machine")
            
            if ow_submitted and ow_machine_name and ow_client_name:
                new_ow_machine = {
                    'id': str(uuid.uuid4()),
                    'machine_name': ow_machine_name,
                    'client_name': ow_client_name,
                    'num_machines': ow_num_machines,
                    'inspected': ow_inspected,
                    'quote_lpo_status': quote_status,
                    'added_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.out_of_warranty_machines.append(new_ow_machine)
                st.success("✅ Machine added successfully!")
                st.rerun()
        
        # Display out-of-warranty machines
        if st.session_state.out_of_warranty_machines:
            st.write("📋 Current Out-of-Warranty Machines:")
            
            for i, machine in enumerate(st.session_state.out_of_warranty_machines):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    inspect_color = {"Yes": "✅", "No": "❌", "Pending": "⏳"}
                    quote_color = {
                        "Quote Sent": "📤", 
                        "LPO Received": "✅", 
                        "Pending": "⏳", 
                        "Not Required": "➖"
                    }
                    
                    st.markdown(f"""
                    <div style="
                        border: 2px solid #e74c3c;
                        border-radius: 10px;
                        padding: 15px;
                        margin: 10px 0;
                        background-color: #fdeaea;
                    ">
                        <h5>🔧 {machine['machine_name']}</h5>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div><strong>🏢 Client:</strong> {machine['client_name']}</div>
                            <div><strong>🔢 Quantity:</strong> {machine['num_machines']}</div>
                            <div><strong>🔍 Inspected:</strong> {inspect_color.get(machine['inspected'], '❓')} {machine['inspected']}</div>
                            <div><strong>📋 Quote/LPO:</strong> {quote_color.get(machine['quote_lpo_status'], '❓')} {machine['quote_lpo_status']}</div>
                        </div>
                        <small><strong>📅 Added:</strong> {machine['added_date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"del_out_warranty_{machine['id']}"):
                        st.session_state.out_of_warranty_machines = [m for m in st.session_state.out_of_warranty_machines if m['id'] != machine['id']]
                        st.rerun()
        else:
            st.info("📝 No out-of-warranty machines added yet.")
    
    # Summary section for warehouse
    if st.session_state.warranty_machines or st.session_state.out_of_warranty_machines:
        st.subheader("📊 Warehouse Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_warranty = sum(m['num_machines'] for m in st.session_state.warranty_machines)
            st.metric("🟢 Warranty Machines", total_warranty)
        
        with col2:
            total_out_warranty = sum(m['num_machines'] for m in st.session_state.out_of_warranty_machines)
            st.metric("🔴 Out-of-Warranty", total_out_warranty)
        
        with col3:
            total_machines = total_warranty + total_out_warranty
            st.metric("🏭 Total Machines", total_machines)
        
        with col4:
            warranty_percentage = (total_warranty / total_machines * 100) if total_machines > 0 else 0
            st.metric("📊 Warranty %", f"{warranty_percentage:.1f}%")

# Footer
st.markdown("---")
st.markdown("💡 **Tips:**")
st.markdown("- Upload CSV files in the Invoice Analysis tab to visualize your data")
st.markdown("- Use the Machine Warehouse tab to track equipment status")
st.markdown("- Deleted tiles are remembered until you restore them or restart the app")
st.markdown("- All data is stored in your browser session")