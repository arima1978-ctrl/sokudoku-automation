"""スプレッドシートの既存データにO列マーク:
- 行2-203: フォーム経由の旧申込 → 「旧データ(自動化前)」
- 行204以降(手入力分): timestamp列に何か入っていれば 「手入力(処理対象外)」
これで明日以降の自動実行は O列が空の新規申込のみを対象にする。
"""

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from main import fetch_spreadsheet_data, SPREADSHEET_ID, SHEET_GID, COL_STATUS
import sheets_writer

FORM_BOUNDARY_ROW = 203  # この行までがフォーム送信分(行2〜203)
LEGACY_MARK = "2026/04/14 旧データ(自動化前)"
MANUAL_MARK = "2026/04/14 手入力(処理対象外)"


def main():
    rows = fetch_spreadsheet_data()
    print(f"total rows: {len(rows)}")

    client = sheets_writer._get_client()
    if client is None:
        print("❌ GCP認証情報なし (credentials.json 未配置)")
        sys.exit(1)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    target_sheet = None
    for ws in spreadsheet.worksheets():
        if str(ws.id) == str(SHEET_GID):
            target_sheet = ws
            break
    if target_sheet is None:
        print(f"❌ シート gid={SHEET_GID} が見つかりません")
        sys.exit(1)

    legacy_rows: list[int] = []
    manual_rows: list[int] = []

    for i, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        status = row[COL_STATUS].strip() if len(row) > COL_STATUS else ""
        if status:
            continue  # 既に印あり

        # 何らかのデータがある行(塾名 or timestamp)を対象
        has_data = False
        for col_idx in (0, 1, 3):  # timestamp, email, juku_name
            if len(row) > col_idx and row[col_idx].strip():
                has_data = True
                break
        if not has_data:
            continue

        if i <= FORM_BOUNDARY_ROW:
            legacy_rows.append(i)
        else:
            manual_rows.append(i)

    print(f"\nマーク対象:")
    print(f"  行2〜{FORM_BOUNDARY_ROW} (旧データ): {len(legacy_rows)} 件")
    print(f"  行{FORM_BOUNDARY_ROW + 1}〜 (手入力): {len(manual_rows)} 件")

    total = len(legacy_rows) + len(manual_rows)
    if total == 0:
        print("対象ゼロ。処理不要")
        return

    confirm = input(f"\n合計 {total} 行に O列を記入します。よろしいですか? (y/N): ")
    if confirm.lower() != "y":
        print("キャンセルしました")
        return

    col_letter = "O"  # COL_STATUS=14 の 1-indexed = 15 = O列
    updates = []
    for r in legacy_rows:
        updates.append({"range": f"{col_letter}{r}", "values": [[LEGACY_MARK]]})
    for r in manual_rows:
        updates.append({"range": f"{col_letter}{r}", "values": [[MANUAL_MARK]]})

    # バッチ更新(100件ずつ)
    BATCH = 100
    for i in range(0, len(updates), BATCH):
        chunk = updates[i: i + BATCH]
        target_sheet.batch_update(chunk)
        print(f"  {i + len(chunk)}/{len(updates)} 更新完了")

    print(f"\n✅ 完了: 旧データ {len(legacy_rows)} 件 + 手入力 {len(manual_rows)} 件 = {total} 件にO列マーク")
    print(f"今後の自動実行は O列が空の新規申込のみを対象にします")


if __name__ == "__main__":
    main()
