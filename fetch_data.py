import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# ==== 配置 ====
SPREADSHEET_NAME = "express-claim-app"
MAIN_SHEET = "Sheet1"
URL = "http://www.yuanriguoji.com/Phone/Package?WaveHouse=0&Prediction=2&Storage=0&Grounding=0&active=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": (
        "ClientData=eyJDbGllbnRJbmZvIjp7IklEIjo0OTQ1NzcsIk5hbWUiOiI6RGl2ZW7wn5KtIiwiTGV2ZWwiOjIwMDU3LCJMZXZlbE5hbWUiOiLmma7pgJrkvJrlkZgiLCJHcm91cCI6NDksIkdyb3VwTmFtZSI6IuWFrOWPuOS4muWKoSIsIlNob3AiOjEwMDYwLCJTaG9wTmFtZSI6IuS4iua1t+a6kOaXpei0p+i/kOS7o+eQhuaciemZkOWFrOWPuCIsIlBlcnNvbm5lbCI6MTAzMjAsIlBlcnNvbm5lbE5hbWUiOiLokovlsI/oirMiLCJPcGVuSUQiOiJvamVTZndFLWZxaUttUHdJcVJSVXFZclZEbWlJIiwiTGluZUlEIjpudWxsLCJGYXJlQm9va0lEIjpudWxsLCJVaWQiOiI0OTQ1NzciLCJTZXgiOiLnlLciLCJQaG9uZSI6IiIsIlRlbCI6bnVsbCwiRW1haWwiOiIiLCJDcmVkaXQiOjAuMDAsIk1vbmV5IjowLjAwLCJBbGxNb25leSI6MTIwOC4wMCwiQ2FzaE1vbmV5IjowLjAwLCJJbnRlZ3JhbCI6MC4wMCwiRGlzY291bnQiOjEuMDAsIlNvdXJjZSI6IuW+ruS/oeiHquWKqOazqOWGjCIsIkltYWdlIjoiaHR0cHM6Ly90aGlyZHd4LnFsb2dvLmNuL21tb3Blbi92aV8zMi9EWUFJT2dxODNlcHhGRmJTQlRtZXJlMTc0U0VjUmdkc2Ewd3J5b2cwVmxGVEV2emxNcUl3ZUZ6QVJDWnhhSjd3MFZUdzZ1UHR1YUlYamJkS2xVRk1GZXprNWRrRFNydE8zMjhXa24ycmoyam12b2lhVzFpYmhkNWcvMTMyIiwiUGFzc1dvcmQiOiJGNTlCRDY1RjdFREFGQjA4N0E4MUQ0RENBMDZDNDkxMCIsIlJlY29tbWVuZGVyIjowLCJSZWNvbW1lbmRlck5hbWUiOm51bGwsIkFnZW50SUQiOjAsIkFnZW50TmFtZSI6bnVsbCwiQ3JlYXRlVGltZSI6IjIwMjMtMDgtMTAgMTM6MzU6MDAiLCJMb2dpblRpbWUiOiIyMDI1LTA1LTE3IDE0OjQ1OjQ1IiwiQWN0aXZpdHlUaW1lIjoiMjAyNC0xMC0xMCAxMDo0NDozNCIsIkxvZ2luSVAiOiI2MC42NS4xNjkuMjM0IiwiT3JkZXJDb3VudCI6MywiT3JkZXJXZWlnaHQiOjYwLjAwLCJPcmRlck1vbmV5IjoxMjA4LjAwLCJXeEJpbmRTdGF0ZSI6dHJ1ZSwiTGluZUJpbmRTdGF0ZSI6ZmFsc2UsIlJlbSI6bnVsbCwiU3RhdGUiOjAsIlN0YXRlTmFtZSI6IuWPr+eUqCIsIk1pbmlPcGVuSWQiOm51bGwsIld4VW5pb25JZCI6bnVsbCwiQ2hhbmdlU3RhdGUiOjB9LCJDb3Vwb25fVXNhYmxlIjowLCJDb3Vwb25fSW52YWxpZCI6OSwiTm90X0Fycml2ZWQiOjAsIkFycml2ZWQiOjI4LCJOb3RfU2lnbiI6MCwiTm9QYXlDb3VudCI6MH0=;"
        "LoginData=eyJQbGF0Rm9ybSI6MjIsIlNob3AiOjEwMDYwLCJVaWQiOm51bGwsIlB3ZCI6bnVsbCwiTG9naW5JUCI6IjEzMy4xMDYuMjA0Ljk1IiwiTG9naW5Nb2RlIjpmYWxzZSwiT3BlbklEIjoib2plU2Z3RS1mcWlLbVB3SXFSUlVxWXJWRG1pSSIsIkxpbmVJRCI6bnVsbCwiRmFyZUJvb2tJRCI6bnVsbCwiTmFtZSI6IuOBj+OBhSIsIkhlYWRVcmwiOiJodHRwczovL3RoaXJkd3gucWxvZ28uY24vbW1vcGVuL3ZpXzMyL0RZQUlPZ3E4M2VweEZGYlNCVG1lcmUxNzRTRWNSZ2RzYTB3cnlvZzBWbEZURXZ6bE1xSXdlRnpBUkNaeGFKN3cwVlR3NnVQdHVhSVhqYmRLbFVGTUZlems1ZGtEU3J0TzMyOFdrbjJyajJqbXZvaWFXMWliaGQ1Zy8xMzIiLCJTZXgiOiLnlLciLCJSZWNvbW1lbmRlciI6MCwiQWdlbnRJRCI6MCwiUGVyc29ubmVsIjowLCJNaW5pT3BlbklkIjpudWxsLCJXeFVuaW9uSWQiOm51bGx9; "
        "OpenID=eyJvcGVuaWQiOiJvamVTZndFLWZxaUttUHdJcVJSVXFZclZEbWlJIiwiYWNjZXNzX3Rva2VuIjoiOTJfMWd4YmdSd2ZWYXRSMVF4ZU92c3RmSGUxYXFvV0lfR21KSW50UG9GQmEydEJwMDhXSmpVOHJhWGR6RjFyZldmMWw3R2poNjZJS2xZZzJKdXkwT2RnOEtRLVh5aE92TWVCNWhVYU55LXBiV0kiLCJ1bmlvbmlkIjpudWxsfQ==; "
        "SplitPackage=W3siUGFja05vIjoxLCJCaWxsTGlzdCI6WzEyMDc3OTQxLDEyMDk1MDU3LDEyMTE5Nzc5LDEyMTIwNjU1LDEyMTIwNjg4LDEyMTIxNzQxLDEyMTIyMTcyLDEyMTIyMzY3LDEyMTIzMDk3LDEyMTIzMTEzLDEyMTI0NzQwLDEyMTI0OTY3LDEyMTI2NjQwLDEyMTI3NzcxLDEyMTI3NzgxLDEyMTMwOTU1LDEyMTMxNzYxLDEyMTMxODA1LDEyMTMxOTM3LDEyMTMzNzUyLDEyMTM1NTI5LDEyMTM1NTQ5LDEyMTM3NzQ0LDEyMTM4MTU4LDEyMTM5ODcxLDEyMTQxOTg4LDEyMTQ0NjEwLDEyMTM3ODU5XX1d; "
        "Users=eyJPcGVuSUQiOiJvamVTZndFLWZxaUttUHdJcVJSVXFZclZEbWlJIiwiUHVibGljSWQiOm51bGwsIlVzZXJJRCI6bnVsbCwiTmlja05hbWUiOiLjgY/jgYUiLCJTdWJzY3JpYmUiOjAsIkNvdW50cnkiOiIiLCJQcm92aW5jZSI6IiIsIkNpdHkiOiIiLCJDcmVhdGVEYXRlIjoiXC9EYXRlKC02MjEzNTU5NjgwMDAwMClcLyIsIkhlYWRpbWdVcmwiOiJodHRwczovL3RoaXJkd3gucWxvZ28uY24vbW1vcGVuL3ZpXzMyL0RZQUlPZ3E4M2VweEZGYlNCVG1lcmUxNzRTRWNSZ2RzYTB3cnlvZzBWbEZURXZ6bE1xSXdlRnpBUkNaeGFKN3cwVlR3NnVQdHVhSVhqYmRLbFVGTUZlems1ZGtEU3J0TzMyOFdrbjJyajJqbXZvaWFXMWliaGQ1Zy8xMzIiLCJVbmlvbklEIjpudWxsLCJVbl9TdWJzY3JpYmVfVGltZSI6IlwvRGF0ZSgtNjIxMzU1OTY4MDAwMDApXC8ifQ==; "
        "VirtualHouseData=W3siV2FyZUhvdXNlIjoxMDA0MSwiV2FyZUhvdXNlTmFtZSI6IuS4iua1t+S7k+W6kyjlhY3otLnku5PlgqgxODDlpKks6YC+5pyf6Ieq5Yqo6ZSA5q+BLOS8muWRmElE57yW5Y+35LiA5a6a6KaB5YaZ5Zyw5Z2A5Lit6Ze0ISkiLCJTaG9wIjoxMDA2MCwiU2hvcE5hbWUiOiLkuIrmtbfmupDml6XotKfov5Dku6PnkIbmnInpmZDlhazlj7giLCJTb3J0IjowLCJJRCI6MTAwNTIsIk5hbWUiOiLkuIrmtbfku5PlupMo5YWN6LS55LuT5YKoMTgw5aSp77yMMTgw5aSp5ZCO6ZSA5q+BLOS8muWRmElE57yW5Y+35LiA5a6a6KaB5YaZ5Zyw5Z2A5Lit6Ze0ISkiLCJDb3VudHJ5Ijo1MDA5LCJDb3VudHJ5TmFtZSI6IuS4reWbvSIsIlBlcnNvbiI6Iih7Q2xpZW50TmFtZX0pKHtDbGllbnRJRH0pIiwiUGhvbmUiOiIxOTExODgxODgwMyIsIlRlbCI6IjE5MTE4ODE4ODAzIiwiQXBpTmFtZSI6bnVsbCwiUHJvdmluY2UiOjg5MywiUHJvdmluY2VOYW1lIjoi5LiK5rW35biCIiwiQ2l0eSI6NzAxMSwiQ2l0eU5hbWUiOiLluILovpbljLoiLCJBcmVhIjo2ODkwOSwiQXJlYU5hbWUiOiLpnZLmtabljLoiLCJBZGRyZXNzIjoi5LiK5rW35biC6Z2S5rWm5Yy655m96bmk6ZWHKHtDbGllbnRJRH3kuI3lhplJROWPt+eggeaLkuaUtuWMheijuSnpuaTnpaXot68yN+WPt0HljLoiLCJQb3N0Q29kZSI6IjIwMTcwOSIsIkZyZWVEYXkiOjE4MCwiRm9ybXVsYSI6IiIsIlJlbSI6IuWuouaIt+S9v+eUqOatpOWcsOWdgOmbhui0p+WMheijueWFpeW6k0lE5Y+356CB5YaZ5Zyw5Z2A5Lit6Ze0ICIsIkNoYW5nZVN0YXRlIjowfV0=; "
        "zh_choose=t; "
        "__RequestVerificationToken=D8jRgdRNA2qhNyPo7MweU6AtSghUaC94Foehzt9uWM6LfAq9XoxFA6_M_H5WmVAJpqlxFXckhmsvrncfV4XxyXFg1YnhvP_UgPMW8IaECJo1"
    )

}
# ==============

