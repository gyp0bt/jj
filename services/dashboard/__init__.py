"""ダッシュボード UI 層（Streamlit）

データ層は `services.graph.query.GraphQuery` に統合済み。本パッケージは UI のみ:
- `widgets`: `try_render_aggrid`（streamlit / streamlit-aggrid 依存、遅延import）
- `app/`: `streamlit run services/dashboard/app/Home.py` で起動するページ群

UI依存（streamlit, plotly, streamlit-aggrid, pandas）は optional-dependencies の
`dashboard` グループに分離されている。

[READMEへ戻る](../../README.md)
"""
