# -*- coding: utf-8 -*-
"""
統一奔騰基金歷史淨值與技術指標計算程式
資料來源：統一投信官網 (https://www.ezmoney.com.tw/funds/nav)
儲存目標：SQLite 資料庫 "股市資料庫.db" 中的 "基金" 資料表
指標公式參考："奔騰02.xlsx" (布林通道、MA5/10/20/60、均線排列、交叉訊號、9日KD)
查詢區間：2025/01/01 (民國 114 年 1 月 1 日) 至今日 (動態變數)
"""

import time
import datetime
import sqlite3
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd

DB_FILE = "股市資料庫.db"
FUND_TABLE_NAME = "基金"

def init_fund_table(db_path=DB_FILE, table_name=FUND_TABLE_NAME):
    """
    初始化 SQLite 資料表，建立「基金」資料表 (若不存在)。
    主鍵為 (基金名稱, 西元日期)，支援多基金擴充與冪等性更新。
    欄位完全參考 奔騰02.xlsx，並於最前面增加「基金名稱」欄位。
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            基金名稱 TEXT,
            西元日期 TEXT,
            日期 TEXT,
            基金淨值 REAL,
            基金漲跌 REAL,
            基金漲跌幅 REAL,
            "20日平均(中軌)" REAL,
            "標準差(波動度)" REAL,
            "布林上軌(天花板)" REAL,
            "布林下軌(地板)" REAL,
            "5MA" REAL,
            "10MA" REAL,
            "20MA" REAL,
            "60MA" REAL,
            均線排列 TEXT,
            交叉訊號 TEXT,
            "RSV(今日成績排名)" REAL,
            "K值(快線)" REAL,
            "D值(慢線)" REAL,
            PRIMARY KEY (基金名稱, 西元日期)
        )
    """)
    conn.commit()
    conn.close()

