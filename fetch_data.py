import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
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

def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write(creds_json)
        tmp.flush()
        creds = Credentials.from_service_account_file(tmp.name, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def fetch_packages():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select("table tr")

    records = []
    for row in rows:
        span = row.find("span", {"name": "BillCode"})
        input_tag = row.find("input", class_="chk_select")
        if span and input_tag:
            tracking = span.text.strip()
            weight = input_tag.get("data-weight", "0")
            records.append({
                "快递单号": tracking,
                "重量（kg）": weight,
                "谁的快递": ""
            })
    return pd.DataFrame(records)

def update_main_sheet(new_df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)
    old_df = pd.DataFrame(sheet.get_all_records())

    if not old_df.empty:
        old_df["快递单号"] = old_df["快递单号"].astype(str)
    new_df["快递单号"] = new_df["快递单号"].astype(str)

    existing = set(old_df["快递单号"]) if not old_df.empty else set()
    new_entries = new_df[~new_df["快递单号"].isin(existing)]

    print(f"📦 抓取到的所有单号： {new_df['快递单号'].tolist()}")
    print(f"📄 表中已有单号： {list(existing)}")

    if new_entries.empty:
        print("📭 没有新增记录，跳过更新 ✅")
    else:
        combined_df = pd.concat([old_df, new_entries], ignore_index=True)
        sheet.clear()
        sheet.update([combined_df.columns.tolist()] + combined_df.values.tolist())
        print(f"✅ 已新增 {len(new_entries)} 条记录并同步更新 Google Sheets ✅")

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
