# -*- coding: utf-8 -*-
"""
臺灣證券交易所 (TWSE) 發行量加權股價指數歷史資料抓取與更新程式
抓取區間：民國 114 年 1 月 1 日 (2025/01/01) 至今日 (動態取當天日期)
API 端點：https://www.twse.com.tw/indicesReport/MI_5MINS_HIST
儲存目標：SQLite 資料庫 "股市資料庫.db" 中的 "大盤資料表"

支援功能：
1. 完整全量歷史資料補齊 (fetch_twse_taiex)
2. 最近一個星期增量資料更新 (update_recent_week_taiex)：只抓取一星期內缺少的交易日並追加新增到大盤資料表
"""

import time
import datetime
import sqlite3
import argparse
import sys
import requests
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB_FILE = "股市資料庫.db"
TABLE_NAME = "大盤資料表"

def clear_market_table(db_path=DB_FILE, table_name=TABLE_NAME):
    """清空指定之 SQLite 大盤資料表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
    conn.commit()
    conn.close()
    print(f"已清空資料庫 [{db_path}] 中的 [{table_name}] 資料表。")

def save_to_sqlite(df, db_path=DB_FILE, table_name=TABLE_NAME):
    """
    將大盤歷史資料儲存/更新至 SQLite 資料庫。
    """
    if df is None or df.empty:
        print("沒有資料可寫入資料庫。")
        return 0
        
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
    
    cursor.execute(f'SELECT COUNT(*), MIN(民國日期), MAX(民國日期) FROM "{table_name}"')
    total_count, min_date, max_date = cursor.fetchone()
    conn.close()
    
    print(f"SQLite 寫入成功：資料庫 [{db_path}] / 資料表 [{table_name}]")
    print(f"本次寫入/更新：{len(records)} 筆，資料表累計總筆數：{total_count} 筆 (區間: 民國 {min_date} ~ 民國 {max_date})")
    return len(records)

def update_recent_week_taiex(db_path=DB_FILE, table_name=TABLE_NAME):
    """
    檢查 Table 大盤資料表 最近一個星期 (7天內) 沒有的 Data，
    連線至 TWSE 抓取後，新增寫入到 Table 大盤資料表。
    """
    today = datetime.date.today()
    one_week_ago = today - datetime.timedelta(days=7)
    
    print("=" * 55)
    print("【執行增量更新】開始檢查 Table [大盤資料表] 近一星期缺失數據")
    print(f"今日日期（動態）：{today.strftime('%Y-%m-%d')} (民國 {today.year - 1911} 年 {today.month:02d} 月 {today.day:02d} 日)")
    print(f"檢查範圍（近一星期）：{one_week_ago.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}")
    print("=" * 55)
    
    # 1. 查詢資料庫中近一星期已存在的日期
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    cursor.execute(f'SELECT 西元日期 FROM "{table_name}" WHERE 西元日期 >= ?;', (one_week_ago.strftime("%Y-%m-%d"),))
    existing_dates = set(row[0] for row in cursor.fetchall())
    conn.close()
    
    print(f"資料庫中近一星期已有之日期 ({len(existing_dates)} 天):", sorted(list(existing_dates)))
    
    # 2. 計算需要向 TWSE 查詢的月份 (若近 7 天跨月，則抓取這兩個月份)
    target_months = []
    curr = datetime.date(one_week_ago.year, one_week_ago.month, 1)
    while curr <= today:
        target_months.append(curr.strftime("%Y%m01"))
        if curr.month == 12:
            curr = datetime.date(curr.year + 1, 1, 1)
        else:
            curr = datetime.date(curr.year, curr.month + 1, 1)
            
    # 3. 發起請求向 TWSE 抓取
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    new_records = []
    for month_str in target_months:
        url = f"https://www.twse.com.tw/indicesReport/MI_5MINS_HIST?response=json&date={month_str}"
        try:
            resp = session.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("stat") == "OK" and "data" in data:
                    for row in data["data"]:
                        parts = row[0].split("/")
                        if len(parts) == 3:
                            y_ad = int(parts[0]) + 1911
                            m_val = int(parts[1])
                            d_val = int(parts[2])
                            row_dt = datetime.date(y_ad, m_val, d_val)
                            row_iso = row_dt.strftime("%Y-%m-%d")
                            
                            # 條件：在近一星期範圍內，且資料庫目前「沒有」這筆 Data
                            if one_week_ago <= row_dt <= today and row_iso not in existing_dates:
                                new_records.append({
                                    "民國日期": row[0],
                                    "西元日期": row_iso,
                                    "開盤指數": float(row[1].replace(",", "")),
                                    "最高指數": float(row[2].replace(",", "")),
                                    "最低指數": float(row[3].replace(",", "")),
                                    "收盤指數": float(row[4].replace(",", ""))
                                })
        except Exception as e:
            print(f"抓取 {month_str} 異常: {e}")
            
    if new_records:
        df_new = pd.DataFrame(new_records)
        df_new.drop_duplicates(subset=["西元日期"], inplace=True)
        df_new.sort_values(by="西元日期", inplace=True)
        print(f"\n[發現新資料] 找到 Table [大盤資料表] 一星期內沒有的 Data 共 {len(df_new)} 筆：")
        print(df_new.to_string(index=False))
        
        # 寫入 SQLite Table 大盤資料表
        inserted_count = save_to_sqlite(df_new, db_path=db_path, table_name=table_name)
        
        # 4. 同步呼叫產生器，更新 mitake_fund_desktop.html, index.html, code_artifact.html
        try:
            import generate_mitake_desktop
            generate_mitake_desktop.generate_desktop_html()
            print("已同步更新 mitake_fund_desktop.html、index.html 與 code_artifact.html！")
        except Exception as e:
            print(f"產生 HTML 看盤工作站時發生提醒: {e}")
            
        return {
            "status": "success",
            "message": f"成功新增 {len(df_new)} 筆大盤最新數據至資料庫！",
            "new_count": len(df_new),
            "new_dates": df_new["西元日期"].tolist(),
            "latest_record": df_new.iloc[-1].to_dict()
        }
    else:
        print("\n[檢查完成] Table [大盤資料表] 近一星期內之開盤日資料已全部齊全，無缺少 Data！")
        return {
            "status": "up_to_date",
            "message": "近一星期內之大盤資料已為最新，無需新增！",
            "new_count": 0,
            "new_dates": []
        }

def fetch_twse_taiex(start_date_str="2025-01-01", end_date_str=None, db_path=DB_FILE, table_name=TABLE_NAME, clear_table=False, delay=2.0):
    """
    抓取 TWSE 發行量加權股價指數歷史資料 (全量模式)。
    """
    if clear_table:
        clear_market_table(db_path, table_name)
        
    start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_dt = datetime.date.today() if end_date_str is None else datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    current_dt = datetime.date(start_dt.year, start_dt.month, 1)
    target_months = []
    while current_dt <= end_dt:
        target_months.append(current_dt.strftime("%Y%m01"))
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
    for idx, month_str in enumerate(target_months, start=1):
        year_tw = int(month_str[:4]) - 1911
        month = int(month_str[4:6])
        url = f"https://www.twse.com.tw/indicesReport/MI_5MINS_HIST?response=json&date={month_str}"
        print(f"[{idx}/{len(target_months)}] 抓取 {year_tw} 年 {month:02d} 月資料 (date={month_str})...", end=" ", flush=True)
        
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
                        print(f"成功，取得 {len(month_data)} 筆。")
                        for row in month_data:
                            date_parts = row[0].split("/")
                            if len(date_parts) == 3:
                                y_ad = int(date_parts[0]) + 1911
                                m_val = int(date_parts[1])
                                d_val = int(date_parts[2])
                                row_dt = datetime.date(y_ad, m_val, d_val)
                                
                                if start_dt <= row_dt <= end_dt:
                                    all_records.append({
                                        "民國日期": row[0],
                                        "西元日期": row_dt.strftime("%Y-%m-%d"),
                                        "開盤指數": float(row[1].replace(",", "")),
                                        "最高指數": float(row[2].replace(",", "")),
                                        "最低指數": float(row[3].replace(",", "")),
                                        "收盤指數": float(row[4].replace(",", ""))
                                    })
                        break
                    else:
                        print(f"查無資料或回傳狀態非 OK: {data.get('stat')}")
                        break
                else:
                    print(f"HTTP 錯誤碼: {resp.status_code}")
            except Exception as e:
                print(f"發生異常: {e}")
                time.sleep(2)
                
        if idx < len(target_months):
            time.sleep(delay)
            
    df = pd.DataFrame(all_records)
    if not df.empty:
        df.drop_duplicates(subset=["西元日期"], inplace=True)
        df.sort_values(by="西元日期", inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        save_to_sqlite(df, db_path=db_path, table_name=table_name)
        return df
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TWSE 大盤資料抓取與更新工具")
    parser.add_argument("--recent", action="store_true", help="只檢查並更新最近一星期缺失之大盤資料")
    args = parser.parse_args()
    
    if args.recent:
        update_recent_week_taiex()
    else:
        # 全量模式
        fetch_twse_taiex(start_date_str="2025-01-01", end_date_str=None, clear_table=True, delay=2.0)
