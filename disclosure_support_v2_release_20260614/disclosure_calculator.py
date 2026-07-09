import re

def inject_dynamic_borderlines(text, financial_data):
    if not text:
        return text
        
    def replace_fraction(match):
        metric_name = match.group(1)
        denominator_str = match.group(2).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        numerator_str = match.group(3).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        
        denominator = float(denominator_str)
        numerator = float(numerator_str)
        
        val = None
        if "純資産" in metric_name:
            val = financial_data.get("net_assets")
        elif "売上高" in metric_name:
            val = financial_data.get("net_sales")
        elif "経常利益" in metric_name:
            val = financial_data.get("recurring_profit")
        elif "当期" in metric_name or "利益" in metric_name:
            val = financial_data.get("net_income")
        elif "資本金" in metric_name:
            val = financial_data.get("capital_stock")
        elif "資産" in metric_name:
            val = financial_data.get("net_assets")
            
        if val is not None and denominator > 0:
            borderline = val * (numerator / denominator)
            return f"{match.group(0)} **【判定ライン: {borderline:,.0f}百万円】**"
        else:
            return f"{match.group(0)} **【判定ライン: 計算不可】**"

    # 純資産額の100分の30 等のパーサー (「の 100分」「の総額の」等の表記揺れに対応)
    pattern_fraction = r'(純資産額|売上高|仕入高|経常利益金額|当期純利益金額|当期純利益|利益|資産の額|総資産の帳簿価額|純資産の額|資本金の額)(?:の総額)?\s*の\s*([０-９0-9]+)\s*分の\s*([０-９0-9\.]+)'
    text = re.sub(pattern_fraction, replace_fraction, text)

    def replace_fixed(match):
        amount_oku = match.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        oku_val = float(amount_oku)
        # 1億円 = 100百万円
        return f"{match.group(0)} **【判定ライン: {oku_val * 100:,.0f}百万円】**"

    # 1億円未満 等のパーサー
    pattern_fixed = r'([１-９1-9][０-９0-9\.]*)\s*億円'
    text = re.sub(pattern_fixed, replace_fixed, text)
    
    return text

def extract_summary_lines(text, financial_data):
    """
    サマリー表示用に、条文から該当する文脈全体を抽出し、動的計算を含んだ自然言語のリストを返します。
    """
    if not text:
        return []
        
    injected_text = inject_dynamic_borderlines(text, financial_data)
    
    # 段落や箇条書きで分割して、「判定ライン:」を含む文を抽出
    # ａ～ｚ、①～⑨、●、○ 等と句点「。」で適度に切る
    # シンプルに newline で分割し、一部を句点で補完する
    injected_text = injected_text.replace('\n', '')
    sentences = re.split(r'(?<=。)', injected_text)
    
    summary = []
    seen = set()
    for s in sentences:
        if '【判定ライン:' in s:
            # ａ、ｂ などの先頭マーカーを整える
            s_clean = s.strip()
            # 短すぎる場合は前後を結合する処理などが必要ですが、今回は「。」で切っているので文脈は保たれます。
            if s_clean not in seen:
                seen.add(s_clean)
                # 辞書のリストではなく、文字列のリストとして返すように app.py 側と調整
                summary.append({"metric": "文脈抽出", "condition": "", "borderline": s_clean})
                
    return summary
