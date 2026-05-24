import google.generativeai as genai
import re
import json
from typing import Dict, Any, Tuple

def analyze_stock(
    ticker: str, 
    name: str, 
    formatted_profile: str, 
    api_key: str, 
    model_name: str = "gemini-2.5-flash"
) -> Tuple[str, str, str]:
    """
    Analyzes a stock using the Gemini API based on a customized 6-step prompt 
    and returns (raw_analysis_markdown, recommendation, weight).
    """
    # 1. Configure the Gemini API
    genai.configure(api_key=api_key)
    
    # 2. Compile the full prompt
    prompt = f"""คุณคือ "ผู้เชี่ยวชาญด้านการลงทุนแนวพื้นฐานและสัญญะขับเคลื่อนมูลค่า (Damodaran Companion Variables & Top-Down Index Picking Framework)" 

จงวิเคราะห์หุ้น {name} ({ticker}) โดยใช้ข้อมูลที่แนบมา และตอบคำถามตามโครงสร้าง 6 ขั้นตอนอย่างเคร่งครัด ห้ามข้ามขั้นตอนเด็ดขาด:

### ขั้นตอนที่ 1: Global Macro & Theme Alignment (Top-Down Filter)
1. หุ้นนี้อยู่ในอุตสาหกรรมใด และสอดคล้องกับเศรษฐกิจช่วงใด (Early Recovery, Expansion, Late Cycle, Recession)? ทิศทางดอกเบี้ยปัจจุบันเป็นแรงหนุนหรือแรงต้าน?
2. หุ้นนี้เกาะไปกับ Mega Theme ระยะยาว (5-15 ปี) เรื่องใดชัดเจนที่สุด? (เช่น AI Infra, Aging Population, Energy Transition) มีหลักฐานความสำเร็จเชิงประจักษ์ (Business Reality) อะไรมารองรับ?

### ขั้นตอนที่ 2: Business Model & Moat Analysis (5 Quality Questions)
1. Core DNA: บริษัทขายอะไร ให้ใคร ทำไมลูกค้าต้องจ่ายเงิน และถ้าบริษัทหยุดดำเนินการ 1 ปี ลูกค้าจะเดือดร้อนแค่ไหน? 
2. Revenue Durability: รายได้เป็นแบบครั้งเดียว (Cyclical) หรือรายได้ต่อเนื่อง (Recurring)?
3. Moat Type & Proof: ป้อมปราการของธุรกิจคืออะไร? (Switching Cost, Network Effect, Cost Advantage, หรือ Intangible Assets) และพิสูจน์ด้วยตัวเลขหรือไม่ว่า ROIC > WACC ติดต่อกันอย่างน้อย 3-5 ปี?

### ขั้นตอนที่ 3: Financial Deep Dive & Quality Gates (Numbers Sanity Check)
จงคำนวณและประเมิน 5 ตัวเลขหลักเทียบกับค่าเฉลี่ยอุตสาหกรรม (Sector Benchmarks):
1. Revenue Growth YoY: เติบโตมากกว่า 10% หรือกำลังเร่งตัวขึ้น (Accelerating) หรือไม่?
2. Net Profit Margin & Operating Margin: ทางบัญชีเป็นอย่างไร และมีสภาพ Operating Leverage (รายได้โตเร็วกว่าค่าใช้จ่าย) หรือไม่?
3. FCF Conversion: Free Cash Flow เป็นบวกหรือไม่? และคิดเป็นกี่ % ของ Net Income (ผ่านเกณฑ์ Gate > 80% หรือไม่)?
4. Balance Sheet Stability: Net Debt / EBITDA เกิน 2.5x หรือไม่? เสี่ยงต่อภาวะดอกเบี้ยสูงแค่ไหน?
5. ROIC vs WACC: แสดงตัวเลขสรุปว่าบริษัทกำลัง "สร้างมูลค่า" หรือ "ทำลายมูลค่า"?

### ขั้นตอนที่ 4: Capital Allocation Hierarchy & Management Quality
1. ผู้บริหารนำเงินสดไปใช้อย่างไรตามลำดับความสำคัญ (Reinvest in Core, M&A, Buyback, Dividend)?
2. Buyback & M&A Quality Test: ประวัติการซื้อหุ้นคืนทำตอนราคาต่ำกว่ามูลค่าจริง หรือทำเพื่อกลบ Dilution? การทำ M&A ในอดีตส่งผลให้ ROIC ดีขึ้นหรือแย่ลงใน 3 ปีต่อมา? มี Goodwill เกิน 40% ของสินทรัพย์หรือไม่?
3. Skin in the Game & Credibility: ผู้บริหารและ Insider ถือหุ้นเกิน 10% หรือไม่? มีประวัติการทำตาม Guidance หรือ Beat/Miss อย่างไร?

### ขั้นตอนที่ 5: Valuation & Companion Variables Gut Check
ห้ามวิเคราะห์ Multiple ลอยๆ ให้ประเมินมูลค่าผ่านคู่ตัวแปรขับเคลื่อนดังนี้:
1. P/E คู่กับ EPS Growth: ค่า PEG Ratio อยู่ในระดับใด (< 1.0 = Undervalued, > 2.0 = Overvalued)?
2. EV/Sales คู่กับ After-Tax Operating Margin: ค่า EV/Sales สูงหรือต่ำเมื่อเทียบกับความสามารถในการทำกำไร? (ระวัง Red Flag: EV/Sales สูงแต่ Margin กำลังหดตัว)
3. P/B คู่กับ ROE (DuPont Analysis): ROE ที่สูงมาจาก Margin/Asset Turnover จริงๆ หรือเกิดจาก Financial Engineering (กู้หนี้มาปั่น Equity Multiplier)? Justified P/B ควรเป็นเท่าใด?
4. Reverse DCF Thinking: ราคาหุ้น ณ ปัจจุบัน ตลาดกำลัง Price In อัตราการเติบโต (Implied Growth Rate) ไว้กี่ %? และความคาดหวังนั้นเกินจริง (Priced for Perfection) หรือไม่?

### ขั้นตอนที่ 6: Synthesis & Action Plan (3 Final Questions)
1. ตัวเนื้อธุรกิจจะใหญ่ขึ้นและทำกำไรได้มากกว่านี้ในอีก 5-10 ปีข้างหน้าใช่หรือไม่?
2. หากหุ้นตัวนี้ตกลง 30% พรุ่งนี้โดยพื้นฐานไม่เปลี่ยน เราจะกล้าซื้อเพิ่ม (Conviction Pass) ใช่หรือไม่?
3. Variant View: ตลาดกำลังเข้าใจอะไรผิดเกี่ยวกับหุ้นตัวนี้ (ทำไมเราถึงคิดว่า Misprice)?
4. จงสรุปคำแนะนำ (BUY พร้องระบุน้ำหนักพอร์ตที่แนะนำ 2-15% ตามกรอบความตึงของ Valuation / หรือ AVOID หากเจอ Red Flag พร้อมระบุเหตุผล)

===========================================
ข้อมูลที่แนบมา (REAL-TIME FINANCIALS & VALUATION RATIOS):
{formatted_profile}
===========================================

*** คำสั่งพิเศษสำหรับการจัดส่งข้อมูลกลับ (CRITICAL FORMATTING REQUIREMENT) ***
ที่ท้ายสุดของการวิเคราะห์ของคุณ กรุณาพิมพ์แท็ก <METADATA>...</METADATA> ซึ่งข้างในแท็กจะเป็น JSON object ที่สรุปผลวิเคราะห์ โดยระบุ "recommendation" (ใส่ค่า "BUY", "AVOID" หรือ "HOLD" เท่านั้น) และ "weight" (ระบุเป็นเปอร์เซ็นต์ เช่น "5%", "10%", "2-15%", หรือ "N/A" ในกรณีที่เป็น AVOID/HOLD) ให้ตรงตามที่คุณสรุปในขั้นตอนที่ 6 

ตัวอย่างรูปแบบที่ต้องการ:
<METADATA>
{{
  "recommendation": "BUY",
  "weight": "8%"
}}
</METADATA>
หรือหากแนะนำให้หลีกเลี่ยง:
<METADATA>
{{
  "recommendation": "AVOID",
  "weight": "N/A"
}}
</METADATA>
ห้ามมีคำพูดอื่นใดนอกแท็ก <METADATA> ในบรรทัดเดียวกันเด็ดขาด และห้ามลืมใส่แท็กนี้ เพราะระบบจะใช้ดึงข้อมูลสรุปสำหรับการแสดงผลบนหน้า Dashboard
"""
    
    # 3. Request analysis from Gemini
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    raw_response = response.text
    
    # Default values
    recommendation = "HOLD"
    weight = "N/A"
    cleaned_analysis = raw_response
    
    # 4. Extract metadata using regex
    metadata_pattern = r"<METADATA>\s*(.*?)\s*</METADATA>"
    match = re.search(metadata_pattern, raw_response, re.DOTALL)
    
    if match:
        try:
            metadata_str = match.group(1).strip()
            # Parse json
            metadata = json.loads(metadata_str)
            recommendation = metadata.get("recommendation", "HOLD").upper().strip()
            weight = metadata.get("weight", "N/A").strip()
            
            # Keep recommendation clean (strictly BUY / AVOID / HOLD)
            if recommendation not in ["BUY", "AVOID", "HOLD"]:
                if "BUY" in recommendation:
                    recommendation = "BUY"
                elif "AVOID" in recommendation:
                    recommendation = "AVOID"
                else:
                    recommendation = "HOLD"
            
            # Clean up the METADATA block from the final displayed text
            cleaned_analysis = re.sub(metadata_pattern, "", raw_response, flags=re.DOTALL).strip()
        except Exception as e:
            print(f"Error parsing metadata JSON for {ticker}: {e}")
            
    # Robust fallbacks if metadata extraction failed or model didn't provide clean JSON
    if recommendation == "HOLD" and weight == "N/A":
        # Search the last part of response for keywords
        last_chars = raw_response[-2000:].upper()
        if "AVOID" in last_chars or "หลีกเลี่ยง" in last_chars:
            recommendation = "AVOID"
        elif "BUY" in last_chars or "ซื้อ" in last_chars:
            recommendation = "BUY"
            
        # Try to find a percentage like 2-15% or 5% in the last 1000 characters
        percentage_match = re.search(r"(\d+%\s*-\s*\d+%|\d+%)", raw_response[-1000:])
        if percentage_match:
            weight = percentage_match.group(1)
            
    return cleaned_analysis, recommendation, weight

