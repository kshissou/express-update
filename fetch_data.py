import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import tempfile

SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"
URL = "http://www.yuanriguoji.com/Phone/Package?WaveHouse=0&Prediction=2&Storage=0&Grounding=0&active=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "http://www.yuanriguoji.com/",
    "Cookie": os.environ["YUANRI_COOKIE"]
}

def get_gsheet():
    json_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write(json_str)
        f.flush()
        creds = Credentials.from_service_account_file(f.name, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
    return gspread.authorize(creds)

def fetch_packages():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    records = []

    rows = soup.find_all("tr")
    for row in rows:
        input_tag = row.find("input", class_="chk_select")
        span_tag = row.find("span", {"name": "BillCode"})
        if input_tag and span_tag:
            tracking = span_tag.text.strip()
            weight = input_tag.get("data-weight", "0").strip()
            records.append({
                "快递单号": tracking,
                "重量（kg）": weight,
                "谁的快递": ""
            })

    return pd.DataFrame(records)

def update_main_sheet(new_df):
    if new_df.empty:
        print("⚠️ 未抓取到任何记录，请检查 Cookie 或页面结构")
        return

    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    existing_data = sheet.get_all_records()
    existing_df = pd.DataFrame(existing_data)

    new_df["快递单号"] = new_df["快递单号"].astype(str)
    existing_df["快递单号"] = existing_df["快递单号"].astype(str)

    print(f"📦 抓取到的所有单号： {list(new_df['快递单号'])}")
    print(f"📄 表中已有单号： {list(existing_df['快递单号'])}")

    merged_df = pd.merge(new_df, existing_df, on="快递单号", how="left", suffixes=("", "_old"))
    merged_df["谁的快递"] = merged_df["谁的快递_old"].fillna("")
    merged_df = merged_df[["快递单号", "重量（kg）", "谁的快递"]]

    new_records = merged_df[~merged_df["快递单号"].isin(existing_df["快递单号"])]

    if new_records.empty:
        print("📭 没有新增记录，跳过更新 ✅")
    else:
        sheet.clear()
        sheet.update([merged_df.columns.tolist()] + merged_df.values.tolist())
        print(f"✅ 已新增 {len(new_records)} 条记录并同步到 Google Sheets")

def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    update_main_sheet(df)
    print("✅ Google Sheets 已更新")

if __name__ == "__main__":
    main()
