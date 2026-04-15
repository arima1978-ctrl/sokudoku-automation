"""
100万人の速読 - 新規塾ID自動発行スクリプト

処理フロー:
1. Google Spreadsheet から新規申込データを読み取る
2. anyschool.jp で塾名検索し、家族コード（=塾ID）を取得
3. 100mil-sokudoku 管理サイトに塾IDを登録
4. スプレッドシートに処理結果を出力
"""

import argparse
import csv
import io
import os
import smtplib
import sys

# Windowsコンソール(cp932)で絵文字を出せるようUTF-8に変更
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import string
import secrets
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver

import telegram_approval as tg
import sheets_writer
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# ===================== 設定 =====================

load_dotenv(Path(__file__).parent / ".env", override=True)

SPREADSHEET_ID = "1jamO6vv1HjjYwm5D7VrMRhshkR_QNSLfEbc8UdEb5Fo"
SHEET_GID = "1353860533"

ANYSCHOOL_URL = "https://www.anyschool.jp/rakuraku_eduplus/k/menu.aspx?dummy=3229295875"
ANYSCHOOL_ID = os.environ.get("ANYSCHOOL_ID", "")
ANYSCHOOL_PW = os.environ.get("ANYSCHOOL_PW", "")

SOKUDOKU_URL = "https://new.100mil-sokudoku.com/manager"
SOKUDOKU_ADMIN_ID = os.environ.get("SOKUDOKU_ADMIN_ID", "")
SOKUDOKU_ADMIN_PW = os.environ.get("SOKUDOKU_ADMIN_PW", "")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").replace(" ", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_NAME = os.environ.get("SENDER_NAME", "磯一郎の100万人の速読 事務局")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# スプレッドシート列 (0-indexed)
COL_TIMESTAMP = 0
COL_EMAIL = 1
COL_JUKU_NAME = 3
COL_POSTAL_CODE = 4
COL_ADDRESS = 5
COL_TEL = 6
COL_CONTACT_NAME = 7
COL_CONTACT_MOBILE = 8
COL_CONTRACT_TYPE = 10
COL_DESIRED_PASSWORD = 11
COL_STATUS = 14  # O列 (M/N列は既存データで使用中のため)

HEADLESS = True


# ===================== ユーティリティ =====================

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]


def extract_prefecture(address: str) -> str:
    for pref in PREFECTURES:
        if address.startswith(pref):
            return pref
    return ""


def map_contract_type(contract_str: str) -> str:
    """2=カルチャーキッズ, 1=エデュプラス, 0=非会員"""
    if "カルチャーキッズ" in contract_str:
        return "2"
    if "エデュプラス" in contract_str:
        return "1"
    return "0"


def generate_password(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ===================== スプレッドシート =====================

def fetch_spreadsheet_data() -> list[list[str]]:
    url = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        f"/gviz/tq?tqx=out:csv&gid={SHEET_GID}"
    )
    response = urlopen(url)
    content = response.read().decode("utf-8")
    return list(csv.reader(io.StringIO(content)))


def get_pending_entries(
    rows: list[list[str]],
    target_rows: list[int] | None = None,
) -> list[dict]:
    if not rows:
        return []

    pending = []
    for i, row in enumerate(rows[1:], start=2):
        if target_rows is not None and i not in target_rows:
            continue
        if not row or len(row) <= COL_DESIRED_PASSWORD:
            continue
        if not row[COL_TIMESTAMP].strip():
            continue
        status = row[COL_STATUS].strip() if len(row) > COL_STATUS else ""
        if status and target_rows is None:
            continue

        address = row[COL_ADDRESS].strip()
        contract = row[COL_CONTRACT_TYPE].strip() if len(row) > COL_CONTRACT_TYPE else ""

        pending.append({
            "row_index": i,
            "email": row[COL_EMAIL].strip(),
            "juku_name": row[COL_JUKU_NAME].strip(),
            "address": address,
            "prefecture": extract_prefecture(address),
            "tel": row[COL_TEL].strip(),
            "mobile": row[COL_CONTACT_MOBILE].strip() if len(row) > COL_CONTACT_MOBILE else "",
            "contact_name": row[COL_CONTACT_NAME].strip(),
            "contract_type": contract,
            "culture_kids_flg": map_contract_type(contract),
            "desired_password": row[COL_DESIRED_PASSWORD].strip() if len(row) > COL_DESIRED_PASSWORD else "",
        })

    return pending


