import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_average_daily_demand(sales_df, days=30):
    """
    Calculate Average Daily Demand (ADD).
    If quantity_sold represents total sales for the period, 
    we divide by the number of days to get a per-day rate.
    """
    # Filter last 'days' worth of data
    cutoff_date = datetime.today() - timedelta(days=days)
    recent_sales = sales_df[sales_df['date'] >= cutoff_date]

    if recent_sales.empty:
        st.warning("⚠️ No sales data available for the last 30 days.")
        return pd.DataFrame(columns=['sku', 'average_daily_demand'])

    # Group by SKU and calculate total quantity sold
    grouped_sales = recent_sales.groupby('sku', as_index=False)['quantity_sold'].sum()
    grouped_sales['average_daily_demand'] = grouped_sales['quantity_sold'] / days

    return grouped_sales[['sku', 'average_daily_demand']]

def calculate_reorder_point(add, lead_time, safety_stock):
    """Calculate Reorder Point (ROP)."""
    return (add * lead_time) + safety_stock

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Inventory Dashboard", layout="wide")
st.title("📊 Inventory & Sales Dashboard")

# Upload files
sales_file = st.file_uploader("Upload Sales Data (CSV or Excel)", type=['csv', 'xlsx'])
inventory_file = st.file_uploader("Upload Inventory Data (CSV or Excel)", type=['csv', 'xlsx'])

# -----------------------------
# Main Logic
# -----------------------------
if sales_file and inventory_file:
    # --- Load Sales Data ---
    sales_df = pd.read_csv(sales_file) if sales_file.name.endswith('.csv') else pd.read_excel(sales_file)
    sales_df.columns = sales_df.columns.str.strip().str.lower()

    required_sales_cols = {'date', 'sku', 'quantity_sold'}
    if not required_sales_cols.issubset(sales_df.columns):
        st.error(f"❌ Sales file must contain columns: {required_sales_cols}")
        st.stop()

    # Convert date column
    sales_df['date'] = pd.to_datetime(sales_df['date'], errors='coerce')

    # --- Load Inventory Data ---
    inventory_df = pd.read_csv(inventory_file) if inventory_file.name.endswith('.csv') else pd.read_excel(inventory_file)
    inventory_df.columns = inventory_df.columns.str.strip().str.lower()

    required_inventory_cols = {'sku', 'current_stock', 'safety_stock', 'lead_time'}
    if not required_inventory_cols.issubset(inventory_df.columns):
        st.error(f"❌ Inventory file must contain columns: {required_inventory_cols}")
        st.stop()

    # Clean SKU values
    inventory_df['sku'] = inventory_df['sku'].astype(str).str.strip().str.lower()
    sales_df['sku'] = sales_df['sku'].astype(str).str.strip().str.lower()

    # --- Calculate Average Daily Demand (ADD) ---
    avg_daily_demand = calculate_average_daily_demand(sales_df)

    st.write("**Debug: Average Daily Demand DataFrame**")
    st.write(avg_daily_demand.head())

    # --- Merge with Inventory Data ---
    merged_df = inventory_df.merge(avg_daily_demand, on='sku', how='left')

    # If ADD is missing, fill with 0
    if 'average_daily_demand' not in merged_df.columns:
        merged_df['average_daily_demand'] = 0
    else:
        merged_df['average_daily_demand'] = merged_df['average_daily_demand'].fillna(0)

    # --- Calculate ROP & Days Inventory Left ---
    merged_df['rop'] = merged_df.apply(
        lambda row: calculate_reorder_point(row['average_daily_demand'], row['lead_time'], row['safety_stock']),
        axis=1
    )

    merged_df['days_inventory_left'] = merged_df.apply(
        lambda row: row['current_stock'] / row['average_daily_demand'] if row['average_daily_demand'] > 0 else None,
        axis=1
    )

    # --- Display Final Table ---
    st.subheader("📋 Inventory Summary")
    st.dataframe(
        merged_df.style.format({
            "average_daily_demand": "{:.2f}",
            "rop": "{:.2f}",
            "days_inventory_left": "{:.1f}"
        })
    )

    # --- Visualization 1: Stock vs ROP ---
    st.subheader("📊 Stock vs Reorder Point")
    fig = px.bar(
        merged_df,
        x='sku',
        y=['current_stock', 'rop'],
        barmode='group',
        title="Current Stock vs Reorder Point",
        labels={'value': 'Quantity', 'variable': 'Metric'}
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Visualization 2: Sales Trend ---
    st.subheader("📈 Sales Trend (Last 30 Days)")
    sales_trend = sales_df.groupby('date', as_index=False)['quantity_sold'].sum()
    fig2 = px.line(
        sales_trend,
        x='date',
        y='quantity_sold',
        title="Daily Sales Trend",
        labels={'quantity_sold': 'Units Sold'}
    )
    st.plotly_chart(fig2, use_container_width=True)

    # --- Debugging Section ---
    with st.expander("Debug Information"):
        st.write("Sales Data Columns:", list(sales_df.columns))
        st.write("Inventory Data Columns:", list(inventory_df.columns))
        st.write("Merged DataFrame Columns:", list(merged_df.columns))
        st.write("Sample Merged Data:", merged_df.head())

else:
    st.info("Please upload both Sales and Inventory files to generate the dashboard.")
