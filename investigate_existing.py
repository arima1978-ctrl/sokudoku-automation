"""既存塾ID 101817 の詳細情報を取得"""

from main import sokudoku_create_session, SOKUDOKU_URL
from bs4 import BeautifulSoup

session = sokudoku_create_session()

# 1. 検索
mypage = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
soup = BeautifulSoup(mypage.text, "html.parser")
search_form = soup.find("form", action=lambda x: x and "Search" in x)
token = search_form.find("input", {"name": "__RequestVerificationToken"})["value"]

resp = session.post(
    "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Search",
    data={
        "__RequestVerificationToken": token,
        "SEARCH_CONTENT_DATA.JUKU_ID": "101817",
        "SEARCH_CONTENT_DATA.JUKU_NM": "",
        "SEARCH_CONTENT_DATA.JUKU_STATUS_CD": "",
        "SEARCH_CONTENT_DATA.COURSE_CD": "00",
    },
)

with open("search_101817.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print(f"検索結果保存: search_101817.html ({len(resp.text)} chars)")

# 2. 詳細ページへのリンクを探す
resp_soup = BeautifulSoup(resp.text, "html.parser")

# 101817を含む行から詳細リンクを探索
for tr in resp_soup.find_all("tr"):
    tds = tr.find_all("td")
    tds_text = [td.get_text(strip=True) for td in tds]
    if "101817" in tds_text:
        print(f"\n該当行発見: {tds_text}")
        for a in tr.find_all("a"):
            href = a.get("href", "")
            print(f"  link: text='{a.get_text(strip=True)}' href='{href}'")
        for inp in tr.find_all("input"):
            print(f"  input: {inp}")
        for btn in tr.find_all("button"):
            print(f"  button: {btn}")
        break
