import os
import requests
import zipfile
import io
import datetime
import concurrent.futures
import re
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
    "net_assets": [
        "netassets",
        "totalequity",
        "equityattributabletoownersofparent",
        "equityifrs",
        "totalnetassets",
    ],
    "net_sales": [
        "netsales",
        "operatingrevenue",
        "operatingrevenues",
        "ordinaryrevenues",
        "ordinaryincome",
        "ordinaryincometotal",
        "revenueifrs",
        "insurancerevenue",
        "insurancepremiumsandincome",
        "netpremiums",
        "insurancepremium",
    ],
    "recurring_profit": [
        "ordinaryprofit",
        "ordinaryincomeloss",
        "recurringprofit",
        "profitbeforetax",
        "profitlossbeforetax",
        "incomebeforeincometaxes",
    ],
    "net_income": [
        "profitlossattributabletoownersofparent",
        "profitattributabletoownersofparent",
        "profitlossattributabletoownersoftheparent",
        "netincomeloss",
        "netincome",
    ],
    "capital_stock": ["capitalstock"],
}

FINANCIAL_LABELS = {
    "net_assets": "連結純資産",
    "net_sales": "連結売上高/経常収益",
    "recurring_profit": "連結経常利益",
    "net_income": "親会社株主に帰属する当期純利益",
    "capital_stock": "資本金",
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

def _tag_name_attr(tag):
    return tag.get("name") or getattr(tag, "name", "") or ""

def _get_attr(tag, attr_name):
    if tag.has_attr(attr_name):
        return tag.get(attr_name)
    attr_lower = attr_name.lower()
    for key, value in tag.attrs.items():
        if str(key).lower() == attr_lower:
            return value
    return None

def _financial_key_for_tag(name_attr):
    name = name_attr.lower().split(":")[-1]
    if _is_abstract_tag(name):
        return None
    if "ordinaryincomeloss" in name:
        return "recurring_profit"
    for key, patterns in FINANCIAL_TAG_PATTERNS.items():
        if any(pattern in name for pattern in patterns):
            return key
    return None

def _financial_match_score(name_attr):
    name = name_attr.lower().split(":")[-1]
    if _is_abstract_tag(name):
        return None
    if "ordinaryincomeloss" in name:
        return ("recurring_profit", 300)
    best = None
    for key, patterns in FINANCIAL_TAG_PATTERNS.items():
        for index, pattern in enumerate(patterns):
            if pattern == name:
                priority = 500 - index
            elif name.endswith(pattern):
                priority = 350 - index
            elif pattern in name:
                priority = 200 - index
            else:
                continue
            if best is None or priority > best[1]:
                best = (key, priority)
    return best

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
    val_str = tag.text.replace(",", "").replace("，", "").strip()
    if not val_str:
        return None

    negative = val_str.startswith("(") and val_str.endswith(")")
    val_str = val_str.strip("()")
    val = float(val_str)
    if negative:
        val = -val
    if tag.get("sign", "+") == "-":
        val = -val

    scale = tag.get("scale")
    if scale:
        try:
            return val * (10 ** int(scale)) / 1_000_000
        except ValueError:
            return val / 1_000_000
    return val / 1_000_000

DEBUG_FINANCIAL_TERMS = (
    "equity", "asset", "revenue", "income", "profit", "capital",
    "insurance", "premium",
)

def _rank_debug_candidates(candidates):
    def rank(candidate):
        tag_name = candidate["tag_name"].lower()
        return (
            candidate["normalized_value"] != 0,
            any(term in tag_name for term in DEBUG_FINANCIAL_TERMS),
        )

    return sorted(candidates, key=rank, reverse=True)[:20]

def _parse_financial_data_from_soup(soup, debug_candidates=None):
    parsed_data = {}

    for tag in soup.find_all(lambda item: _tag_name_attr(item) and _get_attr(item, "contextRef")):
        name_attr = _tag_name_attr(tag)
        context_ref = _get_attr(tag, "contextRef")
        context_score = _context_score(context_ref)
        if context_score is None:
            continue

        try:
            val_in_millions = _value_in_millions(tag)
        except ValueError:
            continue
        if val_in_millions is None:
            continue

        match = _financial_match_score(name_attr)
        if debug_candidates is not None and _get_attr(tag, "unitRef"):
            debug_candidates.append({
                "tag_name": name_attr,
                "context_ref": context_ref,
                "raw_value": tag.get_text(strip=True),
                "normalized_value": val_in_millions,
                "candidate_key": match[0] if match else "unmatched",
            })

        if not match:
            continue
        key, tag_priority = match

        candidate_score = (
            val_in_millions != 0,
            context_score,
            tag_priority,
            abs(val_in_millions),
        )
        previous = parsed_data.get(key)
        if previous is None or candidate_score > previous[1]:
            parsed_data[key] = (val_in_millions, candidate_score)

    return parsed_data

def _parse_date(value):
    if not value:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(text[:10], pattern).date()
        except ValueError:
            pass
    match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if match:
        return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None

def _period_label_from_end_date(end_date):
    parsed = _parse_date(end_date)
    if not parsed:
        return ""
    return f"{parsed.year}年{parsed.month}月期"

def _extract_doc_info_from_soup(soup):
    info = {}
    tag_patterns = {
        "period_start": ["currentfiscalyearstartdatedei", "currentperiodstartdatedei"],
        "period_end": ["currentfiscalyearenddatedei", "currentperiodenddatedei"],
        "document_title": ["documenttitlecoverpage"],
    }
    for tag in soup.find_all(lambda item: _tag_name_attr(item)):
        name = _tag_name_attr(tag).lower().split(":")[-1]
        text = tag.get_text(strip=True)
        if not text:
            continue
        for key, patterns in tag_patterns.items():
            if key not in info and any(pattern in name for pattern in patterns):
                info[key] = text
    if info.get("period_end"):
        info["period_label"] = _period_label_from_end_date(info["period_end"])
    return info

def _merge_doc_info(base, update):
    merged = dict(base or {})
    for key, value in (update or {}).items():
        if value and not merged.get(key):
            merged[key] = value
    if not merged.get("period_label") and merged.get("period_end"):
        merged["period_label"] = _period_label_from_end_date(merged["period_end"])
    return merged

def _format_doc_info(info):
    info = info or {}
    parts = []
    if info.get("doc_description"):
        parts.append(info["doc_description"])
    elif info.get("document_title"):
        parts.append(info["document_title"])
    if info.get("period_label"):
        parts.append(info["period_label"])
    if info.get("period_start") or info.get("period_end"):
        parts.append(f"{info.get('period_start', '?')}〜{info.get('period_end', '?')}")
    if info.get("submit_datetime"):
        parts.append(f"提出日: {str(info['submit_datetime'])[:10]}")
    if info.get("doc_id"):
        parts.append(f"docID: {info['doc_id']}")
    return " / ".join(parts)

def _format_financial_data(parsed_data, doc_info=None, debug_candidates=None):
    missing_keys = [key for key in FINANCIAL_KEYS if key not in parsed_data]
    financial_data = {key: parsed_data.get(key, (0, 0))[0] for key in FINANCIAL_KEYS}
    financial_data["missing_keys"] = missing_keys
    financial_data["doc_info"] = doc_info or {}
    financial_data["doc_info_label"] = _format_doc_info(doc_info)
    warnings = [
        "EDINET XBRLで値を取得できなかった項目があります: "
        + "、".join(FINANCIAL_LABELS.get(key, key) for key in missing_keys)
    ] if missing_keys else []
    ranked_debug_candidates = _rank_debug_candidates(debug_candidates or [])
    all_values_zero = all(
        financial_data.get(key, 0) == 0 for key in FINANCIAL_KEYS
    )
    has_zero_or_missing = bool(missing_keys) or any(
        financial_data.get(key, 0) == 0 for key in FINANCIAL_KEYS
    )
    if all_values_zero and ranked_debug_candidates:
        warnings.append(
            "EDINET XBRLで候補タグは見つかりましたが、値がすべて0です。"
            "財務諸表タグの形式が未対応の可能性があります。"
        )
    if has_zero_or_missing and ranked_debug_candidates:
        financial_data["debug_candidates"] = ranked_debug_candidates
    financial_data["warnings"] = warnings
    return financial_data

def _extract_financial_data_from_zip_bytes(zip_bytes, doc_info=None):
    parsed_data = {}
    debug_candidates = []
    merged_doc_info = dict(doc_info or {})

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        xbrl_files = [
            f for f in z.namelist()
            if f.startswith("XBRL/PublicDoc/")
            and f.lower().endswith((".htm", ".html", ".xbrl", ".xml"))
        ]

        for xbrl_file in xbrl_files:
            html_content = z.read(xbrl_file)
            soup = BeautifulSoup(html_content, "html.parser")
            merged_doc_info = _merge_doc_info(merged_doc_info, _extract_doc_info_from_soup(soup))
            for key, candidate in _parse_financial_data_from_soup(
                soup, debug_candidates
            ).items():
                previous = parsed_data.get(key)
                if previous is None or candidate[1] > previous[1]:
                    parsed_data[key] = candidate

    return _format_financial_data(parsed_data, merged_doc_info, debug_candidates)

def _doc_metadata_from_result(doc, target_date_str):
    period_start = doc.get("periodStart")
    period_end = doc.get("periodEnd")
    return {
        "doc_id": doc.get("docID"),
        "filer_name": doc.get("filerName") or "",
        "sec_code": str(doc.get("secCode") or ""),
        "doc_description": doc.get("docDescription") or "",
        "submit_datetime": doc.get("submitDateTime") or target_date_str,
        "search_date": target_date_str,
        "period_start": period_start,
        "period_end": period_end,
        "period_label": _period_label_from_end_date(period_end),
    }

def _subscription_key_from_headers(headers):
    return (headers or {}).get("Ocp-Apim-Subscription-Key")

def _response_error_message(resp, action):
    detail = getattr(resp, "text", "") or ""
    detail = detail.strip()
    if len(detail) > 200:
        detail = detail[:200] + "..."
    suffix = f": {detail}" if detail else ""
    return f"EDINET APIエラー（{action} HTTP {resp.status_code}）{suffix}"

def get_doc_id_for_date(target_date_str, company_name, base_url, headers):
    params = {"date": target_date_str, "type": 2}
    api_key = _subscription_key_from_headers(headers)
    if api_key:
        params["Subscription-Key"] = api_key
    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=20)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        raise RuntimeError(_response_error_message(resp, "書類一覧取得"))

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
                return _doc_metadata_from_result(doc, target_date_str)
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
                    d_str = future_to_date[future]
                    found_docs.append((d_str, result))
                    
        if found_docs:
            # 同じチャンク内で複数見つかった場合は、もっとも日付が新しいものを優先
            found_docs.sort(key=lambda x: x[0], reverse=True)
            return found_docs[0][1]
            
    return None

