# Web V2 Final Acceptance Record

記録日: 2026-07-09  
対象: `web_v2`

## 結論

ローカルで実装・テスト・画面確認・公開素材準備前レビューまで完了。GitHub / Streamlit への公開、EDINET実API結合、法令本文差分精査、運営者情報確定は外部入力待ち。

## 実装確認済み

- PDF全6区分・101項目、mapping_id 101件、manual 13件。
- 検索、区分、manual絞り込み、0件時の停止と案内。
- 東証適時開示、内部者取引規制、臨時報告書、数値ライン要約の表示。
- 「該当記載なし」は非該当を意味しない注意。
- 動的判定ライン: 分数基準、億円、百万円、万円、人数の代表ケース。
- EDINET XBRL: 証券コード完全一致、Abstract除外、context優先、欠損警告。
- EDINET UI: 取得警告を表示し、財務計算用データは5数値キーに限定。
- Excel: 会社入力、取得企業名、開示情報、3制度本文、数値ライン、財務数値、免責。
- 出典ページ: 公式リンク、確認日、免責、公開前確認事項。

## 実行テスト

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

結果: 11 tests OK

## 公開用素材

- 展開フォルダ: `outputs/disclosure_support_v2_release_20260709_final`
- ZIP: `outputs/disclosure_support_v2_source_20260709_final.zip`
- 混入除外確認: `.env`、`.venv`、`.streamlit/secrets.toml`、`__pycache__`、`*.pyc` は含めない。

## ブラウザQA

ローカル Streamlit を一時起動し、ブラウザで確認。

- PC幅: タイトル、検索、3制度表示、Excelボタン、数値ライン要約、全101項目一覧、出典ページを確認。
- 検索0件: 「検索条件に一致する開示項目がありません」と条件変更案内を確認。
- スマートフォン幅 390px: タイトル、検索、3制度表示、Excelボタンを確認。
- 起動ログ: Streamlit 1.59系の `use_container_width` 警告は `width="stretch"` へ修正後、再QAログでは未検出。

## 公式リンク確認

- JPX 定款等諸規則・諸規則内規: 2026-07-09 到達確認。
- JPX 規則改正新旧対照表: 2026-07-09 到達確認。2026-07-03 公表情報を確認。
- e-Gov 金融商品取引法、企業内容等の開示に関する内閣府令等: リンク到達確認。

## 未完了ゲート

- GitHub配置先リポジトリ、ブランチ、Streamlit公開方針。
- Streamlit Secrets への `EDINET_API_KEY` 登録。
- 実EDINET APIでの企業サンプル結合テスト。
- JPX規則・e-Gov法令本文と101項目データの差分精査。
- 正式サイト名、運営者名、問い合わせ先、規約・プライバシーポリシー要否。
- 先行公開URLでの結合テストと現行URL切替。
