# 沖縄選挙ポータル v0.9

トップページから2つのページへ移動する統合版です。

## トップページ
- 開票速報を見る
- 過去の選挙結果を見る

各ページ上部の「← トップへ」で入口へ戻れます。

## 開票速報
v0.7 を統合。
- 全県集計
- 得票シェア / リード票 / 推定残票
- 本島・周辺離島 / 宮古・八重山 / 大東
- 市町村一覧
- 過去選挙との保革マージン変化

## 過去の選挙結果
v0.8.1 系のStreamlit画面を統合。
- 表示する選挙を切替
- 全県候補者集計
- 市町村別結果地図
- リード票
- 投票率（収録選挙のみ）
- 市町村一覧
- 比較対象の選挙を独立選択して保革マージン比較

## 起動
```bash
pip install -r requirements.txt
streamlit run app.py
```


## v0.9.2 完全統合版

このZIPは、以下をすべて1つにまとめた配布用パッケージです。

### Streamlit本体
- app.py
- live_results.py
- historical_results.py
- requirements.txt
- data/
- run_portal.bat

### HTML確認サイト
- preview_site/index.html
- preview_site/live.html
- preview_site/history.html
- preview_site/README.txt

HTMLだけ確認する場合は `preview_site/index.html` を開いてください。
Streamlitで動かす場合はルートの `app.py` を起動してください。
