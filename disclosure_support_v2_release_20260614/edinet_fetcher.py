import os
import requests
import zipfile
import io
import datetime
import concurrent.futures
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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
                # APIは5桁(例:72030)で返すため前方一致なども含め包含判定
                elif sec_code and company_name in sec_code:
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
        
    parsed_data = {}
    
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        htm_files = [f for f in z.namelist() if f.startswith("XBRL/PublicDoc/") and f.endswith(".htm")]
        
        for htm_file in htm_files:
            html_content = z.read(htm_file)
            soup = BeautifulSoup(html_content, "html.parser")
            
            elements = soup.find_all("ix:nonfraction")
            for tag in elements:
                name_attr = tag.get("name", "").lower()
                context_ref = tag.get("contextref", "").lower()
                
                # 直近年度(CurrentYear)のみ取得
                if "currentyear" in context_ref:
                    val_str = tag.text.replace(",", "").strip()
                    try:
                        sign = tag.get("sign", "+")
                        if not val_str:
                            continue
                        val = int(val_str)
                        if sign == "-": val = -val

                        # 単位判定と「百万円」への統一
                        # unitRefやscale, decimalsを複合的に評価して、元データが「円」か「百万円」かを判定する
                        scale = tag.get("scale")
                        unit_ref = tag.get("unitref", "").lower()
                        decimals = tag.get("decimals")
                        
                        # jpy（円）であり、かつ scale が設定されていない場合は、通常1円単位のデータと見なす
                        if scale:
                            try:
                                val_in_millions = val * (10 ** int(scale)) / 1_000_000
                            except ValueError:
                                val_in_millions = val / 1_000_000
                        else:
                            # 企業によっては「百万円」単位のデータを直接入力しているケースがある
                            # その場合は通常 unit_ref が millions などを指すか、あるいは値自体が桁違いに小さい
                            # （ただし日本のEDINETの標準コンテキストでは、金額は「円」単位で格納されるのが原則）
                            # 「円」単位とみなして 1,000,000 で除算する
                            val_in_millions = val / 1_000_000
                            
                        # 明示的に Consolidated かどうかを確認（前方一致等も含め）
                        is_consolidated = "consolidated" in context_ref.lower()
                        
                        def update_best(k):
                            if k not in parsed_data:
                                parsed_data[k] = (val_in_millions, is_consolidated)
                            else:
                                prev_val, prev_cons = parsed_data[k]
                                # 連結タグ（Consolidated）を最優先で取得し上書き
                                if is_consolidated and not prev_cons:
                                    parsed_data[k] = (val_in_millions, is_consolidated)

                        # 売上、純資産、経常利益、純利益の各タグ名に対応
                        if any(x in name_attr for x in ["netassets", "netassetsabstract"]):
                            update_best("net_assets")
                        elif any(x in name_attr for x in ["netsales", "operatingrevenue", "ordinaryrevenues", "revenue"]):
                            update_best("net_sales")
                        elif any(x in name_attr for x in ["ordinaryincome", "ordinaryprofit", "ordinaryincomeloss"]):
                            update_best("recurring_profit")
                        elif any(x in name_attr for x in ["profitlossattributabletoownersofparent", "netincomeloss", "profitloss"]):
                            update_best("net_income")
                        elif any(x in name_attr for x in ["capitalstock"]):
                            update_best("capital_stock")
                    except ValueError:
                        pass
                        
    # 最終整形: 見つからなかった項目は0とする
    financial_data = {
        "net_assets": parsed_data.get("net_assets", (0, False))[0],
        "net_sales": parsed_data.get("net_sales", (0, False))[0],
        "recurring_profit": parsed_data.get("recurring_profit", (0, False))[0],
        "net_income": parsed_data.get("net_income", (0, False))[0],
        "capital_stock": parsed_data.get("capital_stock", (0, False))[0]
    }
            
    return financial_data

def get_financial_data(company_name):
    """
    会社名によりAPIからXBRLデータを検索・抽出し、辞書で返します。
    """
    doc_result = get_latest_yuho_doc_id(company_name, max_days=365)
    if not doc_result:
        raise ValueError(f"過去1年間に提出された「{company_name}」の有価証券報告書が見つかりませんでした。")
    
    doc_id, _ = doc_result
    return extract_financial_data_from_xbrl(doc_id)
