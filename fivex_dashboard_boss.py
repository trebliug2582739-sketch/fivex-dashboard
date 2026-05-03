import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import calendar
import base64
import os

# ── Page config ────────────────────────────────────
st.set_page_config(
    page_title="The Brands Den | Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Background image ───────────────────────────────
def get_bg_base64():
    bg_path = os.path.join(os.path.dirname(__file__), "brands_den_dashboard_bg.png")
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

bg_b64 = get_bg_base64()
bg_css = f"""
background-image: url("data:image/png;base64,{bg_b64}");
background-size: cover;
background-position: center;
background-attachment: fixed;
""" if bg_b64 else "background-color: #05100e;"

# ── Color palette ──────────────────────────────────
C1 = "#036661"
C2 = "#062e24"
C3 = "#114945"
C4 = "#05100e"
C5 = "#6ba29f"
CTEXT   = "#e0f0ee"
CSUB    = "#6ba29f"
CBORDER = "#114945"

CHANNEL_ORDER  = ["bolcom", "shopify", "mediamarkt", "anwb", "amazon", "decathlon"]
CHANNEL_LABELS = {
    "bolcom": "Bol.com", "shopify": "Shopify",
    "mediamarkt": "MediaMarkt", "anwb": "ANWB",
    "amazon": "Amazon", "decathlon": "Decathlon"
}
CHANNEL_COLORS = [C1, C5, C3, "#1a6b5a", "#0d4a3f", "#2a8a7a"]

# ── Custom CSS ─────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
    .stApp {{ {bg_css} }}
    section[data-testid="stSidebar"] {{
        background: rgba(5,16,14,0.95) !important;
        border-right: 1px solid {CBORDER} !important;
    }}
    .stApp > header {{ background: transparent !important; }}
    .metric-card {{
        background: rgba(6,46,36,0.85);
        border: 1px solid {CBORDER};
        border-radius: 12px;
        padding: 14px 16px;
        backdrop-filter: blur(8px);
    }}
    .metric-label {{
        font-size: 10px; color: {CSUB}; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px;
    }}
    .metric-value {{ font-size: 22px; font-weight: 600; color: {CTEXT}; line-height: 1.2; }}
    .metric-delta-up   {{ font-size: 10px; color: #4ade80; margin-top: 4px; }}
    .metric-delta-down {{ font-size: 10px; color: #f87171; margin-top: 4px; }}
    .metric-delta-neu  {{ font-size: 10px; color: {CSUB};  margin-top: 4px; }}
    .section-title {{
        font-size: 14px; font-weight: 600; color: {C5};
        margin: 1.2rem 0 0.8rem 0; padding-bottom: 6px;
        border-bottom: 1px solid {CBORDER};
    }}
    .page-header {{ font-size: 26px; font-weight: 600; color: {CTEXT}; margin-bottom: 2px; }}
    .page-subtitle {{ font-size: 13px; color: {CSUB}; margin-bottom: 1.2rem; }}
    .stSidebar label, .stSidebar .stRadio label,
    .stSidebar p, .stSidebar span {{ color: {CTEXT} !important; }}
    .stSidebar h2, .stSidebar h3 {{ color: {C5} !important; }}
    div[data-testid="stSidebarNav"] {{display: none;}}
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(6,46,36,0.6)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=CTEXT, family="DM Sans"),
    margin=dict(l=0, r=0, t=10, b=0),
    legend=dict(font=dict(color=CTEXT)),
    xaxis=dict(gridcolor="rgba(107,162,159,0.15)", color=CSUB),
    yaxis=dict(gridcolor="rgba(107,162,159,0.15)", color=CSUB),
)

# ── Connect to Google Sheets ───────────────────────
@st.cache_resource
def get_gc():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "gcp_service_account" in st.secrets:
        creds_dict = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"],
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        }
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=900)
def load_sheet(sheet_name, tab_name):
    gc = get_gc()
    ws = gc.open(sheet_name).worksheet(tab_name)
    return pd.DataFrame(ws.get_all_records())

SHEET = "FiveX Dashboard Data"

@st.cache_data(ttl=900)
def load_all():
    try:
        orders    = load_sheet(SHEET, "orders")
        returns   = load_sheet(SHEET, "returns")
        ads       = load_sheet(SHEET, "ads")
        cancelled = load_sheet(SHEET, "cancelled")
        try: prod_info = load_sheet(SHEET, "product_info")
        except: prod_info = pd.DataFrame()
        return orders, returns, ads, cancelled, prod_info
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return [pd.DataFrame()]*5

# ── Helpers ────────────────────────────────────────
def get_weeks(year):
    weeks, d = [], datetime(year, 1, 1)
    d = d - timedelta(d.weekday())
    w = 1
    while d.year <= year and w <= 53:
        we = d + timedelta(6)
        weeks.append((w, d.date(), we.date()))
        d += timedelta(7); w += 1
    return weeks

def fmt_cur(v): return f"€{v:,.2f}"
def fmt_num(v): return f"{int(v):,}"

def to_num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def fdate(df, col, s, e):
    if df.empty or col not in df.columns: return df
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    return df[(df[col].dt.date >= s) & (df[col].dt.date <= e)]

def fch(df, ch, col="api_type"):
    if not ch or df.empty or col not in df.columns: return df
    return df[df[col].isin(ch)]

def mcard(label, value, delta=None, delta_type="neu"):
    cls = f"metric-delta-{delta_type}"
    arrow = "▲" if delta_type == "up" else ("▼" if delta_type == "down" else "")
    delta_html = f'<div class="{cls}">{arrow} {delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def delta_pct(curr, prev):
    if prev == 0: return None, "neu"
    pct = ((curr - prev) / prev) * 100
    return f"{abs(pct):.1f}% vs prev", "up" if pct >= 0 else "down"

# ── Sidebar ─────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:{C5}; margin-bottom:4px;'>📊 The Brands Den</h2>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:{CSUB}; font-size:11px; margin-bottom:12px;'>Sales Dashboard</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown(f"<div style='color:{C5}; font-size:12px; font-weight:600;'>📅 DATE FILTER</div>", unsafe_allow_html=True)
    ftype = st.radio("", ["Month","Week","Day","Date Range","Quick Select"], label_visibility="collapsed")
    today = datetime.today().date()
    years = [2026,2025,2024]

    if ftype == "Month":
        c1,c2 = st.columns(2)
        yr = c1.selectbox("Year", years, key="my")
        mo = c2.selectbox("Month", list(calendar.month_abbr)[1:], index=2, key="mm")
        mn = list(calendar.month_abbr).index(mo)
        start_date = datetime(yr,mn,1).date()
        end_date   = datetime(yr,mn,calendar.monthrange(yr,mn)[1]).date()
    elif ftype == "Week":
        c1,c2 = st.columns(2)
        yr = c1.selectbox("Year", years, key="wy")
        wks = get_weeks(yr)
        wlbls = [f"W{w[0]} ({w[1].strftime('%b%d')}-{w[2].strftime('%d')})" for w in wks]
        wi = c2.selectbox("Week", range(len(wlbls)), format_func=lambda x: wlbls[x], key="wn")
        start_date, end_date = wks[wi][1], wks[wi][2]
    elif ftype == "Day":
        d = st.date_input("Day", value=today)
        start_date = end_date = d
    elif ftype == "Date Range":
        start_date = st.date_input("Start", value=datetime(2026,3,1).date())
        end_date   = st.date_input("End",   value=datetime(2026,3,31).date())
    else:
        q = st.selectbox("", ["Today","Yesterday","Last 7 days","Last 30 days",
                               "This month","Last month","Q1 2026","Q2 2026","Year to date"],
                         label_visibility="collapsed")
        if q=="Today": start_date=end_date=today
        elif q=="Yesterday": start_date=end_date=today-timedelta(1)
        elif q=="Last 7 days": start_date=today-timedelta(7); end_date=today
        elif q=="Last 30 days": start_date=today-timedelta(30); end_date=today
        elif q=="This month": start_date=today.replace(day=1); end_date=today
        elif q=="Last month":
            f=today.replace(day=1); le=f-timedelta(1)
            start_date=le.replace(day=1); end_date=le
        elif q=="Q1 2026": start_date=datetime(2026,1,1).date(); end_date=datetime(2026,3,31).date()
        elif q=="Q2 2026": start_date=datetime(2026,4,1).date(); end_date=datetime(2026,6,30).date()
        else: start_date=datetime(today.year,1,1).date(); end_date=today

    st.markdown(f"<div style='font-size:11px; color:{C5}; margin-top:6px;'>📅 {start_date.strftime('%b %d, %Y')} → {end_date.strftime('%b %d, %Y')}</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown(f"<div style='color:{C5}; font-size:12px; font-weight:600;'>🏪 SALES CHANNEL</div>", unsafe_allow_html=True)
    ch_filter = st.multiselect("", CHANNEL_ORDER,
        format_func=lambda x: CHANNEL_LABELS.get(x,x),
        label_visibility="collapsed")

    st.markdown("---")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear(); st.rerun()
    st.markdown(f"<div style='font-size:10px; color:{CSUB};'>Last updated: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# ── Load data ──────────────────────────────────────
with st.spinner("Loading data..."):
    orders_df, returns_df, ads_df, cancelled_df, prod_info_df = load_all()

NUM_COLS = ["gross_revenue","net_revenue","btw","commission","delivery_costs",
            "pick_pack_costs","extra_costs","purchase_costs","net_profit","quantity","corrected_revenue"]

orders_f    = to_num(fch(fdate(orders_df,    "order_date",  start_date, end_date), ch_filter), NUM_COLS)
returns_f   = to_num(fch(fdate(returns_df,   "return_date", start_date, end_date), ch_filter, "api_type"),
                    ["quantity","gross_revenue","net_revenue","commission","delivery_costs","pick_pack_costs","extra_costs","purchase_costs"])
ads_f       = to_num(fdate(ads_df, "ad_date", start_date, end_date),
                    ["impressions","clicks","spent","conversions","sales","roas","acos","ctr","cpc"])
cancelled_f = to_num(fch(fdate(cancelled_df, "order_date",  start_date, end_date), ch_filter), NUM_COLS)

period_days = (end_date - start_date).days + 1
prev_end    = start_date - timedelta(1)
prev_start  = prev_end - timedelta(period_days - 1)
prev_orders = to_num(fch(fdate(orders_df, "order_date", prev_start, prev_end), ch_filter), NUM_COLS)

# ── Calculate metrics ──────────────────────────────
total_orders    = orders_f["order_number"].nunique() if not orders_f.empty else 0
total_units     = int(orders_f["quantity"].sum()) if not orders_f.empty else 0
total_gross_rev = orders_f["gross_revenue"].sum() if not orders_f.empty else 0
total_btw       = orders_f["btw"].sum() if not orders_f.empty else 0
total_net_rev   = total_gross_rev - total_btw
total_returns   = returns_f["order_number"].nunique() if not returns_f.empty else 0
total_cancelled = cancelled_f["order_number"].nunique() if not cancelled_f.empty else 0
ret_net_rev     = returns_f["net_revenue"].sum() if not returns_f.empty else 0
can_net_rev     = cancelled_f["net_revenue"].sum() if not cancelled_f.empty else 0
adjusted_rev    = total_net_rev - ret_net_rev - can_net_rev
total_ads       = ads_f["spent"].sum() if not ads_f.empty else 0
def safe_sum(df, col): return df[col].sum() if not df.empty and col in df.columns else 0
net_commission  = safe_sum(orders_f,"commission") - safe_sum(returns_f,"commission") - safe_sum(cancelled_f,"commission")
net_delivery    = safe_sum(orders_f,"delivery_costs") - safe_sum(returns_f,"delivery_costs") - safe_sum(cancelled_f,"delivery_costs")
net_pick_pack   = safe_sum(orders_f,"pick_pack_costs") - safe_sum(returns_f,"pick_pack_costs") - safe_sum(cancelled_f,"pick_pack_costs")
net_extra       = safe_sum(orders_f,"extra_costs") - safe_sum(returns_f,"extra_costs") - safe_sum(cancelled_f,"extra_costs")
net_purchase    = safe_sum(orders_f,"purchase_costs") - safe_sum(returns_f,"purchase_costs") - safe_sum(cancelled_f,"purchase_costs")
ret_ship_cost   = returns_f["delivery_costs"].sum() if not returns_f.empty else 0
profit          = adjusted_rev - total_ads - net_commission - net_purchase - net_delivery - net_pick_pack - ret_ship_cost - net_extra
profit_margin   = (profit / adjusted_rev * 100) if adjusted_rev > 0 else 0
aov             = total_gross_rev / total_orders if total_orders > 0 else 0
roi             = (profit / net_purchase * 100) if net_purchase > 0 else 0

prev_gross      = prev_orders["gross_revenue"].sum() if not prev_orders.empty else 0
prev_orders_cnt = prev_orders["order_number"].nunique() if not prev_orders.empty else 0
prev_units      = int(prev_orders["quantity"].sum()) if not prev_orders.empty else 0
prev_net        = prev_gross - prev_orders["btw"].sum() if not prev_orders.empty else 0
prev_aov        = prev_gross / prev_orders_cnt if prev_orders_cnt > 0 else 0

# ══════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════
st.markdown('<div class="page-header">📊 Sales Overview</div>', unsafe_allow_html=True)
st.markdown(f'<div class="page-subtitle">{start_date.strftime("%B %d, %Y")} — {end_date.strftime("%B %d, %Y")}</div>', unsafe_allow_html=True)

# Row 1
c1,c2,c3,c4 = st.columns(4)
dv,dt = delta_pct(total_gross_rev, prev_gross)
with c1: mcard("Gross Revenue", fmt_cur(total_gross_rev), dv, dt)
dv,dt = delta_pct(total_orders, prev_orders_cnt)
with c2: mcard("Total Orders", fmt_num(total_orders), dv, dt)
with c3: mcard("Cancelled", f"{fmt_num(total_cancelled)} / {fmt_cur(can_net_rev)}")
with c4: mcard("Profit", fmt_cur(profit))

st.markdown("")
# Row 2
c5,c6,c7,c8 = st.columns(4)
dv,dt = delta_pct(total_net_rev, prev_net)
with c5: mcard("Net Revenue", fmt_cur(total_net_rev), dv, dt)
dv,dt = delta_pct(total_units, prev_units)
with c6: mcard("Total Units", fmt_num(total_units), dv, dt)
with c7: mcard("Returns", f"{fmt_num(total_returns)} / {fmt_cur(ret_net_rev)}")
with c8: mcard("Profit Margin", f"{profit_margin:.1f}%")

st.markdown("")
# Row 3
c9,c10,c11,c12 = st.columns(4)
with c9:  mcard("Adjusted Revenue", fmt_cur(adjusted_rev))
dv,dt = delta_pct(aov, prev_aov)
with c10: mcard("AOV", fmt_cur(aov), dv, dt)
with c11: mcard("Ads Spent", fmt_cur(total_ads))
with c12: mcard("ROI", f"{roi:.0f}%")

# Daily Trend
st.markdown("<br>", unsafe_allow_html=True)
tcol1, tcol2 = st.columns([2,3])
with tcol1: st.markdown('<div class="section-title">Daily Trend</div>', unsafe_allow_html=True)
with tcol2:
    tm = st.radio("", ["Gross Revenue","Net Profit","Quantity","Net Revenue","Adjusted Revenue"],
                 horizontal=True, label_visibility="collapsed")

if not orders_f.empty:
    orders_f["order_date"] = pd.to_datetime(orders_f["order_date"], errors="coerce")
    tmap = {
        "Gross Revenue":    ("gross_revenue", "€", C1),
        "Net Profit":       ("net_profit",    "€", C5),
        "Quantity":         ("quantity",      "",  C3),
        "Net Revenue":      ("net_revenue",   "€", "#1a8a7a"),
        "Adjusted Revenue": ("net_revenue",   "€", "#2aaa9a"),
    }
    tcol, tpfx, tclr = tmap[tm]
    daily = orders_f.groupby(orders_f["order_date"].dt.date)[tcol].sum().reset_index()
    daily.columns = ["date","value"]
    fig = px.line(daily, x="date", y="value", color_discrete_sequence=[tclr])
    fig.update_traces(line_width=2, fill="tozeroy", fillcolor="rgba(3,102,97,0.15)")
    fig.update_layout(**{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis","legend"]}, height=420,
                     yaxis=dict(tickprefix=tpfx, gridcolor="rgba(107,162,159,0.15)", color=CSUB),
                     xaxis=dict(gridcolor="rgba(107,162,159,0.15)", color=CSUB, tickformat="%b %d",
                               range=[str(start_date), str(end_date)], nticks=20))
    st.plotly_chart(fig, use_container_width=True)

# Channel Performance + Country Map
col1, col2 = st.columns([1.2, 0.8])
with col1:
    st.markdown('<div class="section-title">Channel Performance</div>', unsafe_allow_html=True)
    if not orders_f.empty and "api_type" in orders_f.columns:
        ch_ord = orders_f.groupby("api_type").agg(
            Revenue=("gross_revenue","sum"), Orders=("order_number","nunique"),
            Units=("quantity","sum"), Profit=("net_profit","sum")
        ).reset_index()
        ch_ret = returns_f.groupby("api_type").agg(Returns=("order_number","nunique")).reset_index() if not returns_f.empty and "api_type" in returns_f.columns else pd.DataFrame(columns=["api_type","Returns"])
        ch_can = cancelled_f.groupby("api_type").agg(Cancelled=("order_number","nunique")).reset_index() if not cancelled_f.empty else pd.DataFrame(columns=["api_type","Cancelled"])
        ch = ch_ord.merge(ch_ret, on="api_type", how="left").merge(ch_can, on="api_type", how="left").fillna(0)
        ch["AOV"]    = (ch["Revenue"] / ch["Orders"]).round(2)
        ch["Margin"] = (ch["Profit"] / ch["Revenue"] * 100).round(1).astype(str) + "%"
        ch["Channel"] = ch["api_type"].map(CHANNEL_LABELS).fillna(ch["api_type"])
        ch["Revenue"] = ch["Revenue"].apply(lambda x: f"€{x:,.0f}")
        ch["AOV"]     = ch["AOV"].apply(lambda x: f"€{x:,.2f}")
        ch["Profit"]  = ch["Profit"].apply(lambda x: f"€{x:,.0f}")
        ch["Orders"]  = ch["Orders"].astype(int)
        ch["Units"]   = ch["Units"].astype(int)
        ch["Returns"] = ch["Returns"].astype(int)
        ch["Cancelled"] = ch["Cancelled"].astype(int)
        ch["sort_key"] = ch["api_type"].apply(lambda x: CHANNEL_ORDER.index(x) if x in CHANNEL_ORDER else 99)
        ch = ch.sort_values("sort_key").drop(columns=["api_type","sort_key"])
        ch = ch[["Channel","Revenue","Orders","Units","AOV","Profit","Margin","Returns","Cancelled"]]
        st.dataframe(ch, use_container_width=True, hide_index=True, height=260)

with col2:
    st.markdown('<div class="section-title">Sales by Country</div>', unsafe_allow_html=True)
    if not orders_f.empty and "country_code" in orders_f.columns:
        iso2_to_iso3 = {
            "NL":"NLD","BE":"BEL","DE":"DEU","FR":"FRA","GB":"GBR",
            "ES":"ESP","IT":"ITA","PL":"POL","PT":"PRT","AT":"AUT",
            "SE":"SWE","DK":"DNK","NO":"NOR","FI":"FIN","CH":"CHE",
            "US":"USA","CA":"CAN","AU":"AUS","NZ":"NZL","JP":"JPN",
            "CN":"CHN","IN":"IND","BR":"BRA","MX":"MEX","ZA":"ZAF",
            "AE":"ARE","SA":"SAU","SG":"SGP","HK":"HKG","MY":"MYS",
            "IE":"IRL","LU":"LUX","CZ":"CZE","HU":"HUN","RO":"ROU",
        }
        ctry = orders_f.groupby("country_code").agg(
            Revenue=("gross_revenue","sum"), Orders=("order_number","nunique")
        ).reset_index()
        ctry = ctry[ctry["country_code"].str.len() == 2]
        ctry["iso3"] = ctry["country_code"].map(iso2_to_iso3).fillna(ctry["country_code"])
        ctry["Revenue_fmt"] = ctry["Revenue"].apply(lambda x: f"€{x:,.2f}")
        fig = px.choropleth(ctry, locations="iso3", locationmode="ISO-3",
                           color="Revenue", hover_name="country_code",
                           hover_data={"Revenue_fmt":True, "Orders":True, "Revenue":False, "iso3":False},
                           color_continuous_scale=[[0, C4],[0.3, C3],[0.6, C1],[1, C5]])
        fig.update_layout(**{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis","legend"]}, height=260,
                         coloraxis_colorbar=dict(tickfont=dict(color=CSUB), title=dict(text="Revenue", font=dict(color=CSUB))),
                         geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)",
                                 landcolor="rgba(17,73,69,0.3)", showframe=False,
                                 coastlinecolor=CBORDER, projection_type="natural earth"))
        st.plotly_chart(fig, use_container_width=True)

# Week over week + Profit breakdown
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="section-title">Week over Week Revenue & Profit</div>', unsafe_allow_html=True)
    if not orders_f.empty:
        orders_f["week"] = orders_f["order_date"].dt.isocalendar().week
        wow = orders_f.groupby("week").agg(revenue=("gross_revenue","sum"), profit=("net_profit","sum")).reset_index()
        wow["week"] = "Week " + wow["week"].astype(str)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Revenue", x=wow["week"], y=wow["revenue"], marker_color=C1, opacity=0.85))
        fig.add_trace(go.Scatter(name="Profit", x=wow["week"], y=wow["profit"],
                                mode="lines+markers", line=dict(color=C5, width=2), marker=dict(size=6)))
        fig.update_layout(**{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis","legend"]}, height=300,
                         yaxis=dict(tickprefix="€", gridcolor="rgba(107,162,159,0.15)", color=CSUB),
                         legend=dict(orientation="h", y=1.1, font=dict(color=CTEXT, size=11)))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown('<div class="section-title">Profit Breakdown</div>', unsafe_allow_html=True)
    breakdown = pd.DataFrame({
        "Category": ["Adj Rev","Ads","Commission","Purchase","Shipping","Pick&Pack","Extra","Profit"],
        "Amount":   [adjusted_rev,-total_ads,-net_commission,-net_purchase,-net_delivery,-net_pick_pack,-net_extra,profit],
        "Color":    [C1,"#f87171","#f87171","#f87171","#f87171","#f87171","#f87171",C5]
    })
    fig = go.Figure(go.Bar(x=breakdown["Category"], y=breakdown["Amount"],
                           marker_color=breakdown["Color"], marker_line_width=0))
    fig.update_layout(**{k:v for k,v in CHART_LAYOUT.items() if k not in ["xaxis","yaxis","legend"]}, height=300,
                     yaxis=dict(tickprefix="€", gridcolor="rgba(107,162,159,0.15)", color=CSUB),
                     xaxis=dict(color=CSUB, tickangle=30))
    st.plotly_chart(fig, use_container_width=True)

# Top products
st.markdown('<div class="section-title">Top Products</div>', unsafe_allow_html=True)
top_col1, top_col2 = st.columns([1, 1.5])
with top_col1:
    st.markdown(f"<div style='font-size:12px; font-weight:600; color:{C5}; margin-bottom:6px;'>Top 10 by Revenue</div>", unsafe_allow_html=True)
    if not orders_f.empty:
        top = orders_f.groupby("ean").agg(
            Revenue=("gross_revenue","sum"), Units=("quantity","sum"), Orders=("order_number","nunique")
        ).nlargest(10,"Revenue").reset_index()
        if not prod_info_df.empty:
            prod_info_df.columns = [c.strip() for c in prod_info_df.columns]
            prod_info_df = prod_info_df.rename(columns={"EAN":"ean","Product Name":"product_short","Brand":"Brand"})
            prod_info_df["ean"] = prod_info_df["ean"].astype(str)
            top["ean"] = top["ean"].astype(str)
            top = top.merge(prod_info_df[["ean","product_short","Brand"]], on="ean", how="left")
            top["Product Name"] = top["product_short"].fillna(top["ean"])
        else:
            top["Product Name"] = top["ean"]
        top["Revenue"] = top["Revenue"].apply(lambda x: f"€{x:,.2f}")
        top["Units"]   = top["Units"].astype(int)
        top["Orders"]  = top["Orders"].astype(int)
        cols = ["Brand","Product Name","Revenue","Units","Orders"]
        if "Brand" not in top.columns: cols = [c for c in cols if c != "Brand"]
        st.dataframe(top[[c for c in cols if c in top.columns]], use_container_width=True, hide_index=True, height=500)

with top_col2:
    st.markdown(f"<div style='font-size:12px; font-weight:600; color:{C5}; margin-bottom:6px;'>Top 5 per Brand</div>", unsafe_allow_html=True)
    if not prod_info_df.empty and not orders_f.empty:
        prod_info_norm = prod_info_df.copy()
        orders_brand = orders_f.copy()
        orders_brand["ean"] = orders_brand["ean"].astype(str)
        orders_brand = orders_brand.merge(prod_info_norm[["ean","product_short","Brand"]], on="ean", how="left")
        orders_brand = orders_brand[orders_brand["Brand"].notna()]
        brands = sorted(orders_brand["Brand"].dropna().unique())
        brand_tabs = st.tabs(brands)
        for i, brand in enumerate(brands):
            brand_df = orders_brand[orders_brand["Brand"] == brand]
            top_brand = brand_df.groupby("product_short").agg(
                Revenue=("gross_revenue","sum"), Units=("quantity","sum")
            ).nlargest(5,"Revenue").reset_index()
            top_brand["Revenue"] = top_brand["Revenue"].apply(lambda x: f"€{x:,.2f}")
            top_brand["Units"]   = top_brand["Units"].astype(int)
            top_brand = top_brand.rename(columns={"product_short":"Product"})
            with brand_tabs[i]:
                st.dataframe(top_brand, use_container_width=True, hide_index=True, height=320)
