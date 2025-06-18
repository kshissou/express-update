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
    print("🚚 抓取快递数据中...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": os.environ["YUANRI_COOKIE"]
    }
    res = requests.get(URL, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select("table tr")

    records = []
    for row in rows:
        billcode_span = row.find("span", attrs={"name": "BillCode"})
        if billcode_span:
            tracking = billcode_span.text.strip()
            weight_td = row.find("td", attrs={"data-weight": True})
            weight = weight_td.get("data-weight", "0") if weight_td else "0"
            records.append({
                "快递单号": tracking,
                "重量（kg）": weight,
                "谁的快递": ""
            })

    df = pd.DataFrame(records)
    print(f"📦 共获取 {len(df)} 条快递记录")
    return df

# 更新主表
def update_main_sheet(new_df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    records = sheet.get_all_records()
    existing_df = pd.DataFrame(records)

    # 确保字段格式一致
    if not existing_df.empty:
        existing_df["快递单号"] = existing_df["快递单号"].astype(str)
    new_df["快递单号"] = new_df["快递单号"].astype(str)

    existing_tracking = set(existing_df["快递单号"].tolist()) if not existing_df.empty else set()
    new_entries = new_df[~new_df["快递单号"].isin(existing_tracking)]

    print("📦 抓取到的所有单号：", new_df["快递单号"].tolist())
    print("📄 表中已有单号：", list(existing_tracking))

    if new_entries.empty:
        print("📭 没有新增记录，跳过更新 ✅")
        return

    combined_df = pd.concat([existing_df, new_entries], ignore_index=True)
    sheet.clear()
    sheet.update([combined_df.columns.values.tolist()] + combined_df.values.tolist())
    print(f"✅ Google Sheets 已更新，新增 {len(new_entries)} 条记录")

# 主流程
def main():
    df = fetch_packages()
    update_main_sheet(df)

if __name__ == "__main__":
    main()
