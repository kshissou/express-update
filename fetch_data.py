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
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": os.environ["YUANRI_COOKIE"]
    }
    res = requests.get(URL, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    inputs = soup.find_all("input", class_="chk_select")

    records = []
    for tag in inputs:
        pkg_id = tag.get("value")
        weight = tag.get("data-weight", "0")
        span = soup.find("span", {"name": "BillCode", "data-id": pkg_id})
        if span:
            tracking = span.text.strip()
            records.append({
                "快递单号": tracking,
                "重量（kg）": weight,
                "谁的快递": ""
            })
    return pd.DataFrame(records)

# 更新主表（只添加新记录）
def update_main_sheet(new_df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    existing = pd.DataFrame(sheet.get_all_records())

    if existing.empty:
        print("📄 表为空，首次写入数据")
        sheet.update([new_df.columns.values.tolist()] + new_df.values.tolist())
        return

    existing["快递单号"] = existing["快递单号"].astype(str)
    new_df["快递单号"] = new_df["快递单号"].astype(str)

    # 打印调试信息
    print("📦 抓取到的所有单号：", new_df["快递单号"].tolist())
    print("📄 表中已有单号：", existing["快递单号"].tolist())

    merged_df = pd.concat([existing, new_df[~new_df["快递单号"].isin(existing["快递单号"])]], ignore_index=True)
    if len(merged_df) == len(existing):
        print("📭 没有新增记录，跳过更新 ✅")
        return

    print(f"📥 新增记录数：{len(merged_df) - len(existing)}")
    sheet.clear()
    sheet.update([merged_df.columns.values.tolist()] + merged_df.values.tolist())

# 主流程
def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    update_main_sheet(df)
    print("✅ Google Sheets 已更新")

if __name__ == "__main__":
    main()
