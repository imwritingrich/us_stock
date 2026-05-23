import re
import pandas as pd
import yfinance as yf
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from typing import List, Dict, Any, Optional, Tuple

def get_custom_session() -> requests.Session:
    """Creates a requests session configured with custom headers and retries to prevent blocking."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    })
    
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def download_tickers_from_sheet(sheet_url: str) -> List[str]:
    """
    Downloads stock tickers from a Google Sheet.
    Accepts standard Google Sheets links, extracts the sheet ID, 
    and downloads the first column of the sheet as tickers.
    """
    try:
        # Check if it's a standard Google Sheets URL and extract ID
        # Example URL: https://docs.google.com/spreadsheets/d/1PSYb9wyqXkRZT8NJtna9749Fqb_Pb8mPxZITmKLXTuA/edit?usp=drive_link
        pattern = r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, sheet_url)
        
        if match:
            spreadsheet_id = match.group(1)
            export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
        else:
            # Fallback if the link is already an export link or direct CSV
            export_url = sheet_url
            
        # Read the sheet. Tickers are often stored in the first column with no headers.
        df = pd.read_csv(export_url, header=None)
        
        if df.empty:
            return []
            
        # Get the first column, drop nulls, convert to string, strip spaces, and capitalize
        tickers = df[0].dropna().astype(str).str.strip().str.upper().tolist()
        
        # Remove any duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            # Clean symbols (e.g. remove any non-alphanumeric chars except dots/dashes)
            cleaned = re.sub(r"[^A-Z.-]", "", ticker)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                unique_tickers.append(cleaned)
                
        return unique_tickers
    except Exception as e:
        raise Exception(f"Failed to read tickers from Google Sheet: {e}")

def format_df_to_markdown(df: pd.DataFrame) -> str:
    """Formats a pandas DataFrame to a clean markdown table, showing the last 4 periods."""
    try:
        if df is None or df.empty:
            return "No data available."
        # Limit to the last 4 periods (columns in yfinance are dates, descending or ascending)
        # Select first 4 columns
        cols = df.columns[:4]
        subset = df[cols]
        # Format numbers to be more human readable (thousands/millions/billions separators)
        formatted_subset = subset.copy()
        for col in formatted_subset.columns:
            # yfinance indexes can be floats, handle them
            formatted_subset[col] = formatted_subset[col].apply(
                lambda val: f"{val:,.2f}" if isinstance(val, (int, float)) and not pd.isna(val) else str(val)
            )
        return formatted_subset.to_markdown()
    except Exception as e:
        return f"Error formatting table: {e}"

def get_stock_profile(ticker: str) -> Dict[str, Any]:
    """
    Downloads stock data from yfinance and compiles a rich financial 
    and technical profile to pass to Gemini and save to the database.
    Raises descriptive exceptions if the stock has incomplete or invalid data.
    """
    ticker = ticker.upper().strip()
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        # 1. Check if yfinance returned basic info, otherwise check history
        if not info or ('symbol' not in info and not info.get('longName')):
            hist = ticker_obj.history(period="1mo")
            if hist.empty:
                raise ValueError("ไม่พบข้อมูลสัญลักษณ์หุ้นใน Yahoo Finance หรือสัญลักษณ์นี้สะกดไม่ถูกต้อง (Invalid symbol/No data)")
        
        # Fetch 1 year of daily historical price data
        hist_1y = ticker_obj.history(period="1y")
        
        price = None
        ma50 = None
        ma200 = None
        rsi = None
        
        if not hist_1y.empty:
            close_series = hist_1y['Close']
            price = float(close_series.iloc[-1])
            try:
                if len(close_series) >= 50:
                    ma50 = float(close_series.rolling(window=50).mean().iloc[-1])
                if len(close_series) >= 200:
                    ma200 = float(close_series.rolling(window=200).mean().iloc[-1])
                if len(close_series) >= 15:
                    delta = close_series.diff()
                    up = delta.clip(lower=0)
                    down = -1 * delta.clip(upper=0)
                    ema_up = up.ewm(com=13, adjust=False).mean()
                    ema_down = down.ewm(com=13, adjust=False).mean()
                    rs = ema_up / ema_down
                    rsi = float(100 - (100 / (1 + rs)).iloc[-1])
            except Exception as e_tech:
                print(f"Error calculating technical indicators: {e_tech}")
            
        # If price is still None, fallback to info
        if price is None:
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            
        # 2. Check if price is still missing or invalid (0 or negative)
        if price is None or price <= 0:
            raise ValueError("ไม่สามารถดึงราคาตลาดปัจจุบันได้ หุ้นตัวนี้อาจพ้นสภาพการซื้อขายแล้ว (No current price/Delisted)")
            
        # Key Ratios (with safe fallbacks)
        pe = info.get('trailingPE') or info.get('forwardPE')
        peg = info.get('trailingPegRatio') or info.get('pegRatio')
        pb = info.get('priceToBook')
        roe = info.get('returnOnEquity')
        
        # Convert ROE from decimal to percentage if needed
        if roe is not None:
            roe = float(roe) * 100.0 if abs(roe) < 1.0 else float(roe)
            
        # Basic descriptive details
        name = info.get('longName') or info.get('shortName') or ticker
        sector = info.get('sector') or 'N/A'
        industry = info.get('industry') or 'N/A'
        
        # 3. Check if company profile is completely empty (indicating dead ticker or placeholder info)
        if (not name or name == ticker) and sector == 'N/A' and industry == 'N/A':
            raise ValueError("ข้อมูลโปรไฟล์หลักของบริษัทไม่สมบูรณ์ (Incomplete company profile)")
            
        # Financial Statements as Markdown Tables
        financials_md = format_df_to_markdown(ticker_obj.financials)
        balance_sheet_md = format_df_to_markdown(ticker_obj.balance_sheet)
        cashflow_md = format_df_to_markdown(ticker_obj.cashflow)
        
        # 4. Check for empty financials (critical for Aswath Damodaran valuation analysis)
        if financials_md == "No data available." and balance_sheet_md == "No data available." and cashflow_md == "No data available.":
            raise ValueError("ไม่พบรายงานงบการเงินใดๆ ในฐานข้อมูลของ Yahoo Finance ซึ่งจำเป็นต่อการวิเคราะห์มูลค่าพื้นฐาน (Missing all financial statements)")
        
        return {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "price": price,
            "pe": pe,
            "peg": peg,
            "pb": pb,
            "roe": roe,
            "formatted_profile": f"""### FINANCIAL PROFILE: {name} ({ticker})
