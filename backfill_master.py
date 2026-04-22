"""マスターシート転記漏れ行の遡及転記

2026-04-20 の commit b65ada5 で _transfer_to_master の呼び出しが誤削除され、
4/20 〜 本日 に新規発行したレコードがマスターシートに転記されなかった。
このスクリプトは STATUS 列 (`YYYY/MM/DD 新規登録 ID:xxxxx`) を解析して
master_list_writer.write_entry() を直接呼び出し、遡及的に転記する。

使い方 (192.168.1.16 上で実行):

    cd /home/skyuser/sokudoku-automation
    source venv/bin/activate
    python backfill_master.py --rows 204,205 --dry-run   # 確認
    python backfill_master.py --rows 204,205             # 本実行
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

import main as sokudoku_main
import master_list_writer

load_dotenv(Path(__file__).parent / ".env", override=True)

STATUS_PATTERN = re.compile(
    r"(?P<date>\d{4}/\d{1,2}/\d{1,2})\s*新規登録\s*ID[:：]\s*(?P<juku_id>\S+)"
)


def parse_status(status: str) -> tuple[str, str] | None:
    """STATUS 列文字列から (issue_date, juku_id) を抽出。マッチしなければ None"""
    m = STATUS_PATTERN.search(status or "")
    if not m:
        return None
    return m.group("date"), m.group("juku_id")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="マスターシート遡及転記")
    parser.add_argument(
        "--rows",
        required=True,
        help="対象行のカンマ区切り (例: 204,205)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実書き込みせず、転記予定の内容だけ表示",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_rows = [int(x.strip()) for x in args.rows.split(",") if x.strip()]

    print("=" * 60)
    print("マスターシート遡及転記")
    print(f"対象行: {target_rows}")
    print(f"dry-run: {args.dry_run}")
    print("=" * 60)

    rows = sokudoku_main.fetch_spreadsheet_data()

    success = 0
    skipped = 0
    failed = 0

    for row_idx in target_rows:
        print(f"\n--- 行 {row_idx} ---")
        if row_idx < 2 or row_idx > len(rows):
            print(f"  範囲外 (シート行数={len(rows)})")
            failed += 1
            continue

        raw = rows[row_idx - 1]
        if not raw or len(raw) <= sokudoku_main.COL_STATUS:
            print("  行データ不足")
            failed += 1
            continue

        status = raw[sokudoku_main.COL_STATUS].strip()
        parsed = parse_status(status)
        if not parsed:
            print(f"  STATUS 解析失敗: {status!r}")
            failed += 1
            continue

        issue_date, juku_id = parsed

        address = raw[sokudoku_main.COL_ADDRESS].strip()
        contract = (
            raw[sokudoku_main.COL_CONTRACT_TYPE].strip()
            if len(raw) > sokudoku_main.COL_CONTRACT_TYPE
            else ""
        )
        mobile = (
            raw[sokudoku_main.COL_CONTACT_MOBILE].strip()
            if len(raw) > sokudoku_main.COL_CONTACT_MOBILE
            else ""
        )

        entry = {
            "row_index": row_idx,
            "email": raw[sokudoku_main.COL_EMAIL].strip(),
            "juku_name": raw[sokudoku_main.COL_JUKU_NAME].strip(),
            "address": address,
            "tel": raw[sokudoku_main.COL_TEL].strip(),
            "contact_name": raw[sokudoku_main.COL_CONTACT_NAME].strip(),
            "contract_type": contract,
        }

        print(f"  塾名     : {entry['juku_name']}")
        print(f"  email    : {entry['email']}")
        print(f"  TEL      : {entry['tel']}")
        print(f"  契約     : {entry['contract_type']}")
        print(f"  juku_id  : {juku_id}")
        print(f"  発行日   : {issue_date}")

        ok, msg = master_list_writer.write_entry(
            entry,
            juku_id,
            mobile=mobile,
            issue_date=issue_date,
            dry_run=args.dry_run,
        )
        print(f"  結果     : {'OK' if ok else 'SKIP/FAIL'} - {msg}")
        if ok:
            success += 1
        elif "スキップ" in msg or "既存行" in msg:
            skipped += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"成功: {success}  スキップ: {skipped}  失敗: {failed}")
    print("=" * 60)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
