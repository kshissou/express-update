import os
import requests
import urllib3
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# 本地运行才加载dotenv
if os.getenv("RUN_LOCAL") == "1":
    from dotenv import load_dotenv
    load_dotenv()

# 关闭 SSL 证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 获取环境变量
cookie = os.environ["YUANRI_COOKIE"]
google_credentials = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])

# 获取 Google Sheets 客户端
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(google_credentials, scopes=scopes)
    gc = gspread.authorize(credentials)
    return gc

# 抓取网页并解析包裹数据
def fetch_packages():
    url = "https://www.yuanriguoji.com/Package/Package_Select_Package.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookie
    }
    response = requests.get(url, headers=headers, verify=False)
    soup = BeautifulSoup(response.content, "html.parser")

    packages = []
    rows = soup.find_all("tr", class_="Grid_Row_Style")

    for row in rows:
        billcode_span = row.find("span", {"name": "BillCode"})
        if not billcode_span:
            continue
        billcode = billcode_span.text.strip()

        tds = row.find_all("td")
        weight = tds[7].text.strip().replace("kg", "") if len(tds) >= 8 else ""

        arrival_time = ""
        next_p = row.find_next("p", class_="more_massage Hide_12123113")
        if next_p:
            spans = next_p.find_all("span")
            if len(spans) >= 2 and "到库时间" in spans[0].text:
                arrival_time = spans[1].text.strip()

        packages.append({
            "快递单号": billcode,
            "重量（kg）": weight,
            "到货时间": arrival_time
        })

    return pd.DataFrame(packages)

# 更新 Google Sheets 表格
def update_main_sheet(new_df):
    gc = get_gsheet_client()
    sheet = gc.open("express-claim-app").worksheet("主表")
    existing_data = sheet.get_all_records()
    existing_df = pd.DataFrame(existing_data)

    if "快递单号" not in existing_df.columns:
        print("❌ 表格中未找到 '快递单号' 列")
        return

    existing_df["快递单号"] = existing_df["快递单号"].astype(str)
    new_df["快递单号"] = new_df["快递单号"].astype(str)

    new_tracking_numbers = set(new_df["快递单号"])
    existing_tracking_numbers = set(existing_df["快递单号"])

    print(f"📦 抓取到的所有单号： {sorted(list(new_tracking_numbers))}")
    print(f"📄 表中已有单号： {sorted(list(existing_tracking_numbers))}")

    to_add = new_df[~new_df["快递单号"].isin(existing_tracking_numbers)]

    if to_add.empty:
        print("📭 没有新增记录，跳过更新 ✅")
    else:
        print(f"✅ 已新增 {len(to_add)} 条记录，并更新 Google Sheets ✅")
        combined_df = pd.concat([existing_df, to_add], ignore_index=True)
        sheet.clear()
        sheet.update([combined_df.columns.tolist()] + combined_df.values.tolist())

def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    if df.empty:
        print("⚠️ 未抓取到任何记录，请检查 Cookie 或页面结构")
    else:
        update_main_sheet(df)
        print("✅ Google Sheets 已更新")

if __name__ == "__main__":
    main()