- **Sector**: {sector}
- **Industry**: {industry}
- **Current Price**: {f"${price:,.2f}" if price else 'N/A'}

#### Valuation & Performance Indicators:
- **P/E Ratio**: {f'{pe:.2f}' if pe else 'N/A'}
- **PEG Ratio**: {f'{peg:.2f}' if peg else 'N/A'}
- **P/B Ratio**: {f'{pb:.2f}' if pb else 'N/A'}
- **Return on Equity (ROE)**: {f'{roe:.2f}%' if roe else 'N/A'}
- **Beta**: {info.get('beta', 'N/A')}
- **Market Cap**: {f"${info.get('marketCap'):,}" if info.get('marketCap') else 'N/A'}
- **50-Day Moving Average (MA50)**: {f"${ma50:,.2f}" if ma50 else 'N/A'}
- **200-Day Moving Average (MA200)**: {f"${ma200:,.2f}" if ma200 else 'N/A'}
- **Relative Strength Index (RSI-14)**: {f"{rsi:.2f}" if rsi else 'N/A'}

#### 1. Annual Income Statement (Last 4 Periods):
{financials_md}

#### 2. Annual Balance Sheet (Last 4 Periods):
{balance_sheet_md}

#### 3. Annual Cash Flow Statement (Last 4 Periods):
{cashflow_md}
"""
        }
    except Exception as e:
        # If it is already one of our custom ValueErrors, pass it up
        if isinstance(e, ValueError):
            raise e
        # Otherwise raise a generic ingestion exception
        raise Exception(f"มีข้อผิดพลาดในการโหลดข้อมูลจาก Yahoo Finance: {str(e)}")

def analyze_stock_locally(profile: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """
    Analyzes stock profile locally using basic quantitative rules instead of Gemini.
    Returns (raw_analysis_markdown, recommendation, weight, comprehensive_report).
    """
    ticker = profile.get("ticker", "").upper()
    name = profile.get("name", "")
    sector = profile.get("sector", "")
    industry = profile.get("industry", "")
    price = profile.get("price")
    pe = profile.get("pe")
    peg = profile.get("peg")
    pb = profile.get("pb")
    roe = profile.get("roe")
    
    # Determine Recommendation & Weight
    recommendation = "HOLD"
    weight = "N/A"
    reasons = []
    
    if peg is not None:
        reasons.append(f"วิเคราะห์ตามเกณฑ์ PEG Ratio: {peg:.2f}")
        if 0 < peg < 1.0:
            recommendation = "BUY"
            weight = "10%"
            reasons.append("✅ PEG Ratio ต่ำกว่า 1.0 เท่า บ่งบอกถึงราคาหุ้นที่ยังถูกเมื่อเทียบกับอัตราการเติบโตของกำไร (Undervalued / Growth Discount)")
        elif peg >= 2.0 or peg < 0:
            recommendation = "AVOID"
            weight = "N/A"
            reasons.append("⚠️ PEG Ratio สูงเกิน 2.0 เท่า หรือเป็นค่าลบ บ่งบอกถึงราคาหุ้นที่แพงเกินจริงเมื่อเทียบกับอัตราการเติบโต หรือมีแนวโน้มกำไรชะลอตัว (Overvalued / Decline Risk)")
        else:
            recommendation = "HOLD"
            weight = "5%"
            reasons.append("📊 PEG Ratio อยู่ในช่วง 1.0 - 2.0 เท่า มูลค่าหุ้นอยู่ในเกณฑ์เหมาะสมและเติบโตสม่ำเสมอ (Fairly Valued)")
    else:
        reasons.append("ℹ️ ไม่พบข้อมูล PEG Ratio ในระบบ จึงใช้เกณฑ์ P/E และ ROE ในการประเมินราคาเหมาะสม")
        if pe is not None and roe is not None:
            reasons.append(f"สถิติพื้นฐาน: P/E Ratio = {pe:.2f} เท่า | ROE = {roe:.2f}%")
            if 0 < pe < 18 and roe > 15:
                recommendation = "BUY"
                weight = "10%"
                reasons.append("✅ หุ้นมีอัตราส่วนการทำกำไร (ROE) สูงกว่า 15% และซื้อขายที่ระดับ P/E ต่ำกว่า 18 เท่า ซึ่งสอดคล้องกับคุณลักษณะของหุ้นคุณภาพดีราคาคุ้มค่า (High Quality at Fair Price)")
            elif pe >= 35 or roe < 5:
                recommendation = "AVOID"
                weight = "N/A"
                if pe >= 35:
                    reasons.append("⚠️ P/E Ratio สูงเกิน 35 เท่า ถือว่ามีมูลค่าค่อนข้างแพงและมีความเสี่ยงสูงจากแรงขายทำกำไร")
                if roe < 5:
                    reasons.append("⚠️ อัตราผลตอบแทนต่อส่วนผู้ถือหุ้น (ROE) ต่ำกว่า 5% แสดงว่ามีความสามารถในการสร้างกระแสกำไรค่อนข้างต่ำ")
            else:
                recommendation = "HOLD"
                weight = "5%"
                reasons.append("📊 P/E Ratio และ ROE อยู่ในเกณฑ์ปานกลางตามค่าเฉลี่ยของกลุ่มอุตสาหกรรม")
        elif pe is not None:
            reasons.append(f"ประเมินด้วย P/E Ratio: {pe:.2f} เท่า")
            if 0 < pe < 15:
                recommendation = "BUY"
                weight = "8%"
                reasons.append("✅ P/E ต่ำกว่า 15 เท่า เหมาะสมสำหรับการเข้าสะสมเพื่อลงทุนระยะยาว")
            elif pe > 40:
                recommendation = "AVOID"
                weight = "N/A"
                reasons.append("⚠️ P/E สูงเกิน 40 เท่า ราคาสะท้อนความคาดหวังของตลาดมากเกินไป")
            else:
                recommendation = "HOLD"
                weight = "5%"
        elif roe is not None:
            reasons.append(f"ประเมินด้วยอัตราส่วนผลตอบแทนต่อส่วนของเงินลงทุน (ROE): {roe:.2f}%")
            if roe > 20:
                recommendation = "BUY"
                weight = "8%"
                reasons.append("✅ ROE สูงกว่า 20% แสดงว่าประสิทธิภาพในการหมุนเงินทุนเพื่อสร้างส่วนต่างกำไรสูงมาก")
            elif roe < 3:
                recommendation = "AVOID"
                weight = "N/A"
                reasons.append("⚠️ ROE ต่ำกว่า 3% การเติบโตไม่เสถียร มีความเสี่ยงในการลงทุน")
            else:
                recommendation = "HOLD"
                weight = "5%"
        else:
            recommendation = "HOLD"
            weight = "N/A"
            reasons.append("ℹ️ มีข้อมูลอัตราส่วนประเมินมูลค่าน้อยเกินกว่าจะให้คำแนะนำเชิงรุก แนะนำให้ถือ/รอข้อมูลเพิ่มเติม")

    # Build reasons list in markdown
    reasons_list = "\n".join([f"- {r}" for r in reasons])
    
    raw_analysis = f"""### 📊 รายงานประเมินมูลค่าปัจจัยพื้นฐานเชิงปริมาณ (Quantitative Valuation Report)
