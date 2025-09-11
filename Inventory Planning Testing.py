import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_average_daily_demand(sales_df, days=30):
    """
    Calculate Average Daily Demand (ADD) based on last 'days' of sales.
    """
    # Filter only the last 'days' of data
    cutoff_date = datetime.today() - timedelta(days=days)
    recent_sales = sales_df[sales_df['date'] >= cutoff_date]

    # Group by SKU and calculate ADD
    avg_daily_demand = recent_sales.groupby('sku', as_index=False)['quantity_sold'].sum()
    avg_daily_demand['average_daily_demand'] = avg_daily_demand['quantity_sold'] / days

    return avg_daily_demand[['sku', 'average_daily_demand']]

def calculate_reorder_point(add, lead_time, safety_stock):
    """
    Calculate Reorder Point (ROP).
    """
    return (add * lead_time) + safety_stock

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Inventory Dashboard", layout="wide")

st.title("📊 Inventory & Sales Dashboard")

# File uploaders for sales and inventory
sales_file = st.file_uploader("Upload Sales Data (CSV/Excel)", type=['csv', 'xlsx'])
inventory_file = st.file_uploader("Upload Inventory Data (CSV/Excel)", type=['csv', 'xlsx'])

if sales_file and inventory_file:
    # -----------------------------
    # Load and Clean Sales Data
    # -----------------------------
    if sales_file.name.endswith('.csv'):
        sales_df = pd.read_csv(sales_file)
    else:
        sales_df = pd.read_excel(sales_file)

    # Clean up column names
    sales_df.columns = sales_df.columns.str.strip().str.lower()

    # Ensure expected columns exist
    required_sales_cols = {'date', 'sku', 'quantity_sold'}
    if not required_sales_cols.issubset(set(sales_df.columns)):
        st.error(f"Sales file must contain columns: {required_sales_cols}")
        st.stop()

    # Convert date column
    sales_df['date'] = pd.to_datetime(sales_df['date'], errors='coerce')

    # -----------------------------
    # Load and Clean Inventory Data
    # -----------------------------
    if inventory_file.name.endswith('.csv'):
        inventory_df = pd.read_csv(inventory_file)
    else:
        inventory_df = pd.read_excel(inventory_file)

    inventory_df.columns = inventory_df.columns.str.strip().str.lower()

    required_inventory_cols = {'sku', 'current_stock', 'safety_stock', 'lead_time'}
    if not required_inventory_cols.issubset(set(inventory_df.columns)):
        st.error(f"Inventory file must contain columns: {required_inventory_cols}")
        st.stop()

    # -----------------------------
    # Calculate Metrics
    # -----------------------------
    avg_daily_demand = calculate_average_daily_demand(sales_df)

    # Merge ADD into inventory
    merged_df = inventory_df.merge(avg_daily_demand, on='sku', how='left')

    # Fill missing ADD with 0
    merged_df['average_daily_demand'] = merged_df['average_daily_demand'].fillna(0)

    # Calculate ROP
    merged_df['rop'] = merged_df.apply(
        lambda row: calculate_reorder_point(row['average_daily_demand'], row['lead_time'], row['safety_stock']),
        axis=1
    )

    # Calculate Days of Inventory Left
    merged_df['days_inventory_left'] = merged_df.apply(
        lambda row: row['current_stock'] / row['average_daily_demand'] if row['average_daily_demand'] > 0 else None,
        axis=1
    )

    # -----------------------------
    # Display Final Table
    # -----------------------------
    st.subheader("📋 Inventory Summary")
    st.dataframe(
        merged_df.style.format({
            "average_daily_demand": "{:.2f}",
            "rop": "{:.2f}",
            "days_inventory_left": "{:.1f}"
        })
    )

    # -----------------------------
    # Visualization 1: Current Stock vs ROP
    # -----------------------------
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

    # -----------------------------
    # Visualization 2: Sales Trend
    # -----------------------------
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

else:
    st.info("Please upload both Sales and Inventory files to see the dashboard.")
