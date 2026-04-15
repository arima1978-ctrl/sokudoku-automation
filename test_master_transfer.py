"""マスターシート転記のドライラン検証

実行: python test_master_transfer.py
重複チェックと転記先行番号の確認のみ。実書き込みはしない。
"""

from __future__ import annotations

import argparse

import master_list_writer
from main import fetch_spreadsheet_data, get_pending_entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=str, default="202,203",
                        help="確認対象の行番号 (カンマ区切り)")
    parser.add_argument("--apply", action="store_true",
                        help="実際に書き込む (指定しないと dry-run)")
    args = parser.parse_args()

    target_rows = [int(x) for x in args.rows.split(",") if x.strip()]
    rows = fetch_spreadsheet_data()
    entries = get_pending_entries(rows, target_rows=target_rows)

    if not entries:
        print("対象行が見つかりません")
        return

    for entry in entries:
        print(f"\n=== 行 {entry['row_index']}: {entry['juku_name']} ===")
        print(f"  email:        {entry['email']}")
        print(f"  tel:          {entry['tel']}")
        print(f"  mobile:       {entry.get('mobile', '')}")
        print(f"  contact:      {entry['contact_name']}")
        print(f"  contract:     {entry['contract_type']}")
        print(f"  member_type:  {master_list_writer.map_member_type(entry['contract_type'])}")

        # 既存の塾IDは source row から拾う (col N = index 13)
        src_row = rows[entry["row_index"] - 1]
        juku_id = src_row[13].strip() if len(src_row) > 13 else ""
        print(f"  塾ID(source): {juku_id or '(未発行)'}")

        ok, msg = master_list_writer.write_entry(
            entry,
            juku_id=juku_id,
            mobile=entry.get("mobile", ""),
            dry_run=not args.apply,
        )
        status = "OK" if ok else "SKIP"
        print(f"  → [{status}] {msg}")


if __name__ == "__main__":
    main()
