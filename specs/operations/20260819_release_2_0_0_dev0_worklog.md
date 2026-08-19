# 2.0.0.dev0 開発検証用 prerelease worklog（2026-08-19）

## 対象

- repository: `miyamamoto/jrvltsql`
- worktree: `/home/keiba/scratch/20260819_jrvltsql_release_dev0`
- branch: `agent/release-2.0.0.dev0-20260819`
- frozen base / 検証対象 SHA: `f812ffea45aef2f448d744624c186bbece1685a8`
  （O1-O6 無損失 storage PR #227 の merge commit、短縮 `f812ffe`）
- package version: `pyproject.toml` の `version = "2.0.0.dev0"`（既存値、変更なし）

直列順の最終段。前段までの公式契約イテレーション（HN #217 / docs #218 #219 /
native `NL_UM` #220 / SK #221 / JG・RC・WC #222 / UM #223 / H1 #224 / H6 #225 /
O1-O6 parser #226 / O1-O6 storage #227）はすべて merge 済み・CI green である。

## STOP 条件

- 検証対象 SHA と異なる commit を含めて成果物を作る必要が出たとき
- ゲートが green にならない状態が3回の修正で解消しないとき
- 実 provider（JV-Link）取得、本番 DB、frozen 研究 DB への操作が必要になったとき
- prerelease tag / GitHub release の作成（release state の変更）にユーザー承認が
  得られていないとき
- `2.0.0` 本リリースの判断が必要になったとき（この段の範囲外）

## 実施したこと

1. `origin/master`（`f812ffe`）から専用 worktree を作成し、依存を `uv sync
   --frozen --all-extras --dev` で凍結インストールした。
2. 必須ゲートを再実行した。
   - `uv lock --check`: pass（50 packages resolved）
   - `scripts/validate_test_gate.py`: `TEST GATE PASS`
   - `flake8 --isolated --select=E9,F63,F7,F82 src tests scripts tools`: pass
   - `git diff --check`: pass
3. フルスイートを SQLite と実 PostgreSQL 16（使い捨て container
   `jltsql-sk-pg16-8215`）で実行: **5013 passed, 41 skipped, 23 subtests passed**。
4. 同じ SHA から成果物を build した。
   - `jltsql-2.0.0.dev0-py3-none-any.whl`
   - `jltsql-2.0.0.dev0.tar.gz`
5. 隔離した仮想環境に wheel だけを install して smoke を実施した（sdist は
   build のみで、install 検証はしていない）。
   - `jltsql --version` → `jltsql, version 2.0.0.dev0`
   - `jltsql init` → 作業ディレクトリに `config/config.yaml`（SQLite-only）を作成
   - `SchemaManager.create_all_tables()` → 80/80 テーブル作成
   - 公式固定長 O2（2,042 バイト）を parse → import し、
     `filled=3` の次に `filled=2` を取り込むと組合せが `0102`/`0103` だけになる
     （完全 snapshot 置換）ことと、`------` / `******` / `000000` が
     そのまま保存されることを確認した。

## 事実として記録する制約

- 実 provider（JV-Link）からの取得・provider 順序の検証は行っていない。
- 64-bit SDK 実行経路は未検証のままである。
- 1.x の既存 DB の移行は検証していない。列型と key が変わるため rebuild と
  reimport が必要である。
- したがって `2.0.0.dev0` は開発検証用 prerelease であり、本番互換性や
  取得可用性の主張ではない。RELEASE_NOTES.md 冒頭にこの範囲を明記した。

## 未実施（承認待ち）

- prerelease tag `v2.0.0.dev0` の作成と GitHub prerelease の publish。
  release state を変えるため、ユーザー承認を得てから実施する。
- 実開発環境での install、実 JV-Link 取得・保存確認、`2.0.0` 本リリース判断。
