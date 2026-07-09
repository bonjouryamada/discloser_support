import os
import requests
import zipfile
import io
import datetime
import concurrent.futures
from bs4 import BeautifulSoup
from dotenv import load_dotenv

FINANCIAL_KEYS = [
    "net_assets",
    "net_sales",
    "recurring_profit",
    "net_income",
    "capital_stock",
]

FINANCIAL_TAG_PATTERNS = {
    "net_assets": ["netassets"],
    "net_sales": ["netsales", "operatingrevenue", "ordinaryrevenues", "revenue"],
    "recurring_profit": ["ordinaryincome", "ordinaryprofit", "ordinaryincomeloss"],
    "net_income": ["profitlossattributabletoownersofparent", "netincomeloss", "profitloss"],
    "capital_stock": ["capitalstock"],
}

# EDINET_API_KEY will be loaded dynamically to catch .env or st.secrets updates
def get_api_key():
    import os
    from dotenv import load_dotenv
    
    # 1. 優先: Streamlit secretsからの読み込み (GitHub等でのデプロイ環境用)
    try:
        import streamlit as st
        if "EDINET_API_KEY" in st.secrets:
            return st.secrets["EDINET_API_KEY"]
    except ImportError:
        pass
    except FileNotFoundError:
        pass
        
    # 2. フォールバック: ローカルの .env ファイルからの読み込み
    load_dotenv(override=True)
    return os.getenv("EDINET_API_KEY")

def _normalize_sec_code(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 4:
        return digits + "0"
    if len(digits) == 5:
        return digits
    return None

def _sec_code_matches(input_value, edinet_sec_code):
    input_code = _normalize_sec_code(input_value)
    doc_code = _normalize_sec_code(edinet_sec_code)
    return bool(input_code and doc_code and input_code == doc_code)

def _is_abstract_tag(name_attr):
    return name_attr.lower().split(":")[-1].endswith("abstract")

def _financial_key_for_tag(name_attr):
    name = name_attr.lower().split(":")[-1]
    if _is_abstract_tag(name):
        return None
    for key, patterns in FINANCIAL_TAG_PATTERNS.items():
        if any(pattern in name for pattern in patterns):
            return key
    return None

def _context_score(context_ref):
    context = (context_ref or "").lower()
    if "currentyear" not in context:
        return None

    score = 0
    if "consolidated" in context and "nonconsolidated" not in context:
        score += 100
    if "nonconsolidated" in context:
        score -= 20
    if "duration" in context:
        score += 20
    if "instant" in context:
        score += 15
    if "member" in context or "axis" in context:
        score -= 10
    return score

def _value_in_millions(tag):
    val_str = tag.text.replace(",", "").strip()
    if not val_str:
        return None

    val = int(val_str)
    if tag.get("sign", "+") == "-":
        val = -val

    scale = tag.get("scale")
    if scale:
        try:
            return val * (10 ** int(scale)) / 1_000_000
        except ValueError:
            return val / 1_000_000
    return val / 1_000_000

def _parse_financial_data_from_soup(soup):
    parsed_data = {}

    for tag in soup.find_all("ix:nonfraction"):
        name_attr = tag.get("name", "")
        key = _financial_key_for_tag(name_attr)
        if not key:
            continue

        context_score = _context_score(tag.get("contextref", ""))
        if context_score is None:
            continue

        try:
            val_in_millions = _value_in_millions(tag)
        except ValueError:
            continue
        if val_in_millions is None:
            continue

        previous = parsed_data.get(key)
        if previous is None or context_score > previous[1]:
            parsed_data[key] = (val_in_millions, context_score)

    return parsed_data

def _format_financial_data(parsed_data):
    missing_keys = [key for key in FINANCIAL_KEYS if key not in parsed_data]
    financial_data = {key: parsed_data.get(key, (0, 0))[0] for key in FINANCIAL_KEYS}
    financial_data["missing_keys"] = missing_keys
    financial_data["warnings"] = [
        f"EDINET XBRLで値を取得できなかった項目があります: {', '.join(missing_keys)}"
    ] if missing_keys else []
    return financial_data

def _extract_financial_data_from_zip_bytes(zip_bytes):
    parsed_data = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        htm_files = [f for f in z.namelist() if f.startswith("XBRL/PublicDoc/") and f.endswith(".htm")]

        for htm_file in htm_files:
            html_content = z.read(htm_file)
            soup = BeautifulSoup(html_content, "html.parser")
            for key, candidate in _parse_financial_data_from_soup(soup).items():
                previous = parsed_data.get(key)
                if previous is None or candidate[1] > previous[1]:
                    parsed_data[key] = candidate

    return _format_financial_data(parsed_data)

def get_doc_id_for_date(target_date_str, company_name, base_url, headers):
    params = {"date": target_date_str, "type": 2}
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=20)
    except requests.RequestException:
        return None
    if resp.status_code == 200:
        data = resp.json()
        if "results" in data:
            for doc in data["results"]:
                doc_desc = doc.get("docDescription") or ""
                filer_name = doc.get("filerName") or ""
                sec_code = str(doc.get("secCode") or "")
                
                is_match = False
                if company_name in filer_name:
                    is_match = True
                elif _sec_code_matches(company_name, sec_code):
                    is_match = True

                if doc_desc and filer_name and "有価証券報告書" in doc_desc and is_match:
                    return (doc.get("docID"), filer_name)
    return None

