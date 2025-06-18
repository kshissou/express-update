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
    creds_dict = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        json.dump(creds_dict, tmp)
        tmp.flush()
        creds = Credentials.from_service_account_file(tmp.name, scopes=scopes)
    client = gspread.authorize(creds)
    return client

# 抓取快递数据
def fetch_packages():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    spans = soup.find_all("span", {"name": "BillCode"})

    records = []
    for span in spans:
        tracking = span.text.strip()
        if tracking:
            records.append({
                "快递单号": tracking,
                "重量（kg）": "",
                "谁的快递": ""
            })
    return pd.DataFrame(records)

# 更新主表
def update_main_sheet(new_df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    try:
        existing_df = pd.DataFrame(sheet.get_all_records())
    except Exception:
        existing_df = pd.DataFrame(columns=["快递单号", "重量（kg）", "谁的快递"])

    new_df["快递单号"] = new_df["快递单号"].astype(str)
    existing_df["快递单号"] = existing_df["快递单号"].astype(str)

    new_tracking = set(new_df["快递单号"]) - set(existing_df["快递单号"])
    to_add = new_df[new_df["快递单号"].isin(new_tracking)]

    print(f"📦 抓取到的所有单号： {list(new_df['快递单号'])}")
    print(f"📄 表中已有单号： {list(existing_df['快递单号'])}")
    
    if to_add.empty:
        print("📭 没有新增记录，跳过更新 ✅")
        return

    updated_df = pd.concat([existing_df, to_add], ignore_index=True)
    sheet.clear()
    sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())
    print(f"✅ 已更新 Google Sheets，新增记录数：{len(to_add)}")

# 主流程
def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    update_main_sheet(df)

if __name__ == "__main__":
    main()
