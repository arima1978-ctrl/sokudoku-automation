"""クスタニ塾(101817)のパスワードを kabume55 に更新し、メール送信"""

import sys
from bs4 import BeautifulSoup

from main import (
    sokudoku_create_session, send_welcome_email,
)


def fetch_edit_form(session, juku_id: str) -> tuple[str, dict]:
    """編集ページのフォームデータを取得する。(token, form_data) を返す"""
    # 検索画面からtoken取得
    mypage = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
    soup = BeautifulSoup(mypage.text, "html.parser")
    search_form = soup.find("form", action=lambda x: x and "Search" in x)
    token = search_form.find("input", {"name": "__RequestVerificationToken"})["value"]

    # 検索実行
    search_resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Search",
        data={
            "__RequestVerificationToken": token,
            "SEARCH_CONTENT_DATA.JUKU_ID": juku_id,
            "SEARCH_CONTENT_DATA.JUKU_NM": "",
            "SEARCH_CONTENT_DATA.JUKU_STATUS_CD": "",
            "SEARCH_CONTENT_DATA.COURSE_CD": "00",
        },
    )
    search_soup = BeautifulSoup(search_resp.text, "html.parser")
    edit_form = None
    for form in search_soup.find_all("form"):
        if form.find(id="kyosituChg"):
            edit_form = form
            break
    if not edit_form:
        raise Exception(f"塾ID {juku_id} の編集フォームが見つかりません")

    edit_token = edit_form.find("input", {"name": "__RequestVerificationToken"})["value"]

    # 編集(変更)画面を開く
    henkou_resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Henkou",
        data={
            "__RequestVerificationToken": edit_token,
            "kyosituChg": "変更",
            "JUKU_ID": juku_id,
            "COURSE_CD": "00",
        },
    )
    edit_soup = BeautifulSoup(henkou_resp.text, "html.parser")
    form = edit_soup.find("form", action=lambda x: x and "UPDATE" in x)
    if not form:
        raise Exception("UPDATE フォームが見つかりません")

    new_token = form.find("input", {"name": "__RequestVerificationToken"})["value"]

    data: dict = {}
    # すべての input を辞書に(同名の場合は checked radio 優先)
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        typ = inp.get("type", "text")
        val = inp.get("value", "")
        if typ == "radio":
            if inp.has_attr("checked"):
                data[name] = val
            else:
                data.setdefault(name, data.get(name, ""))
        elif typ == "checkbox":
            # checked な場合のみ値を(通常false)
            if inp.has_attr("checked"):
                data[name] = val
            else:
                data.setdefault(name, "false")
        else:
            data[name] = val

    data["__RequestVerificationToken"] = new_token

    # 現在の詳細情報(メール送信用)
    current_info = {
        "juku_name": data.get("UPDATE_INFO.JUKU_NM", ""),
        "email": data.get("UPDATE_INFO.MAIL", ""),
        "tel": data.get("UPDATE_INFO.TEL", ""),
        "contact_name": data.get("UPDATE_INFO.TANT_NM", ""),
        "current_pass": data.get("UPDATE_INFO.PASS", ""),
    }
    return data, current_info


def update_password(session, juku_id: str, new_password: str, dry_run: bool = False) -> tuple[dict, bool]:
    data, info = fetch_edit_form(session, juku_id)

    print(f"\n現行情報:")
    print(f"  塾名: {info['juku_name']}")
    print(f"  メール: {info['email']}")
    print(f"  担当: {info['contact_name']}")
    print(f"  現行PW: {info['current_pass']}")
    print(f"  新PW(予定): {new_password}")

    # パスワード差し替え
    data["UPDATE_INFO.PASS"] = new_password

    if dry_run:
        print("\n[dry-run] 更新POST をスキップ")
        return info, False

    resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/UPDATE",
        data=data,
    )
    print(f"\n更新POST: status={resp.status_code}, url={resp.url}")

    # 成否確認: 再度編集ページを取得してPASSが新値になっているか
    data2, info2 = fetch_edit_form(session, juku_id)
    if info2["current_pass"] == new_password:
        print(f"✅ パスワード更新確認OK: {new_password}")
        return info2, True

    print(f"❌ パスワード更新失敗: 再取得したPW={info2['current_pass']}")
    with open(f"update_failed_{juku_id}.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    return info2, False


def main():
    juku_id = "101817"
    new_password = "kabume55"
    dry_run = "--dry-run" in sys.argv

    session = sokudoku_create_session()
    info, ok = update_password(session, juku_id, new_password, dry_run=dry_run)

    if not ok:
        print("\n⚠️ 更新失敗のためメールは送信しません")
        sys.exit(1)

    # メール送信
    entry = {
        "juku_name": info["juku_name"],
        "email": info["email"],
        "contact_name": info["contact_name"],
    }
    if "--no-email" in sys.argv:
        print(f"\n[--no-email] メール送信をスキップ: {entry['email']}")
        return
    print(f"\nメール送信 → {entry['email']}")
    send_welcome_email(entry, juku_id, new_password)


if __name__ == "__main__":
    main()