# ===================== anyschool.jp (Selenium) =====================

def create_driver() -> webdriver.Chrome:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


def anyschool_login(driver: webdriver.Chrome) -> None:
    driver.get(ANYSCHOOL_URL)
    time.sleep(3)
    if "login" in driver.current_url.lower():
        driver.find_element(By.ID, "txtLoginName").send_keys(ANYSCHOOL_ID)
        driver.find_element(By.ID, "txtPassword").send_keys(ANYSCHOOL_PW)
        driver.find_element(By.ID, "btnLogin").click()
        time.sleep(3)
    print(f"  anyschool.jp ログイン完了")


def _safe_get_value(driver: webdriver.Chrome, element_id: str) -> str:
    try:
        return driver.find_element(By.ID, element_id).get_attribute("value") or ""
    except Exception:
        return ""


def anyschool_search_by_school_name(driver: webdriver.Chrome, juku_name: str) -> dict | None:
    """検索して家族コード + 照合用情報を返す(先頭ヒットを採用)"""
    driver.execute_script("moveToUserList();")
    time.sleep(5)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "FRM_CPH_txtSchool"))
    )

    school_field = driver.find_element(By.ID, "FRM_CPH_txtSchool")
    school_field.clear()
    school_field.send_keys(juku_name)
    driver.find_element(By.ID, "FRM_CPH_btnSchoolSearch").click()
    time.sleep(3)

    detail_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'user_manager')]")
    candidate_count = len(detail_links)
    if not detail_links:
        print(f"    anyschool: '{juku_name}' が見つかりません")
        return None

    detail_links[0].click()
    time.sleep(3)

    family_code = _safe_get_value(driver, "FRM_CPH_txtManCode")
    if not family_code:
        print(f"    anyschool: 家族コードが空です")
        return None

    info = {
        "family_code": family_code,
        "school_name": _safe_get_value(driver, "FRM_CPH_txtSchoolName"),
        "tel": _safe_get_value(driver, "FRM_CPH_txtTel"),
        "address": _safe_get_value(driver, "FRM_CPH_txtAddress"),
        "email": _safe_get_value(driver, "FRM_CPH_txtMail"),
        "candidate_count": candidate_count,
        "search_term": juku_name,
    }
    print(f"    anyschool: 家族コード = {family_code} (候補{candidate_count}件, 検索語='{juku_name}')")
    return info


# ----- Task 3: スマート検索 -----

_SUFFIX_TRIM_LIST = sorted([
    "株式会社", "有限会社", "合同会社", "一般社団法人", "社会福祉法人", "学校法人", "（株）", "(株)",
    "学習教室", "教室", "塾", "学院", "アカデミー", "ゼミナール", "ゼミ",
    "予備校", "スクール", "教育", "進学塾", "学習塾", "英語教室", "英語", "英塾",
    "個別指導塾", "個別指導", "個別塾",
], key=len, reverse=True)  # 長い接尾辞を優先的にマッチ

_PREFIX_TRIM_LIST = sorted([
    "株式会社", "有限会社", "合同会社", "一般社団法人", "社会福祉法人", "学校法人",
    "（株）", "(株)", "（有）", "(有)",
], key=len, reverse=True)


def _trim_juku_name(name: str) -> list[str]:
    """塾名から段階的に短縮候補を生成 (重複排除、先頭一致=フルから短へ)"""
    candidates = [name]
    working = name
    changed = True
    while changed:
        changed = False
        for suffix in _SUFFIX_TRIM_LIST:
            if working.endswith(suffix) and len(working) > len(suffix):
                working = working[: -len(suffix)].strip("　 ")
                if working and working not in candidates:
                    candidates.append(working)
                    changed = True
                    break
    # 括弧除去バリエーション
    import re
    no_paren = re.sub(r"[（(][^）)]*[）)]", "", name).strip()
    if no_paren and no_paren not in candidates:
        candidates.insert(1, no_paren)
    return candidates


