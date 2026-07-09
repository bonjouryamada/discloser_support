# web_v2 ExcelレポートQA

## TODO-11/12 REPORT+QA

- 対象: `web_v2/report_export.py`, `web_v2/tests/test_report_export.py`, `docs/web_v2_report_qa.md`
- 検証日: 2026-07-08
- 検証ケース: `LC-DEC-13`（上場会社・決定事実 / 事業の全部又は一部の譲渡又は譲受け）

## 検証内容

- 会社名・証券コード入力、EDINET取得企業名がExcelに出力されること。
- 開示区分、開示項目、mapping_id、手動レビュー、手動レビュー理由、PDF頁がExcelに出力されること。
- 東証適時開示、内部者取引規制、臨時報告書の3制度について、本文と数値ライン要約がExcelに出力されること。
- 財務数値（連結純資産、連結売上高、連結経常利益、連結純利益、資本金）がExcelに出力されること。
- 免責文がExcelに出力されること。

## 実行結果

- 実行コマンド: `.venv\Scripts\python.exe -m unittest tests\test_report_export.py`
- 結果: OK（2 tests）
- 追加確認: `.venv\Scripts\python.exe -m unittest discover -s tests`
- 追加確認結果: OK（10 tests）

## 2026-07-09 ORCH 追記

- 追加確認: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 追加確認結果: OK（11 tests）
- 公開用ZIP `outputs/disclosure_support_v2_source_20260709.zip` に本QA記録を同梱。
