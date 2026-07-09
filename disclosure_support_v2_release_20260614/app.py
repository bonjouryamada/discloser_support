from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from data_service import compact_record, filter_records, get_categories, load_records, regime_text
from disclosure_calculator import extract_summary_lines, inject_dynamic_borderlines
from edinet_fetcher import extract_financial_data_from_xbrl, get_latest_yuho_doc_id
from report_export import generate_report


st.set_page_config(
    page_title="Disclosure Support V2",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+JP:wght@400;500;600&display=swap');
:root { --navy:#102a43; --blue:#2563a6; --line:#d9e2ec; --paper:#f6f8fb; --ink:#172b4d; }
.stApp { background:var(--paper); color:var(--ink); font-family:'Inter','Noto Sans JP',sans-serif; }
[data-testid="stSidebar"] { background:#102a43; min-width:350px; max-width:350px; }
[data-testid="stSidebar"] * { color:#f8fafc; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] * { color:#172b4d; }
.block-container { max-width:1500px; padding-top:2rem; }
.hero { background:linear-gradient(135deg,#102a43,#2563a6); color:white; padding:26px 30px; border-radius:16px; margin-bottom:18px; }
.hero h1 { margin:0; font-size:2rem; }
.hero p { margin:8px 0 0; color:#d9eaf7; }
.badge { display:inline-block; padding:4px 10px; margin:6px 6px 0 0; border-radius:99px; background:#e8f1fa; color:#174a7c; font-size:.8rem; font-weight:600; }
.badge-warn { background:#fff0df; color:#9a3412; }
.event-card { background:white; border:1px solid var(--line); border-left:5px solid var(--blue); padding:18px 20px; border-radius:10px; margin-bottom:15px; }
.criteria-card { background:white; border:1px solid var(--line); border-radius:10px; padding:16px; line-height:1.85; }
.muted { color:#627d98; font-size:.85rem; }
.source-box { background:#fff8e6; border:1px solid #f0c36d; border-radius:10px; padding:14px 16px; }
div.stButton > button, div.stDownloadButton > button { border-radius:8px; font-weight:600; }
@media (max-width: 900px) {
  [data-testid="stSidebar"] { min-width:auto; max-width:none; }
  .block-container { padding:1rem; }
  .hero h1 { font-size:1.45rem; }
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def cached_records():
    return load_records()


def parse_number(value: str) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        return 0.0


def criteria_html(text: str, financial_data: dict[str, float]) -> str:
    processed = inject_dynamic_borderlines(text, financial_data)
    safe = html.escape(processed)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    return safe.replace("\n", "<br>")


records = cached_records()
categories = ["すべて", *get_categories(records)]

st.sidebar.markdown("## 開示項目を探す")
query = st.sidebar.text_input("キーワード検索", placeholder="例: 合併、自己株式、業績予想")
category = st.sidebar.selectbox("区分", categories)
manual_only = st.sidebar.checkbox("手動レビュー要のみ")
filtered = filter_records(records, category, query, manual_only)

if not filtered:
    st.sidebar.warning("条件に一致する開示項目がありません。")
    filtered = records

labels = {
    f"{item['mapping_id']}｜{item['disclosure_item']}": item
    for item in filtered
}
selected_label = st.sidebar.selectbox("開示項目", list(labels))
selected = labels[selected_label]

st.sidebar.markdown("---")
st.sidebar.caption("データ基準")
st.sidebar.write("PDF全6区分・101項目")
st.sidebar.write("基準ブック: 2025-04-01版")
st.sidebar.warning("添付PDFは基準日明示なし。現行一次情報を要確認。")

st.markdown(
    """
<div class="hero">
  <h1>制度横断 開示判定支援 V2</h1>
  <p>東証適時開示・内部者取引規制・臨時報告書を、同じ開示事象から横断確認します。</p>
</div>
""",
    unsafe_allow_html=True,
)

page_assist, page_list, page_sources = st.tabs(["判定支援", "全101項目一覧", "出典・更新情報"])

with page_assist:
    manual_badge = "<span class='badge badge-warn'>手動レビュー要</span>" if selected["manual_review_flag"] else "<span class='badge'>標準確認</span>"
    pages = ", ".join(map(str, selected.get("pdf_pages", [])))
    st.markdown(
        f"""
<div class="event-card">
  <div class="muted">{html.escape(selected['disclosure_category'])}</div>
  <h3>{html.escape(selected['disclosure_item'])}</h3>
  <span class="badge">{html.escape(selected['mapping_id'])}</span>
  <span class="badge">PDF {html.escape(pages)}頁</span>
  {manual_badge}
</div>
""",
        unsafe_allow_html=True,
    )
    if selected["manual_review_flag"]:
        st.warning(f"手動レビュー理由: {selected['manual_review_reason']}")

    if "financial_data" not in st.session_state:
        st.session_state.financial_data = {
            "net_assets": 0.0,
            "net_sales": 0.0,
            "recurring_profit": 0.0,
            "net_income": 0.0,
            "capital_stock": 0.0,
        }
    if "fetched_company_name" not in st.session_state:
        st.session_state.fetched_company_name = ""

    with st.expander("会社財務データ・EDINET取得", expanded=False):
        company_query = st.text_input("会社名または証券コード")
        if st.button("EDINETから最新有価証券報告書を取得", use_container_width=True):
            if not company_query:
                st.warning("会社名または証券コードを入力してください。")
            else:
                with st.spinner("EDINETを検索しています..."):
                    try:
                        result = get_latest_yuho_doc_id(company_query, max_days=365)
                        if not result:
                            raise ValueError("過去1年間の有価証券報告書が見つかりませんでした。")
                        doc_id, filer_name = result
                        st.session_state.financial_data = extract_financial_data_from_xbrl(doc_id)
                        st.session_state.fetched_company_name = filer_name
                        st.success(f"{filer_name} の財務データを取得しました。")
                    except Exception as exc:
                        st.error(f"EDINET取得エラー: {exc}")

        current = st.session_state.financial_data
        columns = st.columns(5)
        fields = [
            ("連結純資産", "net_assets"),
            ("連結売上高", "net_sales"),
            ("連結経常利益", "recurring_profit"),
            ("連結純利益", "net_income"),
            ("資本金", "capital_stock"),
        ]
        updated = {}
        for column, (label, key) in zip(columns, fields):
            with column:
                updated[key] = parse_number(st.text_input(label, value=f"{current.get(key, 0):,.0f}", key=f"metric_{key}"))
        st.session_state.financial_data = updated

    financial_data = st.session_state.financial_data
    timely = regime_text(selected, "timely")
    insider = regime_text(selected, "insider")
    extraordinary = regime_text(selected, "extraordinary")

    summary_columns = st.columns(3)
    for column, title, text in zip(
        summary_columns,
        ["東証適時開示", "内部者取引規制", "臨時報告書"],
        [timely, insider, extraordinary],
    ):
        with column:
            lines = extract_summary_lines(text, financial_data)
            st.metric(title, f"数値ライン {len(lines)}件")
            if "該当記載なし" in text:
                st.caption("該当記載なし。非該当を意味しません。")

    detail_tabs = st.tabs(["東証適時開示", "内部者取引規制", "臨時報告書", "数値ライン要約"])
    for tab, text in zip(detail_tabs[:3], [timely, insider, extraordinary]):
        with tab:
            st.markdown(f"<div class='criteria-card'>{criteria_html(text, financial_data)}</div>", unsafe_allow_html=True)
    with detail_tabs[3]:
        for title, text in [
            ("東証適時開示", timely),
            ("内部者取引規制", insider),
            ("臨時報告書", extraordinary),
        ]:
            st.markdown(f"#### {title}")
            summary = extract_summary_lines(text, financial_data)
            if summary:
                for item in summary:
                    st.markdown(f"- {item['borderline']}")
            else:
                st.caption("該当する定量的な数値判定ラインはありません。")

    report = generate_report(
        selected,
        financial_data,
        company_query=locals().get("company_query", ""),
        fetched_company_name=st.session_state.fetched_company_name,
    )
    st.download_button(
        "判定支援レポートをExcel出力",
        report,
        file_name=f"disclosure_support_{selected['mapping_id']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with page_list:
    st.subheader("制度比較一覧")
    st.caption(f"現在の絞り込み: {len(filtered)} / {len(records)}項目")
    table = pd.DataFrame(compact_record(item) for item in filtered)
    st.dataframe(table, hide_index=True, use_container_width=True, height=620)

with page_sources:
    st.subheader("出典・更新情報")
    st.markdown(
        """
<div class="source-box">
このサイトは判定補助資料です。添付PDFには法令基準日の明示がなく、基準ブックは2025年4月1日版です。
案件判断時は、必ず最新の公式一次情報と個別事実を確認してください。
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
- [JPX 定款等諸規則・諸規則内規](https://www.jpx.co.jp/rules-participants/rules/regulations/index.html)
- [JPX 規則改正新旧対照表](https://www.jpx.co.jp/rules-participants/rules/revise/index.html)
- [金融商品取引法（e-Gov）](https://laws.e-gov.go.jp/law/323AC0000000025)
- [金融商品取引法施行令（e-Gov）](https://laws.e-gov.go.jp/law/340CO0000000321)
- [有価証券の取引等の規制に関する内閣府令（e-Gov）](https://laws.e-gov.go.jp/law/419M60000002059)
- [企業内容等の開示に関する内閣府令（e-Gov）](https://laws.e-gov.go.jp/law/348M50000002005)
"""
    )
    st.info("公開前に、サイト名・運営者表記・問い合わせ先・更新責任者・プライバシーポリシーを確定してください。")

st.caption("© 2026 Disclosure Support V2 | 判定補助であり、法的判断を確定するものではありません。")