def get_latest_yuho_doc_id(company_name, max_days=365):
    """
    過去 max_days 日間から指定された会社名の有価証券報告書のdocIDを検索します。
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("EDINET_API_KEY is not set in secrets.toml or .env (ファイルが保存されていない可能性があります)")
        
    base_url = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    
    current_date = datetime.date.today()
    
    # 365日分のリクエストを一度に投げると、見つかった後も全スレッドの完了を待機してしまい非常に遅くなります。
    # そのため、30日ごとのチャンクで探索し、見つかり次第即座に終了するようにして劇的に高速化します。
    chunk_size = 30
    for chunk_start in range(0, max_days, chunk_size):
        chunk_end = min(chunk_start + chunk_size, max_days)
        dates_to_check = [(current_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(chunk_start, chunk_end)]
        
        found_docs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_date = {executor.submit(get_doc_id_for_date, d_str, company_name, base_url, headers): d_str for d_str in dates_to_check}
            for future in concurrent.futures.as_completed(future_to_date):
                try:
                    result = future.result()
                except requests.RequestException:
                    continue
                if result:
                    doc_id, filer_name = result
                    d_str = future_to_date[future]
                    found_docs.append((d_str, doc_id, filer_name))
                    
        if found_docs:
            # 同じチャンク内で複数見つかった場合は、もっとも日付が新しいものを優先
            found_docs.sort(key=lambda x: x[0], reverse=True)
            return (found_docs[0][1], found_docs[0][2])
            
    return None

def extract_financial_data_from_xbrl(doc_id):
    """
    doc_id から ZIPを取得し、内容のXBRL(.htm)をパースして純資産・売上高・経常利益・当期純利益を抽出します。
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("EDINET_API_KEY is not set in secrets.toml or .env (ファイルが保存されていない可能性があります)")
        
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
    params = {"type": 1} # 1 = zip containing xbrl
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=60)
    except requests.RequestException as exc:
        raise Exception(f"EDINETから文書を取得できませんでした: {exc}") from exc
    if resp.status_code != 200:
        raise Exception(f"Failed to download document {doc_id} from EDINET API.")
        
    return _extract_financial_data_from_zip_bytes(resp.content)

def get_financial_data(company_name):
    """
    会社名によりAPIからXBRLデータを検索・抽出し、辞書で返します。
    """
    doc_result = get_latest_yuho_doc_id(company_name, max_days=365)
    if not doc_result:
        raise ValueError(f"過去1年間に提出された「{company_name}」の有価証券報告書が見つかりませんでした。")
    
    doc_id, _ = doc_result
    return extract_financial_data_from_xbrl(doc_id)