# 获取 Google Sheets 客户端
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
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

# 更新主表（保留旧数据，仅添加新记录）
def update_main_sheet(new_df):
    client = get_gsheet()
    sheet = client.open(SPREADSHEET_NAME).worksheet(MAIN_SHEET)

    if new_df.empty:
        print("⚠️ 没有抓到任何快递数据，跳过更新。")
        return False

    old_data = sheet.get_all_records()
    old_df = pd.DataFrame(old_data)

    new_df["快递单号"] = new_df["快递单号"].astype(str)

    if not old_df.empty:
        old_df["快递单号"] = old_df["快递单号"].astype(str)
        existing_ids = set(old_df["快递单号"])
        new_rows = new_df[~new_df["快递单号"].isin(existing_ids)]

        if new_rows.empty:
            print("📭 没有新增记录，跳过更新 ✅")
            return False

        updated_df = pd.concat([old_df, new_rows], ignore_index=True)
        print(f"🆕 本次新增 {len(new_rows)} 条记录")
    else:
        updated_df = new_df
        print(f"🆕 表为空，本次写入 {len(new_df)} 条记录")

    sheet.clear()
    sheet.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())
    return True

# 主流程
def main():
    print("🚚 抓取快递数据中...")
    df = fetch_packages()
    print(f"📦 共获取 {len(df)} 条快递记录")
    updated = update_main_sheet(df)
    if updated:
        print("✅ Google Sheets 已更新")

if __name__ == "__main__":
    main()
