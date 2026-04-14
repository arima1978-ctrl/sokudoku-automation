"""行202/203 を Telegram 承認付きで正しくメール再送"""

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from main import (
    fetch_spreadsheet_data, get_pending_entries, send_welcome_email,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
)
import telegram_approval as tg


# 既に登録済みの情報
ROW_CONFIG = {
    202: {"juku_id": "101817", "password": "kabume55"},
    203: {"juku_id": "102878", "password": "melc26001"},
}


def build_resend_text(entry: dict, juku_id: str, password: str) -> str:
    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return "\n".join([
        f"<b>【メール再送 承認依頼】行{entry['row_index']}</b>",
        "",
        "<b>■ 送信先(スプレッドシート)</b>",
        f"宛名: {esc(entry['contact_name'])} 様",
        f"塾名: {esc(entry['juku_name'])}",
        f"メール: <code>{esc(entry['email'])}</code>",
        "",
        "<b>■ メール記載内容</b>",
        f"塾ID: <code>{esc(juku_id)}</code>",
        f"PW: <code>{esc(password)}</code>",
        f"URL: https://new.100mil-sokudoku.com/manager",
        "",
        "※DB上の塾ID登録/PW変更は既に完了済み。これはメール再送のみ",
    ])


def main():
    rows = fetch_spreadsheet_data()
    entries = get_pending_entries(rows, target_rows=list(ROW_CONFIG.keys()))
    entry_map = {e["row_index"]: e for e in entries}

    for row_idx, cfg in ROW_CONFIG.items():
        if row_idx not in entry_map:
            print(f"行{row_idx} がスプレッドシートにありません")
            continue

        entry = entry_map[row_idx]
        juku_id = cfg["juku_id"]
        password = cfg["password"]

        print(f"\n=== 行{row_idx} {entry['juku_name']} ===")
        print(f"  宛名: {entry['contact_name']}")
        print(f"  メール: {entry['email']}")
        print(f"  塾ID: {juku_id}")
        print(f"  PW: {password}")

        # Telegram承認
        text = build_resend_text(entry, juku_id, password)
        msg_id = tg.send_approval_request(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, text, row_idx)
        print(f"  Telegram承認待ち...")
        decision = tg.wait_for_decision(
            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg_id, row_idx, timeout_sec=3600,
        )
        if decision is None:
            print("  タイムアウト - スキップ")
            continue
        if not decision:
            print("  却下 - スキップ")
            continue

        # メール送信
        try:
            send_welcome_email(entry, juku_id, password)
            tg.send_info(
                TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                f"📧 行{row_idx}: <b>{entry['juku_name']}</b> メール再送完了\n宛名: {entry['contact_name']} 様\n塾ID: <code>{juku_id}</code>",
            )
        except Exception as e:
            print(f"  送信失敗: {e}")
            tg.send_info(
                TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                f"❌ 行{row_idx} メール送信失敗: {e}",
            )


if __name__ == "__main__":
    main()