def calculate_technical_indicators(df_raw, fund_name="統一奔騰"):
    """
    依據「奔騰02.xlsx」公式計算所有技術指標：
    - 基金名稱、西元日期、日期 (民國格式)
    - 基金淨值、基金漲跌、基金漲跌幅
    - 20日平均 (中軌)、標準差 (波動度)、布林上軌 (天花板)、布林下軌 (地板)
    - 5MA, 10MA, 20MA, 60MA
    - 均線排列 (進攻隊形/撤退隊形/打結隊形)
    - 交叉訊號 (★黃金交叉(買訊) / ▲死亡交叉(賣訊) / "")
    - 9日KD: RSV(今日成績排名), K值(快線), D值(慢線)
    """
    if df_raw is None or df_raw.empty:
        return None
        
    # 確保按日期由舊到新排序計算
    df = df_raw.sort_values(by="西元日期").reset_index(drop=True).copy()
    
    dates_iso = df["西元日期"].tolist()
    dates_tw = df["民國日期"].tolist()
    navs = df["基金淨值"].astype(float).tolist()
    n = len(navs)
    
    calc_records = []
    prev_k = 50.0
    prev_d = 50.0
    
    for t in range(n):
        curr_nav = navs[t]
        
        # 漲跌與漲跌幅
        if t == 0:
            # 第一筆以原始官方給定或 0 計算
            change = float(df["基金漲跌"].iloc[0]) if "基金漲跌" in df.columns else 0.0
            change_pct = (change / curr_nav) if curr_nav != 0 else 0.0
        else:
            prev_nav = navs[t - 1]
            change = curr_nav - prev_nav
            change_pct = (curr_nav - prev_nav) / prev_nav if prev_nav != 0 else 0.0
            
        # 均線 (不足天數以已有天數平均計算，與 Excel AVERAGE(B...:B...) 一致)
        w5 = navs[max(0, t - 4): t + 1]
        w10 = navs[max(0, t - 9): t + 1]
        w20 = navs[max(0, t - 19): t + 1]
        w60 = navs[max(0, t - 59): t + 1]
        
        ma5 = sum(w5) / len(w5)
        ma10 = sum(w10) / len(w10)
        ma20 = sum(w20) / len(w20)
        ma60 = sum(w60) / len(w60)
        
        # 20日標準差 (STDEV.S 樣本標準差，ddof=1)
        if len(w20) >= 2:
            std20 = float(np.std(w20, ddof=1))
            upper = ma20 + 2.0 * std20
            lower = ma20 - 2.0 * std20
        else:
            std20 = None
            upper = None
            lower = None
            
        # 均線排列判斷
        if ma5 > ma10 and ma10 > ma20:
            align = "進攻隊形，股票大漲"
        elif ma5 < ma10 and ma10 < ma20:
            align = "撤退隊形，股票跌慘"
        else:
            align = "打結隊形，忽上忽下看不懂"
            
        # 交叉訊號 (5MA 與 10MA 交叉判斷)
        cross = ""
        if t > 0:
            prev_w5 = navs[max(0, t - 5): t]
            prev_w10 = navs[max(0, t - 10): t]
            prev_ma5 = sum(prev_w5) / len(prev_w5)
            prev_ma10 = sum(prev_w10) / len(prev_w10)
            
            if ma5 > ma10 and prev_ma5 <= prev_ma10:
                cross = "★黃金交叉(買訊)"
            elif ma5 < ma10 and prev_ma5 >= prev_ma10:
                cross = "▲死亡交叉(賣訊)"
                
        # 9日 RSV
        w9 = navs[max(0, t - 8): t + 1]
        min9 = min(w9)
        max9 = max(w9)
        if max9 == min9:
            rsv = 50.0
        else:
            rsv = (curr_nav - min9) / (max9 - min9) * 100.0
            
        # 9日 KD
        if t == 0:
            k = 50.0
            d = 50.0
        else:
            k = (1.0 / 3.0) * rsv + (2.0 / 3.0) * prev_k
            d = (1.0 / 3.0) * k + (2.0 / 3.0) * prev_d
        prev_k = k
        prev_d = d
        
        calc_records.append({
            "基金名稱": fund_name,
            "西元日期": dates_iso[t],
            "日期": dates_tw[t],
            "基金淨值": round(curr_nav, 2),
            "基金漲跌": round(change, 2),
            "基金漲跌幅": round(change_pct, 4),
            "20日平均(中軌)": round(ma20, 4) if ma20 is not None else None,
            "標準差(波動度)": round(std20, 4) if std20 is not None else None,
            "布林上軌(天花板)": round(upper, 4) if upper is not None else None,
            "布林下軌(地板)": round(lower, 4) if lower is not None else None,
            "5MA": round(ma5, 4),
            "10MA": round(ma10, 4),
            "20MA": round(ma20, 4),
            "60MA": round(ma60, 4),
            "均線排列": align,
            "交叉訊號": cross,
            "RSV(今日成績排名)": round(rsv, 4),
            "K值(快線)": round(k, 4),
            "D值(慢線)": round(d, 4)
        })
        
    df_calc = pd.DataFrame(calc_records)
    return df_calc

