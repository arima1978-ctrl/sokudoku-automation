"""
anyschool.jp の構造を調査するスクリプト
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
        # 1. ログインページ
        print("=== anyschool.jp ログインページ ===")
        driver.get(ANYSCHOOL_URL)
        time.sleep(3)

        print(f"URL: {driver.current_url}")
        print(f"Title: {driver.title}")
        driver.save_screenshot("anyschool_login.png")

        # フォーム要素
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n入力フィールド: {len(inputs)}")
        for inp in inputs:
            print(f"  name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, id={inp.get_attribute('id')}, value={inp.get_attribute('value')}")

        # ログイン試行
        id_field = None
        pw_field = None
        for inp in inputs:
            inp_type = (inp.get_attribute("type") or "").lower()
            inp_name = (inp.get_attribute("name") or "").lower()
            inp_id = (inp.get_attribute("id") or "").lower()
            if inp_type == "password":
                pw_field = inp
            elif inp_type in ("text", "") and ("id" in inp_name or "id" in inp_id or "user" in inp_name or "login" in inp_name):
                id_field = inp
            elif inp_type in ("text", "") and id_field is None and inp_type != "hidden":
                id_field = inp

        if id_field:
            id_field.clear()
            id_field.send_keys(LOGIN_ID)
            print(f"\nID入力: {LOGIN_ID} (field: {id_field.get_attribute('name')})")
        else:
            print("ERROR: IDフィールドが見つかりません")

        if pw_field:
            pw_field.clear()
            pw_field.send_keys(LOGIN_PW)
            print(f"PW入力: *** (field: {pw_field.get_attribute('name')})")
        else:
            print("ERROR: PWフィールドが見つかりません")

        # ログインボタン
        buttons = driver.find_elements(By.TAG_NAME, "button")
        submit_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], input[type='image']")
        all_buttons = buttons + submit_inputs
        print(f"\nボタン: {len(all_buttons)}")
        for btn in all_buttons:
            print(f"  text={btn.text}, type={btn.get_attribute('type')}, id={btn.get_attribute('id')}, value={btn.get_attribute('value')}, name={btn.get_attribute('name')}")

        login_btn = None
        for btn in all_buttons:
            text = (btn.text or "").strip()
            value = (btn.get_attribute("value") or "").strip()
            if "ログイン" in text or "login" in text.lower() or "ログイン" in value or "login" in value.lower():
                login_btn = btn
                break
        if login_btn is None and all_buttons:
            login_btn = all_buttons[0]

        if login_btn:
            login_btn.click()
            print(f"ログインボタンクリック")
        time.sleep(5)

        # 2. ログイン後
        print(f"\n=== ログイン後 ===")
        print(f"URL: {driver.current_url}")
        print(f"Title: {driver.title}")

        with open("anyschool_after_login.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("anyschool_after_login.png")
        print("anyschool_after_login.html / .png 保存")

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

        # ユーザー管理系のリンクを探す
        print("\n=== ユーザー/保護者/塾 関連 ===")
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'ユーザー') or contains(text(), '保護者') or contains(text(), '塾') or contains(text(), '家族') or contains(text(), '管理')]")
        for el in elements:
            try:
                tag = el.tag_name
                text = el.text.strip()[:200]
                href = el.get_attribute("href") or ""
                if text:
                    print(f"  <{tag}> [{text}] {href}")
            except:
                pass

        # ユーザー（保護者）管理ページに遷移を試みる
        print("\n=== ユーザー（保護者）管理ページへの遷移 ===")
        user_mgmt_link = None
        for link in links:
            try:
                text = link.text.strip()
                if "ユーザー" in text or "保護者" in text:
                    user_mgmt_link = link
                    print(f"  Found: [{text}] -> {link.get_attribute('href')}")
                    break
            except:
                pass

        if user_mgmt_link:
            user_mgmt_link.click()
            time.sleep(3)
            print(f"URL: {driver.current_url}")
            print(f"Title: {driver.title}")
            driver.save_screenshot("anyschool_user_mgmt.png")
            with open("anyschool_user_mgmt.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("anyschool_user_mgmt.html / .png 保存")

            # フォーム要素
            print("\n=== ユーザー管理ページのフォーム ===")
            forms = driver.find_elements(By.TAG_NAME, "form")
            for i, form in enumerate(forms):
                try:
                    print(f"\nForm {i+1}: action={form.get_attribute('action')}, method={form.get_attribute('method')}")
                    for inp in form.find_elements(By.TAG_NAME, "input"):
                        if inp.get_attribute("type") != "hidden":
                            print(f"  input: name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, id={inp.get_attribute('id')}, placeholder={inp.get_attribute('placeholder')}")
                    for sel in form.find_elements(By.TAG_NAME, "select"):
                        print(f"  select: name={sel.get_attribute('name')}, id={sel.get_attribute('id')}")
                except:
                    pass

            # リンク一覧
            print("\n=== ユーザー管理ページのリンク ===")
            for link in driver.find_elements(By.TAG_NAME, "a"):
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    if text:
                        print(f"  [{text}] -> {href}")
                except:
                    pass

            # 塾名検索を探す
            print("\n=== 検索関連 ===")
            search_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '検索') or contains(text(), '塾名')]")
            for el in search_elements:
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
