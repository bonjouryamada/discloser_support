# Web V2 Deploy Discovery

調査日: 2026-07-08

## 調査目的

TODO-03 デプロイ調査として、ローカルで自動的に公開準備できる範囲と、ユーザー本人による外部サービス操作が必要な範囲を切り分ける。

## ローカル Git / GitHub 状態

- 作業場所 `C:\Users\sakit\OneDrive\ドキュメント\insider判定補助ツール` は Git リポジトリではない。
  - `git rev-parse --is-inside-work-tree` は `fatal: not a git repository`。
  - `git status --short` も同じ理由で不可。
- そのため、このローカル作業場所から直接 `commit` / `push` / PR 作成はできない。
- `gh` CLI は見つからない。
  - `where.exe gh` は `INFO: Could not find files for the given pattern(s).`
- 既存の GitHub リポジトリ URL、ブランチ、Streamlit 側の連携先はローカルからは確認できない。

## Streamlit 関連設定

確認できた設定:

- `web_v2/app.py` が Streamlit アプリ本体。
- `web_v2/requirements.txt` あり。
  - `streamlit`
  - `pandas`
  - `python-dotenv`
  - `requests`
  - `beautifulsoup4`
  - `lxml`
  - `openpyxl`
- `web_v2/.streamlit/config.toml` あり。
  - light theme
  - `server.headless = true`
- `web_v2/.streamlit/secrets.toml.example` あり。
  - `EDINET_API_KEY = "replace-with-your-edinet-api-key"`
- `web_v2/.gitignore` あり。
  - `.env`
  - `.venv/`
  - `.streamlit/secrets.toml`
  - `__pycache__/`
  - `.pytest_cache/`
  - `*.pyc`
- `web_v2/README.md` と `web_v2/DEPLOYMENT.md` に、Streamlit Community Cloud では Secrets に `EDINET_API_KEY` を設定し、`.env` や API キーを GitHub にコミットしない旨の記載あり。

## outputs の release zip 妥当性

確認対象:

- `outputs/disclosure_support_v2_source_20260614.zip`
- `outputs/disclosure_support_v2_release_20260614/`

zip に含まれる主な内容:

- `app.py`
- `requirements.txt`
- `.gitignore`
- `.env.example`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`
- `data/item_mapping.json`
- `data/pdf_reference.json`
- `data_service.py`
- `disclosure_calculator.py`
- `edinet_fetcher.py`
- `report_export.py`
- `README.md`
- `DEPLOYMENT.md`
- `UPDATE_PLAN.md`
- `tests/`

判断:

- Streamlit Community Cloud に配置する最小構成として必要な主要ファイルは zip に含まれている。
- zip には `.streamlit/secrets.toml` や実 API キーは含まれていない。
- zip には `__pycache__` / `*.pyc` は含まれていない。
- 展開済みフォルダ `outputs/disclosure_support_v2_release_20260614/` には `__pycache__` が残っているため、GitHub へ置く素材としては zip の中身を使う方が安全。
- `outputs/disclosure_support_v2_release_20260614/.env.example` は `EDINET_API_KEY=replace-with-your-edinet-api-key` のサンプルのみ。

## API キーを引き継ぐ場合の安全な手順

実施してよいこと:

1. ローカル成果物に実キーが混入していないか確認する。
2. `.gitignore` に `.env` と `.streamlit/secrets.toml` が含まれていることを確認する。
3. GitHub にアップロードするファイルは、実キーなしの zip 内容に限定する。
4. Streamlit 用の Secrets サンプルとして `.streamlit/secrets.toml.example` を残す。

ユーザー本人が行う必要があること:

1. 現行 Streamlit アプリ、または現行運用資料から EDINET API キーを確認する。
2. Streamlit Community Cloud の対象アプリで `App settings > Secrets` を開く。
3. 次の形式で Secrets に設定する。

```toml
EDINET_API_KEY = "実際のEDINET APIキー"
```

4. 設定後、Streamlit アプリを再起動または再デプロイする。
5. EDINET 取得機能だけを本番相当で動作確認する。

禁止事項:

- 実 API キーを `.env`、`.streamlit/secrets.toml`、README、Issue、PR コメント、チャット本文に貼らない。
- 実 API キー入りファイルを GitHub にアップロードしない。
- 現行 API キーをこちらの worker が外部サービスから取得しようとしない。

## こちらで自動的に準備できる範囲

ネットワークやログインなしで可能:

- zip の内容確認。
- Git 管理対象にすべきファイル一覧の整理。
- `.gitignore` / Secrets サンプル / README / DEPLOYMENT の整合性確認。
- ローカルテストの実行。
- リリース zip から不要なキャッシュを除いた公開用フォルダを作ること。
- GitHub に置くべきファイルと置いてはいけないファイルのリスト化。

GitHub リポジトリ情報がユーザーから提供され、かつネットワーク操作が許可された場合に可能:

- Git リポジトリ初期化または既存 repo への配置案作成。
- ブランチ作成、commit、push、PR 作成。
- ただし、現在は作業場所が Git リポジトリではなく `gh` もないため、この環境だけでは実行不可。

## ユーザー本人の外部サービス操作が必要な範囲

必須:

1. GitHub の配置先リポジトリ URL とブランチを指定する。
2. Streamlit Community Cloud にログインする。
3. 新規テストアプリを作る、または既存アプリの連携先を変更する。
4. Streamlit の実行ファイルを `app.py` に設定する。
5. Streamlit Secrets に `EDINET_API_KEY` を登録する。
6. 現行サイトを置き換えるか、別 URL で先行公開するかを決める。
7. 正式なサイト名、運営者名、問い合わせ先、プライバシーポリシー・利用規約の要否を決める。

任意だが推奨:

- 先行公開用の別 URL でテストしてから現行 URL を置き換える。
- 公開前に JPX 規則および e-Gov 法令の現行版との差分確認を行う。

## ユーザーへの最短依頼事項

公開準備を進めるため、ユーザーに依頼する最短事項は次の 4 点。

1. GitHub の配置先リポジトリ URL とブランチ名を教えてください。
2. Streamlit は「現行サイトを V2 に置き換え」か「別 URL で先行公開」かを選んでください。
3. Streamlit Community Cloud の Secrets に、本人操作で `EDINET_API_KEY` を登録してください。
4. 正式なサイト名、運営者名、問い合わせ先を確定してください。

## 結論

- ローカル成果物としては、`outputs/disclosure_support_v2_source_20260614.zip` が公開用素材として最も適している。
- ただし、この作業場所は Git リポジトリではなく、`gh` もないため、こちらだけで GitHub / Streamlit への公開完了まではできない。
- 実 API キーはローカル成果物に含めず、ユーザー本人が Streamlit Community Cloud の Secrets に登録する手順が安全。
