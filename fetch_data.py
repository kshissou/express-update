import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import tempfile

# ==== 配置 ====
SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"
URL = "http://www.yuanriguoji.com/Phone/Package?WaveHouse=0&Prediction=2&Storage=0&Grounding=0&active=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": os.environ["YUANRI_COOKIE"]
}
# ==============

# 获取 Google Sheets 客户端
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    json_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(json_str)
        tmp.flush()
        creds = Credentials.from_service_account_file(tmp.name, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# 抓取快递数据
def fetch_packages():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    inputs = soup.find_all("input", class_="chk_select")

    records = []
    for tag in inputs:
        pkg_id = tag.get("value")
        weight = tag.get("data-weight", "0").strip()
        span = soup.find("span", {"name": "BillCode", "data-id": pkg_id})
        if span:
            tracking = span.text.strip()
            if tracking:  # 确保单号不为空
                records.append({
                    "快递单号": tracking,
                    "重量（kg）": weight,
                    "谁的快递": ""
                })
    return pd.DataFrame(records)

# 更新主表
def update_main_sheet(new_df):
    if new_df.empty:
        print("📭 没有抓取到有效快递记录，跳过更新 ❌")
        return

    new_df["快递单号"] = new_df["快递单号"].astype(str)
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    existing_data = sheet.get_all_records()
    old_df = pd.DataFrame(existing_data)
    old_df["快递单号"] = old_df["快递单号"].astype(str)

    print(f"📦 抓取到的所有单号： {new_df['快递单号'].tolist()}")
    print(f"📄 表中已有单号： {old_df['快递单号'].tolist()}")

    # 检查哪些是新增
    new_only = new_df[~new_df["快递单号"].isin(old_df["快递单号"])]
    if new_only.empty:
        print("📭 没有新增记录，跳过更新 ✅")
        return

    combined_df = pd.concat([old_df, new_only], ignore_index=True)
    combined_df = combined_df[["快递单号", "重量（kg）", "谁的快递"]]
    sheet.clear()
    sheet.update([combined_df.columns.values.tolist()] + combined_df.values.tolist())
    print(f"📥 成功新增 {len(new_only)} 条记录 ✅")

# 主流程
def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    update_main_sheet(df)
    print("✅ Google Sheets 已更新")

if __name__ == "__main__":
    main()
