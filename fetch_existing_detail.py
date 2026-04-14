"""既存塾ID 101817 の編集ページからパスワード等を取得"""

from main import sokudoku_create_session
from bs4 import BeautifulSoup

session = sokudoku_create_session()

# 1. 検索画面を開いて token 取得
mypage = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
soup = BeautifulSoup(mypage.text, "html.parser")
search_form = soup.find("form", action=lambda x: x and "Search" in x)
token = search_form.find("input", {"name": "__RequestVerificationToken"})["value"]

# 2. 検索実行
session.post(
    "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Search",
    data={
        "__RequestVerificationToken": token,
        "SEARCH_CONTENT_DATA.JUKU_ID": "101817",
        "SEARCH_CONTENT_DATA.JUKU_NM": "",
        "SEARCH_CONTENT_DATA.JUKU_STATUS_CD": "",
        "SEARCH_CONTENT_DATA.COURSE_CD": "00",
    },
)

# 3. 変更画面を開く(検索結果行内のformを再取得してtokenを流用)
mypage2 = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
soup2 = BeautifulSoup(mypage2.text, "html.parser")
# 検索状態が維持されているかは不明なので、再度検索
search_form2 = soup2.find("form", action=lambda x: x and "Search" in x)
token2 = search_form2.find("input", {"name": "__RequestVerificationToken"})["value"]
search_resp = session.post(
    "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Search",
    data={
        "__RequestVerificationToken": token2,
        "SEARCH_CONTENT_DATA.JUKU_ID": "101817",
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
    print("編集フォーム見つからず")
    exit(1)

edit_token = edit_form.find("input", {"name": "__RequestVerificationToken"})["value"]

henkou_resp = session.post(
    "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Henkou",
    data={
        "__RequestVerificationToken": edit_token,
        "kyosituChg": "変更",
        "JUKU_ID": "101817",
        "COURSE_CD": "00",
    },
)

with open("detail_101817.html", "w", encoding="utf-8") as f:
    f.write(henkou_resp.text)
print(f"編集ページ保存: detail_101817.html ({len(henkou_resp.text)} chars)")

# 4. 主要項目を抽出
detail_soup = BeautifulSoup(henkou_resp.text, "html.parser")
fields_of_interest = [
    "R_M_JUKU.JUKU_ID",
    "R_M_JUKU.KAZOKU_ID",
    "R_M_JUKU.JUKU_NM",
    "R_M_JUKU.MAIL",
    "R_M_JUKU.TEL",
    "R_M_JUKU.TANT_NM",
    "R_M_JUKU.TDFK",
    "R_M_JUKU.JUSYO",
    "R_M_LOGIN.PASS",
    "R_M_JUKU_CK.CULTURE_KIDS_FLG",
]
for name in fields_of_interest:
    el = detail_soup.find(attrs={"name": name})
    if el:
        val = el.get("value", "") if el.name == "input" else el.get_text(strip=True)
        print(f"  {name}: {val}")
    else:
        print(f"  {name}: (not found)")

# 追加: すべてのinput要素名と値を表示(発見用)
print("\n--- 全input要素 (value非空のみ) ---")
for inp in detail_soup.find_all("input"):
    name = inp.get("name", "")
    val = inp.get("value", "")
    if val and name and "Token" not in name:
        print(f"  {name}: {val[:80]}")
