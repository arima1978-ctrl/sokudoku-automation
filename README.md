# sokudoku-automation

100万人の速読 新規塾ID自動発行スクリプト

## 処理フロー

1. Google Spreadsheet 申込フォームからSTATUS空(O列)の申込を取得
2. anyschool.jp でスマート検索(接尾辞トリム+メール/TEL/住所照合) → 家族コード取得
3. 100mil-sokudoku で既登録チェック → 分岐
   - **未登録** → Telegram承認 → 新規登録 + メール送信
   - **既登録** → Telegram承認 → (必要なら)PW変更 + メール再送
4. STATUS列(O列)に処理結果書き戻し

## セットアップ (Linux server)

### 1. 依存パッケージ

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv chromium-browser chromium-chromedriver

cd /home/skyuser
git clone https://github.com/arima1978-ctrl/sokudoku-automation.git
cd sokudoku-automation

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 秘密情報の配置

`.env` と `credentials.json` は別途 scp で転送:
```bash
# from local
scp .env skyuser@192.168.1.16:/home/skyuser/sokudoku-automation/
scp credentials.json skyuser@192.168.1.16:/home/skyuser/sokudoku-automation/
```

### 3. 定期実行 (cron)

```bash
crontab -e
```

以下を追記:
```
0 9 * * * cd /home/skyuser/sokudoku-automation && /home/skyuser/sokudoku-automation/venv/bin/python main.py --yes >> logs/run_$(date +\%Y-\%m-\%d).log 2>&1
```

### 4. 動作テスト

```bash
source venv/bin/activate
python main.py --yes --no-telegram --no-email  # ドライラン
```

## コマンド

```bash
python main.py --yes                    # 通常実行
python main.py --rows 205,206 --yes     # 特定行のみ
python main.py --no-telegram --no-email # ドライラン
python bulk_mark_legacy.py              # 既存行の一括マーク(初回のみ)
```

## 環境変数 (.env)

```
SMTP_USER=eteacher.sky@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SENDER_EMAIL=eduplus@meidaisky.jp
SENDER_NAME=磯一郎の100万人の速読 事務局

ANYSCHOOL_ID=arima
ANYSCHOOL_PW=...

SOKUDOKU_ADMIN_ID=...
SOKUDOKU_ADMIN_PW=...

TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=-5155819670

GOOGLE_CREDENTIALS_PATH=credentials.json
```

## スプレッドシート列定義

| 列 | 内容 |
|----|------|
| A | Timestamp |
| B | メールアドレス |
| D | 塾名 |
| E | 郵便番号 |
| F | 住所 |
| G | 電話番号 |
| H | 担当者名 |
| I | 担当者携帯 |
| K | 契約種別 |
| L | 希望パスワード |
| O | STATUS (自動記入) |