def _norm_tel(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _norm_email(s: str) -> str:
    return (s or "").strip().lower()


def anyschool_smart_search(driver: webdriver.Chrome, entry: dict) -> dict | None:
    """塾名フル→短縮→部分 の順で検索し、候補をメール/TELで検証。
    戻り値: anyschool_info + verification dict"""
    candidates = _trim_juku_name(entry["juku_name"])
    print(f"    anyschool: 検索候補 = {candidates}")

    for cand in candidates:
        info = anyschool_search_by_school_name(driver, cand)
        if info:
            # 検証スコアリング
            entry_email = _norm_email(entry.get("email", ""))
            entry_tel = _norm_tel(entry.get("tel", ""))
            anyschool_email = _norm_email(info.get("email", ""))
            anyschool_tel = _norm_tel(info.get("tel", ""))

            match_flags = []
            if anyschool_email and entry_email and anyschool_email == entry_email:
                match_flags.append("email一致")
            if anyschool_tel and entry_tel and anyschool_tel == entry_tel:
                match_flags.append("TEL一致")
            # 住所一致(先頭20文字)
            if info.get("address", "")[:20] and entry.get("address", "")[:20] \
                    and info["address"][:20] == entry["address"][:20]:
                match_flags.append("住所一致")

            info["match_flags"] = match_flags
            info["confidence"] = "high" if match_flags else "low"
            return info

    return None


# ===================== 100mil-sokudoku (requests) =====================

def sokudoku_create_session() -> requests.Session:
    """管理サイトにログインしたセッションを返す"""
    session = requests.Session()
    session.get(SOKUDOKU_URL)
    session.post(SOKUDOKU_URL, data={
        "INPUT_LOGIN_ID": SOKUDOKU_ADMIN_ID,
        "M_LOGIN.PASS": SOKUDOKU_ADMIN_PW,
    })
    print(f"  100mil-sokudoku ログイン完了")
    return session


def sokudoku_register_juku(
    session: requests.Session,
    entry: dict,
    juku_id: str,
    password: str,
) -> None:
    """管理サイトで塾ID登録（requests版）"""
    # CSRFトークン取得
    mypage = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
    soup = BeautifulSoup(mypage.text, "html.parser")
    regist_form = soup.find("form", action=lambda x: x and "Regist" in x)
    if not regist_form:
        raise Exception("登録フォームが見つかりません")

    token_input = regist_form.find("input", {"name": "__RequestVerificationToken"})
    if not token_input:
        raise Exception("CSRFトークンが見つかりません")
    token = token_input["value"]

    today = datetime.now().strftime("%Y/%m/%d")

    resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Regist",
        data={
            "__RequestVerificationToken": token,
            "R_M_JUKU.JUKU_ID": juku_id,
            "R_M_JUKU.KAZOKU_ID": juku_id,
            "R_M_JUKU.JUKU_NM": entry["juku_name"],
            "R_M_LOGIN.PASS": password,
            "R_M_JUKU.MAIL": entry["email"],
            "R_M_JUKU.TDFK": entry["prefecture"],
            "R_M_JUKU.JUSYO": entry["address"],
            "R_M_JUKU.TEL": entry["tel"],
            "R_M_JUKU.BIKO": "",
            "R_M_JUKU.TANT_NM": entry["contact_name"],
            "R_M_JUKU_CK.CULTURE_KIDS_FLG": entry["culture_kids_flg"],
            "STR_DateTime": today,
            "COURSE_LIST[0].COURSE_NM": "磯一郎の100万人の速読",
            "COURSE_LIST[0].COURSE_CD": "00",
            "COURSE_LIST[0].JUKU_STATUS_CD": "3",
            "COURSE_LIST[0].INPUT_STATUS_REF_YMD": today,
            "regist": "登録",
        },
    )

    # エラーチェック
    resp_soup = BeautifulSoup(resp.text, "html.parser")

    if "システムエラー" in resp.text or "EA01" in resp.text:
        raise Exception("サーバーエラー [EA01] - 塾IDが既に登録済みの可能性があります")

    field_errors = resp_soup.find_all(class_="field-validation-error")
    errors = [fe.get_text(strip=True) for fe in field_errors if fe.get_text(strip=True)]
    if errors:
        raise Exception(f"バリデーションエラー: {', '.join(errors)}")

    print(f"    sokudoku: 塾ID {juku_id} を登録しました")


