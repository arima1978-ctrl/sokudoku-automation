"""anyschool.jp の検索フォーム仕様を調べる調査スクリプト

目的:
  1. ユーザー一覧 (moveToUserList) 画面の全検索フィールドを列挙
  2. 学校名検索が前方一致 / 部分一致 / 完全一致のどれか確認
  3. TEL / メール / 住所 用の検索フィールドが存在するか確認
"""
import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def main() -> None:
    load_dotenv()
    url = "https://www.anyschool.jp/rakuraku_eduplus/k/menu.aspx?dummy=3229295875"
    lid = os.environ["ANYSCHOOL_ID"]
    lpw = os.environ["ANYSCHOOL_PW"]

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)

    try:
        # --- login ---
        driver.get(url)
        time.sleep(3)
        if "login" in driver.current_url.lower():
            driver.find_element(By.ID, "txtLoginName").send_keys(lid)
            driver.find_element(By.ID, "txtPassword").send_keys(lpw)
            driver.find_element(By.ID, "btnLogin").click()
            time.sleep(3)
        print(f"[login] current_url = {driver.current_url}")

        # --- move to user list ---
        driver.execute_script("moveToUserList();")
        time.sleep(5)
        print(f"[moveToUserList] current_url = {driver.current_url}")

        # --- enumerate all search form inputs ---
        print("\n=== 検索フォームの全 input ===")
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid = inp.get_attribute("id") or ""
            name = inp.get_attribute("name") or ""
            typ = inp.get_attribute("type") or ""
            val = inp.get_attribute("value") or ""
            ph = inp.get_attribute("placeholder") or ""
            if iid or name:
                print(f"  id={iid!r} name={name!r} type={typ!r} value={val!r} placeholder={ph!r}")

        # --- enumerate labels (th, label) near search form ---
        print("\n=== ラベル候補 (th / label) ===")
        seen = set()
        for lab in driver.find_elements(By.TAG_NAME, "th") + driver.find_elements(By.TAG_NAME, "label"):
            txt = lab.text.strip()
            if txt and txt not in seen:
                seen.add(txt)
                print(f"  {txt!r}")

        # --- try three search terms to learn matching behavior ---
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "FRM_CPH_txtSchool"))
        )
        for term in ["誠心", "誠心館", "学習塾誠心館", "セイシン", "070-5260-0835"]:
            try:
                f = driver.find_element(By.ID, "FRM_CPH_txtSchool")
                f.clear()
                f.send_keys(term)
                driver.find_element(By.ID, "FRM_CPH_btnSchoolSearch").click()
                time.sleep(3)

                links = driver.find_elements(By.XPATH, "//a[contains(@href, 'user_manager')]")
                rows_text = []
                rows = driver.find_elements(By.XPATH, "//table//tr")
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if tds:
                        text = " | ".join(td.text.strip() for td in tds if td.text.strip())
                        if text and "家族コード" not in text:
                            rows_text.append(text[:120])

                print(f"\n=== term={term!r}: 詳細リンク={len(links)} 件 ===")
                for n in rows_text[:8]:
                    print(f"  row: {n}")
            except Exception as e:
                print(f"\n=== term={term!r}: ERROR {e} ===")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