# Quick local test block
if __name__ == "__main__":
    import os
    print("Testing stock analysis with mock profile...")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    mock_profile = """
    ### FINANCIAL PROFILE: NVIDIA Corporation (NVDA)
    - Sector: Technology
    - Industry: Semiconductors
    - Current Price: $219.51
    - P/E Ratio: 33.67
    - PEG Ratio: 0.70
    - P/B Ratio: 33.92
    - Return on Equity (ROE): 114%
    
    #### 1. Annual Income Statement (Last 2 Periods):
    | | 2026-01-31 | 2025-01-31 |
    |---|---|---|
    | Total Revenue | 96,310,000,000 | 60,922,000,000 |
    | Operating Income | 54,320,000,000 | 32,912,000,000 |
    | Net Income | 49,670,000,000 | 29,760,000,000 |
    
    #### 2. Annual Balance Sheet (Last 2 Periods):
    | | 2026-01-31 | 2025-01-31 |
    |---|---|---|
    | Total Assets | 85,210,000,000 | 65,720,000,000 |
    | Total Liabilities | 25,120,000,000 | 22,810,000,000 |
    | Net Debt | -12,450,000,000 | -8,320,000,000 |
    
    #### 3. Annual Cash Flow Statement (Last 2 Periods):
    | | 2026-01-31 | 2025-01-31 |
    |---|---|---|
    | Free Cash Flow | 45,210,000,000 | 27,110,000,000 |
    """
    
    try:
        raw_analysis, recommendation, weight = analyze_stock(
            ticker="NVDA",
            name="NVIDIA Corporation",
            formatted_profile=mock_profile,
            api_key=api_key
        )
        print("Analysis completed successfully!")
        print("Recommendation:", recommendation)
        print("Weight:", weight)
        print("\nAnalysis Snippet (First 300 chars):")
        print(raw_analysis[:300] + "...")
    except Exception as e:
        print("Error analyzing stock:", e)


