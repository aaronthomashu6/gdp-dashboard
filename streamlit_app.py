import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import uuid
import sqlite3
import os

# Page configuration
st.set_page_config(
    page_title="Invoice & Warehouse Management",
    page_icon="📊",
    layout="wide"
)

# Database setup
DB_FILE = "warehouse_management.db"

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table for deleted tiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deleted_tiles (
            tile_id TEXT PRIMARY KEY,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for warranty machines
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warranty_machines (
            id TEXT PRIMARY KEY,
            machine_name TEXT NOT NULL,
            client_name TEXT NOT NULL,
            num_machines INTEGER NOT NULL,
            warranty_status TEXT NOT NULL,
            inspected TEXT NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for out-of-warranty machines
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS out_warranty_machines (
            id TEXT PRIMARY KEY,
            machine_name TEXT NOT NULL,
            client_name TEXT NOT NULL,
            num_machines INTEGER NOT NULL,
            inspected TEXT NOT NULL,
            quote_lpo_status TEXT NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def load_deleted_tiles():
    """Load deleted tile IDs from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT tile_id FROM deleted_tiles")
    deleted_tiles = [row[0] for row in cursor.fetchall()]
    conn.close()
    return deleted_tiles

def add_deleted_tile(tile_id):
    """Add a deleted tile ID to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO deleted_tiles (tile_id) VALUES (?)", (tile_id,))
    conn.commit()
    conn.close()

def restore_deleted_tiles():
    """Remove all deleted tiles from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deleted_tiles")
    conn.commit()
    conn.close()

def load_warranty_machines():
    """Load warranty machines from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, machine_name, client_name, num_machines, 
               warranty_status, inspected, added_date 
        FROM warranty_machines 
        ORDER BY added_date DESC
    """)
    machines = []
    for row in cursor.fetchall():
        machines.append({
            'id': row[0],
            'machine_name': row[1],
            'client_name': row[2],
            'num_machines': row[3],
            'warranty_status': row[4],
            'inspected': row[5],
            'added_date': row[6]
        })
    conn.close()
    return machines

def add_warranty_machine(machine_data):
    """Add warranty machine to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO warranty_machines 
        (id, machine_name, client_name, num_machines, warranty_status, inspected)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        machine_data['id'],
        machine_data['machine_name'],
        machine_data['client_name'],
        machine_data['num_machines'],
        machine_data['warranty_status'],
        machine_data['inspected']
    ))
    conn.commit()
    conn.close()

def delete_warranty_machine(machine_id):
    """Delete warranty machine from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM warranty_machines WHERE id = ?", (machine_id,))
    conn.commit()
    conn.close()

def load_out_warranty_machines():
    """Load out-of-warranty machines from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, machine_name, client_name, num_machines, 
               inspected, quote_lpo_status, added_date 
        FROM out_warranty_machines 
        ORDER BY added_date DESC
    """)
    machines = []
    for row in cursor.fetchall():
        machines.append({
            'id': row[0],
            'machine_name': row[1],
            'client_name': row[2],
            'num_machines': row[3],
            'inspected': row[4],
            'quote_lpo_status': row[5],
            'added_date': row[6]
        })
    conn.close()
    return machines

def add_out_warranty_machine(machine_data):
    """Add out-of-warranty machine to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO out_warranty_machines 
        (id, machine_name, client_name, num_machines, inspected, quote_lpo_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        machine_data['id'],
        machine_data['machine_name'],
        machine_data['client_name'],
        machine_data['num_machines'],
        machine_data['inspected'],
        machine_data['quote_lpo_status']
    ))
    conn.commit()
    conn.close()

