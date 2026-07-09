# Disclosure Support V2 Implementation Plan

最終更新: 2026-07-09

## 1. 目的

`web_v2` は、東証適時開示、金融商品取引法上の重要事実の軽微基準、臨時報告書提出基準を、同一の開示事象から横断確認する Streamlit アプリである。PDF全6区分・101項目を正本データとして採用し、EDINET取得、財務数値入力、動的判定ライン、Excel出力、出典確認を提供する。

## 2. 進行方針

- ORCH が TODO、依存関係、worker成果、公開可否を管理する。
- worker は TODO 単位・所有ファイル単位で作業し、ORCH が成果物をレビューする。
- APIキー、`.env`、Secretsの値は記録・共有・コミットしない。
- 外部サービス操作、実APIキー登録、法令本文の業務差分精査は公開前ゲートとして明示する。

## 3. 現在の実装状態

### 完了済み

- PDF全6区分・101項目、mapping_id 101件、manual 13件の読み込み。
- キーワード検索、区分選択、manual絞り込み、0件時の停止・案内表示。
- 東証適時開示、内部者取引規制、臨時報告書、数値ライン要約の4タブ表示。
- 「該当記載なし」は非該当を意味しない旨の注意表示。
- 財務数値による判定ライン注入。固定金額、百万円、万円、人数、分数基準の代表ケースをテスト済み。
- EDINET証券コード完全一致、XBRL Abstract除外、CurrentYear/Consolidated context優先、欠損値警告。
- EDINET取得結果の `warnings` / `missing_keys` をUI表示し、財務計算用データは5数値キーに限定。
- Excelレポートに会社入力、取得企業名、開示情報、3制度本文、数値ライン、財務数値、免責を出力。
- 出典・更新情報に公式リンク、確認日、免責、公開前確認事項を表示。
- Streamlit 1.59系の `use_container_width` 警告を `width="stretch"` に更新。

### 検証済み

- 単体テスト: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 結果: 11 tests OK
- ブラウザQA: PC幅、390px幅で、検索、0件案内、全101項目一覧、出典ページ、3制度表示、Excelボタンを確認済み。
- 公式リンク確認: 2026-07-09 に JPX規則ページ、JPX規則改正ページ、e-Gov法令リンクへ到達確認。JPX規則改正ページで 2026-07-03 公表情報を確認。

## 4. worker 体制

| Role | 所有範囲 | 現状 |
| --- | --- | --- |
| PLAN | `IMPLEMENTATION_PLAN.md`, `TODO.md` | 計画・TODO作成済み。ORCHが最新化。 |
| DATA | `data/*.json`, データ検証 | 101項目・6区分・manual 13件は完了。法令本文差分は公開前ゲート。 |
| APP | `app.py`, `data_service.py`, `disclosure_calculator.py` | UI、検索、数値ライン、警告表示、レスポンシブQA完了。 |
| EDINET | `edinet_fetcher.py`, EDINETテスト | ネットワーク不要テスト完了。実API結合はSecrets登録後。 |
| REPORT | `report_export.py`, Excelテスト | Excel生成・内容検証完了。 |
| QA | `tests/*`, ブラウザ確認 | 11 tests OK、PC/スマホQA OK。 |
| DEPLOY | README、DEPLOYMENT、公開手順 | ローカル素材準備済み。GitHub/Streamlit情報待ち。 |

## 5. フェーズ計画

### Phase 0: ローカル品質ゲート

完了。依存関係を `.venv` に同期し、全単体テストとローカル画面QAを通過した。

### Phase 1: 公開素材作成

完了。`web_v2` のアプリ、データ、テスト、設定、ドキュメントをクリーンなZIPにまとめた。

- 展開フォルダ: `outputs/disclosure_support_v2_release_20260709_final`
- ZIP: `outputs/disclosure_support_v2_source_20260709_final.zip`
- 実キー、`.env`、`.streamlit/secrets.toml`、`.venv`、`__pycache__`、`*.pyc` は含めない。

### Phase 2: 外部入力確定

未完了。次をユーザーまたは管理画面で確定する。

- GitHub配置先リポジトリURL、ブランチ、実行ファイルパス。
- Streamlitで別URL先行公開にするか、現行URLを置換するか。
- Streamlit Secrets の `EDINET_API_KEY`。
- 正式サイト名、運営者名、問い合わせ先、利用規約・プライバシーポリシー要否。

### Phase 3: 公開前業務レビュー

未完了。JPX規則、JPX規則改正、e-Gov法令本文と、現在の101項目データの差分を確認する。添付PDFに基準日明示がないため、このフェーズは公開完了条件から外さない。

### Phase 4: 先行公開・結合テスト

未着手。GitHub/Streamlit設定後、先行公開URLで次を確認する。

- EDINET実APIで有報検索とXBRL抽出。
- 検索、全101項目一覧、manual 13件。
- 財務手入力、Excel出力、出典ページ。
- PC幅・スマートフォン幅表示。

### Phase 5: 現行URL切替・運用

未着手。Phase 2-4 の完了後に、現行URLをV2へ切り替える。切替日時、戻し手順、確認者を記録し、公開後は法改正、EDINET API仕様変更、問い合わせ、利用者フィードバックを定期確認する。

## 6. 公開完了条件

- 単体テスト11件が成功している。
- PC幅・スマートフォン幅のローカルQAが成功している。
- 公開用ZIPに実キー、`.env`、Secrets実体、`.venv`、キャッシュが含まれていない。
- GitHub/Streamlit設定とSecrets登録が完了している。
- 実EDINET API結合テストが成功、または未取得理由が記録されている。
- JPX規則・e-Gov法令本文との差分確認が完了している。
- 運営者、問い合わせ先、規約・プライバシーポリシー方針、更新責任者が確定している。
- 先行公開URLで結合テストが完了している。

## 7. 主要リスクと対応

| リスク | 影響 | 対応 |
| --- | --- | --- |
| APIキー漏えい | EDINET APIの不正利用 | Secretsと`.env`のみ使用。値を記録しない。 |
| 法令差分未確認 | 判定補助情報の誤表示 | 本文差分レビューを公開前ゲートに残す。 |
| XBRLタグ揺れ | 財務数値の誤抽出 | 欠損警告を表示し、手入力補正を維持。実APIテストでサンプル確認。 |
| 数値ライン誤認 | 自動抽出を網羅済みと誤解 | 「自動抽出できた一部の候補」と明記。 |
| 現行URL切替失敗 | 利用者影響 | 別URL先行公開、戻し手順、切替日時を記録。 |

## 8. 引き継ぎメモ

- ローカル起動: `.\.venv\Scripts\python.exe -m streamlit run app.py`
- テスト: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- Streamlit Secrets例: `EDINET_API_KEY = "実際のキー"`
- 実キーはチャット、README、Issue、PR、GitHub、ZIPに含めない。
- 追加worker起動は利用上限で一部失敗したため、2026-07-09 の最後のAPP警告表示修正は ORCH が最小範囲で実装し、テスト・ブラウザQAで受入済み。
