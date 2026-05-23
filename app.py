import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import yfinance as yf
import plotly.graph_objects as go
import db_manager as db
import data_fetcher as df_fetch
from streamlit_autorefresh import st_autorefresh

# Initialize database on startup
db.init_db()

# Page Config
st.set_page_config(
    page_title="US Stock Fundamental Analyzer & Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for premium look & feel
def inject_custom_css():
    st.markdown("""
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Premium Dark Theme backgrounds */
    .stApp {
        background-color: #0d0f12;
        color: #e2e8f0;
    }
    
    /* Modern Glassmorphic Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        margin-bottom: 16px;
    }
    
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #f8fafc;
    }
    
    .stock-card {
        background: rgba(255, 255, 255, 0.01);
        border: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(8px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 16px;
    }
    
    .stock-card:hover {
        transform: translateY(-4px);
        background: rgba(255, 255, 255, 0.03);
        border-color: rgba(255, 255, 255, 0.12);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .badge-buy {
        background-color: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }
    
    .badge-avoid {
        background-color: rgba(239, 68, 68, 0.12);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }
    
    .badge-hold {
        background-color: rgba(245, 158, 11, 0.12);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    
    .stock-title {
        font-size: 22px;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 2px;
    }
    
    .stock-subtitle {
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 16px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .stock-price {
        font-size: 24px;
        font-weight: 600;
        color: #ffffff;
    }
    
    .stock-metric-row {
        display: flex;
        justify-content: space-between;
        margin-top: 14px;
        font-size: 13px;
        color: #cbd5e1;
        border-top: 1px solid rgba(255, 255, 255, 0.04);
        padding-top: 12px;
    }
    
    /* Clean Title Gradient */
    .title-gradient {
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
    }

    /* Premium Button Custom Styles */
    .stButton > button {
        background: linear-gradient(135deg, #1e1b4b, #312e81) !important;
        color: #ffffff !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        font-weight: 700 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
        text-transform: none !important;
        letter-spacing: 0.03em !important;
        font-size: 14px !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
        color: #ffffff !important;
        border-color: #818cf8 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    
    /* Primary buttons (like the onboard/sync one) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
        border: 1px solid rgba(168, 85, 247, 0.4) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4f46e5, #9333ea) !important;
        box-shadow: 0 8px 25px rgba(168, 85, 247, 0.4) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Run CSS injection
inject_custom_css()

# Retrieve active settings from DB
gemini_key = db.get_setting("gemini_api_key", "AIzaSyBReadh1N0DcGyatkop47n7uokTHCJay-c")
sheet_url = db.get_setting("google_sheet_url", "https://docs.google.com/spreadsheets/d/1PSYb9wyqXkRZT8NJtna9749Fqb_Pb8mPxZITmKLXTuA/edit?usp=drive_link")
gemini_model = db.get_setting("gemini_model", "gemini-2.5-pro")

# Sidebar setup
st.sidebar.markdown("<h2 class='title-gradient' style='font-size: 1.6rem;'>📈 US Analyzer</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "เลือกหน้าการใช้งาน",
    ["📈 หน้ารวมหุ้นอเมริกา", "⚙️ ตั้งค่าระบบ (Settings)"],
    index=0
)

# Sidebar Autorefresh Selectbox
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 อัปเดตราคาอัตโนมัติ")
refresh_option = st.sidebar.selectbox(
    "ความถี่การรีเฟรชราคาด่วน",
    [
        "🛑 ปิดระบบอัปเดตอัตโนมัติ",
        "⚡ ดึงข้อมูลด่วนทุก 15 นาที",
        "⏰ ดึงข้อมูลด่วนทุก 1 ชั่วโมง"
    ],
    index=0,
    help="เลือกระยะเวลาการอัปเดตราคาล่าสุดแบบออฟไลน์ในช่วงเวลาตลาดเปิด"
)

# Parse interval time in ms
refresh_interval = 0
if refresh_option == "⚡ ดึงข้อมูลด่วนทุก 15 นาที":
    refresh_interval = 15 * 60 * 1000
elif refresh_option == "⏰ ดึงข้อมูลด่วนทุก 1 ชั่วโมง":
    refresh_interval = 60 * 60 * 1000

# Trigger background autorefresh if enabled
if refresh_interval > 0:
    st_autorefresh(interval=refresh_interval, key=f"autorefresh_timer_{refresh_interval}")
    
    last_fast_sync = st.session_state.get("last_fast_sync")
    now = datetime.datetime.now()
    interval_seconds = refresh_interval / 1000
    
    should_sync = False
    if last_fast_sync is None:
        should_sync = True
    else:
        elapsed = (now - last_fast_sync).total_seconds()
        if elapsed >= interval_seconds:
            should_sync = True
            
    if should_sync:
        try:
            succ, fail = df_fetch.update_prices_and_recommendations_batch()
            st.session_state.last_fast_sync = now
            if succ > 0:
                st.toast(f"⚡ อัปเดตราคาด่วนอัตโนมัติสำเร็จ {succ} ตัว", icon="✅")
        except Exception as e:
            st.toast(f"❌ อัปเดตราคากลุ่มอัตโนมัติล้มเหลว: {e}", icon="⚠️")

# Sidebar System Health Info
st.sidebar.markdown("---")
st.sidebar.subheader("สถานะระบบ (System Status)")
stocks_count = len(db.get_all_stocks())
st.sidebar.metric("หุ้นในระบบทั้งหมด", f"{stocks_count} ตัว")
st.sidebar.caption("การวิเคราะห์: `Offline Quantitative Model`")
st.sidebar.caption(f"Google Sheet ล่าสุด: [ลิงก์เปิดดู]({sheet_url})")

last_fast_sync = st.session_state.get("last_fast_sync")
if last_fast_sync:
    st.sidebar.caption(f"อัปเดตราคาล่าสุด: `{last_fast_sync.strftime('%H:%M:%S')}`")
else:
    st.sidebar.caption("อัปเดตราคาล่าสุด: `ยังไม่ได้รีเฟรช`")

# 1. PAGE: Settings
if menu == "⚙️ ตั้งค่าระบบ (Settings)":
    st.markdown("<h1>⚙️ ตั้งค่าระบบ (Settings)</h1>", unsafe_allow_html=True)
    st.write("ตั้งค่า Google Sheet รายชื่อหุ้น และ คีย์สำหรับการเชื่อมต่อ Gemini API เพื่อใช้วิเคราะห์หุ้น")
    
    with st.form("settings_form"):
        new_sheet = st.text_input(
            "ลิงก์ Google Sheet รายชื่อหุ้น",
            value=sheet_url,
            help="ระบุลิงก์ Google Sheet ที่มีสิทธิ์แชร์อ่านได้ เพื่อดึงข้อมูลรายชื่อหุ้นในคอลัมน์แรก"
        )
        new_key = st.text_input(
            "Gemini API Key (ไม่จำเป็นต้องระบุ - ระบบใช้คำนวณเชิงปริมาณออฟไลน์)",
            value=gemini_key,
            type="password",
            help="ฟังก์ชันนี้ไม่ได้ใช้งานหลักในการดึงหุ้นแล้ว สามารถเว้นว่างได้เลย"
        )
        
        # Available models list
        model_options = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        default_model_idx = model_options.index(gemini_model) if gemini_model in model_options else 0
        new_model = st.selectbox(
            "โมเดลของ Gemini ที่ใช้งาน",
            model_options,
            index=default_model_idx,
            help="แนะนำให้ใช้ gemini-2.5-flash เพื่อความรวดเร็ว หรือ gemini-2.5-pro เพื่อความลึกซึ้งในการวิเคราะห์เชิงปริมาณ"
        )
        
        submitted = st.form_submit_button("💾 บันทึกการตั้งค่า")
        if submitted:
            if not new_sheet.strip():
                st.error("กรุณาระบุลิงก์ Google Sheet")
            else:
                db.set_setting("google_sheet_url", new_sheet.strip())
                db.set_setting("gemini_api_key", new_key.strip())
                db.set_setting("gemini_model", new_model)
                st.success("บันทึกการตั้งค่าลงฐานข้อมูล SQLite สำเร็จ!")
                st.rerun()
                
    st.markdown("---")
    st.markdown("<h3>⚠️ พื้นที่จัดการฐานข้อมูล (Database Tools)</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**ล้างข้อมูลการวิเคราะห์**")
        st.write("ปุ่มนี้จะทำการลบข้อมูลการวิเคราะห์หุ้นออกทั้งหมดจาก SQLite (ประวัติและตารางความเห็น) เพื่อให้ระบบทำการวิเคราะห์หุ้นใหม่จากชีทในการรันครั้งหน้า ส่วนหน้าการตั้งค่าจะยังคงอยู่")
        if st.button("🚨 ล้างข้อมูลหุ้นทั้งหมด", use_container_width=True):
            db.clear_stocks()
            st.success("ล้างข้อมูลหุ้นใน SQLite เรียบร้อยแล้ว หน้าต่างรวมจะตรวจสอบพบว่าไม่มีข้อมูลและเริ่มให้กดนำเข้าข้อมูลใหม่")
            st.rerun()
            
    with col2:
        st.markdown("**ดูตารางข้อมูลดิบ (Raw Data)**")
        st.write("แสดงผลข้อมูลดิบทั้งหมดที่เก็บไว้ในตาราง `stocks` ของ SQLite เพื่อการตรวจสอบโครงสร้างฐานข้อมูล")
        if st.button("🔍 ตรวจสอบตาราง SQLite", use_container_width=True):
            raw_stocks = db.get_all_stocks()
            if raw_stocks:
                st.dataframe(pd.DataFrame(raw_stocks))
            else:
                st.info("ยังไม่มีข้อมูลหุ้นในระบบ")

# 2. PAGE: Dashboard (หน้ารวมหุ้น)
else:
    # State tracking
    if "selected_ticker" not in st.session_state:
        st.session_state.selected_ticker = None
        
    stocks = db.get_all_stocks()
    
    # 2.1 DETAIL VIEW RENDER
    if st.session_state.selected_ticker:
        ticker = st.session_state.selected_ticker
        stock = db.get_stock(ticker)
        
        if not stock:
            st.error(f"ไม่พบข้อมูลวิเคราะห์ของหุ้น {ticker}")
            st.session_state.selected_ticker = None
            st.rerun()
            
        # Header block
        st.markdown(f"<p style='margin-bottom: 0px; font-weight: 600; color: #6366f1; text-transform: uppercase;'>ข้อมูลวิเคราะห์ปัจจัยพื้นฐาน</p>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='margin-top: 0px;'>{stock['name']} ({stock['ticker']})</h1>", unsafe_allow_html=True)
        st.caption(f"การวิเคราะห์ล่าสุด: {stock['analysis_date']} | หมวดอุตสาหกรรม: {stock['sector']} / {stock['industry']}")
        
        # Navigation
        if st.button("⬅️ กลับไปหน้ารวม (Back to Dashboard)", use_container_width=True):
            st.session_state.selected_ticker = None
            st.rerun()
            
        # Top KPI bar for the stock
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        
        rec = stock["recommendation"]
        badge_style = "color: #10b981; background: rgba(16, 185, 129, 0.1);" if rec == "BUY" else "color: #ef4444; background: rgba(239, 68, 68, 0.1);" if rec == "AVOID" else "color: #f59e0b; background: rgba(245, 158, 11, 0.1);"
        
        price_val = stock["price"]
        price_formatted = f"${price_val:,.2f}" if price_val is not None else "N/A"
        
        with kpi_col1:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">คำแนะนำพื้นฐาน</div>
                <div class="metric-value" style="{badge_style} border-radius: 8px; font-size: 24px; padding: 4px;">{rec}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col2:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">น้ำหนักการลงทุน</div>
                <div class="metric-value" style="color: #6366f1;">{stock['weight'] or 'N/A'}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col3:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">ราคาปัจจุบัน</div>
                <div class="metric-value">{price_formatted}</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col4:
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">PEG Ratio</div>
                <div class="metric-value">{f"{stock['peg']:.2f}" if stock['peg'] is not None else "N/A"}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Section 1: Live Interactive Chart (TradingView) - Displayed directly as the first main component of the page
        st.write("")
        st.markdown("<h3 style='margin-bottom: 5px; color: #6366f1;'>📊 กราฟสดเรียลไทม์ (TradingView Live Chart)</h3>", unsafe_allow_html=True)
        
        try:
            import streamlit.components.v1 as components
            # Build TradingView HTML Widget with dark theme and robust loading mechanism
            tv_html = f"""
            <div class="tradingview-widget-container" style="height:500px;width:100%;">
              <div id="tradingview_chart_{ticker}"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              function initWidget() {{
                if (typeof TradingView !== 'undefined') {{
                  new TradingView.widget({{
                    "width": "100%",
                    "height": 500,
                    "symbol": "{ticker}",
                    "interval": "D",
                    "timezone": "Etc/UTC",
                    "theme": "dark",
                    "style": "1",
                    "locale": "th",
                    "toolbar_bg": "#111827",
                    "enable_publishing": false,
                    "hide_side_toolbar": false,
                    "allow_symbol_change": true,
                    "container_id": "tradingview_chart_{ticker}"
                  }});
                }} else {{
                  setTimeout(initWidget, 100);
                }}
              }}
              initWidget();
              </script>
            </div>
            """
            components.html(tv_html, height=515)
        except Exception as e:
            st.warning(f"ไม่สามารถโหลดกราฟ TradingView ได้: {e}")
            
        # Section 2: Detailed Analysis, Plotly Chart & Financial Statements
        st.markdown("---")
        
        tab_comprehensive, tab_analysis, tab_plotly, tab_statements = st.tabs([
            "📋 รายงานการวิเคราะห์พื้นฐานแบบครอบคุม",
            "📑 รายงานประเมินมูลค่าปัจจัยพื้นฐาน (Quantitative Report)", 
            "📈 กราฟประวัติราคา 1 ปี (Plotly Historical)",
            "📊 ตัวเลขงบการเงินดิบ (Raw yfinance Data)"
        ])
        
        with tab_comprehensive:
            if "comprehensive_report" in stock and stock["comprehensive_report"]:
                st.markdown(stock["comprehensive_report"])
            else:
                st.info("ยังไม่มีข้อมูล รายงานการวิเคราะห์พื้นฐานแบบครอบคุม กรุณากดปุ่มด้านล่างเพื่อเริ่มการประเมินวิเคราะห์เจาะลึกด้วย AI")
            
            st.markdown("---")
            st.markdown("### 🧠 วิเคราะห์ปัจจัยพื้นฐานและเทคนิคเชิงลึกด้วย AI")
            st.write("ระบบจะดึงงบการเงินล่าสุดและประเมินทางเทคนิค (MA50, MA200, RSI) ส่งให้โมเดล Gemini วิเคราะห์ตามกรอบการวิเคราะห์ 6 ขั้นตอนอย่างเป็นระบบ")
            
            # Check for dummy/default key
            if not gemini_key or gemini_key == "AIzaSyBReadh1N0DcGyatkop47n7uokTHCJay-c":
                st.warning("⚠️ ตรวจพบว่ายังไม่ได้ตั้งค่า Gemini API Key หรือเป็นคีย์ตั้งต้น กรุณาอัปเดตคีย์ในหน้า '⚙️ ตั้งค่าระบบ (Settings)' ก่อนเริ่มวิเคราะห์เชิงลึกด้วย AI")
            
            btn_ai = st.button("🤖 เริ่มการวิเคราะห์ด้วย AI (Gemini Ingestion)", key=f"btn_ai_{ticker}", use_container_width=True, type="primary")
            
            if btn_ai:
                with st.spinner("📥 กำลังดึงข้อมูลตัวเลขงบการเงินล่าสุดและราคาปิดเรียลไทม์จาก Yahoo Finance..."):
                    try:
                        import gemini_analyzer as ga
                        
                        # 1. Fetch latest profile
                        profile = df_fetch.get_stock_profile(ticker)
                        
                        # 2. Run local stats
                        raw_analysis, recommendation, weight, local_report = df_fetch.analyze_stock_locally(profile)
                        
                        # 3. Call Gemini
                        with st.spinner("🧠 โมเดล Gemini กำลังเริ่มจัดทำรายงานความเห็นเชิงคุณภาพ (ขั้นตอนที่ 1 ถึง 6)..."):
                            ai_report = ga.analyze_stock_comprehensively(
                                ticker=ticker,
                                name=profile["name"],
                                formatted_profile=profile["formatted_profile"],
                                api_key=gemini_key,
                                model_name=gemini_model
                            )
                        
                        # 4. Save back to SQLite
                        updated_stock = {
                            "ticker": ticker,
                            "name": profile["name"],
                            "sector": profile["sector"],
                            "industry": profile["industry"],
                            "price": profile["price"],
                            "pe": profile["pe"],
                            "pb": profile["pb"],
                            "peg": profile["peg"],
                            "roe": profile["roe"],
                            "recommendation": recommendation,
                            "weight": weight,
                            "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "raw_analysis": raw_analysis,
                            "comprehensive_report": ai_report
                        }
                        
                        db.save_stock(updated_stock)
                        st.success("🎉 วิเคราะห์เชิงลึกด้วย AI สำเร็จและบันทึกรายงานแล้ว!")
                        time.sleep(1.0)
                        st.rerun()
                        
                    except Exception as e_ai:
                        st.error(f"❌ เกิดข้อผิดพลาดระหว่างการเชื่อมต่อหรือประมวลผล Gemini: {e_ai}")
                
        with tab_analysis:
            st.markdown(stock["raw_analysis"])
            
        with tab_plotly:
            try:
                with st.spinner("กำลังดึงราคาย้อนหลังเพื่อแสดงกราฟ..."):
                    t = yf.Ticker(ticker)
                    hist = t.history(period="1y")
                    
                    if not hist.empty:
                        # Draw Plotly chart with price
                        fig = go.Figure()
                        
                        # Close Price line
                        fig.add_trace(go.Scatter(
                            x=hist.index, 
                            y=hist['Close'], 
                            name='ราคาปิด (Close Price)', 
                            line=dict(color='#6366f1', width=2.5)
                        ))
                        
                        fig.update_layout(
                            title=f"กราฟแนวโน้มราคาหุ้นย้อนหลัง 1 ปี ของ {ticker}",
                            template="plotly_dark",
                            plot_bgcolor='rgba(13,15,18,0.7)',
                            paper_bgcolor='rgba(13,15,18,0.7)',
                            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)'),
                            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.04)'),
                            margin=dict(l=40, r=40, t=50, b=40),
                            height=400,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("ไม่สามารถโหลดประวัติกราฟราคาได้จาก yfinance")
            except Exception as e:
                st.warning(f"เกิดข้อผิดพลาดในการโหลดกราฟ: {e}")
        
        with tab_statements:
            st.subheader("งบการเงินย้อนหลังที่แนบวิเคราะห์")
            try:
                with st.spinner("กำลังโหลดงบการเงินดิบ..."):
                    t_obj = yf.Ticker(ticker)
                    
                    # Display Income Statement, Balance Sheet, and Cash Flow in tabs
                    sub_income, sub_balance, sub_cash = st.tabs(["งบกำไรขาดทุน (Income Statement)", "งบแสดงฐานะการเงิน (Balance Sheet)", "งบกระแสเงินสด (Cash Flow)"])
                    
                    with sub_income:
                        st.dataframe(t_obj.financials, use_container_width=True)
                    with sub_balance:
                        st.dataframe(t_obj.balance_sheet, use_container_width=True)
                    with sub_cash:
                        st.dataframe(t_obj.cashflow, use_container_width=True)
                        
                    # Ratios table
                    st.markdown("### ตัวชี้วัดสำคัญทางการเงิน (Key Statistics)")
                    stats_data = []
                    for key in ["trailingPE", "forwardPE", "priceToBook", "trailingPegRatio", "returnOnEquity", "debtToEquity", "quickRatio", "beta", "dividendYield"]:
                        stats_data.append({"Indicator": key, "Value": t_obj.info.get(key, "N/A")})
                    st.table(pd.DataFrame(stats_data))
            except Exception as e:
                st.info(f"ไม่พบข้อมูลรายงานงบการเงินดิบเพิ่มเติมจาก yfinance: {e}")
                
        st.write("")
        if st.button("⬅️ กลับไปหน้ารวม (Back to Dashboard) ", use_container_width=True):
            st.session_state.selected_ticker = None
            st.rerun()

    # 2.2 NO STOCK IN DB - ONBOARDING VIEW
    elif len(stocks) == 0:
        st.markdown("<h1 class='title-gradient'>📈 US Stock Fundamental Dashboard</h1>", unsafe_allow_html=True)
        st.write("ยินดีต้อนรับสู่ระบบประเมินราคาเหมาะสมและวิเคราะห์หุ้นสหรัฐฯ! ระบบตรวจพบว่าปัจจุบันยังไม่มีข้อมูลหุ้นบันทึกอยู่ในฐานข้อมูล SQLite")
        
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #6366f1;">
            <h4 style="margin-top: 0px; color: #a855f7;">📋 แหล่งข้อมูลของระบบ</h4>
            <p>ระบบจะดึงรายชื่อสัญลักษณ์หุ้นจาก Google Sheet:</p>
            <p>👉 <a href="{sheet_url}" target="_blank" style="color: #cbd5e1; font-weight: bold; text-decoration: underline;">เปิดดู Google Sheet รายชื่อหุ้น</a></p>
            <p>จากนั้นสำหรับหุ้นแต่ละตัว ระบบจะดึงข้อมูลตัวเลขงบการเงินย้อนหลังจาก <b>Yahoo Finance (yfinance)</b> และประเมินราคาเหมาะสมด้วยเกณฑ์อัตราส่วนเชิงปริมาณ (Quantitative Rules: PEG Ratio, PE, ROE) โดยจะบันทึกผลลัพธ์ (BUY/HOLD/AVOID) และสัดส่วนลงฐานข้อมูล SQLite ทันทีอย่างรวดเร็ว</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h3>🚀 เริ่มวิเคราะห์หุ้นทั้งหมด</h3>", unsafe_allow_html=True)
        st.write("คลิกปุ่มด้านล่างเพื่อเริ่มดึงข้อมูลและคำนวณระดับราคาเชิงปริมาณของหุ้นทั้งหมดแบบออฟไลน์")
        
        # Trigger import
        if st.button("📥 เริ่มดึงข้อมูลจาก Google Sheet และประเมินราคาเหมาะสม", use_container_width=True, type="primary"):
            st.session_state.sync_running = True
            st.rerun()
            
        if st.session_state.get("sync_running", False):
            # Log placeholder
            status_container = st.status("🚀 กำลังเชื่อมโยงและนำเข้าข้อมูลวิเคราะห์...")
            with status_container:
                try:
                    # 1. Download sheet
                    status_container.write("1. กำลังเปิดและดาวน์โหลดรายชื่อหุ้นจาก Google Sheet...")
                    tickers = df_fetch.download_tickers_from_sheet(sheet_url)
                    
                    if not tickers:
                        st.error("ดาวน์โหลดรายชื่อหุ้นไม่สำเร็จ หรือ Google Sheet ว่างเปล่า กรุณาตั้งค่าลิงก์ใหม่ในหน้า Setting")
                        st.session_state.sync_running = False
                    else:
                        st.success(f"พบสัญลักษณ์หุ้นทั้งหมด {len(tickers)} ตัวในชีท: {', '.join(tickers)}")
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Loop analyze
                        total = len(tickers)
                        successful_count = 0
                        failed_count = 0
                        
                        for i, ticker in enumerate(tickers):
                            status_text.markdown(f"**ตัวที่ {i+1} จาก {total}**: กำลังประมวลผลหุ้น `{ticker}`...")
                            progress_bar.progress((i) / total)
                            
                            try:
                                # Fetch data
                                status_container.write(f"📥 `{ticker}`: ดึงตัวเลขงบการเงินย้อนหลังจาก yfinance...")
                                profile = df_fetch.get_stock_profile(ticker)
                                
                                if not profile:
                                    status_container.write(f"❌ `{ticker}`: ไม่สามารถนำเข้าข้อมูล yfinance ได้ ข้ามตัวนี้...")
                                    failed_count += 1
                                    continue
                                    
                                # Analyze with local quantitative engine
                                status_container.write(f"📊 `{ticker}`: ประเมินราคาเหมาะสมด้วยโมเดลวิเคราะห์ทางสถิติการเงิน...")
                                raw_analysis, recommendation, weight, comprehensive_report = df_fetch.analyze_stock_locally(profile)
                                
                                # Complete fields
                                profile["raw_analysis"] = raw_analysis
                                profile["recommendation"] = recommendation
                                profile["weight"] = weight
                                profile["analysis_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                profile["comprehensive_report"] = comprehensive_report
                                
                                # Save to DB
                                status_container.write(f"💾 `{ticker}`: บันทึกบทวิเคราะห์และสถานะลงฐานข้อมูล SQLite เรียบร้อย")
                                db.save_stock(profile)
                                db.delete_failed_stock(ticker)
                                successful_count += 1
                                status_container.write(f"✅ วิเคราะห์สำเร็จ! ผล: **{recommendation}** (น้ำหนักแนะ: **{weight}**)")
                                
                                # Sleep briefly to be respectful to API
                                time.sleep(0.5)
                                
                            except Exception as e:
                                status_container.write(f"❌ `{ticker}`: ข้ามเนื่องจากดึงข้อมูลไม่ได้หรือข้อมูลไม่ครบถ้วน: {e}")
                                db.save_failed_stock(ticker, str(e), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                                db.log_error_to_file(ticker, str(e))
                                failed_count += 1
                                # Sleep briefly even on failure
                                time.sleep(0.5)
                                
                        progress_bar.progress(1.0)
                        status_text.write("")
                        
                        st.session_state.sync_running = False
                        st.toast(f"วิเคราะห์เสร็จสิ้นสำเร็จ {successful_count} ตัว, ล้มเหลว {failed_count} ตัว")
                        status_container.update(label="🎉 วิเคราะห์ข้อมูลและบันทึกฐานข้อมูล SQLite ครบหมดเรียบร้อยแล้ว!", state="complete")
                        
                        st.button("🔄 โหลดหน้าเว็บเพื่อแสดงแดชบอร์ด", use_container_width=True)
                        st.rerun()
                except Exception as ex:
                    st.error(f"เกิดความผิดพลาดในการประมวลผล: {ex}")
                    st.session_state.sync_running = False

    # 2.3 DASHBOARD MAIN VIEW
    else:
        st.markdown("<h1 class='title-gradient'>📈 US Stock Fundamental Dashboard</h1>", unsafe_allow_html=True)
        st.write("หน้ารวมสรุปข้อมูลคำแนะนำการลงทุนพื้นฐานและคัดเลือกหุ้นสหรัฐฯ ตามกรอบวิเคราะห์ของศาสตราจารย์ Aswath Damodaran")
        
        # Display sync complete banner if exists
        if "sync_complete_msg" in st.session_state:
            st.success(st.session_state.sync_complete_msg)
            if st.button("ตกลง (Dismiss)", key="btn_dismiss_sync"):
                del st.session_state.sync_complete_msg
                st.rerun()
        
        # High level overview KPI blocks
        buy_count = sum(1 for s in stocks if s["recommendation"] == "BUY")
        avoid_count = sum(1 for s in stocks if s["recommendation"] == "AVOID")
        hold_count = sum(1 for s in stocks if s["recommendation"] == "HOLD")
        
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">หุ้นที่วิเคราะห์แล้วทั้งหมด</div>
                <div class="metric-value">{len(stocks)} <span style="font-size: 16px; color: #94a3b8; font-weight: normal;">Ticker</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">โอกาสแนะนำซื้อ (BUY Opportunities)</div>
                <div class="metric-value" style="color: #10b981;">{buy_count} <span style="font-size: 16px; color: #94a3b8; font-weight: normal;">ตัว ({buy_count/len(stocks)*100:.0f}%)</span></div>
            </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">หลีกเลี่ยง (AVOID Stocks)</div>
                <div class="metric-value" style="color: #ef4444;">{avoid_count} <span style="font-size: 16px; color: #94a3b8; font-weight: normal;">ตัว</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        # Search and filters row
        st.markdown("<h3>🔍 ค้นหาและกรองการลงทุน</h3>", unsafe_allow_html=True)
        
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        
        with f_col1:
            search_query = st.text_input("ค้นหาสัญลักษณ์ หรือ ชื่อหุ้น", value="").strip().upper()
            
        with f_col2:
            rec_options = ["ทั้งหมด (All)", "BUY", "HOLD", "AVOID"]
            filter_rec = st.selectbox("คำแนะนำพื้นฐาน", rec_options, index=0)
            
        with f_col3:
            unique_sectors = sorted(list(set(s["sector"] for s in stocks if s["sector"])))
            sector_options = ["ทั้งหมด (All)"] + unique_sectors
            filter_sector = st.selectbox("กลุ่มอุตสาหกรรม (Sector)", sector_options, index=0)
            
        with f_col4:
            sort_options = [
                "ชื่อสัญลักษณ์ (Ticker ASC)", 
                "ราคาปัจจุบันสูงสุด (Price DESC)", 
                "PEG ต่ำสุด (PEG ASC)", 
                "ROE สูงสุด (ROE DESC)"
            ]
            sort_by = st.selectbox("จัดเรียงลำดับผลลัพธ์", sort_options, index=0)
            
        # Apply filters
        filtered_stocks = stocks
        
        if search_query:
            filtered_stocks = [
                s for s in filtered_stocks 
                if search_query in s["ticker"] or search_query in s["name"].upper()
            ]
            
        if filter_rec != "ทั้งหมด (All)":
            filtered_stocks = [s for s in filtered_stocks if s["recommendation"] == filter_rec]
            
        if filter_sector != "ทั้งหมด (All)":
            filtered_stocks = [s for s in filtered_stocks if s["sector"] == filter_sector]
            
        # Apply sorting
        if sort_by == "ชื่อสัญลักษณ์ (Ticker ASC)":
            filtered_stocks = sorted(filtered_stocks, key=lambda x: x["ticker"])
        elif sort_by == "ราคาปัจจุบันสูงสุด (Price DESC)":
            filtered_stocks = sorted(filtered_stocks, key=lambda x: x["price"] or 0, reverse=True)
        elif sort_by == "PEG ต่ำสุด (PEG ASC)":
            # Handle Nones in sorting
            filtered_stocks = sorted(filtered_stocks, key=lambda x: x["peg"] if x["peg"] is not None else float('inf'))
        elif sort_by == "ROE สูงสุด (ROE DESC)":
            filtered_stocks = sorted(filtered_stocks, key=lambda x: x["roe"] if x["roe"] is not None else -float('inf'), reverse=True)
            
        st.markdown(f"💡 **พบหุ้นที่ตรงตามเงื่อนไขค้นหา:** `{len(filtered_stocks)}` จาก `{len(stocks)}` ตัว")
        
        # Action Bar to trigger Re-Sync/New Tickers
        col_act1, col_act2 = st.columns([2, 2])
        with col_act1:
            if st.button("⚡ อัปเดตราคาด่วนทันที (Fast Price Sync)", use_container_width=True):
                with st.spinner("🚀 กำลังอัปเดตราคากลุ่มล่าสุดและประเมินคำแนะนำใหม่..."):
                    try:
                        succ, fail = df_fetch.update_prices_and_recommendations_batch()
                        st.session_state.last_fast_sync = datetime.datetime.now()
                        st.success(f"⚡ อัปเดตราคาและคำแนะนำสำเร็จ {succ} ตัว ในเวลาน้อยกว่า 1 วินาที!")
                        time.sleep(1.0)
                        st.rerun()
                    except Exception as ex:
                        st.error(f"เกิดข้อผิดพลาดในการดึงราคาด่วน: {ex}")
                        
        with col_act2:
            if st.button("🚨 ซิงค์งบการเงินเต็มรูปแบบ (Full Daily Ingestion)", use_container_width=True):
                st.session_state.sync_running = True
                st.rerun()
                
        if st.session_state.get("sync_running", False):
            failed_only = st.session_state.get("sync_failed_only", False)
            if failed_only:
                st.info("🔄 กำลังดึงข้อมูลเฉพาะหุ้นที่เคยล้มเหลวหรือข้อมูลไม่ครบถ้วน...")
            else:
                st.info("🔄 กำลังตรวจสอบและนำเข้าเฉพาะหุ้นที่ยังไม่มีในฐานข้อมูล SQLite...")
            
            db_stocks_original = db.get_all_stocks()
            
            status_container = st.status("🔄 กำลังประมวลผลข้อมูลใหม่..." if failed_only else "🔄 กำลังประมวลผลข้อมูลหุ้นใหม่จาก Google Sheet...")
            with status_container:
                try:
                    if failed_only:
                        failed_records = db.get_all_failed_stocks()
                        tickers = [f["ticker"] for f in failed_records]
                    else:
                        tickers = df_fetch.download_tickers_from_sheet(sheet_url)
                        
                    if not tickers:
                        if failed_only:
                            st.info("ไม่มีรายการหุ้นที่เคยล้มเหลวให้ประมวลผล")
                        else:
                            st.error("ดาวน์โหลดรายชื่อหุ้นจาก Google Sheet ล้มเหลว")
                        st.session_state.sync_running = False
                        st.session_state.sync_failed_only = False
                    else:
                        if failed_only:
                            status_container.write(f"📊 พบหุ้นที่เคยล้มเหลวและต้องประมวลผลใหม่ {len(tickers)} ตัว")
                        else:
                            status_container.write(f"📊 พบรายชื่อหุ้นล่าสุดทั้งหมด {len(tickers)} ตัวใน Google Sheet")
                            
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        total = len(tickers)
                        
                        successful_count = 0
                        failed_count = 0
                        skipped_count = 0
                        
                        for i, ticker in enumerate(tickers):
                            if not failed_only:
                                existing = db.get_stock(ticker)
                                if existing:
                                    status_container.write(f"⏭️ `{ticker}`: มีข้อมูลการวิเคราะห์อยู่แล้ว (ข้ามการวิเคราะห์ซ้ำ)")
                                    skipped_count += 1
                                    progress_bar.progress((i+1)/total)
                                    continue
                                
                            status_text.markdown(f"**ตัวที่ {i+1} จาก {total}**: กำลังประมวลผลหุ้น `{ticker}`...")
                            progress_bar.progress(i / total)
                            
                            try:
                                status_container.write(f"📥 `{ticker}`: ดึงตัวเลขการเงินย้อนหลังจริง...")
                                profile = df_fetch.get_stock_profile(ticker)
                                
                                if not profile:
                                    status_container.write(f"❌ `{ticker}`: ไม่พบข้อมูลหรือดาวน์โหลด yfinance ล้มเหลว (ข้าม...)")
                                    failed_count += 1
                                    continue
                                    
                                status_container.write(f"📊 `{ticker}`: ประเมินราคาเหมาะสมด้วยโมเดลวิเคราะห์ทางสถิติการเงิน...")
                                raw_analysis, recommendation, weight, comprehensive_report = df_fetch.analyze_stock_locally(profile)
                                
                                profile["raw_analysis"] = raw_analysis
                                profile["recommendation"] = recommendation
                                profile["weight"] = weight
                                profile["analysis_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                profile["comprehensive_report"] = comprehensive_report
                                
                                db.save_stock(profile)
                                db.delete_failed_stock(ticker)
                                successful_count += 1
                                status_container.write(f"✅ บันทึก `{ticker}` สำเร็จ! คำแนะนำ: **{recommendation}** (สัดส่วนพอร์ต: **{weight}**)")
                                
                                # Sleep briefly
                                time.sleep(0.5)
                                
                            except Exception as ex:
                                status_container.write(f"❌ `{ticker}`: ข้ามเนื่องจากดึงข้อมูลไม่ได้หรือข้อมูลไม่ครบถ้วน: {ex}")
                                db.save_failed_stock(ticker, str(ex), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                                db.log_error_to_file(ticker, str(ex))
                                failed_count += 1
                                time.sleep(0.5)
                                
                        progress_bar.progress(1.0)
                        status_text.write("")
                        st.session_state.sync_running = False
                        st.session_state.sync_failed_only = False
                        
                        if failed_only:
                            st.session_state.sync_complete_msg = f"🎉 รีไทร์ดึงหุ้นเสร็จสิ้น! | ดึงหุ้นใหม่สำเร็จ: **{successful_count}** ตัว | ดึงข้อมูลล้มเหลวอีกรอบ: **{failed_count}** ตัว"
                        else:
                            st.session_state.sync_complete_msg = f"🎉 การดึงหุ้นใหม่เสร็จสิ้น! | เพิ่มหุ้นใหม่สำเร็จ: **{successful_count}** ตัว | มีอยู่แล้วในฐานข้อมูล (ข้าม): **{skipped_count}** ตัว | ดึงข้อมูลล้มเหลว: **{failed_count}** ตัว"
                        status_container.update(label="🎉 ดึงข้อมูลและวิเคราะห์เสร็จสิ้นเรียบร้อย!", state="complete")
                        st.rerun()
                except Exception as ex:
                    st.error(f"เกิดความผิดพลาดในการประมวลผลรายชื่อหุ้น: {ex}")
                    st.session_state.sync_running = False
                    
        st.markdown("---")
        
        # Grid of stock cards
        if not filtered_stocks:
            st.info("ไม่พบรายการหุ้นที่ตรงกับผลการกรอง ค้นหาใหม่อีกครั้ง")
        else:
            grid_cols = st.columns(3)
            for idx, s in enumerate(filtered_stocks):
                col = grid_cols[idx % 3]
                
                with col:
                    rec_val = s["recommendation"]
                    badge_style_class = "badge-buy" if rec_val == "BUY" else "badge-avoid" if rec_val == "AVOID" else "badge-hold"
                    weight_val = f"น้ำหนัก: {s['weight']}" if s['weight'] and s['weight'] != 'N/A' else ""
                    
                    price_val = s["price"]
                    price_formatted = f"${price_val:,.2f}" if price_val is not None else "N/A"
                    
                    card_html = f"""
                    <div class="stock-card">
                        <div class="stock-title">{s['ticker']}</div>
                        <div class="stock-subtitle" title="{s['name']}">{s['name']}</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div class="stock-price">{price_formatted}</div>
                            <div class="badge {badge_style_class}">{rec_val} {weight_val}</div>
                        </div>
                        <div class="stock-subtitle" style="margin-top: 8px; margin-bottom: 0; font-size: 12px; color: #64748b;">{s['sector']}</div>
                        <div class="stock-metric-row">
                            <span>P/E: <span style="font-weight: 600;">{f"{s['pe']:.1f}" if s['pe'] is not None else 'N/A'}</span></span>
                            <span>ROE: <span style="font-weight: 600;">{f"{s['roe']:.1f}%" if s['roe'] is not None else 'N/A'}</span></span>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    # Detail view button under the card
                    if st.button(f"🔍 ดูรายละเอียด & กราฟเชิงลึก {s['ticker']}", key=f"btn_grid_{s['ticker']}", use_container_width=True):
                        st.session_state.selected_ticker = s["ticker"]
                        st.rerun()
                        
        # 2.4 FAILED STOCK SYNC LOGS TABLE & RETRY ACTION
        failed_stocks = db.get_all_failed_stocks()
        if failed_stocks:
            st.markdown("---")
            st.markdown("<h3 style='color: #ef4444;'>⚠️ รายงานข้อมูลหุ้นที่ดึงไม่สำเร็จหรือข้อมูลไม่ครบถ้วน (Failed Ingestion Logs)</h3>", unsafe_allow_html=True)
            st.write("รายชื่อหุ้นด้านล่างนี้พบปัญหาขณะพยายามนำเข้าข้อมูล เช่น สัญลักษณ์ไม่ถูกต้อง ถูกถอนออกจากตลาด หรือไม่มีรายงานทางการเงินครบถ้วน")
            st.caption("📝 ระบบได้บันทึกรายงานความผิดพลาดแบบละเอียดลงไฟล์ `sync_errors.log` ในโฟลเดอร์ของโปรเจกต์นี้เรียบร้อยแล้ว")
            
            # Format logs to a beautiful dataframe
            logs_df = pd.DataFrame(failed_stocks)
            # Rename columns for localized display
            logs_df = logs_df.rename(columns={
                "ticker": "สัญลักษณ์หุ้น (Ticker)",
                "error_message": "สาเหตุและข้อผิดพลาด (Error Message)",
                "failed_at": "เวลาที่เกิดข้อผิดพลาด (Timestamp)"
            })
            
            # Display beautifully using Streamlit Dataframe
            st.dataframe(logs_df, use_container_width=True, hide_index=True)
            
            err_col1, err_col2 = st.columns([2, 1])
            with err_col1:
                if st.button("🔄 ลองดึงข้อมูลเฉพาะหุ้นที่ดึงไม่ได้อีกครั้ง (Retry Failed Stocks)", use_container_width=True, type="secondary", key="btn_retry_failed_stocks"):
                    st.session_state.sync_failed_only = True
                    st.session_state.sync_running = True
                    st.rerun()
            with err_col2:
                if st.button("🚨 ล้างบันทึกข้อผิดพลาดทั้งหมด (Clear Logs)", use_container_width=True, key="btn_clear_failed_logs"):
                    db.clear_failed_stocks()
                    st.success("ล้างบันทึกข้อผิดพลาดเรียบร้อยแล้ว")
                    st.rerun()
