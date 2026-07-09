# Disclosure Support V2

東証適時開示、内部者取引規制、臨時報告書の関連基準を横断確認するStreamlitアプリです。

## Local run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

EDINET取得を使う場合は、ローカルでは`.env`、Streamlit Community CloudではSecretsに
`EDINET_API_KEY`を設定してください。`.env`やAPIキーはリポジトリへコミットしないでください。

## Test

```powershell
python -m unittest discover -s tests -v
```

データ正本は`data/pdf_reference.json`と`data/item_mapping.json`です。添付PDFには基準日の明示が
ないため、公開・更新前に現行のJPX規則およびe-Gov法令を確認してください。