**สัญลักษณ์หุ้น**: {ticker} | **บริษัท**: {name}
**หมวดธุรกิจ/อุตสาหกรรม**: {sector} / {industry}

---

#### 🎯 สรุปคำแนะนำการลงทุน (Investment Decision)
- **คำแนะนำขั้นพื้นฐาน**: **{recommendation}**
- **สัดส่วนพอร์ตการลงทุนที่แนะนำ**: **{weight}**

#### 🔍 เกณฑ์ประกอบการพิจารณาและการคำนวณ (Valuation Rationale)
{reasons_list}

---

{profile.get("formatted_profile", "")}
"""

    # Form comprehensive report in Thai, following the strict format guidelines:
    # 1. Capitalize abbreviations: P/E, P/B, PEG, ROE, FCF, EBITDA, WACC, ROIC
    # 2. Use clean markdown tables for visual beauty.
    
    peg_status = "🟢 ผ่านเกณฑ์ดีเยี่ยม (< 1.0)" if (peg is not None and 0 < peg < 1.0) else \
                 "🟡 ระดับปานกลาง (1.0 - 2.0)" if (peg is not None and 1.0 <= peg < 2.0) else \
                 "🔴 ความเสี่ยงสูง / แพง (> 2.0 หรือติดลบ)" if peg is not None else "⚪ ไม่มีข้อมูล (N/A)"
                 
    roe_status = "🟢 ผ่านเกณฑ์สูงมาก (> 15%)" if (roe is not None and roe > 15) else \
                 "🟡 ระดับปานกลาง (5% - 15%)" if (roe is not None and 5 <= roe <= 15) else \
                 "🔴 ต่ำเกินไป (< 5%)" if roe is not None else "⚪ ไม่มีข้อมูล (N/A)"
                 
    pe_status = "🟢 ดึงดูดมาก (< 18 เท่า)" if (pe is not None and 0 < pe < 18) else \
                "🟡 สมเหตุสมผล (18 - 35 เท่า)" if (pe is not None and 18 <= pe < 35) else \
                "🔴 ราคาสูง / พรีเมียม (> 35 เท่า)" if pe is not None else "⚪ ไม่มีข้อมูล (N/A)"
                
    pb_status = "🟢 มูลค่าสมเหตุสมผล (< 3.0 เท่า)" if (pb is not None and pb < 3.0) else \
                "🟡 ราคาค่อนข้างพรีเมียม (>= 3.0 เท่า)" if pb is not None else "⚪ ไม่มีข้อมูล (N/A)"
                
    price_str = f"${price:,.2f}" if price else "N/A"
    pe_str = f"{pe:.2f} เท่า" if pe is not None else "N/A"
    peg_str = f"{peg:.2f} เท่า" if peg is not None else "N/A"
    pb_str = f"{pb:.2f} เท่า" if pb is not None else "N/A"
    roe_str = f"{roe:.2f}%" if roe is not None else "N/A"
    
    comprehensive_report = f"""## 📋 รายงานการวิเคราะห์พื้นฐานแบบครอบคลุม (Comprehensive Fundamental Analysis)
