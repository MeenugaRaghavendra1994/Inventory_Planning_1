import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------
# Helper Functions
# -----------------------------
def calculate_total_quantity_sold(sales_df, days=30):
    """
    Calculate total Quantity Sold for the last 'days'.
    """
    recent_sales = sales_df[sales_df['Date'] >= (datetime.today() - timedelta(days=days))]
    total_quantity_sold = recent_sales.groupby('SKU')['Quantity_Sold'].sum()
    return total_quantity_sold

def calculate_reorder_point(total_quantity_sold, lead_time, safety_stock):
    """
    Calculate Reorder Point (ROP).
    """
    return (total_quantity_sold * lead_time) + safety_stock

# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="Inventory Dashboard", layout="wide")

st.title("📊 Inventory & Sales Dashboard")

# File uploaders for sales and inventory
sales_file = st.file_uploader("Upload Sales Data (CSV/Excel)", type=['csv', 'xlsx'])
inventory_file = st.file_uploader("Upload Inventory Data (CSV/Excel)", type=['csv', 'xlsx'])

if sales_file and inventory_file:
    # Load Sales Data
    if sales_file.name.endswith('.csv'):
        sales_df = pd.read_csv(sales_file)
    else:
        sales_df = pd.read_excel(sales_file)
    
    # Load Inventory Data
    if inventory_file.name.endswith('.csv'):
        inventory_df = pd.read_csv(inventory_file)
    else:
        inventory_df = pd.read_excel(inventory_file)

    # Convert Date column to datetime
    sales_df['Date'] = pd.to_datetime(sales_df['Date'])

    # Calculate total quantity sold for each SKU
    total_quantity_sold = calculate_total_quantity_sold(sales_df)
    
    # Merge with inventory
    merged_df = inventory_df.merge(total_quantity_sold, on='SKU', how='left')
    merged_df.rename(columns={'Quantity_Sold': 'Total_Quantity_Sold'}, inplace=True)

    # Calculate ROP
    merged_df['ROP'] = merged_df.apply(
        lambda row: calculate_reorder_point(row['Total_Quantity_Sold'], row['Lead_Time'], row['Safety_Stock']),
        axis=1
    )

    # Days of Inventory Remaining
    merged_df['Days_Inventory_Left'] = merged_df['Current_Stock'] / merged_df['Total_Quantity_Sold']

    # Show table
    st.subheader("📋 Inventory Summary")
    st.dataframe(merged_df.style.format({
        "Total_Quantity_Sold": "{:.0f}",
        "ROP": "{:.2f}",
        "Days_Inventory_Left": "{:.1f}"
    }))

    # Visualization - Current Stock vs ROP
    st.subheader("📊 Stock vs Reorder Point")
    fig = px.bar(
        merged_df,
        x='SKU',
        y=['Current_Stock', 'ROP'],
        barmode='group',
        title="Current Stock vs Reorder Point",
        labels={'value': 'Quantity', 'variable': 'Metric'}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Visualization - Sales Trend
    st.subheader("📈 Sales Trend (Last 30 Days)")
    sales_trend = sales_df.groupby('Date')['Quantity_Sold'].sum().reset_index()
    fig2 = px.line(
        sales_trend,
        x='Date',
        y='Quantity_Sold',
        title="Daily Sales Trend",
        labels={'Quantity_Sold': 'Units Sold'}
    )
    st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("Please upload both Sales and Inventory files to see the dashboard.")
