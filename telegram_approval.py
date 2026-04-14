"""Telegram 承認フロー - インラインボタンで OK/NG を受け取る"""

import json
import os
import time
from typing import Optional

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, params: dict) -> dict:
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.post(url, json=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data}")
    return data


def send_approval_request(
    token: str,
    chat_id: str,
    text: str,
    row_index: int,
) -> int:
    """承認ボタン付きメッセージを送信し message_id を返す"""
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ 承認", "callback_data": f"approve:{row_index}"},
            {"text": "❌ 却下", "callback_data": f"reject:{row_index}"},
        ]]
    }
    data = _call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
    })
    return data["result"]["message_id"]


def wait_for_decision(
    token: str,
    chat_id: str,
    message_id: int,
    row_index: int,
    timeout_sec: int = 3600,
    poll_interval: int = 3,
) -> Optional[bool]:
    """承認ボタン押下を待機。True=承認, False=却下, None=タイムアウト"""
    offset = 0
    deadline = time.time() + timeout_sec
    expected_approve = f"approve:{row_index}"
    expected_reject = f"reject:{row_index}"

    while time.time() < deadline:
        params = {"timeout": 0, "allowed_updates": ["callback_query"]}
        if offset:
            params["offset"] = offset
        try:
            data = _call(token, "getUpdates", params)
        except Exception as e:
            print(f"    [telegram poll error] {e}")
            time.sleep(poll_interval)
            continue

        for update in data["result"]:
            offset = update["update_id"] + 1
            cq = update.get("callback_query")
            if not cq:
                continue
            cq_data = cq.get("data", "")
            cq_msg = cq.get("message", {})
            if cq_msg.get("message_id") != message_id:
                continue

            # 押下を即時反映(ローディング解除)
            try:
                _call(token, "answerCallbackQuery", {"callback_query_id": cq["id"]})
            except Exception:
                pass

            user = cq.get("from", {})
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

            if cq_data == expected_approve:
                _update_message(token, chat_id, message_id, cq_msg.get("text", ""), f"✅ 承認済 by {user_name}")
                return True
            if cq_data == expected_reject:
                _update_message(token, chat_id, message_id, cq_msg.get("text", ""), f"❌ 却下 by {user_name}")
                return False

        time.sleep(poll_interval)

    _update_message(token, chat_id, message_id, "", "⏱ タイムアウト")
    return None


def _update_message(token: str, chat_id: str, message_id: int, original_text: str, status: str) -> None:
    """承認後にメッセージを編集してボタンを消す"""
    new_text = (original_text + "\n\n" + status) if original_text else status
    try:
        _call(token, "editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "HTML",
        })
    except Exception:
        pass


def send_info(token: str, chat_id: str, text: str) -> None:
    """情報通知のみ(ボタンなし)"""
    try:
        _call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
    except Exception as e:
        print(f"    [telegram send_info error] {e}")
