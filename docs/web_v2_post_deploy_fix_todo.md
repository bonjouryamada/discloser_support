# Web V2 Post-Deploy Fix TODO

作成日: 2026-07-09  
ORCH: Codex  
対象: EDINET取得表示、決算期表示、内部ID非表示

## 背景

公開版で、EDINET取得後に「財務データを取得しました」と表示される一方、財務数値がすべて0になるケースが確認された。また、どの有価証券報告書・何年何月期から取得した値かが画面に出ていない。さらに、`LC-DEC-01` 等の内部管理IDが利用者に意味不明な表示として出ている。

## TODO

| ID | 状態 | 担当 | 内容 | 受入基準 |
| --- | --- | --- | --- | --- |
| PDFIX-01 | 完了 | EDINET worker | EDINET検索結果に書類メタ情報を持たせる | docID、提出者名、書類名、提出日、対象期候補を返す |
| PDFIX-02 | 完了 | EDINET worker | XBRLから対象決算期を抽出する | CurrentFiscalYearEndDateDEI等から `YYYY年M月期` を作れる |
| PDFIX-03 | 完了 | EDINET worker | 財務値抽出対象タグを拡張する | name/contextRef属性を持つタグを対象にし、金融/保険寄りタグも拾う |
| PDFIX-04 | 完了 | UI worker | EDINET取得元を画面に表示する | 書類名、提出日、対象決算期、docIDが見える |
| PDFIX-05 | 完了 | UI worker | 財務数値欄に対象期を表示する | 「表示中の決算数値: YYYY年M月期（百万円）」が出る |
| PDFIX-06 | 完了 | UI worker | 0値/欠損時の警告を明確にする | 全部0または欠損時に、取得成功だけで終わらず注意を出す |
| PDFIX-07 | 完了 | UI worker | 内部管理IDを画面から消す | サイドバー、カード、バッジに `LC-DEC-01` 等を出さない |
| PDFIX-08 | 完了 | REPORT worker | Excelから内部管理IDを消す | `mapping_id` 行を削除し、利用者向け情報だけ出す |
| PDFIX-09 | 完了 | REPORT worker | ExcelにEDINET取得元/対象期を出す | 書類名、提出日、対象期、docID、財務数値期を出力 |
| PDFIX-10 | 完了 | ORCH | 全テストとローカルQAを実施する | unittest全件OK、画面上で内部ID非表示と対象期表示を確認 |
| PDFIX-11 | ローカル完了・公開反映待ち | ORCH/USER | GitHub/Streamlitへ反映する | 修正ZIPを作成済み。GitHub反映後にStreamlitで再デプロイ |

## worker運用

- worker推論レベルはlow。
- workerは担当ファイル以外を編集しない。
- ORCHが成果物を確認し、受入基準未達なら同じworkerへ差し戻す。
- APIキー値は記録しない。
- 検証結果: `python -m unittest discover -s tests -v` 15件OK、主要ファイルの構文確認OK、Streamlitテストで例外0件。
- 配布ZIP: `outputs/disclosure_support_v2_source_20260710_postfix.zip`
- 公開反映はGitHubへのアップロード後にStreamlitで再デプロイする。
