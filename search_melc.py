"""メルク英語教室を複数の表記で anyschool.jp 検索"""

import time
from main import (
    create_driver, anyschool_login, anyschool_search_by_school_name,
)

candidates = [
    "メルク英語教室",
    "メルク",
    "MELC",
    "melc",
    "メルク英語",
    "melc英語教室",
]

driver = create_driver()
try:
    anyschool_login(driver)
    for cand in candidates:
        print(f"\n--- 検索: '{cand}' ---")
        try:
            info = anyschool_search_by_school_name(driver, cand)
            if info:
                print(f"  HIT!")
                for k, v in info.items():
                    print(f"    {k}: {v}")
                break
        except Exception as e:
            print(f"  エラー: {e}")
        time.sleep(1)
finally:
    driver.quit()
