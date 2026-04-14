"""行202/203 の特殊対応:
行202: 既登録クスタニ塾(101817) のPW変更 + メール送信 (Telegram承認付き)
行203: メルク英語教室 を家族コード102878で新規登録 + メール送信 (Telegram承認付き)
"""

import sys

import main as m
import telegram_approval as tg
from update_password import fetch_edit_form
from main import (
    fetch_spreadsheet_data, get_pending_entries,
    sokudoku_create_session, sokudoku_search_juku,
    sokudoku_register_juku, send_welcome_email,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
)


def build_update_approval_text(entry: dict, juku_id: str, current_info: dict, new_password: str) -> str:
    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return "\n".join([
        f"<b>【承認依頼】行{entry['row_index']} (既登録/PW変更)</b>",
        "",
        "<b>■ 既存塾情報 (100mil-sokudoku)</b>",
        f"塾ID: <code>{esc(juku_id)}</code>",
        f"塾名: {esc(current_info['juku_name'])}",
        f"メール: {esc(current_info['email'])}",
        f"TEL: {esc(current_info['tel'])}",
        f"担当: {esc(current_info['contact_name'])}",
        f"現行PW: <code>{esc(current_info['current_pass'])}</code>",
        "",
        "<b>■ 申込内容 (スプレッドシート)</b>",
        f"塾名: {esc(entry['juku_name'])}",
        f"メール: {esc(entry['email'])}",
        f"TEL: {esc(entry['tel'])}",
        f"担当: {esc(entry['contact_name'])}",
        "",
        "<b>■ 実行内容</b>",
        f"パスワードを <code>{esc(current_info['current_pass'])}</code> → <code>{esc(new_password)}</code> に変更",
        f"その後 {esc(current_info['email'])} にご案内メール送信",
    ])


def build_register_approval_text(entry: dict, juku_id: str) -> str:
    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    password = entry["desired_password"]
    return "\n".join([
        f"<b>【承認依頼】行{entry['row_index']} (新規登録)</b>",
        "",
        "<b>■ 申込内容</b>",
        f"塾名: {esc(entry['juku_name'])}",
        f"メール: {esc(entry['email'])}",
        f"TEL: {esc(entry['tel'])}",
        f"住所: {esc(entry['address'])}",
        f"担当: {esc(entry['contact_name'])}",
        f"契約: {esc(entry['contract_type'])}",
        "",
        "<b>■ 登録予定</b>",
        f"塾ID(家族コード): <code>{esc(juku_id)}</code> (手動指定)",
        f"PW: <code>{esc(password)}</code>",
        f"→ 承認後 {esc(entry['email'])} にメール送信",
    ])


def handle_row_202(session, entry: dict) -> bool:
    juku_id = "101817"
    new_password = entry["desired_password"] or "kabume55"

    # 編集フォーム取得(現行情報の表示用)
    data, current_info = fetch_edit_form(session, juku_id)

    # Telegram承認
    text = build_update_approval_text(entry, juku_id, current_info, new_password)
    msg_id = tg.send_approval_request(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, text, entry["row_index"])
    print(f"  Telegram承認待ち (行{entry['row_index']})...")
    decision = tg.wait_for_decision(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg_id, entry["row_index"], timeout_sec=3600)
    if decision is None:
        print("  タイムアウト - スキップ")
        return False
    if not decision:
        print("  却下 - スキップ")
        return False

    # PW更新
    data["UPDATE_INFO.PASS"] = new_password
    resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/UPDATE",
        data=data,
    )
    print(f"  更新POST: status={resp.status_code}")

    # 更新確認
    _, after = fetch_edit_form(session, juku_id)
    if after["current_pass"] != new_password:
        print(f"  ❌ PW更新失敗: 再取得={after['current_pass']}")
        tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                     f"❌ 行{entry['row_index']} PW更新失敗")
        return False
    print(f"  ✅ PW更新OK: {new_password}")

    # メール送信
    mail_entry = {
        "juku_name": after["juku_name"],
        "email": after["email"],
        "contact_name": after["contact_name"],
    }
    send_welcome_email(mail_entry, juku_id, new_password)
    tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                 f"✉️ 行{entry['row_index']}: <b>{after['juku_name']}</b> PW変更+メール送信完了\n塾ID: <code>{juku_id}</code>\nPW: <code>{new_password}</code>")
    return True


def handle_row_203(session, entry: dict) -> bool:
    juku_id = "102878"  # anyschool家族コード (手動指定)
    password = entry["desired_password"] or "melc26001"

    if sokudoku_search_juku(session, juku_id):
        print(f"  SKIP: 塾ID {juku_id} は既に登録済み")
        tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                     f"⏭ 行{entry['row_index']}: 塾ID {juku_id} は既に登録済み")
        return False

    # Telegram承認
    text = build_register_approval_text(entry, juku_id)
    msg_id = tg.send_approval_request(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, text, entry["row_index"])
    print(f"  Telegram承認待ち (行{entry['row_index']})...")
    decision = tg.wait_for_decision(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, msg_id, entry["row_index"], timeout_sec=3600)
    if decision is None:
        print("  タイムアウト - スキップ")
        return False
    if not decision:
        print("  却下 - スキップ")
        return False

    # 登録
    sokudoku_register_juku(session, entry, juku_id, password)

    if sokudoku_search_juku(session, juku_id):
        print(f"  ✅ 登録確認OK: {juku_id}")
    else:
        print(f"  ⚠️ 登録後の確認失敗")

    # メール送信
    send_welcome_email(entry, juku_id, password)
    tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                 f"✉️ 行{entry['row_index']}: <b>{entry['juku_name']}</b> 登録+メール送信完了\n塾ID: <code>{juku_id}</code>\nPW: <code>{password}</code>")
    return True


def main():
    rows = fetch_spreadsheet_data()
    entries = get_pending_entries(rows, target_rows=[202, 203])
    entry_map = {e["row_index"]: e for e in entries}

    session = sokudoku_create_session()

    if 202 in entry_map:
        print("\n=== 行202 クスタニ塾 (PW変更+メール) ===")
        try:
            handle_row_202(session, entry_map[202])
        except Exception as e:
            print(f"  ERROR: {e}")
            tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                         f"❌ 行202 エラー: {e}")

    if 203 in entry_map:
        print("\n=== 行203 メルク英語教室 (新規登録) ===")
        try:
            handle_row_203(session, entry_map[203])
        except Exception as e:
            print(f"  ERROR: {e}")
            tg.send_info(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                         f"❌ 行203 エラー: {e}")


if __name__ == "__main__":
    main()