def delete_out_warranty_machine(machine_id):
    """Delete out-of-warranty machine from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM out_warranty_machines WHERE id = ?", (machine_id,))
    conn.commit()
    conn.close()

# Initialize database
init_database()

# Initialize session state with database data
if 'deleted_tiles' not in st.session_state:
    st.session_state.deleted_tiles = load_deleted_tiles()

if 'warranty_machines' not in st.session_state:
    st.session_state.warranty_machines = load_warranty_machines()

if 'out_of_warranty_machines' not in st.session_state:
    st.session_state.out_of_warranty_machines = load_out_warranty_machines()

# Helper functions
def process_csv_data(df):
    """Process CSV data and group by DocNo"""
    # Clean column names - remove extra spaces and handle formatting issues
    df.columns = df.columns.str.strip()
    
    # Remove any completely empty rows
    df = df.dropna(how='all')
    
    # Check if required columns exist (try variations)
    column_mapping = {
        'DocNo': ['DocNo', 'Document Number', 'Doc No', 'Docno'],
        'Date': ['Date', 'Doc Date', 'Document Date'],
        'Party': ['Party', 'Customer', 'Client', 'Company'],
        'StockCode': ['StockCode', 'Stock Code', 'Item Code', 'Product Code'],
        'Description': ['Description', 'Item Description', 'Product Description'],
        'Rate': ['Rate', 'Amount', 'Price', 'Unit Price', 'Gr.Amt']
    }
    
    # Map columns to standard names
    for standard_name, possible_names in column_mapping.items():
        for possible_name in possible_names:
            if possible_name in df.columns:
                if standard_name != possible_name:
                    df[standard_name] = df[possible_name]
                break
    
    # Check if required columns exist after mapping
    required_columns = ['DocNo', 'Date', 'Party', 'StockCode', 'Description', 'Rate']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"❌ Missing required columns: {missing_columns}")
        st.write("**Available columns:**", list(df.columns))
        st.write("**Column mapping attempted:**")
        for standard, possible in column_mapping.items():
            found = next((col for col in possible if col in df.columns), "Not found")
            st.write(f"- {standard}: {found}")
        return pd.DataFrame()
    
    # Include ALL stock codes - no filtering
    df_filtered = df.copy()
    
    # Remove rows with missing essential data
    df_filtered = df_filtered.dropna(subset=['DocNo', 'Party'])
    
    if len(df_filtered) == 0:
        st.warning("⚠️ No valid records found")
        return pd.DataFrame()
    
    # Convert Date to datetime - handle multiple date formats
    df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], errors='coerce', dayfirst=True)
    
    # Convert Rate to numeric, handling any formatting issues
    df_filtered['Rate'] = pd.to_numeric(df_filtered['Rate'], errors='coerce').fillna(0)
    
    # Clean text fields
    df_filtered['Party'] = df_filtered['Party'].astype(str).str.strip()
    df_filtered['Description'] = df_filtered['Description'].astype(str).str.strip()
    df_filtered['StockCode'] = df_filtered['StockCode'].astype(str).str.strip()
    
    # Group by DocNo and aggregate
    grouped = df_filtered.groupby('DocNo').agg({
        'Date': 'first',
        'Party': 'first',
        'StockCode': lambda x: ', '.join(x.astype(str)),
        'Description': lambda x: ' | '.join(x.astype(str)),
        'Rate': 'sum'
    }).reset_index()
    
    # Add unique ID for each tile based on DocNo for consistency
    grouped['tile_id'] = grouped['DocNo'].astype(str) + '_tile'
    
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
                border: 2px solid #3498db;
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                background-color: #ffffff;
                color: #2c3e50;
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            ">
                <h4 style="color: #2980b9; margin-bottom: 10px; font-weight: bold;">🏢 {row['Party']}</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; color: #34495e;">
                    <div><strong style="color: #e74c3c;">📄 Doc No:</strong> {row['DocNo']}</div>
                    <div><strong style="color: #e67e22;">📅 Date:</strong> {row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else 'N/A'}</div>
                    <div style="grid-column: 1 / -1;"><strong style="color: #27ae60;">📦 Stock Codes:</strong> {row['StockCode']}</div>
                    <div style="grid-column: 1 / -1;"><strong style="color: #8e44ad;">💰 Total Amount:</strong> <span style="font-size: 1.2em; color: #27ae60;">{row['Rate']:,.2f}</span></div>
                </div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ecf0f1;">
                    <strong style="color: #7f8c8d;">📝 Description:</strong><br>
                    <span style="color: #5d6d7e; font-size: 0.95em; line-height: 1.4;">{row['Description'][:200] if len(str(row['Description'])) > 200 else row['Description']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button(f"🗑️ Delete", key=f"delete_{tile_id}", help="Delete this tile"):
                if tile_id not in st.session_state.deleted_tiles:
                    st.session_state.deleted_tiles.append(tile_id)
                    add_deleted_tile(tile_id)
                    st.success(f"✅ Tile {row['DocNo']} deleted!")
                    st.rerun()
    
    return row

# Main app
st.title("📊 Invoice & Warehouse Management System")
st.info("💾 All data is automatically saved to local database: warehouse_management.db")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Invoice Analysis", "🏭 Machine in Warehouse", "🗄️ Database Info"])

with tab1:
    st.header("📄 Invoice Data Analysis")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            # First, try to read the CSV normally
            df_temp = pd.read_csv(uploaded_file)
            
            # Check if first row contains "TRANSACTION CHECKLIST" or similar header issues
            if len(df_temp.columns) > 0 and ('TRANSACTION CHECKLIST' in str(df_temp.columns[0]) or 
                                           'Unnamed:' in str(df_temp.columns[0])):
                # Skip the first row and use the second row as headers
                uploaded_file.seek(0)  # Reset file pointer
                df = pd.read_csv(uploaded_file, skiprows=1)
                st.info("ℹ️ Detected header row issue - automatically skipped first row")
            else:
                df = df_temp
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Remove any completely empty rows
            df = df.dropna(how='all')
            
            # Show available columns for debugging
            with st.expander("🔍 Debug Info"):
                st.write(f"**Available columns:** {list(df.columns)}")
                st.write(f"**Data shape:** {df.shape}")
                if len(df) > 0:
                    st.write("**First few rows:**")
                    st.dataframe(df.head())
            
            # Display original data info
            st.subheader("📋 Original Data Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rows", len(df))
            with col2:
                if 'StockCode' in df.columns:
                    unique_stock_count = df['StockCode'].nunique()
                    st.metric("Unique Stock Items", unique_stock_count)
                else:
                    st.metric("Unique Stock Items", "N/A - No StockCode column")
            with col3:
                if 'DocNo' in df.columns:
                    unique_docs = df['DocNo'].nunique()
                    st.metric("Unique Documents", unique_docs)
                else:
                    st.metric("Unique Documents", "N/A - No DocNo column")
            
            # Process data
            processed_df = process_csv_data(df)
            
            if len(processed_df) > 0:
                # Filter out deleted tiles for display
                display_df = processed_df[~processed_df['tile_id'].isin(st.session_state.deleted_tiles)]
                
                # Display tiles
                st.subheader("📋 All Invoice Tiles")
                st.write(f"Showing {len(display_df)} active tiles out of {len(processed_df)} total")
                st.info("ℹ️ **Now including ALL stock codes** in each document - no filtering applied")
                
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
                        yaxis_title="Income ()"
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
                
                with col2:
                    st.subheader("📊 Party-wise Machine Count & Revenue")
                    
                    # Count machines per party and calculate total revenue
                    party_stats = display_df.groupby('Party').agg({
                        'DocNo': 'count',  # Count of documents (machines/orders)
                        'Rate': 'sum'      # Total revenue
                    }).reset_index()
                    party_stats.columns = ['Party', 'Machine_Count', 'Total_Revenue']
                    
                    # Create pie chart for machine count
                    fig_pie = px.pie(
                        party_stats, 
                        values='Machine_Count', 
                        names='Party',
                        title='Machine/Order Distribution by Party',
                        hover_data=['Total_Revenue'],
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        hovertemplate='<b>%{label}</b><br>' +
                                    'Machines/Orders: %{value}<br>' +
                                    'Total Revenue: %{customdata[0]:,.2f}<extra></extra>'
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Show party statistics table
                    st.write("**📋 Party Summary:**")
                    party_stats['Total_Revenue'] = party_stats['Total_Revenue'].apply(lambda x: f"{x:,.2f}")
                    party_stats.columns = ['🏢 Party', '🔧 Machines/Orders', '💰 Total Revenue']
                    st.dataframe(party_stats, use_container_width=True, hide_index=True)
                
                # Summary statistics
                st.subheader("📊 Summary Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("💰 Total Income", f"{display_df['Rate'].sum():,.2f}")
                with col2:
                    st.metric("📈 Average per Order", f"{display_df['Rate'].mean():,.2f}")
                with col3:
                    st.metric("🔝 Highest Order", f"{display_df['Rate'].max():,.2f}")
                with col4:
                    unique_parties = display_df['Party'].nunique()
                    st.metric("🏢 Active Parties", unique_parties)
                
                # Top party analysis
                if len(display_df) > 1:
                    # st.subheader("🏆 Top Performers")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        top_revenue_party = party_stats.loc[party_stats['Total_Revenue'].str.replace('', '').str.replace(',', '').astype(float).idxmax()]
                        st.info(f"**💰 Highest Revenue:** {top_revenue_party['🏢 Party']}\n\n**Amount:** {top_revenue_party['💰 Total Revenue']}")
                    
                    with col2:
                        top_volume_party = party_stats.loc[party_stats['🔧 Machines/Orders'].idxmax()]
                        st.info(f"**🔧 Most Orders:** {top_volume_party['🏢 Party']}\n\n**Orders:** {top_volume_party['🔧 Machines/Orders']}")
                
                # Option to reset deleted tiles
                if st.session_state.deleted_tiles:
                    st.warning(f"⚠️ {len(st.session_state.deleted_tiles)} tiles have been deleted")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Restore All Deleted Tiles"):
                            st.session_state.deleted_tiles = []
                            restore_deleted_tiles()
                            st.success("✅ All deleted tiles restored!")
                            st.rerun()
                    with col2:
                        deleted_docnos = [tile_id.replace('_tile', '') for tile_id in st.session_state.deleted_tiles]
                        st.info(f"**Deleted DocNos:** {', '.join(deleted_docnos)}")
            
            else:
                st.warning("⚠️ No valid records found after processing")
                
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
                add_warranty_machine(new_machine)
                st.success("✅ Machine added and saved to database!")
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
                        background-color: #ffffff;
                        color: #2c3e50;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                    ">
                        <h5 style="color: #27ae60; margin-bottom: 10px; font-weight: bold;">🔧 {machine['machine_name']}</h5>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; color: #34495e;">
                            <div><strong style="color: #e74c3c;">🏢 Client:</strong> <span style="color: #2c3e50;">{machine['client_name']}</span></div>
                            <div><strong style="color: #f39c12;">🔢 Quantity:</strong> <span style="color: #2c3e50;">{machine['num_machines']}</span></div>
                            <div><strong style="color: #3498db;">📋 Warranty:</strong> {status_color.get(machine['warranty_status'], '⚪')} <span style="color: #2c3e50;">{machine['warranty_status']}</span></div>
                            <div><strong style="color: #9b59b6;">🔍 Inspected:</strong> {inspect_color.get(machine['inspected'], '❓')} <span style="color: #2c3e50;">{machine['inspected']}</span></div>
                        </div>
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ecf0f1;">
                            <small style="color: #7f8c8d;"><strong>📅 Added:</strong> {machine['added_date']}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"del_warranty_{machine['id']}"):
                        st.session_state.warranty_machines = [m for m in st.session_state.warranty_machines if m['id'] != machine['id']]
                        delete_warranty_machine(machine['id'])
                        st.success("✅ Machine deleted from database!")
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
                add_out_warranty_machine(new_ow_machine)
                st.success("✅ Machine added and saved to database!")
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
                        background-color: #ffffff;
                        color: #2c3e50;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                    ">
                        <h5 style="color: #e74c3c; margin-bottom: 10px; font-weight: bold;">🔧 {machine['machine_name']}</h5>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; color: #34495e;">
                            <div><strong style="color: #e74c3c;">🏢 Client:</strong> <span style="color: #2c3e50;">{machine['client_name']}</span></div>
                            <div><strong style="color: #f39c12;">🔢 Quantity:</strong> <span style="color: #2c3e50;">{machine['num_machines']}</span></div>
                            <div><strong style="color: #3498db;">🔍 Inspected:</strong> {inspect_color.get(machine['inspected'], '❓')} <span style="color: #2c3e50;">{machine['inspected']}</span></div>
                            <div><strong style="color: #9b59b6;">📋 Quote/LPO:</strong> {quote_color.get(machine['quote_lpo_status'], '❓')} <span style="color: #2c3e50;">{machine['quote_lpo_status']}</span></div>
                        </div>
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ecf0f1;">
                            <small style="color: #7f8c8d;"><strong>📅 Added:</strong> {machine['added_date']}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"del_out_warranty_{machine['id']}"):
                        st.session_state.out_of_warranty_machines = [m for m in st.session_state.out_of_warranty_machines if m['id'] != machine['id']]
                        delete_out_warranty_machine(machine['id'])
                        st.success("✅ Machine deleted from database!")
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

with tab3:
    st.header("🗄️ Database Information")
    
    # Database file info
    if os.path.exists(DB_FILE):
        file_size = os.path.getsize(DB_FILE)
        st.success(f"✅ Database connected: {DB_FILE}")
        st.info(f"📁 Database size: {file_size:,} bytes")
        
        # Show database statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🗑️ Deleted Tiles", len(st.session_state.deleted_tiles))
        
        with col2:
            st.metric("✅ Warranty Machines", len(st.session_state.warranty_machines))
        
        with col3:
            st.metric("❌ Out-of-Warranty", len(st.session_state.out_of_warranty_machines))
        
        # Database management options
        st.subheader("🔧 Database Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Data from Database"):
                st.session_state.deleted_tiles = load_deleted_tiles()
                st.session_state.warranty_machines = load_warranty_machines()
                st.session_state.out_of_warranty_machines = load_out_warranty_machines()
                st.success("✅ Data refreshed from database!")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear All Database Data", type="secondary"):
                if st.session_state.get('confirm_clear', False):
                    # Clear all tables
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM deleted_tiles")
                    cursor.execute("DELETE FROM warranty_machines")
                    cursor.execute("DELETE FROM out_warranty_machines")
                    conn.commit()
                    conn.close()
                    
                    # Reset session state
                    st.session_state.deleted_tiles = []
                    st.session_state.warranty_machines = []
                    st.session_state.out_of_warranty_machines = []
                    st.session_state.confirm_clear = False
                    
                    st.success("✅ All database data cleared!")
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("⚠️ Click again to confirm deletion of ALL data!")
        
        # Show raw database content
        st.subheader("📊 Database Tables")
        
        # Show deleted tiles
        if st.session_state.deleted_tiles:
            st.write("🗑️ **Deleted Tiles:**")
            deleted_df = pd.DataFrame({'Tile ID': st.session_state.deleted_tiles})
            st.dataframe(deleted_df, use_container_width=True)
        
        # Show warranty machines table
        if st.session_state.warranty_machines:
            st.write("✅ **Warranty Machines:**")
            warranty_df = pd.DataFrame(st.session_state.warranty_machines)
            st.dataframe(warranty_df, use_container_width=True)
        
        # Show out-of-warranty machines table
        if st.session_state.out_of_warranty_machines:
            st.write("❌ **Out-of-Warranty Machines:**")
            out_warranty_df = pd.DataFrame(st.session_state.out_of_warranty_machines)
            st.dataframe(out_warranty_df, use_container_width=True)
    
    else:
        st.error(f"❌ Database file not found: {DB_FILE}")
        st.info("The database will be created automatically when you add your first machine or delete a tile.")

# Footer