def sokudoku_search_juku(session: requests.Session, juku_id: str) -> bool:
    """塾IDが登録済みかチェック（テーブルのtdセル内で完全一致）"""
    mypage = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
    soup = BeautifulSoup(mypage.text, "html.parser")
    search_form = soup.find("form", action=lambda x: x and "Search" in x)
    if not search_form:
        return False

    token = search_form.find("input", {"name": "__RequestVerificationToken"})["value"]
    resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/Search",
        data={
            "__RequestVerificationToken": token,
            "SEARCH_CONTENT_DATA.JUKU_ID": juku_id,
            "SEARCH_CONTENT_DATA.JUKU_NM": "",
            "SEARCH_CONTENT_DATA.JUKU_STATUS_CD": "",
            "SEARCH_CONTENT_DATA.COURSE_CD": "00",
        },
    )

    # テーブルのtdセル内で塾IDが完全一致するか確認
    resp_soup = BeautifulSoup(resp.text, "html.parser")
    for td in resp_soup.find_all("td"):
        if td.get_text(strip=True) == juku_id:
            return True
    return False


# ----- Task 4: 既登録塾の情報取得とPW更新 -----

def sokudoku_fetch_existing(session: requests.Session, juku_id: str) -> dict | None:
    """既登録塾の編集ページからフォームデータと現行情報を取得"""
    mypage = session.get("https://new.100mil-sokudoku.com/Manager/KanriMyPage/Index")
    soup = BeautifulSoup(mypage.text, "html.parser")
    search_form = soup.find("form", action=lambda x: x and "Search" in x)
    if not search_form:
        return None
    token = search_form.find("input", {"name": "__RequestVerificationToken"})["value"]

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
        return None

    edit_token = edit_form.find("input", {"name": "__RequestVerificationToken"})["value"]

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
        return None

    form_data: dict = {
        "__RequestVerificationToken": form.find(
            "input", {"name": "__RequestVerificationToken"}
        )["value"]
    }
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name or name == "__RequestVerificationToken":
            continue
        typ = inp.get("type", "text")
        val = inp.get("value", "")
        if typ == "radio":
            if inp.has_attr("checked"):
                form_data[name] = val
            else:
                form_data.setdefault(name, form_data.get(name, ""))
        elif typ == "checkbox":
            if inp.has_attr("checked"):
                form_data[name] = val
            else:
                form_data.setdefault(name, "false")
        else:
            form_data[name] = val

    return {
        "form_data": form_data,
        "current_info": {
            "juku_id": juku_id,
            "juku_name": form_data.get("UPDATE_INFO.JUKU_NM", ""),
            "email": form_data.get("UPDATE_INFO.MAIL", ""),
            "tel": form_data.get("UPDATE_INFO.TEL", ""),
            "contact_name": form_data.get("UPDATE_INFO.TANT_NM", ""),
            "password": form_data.get("UPDATE_INFO.PASS", ""),
        },
    }


def sokudoku_update_password(
    session: requests.Session, juku_id: str, new_password: str,
) -> bool:
    """既登録塾のパスワードを更新し、再取得で確認"""
    existing = sokudoku_fetch_existing(session, juku_id)
    if not existing:
        raise Exception(f"既存塾情報の取得失敗: {juku_id}")

    form_data = existing["form_data"].copy()
    form_data["UPDATE_INFO.PASS"] = new_password

    resp = session.post(
        "https://new.100mil-sokudoku.com/Manager/KanriMyPage/UPDATE",
        data=form_data,
    )
    if resp.status_code != 200:
        return False

    verify = sokudoku_fetch_existing(session, juku_id)
    return bool(verify and verify["current_info"]["password"] == new_password)


# ===================== メール送信 =====================