def analyze_stock_comprehensively(
    ticker: str, 
    name: str, 
    formatted_profile: str, 
    api_key: str, 
    model_name: str = "gemini-2.5-flash"
) -> str:
    """
    Analyzes a stock using Gemini based on a customized 6-step prompt 
    with Step 5.5 Technical Context and returns the raw comprehensive markdown report.
    """
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    prompt = f"""คุณคือ "ผู้เชี่ยวชาญด้านการลงทุนแนวพื้นฐานและสัญญะขับเคลื่อนมูลค่า (Damodaran Companion Variables & Top-Down Index Picking Framework)" 

จงวิเคราะห์หุ้น {name} ({ticker}) โดยใช้ข้อมูลที่แนบมา และตอบคำถามตามโครงสร้าง 6 ขั้นตอนอย่างเคร่งครัด ห้ามข้ามขั้นตอนเด็ดขาด:

### ขั้นตอนที่ 1: Global Macro & Theme Alignment (Top-Down Filter)
1. หุ้นนี้อยู่ในอุตสาหกรรมใด และสอดคล้องกับเศรษฐกิจช่วงใด (Early Recovery, Expansion, Late Cycle, Recession)? ทิศทางดอกเบี้ยปัจจุบันเป็นแรงหนุนหรือแรงต้าน?
2. หุ้นนี้เกาะไปกับ Mega Theme ระยะยาว (5-15 ปี) เรื่องใดชัดเจนที่สุด? (เช่น AI Infra, Aging Population, Energy Transition) มีหลักฐานความสำเร็จเชิงประจักษ์ (Business Reality) อะไรมารองรับ?

### ขั้นตอนที่ 2: Business Model & Moat Analysis (5 Quality Questions)
1. Core DNA: บริษัทขายอะไร ให้ใคร ทำไมลูกค้าต้องจ่ายเงิน และถ้าบริษัทหยุดดำเนินการ 1 ปี ลูกค้าจะเดือดร้อนแค่ไหน? 
2. Revenue Durability: รายได้เป็นแบบครั้งเดียว (Cyclical) หรือรายได้ต่อเนื่อง (Recurring)?
3. Moat Type & Proof: ป้อมปราการของธุรกิจคืออะไร? (Switching Cost, Network Effect, Cost Advantage, หรือ Intangible Assets) และพิสูจน์ด้วยตัวเลขหรือไม่ว่า ROIC > WACC ติดต่อกันอย่างน้อย 3-5 ปี?

### ขั้นตอนที่ 3: Financial Deep Dive & Quality Gates (Numbers Sanity Check)
จงคำนวณและประเมิน 5 ตัวเลขหลักเทียบกับค่าเฉลี่ยอุตสาหกรรม (Sector Benchmarks):
1. Revenue Growth YoY: เติบโตมากกว่า 10% หรือกำลังเร่งตัวขึ้น (Accelerating) หรือไม่?
2. Net Profit Margin & Operating Margin: ทางบัญชีเป็นอย่างไร และมีสภาพ Operating Leverage (รายได้โตเร็วกว่าค่าใช้จ่าย) หรือไม่?
3. FCF Conversion: Free Cash Flow เป็นบวกหรือไม่? และคิดเป็นกี่ % ของ Net Income (ผ่านเกณฑ์ Gate > 80% หรือไม่)?
4. Balance Sheet Stability: Net Debt / EBITDA เกิน 2.5x หรือไม่? เสี่ยงต่อภาวะดอกเบี้ยสูงแค่ไหน?
5. ROIC vs WACC: แสดงตัวเลขสรุปว่าบริษัทกำลัง "สร้างมูลค่า" หรือ "ทำลายมูลค่า"?

### ขั้นตอนที่ 4: Capital Allocation Hierarchy & Management Quality
1. ผู้บริหารนำเงินสดไปใช้อย่างไรตามลำดับความสำคัญ (Reinvest in Core, M&A, Buyback, Dividend)?
2. Buyback & M&A Quality Test: ประวัติการซื้อหุ้นคืนทำตอนราคาต่ำกว่ามูลค่าจริง หรือทำเพื่อกลบ Dilution? การทำ M&A ในอดีตส่งผลให้ ROIC ดีขึ้นหรือแย่ลงใน 3 ปีต่อมา? มี Goodwill เกิน 40% ของสินทรัพย์หรือไม่?
3. Skin in the Game & Credibility: ผู้บริหารและ Insider ถือหุ้นเกิน 10% หรือไม่? มีประวัติการทำตาม Guidance หรือ Beat/Miss อย่างไร?

### ขั้นตอนที่ 5: Valuation & Companion Variables Gut Check
ห้ามวิเคราะห์ Multiple ลอยๆ ให้ประเมินมูลค่าผ่านคู่ตัวแปรขับเคลื่อนดังนี้:
1. P/E คู่กับ EPS Growth: ค่า PEG Ratio อยู่ในระดับใด (< 1.0 = Undervalued, > 2.0 = Overvalued)?
2. EV/Sales คู่กับ After-Tax Operating Margin: ค่า EV/Sales สูงหรือต่ำเมื่อเทียบกับความสามารถในการทำกำไร? (ระวัง Red Flag: EV/Sales สูงแต่ Margin กำลังหดตัว)
3. P/B คู่กับ ROE (DuPont Analysis): ROE ที่สูงมาจาก Margin/Asset Turnover จริงๆ หรือเกิดจาก Financial Engineering (กู้หนี้มาปั่น Equity Multiplier)? Justified P/B ควรเป็นเท่าใด?
4. Reverse DCF Thinking: ราคาหุ้น ณ ปัจจุบัน ตลาดกำลัง Price In อัตราการเติบโต (Implied Growth Rate) ไว้กี่ %? และความคาดหวังนั้นเกินจริง (Priced for Perfection) หรือไม่?

### ขั้นตอนที่ 5.5: Technical Context (Entry Timing)
1. ราคาปัจจุบันอยู่เหนือหรือใต้เส้น MA50 / MA200? Volume ในการขึ้นหรือลงสะท้อนความมั่นใจของตลาดอย่างไร? มี RSI Divergence สัญญาณเตือนความอ่อนแรงหรือไม่?

### ขั้นตอนที่ 6: Synthesis & Action Plan (3 Final Questions)
1. ตัวเนื้อธุรกิจจะใหญ่ขึ้นและทำกำไรได้มากกว่านี้ในอีก 5-10 ปีข้างหน้าใช่หรือไม่?
2. หากหุ้นตัวนี้ตกลง 30% พรุ่งนี้โดยพื้นฐานไม่เปลี่ยน เราจะกล้าซื้อเพิ่ม (Conviction Pass) ใช่หรือไม่?
3. Variant View: ตลาดกำลังเข้าใจอะไรผิดเกี่ยวกับหุ้นตัวนี้ (ทำไมเราถึงคิดว่า Misprice)?
4. จงสรุปคำแนะนำ (BUY พร้องระบุน้ำหนักพอร์ตที่แนะนำ 2-15% ตามกรอบความตึงของ Valuation / หรือ AVOID หากเจอ Red Flag พร้อมระบุเหตุผล)

===========================================
ข้อมูลที่แนบมา (REAL-TIME FINANCIALS & VALUATION RATIOS):
{formatted_profile}
===========================================

*** คำสั่งพิเศษสำหรับการจัดรูปแบบรายงาน (CRITICAL FORMATTING REQUIREMENT) ***
1. จงใช้สัญลักษณ์ทางการเงินเป็นภาษาอังกฤษตัวใหญ่ เช่น P/E, P/B, PEG, ROE, FCF, EBITDA, WACC, ROIC
2. จงออกแบบผลลัพธ์ในลักษณะของ Markdown ที่มีความพรีเมียม สวยงาม โดยจัดข้อมูลที่เป็นตัวเลขและการเปรียบเทียบในลักษณะ **ตาราง (Table)** เพื่อให้อ่านง่าย เช่น ตารางเปรียบเทียบ Ratios หรือเกณฑ์ด่านต่าง ๆ
3. เขียนเนื้อหาการวิเคราะห์เป็นภาษาไทยอย่างละเอียดและเข้าใจง่าย
"""
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text
