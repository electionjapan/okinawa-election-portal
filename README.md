# 沖縄県知事選 開票マップ【実寸版】

沖縄県41市町村を、離島をインセット配置せず、島々の実際の位置関係に近い形で表示する独立Streamlitサイトです。

## 基準バージョン

速報ロジックはユーザー提供の **沖縄選挙ポータル v0.9.35** を基準にしています。既存ポータル本体とは別サイトです。

v0.9.35から引き継いだ主な仕様：

- 全県開票率は市町村別 `reporting_pct` の投票者数加重平均
- 開票率100%相当の自治体は残票0
- 最終投票者数に期日前票を二重加算しない
- 中間投票速報は当日票＋期日前票で投票者数を計算
- 「国盗り」モードは勝差に関係なく保守系＝赤、オール沖縄系＝青

## 表示モード

- 得票シェア
- 国盗り
- リード票
- 残票

クイックズームは座標を動かさず、カメラ範囲だけを変更します。

## データ元

Google Sheet ID：

`1s6H3je6DPCSNIzwcOQpA39t_ecISuuAjY4qT2a291is`

既存ポータルと同じ公開Googleスプレッドシートを読み取り専用で参照します。書き込み処理はありません。

## 地図データ

`data/okinawa_municipalities_real_distance_approx_v2.geojson`

- 41市町村
- `municipality_code` で速報データとJOIN
- CRS84（経度・緯度）
- 与那国～大東まで同じ地図キャンバスに表示
- 離島インセットなし

このGeoJSONは既存ポータルのWeb簡略形状を実位置に再配置した**実距離配置近似版**です。法的・測量的に厳密な行政界ではありません。将来は国土数値情報N03のgeometryへ差し替え可能です。

## GitHubへアップするもの

このZIPを展開したフォルダ内のファイルを、新しいGitHubリポジトリのルートへアップしてください。

主要ファイル：

- `app.py`
- `live_data.py`
- `map_view.py`
- `requirements.txt`
- `.streamlit/config.toml`
- `data/`

## Streamlit Community Cloud

Main file path：

`app.py`

追加のSecretsは不要です（公開Google SheetをGViz CSVで読みます）。

## ローカル起動

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 注意

既存の `okinawa-election-portal` リポジトリへ上書きしないでください。実寸版は**別リポジトリ・別URL**で運用する前提です。
