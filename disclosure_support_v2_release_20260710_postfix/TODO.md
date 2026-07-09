# Disclosure Support V2 TODO

最終更新: 2026-07-09  
状態は `未着手`、`進行中`、`レビュー待ち`、`入力待ち`、`完了`、`保留` で管理する。完了判定は worker の自己申告ではなく、ORCH が受入基準と検証結果を確認して確定する。

## 優先 TODO

| ID | 状態 | 担当 | TODO | 受入基準・現在の判定 |
| --- | --- | --- | --- | --- |
| TODO-01 | 完了 | PLAN | 実装計画書と TODO を作成する | `IMPLEMENTATION_PLAN.md` と本 TODO を整備済み。 |
| TODO-02 | 完了 | QA | ローカル単体テスト環境を復旧する | `.venv` で依存関係同期済み。`.\.venv\Scripts\python.exe -m unittest discover -s tests -v` が 11 tests OK。 |
| TODO-03 | 完了 | DATA | 正本データ101項目・6区分・manual 13件を読み込む | `test_data_service.py` 成功。101項目、mapping_id 101件、6区分、manual 13件を確認済み。 |
| TODO-04 | 保留 | DATA/ORCH | 公式一次情報との差分確認を実施する | 公式リンク到達確認済み。JPX規則改正ページで 2026-07-03 公表情報を確認。本文差分精査は公開前ゲートとして残す。 |
| TODO-05 | 完了 | APP | 検索、区分、手動レビュー絞り込みを提供する | ブラウザQAで検索欄、0件時警告、条件変更案内を確認済み。 |
| TODO-06 | 完了 | APP | 3制度比較表示を提供する | 東証適時開示、内部者取引規制、臨時報告書、数値ライン要約タブを確認済み。 |
| TODO-07 | 完了 | APP | 「該当記載なし」の注意を表示する | `regime_text()` と画面 caption で非該当ではない旨を表示。 |
| TODO-08 | 完了 | APP | 動的判定ラインの抽出精度をレビューする | 固定金額、百万円、万円、人数、分数基準の代表テストを追加済み。自動抽出は一部候補である旨をUI表示。 |
| TODO-09 | 入力待ち | EDINET/USER | 現行 EDINET API キーを安全に引き継ぐ | `.env` / Streamlit Secrets 手順とサンプルは整備済み。実キー登録はユーザー本人またはStreamlit管理画面操作が必要。 |
| TODO-10 | 保留 | EDINET | 実 EDINET API で有報検索と XBRL 抽出を結合テストする | ネットワーク不要テストは4件成功。実APIテストは `EDINET_API_KEY` と外部接続が必要。 |
| TODO-11 | 完了 | REPORT | Excel 出力テストを復旧する | `test_report_export.py` 成功。生成ファイルを `openpyxl` で開ける。 |
| TODO-12 | 完了 | REPORT | Excel レポート内容を業務観点でレビューする | 会社入力、取得企業名、開示区分、開示項目、mapping_id、手動レビュー、PDF頁、3制度本文、数値ライン、財務数値、免責を検証済み。 |
| TODO-13 | 完了 | QA | PC・スマートフォン表示を確認する | PC幅と390px幅で、検索、項目表示、3制度表示、Excelボタン、出典ページを確認済み。 |
| TODO-14 | 入力待ち | DEPLOY/USER | 現行 GitHub/Streamlit 情報を確定する | 作業場所はGitリポジトリではなく、`gh`も未導入。配置先repo、branch、Streamlit公開方針が必要。 |
| TODO-15 | 入力待ち | DEPLOY/USER | 運営者情報と規約方針を確定する | 正式サイト名、運営者名、問い合わせ先、規約・プライバシーポリシー要否が必要。 |
| TODO-16 | レビュー待ち | DEPLOY | 出典・更新情報ページを公開用に仕上げる | 公式リンク、確認日、免責、公開前確認事項は表示済み。運営者情報確定後に最終文言へ差し替え。 |
| TODO-17 | 入力待ち | DEPLOY/USER | V2 を別 URL で先行公開する | GitHub/Streamlitログイン・Secrets登録が必要。 |
| TODO-18 | 入力待ち | QA/USER | 先行公開 URL で結合テストする | 先行公開URL取得後に、実EDINET、Excel、PC/スマホを再確認する。 |
| TODO-19 | 入力待ち | ORCH/USER | 現行 URL を V2 へ切り替える | TODO-04、09、10、14、15、18 完了後に実施。 |
| TODO-20 | 保留 | ORCH | 公開後 PDCA を運用する | 公開後に法改正、EDINET API、問い合わせ、利用者フィードバックの定期確認へ移行。 |

## worker / ORCH 実績

| 日付 | Phase | 記録 | 判定 |
| --- | --- | --- | --- |
| 2026-07-08 | Plan | PLAN worker が実装計画書と TODO を作成。 | 受入済み |
| 2026-07-08 | Check | CODE AUDIT worker が中リスクを抽出。 | 指摘をAPP/EDINET/REPORTへ展開 |
| 2026-07-08 | Do | APP worker が検索0件、数値抽出、入力エラー処理を修正。 | 受入済み |
| 2026-07-08 | Do | EDINET worker が証券コード一致、XBRL context選別、欠損警告を修正。 | 受入済み |
| 2026-07-08 | Do | REPORT worker がExcel内容検証テストとQA記録を追加。 | 受入済み |
| 2026-07-09 | Act | APP警告表示はworker差し戻し後も未反映。追加workerは利用上限で失敗したため、ORCHが最小修正を実施。 | 受入済み |
| 2026-07-09 | Check | 単体テスト 11件 OK、PC/スマホ ブラウザQA OK。 | ローカル公開素材として受入 |
| 2026-07-09 | Act | 公開用ZIP `outputs/disclosure_support_v2_source_20260709_final.zip` を作成。 | GitHub/Streamlit情報待ち |

## 残ブロッカー

| ID | 内容 | 影響 | 解消に必要なもの |
| --- | --- | --- | --- |
| BLK-02 | 現行 GitHub/Streamlit 情報が未確定 | デプロイ、Secrets引き継ぎ、先行公開ができない | repo URL、branch、Streamlit公開方針 |
| BLK-03 | 運営者情報と規約方針が未確定 | 公開用表示と法務文言が確定しない | サイト名、運営者名、問い合わせ先、規約・プライバシーポリシー要否 |
| BLK-04 | 公式一次情報の本文差分確認が未完了 | 制度面の公開ゲートを通過できない | JPX規則・e-Gov本文の業務レビュー |
| BLK-05 | 実EDINET API結合テスト未実施 | EDINET自動取得の本番保証が未完了 | `EDINET_API_KEY` のSecrets登録、実企業サンプル |

## worker への注意

- API キー値、`.env` 内容、個人情報を TODO、ログ、チャット、コミットへ書かない。
- 担当外ファイルを編集しない。必要がある場合は ORCH に依存 TODO として戻す。
- 受入基準を満たした証跡を残す。証跡がないものは「完了」にしない。
- 外部確認が必要なものは、実装済みでも「入力待ち」または「保留」として扱う。
- 公開判断は ORCH が行い、worker 単独で現行 URL 切替を行わない。
