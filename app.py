import streamlit as st
import pymssql
import pandas as pd
from streamlit_calendar import calendar

st.set_page_config(layout="wide", page_title="Infin Tradelog Ultra")

# --- THE "HARD UI" PRODUCTION CSS ---
st.markdown("""
    <style>
    /* 1. SOLID MECHANICAL GRID */
    .fc-theme-standard td, .fc-theme-standard th, .fc-scrollgrid { border: 2px solid #000 !important; }
    .fc-daygrid-day-number { font-weight: 900 !important; color: #000 !important; font-size: 1.1rem !important; }
    
    /* 2. HERO CARDS */
    .metric-card {
        background: #ffffff; padding: 24px; border: 2.5px solid #000000;
        box-shadow: 8px 8px 0px #000000; flex: 1; text-align: center;
    }
    .metric-value { font-size: 42px !important; font-weight: 900 !important; }

    /* 3. MOBILE OVERRIDES */
    @media (max-width: 768px) {
        .metric-value { font-size: 24px !important; }
        .metric-card { padding: 12px !important; box-shadow: 4px 4px 0px #000 !important; }
        .stButton button { font-size: 10px !important; padding: 2px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def get_data():
    try:
        conn = pymssql.connect(
            server=st.secrets["db_server"],
            port=st.secrets["db_port"],
            user=st.secrets["db_user"],
            password=st.secrets["db_password"],
            database=st.secrets["db_name"]
        )
        df = pd.read_sql("SELECT * FROM v_TradeZella_Calendar", conn)
        conn.close()
        df['CleanDate'] = pd.to_datetime(df['CleanDate'])
        return df
    except:
        return pd.DataFrame()

df = get_data()

if not df.empty:
    # --- NAVIGATION ---
    months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if 'selected_month_idx' not in st.session_state:
        st.session_state.selected_month_idx = 1

    cols = st.columns(12)
    for i, month_name in enumerate(months_list):
        if cols[i].button(month_name, use_container_width=True, 
                          type="primary" if st.session_state.selected_month_idx == i + 1 else "secondary"):
            st.session_state.selected_month_idx = i + 1
            st.rerun()

    m_num = st.session_state.selected_month_idx
    selected_month_name = pd.to_datetime(f"2026-{m_num:02d}-01").strftime('%B')
    
    # --- DATA CALCS ---
    ytd_total = df['DailyTotalPnL'].sum()
    month_df = df[df['CleanDate'].dt.month == m_num].copy()
    monthly_pnl = month_df['DailyTotalPnL'].sum()
    
    # --- HERO METRICS ---
    st.markdown(f"""
        <div style="display: flex; gap: 20px; margin-bottom: 30px;">
            <div class="metric-card">
                <div style="font-weight:900; font-size:12px;">YTD TOTAL</div>
                <div class="metric-value" style="color:{'#059669' if ytd_total >=0 else '#DC2626'}">${ytd_total:,.2f}</div>
            </div>
            <div class="metric-card">
                <div style="font-weight:900; font-size:12px;">{selected_month_name.upper()} TOTAL</div>
                <div class="metric-value" style="color:{'#059669' if monthly_pnl >=0 else '#DC2626'}">${monthly_pnl:,.2f}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- THE SMART VIEW TOGGLE ---
    view_mode = st.radio("Display View", ["Desktop Calendar", "iPhone List Mode"], horizontal=True, label_visibility="collapsed")

    if view_mode == "iPhone List Mode":
        # Sort newest trades to the top for the phone
        sorted_df = month_df.sort_values('CleanDate', ascending=False)
        for _, row in sorted_df.iterrows():
            c = "#059669" if row['DailyTotalPnL'] >= 0 else "#DC2626"
            st.markdown(f"""
                <div style="border: 2.5px solid #000; border-left: 15px solid {c}; padding: 15px; margin-bottom: 15px; background: #fff; box-shadow: 4px 4px 0px #000;">
                    <div style="font-weight: 900; font-size: 13px; color: #555;">{row['CleanDate'].strftime('%A, %b %d')}</div>
                    <div style="font-size: 30px; font-weight: 900; color: {c};">${row['DailyTotalPnL']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # CALENDAR WITH SATURDAY TOTALS INJECTED
        calendar_events = []
        for _, row in month_df.iterrows():
            c = "#059669" if row['DailyTotalPnL'] >= 0 else "#DC2626"
            calendar_events.append({"title": f"${row['DailyTotalPnL']:,.0f}", "start": row['CleanDate'].strftime('%Y-%m-%d'), "backgroundColor": c})

        # Inject Weekly Saturday Totals
        month_df['WeekOfYear'] = month_df['CleanDate'].dt.isocalendar().week
        weekly_sums = month_df.groupby('WeekOfYear')['DailyTotalPnL'].sum()
        saturdays = pd.date_range(start=f"2026-{m_num:02d}-01", end=pd.to_datetime(f"2026-{m_num:02d}-01") + pd.offsets.MonthEnd(0), freq='W-SAT')
        
        for sat in saturdays:
            w_total = weekly_sums.get(sat.isocalendar().week, 0)
            w_color = "#059669" if w_total >= 0 else "#DC2626"
            calendar_events.append({
                "title": f"WEEKLY: ${w_total:,.0f}", 
                "start": sat.strftime('%Y-%m-%d'), 
                "backgroundColor": "transparent", "textColor": w_color, "display": "block"
            })

        calendar(events=calendar_events, options={"initialDate": f"2026-{m_num:02d}-01", "height": "auto", "headerToolbar": False})

else:
    st.error("Connection live but no data found. Check your TradeZella view.")