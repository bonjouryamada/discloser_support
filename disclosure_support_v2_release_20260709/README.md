# Disclosure Support V2

東証適時開示、内部者取引規制、臨時報告書の関連基準を横断確認するStreamlitアプリです。

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

EDINET取得を使う場合は、ローカルでは`.env`、Streamlit Community CloudではSecretsに
`EDINET_API_KEY`を設定してください。`.env`やAPIキーはリポジトリへコミットしないでください。

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

2026-07-09時点のローカル確認では、11 tests OK、PC幅・390px幅のブラウザQA OKです。

データ正本は`data/pdf_reference.json`と`data/item_mapping.json`です。添付PDFには基準日の明示が
ないため、公開・更新前に現行のJPX規則およびe-Gov法令本文との差分を確認してください。
