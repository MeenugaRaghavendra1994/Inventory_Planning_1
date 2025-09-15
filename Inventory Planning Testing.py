import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

# -----------------------------
# Helper Functions
# -----------------------------
def load_file(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    elif file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    else:
        st.error("Unsupported file type. Please upload CSV or Excel files only.")
        return None

def calculate_add(sales_df, days=30):
    recent_sales = sales_df[sales_df['Order_Date'] >= (datetime.today() - timedelta(days=days))]
    daily_sales = recent_sales.groupby('Product')['Quantity'].sum() / days
    return daily_sales

def calculate_rop(add, lead_time, safety_stock):
    return (add * lead_time) + safety_stock

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Inventory Planning Dashboard", layout="wide")

st.title("📦 Inventory Planning Dashboard")

# Sidebar Uploads
st.sidebar.header("Upload Your Data")
orders_file = st.sidebar.file_uploader("Upload Orders CSV or Excel", type=["csv", "xlsx"])
current_stock_file = st.sidebar.file_uploader("Upload Current Stock CSV or Excel", type=["csv", "xlsx"])
product_master_file = st.sidebar.file_uploader("Upload Product Master CSV or Excel", type=["csv", "xlsx"])

if orders_file and current_stock_file and product_master_file:
    # Display file names for debugging
    st.write("Uploaded Orders File:", orders_file.name)
    st.write("Uploaded Current Stock File:", current_stock_file.name)
    st.write("Uploaded Product Master File:", product_master_file.name)

    # Load data using flexible loader
    orders = load_file(orders_file)
    current_stock = load_file(current_stock_file)
    product_master = load_file(product_master_file)

    if orders is not None and current_stock is not None and product_master is not None:
        # Ensure correct date format
        orders['Order_Date'] = pd.to_datetime(orders['Order_Date'])

        # Calculate ADD
        add_series = calculate_add(orders)

        # Merge dataframes
        df = current_stock.merge(product_master, on='Product')
        df = df.merge(add_series.rename('ADD'), on='Product', how='left').fillna(0)

        # Calculate ROP & Projected Inventory
        df['ROP'] = calculate_rop(df['ADD'], df['Lead_Time_Days'], df['Safety_Stock'])
        open_orders = orders[orders['Status'] == 'Open'].groupby('Product')['Quantity'].sum().rename('Open_Orders')
        df = df.merge(open_orders, on='Product', how='left').fillna(0)

        df['Projected_Inventory'] = df['Current_Stock'] - df['Open_Orders']
        df['Stock_Status'] = df.apply(lambda x: 'Reorder Needed' if x['Projected_Inventory'] < x['ROP'] else 'OK', axis=1)

        # -----------------------------
        # Dashboard KPIs
        # -----------------------------
        total_inventory = df['Current_Stock'].sum()
        total_open_orders = df['Open_Orders'].sum()
        items_below_rop = (df['Stock_Status'] == 'Reorder Needed').sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Inventory", total_inventory)
        col2.metric("Total Open Orders", total_open_orders)
        col3.metric("Items Below ROP", items_below_rop)

        # -----------------------------
        # Charts
        # -----------------------------
        st.subheader("Current Stock vs ROP")
        chart_data = df[['Product', 'Current_Stock', 'ROP']].melt(id_vars='Product', var_name='Type', value_name='Quantity')
        fig = px.bar(chart_data, x='Product', y='Quantity', color='Type', barmode='group', title="Stock vs Reorder Point")
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------
        # Detailed Table
        # -----------------------------
        st.subheader("Inventory Planning Table")
        st.dataframe(df[['Product', 'Current_Stock', 'Open_Orders', 'Projected_Inventory', 'ROP', 'Stock_Status']])

else:
    st.warning("Please upload all required files to proceed.")
