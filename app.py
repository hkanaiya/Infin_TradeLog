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
    
    /* 2. EXTRA BOLD NUMBERS */
    .fc-daygrid-day-number { font-weight: 900 !important; color: #000 !important; }

    /* 3. HERO CARDS */
    .metric-card {
        background: #fff; padding: 20px; border: 2.5px solid #000;
        box-shadow: 6px 6px 0px #000; text-align: center; flex: 1;
    }
    .metric-value { font-size: 38px !important; font-weight: 900 !important; }
    
    /* 4. MOBILE-SPECIFIC FIXES */
    @media (max-width: 768px) {
        .metric-value { font-size: 22px !important; }
        .stButton button { font-size: 10px !important; padding: 5px !important; }
        /* Hide the calendar on very small screens to prevent the "$50" cut-off */
        .hide-on-mobile { display: none !important; }
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
    month_df = df[df['CleanDate'].dt.month == m_num].sort_values('CleanDate', ascending=False)
    
    # --- HERO METRICS ---
    ytd_total = df['DailyTotalPnL'].sum()
    monthly_pnl = month_df['DailyTotalPnL'].sum()
    
    st.markdown(f"""
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div class="metric-card">
                <div style="font-weight:900; font-size:12px;">YTD TOTAL</div>
                <div class="metric-value" style="color:{'#059669' if ytd_total >=0 else '#DC2626'}">${ytd_total:,.0f}</div>
            </div>
            <div class="metric-card">
                <div style="font-weight:900; font-size:12px;">MONTH TOTAL</div>
                <div class="metric-value" style="color:{'#059669' if monthly_pnl >=0 else '#DC2626'}">${monthly_pnl:,.0f}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- THE MOBILE SOLUTION: SELECTOR ---
    view_mode = st.radio("Display Mode", ["Desktop Calendar", "Mobile List"], label_visibility="collapsed")

    if view_mode == "Mobile List":
        for _, row in month_df.iterrows():
            c = "#059669" if row['DailyTotalPnL'] >= 0 else "#DC2626"
            st.markdown(f"""
                <div style="border: 2.5px solid #000; border-left: 12px solid {c}; 
                            padding: 15px; margin-bottom: 12px; background: #fff; 
                            box-shadow: 4px 4px 0px #000;">
                    <div style="font-weight: 900; font-size: 12px; color: #666;">{row['CleanDate'].strftime('%A, %b %d')}</div>
                    <div style="font-size: 32px; font-weight: 900; color: {c};">${row['DailyTotalPnL']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # DESKTOP CALENDAR RENDER
        calendar_events = []
        for _, row in month_df.iterrows():
            c = "#059669" if row['DailyTotalPnL'] >= 0 else "#DC2626"
            calendar_events.append({"title": f"${row['DailyTotalPnL']:,.0f}", "start": row['CleanDate'].strftime('%Y-%m-%d'), "backgroundColor": c})
        
        calendar(events=calendar_events, options={"initialDate": f"2026-{m_num:02d}-01", "height": "auto"})

else:
    st.error("No data found. Check your SQL connection.")