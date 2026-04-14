"""行202/203 は既にDB登録済み。メール送信だけ行う"""

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from main import send_welcome_email
import telegram_approval as tg
from main import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


# 行202 クスタニ塾
entry_202 = {
    "juku_name": "クスタニ塾",
    "email": "taishojuku@mist.ocn.ne.jp",
    "contact_name": "中村 博司",
}
juku_id_202 = "101817"
pw_202 = "kabume55"

# 行203 メルク英語教室
entry_203 = {
    "juku_name": "メルク英語教室",
    "email": "info@melc-eigo.com",
    "contact_name": "堀英雄",
}
juku_id_203 = "102878"
pw_203 = "melc26001"

print("=== 行202 クスタニ塾 メール送信 ===")
send_welcome_email(entry_202, juku_id_202, pw_202)
tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
             f"✉️ 行202: <b>{entry_202['juku_name']}</b> PW変更+メール送信完了\n塾ID: <code>{juku_id_202}</code>\nPW: <code>{pw_202}</code>")

print("\n=== 行203 メルク英語教室 メール送信 ===")
send_welcome_email(entry_203, juku_id_203, pw_203)
tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
             f"✉️ 行203: <b>{entry_203['juku_name']}</b> 登録+メール送信完了\n塾ID: <code>{juku_id_203}</code>\nPW: <code>{pw_203}</code>")

print("\n完了")
