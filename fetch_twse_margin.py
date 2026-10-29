# -*- coding: utf-8 -*-
"""
臺灣證券交易所 (TWSE) 信用交易融資融券餘額歷史資料抓取程式
抓取端點：https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN
儲存目標：SQLite 資料庫 "股市資料庫.db" 中的 "融資餘額" 資料表
抓取區間：民國 114 年 1 月 1 日 (2025/01/01) 起至今日 (動態變數)
"""

import time
import datetime
import sqlite3
import requests
import pandas as pd

DB_FILE = "股市資料庫.db"
TABLE_NAME = "融資餘額"

def init_db(db_path=DB_FILE, table_name=TABLE_NAME, clear_table=False):
    """
    初始化 SQLite 資料表，建立融資餘額資料表 (若不存在)。
    以西元日期作為 PRIMARY KEY，支援冪等性更新。
    
    :param clear_table: 若為 True，則在初始化前清空資料表所有內容。
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if clear_table:
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
        print(f"已清空資料庫 [{db_path}] 中的 [{table_name}] 資料表。")
        
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            西元日期 TEXT PRIMARY KEY,
            民國日期 TEXT,
            融資買進_張 INTEGER,
            融資賣出_張 INTEGER,
            融資現金償還_張 INTEGER,
            融資前日餘額_張 INTEGER,
            融資今日餘額_張 INTEGER,
            融券買進_張 INTEGER,
            融券賣出_張 INTEGER,
            融券現券償還_張 INTEGER,
            融券前日餘額_張 INTEGER,
            融券今日餘額_張 INTEGER,
            融資買進_仟元 INTEGER,
            融資賣出_仟元 INTEGER,
            融資現金償還_仟元 INTEGER,
            融資前日餘額_仟元 INTEGER,
            融資今日餘額_仟元 INTEGER,
            融資增減_仟元 INTEGER
        )
    """)
    conn.commit()
    conn.close()

def parse_num(val):
    """清洗數值字串並轉換為整數"""
    if val is None:
        return 0
    clean_str = str(val).replace(",", "").replace("--", "0").strip()
    try:
        return int(float(clean_str))
    except (ValueError, TypeError):
        return 0

def fetch_single_day_margin(date_obj, session=None, headers=None, max_retries=3):
    """
    抓取指定日期的 TWSE 信用交易統計 (大盤整體融資融券)。
    
    :param date_obj: datetime.date 物件
    :param session: requests.Session 物件
    :param headers: HTTP 標頭
    :param max_retries: 最大重試次數
    :return: dict 或 None (若為休市日或無資料)
    """
    date_str_num = date_obj.strftime("%Y%m%d")
    date_iso = date_obj.strftime("%Y-%m-%d")
    year_tw = date_obj.year - 1911
    date_tw = f"{year_tw}/{date_obj.month:02d}/{date_obj.day:02d}"
    
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str_num}&selectType=MS&response=json"
    req = session if session else requests
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = req.get(url, headers=headers, timeout=12)
            if resp.status_code == 429:
                print(f"[頻率限制 429] 等待 6 秒後重試 ({attempt}/{max_retries})...")
                time.sleep(6)
                continue
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            if data.get("stat") != "OK":
                return None
                
            tables = data.get("tables", [])
            if not tables or not tables[0].get("data"):
                return None
                
            rows = tables[0]["data"]
            if len(rows) < 3:
                return None
                
            m_shares = [parse_num(x) for x in rows[0][1:]]
            s_shares = [parse_num(x) for x in rows[1][1:]]
            m_amount = [parse_num(x) for x in rows[2][1:]]
            
            diff_amount = m_amount[4] - m_amount[3]
            
            return {
                "西元日期": date_iso,
                "民國日期": date_tw,
                "融資買進_張": m_shares[0],
                "融資賣出_張": m_shares[1],
                "融資現金償還_張": m_shares[2],
                "融資前日餘額_張": m_shares[3],
                "融資今日餘額_張": m_shares[4],
                "融券買進_張": s_shares[0],
                "融券賣出_張": s_shares[1],
                "融券現券償還_張": s_shares[2],
                "融券前日餘額_張": s_shares[3],
                "融券今日餘額_張": s_shares[4],
                "融資買進_仟元": m_amount[0],
                "融資賣出_仟元": m_amount[1],
                "融資現金償還_仟元": m_amount[2],
                "融資前日餘額_仟元": m_amount[3],
                "融資今日餘額_仟元": m_amount[4],
                "融資增減_仟元": diff_amount
            }
        except Exception as e:
            if attempt == max_retries:
                print(f"抓取 {date_iso} 發生異常: {e}")
                return None
            time.sleep(2)
    return None

