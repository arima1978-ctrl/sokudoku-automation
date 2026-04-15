"""マスターシート (速読 問い合わせリスト) への転記ユーティリティ

転記元: フォーム回答シート (SPREADSHEET_ID=1jamO6...)
転記先: マスター (TARGET_SPREADSHEET_ID=1qVt7h..., シート名=速読 問い合わせリスト)

重複判定: メールアドレス (完全一致, 大文字小文字無視)
重複時: スキップ + ログ
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TARGET_SPREADSHEET_ID = "1qVt7hlBdPwFUdy9os9H6gr8vD5qCNU3i4OzhU_re5DI"
TARGET_SHEET_NAME = "速読　問い合わせリスト"

# 転記先の列 (1-indexed, setCell 用)
COL_NO = 1
COL_JUKU_ID = 4
COL_JUKU_NAME = 5
COL_AGENT = 6
COL_CONTACT_NAME = 8
COL_MEMBER_TYPE = 11
COL_STATUS = 12
COL_PHONE = 22
COL_ADDRESS = 23
COL_EMAIL = 24

AGENT_NAME = "名大SKY"
DEFAULT_STATUS = "体験"

_client: gspread.Client | None = None


def _get_client() -> gspread.Client | None:
    global _client
    if _client is not None:
        return _client

    cred_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    cred_file = Path(cred_path)
    if not cred_file.is_absolute():
        cred_file = Path(__file__).parent / cred_path

    if not cred_file.exists():
        logger.warning("認証情報なし: %s", cred_file)
        return None

    creds = Credentials.from_service_account_file(str(cred_file), scopes=SCOPES)
    _client = gspread.authorize(creds)
    return _client


def map_member_type(contract_str: str) -> str:
    """フォームの契約種別 → マスター会員種別"""
    if not contract_str:
        return ""
    edu = "エデュプラス" in contract_str
    ck = "カルチャーキッズ" in contract_str
    if edu and ck:
        return "eduplus・カルチャーキッズユーザー"
    if edu:
        return "eduplusユーザー"
    if ck:
        return "カルチャーキッズ・プログラミングユーザー"
    return "左記以外"


def _find_duplicate_row(worksheet: gspread.Worksheet, email: str) -> int:
    """メール一致の既存行を探す (1-indexed 行番号、なければ 0)"""
    if not email:
        return 0
    target = email.strip().lower()
    emails = worksheet.col_values(COL_EMAIL)
    for idx, val in enumerate(emails, start=1):
        if idx == 1:
            continue
        if val and val.strip().lower() == target:
            return idx
    return 0


def _find_next_empty_data_row(worksheet: gspread.Worksheet) -> int:
    """NO列に番号はあるが塾名が空の最初の行。なければ最終行+1"""
    no_col = worksheet.col_values(COL_NO)
    name_col = worksheet.col_values(COL_JUKU_NAME)
    for idx in range(2, len(no_col) + 1):
        no_val = no_col[idx - 1] if idx - 1 < len(no_col) else ""
        name_val = name_col[idx - 1] if idx - 1 < len(name_col) else ""
        if no_val.strip() and not (name_val or "").strip():
            return idx
    return max(len(no_col), len(name_col)) + 1


def write_entry(
    entry: dict,
    juku_id: str,
    mobile: str = "",
    dry_run: bool = False,
) -> tuple[bool, str]:
    """エントリをマスターに転記。重複時はスキップ。

    Returns:
        (transferred, message): 転記した場合 True / スキップは False
    """
    client = _get_client()
    if client is None:
        return False, "認証情報なし"

    try:
        ss = client.open_by_key(TARGET_SPREADSHEET_ID)
        ws = ss.worksheet(TARGET_SHEET_NAME)
    except Exception as e:
        return False, f"シート取得失敗: {e}"

    email = (entry.get("email") or "").strip()
    dup_row = _find_duplicate_row(ws, email)
    if dup_row:
        msg = f"既存行 {dup_row} にメール一致 ({email}) のためスキップ"
        logger.info(msg)
        return False, msg

    phone_parts = [
        (entry.get("tel") or "").strip(),
        (mobile or "").strip(),
    ]
    phone = "\n".join(p for p in phone_parts if p)

    target_row = _find_next_empty_data_row(ws)

    updates = [
        (COL_JUKU_ID, juku_id or ""),
        (COL_JUKU_NAME, entry.get("juku_name", "")),
        (COL_AGENT, AGENT_NAME),
        (COL_CONTACT_NAME, entry.get("contact_name", "")),
        (COL_MEMBER_TYPE, map_member_type(entry.get("contract_type", ""))),
        (COL_STATUS, DEFAULT_STATUS),
        (COL_PHONE, phone),
        (COL_ADDRESS, entry.get("address", "")),
        (COL_EMAIL, email),
    ]

    if dry_run:
        logger.info("[dry-run] target row %d updates: %s", target_row, updates)
        return True, f"[dry-run] 行 {target_row} に転記予定"

    try:
        batch = [
            {
                "range": gspread.utils.rowcol_to_a1(target_row, col),
                "values": [[val]],
            }
            for col, val in updates
        ]
        ws.batch_update(batch, value_input_option="USER_ENTERED")
        msg = f"行 {target_row} に転記完了 (juku_id={juku_id})"
        logger.info(msg)
        return True, msg
    except Exception as e:
        return False, f"書き込み失敗: {e}"


def update_juku_id(email: str, juku_id: str) -> tuple[bool, str]:
    """既存行の 塾ID 列だけを更新 (フォーム時点で転記 → 後で塾ID発行時に反映)"""
    client = _get_client()
    if client is None:
        return False, "認証情報なし"

    try:
        ss = client.open_by_key(TARGET_SPREADSHEET_ID)
        ws = ss.worksheet(TARGET_SHEET_NAME)
    except Exception as e:
        return False, f"シート取得失敗: {e}"

    row = _find_duplicate_row(ws, email)
    if not row:
        return False, f"行が見つかりません (email={email})"

    try:
        ws.update_cell(row, COL_JUKU_ID, juku_id)
        return True, f"行 {row} の塾ID を {juku_id} に更新"
    except Exception as e:
        return False, f"更新失敗: {e}"
