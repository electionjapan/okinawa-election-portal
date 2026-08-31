# 沖縄選挙ポータル v0.9.7 — GitHubアップロード用

このフォルダは Streamlit Community Cloud 用の最小構成です。

## 更新方法
1. このフォルダの中身をすべて選択
2. GitHub の `electionjapan/okinawa-election-portal` で **Add file → Upload files**
3. 同名ファイルは上書きされます
4. Commit changes
5. Streamlit Community Cloud の再読み込みを待つ

## 反映確認
トップページ上部に **v0.9.7 · NEW MAP** と出れば新版です。
開票速報・過去の選挙結果にも **v0.9.7 · NEW MAP · 模式配置** と表示されます。

## 地図について
アプリが読む表示用地図は `data/map_layout_v097.geojson` だけです。
旧レイアウトGeoJSONはこの配布物に含めていません。
`st.cache_data` もデータ読込から外し、旧地図キャッシュを避けています。