**บริษัท**: {name} | **สัญลักษณ์หุ้น**: {ticker}
**หมวดธุรกิจ**: {sector} | **กลุ่มอุตสาหกรรม**: {industry}

---

### 1. 📊 ตารางสรุปตัวชี้วัดทางการเงินและราคาปัจจุบัน
ตารางด้านล่างแสดงข้อมูลตัวเลขทางการเงินที่สำคัญ (Key Financial Ratios) ของหุ้น **{ticker}** เพื่อใช้ในการประเมินมูลค่าเบื้องต้น:

| อัตราส่วนทางการเงิน (Ratios) | ค่าที่วัดได้จริง | ระดับความเหมาะสมทางการเงิน (Assessment) | เกณฑ์มาตรฐานที่ปลอดภัย (Safe Benchmarks) |
| :--- | :---: | :---: | :---: |
| **Current Price** (ราคาปัจจุบัน) | {price_str} | อิงตามราคาตลาดปิดล่าสุด | N/A |
| **P/E Ratio** (ราคาต่อกำไรต่อหุ้น) | {pe_str} | {pe_status} | < 18.00 เท่า (อุตสาหกรรมทั่วไป) |
| **PEG Ratio** (การเติบโตกราฟกำไร) | {peg_str} | {peg_status} | < 1.00 เท่า (คุ้มค่าการเติบโต) |
| **P/B Ratio** (ราคาต่อมูลค่าทางบัญชี) | {pb_str} | {pb_status} | < 3.00 เท่า (มูลค่าสินทรัพย์ปลอดภัย) |
| **ROE** (อัตราผลตอบแทนต่อส่วนผู้ถือหุ้น) | {roe_str} | {roe_status} | > 15.00% (ความสามารถในการสร้างกำไรสูง) |

