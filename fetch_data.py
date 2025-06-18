import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# ========== 配置 ==========
SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"

cookie_string = os.environ.get("YUANRI_COOKIE", "")
json_str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "")

# 修复：抓取“全部”状态的页面
URL = "http://www.yuanriguoji.com/Phone/Package"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": cookie_string
}

# ========== 获取 Google Sheets 客户端 ==========
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    info = json.loads(json_str)
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# ========== 抓取页面中的快递记录 ==========
def fetch_packages():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    inputs = soup.find_all("input", class_="chk_select")

    records = []
    for tag in inputs:
        pkg_id = tag.get("value")
        weight = tag.get("data-weight", "0")
        span = soup.find("span", {"name": "BillCode", "data-id": pkg_id})
        if not span:
            continue
        tracking = span.text.strip()

        # 查找“到库时间”
        arrive_time = ""
        container_div = span.find_parent("div")
        if container_div:
            time_pair = container_div.find_all("p", class_="more_massage")
            for p in time_pair:
                label = p.find("span", class_="SpanTitleLang")
                value = p.find("span", class_="SpanTextLang")
                if label and "到库时间" in label.text and value:
                    arrive_time = value.text.strip()
                    break

        # ✅ Debug 输出
        print(f"📦 单号: {tracking} | 重量: {weight} | 到库时间: {arrive_time}")

        records.append({
            "快递单号": tracking,
            "重量（kg）": weight,
            "谁的快递": "",
            "到库时间": arrive_time
        })
    return pd.DataFrame(records)

# ========== 合并新增数据 ==========
def update_main_sheet(new_df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    existing = pd.DataFrame(sheet.get_all_records())

    if existing.empty:
        existing = pd.DataFrame(columns=["快递单号", "重量（kg）", "谁的快递", "到库时间"])

    existing["快递单号"] = existing["快递单号"].astype(str)
    new_df["快递单号"] = new_df["快递单号"].astype(str)

    existing_ids = set(existing["快递单号"])
    new_entries = new_df[~new_df["快递单号"].isin(existing_ids)]

    print(f"📦 抓取到的所有单号： {list(new_df['快递单号'])}")
    print(f"📄 表中已有单号： {list(existing['快递单号'])}")

    if new_entries.empty:
        print("📭 没有新增记录，跳过更新 ✅")
        return

    updated = pd.concat([existing, new_entries], ignore_index=True)
    updated = updated[["快递单号", "重量（kg）", "谁的快递", "到库时间"]]
    sheet.clear()
    sheet.update([updated.columns.values.tolist()] + updated.values.tolist())
    print(f"✅ 已新增 {len(new_entries)} 条记录，并更新 Google Sheets ✅")

# ========== 主流程 ==========
def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    if df.empty:
        print("⚠️ 未抓取到任何记录，请检查 Cookie 或页面结构")
        return
    update_main_sheet(df)
    print("✅ Google Sheets 已更新")

if __name__ == "__main__":
    main()
