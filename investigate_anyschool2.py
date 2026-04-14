"""
anyschool.jp ユーザー管理ページの調査
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time


ANYSCHOOL_URL = "https://www.anyschool.jp/rakuraku_eduplus/k/menu.aspx?dummy=3229295875"
LOGIN_ID = "arima"
LOGIN_PW = "b87w"


def investigate():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)

    try:
        # ログイン
        driver.get(ANYSCHOOL_URL)
        time.sleep(3)
        driver.find_element(By.ID, "txtLoginName").send_keys(LOGIN_ID)
        driver.find_element(By.ID, "txtPassword").send_keys(LOGIN_PW)
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)
        print(f"ログイン後URL: {driver.current_url}")

        # ユーザー（保護者）管理ページへ遷移
        print("\n=== ユーザー（保護者）管理へ遷移 ===")
        driver.execute_script("moveToUserList();")
        time.sleep(5)
        print(f"URL: {driver.current_url}")
        print(f"Title: {driver.title}")
        driver.save_screenshot("anyschool_userlist.png")
        with open("anyschool_userlist.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # 検索フォーム
        print("\n=== 検索フォーム ===")
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            inp_type = (inp.get_attribute("type") or "").lower()
            if inp_type != "hidden":
                print(f"  input: name={inp.get_attribute('name')}, type={inp_type}, id={inp.get_attribute('id')}, value={inp.get_attribute('value')}")
        for sel in driver.find_elements(By.TAG_NAME, "select"):
            print(f"  select: name={sel.get_attribute('name')}, id={sel.get_attribute('id')}")
            for opt in sel.find_elements(By.TAG_NAME, "option"):
                print(f"    option: value={opt.get_attribute('value')}, text={opt.text}")

        # ボタン
        print("\n=== ボタン ===")
        for btn in driver.find_elements(By.TAG_NAME, "input"):
            if (btn.get_attribute("type") or "").lower() in ("submit", "button"):
                print(f"  name={btn.get_attribute('name')}, value={btn.get_attribute('value')}, id={btn.get_attribute('id')}")
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            print(f"  button: text={btn.text}, id={btn.get_attribute('id')}")

        # リンク
        print("\n=== リンク ===")
        for link in driver.find_elements(By.TAG_NAME, "a"):
            try:
                text = link.text.strip()
                href = link.get_attribute("href") or ""
                if text:
                    print(f"  [{text}] -> {href}")
            except:
                pass

        # テーブル（ユーザーリスト）
        print("\n=== テーブル ===")
        tables = driver.find_elements(By.TAG_NAME, "table")
        for i, table in enumerate(tables):
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                print(f"\nTable {i+1}: {len(rows)} rows")
                for j, row in enumerate(rows[:10]):
                    cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                    texts = [c.text.strip()[:30] for c in cells]
                    print(f"  Row {j}: {texts}")
            except:
                pass

        # 塾名検索を試す
        print("\n=== 塾名検索テスト ===")
        search_fields = driver.find_elements(By.XPATH, "//input[contains(@id, 'school') or contains(@id, 'School') or contains(@name, 'school') or contains(@name, 'School') or contains(@id, 'juku') or contains(@id, 'search') or contains(@id, 'Search')]")
        for sf in search_fields:
            print(f"  検索フィールド候補: name={sf.get_attribute('name')}, id={sf.get_attribute('id')}, type={sf.get_attribute('type')}")

        # 新規登録リンク/ボタン
        print("\n=== 新規登録関連 ===")
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '新規') or contains(text(), '登録') or contains(text(), '追加')]")
        for el in elements:
            try:
                print(f"  <{el.tag_name}> [{el.text.strip()[:100]}] id={el.get_attribute('id')} href={el.get_attribute('href')}")
            except:
                pass

        print("\n調査完了。")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        try:
            driver.save_screenshot("anyschool_error.png")
        except:
            pass
    finally:
        driver.quit()


if __name__ == "__main__":
    investigate()