---

### 2. 🎯 สรุปคำแนะนำและการจัดพอร์ตลงทุน (Investment Matrix)
การประเมินราคาเหมาะสมเชิงปริมาณและคุณภาพตามหลักการลงทุนแนวเน้นคุณค่า (Value Investing):

| รายการประเมิน | ผลลัพธ์การคำนวณ | รายละเอียดและกลยุทธ์ |
| :--- | :---: | :--- |
| **คำแนะนำพื้นฐาน (Recommendation)** | **{recommendation}** | คำแนะนำเชิงคุณภาพจากการประเมินเกณฑ์อัตราส่วนมูลค่า |
| **สัดส่วนที่แนะนำ (Recommended Weight)** | **{weight}** | สัดส่วนการลงทุนสูงสุดที่แนะนำในพอร์ตการลงทุนรวม |

---

### 3. 🔍 คำอธิบายวิเคราะห์ปัจจัยพื้นฐานรายตัวชี้วัด (Detailed Fundamental Rationale)

* **สัญลักษณ์หุ้น {ticker} ({name})** ได้รับการวิเคราะห์บนเกณฑ์คำนวณเชิงปริมาณ (Quantitative Financial Modeling) โดยมีปัจจัยสนับสนุนดังนี้:
  
  * **PEG Ratio (Price/Earnings-to-Growth)**: {f"ค่า PEG ปัจจุบันอยู่ที่ {peg_str} ซึ่งอยู่ในระดับ {peg_status} อัตราส่วนนี้แสดงการเปรียบเทียบระหว่าง P/E กับอัตราการโตของ EPS (YoY EPS Growth) ช่วยวิเคราะห์หาหุ้นเติบโตที่ราคาไม่แพงเกินไป" if peg is not None else "ไม่พบข้อมูลอัตราส่วน PEG ส่งผลให้ต้องอ้างอิง P/E และ ROE เป็นด่านหลัก"}
  
  * **ROE (Return on Equity)**: {f"มีอัตราผลตอบแทนต่อส่วนของผู้ถือหุ้นที่ {roe_str} อยู่ในเกณฑ์ {roe_status} สะท้อนถึงการนำเงินลงทุนของผู้ถือหุ้นไปสร้างผลตอบแทนกำไรสุทธิได้อย่างมีประสิทธิภาพ" if roe is not None else "ไม่พบข้อมูลอัตราส่วน ROE ของบริษัท"}
  
  * **P/E & P/B Multiple**: {f"ระดับ P/E อยู่ที่ {pe_str} และ P/B อยู่ที่ {pb_str} ซึ่งบ่งชี้ว่าระดับราคานี้มีความ {pe_status.replace('🟢 ', '').replace('🟡 ', '').replace('🔴 ', '')} เมื่อเทียบกับกระแสเงินสดและสินทรัพย์สุทธิของบริษัท" if (pe is not None and pb is not None) else "ข้อมูล Multiple ไม่ครบถ้วน"}

