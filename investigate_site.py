"""
管理サイトの構造を調査するスクリプト (v2)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

MANAGER_URL = "https://new.100mil-sokudoku.com/manager"
LOGIN_ID = "999003"
LOGIN_PW = "Gccmeidaisky003"


def investigate():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)

    try:
        # 1. ログイン
        print("=== ログイン ===")
        driver.get(MANAGER_URL)
        time.sleep(2)

        driver.find_element(By.ID, "INPUT_LOGIN_ID").send_keys(LOGIN_ID)
        driver.find_element(By.ID, "M_LOGIN_PASS").send_keys(LOGIN_PW)
        driver.find_element(By.ID, "login").click()
        time.sleep(5)

        # 2. ログイン後のページ
        print(f"URL: {driver.current_url}")
        print(f"Title: {driver.title}")

        # HTMLを保存
        with open("after_login.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("after_login.html 保存")

        driver.save_screenshot("after_login_screenshot.png")
        print("after_login_screenshot.png 保存")

        # リンク一覧
        print("\n=== リンク ===")
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if text or href:
                    print(f"  [{text}] -> {href}")
            except:
                pass

        # ボタン一覧
        print("\n=== ボタン ===")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            try:
                print(f"  [{btn.text.strip()}] id={btn.get_attribute('id')} class={btn.get_attribute('class')}")
            except:
                pass

        # フォーム一覧
        print("\n=== フォーム ===")
        forms = driver.find_elements(By.TAG_NAME, "form")
        for i, form in enumerate(forms):
            try:
                print(f"\nForm {i+1}: action={form.get_attribute('action')}, method={form.get_attribute('method')}")
                for inp in form.find_elements(By.TAG_NAME, "input"):
                    print(f"  input: name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, id={inp.get_attribute('id')}, value={inp.get_attribute('value')}, placeholder={inp.get_attribute('placeholder')}")
                for sel in form.find_elements(By.TAG_NAME, "select"):
                    print(f"  select: name={sel.get_attribute('name')}, id={sel.get_attribute('id')}")
                    for opt in sel.find_elements(By.TAG_NAME, "option"):
                        print(f"    option: value={opt.get_attribute('value')}, text={opt.text}")
                for ta in form.find_elements(By.TAG_NAME, "textarea"):
                    print(f"  textarea: name={ta.get_attribute('name')}, id={ta.get_attribute('id')}")
            except:
                pass

        # 塾/新規/登録 関連テキスト
        print("\n=== 塾/新規/登録 関連 ===")
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '塾') or contains(text(), '新規') or contains(text(), '登録') or contains(text(), '追加') or contains(text(), 'ID')]")
        for el in elements:
            try:
                tag = el.tag_name
                text = el.text.strip()[:200]
                if text:
                    print(f"  <{tag}> {text}")
            except:
                pass

        # 全input
        print("\n=== 全input ===")
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            try:
                print(f"  name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, id={inp.get_attribute('id')}, placeholder={inp.get_attribute('placeholder')}")
            except:
                pass

        # 全select
        print("\n=== 全select ===")
        for sel in driver.find_elements(By.TAG_NAME, "select"):
            try:
                print(f"  name={sel.get_attribute('name')}, id={sel.get_attribute('id')}")
                for opt in sel.find_elements(By.TAG_NAME, "option"):
                    print(f"    value={opt.get_attribute('value')}, text={opt.text}")
            except:
                pass

        # テーブル
        print("\n=== テーブル ===")
        tables = driver.find_elements(By.TAG_NAME, "table")
        for i, table in enumerate(tables):
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                print(f"\nTable {i+1}: {len(rows)} rows")
                for j, row in enumerate(rows[:5]):
                    cells = row.find_elements(By.TAG_NAME, "td") + row.find_elements(By.TAG_NAME, "th")
                    texts = [c.text.strip()[:50] for c in cells]
                    print(f"  Row {j}: {texts}")
            except:
                pass

        print("\n調査完了。")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        try:
            driver.save_screenshot("error_screenshot.png")
        except:
            pass

    finally:
        driver.quit()


if __name__ == "__main__":
    investigate()
