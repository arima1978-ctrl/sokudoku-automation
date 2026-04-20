"""anyschool 検索の追加調査: txtName/txtKana/txtParent で漢字/カナがヒットするか"""
import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


TEST_CASES = [
    ("FRM_CPH_txtName", "FRM_CPH_btnNameSearch", "誠心館"),
    ("FRM_CPH_txtName", "FRM_CPH_btnNameSearch", "学習塾誠心館"),
    ("FRM_CPH_txtName", "FRM_CPH_btnNameSearch", "誠心"),
    ("FRM_CPH_txtKana", "FRM_CPH_btnKanaSearch", "セイシンカン"),
    ("FRM_CPH_txtKana", "FRM_CPH_btnKanaSearch", "セイシン"),
    ("FRM_CPH_txtKana", "FRM_CPH_btnKanaSearch", "ガクシュウジュクセイシンカン"),
    ("FRM_CPH_txtParent", "FRM_CPH_btnParentSearch", "誠心館"),
    ("FRM_CPH_txtParent", "FRM_CPH_btnParentSearch", "合同会社誠心館"),
    ("FRM_CPH_txtParent", "FRM_CPH_btnParentSearch", "渡部"),
    ("FRM_CPH_txtSchool", "FRM_CPH_btnSchoolSearch", "セイシンカン"),
    ("FRM_CPH_txtSchool", "FRM_CPH_btnSchoolSearch", "ガクシュウジュクセイシンカン"),
]


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
        driver.get(url)
        time.sleep(3)
        if "login" in driver.current_url.lower():
            driver.find_element(By.ID, "txtLoginName").send_keys(lid)
            driver.find_element(By.ID, "txtPassword").send_keys(lpw)
            driver.find_element(By.ID, "btnLogin").click()
            time.sleep(3)
        print(f"[login] {driver.current_url}")

        driver.execute_script("moveToUserList();")
        time.sleep(5)

        for field_id, btn_id, term in TEST_CASES:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, field_id))
                )
                # clear all text fields first
                for fid in ("FRM_CPH_txtStId", "FRM_CPH_txtName", "FRM_CPH_txtKana",
                            "FRM_CPH_txtSchool", "FRM_CPH_txtGaku2",
                            "FRM_CPH_txtParent", "FRM_CPH_txtBirth"):
                    try:
                        driver.find_element(By.ID, fid).clear()
                    except Exception:
                        pass
                f = driver.find_element(By.ID, field_id)
                f.clear()
                f.send_keys(term)
                driver.find_element(By.ID, btn_id).click()
                time.sleep(3)

                links = driver.find_elements(By.XPATH, "//a[contains(@href, 'user_manager')]")
                rows_text = []
                rows = driver.find_elements(By.XPATH, "//table//tr")
                for row in rows:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if tds:
                        text = " | ".join(td.text.strip() for td in tds if td.text.strip())
                        if text and "家族コード" not in text and "退会者" not in text:
                            rows_text.append(text[:140])

                print(f"\n=== field={field_id.replace('FRM_CPH_', '')} term={term!r}: 詳細リンク={len(links)} 件 ===")
                for n in rows_text[:8]:
                    print(f"  row: {n}")
            except Exception as e:
                print(f"\n=== field={field_id} term={term!r}: ERROR {type(e).__name__}: {e} ===")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