---

### 4. 🛠️ ตารางตรวจสอบด่านประเมินความปลอดภัย (Quality Gates Assessment Checklist)
การตรวจสอบสุขภาพทางการเงินตามมาตรฐานเพื่อหาข้อบ่งชี้ความเสี่ยงเชิงคุณภาพ (Red Flags Check):

| ด่านการประเมิน (Quality Check Gate) | เกณฑ์เป้าหมาย |  สถานะของ {ticker} | ผลการตรวจสอบ |
| :--- | :---: | :---: | :---: |
| **ความสามารถในการทำกำไรสูง (ROE)** | > 15.00% | {roe_str} | {"✅ ผ่านเกณฑ์ดีเยี่ยม" if (roe is not None and roe > 15) else "⚠️ ต่ำกว่าเป้าหมาย"} |
| **ความคุ้มค่าของการเติบโต (PEG)** | < 1.00 เท่า | {peg_str} | {"✅ ผ่านเกณฑ์ดีเยี่ยม" if (peg is not None and 0 < peg < 1.0) else "⚠️ สูงเกินเกณฑ์เหมาะสม"} |
| **การระวังฟองสบู่ราคา (P/E Ratio)** | < 35.00 เท่า | {pe_str} | {"✅ อยู่ในเกณฑ์ปลอดภัย" if (pe is not None and pe < 35) else "⚠️ ราคาสูงพรีเมียม / ควรระวัง"} |

