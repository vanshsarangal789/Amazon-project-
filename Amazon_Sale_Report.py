"""
Amazon Sale Report — Interactive Dashboard
Run with:  streamlit run app.py
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Amazon Sales Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# THEME / COLORS
# ----------------------------------------------------------------------------
PRIMARY = "#FF9900"      # amazon orange
SECONDARY = "#146EB4"    # amazon blue
DARK = "#2B82F5"         # amazon navy
ACCENT = "#37475A"
BG = "#FFFFFF"
CARD_BG = "#161B22"
SUCCESS = "#2ECC71"
DANGER = "#E74C3C"

COLOR_SEQ = ["#FF9900", "#146EB4", "#37475A", "#F2C14E", "#2ECC71",
             "#E74C3C", "#9B59B6", "#1ABC9C", "#E67E22"]

px.defaults.color_discrete_sequence = COLOR_SEQ
px.defaults.template = "plotly_dark"

st.markdown(f"""
<style>
    .stApp {{ background-color:{BG}; }}
    div[data-testid="stMetric"] {{
        background: linear-gradient(135deg, {CARD_BG} 0%, #1e2530 100%);
        border: 1px solid #2a3140;
        border-left: 4px solid {PRIMARY};
        padding: 15px 15px 10px 15px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }}
    div[data-testid="stMetricValue"] {{ color:{PRIMARY}; font-weight:700; }}
    h1, h2, h3 {{ color: #FAFAFA; }}
    .main-header {{
        background: linear-gradient(90deg, {DARK} 0%, {ACCENT} 100%);
        padding: 18px 25px; border-radius: 12px; margin-bottom: 18px;
        border-left: 6px solid {PRIMARY};
    }}
    section[data-testid="stSidebar"] {{ background-color:{DARK}; }}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------
@st.cache_data
def load_data(path="Amazon Sale Report.csv"):
    df = pd.read_csv(path, low_memory=False)

    # Clean up
    df["Date"] = pd.to_datetime(df["Date"], format="%m-%d-%y", errors="coerce")
    df = df.dropna(subset=["Date"])
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df = df[df["Amount"].notna() & (df["Amount"] > 0)]  # keep valid revenue rows
    df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)

    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Weekday"] = df["Date"].dt.day_name()
    df["is_returned"] = df["Status"].str.contains("Return|Rejected|Lost|Damaged", case=False, na=False)
    df["is_cancelled"] = df["Status"].str.contains("Cancelled", case=False, na=False)
    df["B2B"] = df["B2B"].map({True: "B2B", False: "B2C"})
    df["ship-state"] = df["ship-state"].astype(str).str.title().str.strip()
    df["ship-city"] = df["ship-city"].astype(str).str.title().str.strip()

    return df

df_raw = load_data()

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.markdown(f"""
<div class="main-header">
    <h1 style="margin:0;">📦 Amazon Sales Performance Dashboard</h1>
    <p style="margin:0; color:#CBD5E1;">
        End-to-end view of orders, revenue, fulfilment and shipping performance —
        {df_raw['Date'].min().strftime('%d %b %Y')} to {df_raw['Date'].max().strftime('%d %b %Y')}
    </p>
</div>
""", unsafe_allow_html=True)

with st.expander("ℹ️  About this dataset", expanded=True):
    st.markdown(f"""
This dashboard analyses **{len(df_raw):,} Amazon.in orders** covering apparel and accessories
(T-shirts, Shirts, Blazers, Trousers, Shoes, Watches, Wallets, Socks, Perfumes) sold via
**Merchant** and **Amazon**-fulfilled channels, both **B2B** and **B2C**.

Use the filters in the sidebar to slice by date, order status, category, fulfilment type,
sales channel, and shipping state. All KPIs and charts below update live with your selection.
""")

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------------------------------------
st.sidebar.header("🔍 Filters")

min_d, max_d = df_raw["Date"].min().date(), df_raw["Date"].max().date()
date_range = st.sidebar.date_input("Order Date Range", (min_d, max_d), min_value=min_d, max_value=max_d)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_d, max_d

category_sel = st.sidebar.multiselect("Category", sorted(df_raw["Category"].unique()), default=[])
status_sel = st.sidebar.multiselect("Order Status", sorted(df_raw["Status"].unique()), default=[])
fulfilment_sel = st.sidebar.multiselect("Fulfilment", sorted(df_raw["Fulfilment"].unique()), default=[])
channel_sel = st.sidebar.multiselect("Sales Channel", sorted(df_raw["Sales Channel"].unique()), default=[])
b2b_sel = st.sidebar.multiselect("Business Type", sorted(df_raw["B2B"].unique()), default=[])
state_sel = st.sidebar.multiselect("Ship-to State", sorted(df_raw["ship-state"].dropna().unique()), default=[])
size_sel = st.sidebar.multiselect("Size", sorted(df_raw["Size"].unique()), default=[])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset all filters"):
    st.rerun()

# Apply filters
df = df_raw[(df_raw["Date"].dt.date >= start_date) & (df_raw["Date"].dt.date <= end_date)]
if category_sel:   df = df[df["Category"].isin(category_sel)]
if status_sel:      df = df[df["Status"].isin(status_sel)]
if fulfilment_sel:  df = df[df["Fulfilment"].isin(fulfilment_sel)]
if channel_sel:      df = df[df["Sales Channel"].isin(channel_sel)]
if b2b_sel:          df = df[df["B2B"].isin(b2b_sel)]
if state_sel:        df = df[df["ship-state"].isin(state_sel)]
if size_sel:         df = df[df["Size"].isin(size_sel)]

if df.empty:
    st.warning("No data matches the selected filters. Please broaden your selection.")
    st.stop()

# ----------------------------------------------------------------------------
# KPI CARDS
# ----------------------------------------------------------------------------
total_revenue = df["Amount"].sum()
total_orders = df["Order ID"].nunique()
total_qty = df["Qty"].sum()
aov = total_revenue / total_orders if total_orders else 0
cancel_rate = df["is_cancelled"].mean() * 100
return_rate = df["is_returned"].mean() * 100

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("💰 Total Revenue", f"₹{total_revenue:,.0f}")
k2.metric("🧾 Total Orders", f"{total_orders:,}")
k3.metric("📦 Units Sold", f"{int(total_qty):,}")
k4.metric("💳 Avg Order Value", f"₹{aov:,.0f}")
k5.metric("❌ Cancellation Rate", f"{cancel_rate:.1f}%")
k6.metric("↩️ Return/Issue Rate", f"{return_rate:.1f}%")

st.markdown("---")

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Sales Trends", "🛍️ Product & Category", "🚚 Fulfilment & Status", "🗺️ Geography"])

# ---- TAB 1: SALES TRENDS ----------------------------------------------------
with tab1:
    c1, c2 = st.columns((2, 1))

    with c1:
        daily = df.groupby(df["Date"].dt.date).agg(Revenue=("Amount", "sum"), Orders=("Order ID", "nunique")).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily["Date"], y=daily["Revenue"], name="Revenue (₹)",
                                  mode="lines", line=dict(color=PRIMARY, width=2), fill="tozeroy",
                                  fillcolor="rgba(255,153,0,0.15)"))
        fig.update_layout(title="Daily Revenue Trend", height=380,
                           xaxis_title=None, yaxis_title="Revenue (₹)",
                           margin=dict(t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        wk = df.groupby("Weekday").agg(Revenue=("Amount", "sum")).reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]).reset_index()
        fig = px.bar(wk, x="Weekday", y="Revenue", title="Revenue by Weekday",
                     color="Revenue", color_continuous_scale=["#37475A", PRIMARY])
        fig.update_layout(height=380, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        monthly = df.groupby("Month").agg(Orders=("Order ID", "nunique"), Revenue=("Amount", "sum")).reset_index()
        fig = px.bar(monthly, x="Month", y="Orders", title="Monthly Order Volume",
                     text_auto=True, color_discrete_sequence=[SECONDARY])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        b2b_rev = df.groupby("B2B").agg(Revenue=("Amount", "sum")).reset_index()
        fig = px.pie(b2b_rev, names="B2B", values="Revenue", title="Revenue: B2B vs B2C", hole=0.55)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

# ---- TAB 2: PRODUCT & CATEGORY ---------------------------------------------
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        cat = df.groupby("Category").agg(Revenue=("Amount", "sum"), Qty=("Qty", "sum")).sort_values("Revenue", ascending=True).reset_index()
        fig = px.bar(cat, x="Revenue", y="Category", orientation="h", title="Revenue by Category",
                     color="Revenue", color_continuous_scale=["#146EB4", "#FF9900"], text_auto=".2s")
        fig.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        size_dist = df.groupby("Size").agg(Qty=("Qty", "sum")).reset_index()
        fig = px.pie(size_dist, names="Size", values="Qty", title="Units Sold by Size", hole=0.4)
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        tree = df.groupby(["Category", "Size"]).agg(Revenue=("Amount", "sum")).reset_index()
        fig = px.treemap(tree, path=["Category", "Size"], values="Revenue",
                          title="Category → Size Revenue Breakdown",
                          color="Revenue", color_continuous_scale=["#37475A", PRIMARY])
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        qty_cat = df.groupby("Category").agg(Qty=("Qty", "sum")).sort_values("Qty", ascending=False).reset_index()
        fig = px.bar(qty_cat, x="Category", y="Qty", title="Units Sold by Category",
                     color="Category", text_auto=True)
        fig.update_layout(height=420, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ---- TAB 3: FULFILMENT & STATUS --------------------------------------------
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        status_ct = df["Status"].value_counts().reset_index()
        status_ct.columns = ["Status", "Orders"]
        fig = px.bar(status_ct, x="Orders", y="Status", orientation="h", title="Orders by Status",
                     color="Orders", color_continuous_scale=["#37475A", "#E74C3C", PRIMARY])
        fig.update_layout(height=450, coloraxis_showscale=False, yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fulf = df.groupby("Fulfilment").agg(Revenue=("Amount", "sum"), Orders=("Order ID", "nunique")).reset_index()
        fig = px.pie(fulf, names="Fulfilment", values="Revenue", title="Revenue by Fulfilment Type", hole=0.5)
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        cour = df["Courier Status"].value_counts().reset_index()
        cour.columns = ["Courier Status", "Orders"]
        fig = px.bar(cour, x="Courier Status", y="Orders", title="Courier Status Breakdown",
                     color="Courier Status", text_auto=True)
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        chan = df.groupby("Sales Channel").agg(Revenue=("Amount", "sum")).reset_index()
        fig = px.bar(chan, x="Sales Channel", y="Revenue", title="Revenue by Sales Channel",
                     color="Sales Channel", text_auto=".2s")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ---- TAB 4: GEOGRAPHY --------------------------------------------------------
with tab4:
    c1, c2 = st.columns(2)
    with c1:
        top_states = df.groupby("ship-state").agg(Revenue=("Amount", "sum")).sort_values("Revenue", ascending=False).head(10).reset_index()
        fig = px.bar(top_states, x="Revenue", y="ship-state", orientation="h",
                     title="Top 10 States by Revenue", color="Revenue",
                     color_continuous_scale=["#146EB4", PRIMARY])
        fig.update_layout(height=450, coloraxis_showscale=False, yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        top_cities = df.groupby("ship-city").agg(Revenue=("Amount", "sum")).sort_values("Revenue", ascending=False).head(10).reset_index()
        fig = px.bar(top_cities, x="Revenue", y="ship-city", orientation="h",
                     title="Top 10 Cities by Revenue", color="Revenue",
                     color_continuous_scale=["#37475A", "#2ECC71"])
        fig.update_layout(height=450, coloraxis_showscale=False, yaxis=dict(categoryorder="total ascending"))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 State-level Summary Table")
    state_tbl = df.groupby("ship-state").agg(
        Revenue=("Amount", "sum"), Orders=("Order ID", "nunique"), Units=("Qty", "sum")
    ).sort_values("Revenue", ascending=False).reset_index()
    state_tbl["Revenue"] = state_tbl["Revenue"].round(0)
    st.dataframe(state_tbl, use_container_width=True, height=350)

st.markdown("---")
st.caption("Dashboard built with Streamlit + Plotly · Data: Amazon_Sale_Report.csv")