def extract_financial_data_from_xbrl(doc_id, doc_info=None):
    """
    doc_id から ZIPを取得し、内容のXBRL(.htm)をパースして純資産・売上高・経常利益・当期純利益を抽出します。
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("EDINET_API_KEY is not set in secrets.toml or .env (ファイルが保存されていない可能性があります)")
        
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
    params = {"type": 1, "Subscription-Key": api_key} # 1 = zip containing xbrl
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=60)
    except requests.RequestException as exc:
        raise Exception(f"EDINETから文書を取得できませんでした: {exc}") from exc
    if resp.status_code != 200:
        raise Exception(_response_error_message(resp, f"文書取得 docID={doc_id}"))
        
    merged_info = _merge_doc_info(doc_info, {"doc_id": doc_id})
    return _extract_financial_data_from_zip_bytes(resp.content, merged_info)

def get_financial_data(company_name):
    """
    会社名によりAPIからXBRLデータを検索・抽出し、辞書で返します。
    """
    doc_result = get_latest_yuho_doc_id(company_name, max_days=365)
    if not doc_result:
        raise ValueError(f"過去1年間に提出された「{company_name}」の有価証券報告書が見つかりませんでした。")
    
    return extract_financial_data_from_xbrl(doc_result["doc_id"], doc_result)