> [!NOTE]
> รายงานการวิเคราะห์นี้คำนวณและประมวลผลอัตโนมัติด้วยแบบจำลองตัวเลขเชิงปริมาณทางการเงิน (Offline Quantitative Model) ผ่านข้อมูลฐานงบการเงินล่าสุดจาก Yahoo Finance อัปเดตราคาแบบเรียลไทม์
"""

    return raw_analysis, recommendation, weight, comprehensive_report

def update_prices_and_recommendations_batch(db_path: str = "stocks.db") -> Tuple[int, int]:
    """
    Downloads current prices for all stocks in the database using a single batch request,
    mathematically scales their financial ratios (PE, PB, PEG) based on the price change,
    re-runs local quantitative rules to update recommendations/weights, and saves them to the DB.
    
    Returns a tuple: (successful_count, failed_count).
    """
    import db_manager as db
    import datetime
    
    # 1. Retrieve all stocks from the database
    stocks = db.get_all_stocks(db_path)
    if not stocks:
        return 0, 0
        
    tickers = [s["ticker"].upper() for s in stocks if s.get("ticker")]
    if not tickers:
        return 0, 0
        
    successful_count = 0
    failed_count = 0
    
    try:
        # 2. Download latest close prices in a single batch request
        df_prices = yf.download(tickers, period="1d", progress=False)
        
        if df_prices.empty:
            raise Exception("ไม่สามารถดาวน์โหลดข้อมูลราคากลุ่มจาก Yahoo Finance ได้ (Empty response)")
            
        # Get the latest close price for each ticker
        for s in stocks:
            ticker = s["ticker"].upper()
            
            try:
                close_price = None
                if len(tickers) == 1:
                    # Single ticker flat index handling
                    if 'Close' in df_prices.columns:
                        close_series = df_prices['Close'].dropna()
                        if not close_series.empty:
                            close_price = float(close_series.iloc[-1])
                else:
                    # Multi-ticker MultiIndex handling
                    if isinstance(df_prices.columns, pd.MultiIndex):
                        if 'Close' in df_prices.columns.levels[0] and ticker in df_prices.columns.levels[1]:
                            close_series = df_prices.xs('Close', axis=1, level=0)[ticker].dropna()
                            if not close_series.empty:
                                close_price = float(close_series.iloc[-1])
                    else:
                        # Flat index fallback for multi-ticker
                        if 'Close' in df_prices.columns:
                            close_series = df_prices['Close'].dropna()
                            if not close_series.empty:
                                close_price = float(close_series.iloc[-1])
                
                # Single-ticker fallback if batch extraction was unsuccessful
                if close_price is None or pd.isna(close_price) or close_price <= 0:
                    single_t = yf.Ticker(ticker)
                    hist = single_t.history(period="1d")
                    if not hist.empty:
                        close_price = float(hist['Close'].iloc[-1])
                    else:
                        raise ValueError(f"ไม่พบราคาสำหรับสัญลักษณ์ {ticker}")
                
                old_price = s.get("price")
                
                # If we don't have an old price or it was 0, use 1.0 as scaling factor
                price_scale = 1.0
                if old_price and old_price > 0:
                    price_scale = close_price / old_price
                
                # 3. Mathematically scale ratios
                pe = s.get("pe")
                pb = s.get("pb")
                peg = s.get("peg")
                roe = s.get("roe")
                
                new_pe = pe * price_scale if pe is not None else None
                new_pb = pb * price_scale if pb is not None else None
                new_peg = peg * price_scale if peg is not None else None
                
                # ROE remains unchanged as it's fundamentally equity-based, not price-based
                
                # Compile profile for rule analyzer
                temp_profile = {
                    "ticker": ticker,
                    "name": s.get("name"),
                    "sector": s.get("sector"),
                    "industry": s.get("industry"),
                    "price": close_price,
                    "pe": new_pe,
                    "pb": new_pb,
                    "peg": new_peg,
                    "roe": roe,
                    "formatted_profile": s.get("formatted_profile", "")
                }
                
                # 4. Re-run local quantitative rules
                raw_analysis, recommendation, weight, comprehensive_report = analyze_stock_locally(temp_profile)
                
                # Update stock record dict
                updated_stock = {
                    "ticker": ticker,
                    "name": s.get("name"),
                    "sector": s.get("sector"),
                    "industry": s.get("industry"),
                    "price": close_price,
                    "pe": new_pe,
                    "pb": new_pb,
                    "peg": new_peg,
                    "roe": roe,
                    "recommendation": recommendation,
                    "weight": weight,
                    "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "raw_analysis": raw_analysis,
                    "comprehensive_report": comprehensive_report
                }
                
                # Save to database
                db.save_stock(updated_stock, db_path)
                db.delete_failed_stock(ticker, db_path)
                successful_count += 1
                
            except Exception as e_inner:
                print(f"Error scaling price/ratios for {ticker}: {e_inner}")
                db.save_failed_stock(ticker, f"Error during price sync: {e_inner}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), db_path)
                db.log_error_to_file(ticker, f"Fast sync error: {e_inner}")
                failed_count += 1
                
    except Exception as e_outer:
        print(f"Error during batch price sync: {e_outer}")
        raise e_outer
        
    return successful_count, failed_count

# Quick local test block
if __name__ == "__main__":
    print("Testing download from Google Sheet...")
    sheet = "https://docs.google.com/spreadsheets/d/1PSYb9wyqXkRZT8NJtna9749Fqb_Pb8mPxZITmKLXTuA/edit?usp=drive_link"
    tickers = download_tickers_from_sheet(sheet)
    print("Tickers list (first 5):", tickers[:5])
    
    print("\nTesting profile fetch for NVDA...")
    profile = get_stock_profile("NVDA")
    if profile:
        print("Successfully fetched NVDA profile!")
        print("Name:", profile["name"])
        print("Price:", profile["price"])
        print("PE:", profile["pe"])
        print("\nFormatted Profile Snippet (First 500 chars):")
        print(profile["formatted_profile"][:500] + "...")
