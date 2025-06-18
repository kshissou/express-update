import os
import re
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def fetch_packages():
    print("🚚 抓取快递数据中...")

    url = "https://www.yuanriguoji.com/Package/Package_Select_Package.aspx"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": os.environ["YUANRI_COOKIE"]
    }

    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'

    if response.status_code != 200:
        print(f"❌ 页面请求失败，状态码：{response.status_code}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr", attrs={"class": "gridview_items"})

    data = []
    for row in rows:
        tracking_tag = row.find("span", attrs={"name": "BillCode"})
        weight_tag = row.find_all("td")[8]  # 重量在第9列（从0开始）
        arrival_tag = row.find("span", class_="SpanTitleLang", string="到库时间")

        if tracking_tag:
            tracking = tracking_tag.text.strip()
            try:
                weight = float(weight_tag.text.strip().replace("kg", "").strip())
            except:
                weight = ""
            # 查找相邻的到库时间
            arrival_time = ""
            if arrival_tag:
                span_text = arrival_tag.find_next_sibling("span", class_="SpanTextLang")
                if span_text:
                    arrival_time = span_text.text.strip()
            data.append({
                "快递单号": tracking,
                "重量（kg）": weight,
                "谁的快递": "",
                "到库时间": arrival_time
            })

    df = pd.DataFrame(data)
    print(f"📦 共获取 {len(df)} 条快递记录")
    return df

def get_gsheet():
    json_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
    credentials_dict = json.loads(json_str)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

def update_main_sheet(new_df):
    if new_df.empty:
        print("⚠️ 未抓取到任何记录，请检查 Cookie 或页面结构")
        return

    gc = get_gsheet()
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1F28X2UHHb7iCVJWZ1FO4X7-FRkUrRhsikZ3BFmFZr5o/edit")
    worksheet = sh.sheet1
    data = worksheet.get_all_records()
    old_df = pd.DataFrame(data)
    old_df["快递单号"] = old_df["快递单号"].astype(str)

    new_df["快递单号"] = new_df["快递单号"].astype(str)
    existing_ids = set(old_df["快递单号"])
    all_ids = set(new_df["快递单号"])

    print(f"📦 抓取到的所有单号： {list(new_df['快递单号'])}")
    print(f"📄 表中已有单号： {list(old_df['快递单号'])}")

    new_entries = new_df[~new_df["快递单号"].isin(existing_ids)]
    if new_entries.empty:
        print("📭 没有新增记录，跳过更新 ✅")
    else:
        updated_df = pd.concat([old_df, new_entries], ignore_index=True)
        worksheet.clear()
        worksheet.update([updated_df.columns.tolist()] + updated_df.values.tolist())
        print(f"✅ 已新增 {len(new_entries)} 条记录，并更新 Google Sheets ✅")

    print("✅ Google Sheets 已更新")

def main():
    df = fetch_packages()
    update_main_sheet(df)

if __name__ == "__main__":
    main()
