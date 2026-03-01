import streamlit as st
import pymssql
import pandas as pd
from streamlit_calendar import calendar

st.set_page_config(layout="wide", page_title="Infin Tradelog Ultra")

# --- THE "HARD UI" PRODUCTION CSS ---
st.markdown("""
    <style>
    /* 1. SOLID MECHANICAL GRID */
    .fc-theme-standard td, 
    .fc-theme-standard th,
    .fc-scrollgrid,
    .fc-scrollgrid-section td,
    .fc-scrollgrid-section th { 
        border: 2px solid #000000 !important; 
    }
    
    /* 2. EXTRA BOLD DATE NUMBERS */
    .fc-daygrid-day-number, 
    .fc-col-header-cell-cushion { 
        font-weight: 900 !important; 
        color: #000000 !important;
        font-size: 1.1rem !important;
    }

    /* 3. BOLD NAVIGATION BAR */
    .stButton button { 
        font-weight: 900 !important; 
        text-transform: uppercase;
        border: 2.5px solid #000000 !important;
        box-shadow: 2px 2px 0px #000000;
    }
    
    /* 4. DEFINED HERO CARDS */
    .metric-card {
        background: #ffffff; padding: 24px; border-radius: 4px;
        border: 2.5px solid #000000; box-shadow: 8px 8px 0px #000000;
        flex: 1; text-align: center;
    }
    .metric-value { font-size: 42px !important; font-weight: 900 !important; }
    .metric-label { font-weight: 900; color: #000000; text-transform: uppercase; }

    /* 5. SOLID STATUS BARS */
    .fc-event { margin: 2px 0 !important; border-radius: 0 !important; border: 1px solid #000 !important; }
    .fc-event-title { font-weight: 900 !important; font-size: 1.1rem !important; }
    
    /* 6. CLEAN BOUNDARIES */
    .fc-day-other { visibility: hidden !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE CONNECTION (REMOVED CREDENTIALS) ---
@st.cache_data
def get_data():
    # Use st.secrets for deployment!
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
        st.error("Database Connection Failed. Check your Streamlit Secrets.")
        return pd.DataFrame()

try:
    df = get_data()

    # --- TOP ROW: CLICKABLE BOLD MONTHS ---
    months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if 'selected_month_idx' not in st.session_state:
        st.session_state.selected_month_idx = 1 # Start at Jan

    cols = st.columns(12)
    for i, month_name in enumerate(months_list):
        if cols[i].button(month_name, use_container_width=True, 
                          type="primary" if st.session_state.selected_month_idx == i + 1 else "secondary"):
            st.session_state.selected_month_idx = i + 1
            st.rerun()

    m_num = st.session_state.selected_month_idx
    selected_month_full = pd.to_datetime(f"2026-{m_num:02d}-01").strftime('%B')

    # --- DATA CALCULATIONS ---
    ytd_total = df['DailyTotalPnL'].sum()
    month_df = df[df['CleanDate'].dt.month == m_num].copy()
    monthly_pnl = month_df['DailyTotalPnL'].sum()
    
    month_df['WeekOfYear'] = month_df['CleanDate'].dt.isocalendar().week
    weekly_sums = month_df.groupby('WeekOfYear')['DailyTotalPnL'].sum()

    # --- BOLD HERO METRICS ---
    ytd_color = '#DC2626' if ytd_total < 0 else '#059669'
    month_color = '#DC2626' if monthly_pnl < 0 else '#059669'
    
    st.markdown(f"""
        <div style="display: flex; gap: 30px; margin-bottom: 40px;">
            <div class="metric-card">
                <div class="metric-label">Year To Date Total</div>
                <div class="metric-value" style="color: {ytd_color}">${ytd_total:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">{selected_month_full.upper()} P&L TOTAL</div>
                <div class="metric-value" style="color: {month_color}">${monthly_pnl:,.2f}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- CALENDAR PROCESSING ---
    calendar_events = []
    for _, row in month_df.iterrows():
        # COLOR LOGIC: 0.00 is Green
        c = "#059669" if row['DailyTotalPnL'] >= 0 else "#DC2626"
        calendar_events.append({
            "title": f"${row['DailyTotalPnL']:,.0f}",
            "start": row['CleanDate'].strftime('%Y-%m-%d'),
            "backgroundColor": c, "display": "block"
        })

    # Saturday Weekly Injection
    start_date = pd.to_datetime(f"2026-{m_num:02d}-01")
    end_date = start_date + pd.offsets.MonthEnd(0)
    saturdays = pd.date_range(start=start_date, end=end_date, freq='W-SAT')
    
    for sat in saturdays:
        week_key = sat.isocalendar().week
        w_total = weekly_sums.get(week_key, 0)
        w_color = "#059669" if w_total >= 0 else "#DC2626"
        calendar_events.append({
            "title": f"WEEKLY: ${w_total:,.0f}",
            "start": sat.strftime('%Y-%m-%d'),
            "backgroundColor": "transparent", "textColor": w_color, "display": "block"
        })

    # --- RENDER ---
    calendar(events=calendar_events, options={
        "initialDate": f"2026-{m_num:02d}-01",
        "headerToolbar": {"left": "", "center": "", "right": ""},
        "showNonCurrentDates": False,
        "fixedWeekCount": False,
        "height": "auto"
    })

except Exception as e:
    st.write("Please connect your database to see your trades.")