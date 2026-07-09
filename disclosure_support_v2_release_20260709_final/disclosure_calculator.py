import re

_ZEN_TO_HAN = str.maketrans('０１２３４５６７８９．', '0123456789.')


def _to_float(value):
    return float(value.translate(_ZEN_TO_HAN).replace(",", "").replace("，", ""))

def inject_dynamic_borderlines(text, financial_data):
    if not text:
        return text
        
    def replace_fraction(match):
        metric_name = match.group(1)
        denominator = _to_float(match.group(2))
        numerator = _to_float(match.group(3))
        
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

    def replace_fixed_amount(match):
        amount = _to_float(match.group(1))
        unit = match.group(2)
        multiplier = {
            "億円": 100,
            "百万円": 1,
            "万円": 0.01,
        }[unit]
        return f"{match.group(0)} **【判定ライン: {amount * multiplier:,.0f}百万円】**"

    def replace_fixed_people(match):
        people = _to_float(match.group(1))
        return f"{match.group(0)} **【判定ライン: {people:,.0f}人】**"

    # 1億円未満、500百万円以上、3000万円相当 等のパーサー
    pattern_fixed_amount = r'([１-９1-9][０-９0-9０-９,，\.．]*)\s*(億円|百万円|万円)'
    text = re.sub(pattern_fixed_amount, replace_fixed_amount, text)

    # 100人以上、50名未満 等のパーサー
    pattern_fixed_people = r'([１-９1-9][０-９0-9０-９,，\.．]*)\s*(人|名)'
    text = re.sub(pattern_fixed_people, replace_fixed_people, text)

    # 純資産額の100分の30 等のパーサー (「の 100分」「の総額の」等の表記揺れに対応)
    # 固定金額・人数の注記を先に入れてから処理し、分数計算で生成した金額を再抽出しない。
    pattern_fraction = r'(純資産額|売上高|仕入高|経常利益金額|当期純利益金額|当期純利益|利益|資産の額|総資産の帳簿価額|純資産の額|資本金の額)(?:の総額)?\s*の\s*([０-９0-9]+)\s*分の\s*([０-９0-9\.]+)'
    text = re.sub(pattern_fraction, replace_fraction, text)
    
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
