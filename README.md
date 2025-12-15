# Mood App

日々の気分や「よかったこと」を記録するシンプルなWebアプリです。
Flask と SQLite を使って作成しました。
## 機能
- 気分の記録（点数・天気・よかったこと）
- 記録一覧のカード表示
- 記録の編集・削除（確認付き）
- スマホ対応（レスポンシブデザイン）
## 使用技術
- Python 3
- Flask
- SQLite
- HTML / CSS
## セットアップ方法

```bash
git clone https://github.com/ユーザー名/mood_app.git
cd mood_app
python -m venv venv
source venv/bin/activate  # Windowsは venv\Scripts\activate
pip install flask
python app.py
## 今後の改善予定
- ユーザー登録・ログイン機能の追加
- グラフによる気分の可視化
- デザインテーマ切り替え
