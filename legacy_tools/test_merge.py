import sqlite3
import pandas as pd

conn = sqlite3.connect("股市資料庫.db")
df_fund = pd.read_sql_query('SELECT * FROM "基金" WHERE 基金名稱 = "統一奔騰" ORDER BY 西元日期 ASC;', conn)
df_taiex = pd.read_sql_query('SELECT * FROM "大盤資料表" ORDER BY 西元日期 ASC;', conn)
df_margin = pd.read_sql_query('SELECT 西元日期, 融資今日餘額_張, 融資今日餘額_仟元, 融資增減_仟元 FROM "融資餘額" ORDER BY 西元日期 ASC;', conn)
conn.close()

print(f"基金筆數: {len(df_fund)}, 大盤筆數: {len(df_taiex)}, 融資筆數: {len(df_margin)}")
df_merged = pd.merge(df_fund, df_taiex, on="西元日期", how="left", suffixes=("", "_大盤"))
df_merged = pd.merge(df_merged, df_margin, on="西元日期", how="left")
print("合併後總筆數:", len(df_merged))
print("大盤收盤空值筆數:", df_merged["收盤指數"].isnull().sum())
print("融資餘額空值 (ffill前):", df_merged["融資今日餘額_仟元"].isnull().sum())

# 融資以 ffill 處理
df_merged["融資今日餘額_仟元"] = df_merged["融資今日餘額_仟元"].ffill().fillna(0)
df_merged["融資增減_仟元"] = df_merged["融資增減_仟元"].fillna(0)
df_merged["融資今日餘額_張"] = df_merged["融資今日餘額_張"].ffill().fillna(0)
print("融資餘額空值 (ffill後):", df_merged["融資今日餘額_仟元"].isnull().sum())

# 大盤均線計算
df_merged["大盤5MA"] = df_merged["收盤指數"].rolling(5).mean().round(2)
df_merged["大盤20MA"] = df_merged["收盤指數"].rolling(20).mean().round(2)
print("最新一筆大盤數據:", df_merged[["西元日期", "開盤指數", "最高指數", "最低指數", "收盤指數", "大盤5MA", "大盤20MA"]].iloc[-1].to_dict())