def save_fund_table_to_sqlite(df_calc, db_path=DB_FILE, table_name=FUND_TABLE_NAME):
    """將計算好的基金完整指標資料寫入或更新至 SQLite 的 基金 Table"""
    if df_calc is None or df_calc.empty:
        print("沒有指標資料可寫入資料庫。")
        return
        
    init_fund_table(db_path, table_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    insert_sql = f"""
        INSERT OR REPLACE INTO "{table_name}" (
            基金名稱, 西元日期, 日期, 基金淨值, 基金漲跌, 基金漲跌幅,
            "20日平均(中軌)", "標準差(波動度)", "布林上軌(天花板)", "布林下軌(地板)",
            "5MA", "10MA", "20MA", "60MA",
            均線排列, 交叉訊號,
            "RSV(今日成績排名)", "K值(快線)", "D值(慢線)"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    records = []
    for _, row in df_calc.iterrows():
        records.append((
            str(row["基金名稱"]),
            str(row["西元日期"]),
            str(row["日期"]),
            float(row["基金淨值"]),
            float(row["基金漲跌"]),
            float(row["基金漲跌幅"]),
            float(row["20日平均(中軌)"]) if pd.notnull(row["20日平均(中軌)"]) else None,
            float(row["標準差(波動度)"]) if pd.notnull(row["標準差(波動度)"]) else None,
            float(row["布林上軌(天花板)"]) if pd.notnull(row["布林上軌(天花板)"]) else None,
            float(row["布林下軌(地板)"]) if pd.notnull(row["布林下軌(地板)"]) else None,
            float(row["5MA"]),
            float(row["10MA"]),
            float(row["20MA"]),
            float(row["60MA"]),
            str(row["均線排列"]),
            str(row["交叉訊號"]) if pd.notnull(row["交叉訊號"]) else "",
            float(row["RSV(今日成績排名)"]),
            float(row["K值(快線)"]),
            float(row["D值(慢線)"])
        ))
        
    cursor.executemany(insert_sql, records)
    conn.commit()
    
    cursor.execute(f'SELECT COUNT(*), MIN(日期), MAX(日期) FROM "{table_name}" WHERE 基金名稱 = ?;', (df_calc["基金名稱"].iloc[0],))
    total_count, min_date, max_date = cursor.fetchone()
    conn.close()
    
    print(f"SQLite 寫入成功：資料庫 [{db_path}] / 資料表 [{table_name}]")
    print(f"基金名稱：{df_calc['基金名稱'].iloc[0]}，本次寫入/更新：{len(records)} 筆，累計總筆數：{total_count} 筆 (區間: 民國 {min_date} ~ 民國 {max_date})")

def fetch_fund_raw_nav(start_date_str="2025-01-01", end_date_str=None, fund_code="10YTW", fund_name="統一奔騰"):
    """從統一投信官網抓取指定區間之原始歷史淨值"""
    start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_dt = datetime.date.today() if end_date_str is None else datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    start_tw_slash = f"{start_dt.year - 1911}/{start_dt.month:02d}/{start_dt.day:02d}"
    end_tw_slash = f"{end_dt.year - 1911}/{end_dt.month:02d}/{end_dt.day:02d}"
    
    print("==================================================")
    print(f"開始抓取【{fund_name}】官方歷史淨值資料")
    print(f"資料來源：統一投信官方網站 (代碼: {fund_code})")
    print(f"今日日期（動態）：{end_dt.strftime('%Y-%m-%d')} (民國 {end_dt.year - 1911} 年 {end_dt.month} 月 {end_dt.day} 日)")
    print(f"查詢區間：民國 {start_tw_slash} ~ 民國 {end_tw_slash}")
    print("==================================================")
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Origin": "https://www.ezmoney.com.tw",
        "Referer": "https://www.ezmoney.com.tw/funds/nav"
    }
    
    nav_url = "https://www.ezmoney.com.tw/funds/nav"
    
    try:
        get_resp = session.get(nav_url, headers=headers, timeout=15)
        if get_resp.status_code != 200:
            print(f"首頁連線失敗，狀態碼: {get_resp.status_code}")
            return None
        soup = BeautifulSoup(get_resp.text, "html.parser")
        token_tag = soup.find("input", {"name": "__RequestVerificationToken"})
        if not token_tag:
            print("無法取得驗證權杖。")
            return None
        token = token_tag.get("value")
    except Exception as e:
        print(f"取得驗證權杖時發生異常: {e}")
        return None
        
    payload = {
        "__RequestVerificationToken": token,
        "Fund": fund_code,
        "start": start_tw_slash,
        "end": end_tw_slash
    }
    
    try:
        post_resp = session.post(nav_url, data=payload, headers=headers, timeout=20)
        if post_resp.status_code != 200:
            print(f"查詢表單提交失敗，狀態碼: {post_resp.status_code}")
            return None
    except Exception as e:
        print(f"提交查詢表單時發生異常: {e}")
        return None
        
    soup_res = BeautifulSoup(post_resp.text, "html.parser")
    tables = soup_res.find_all("table")
    
    target_table = None
    for t in tables:
        th_texts = [th.get_text(strip=True) for th in t.find_all("th")]
        if "基金淨值" in th_texts:
            target_table = t
            break
            
    if not target_table:
        print("未在回傳頁面中找到淨值表格。")
        return None
        
    records = []
    rows = target_table.find_all("tr")
    for row in rows:
        dd_elements = row.find_all("dd")
        if len(dd_elements) >= 4:
            date_tw = dd_elements[0].get_text(strip=True)
            nav_str = dd_elements[1].get_text(strip=True).replace(",", "")
            change_str = dd_elements[2].get_text(strip=True).replace(",", "")
            pct_str = dd_elements[3].get_text(strip=True).replace("%", "").strip()
            
            parts = date_tw.split("/")
            if len(parts) == 3:
                try:
                    y_ad = int(parts[0]) + 1911
                    m = int(parts[1])
                    d = int(parts[2])
                    date_iso = f"{y_ad}-{m:02d}-{d:02d}"
                    row_dt = datetime.date(y_ad, m, d)
                    
                    if start_dt <= row_dt <= end_dt:
                        records.append({
                            "西元日期": date_iso,
                            "民國日期": date_tw,
                            "基金淨值": float(nav_str),
                            "基金漲跌": float(change_str),
                            "基金漲跌幅_百分比": float(pct_str) if pct_str else 0.0
                        })
                except (ValueError, TypeError):
                    continue
                    
    df = pd.DataFrame(records)
    if not df.empty:
        df.drop_duplicates(subset=["西元日期"], inplace=True)
        df.sort_values(by="西元日期", inplace=True)
        df.reset_index(drop=True, inplace=True)
        print(f"成功自官網取得 {len(df)} 筆淨值歷史資料！")
        return df
    else:
        return None

def fetch_and_build_fund_table(start_date_str="2025-01-01", end_date_str=None, fund_code="10YTW", fund_name="統一奔騰", db_path=DB_FILE, table_name=FUND_TABLE_NAME):
    """
    整合流程：
    1. 抓取統一奔騰淨值
    2. 參考奔騰02.xlsx公式計算所有技術指標
    3. 寫入到 SQLite 股市資料庫.db 的「基金」Table
    4. 匯出 Excel / CSV 備查
    """
    # 1. 抓取原始淨值
    df_raw = fetch_fund_raw_nav(start_date_str, end_date_str, fund_code=fund_code, fund_name=fund_name)
    if df_raw is None or df_raw.empty:
        print("未能取得原始淨值資料，結束作業。")
        return None
        
    # 2. 計算技術指標
    print("正在依據【奔騰02.xlsx】公式模型計算技術指標與均線隊形...")
    df_calc = calculate_technical_indicators(df_raw, fund_name=fund_name)
    
    # 3. 寫入 SQLite 基金 Table
    save_fund_table_to_sqlite(df_calc, db_path=db_path, table_name=table_name)
    
    # 4. 匯出 Excel 與 CSV (按新到舊排列以符合奔騰02.xlsx的視覺慣例)
    start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_dt = datetime.date.today() if end_date_str is None else datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    start_tw_str = f"{start_dt.year - 1911}{start_dt.month:02d}{start_dt.day:02d}"
    end_tw_str = f"{end_dt.year - 1911}{end_dt.month:02d}{end_dt.day:02d}"
    
    df_export = df_calc.sort_values(by="西元日期", ascending=False).reset_index(drop=True)
    excel_filename = f"統一奔騰基金完整指標_{start_tw_str}_{end_tw_str}.xlsx"
    csv_filename = f"統一奔騰基金完整指標_{start_tw_str}_{end_tw_str}.csv"
    
    df_export.to_excel(excel_filename, index=False)
    df_export.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    
    print("\n================ 指標計算與建表完成 ================")
    print(f"資料起訖：{df_calc['日期'].iloc[0]} ~ {df_calc['日期'].iloc[-1]}")
    print(f"Excel 存檔：{excel_filename}")
    print(f"CSV 存檔：{csv_filename}")
    print("\n最新 5 筆【基金】Table 資料預覽：")
    cols_preview = ["基金名稱", "日期", "基金淨值", "5MA", "10MA", "20MA", "均線排列", "交叉訊號", "K值(快線)", "D值(慢線)"]
    print(df_export[cols_preview].head(5).to_string(index=False))
    return df_calc

if __name__ == "__main__":
    fetch_and_build_fund_table(start_date_str="2025-01-01", end_date_str=None, fund_code="10YTW", fund_name="統一奔騰")
