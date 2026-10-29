# -*- coding: utf-8 -*-
"""
臺灣證券交易所 (TWSE) 發行量加權股價指數歷史資料抓取程式
抓取區間：民國 114 年 1 月 1 日 (2025/01/01) 至今日 (動態取當天日期)
API 端點：https://www.twse.com.tw/indicesReport/MI_5MINS_HIST
儲存目標：SQLite 資料庫 "股市資料庫.db" 中的 "大盤資料表"
"""

import time
import datetime
import sqlite3
import requests
import pandas as pd

def clear_market_table(db_path="股市資料庫.db", table_name="大盤資料表"):
    """清空指定之 SQLite 大盤資料表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
    conn.commit()
    conn.close()
    print(f"已清空資料庫 [{db_path}] 中的 [{table_name}] 資料表。")

def save_to_sqlite(df, db_path="股市資料庫.db", table_name="大盤資料表"):
    """
    將大盤歷史資料儲存/更新至 SQLite 資料庫。
    
    :param df: 包含大盤資料的 pandas DataFrame
    :param db_path: SQLite 資料庫檔案路徑，預設為 '股市資料庫.db'
    :param table_name: 資料表名稱，預設為 '大盤資料表'
    """
    if df is None or df.empty:
        print("沒有資料可寫入資料庫。")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 建立資料表 (西元日期作為 PRIMARY KEY，避免重複寫入)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            西元日期 TEXT PRIMARY KEY,
            民國日期 TEXT,
            開盤指數 REAL,
            最高指數 REAL,
            最低指數 REAL,
            收盤指數 REAL
        )
    """)
    
    # 使用 INSERT OR REPLACE 進行冪等寫入（若已存在相同日期則更新數值）
    insert_sql = f"""
        INSERT OR REPLACE INTO "{table_name}" (西元日期, 民國日期, 開盤指數, 最高指數, 最低指數, 收盤指數)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    records = [
        (
            str(row["西元日期"]),
            str(row["民國日期"]),
            float(row["開盤指數"]),
            float(row["最高指數"]),
            float(row["最低指數"]),
            float(row["收盤指數"])
        )
        for _, row in df.iterrows()
    ]
    
    cursor.executemany(insert_sql, records)
    conn.commit()
    
    # 查詢目前資料表總筆數與日期起訖
    cursor.execute(f'SELECT COUNT(*), MIN(民國日期), MAX(民國日期) FROM "{table_name}"')
    total_count, min_date, max_date = cursor.fetchone()
    conn.close()
    
    print(f"SQLite 寫入成功：資料庫 [{db_path}] / 資料表 [{table_name}]")
    print(f"本次寫入/更新：{len(records)} 筆，資料表累計總筆數：{total_count} 筆 (區間: 民國 {min_date} ~ 民國 {max_date})")


def fetch_twse_taiex(start_date_str="2025-01-01", end_date_str=None, db_path="股市資料庫.db", table_name="大盤資料表", clear_table=False, delay=2.0):
    """
    抓取 TWSE 發行量加權股價指數歷史資料並存入 CSV、Excel 與 SQLite 資料庫。
    
    :param start_date_str: 起始日期字串 (格式: YYYY-MM-DD)，預設為 '2025-01-01' (民國 114 年 1 月 1 日)
    :param end_date_str: 結束日期字串 (格式: YYYY-MM-DD)，若為 None 則自動取系統當日 (今日)
    :param db_path: SQLite 資料庫路徑
    :param table_name: SQLite 資料表名稱
    :param clear_table: 抓取寫入前是否清空資料表
    :param delay: 每次請求間隔秒數
    """
    if clear_table:
        clear_market_table(db_path, table_name)
        
    # 解析起始日期
    start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    
    # 動態取得今日日期 (若未指定結束日，則取執行當天的最新日期)
    if end_date_str is None:
        end_dt = datetime.date.today()
    else:
        end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    # 產生月份列表 (YYYYMM01)
    current_dt = datetime.date(start_dt.year, start_dt.month, 1)
    target_months = []
    while current_dt <= end_dt:
        target_months.append(current_dt.strftime("%Y%m01"))
        # 前進至下個月
        if current_dt.month == 12:
            current_dt = datetime.date(current_dt.year + 1, 1, 1)
        else:
            current_dt = datetime.date(current_dt.year, current_dt.month + 1, 1)
            
    start_tw_str = f"{start_dt.year - 1911}{start_dt.month:02d}{start_dt.day:02d}"
    end_tw_str = f"{end_dt.year - 1911}{end_dt.month:02d}{end_dt.day:02d}"
    
    print(f"==================================================")
    print(f"開始抓取 TWSE 發行量加權股價指數歷史資料")
    print(f"資料庫：{db_path}，資料表：{table_name}")
    print(f"今日日期（動態）：民國 {end_dt.year - 1911} 年 {end_dt.month:02d} 月 {end_dt.day:02d} 日 ({end_dt.strftime('%Y-%m-%d')})")
    print(f"查詢區間：民國 {start_dt.year - 1911} 年 {start_dt.month:02d} 月 {start_dt.day:02d} 日 ~ 民國 {end_dt.year - 1911} 年 {end_dt.month:02d} 月 {end_dt.day:02d} 日")
    print(f"預計抓取月份數：{len(target_months)} 個月份")
    print(f"==================================================")
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    all_records = []
    fields = ["日期", "開盤指數", "最高指數", "最低指數", "收盤指數"]
    
    for idx, month_str in enumerate(target_months, start=1):
        year_tw = int(month_str[:4]) - 1911
        month = int(month_str[4:6])
        url = f"https://www.twse.com.tw/indicesReport/MI_5MINS_HIST?response=json&date={month_str}"
        print(f"[{idx}/{len(target_months)}] 抓取 {year_tw} 年 {month:02d} 月資料 (date={month_str})...", end=" ", flush=True)
        
        success = False
        for retry in range(1, 4):
            try:
                resp = session.get(url, headers=headers, timeout=15)
                if resp.status_code == 429:
                    print(f"[頻率限制 429] 暫停 6 秒重試 ({retry}/3)...", end=" ", flush=True)
                    time.sleep(6)
                    continue
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("stat") == "OK" and "data" in data:
                        month_data = data["data"]
                        if "fields" in data:
                            fields = data["fields"]
                        print(f"成功，取得 {len(month_data)} 筆。")
                        for row in month_data:
                            # row: [日期(民國), 開盤, 最高, 最低, 收盤]
                            date_parts = row[0].split("/")
                            if len(date_parts) == 3:
                                y_ad = int(date_parts[0]) + 1911
                                m_val = int(date_parts[1])
                                d_val = int(date_parts[2])
                                row_dt = datetime.date(y_ad, m_val, d_val)
                                
                                # 篩選在起訖範圍內 (包含今日)
                                if start_dt <= row_dt <= end_dt:
                                    all_records.append({
                                        "民國日期": row[0],
                                        "西元日期": row_dt.strftime("%Y-%m-%d"),
                                        "開盤指數": float(row[1].replace(",", "")),
                                        "最高指數": float(row[2].replace(",", "")),
                                        "最低指數": float(row[3].replace(",", "")),
                                        "收盤指數": float(row[4].replace(",", ""))
                                    })
                        success = True
                        break
                    else:
                        print(f"查無資料或回傳狀態非 OK: {data.get('stat')}")
                        success = True
                        break
                else:
                    print(f"HTTP 錯誤碼: {resp.status_code}")
            except Exception as e:
                print(f"發生異常: {e}")
                time.sleep(2)
                
        # TWSE 防爬蟲機制：請求間隔 delay 秒
        if idx < len(target_months):
            time.sleep(delay)
            
    df = pd.DataFrame(all_records)
    if not df.empty:
        # 依日期排序並去除重複
        df.drop_duplicates(subset=["西元日期"], inplace=True)
        df.sort_values(by="西元日期", inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        # 動態存檔檔名，反映實際抓取的起訖日期
        csv_filename = f"加權股價指數歷史資料_{start_tw_str}_{end_tw_str}.csv"
        excel_filename = f"加權股價指數歷史資料_{start_tw_str}_{end_tw_str}.xlsx"
        
        # 輸出 UTF-8-SIG 讓 Excel 直接開啟不會亂碼
        df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
        df.to_excel(excel_filename, index=False)
        
        print("\n================ 抓取完成 ================")
        print(f"總共取得 {len(df)} 筆交易日資料")
        print(f"資料起訖：{df['民國日期'].iloc[0]} ~ {df['民國日期'].iloc[-1]}")
        print(f"CSV 存檔位置：{csv_filename}")
        print(f"Excel 存檔位置：{excel_filename}")
        
        # 寫入 SQLite 資料庫「股市資料庫.db」的「大盤資料表」
        save_to_sqlite(df, db_path=db_path, table_name=table_name)
        
        print("\n最新 5 筆大盤指數資料預覽：")
        print(df.tail(5).to_string(index=False))
        return df
    else:
        print("未抓取到任何資料。")
        return None

if __name__ == "__main__":
    # 執行前清空資料表，並抓取民國 114 年 1 月 1 日 (2025-01-01) 起至今日 (動態變數)
    fetch_twse_taiex(start_date_str="2025-01-01", end_date_str=None, db_path="股市資料庫.db", table_name="大盤資料表", clear_table=True, delay=2.0)
