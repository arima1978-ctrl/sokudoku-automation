"""
anyschool.jp ユーザー詳細ページと新規登録の調査
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

        # ユーザー一覧へ
        driver.execute_script("moveToUserList();")
        time.sleep(5)

        # 最初の詳細リンクをクリック
        print("=== ユーザー詳細ページ ===")
        detail_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "\u8a73\u7d30")
        if not detail_links:
            detail_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'user_manager')]")

        if detail_links:
            print(f"詳細リンク数: {len(detail_links)}")
            detail_links[0].click()
            time.sleep(5)

            print(f"URL: {driver.current_url}")
            print(f"Title: {driver.title}")
            driver.save_screenshot("anyschool_detail.png")
            with open("anyschool_detail.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            # フォーム要素
            print("\n=== フォーム要素 ===")
            for inp in driver.find_elements(By.TAG_NAME, "input"):
                inp_type = (inp.get_attribute("type") or "").lower()
                if inp_type != "hidden":
                    name = inp.get_attribute("name") or ""
                    value = inp.get_attribute("value") or ""
                    print(f"  input: name={name}, type={inp_type}, id={inp.get_attribute('id')}, value={value[:50]}")

            for sel in driver.find_elements(By.TAG_NAME, "select"):
                selected = ""
                for opt in sel.find_elements(By.TAG_NAME, "option"):
                    if opt.is_selected():
                        selected = opt.text
                print(f"  select: name={sel.get_attribute('name')}, id={sel.get_attribute('id')}, selected={selected}")

            for ta in driver.find_elements(By.TAG_NAME, "textarea"):
                print(f"  textarea: name={ta.get_attribute('name')}, id={ta.get_attribute('id')}, value={ta.get_attribute('value')[:50]}")

            # 家族コード関連
            print("\n=== 家族コード関連 ===")
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), '家族') or contains(text(), 'kazoku') or contains(text(), 'family')]")
            for el in elements:
                try:
                    print(f"  <{el.tag_name}> [{el.text.strip()[:200]}]")
                except:
                    pass

            # ラベルとテキスト
            print("\n=== 全テキストラベル ===")
            tds = driver.find_elements(By.TAG_NAME, "td")
            for td in tds:
                text = td.text.strip()
                if text and len(text) < 100:
                    print(f"  <td> {text}")

            # spanも確認
            spans = driver.find_elements(By.TAG_NAME, "span")
            for sp in spans:
                text = sp.text.strip()
                sp_id = sp.get_attribute("id") or ""
                if text and len(text) < 100:
                    print(f"  <span id={sp_id}> {text}")

            # ボタン
            print("\n=== ボタン ===")
            for btn in driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], input[type='button'], button"):
                print(f"  {btn.tag_name}: name={btn.get_attribute('name')}, value={btn.get_attribute('value')}, id={btn.get_attribute('id')}, text={btn.text}")

            # リンク
            print("\n=== リンク ===")
            for link in driver.find_elements(By.TAG_NAME, "a"):
                try:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""
                    onclick = link.get_attribute("onclick") or ""
                    if text:
                        print(f"  [{text}] href={href} onclick={onclick[:100]}")
                except:
                    pass

        else:
            print("詳細リンクが見つかりません")

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