def save_record_to_sqlite(record, db_path=DB_FILE, table_name=TABLE_NAME):
    """將單筆記錄寫入或更新至 SQLite 資料庫"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sql = f"""
        INSERT OR REPLACE INTO "{table_name}" (
            西元日期, 民國日期,
            融資買進_張, 融資賣出_張, 融資現金償還_張, 融資前日餘額_張, 融資今日餘額_張,
            融券買進_張, 融券賣出_張, 融券現券償還_張, 融券前日餘額_張, 融券今日餘額_張,
            融資買進_仟元, 融資賣出_仟元, 融資現金償還_仟元, 融資前日餘額_仟元, 融資今日餘額_仟元,
            融資增減_仟元
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(sql, (
        record["西元日期"], record["民國日期"],
        record["融資買進_張"], record["融資賣出_張"], record["融資現金償還_張"], record["融資前日餘額_張"], record["融資今日餘額_張"],
        record["融券買進_張"], record["融券賣出_張"], record["融券現券償還_張"], record["融券前日餘額_張"], record["融券今日餘額_張"],
        record["融資買進_仟元"], record["融資賣出_仟元"], record["融資現金償還_仟元"], record["融資前日餘額_仟元"], record["融資今日餘額_仟元"],
        record["融資增減_仟元"]
    ))
    conn.commit()
    conn.close()

def generate_target_weekdays(start_date_str="2025-01-01", end_date_str=None):
    """產生指定區間內的平日列表 (週一至週五)"""
    start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_dt = datetime.date.today() if end_date_str is None else datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    dates = []
    curr = start_dt
    while curr <= end_dt:
        if curr.weekday() < 5:  # 0~4 代表週一至週五
            dates.append(curr)
        curr += datetime.timedelta(days=1)
    return dates, end_dt

def fetch_and_save_margin_history(start_date_str="2025-01-01", end_date_str=None, db_path=DB_FILE, table_name=TABLE_NAME, clear_table=False, delay=0.8):
    """
    主抓取流程：自動支援清空重置、斷點續傳與增量抓取，抓取 TWSE 融資融券餘額寫入 SQLite。
    
    :param start_date_str: 起始日期 (預設 2025-01-01，即民國 114 年 1 月 1 日)
    :param end_date_str: 結束日期 (若為 None 則動態取今日)
    :param clear_table: 執行前是否清空資料表
    :param delay: 每次請求間隔秒數 (預設 0.8 秒)
    """
    init_db(db_path, table_name, clear_table=clear_table)
    
    weekday_list, end_dt = generate_target_weekdays(start_date_str, end_date_str)
    today_str = end_dt.strftime("%Y-%m-%d")
    
    # 查詢已存在的日期
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f'SELECT 西元日期 FROM "{table_name}";')
    existing_dates = set(r[0] for r in cursor.fetchall())
    conn.close()
    
    # 篩選待抓取日期
    pending_dates = []
    for d in weekday_list:
        d_str = d.strftime("%Y-%m-%d")
        if d_str not in existing_dates or d_str == today_str:
            pending_dates.append(d)
            
    print(f"==================================================")
    print(f"開始抓取 TWSE 信用交易融資融券餘額")
    print(f"資料庫：{db_path}，資料表：{table_name}")
    print(f"查詢區間：民國 {int(start_date_str[:4]) - 1911} 年 1 月 1 日 ~ 今日 ({today_str}，民國 {end_dt.year - 1911} 年 {end_dt.month} 月 {end_dt.day} 日)")
    print(f"工作日總計：{len(weekday_list)} 天，已存在：{len(existing_dates)} 天，本次待抓取：{len(pending_dates)} 天")
    print(f"==================================================")
    
    if not pending_dates:
        print("所有日期的融資融券餘額皆已完整儲存，無需抓取。")
        return
        
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    success_count = 0
    skip_holiday_count = 0
    
    for idx, d in enumerate(pending_dates, start=1):
        d_iso = d.strftime("%Y-%m-%d")
        d_tw = f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"
        pct = (idx / len(pending_dates)) * 100
        print(f"[{idx}/{len(pending_dates)} - {pct:.1f}%] 抓取 {d_tw} ({d_iso})...", end=" ", flush=True)
        
        record = fetch_single_day_margin(d, session=session, headers=headers)
        if record:
            save_record_to_sqlite(record, db_path, table_name)
            balance_yi = record['融資今日餘額_仟元'] / 100000.0  # 轉為億元
            diff_yi = record['融資增減_仟元'] / 100000.0
            diff_sign = "+" if diff_yi >= 0 else ""
            print(f"成功！融資: {balance_yi:.2f} 億 ({diff_sign}{diff_yi:.2f} 億), 融券: {record['融券今日餘額_張']:,} 張")
            success_count += 1
        else:
            print("休市日/無資料。")
            skip_holiday_count += 1
            
        if idx < len(pending_dates):
            time.sleep(delay)
            
    print("\n================ 抓取完成 ================")
    print(f"本次成功抓取/更新：{success_count} 筆，休市日略過：{skip_holiday_count} 筆")
    
    # 顯示目前資料庫中的最新 5 筆
    conn = sqlite3.connect(db_path)
    df_preview = pd.read_sql_query(f'SELECT * FROM "{table_name}" ORDER BY 西元日期 DESC LIMIT 5;', conn)
    cursor = conn.cursor()
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}";')
    total_in_db = cursor.fetchone()[0]
    cursor.execute(f'SELECT MIN(民國日期), MAX(民國日期) FROM "{table_name}";')
    min_date, max_date = cursor.fetchone()
    conn.close()
    
    print(f"資料表 [{table_name}] 累計總筆數：{total_in_db} 筆")
    print(f"資料涵蓋區間：民國 {min_date} ~ 民國 {max_date}")
    print("\n最新 5 筆融資餘額資料預覽：")
    cols_to_show = ["西元日期", "民國日期", "融資今日餘額_張", "融資今日餘額_仟元", "融資增減_仟元", "融券今日餘額_張"]
    if not df_preview.empty:
        print(df_preview[cols_to_show].to_string(index=False))

if __name__ == "__main__":
    # 執行前清空資料表，並抓取民國 114 年 1 月 1 日 (2025-01-01) 起至今日 (動態變數)
    fetch_and_save_margin_history(start_date_str="2025-01-01", end_date_str=None, clear_table=True, delay=0.8)


