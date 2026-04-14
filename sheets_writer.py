"""Google Sheets STATUS列書き戻し用ユーティリティ"""

import os
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_client = None


def _get_client() -> gspread.Client | None:
    global _client
    if _client is not None:
        return _client

    cred_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    cred_file = Path(cred_path)
    if not cred_file.is_absolute():
        cred_file = Path(__file__).parent / cred_path

    if not cred_file.exists():
        return None

    creds = Credentials.from_service_account_file(str(cred_file), scopes=SCOPES)
    _client = gspread.authorize(creds)
    return _client


def update_status(
    spreadsheet_id: str,
    sheet_gid: str,
    row_index: int,
    status: str,
    col_status: int = 15,  # 1-indexed: O列=15 (COL_STATUS=14 の1-indexed)
) -> bool:
    """指定行のSTATUS列を更新。sheet_gid は数値。成功したらTrue"""
    client = _get_client()
    if client is None:
        print(f"    [sheets] 認証情報なし ({os.environ.get('GOOGLE_CREDENTIALS_PATH', 'credentials.json')} 未配置)")
        return False

    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        target_sheet = None
        for ws in spreadsheet.worksheets():
            if str(ws.id) == str(sheet_gid):
                target_sheet = ws
                break
        if target_sheet is None:
            print(f"    [sheets] gid={sheet_gid} のシートが見つかりません")
            return False

        target_sheet.update_cell(row_index, col_status, status)
        return True
    except Exception as e:
        print(f"    [sheets] 更新エラー: {e}")
        return False


def make_status_message(mode: str, juku_id: str) -> str:
    """STATUS列に書き込む文言"""
    today = datetime.now().strftime("%Y/%m/%d")
    mode_label = {
        "registered": "新規登録",
        "updated": "PW変更",
        "resent": "メール再送",
    }.get(mode, mode)
    return f"{today} {mode_label} ID:{juku_id}"