def send_welcome_email(entry: dict, juku_id: str, password: str) -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"    メール送信: SMTP設定未完了のためスキップ")
        return

    subject = "【磯一郎の100万人の速読】ログインID・パスワードのご案内"
    contact_name = entry["contact_name"] or entry["juku_name"]

    body = f"""{contact_name} 様

いつもお世話になっております。
磯一郎の100万人の速読 事務局です。

この度は、ご登録いただきありがとうございます。
以下がログインID・パスワードとなります。

━━━━━━━━━━━━━━━━━━━━━━━━
■ ログインURL
  https://new.100mil-sokudoku.com/manager

■ 塾名: {entry['juku_name']}

■ 塾ID: {juku_id}

■ パスワード: {password}
━━━━━━━━━━━━━━━━━━━━━━━━

上記のURLにアクセスし、塾IDとパスワードを入力してログインしてください。

ご不明点がございましたら、お気軽にお問い合わせください。

---
磯一郎の100万人の速読 事務局
"""

    msg = MIMEMultipart()
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = entry["email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    print(f"    メール送信完了: {entry['email']}")


# ===================== メイン =====================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="100万人の速読 - 新規塾ID自動発行")
    parser.add_argument(
        "--rows",
        type=str,
        default=None,
        help="処理する行番号のカンマ区切り (例: 202,203)。未指定時は STATUS 空の全行",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="確認プロンプトをスキップ",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="メール送信をスキップ",
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Telegram承認をスキップ(無条件に登録)",
    )
    parser.add_argument(
        "--approval-timeout",
        type=int,
        default=3600,
        help="Telegram承認待機タイムアウト秒 (default: 3600)",
    )
    return parser.parse_args()


def _write_status(row_index: int, mode: str, juku_id: str) -> None:
    """STATUS列を書き戻す。失敗してもログのみ"""
    try:
        status = sheets_writer.make_status_message(mode, juku_id)
        ok = sheets_writer.update_status(SPREADSHEET_ID, SHEET_GID, row_index, status)
        if ok:
            print(f"    STATUS書き戻し OK: 行{row_index} = '{status}'")
        else:
            print(f"    STATUS書き戻し 未実施 (認証情報なし等)")
    except Exception as e:
        print(f"    STATUS書き戻し 失敗: {e}")


def _transfer_to_master(entry: dict, juku_id: str) -> None:
    """マスターシートへ転記。重複時はスキップ。失敗してもログのみ"""
    try:
        import master_list_writer
        ok, msg = master_list_writer.write_entry(
            entry, juku_id, mobile=entry.get("mobile", "")
        )
        prefix = "マスター転記" if ok else "マスター転記スキップ"
        print(f"    {prefix}: {msg}")
    except Exception as e:
        print(f"    マスター転記 失敗: {e}")


def _esc_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_approval_text(entry: dict, info: dict, juku_id: str, password: str) -> str:
    """新規登録用の承認リクエストメッセージ"""
    esc = _esc_html

    match_flags = info.get("match_flags", [])
    warnings = []
    if info.get("candidate_count", 0) > 1:
        warnings.append(f"⚠️ anyschool候補 {info['candidate_count']}件 (1件目採用)")
    if info.get("confidence") == "low":
        warnings.append("⚠️ メール/TEL/住所いずれも一致せず")

    lines = [
        f"<b>【新規登録 承認依頼】行{entry['row_index']}</b>",
        "",
        "<b>■ 申込内容 (スプレッドシート)</b>",
        f"塾名: {esc(entry['juku_name'])}",
        f"TEL: {esc(entry['tel'])}",
        f"メール: {esc(entry['email'])}",
        f"住所: {esc(entry['address'])}",
        f"担当者: {esc(entry['contact_name'])} 様",
        f"契約: {esc(entry['contract_type'])}",
        "",
        f"<b>■ anyschool.jp 検索結果 (検索語='{esc(info.get('search_term', ''))}')</b>",
        f"塾名: {esc(info.get('school_name', ''))}",
        f"TEL: {esc(info.get('tel', ''))}",
        f"メール: {esc(info.get('email', ''))}",
        f"住所: {esc(info.get('address', ''))}",
        f"家族コード: <code>{esc(juku_id)}</code>",
    ]
    if match_flags:
        lines.append(f"照合: ✅ {', '.join(match_flags)}")
    lines += [
        "",
        "<b>■ 登録予定</b>",
        f"塾ID: <code>{esc(juku_id)}</code>",
        f"PW: <code>{esc(password)}</code>",
    ]
    if warnings:
        lines.append("")
        lines.extend(warnings)
    return "\n".join(lines)


def _build_existing_approval_text(
    entry: dict, info: dict, current: dict, new_password: str, password_changed: bool,
) -> str:
    """既登録塾の承認リクエストメッセージ"""
    esc = _esc_html
    action = f"PW変更 (<code>{esc(current['password'])}</code> → <code>{esc(new_password)}</code>) + メール送信" \
        if password_changed else "メール送信のみ (PW変更なし)"

    lines = [
        f"<b>【既登録 承認依頼】行{entry['row_index']}</b>",
        "",
        "<b>■ 既存塾情報 (100mil-sokudoku)</b>",
        f"塾ID: <code>{esc(current['juku_id'])}</code>",
        f"塾名: {esc(current['juku_name'])}",
        f"メール: {esc(current['email'])}",
        f"TEL: {esc(current['tel'])}",
        f"担当: {esc(current['contact_name'])} 様",
        f"現行PW: <code>{esc(current['password'])}</code>",
        "",
        "<b>■ 申込内容 (スプレッドシート)</b>",
        f"塾名: {esc(entry['juku_name'])}",
        f"メール: {esc(entry['email'])}",
        f"TEL: {esc(entry['tel'])}",
        f"担当: {esc(entry['contact_name'])} 様",
        "",
        "<b>■ 実行予定</b>",
        action,
        f"送信先: {esc(current['email'])}",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    target_rows: list[int] | None = None
    if args.rows:
        target_rows = [int(x.strip()) for x in args.rows.split(",") if x.strip()]

    print("=" * 60)
    print("100万人の速読 - 新規塾ID自動発行")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if target_rows:
        print(f"対象行: {target_rows}")
    print("=" * 60)

    # 1. スプレッドシートからデータ取得
    print("\n[1/4] スプレッドシートからデータを取得中...")
    rows = fetch_spreadsheet_data()
    pending = get_pending_entries(rows, target_rows=target_rows)

    if not pending:
        print("  未処理のエントリはありません。")
        # 定期実行時は無通知で終了(申込ゼロは無音)
        return

    print(f"  {len(pending)} 件の対象エントリ:")
    for entry in pending[:10]:
        print(f"    行{entry['row_index']}: {entry['juku_name']} ({entry['email']})")
    if len(pending) > 10:
        print(f"    ... 他 {len(pending) - 10} 件")

    if not args.yes:
        confirm = input("\n処理を開始しますか？ (y/N): ")
        if confirm.lower() != "y":
            print("キャンセルしました。")
            return

    use_telegram = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) and not args.no_telegram

    # 2. 一件ずつ処理
    print("\n[2/3] 処理開始...")
    driver = create_driver()
    results: list[dict] = []
    session = None
    try:
        anyschool_login(driver)
        session = sokudoku_create_session()

        for entry in pending:
            print(f"\n--- 行{entry['row_index']}: {entry['juku_name']} ---")
            result = {"entry": entry, "success": False}
            results.append(result)

            try:
                # a. anyschool でスマート検索
                info = anyschool_smart_search(driver, entry)
                if not info:
                    result["error"] = "家族コード未取得"
                    if use_telegram:
                        tg.send_info(
                            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                            f"⚠️ 行{entry['row_index']}: <b>{entry['juku_name']}</b> - anyschool.jp で見つかりませんでした",
                        )
                    continue

                juku_id = info["family_code"]
                desired_password = entry["desired_password"] or generate_password()

                # b. 既登録チェック → 分岐
                if sokudoku_search_juku(session, juku_id):
                    # 既登録 → 現行情報取得 + PW差分判定
                    existing = sokudoku_fetch_existing(session, juku_id)
                    if not existing:
                        result["error"] = "既登録だが詳細取得失敗"
                        continue
                    current = existing["current_info"]
                    password = desired_password
                    password_changed = current["password"] != password

                    text = _build_existing_approval_text(
                        entry, info, current, password, password_changed,
                    )
                    if use_telegram:
                        msg_id = tg.send_approval_request(
                            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                            text, entry["row_index"],
                        )
                        print(f"    Telegram承認待ち (既登録)...")
                        decision = tg.wait_for_decision(
                            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                            msg_id, entry["row_index"],
                            timeout_sec=args.approval_timeout,
                        )
                        if decision is None:
                            result["error"] = "承認タイムアウト"
                            continue
                        if not decision:
                            result["error"] = "却下"
                            continue

                    # PW更新(必要時)
                    if password_changed:
                        ok = sokudoku_update_password(session, juku_id, password)
                        if not ok:
                            result["error"] = "PW更新失敗"
                            continue
                        print(f"    PW更新OK: {juku_id} -> {password}")

                    # メール送信
                    if not args.no_email:
                        try:
                            send_welcome_email(entry, juku_id, password)
                        except Exception as e:
                            print(f"    メール送信失敗: {e}")

                    result["juku_id"] = juku_id
                    result["password"] = password
                    result["mode"] = "updated" if password_changed else "resent"
                    result["success"] = True
                    _write_status(entry["row_index"], result["mode"], juku_id)
                    _transfer_to_master(entry, juku_id)
                    if use_telegram:
                        action = "PW変更+再送" if password_changed else "メール再送"
                        tg.send_info(
                            TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                            f"✉️ 行{entry['row_index']}: <b>{entry['juku_name']}</b> 既登録→{action}完了\n塾ID: <code>{juku_id}</code>",
                        )
                    continue

                # c. Telegram承認 (新規登録)
                password = desired_password
                if use_telegram:
                    text = _build_approval_text(entry, info, juku_id, password)
                    msg_id = tg.send_approval_request(
                        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                        text, entry["row_index"],
                    )
                    print(f"    Telegram承認待ち (新規登録)...")
                    decision = tg.wait_for_decision(
                        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                        msg_id, entry["row_index"],
                        timeout_sec=args.approval_timeout,
                    )
                    if decision is None:
                        result["error"] = "承認タイムアウト"
                        continue
                    if not decision:
                        result["error"] = "却下"
                        continue

                # d. 登録
                sokudoku_register_juku(session, entry, juku_id, password)
                result["juku_id"] = juku_id
                result["password"] = password
                result["mode"] = "registered"

                if sokudoku_search_juku(session, juku_id):
                    print(f"    確認OK: 塾ID {juku_id}")
                else:
                    print(f"    WARNING: 登録後の確認で見つかりませんでした")

                # e. メール送信
                if not args.no_email:
                    try:
                        send_welcome_email(entry, juku_id, password)
                    except Exception as e:
                        print(f"    メール送信失敗: {e}")

                result["success"] = True
                _write_status(entry["row_index"], "registered", juku_id)
                _transfer_to_master(entry, juku_id)

                if use_telegram:
                    tg.send_info(
                        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                        f"✉️ 行{entry['row_index']}: <b>{entry['juku_name']}</b> 登録+メール送信完了\n塾ID: <code>{juku_id}</code>",
                    )
            except Exception as e:
                print(f"    ERROR: {e}")
                result["error"] = str(e)
                if use_telegram:
                    tg.send_info(
                        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                        f"❌ 行{entry['row_index']}: <b>{entry['juku_name']}</b> エラー: {e}",
                    )
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # 3. 結果出力
    print("\n[3/3] 結果サマリー")
    print("=" * 60)
    success_count = sum(1 for r in results if r["success"])
    fail_count = sum(1 for r in results if not r["success"])
    print(f"  成功: {success_count} 件")
    print(f"  失敗/スキップ: {fail_count} 件")

    if success_count > 0:
        print("\n  登録成功:")
        for r in results:
            if r["success"]:
                print(f"    {r['entry']['juku_name']}: 塾ID={r['juku_id']}, PW={r['password']}")

    if fail_count > 0:
        print("\n  失敗/スキップ:")
        for r in results:
            if not r["success"]:
                print(f"    {r['entry']['juku_name']}: {r.get('error', '不明')}")

    print("=" * 60)


if __name__ == "__main__":
    main()
