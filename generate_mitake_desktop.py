# -*- coding: utf-8 -*-
"""
從 SQLite「股市資料庫.db」讀取：
1. 基金 Table: 統一奔騰基金淨值、布林通道 (20日中軌/上軌/下軌)、9日KD (K值/D值/RSV)、5/10/20/60MA
2. 融資餘額 Table: 全市場融資今日餘額 (張/仟元)、融資增減 (張/仟元)
3. 大盤資料表 Table: 發行量加權股價指數歷史資料 (開、高、低、收、計算5MA/20MA)

專門針對「一般電腦 / 桌面寬螢幕」操作的全新優化版面看盤工作站：
- 重新排版垂直佈局：大盤指數 K 線圖上移至第二位（緊鄰基金主圖，對比極其清晰）
- 四大圖表依黃金比例分配高度：
  【圖一】統一奔騰基金 (34%)：立體淨值圓點 (Dots) + 走勢連線 + 布林通道 (BBAND 20日)
  【圖二】加權大盤指數 K 線圖 (34%)：空間充沛！台股紅漲綠跌蠟燭線 + 5MA/20MA均線 + 最高最低點標註
  【圖三】全市場融資籌碼統計圖 (17%)：三竹金黃折線 + 零軸紅增綠減直方柱
  【圖四】9日KD 體溫計 (15%)：9K/9D雙線 + 80/20 超買超賣著色區塊
- 滿版自適應一屏無捲動全覽（主流筆電與桌機免滾動即可看清四圖）
- 金色雙向十字查價線一口氣穿透四圖、滑鼠滾輪自由縮放、滑鼠拖曳平移、快捷週期切換與指標診斷側欄
"""

import sqlite3
import json
import pandas as pd

DB_FILE = "股市資料庫.db"
OUTPUT_HTML = "mitake_fund_desktop.html"

def generate_desktop_html(output_path=OUTPUT_HTML):
    conn = sqlite3.connect(DB_FILE)
    
    # 1. 讀取基金 Table
    df_fund = pd.read_sql_query('SELECT * FROM "基金" WHERE 基金名稱 = "統一奔騰" ORDER BY 西元日期 ASC;', conn)
    
    # 2. 讀取大盤資料表 Table
    df_taiex = pd.read_sql_query('SELECT * FROM "大盤資料表" ORDER BY 西元日期 ASC;', conn)
    
    # 3. 讀取融資餘額 Table
    df_margin = pd.read_sql_query('SELECT 西元日期, 融資今日餘額_張, 融資今日餘額_仟元, 融資增減_仟元 FROM "融資餘額" ORDER BY 西元日期 ASC;', conn)
    conn.close()
    
    if df_fund.empty:
        print("未在資料庫中找到基金資料！")
        return
        
    # 合併三表 (以西元日期為基準)
    df_merged = pd.merge(df_fund, df_taiex, on="西元日期", how="left", suffixes=("", "_大盤"))
    df_merged = pd.merge(df_merged, df_margin, on="西元日期", how="left")
    
    # 融資欄位前向填補 (ffill)
    df_merged["融資今日餘額_仟元"] = df_merged["融資今日餘額_仟元"].ffill().fillna(0)
    df_merged["融資增減_仟元"] = df_merged["融資增減_仟元"].fillna(0)
    df_merged["融資今日餘額_張"] = df_merged["融資今日餘額_張"].ffill().fillna(0)
    
    # 大盤均線計算
    df_merged["開盤指數"] = df_merged["開盤指數"].ffill().bfill()
    df_merged["最高指數"] = df_merged["最高指數"].ffill().bfill()
    df_merged["最低指數"] = df_merged["最低指數"].ffill().bfill()
    df_merged["收盤指數"] = df_merged["收盤指數"].ffill().bfill()
    df_merged["大盤5MA"] = df_merged["收盤指數"].rolling(5).mean().round(2)
    df_merged["大盤20MA"] = df_merged["收盤指數"].rolling(20).mean().round(2)
    
    # 大盤漲跌計算
    df_merged["大盤前收"] = df_merged["收盤指數"].shift(1)
    df_merged["大盤漲跌"] = (df_merged["收盤指數"] - df_merged["大盤前收"]).round(2).fillna(0)
    df_merged["大盤漲跌幅"] = ((df_merged["大盤漲跌"] / df_merged["大盤前收"]) * 100).round(2).fillna(0)
    
    records = []
    for _, row in df_merged.iterrows():
        margin_yi = round(float(row["融資今日餘額_仟元"]) / 100000.0, 2)
        diff_yi = round(float(row["融資增減_仟元"]) / 100000.0, 2)
        
        records.append({
            "西元日期": str(row["西元日期"]),
            "日期": str(row["日期"]),
            # 基金資料
            "基金淨值": round(float(row["基金淨值"]), 2),
            "基金漲跌": round(float(row["基金漲跌"]), 2),
            "基金漲跌幅": round(float(row["基金漲跌幅"]) * 100, 2),
            "BBAND_中軌": round(float(row["20日平均(中軌)"]), 2) if pd.notnull(row["20日平均(中軌)"]) else None,
            "BBAND_上軌": round(float(row["布林上軌(天花板)"]), 2) if pd.notnull(row["布林上軌(天花板)"]) else None,
            "BBAND_下軌": round(float(row["布林下軌(地板)"]), 2) if pd.notnull(row["布林下軌(地板)"]) else None,
            "5MA": round(float(row["5MA"]), 2) if pd.notnull(row["5MA"]) else None,
            "10MA": round(float(row["10MA"]), 2) if pd.notnull(row["10MA"]) else None,
            "20MA": round(float(row["20MA"]), 2) if pd.notnull(row["20MA"]) else None,
            "60MA": round(float(row["60MA"]), 2) if pd.notnull(row["60MA"]) else None,
            "K值": round(float(row["K值(快線)"]), 2) if pd.notnull(row["K值(快線)"]) else 50.0,
            "D值": round(float(row["D值(慢線)"]), 2) if pd.notnull(row["D值(慢線)"]) else 50.0,
            "RSV": round(float(row["RSV(今日成績排名)"]), 1) if pd.notnull(row["RSV(今日成績排名)"]) else 50.0,
            "均線排列": str(row["均線排列"]) if pd.notnull(row["均線排列"]) else "",
            "交叉訊號": str(row["交叉訊號"]) if pd.notnull(row["交叉訊號"]) else "",
            # 融資資料
            "融資餘額_億": margin_yi,
            "融資增減_億": diff_yi,
            "融資餘額_張": int(row["融資今日餘額_張"]),
            # 大盤資料
            "大盤開盤": round(float(row["開盤指數"]), 2),
            "大盤最高": round(float(row["最高指數"]), 2),
            "大盤最低": round(float(row["最低指數"]), 2),
            "大盤收盤": round(float(row["收盤指數"]), 2),
            "大盤漲跌": round(float(row["大盤漲跌"]), 2),
            "大盤漲跌幅": round(float(row["大盤漲跌幅"]), 2),
            "大盤5MA": round(float(row["大盤5MA"]), 2) if pd.notnull(row["大盤5MA"]) else None,
            "大盤20MA": round(float(row["大盤20MA"]), 2) if pd.notnull(row["大盤20MA"]) else None,
        })
        
    json_data = json.dumps(records, ensure_ascii=False)
    total_records = len(records)
    latest = records[-1]
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統一奔騰基金 × 加權大盤指數 - 三竹專業桌面看盤工作站</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Phosphor Icons -->
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');
        
        * {{
            box-sizing: border-box;
            user-select: none;
            -webkit-user-select: none;
        }}
        
        body {{
            font-family: 'Roboto Mono', 'Noto Sans TC', monospace, sans-serif;
            background-color: #06080b;
            color: #ffffff;
            margin: 0;
            padding: 0;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
        }}
        
        /* 自定義捲軸 */
        ::-webkit-scrollbar {{
            width: 7px;
            height: 7px;
        }}
        ::-webkit-scrollbar-track {{
            background: #080d14;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #1e293b;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #334155;
        }}
        
        /* 三竹高對比金融色 */
        .color-up {{
            color: #ff333a !important;
        }}
        .color-down {{
            color: #00e676 !important;
        }}
        .color-yellow {{
            color: #ffd600 !important;
        }}
        .color-cyan {{
            color: #00e5ff !important;
        }}
        .color-purple {{
            color: #d500f9 !important;
        }}

        canvas {{
            display: block;
            touch-action: none;
            cursor: crosshair;
        }}
    </style>
</head>
<body class="w-full h-full flex flex-col bg-[#06080b]">

    <!-- 1. 頂部金融看盤 Header -->
    <header class="h-13 bg-[#0a1017] border-b border-[#182330] px-4 flex items-center justify-between select-none z-30 shrink-0">
        <!-- 標的名稱與雙核心指標 -->
        <div class="flex items-center gap-4">
            <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-sky-950 border border-sky-600/50 flex items-center justify-center text-sky-400 shadow-md">
                    <i class="ph-bold ph-chart-polar text-lg"></i>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-base font-extrabold text-white tracking-wide">統一奔騰基金</h1>
                        <span class="text-xs font-bold text-[#00e5ff] bg-[#0c2438] px-2 py-0.5 rounded border border-[#14476e]">淨值圓點</span>
                        <span class="text-xs font-bold text-amber-300 bg-amber-950/70 px-2 py-0.5 rounded border border-amber-800">加權大盤K線</span>
                    </div>
                    <div class="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                        <span>直連：<code class="text-sky-300 font-mono">股市資料庫.db</code></span> •
                        <span>交易日：<strong class="text-slate-200">{total_records} 筆</strong></span> •
                        <span>雙主圖並列對照</span>
                    </div>
                </div>
            </div>

            <!-- Header 即時雙報價看板 -->
            <div class="hidden xl:flex items-center gap-5 pl-5 border-l border-slate-800 font-mono">
                <!-- 基金即時 -->
                <div>
                    <div class="text-[9px] text-slate-400 font-sans">統一奔騰淨值 ({latest["日期"]})</div>
                    <div class="flex items-baseline gap-1.5 mt-0.5">
                        <span class="text-xl font-black text-[#00e676] leading-none" id="headNavVal">{latest["基金淨值"]}</span>
                        <span class="text-xs font-bold text-[#00e676]" id="headNavDiff">{latest["基金漲跌"]} ({latest["基金漲跌幅"]}%)</span>
                    </div>
                </div>
                <!-- 大盤即時 -->
                <div class="pl-4 border-l border-slate-800/80">
                    <div class="text-[9px] text-slate-400 font-sans">加權大盤指數 (TAIEX)</div>
                    <div class="flex items-baseline gap-1.5 mt-0.5">
                        <span class="text-xl font-black text-[#ff333a] leading-none" id="headTaiexVal">{latest["大盤收盤"]}</span>
                        <span class="text-xs font-bold text-[#ff333a]" id="headTaiexDiff">{latest["大盤漲跌"]} ({latest["大盤漲跌幅"]}%)</span>
                    </div>
                </div>
                <!-- 融資籌碼 -->
                <div class="pl-4 border-l border-slate-800/80">
                    <div class="text-[9px] text-slate-400 font-sans">全市場融資餘額</div>
                    <div class="flex items-baseline gap-1.5 mt-0.5">
                        <span class="text-sm font-bold text-[#ffd600] leading-none" id="headMarginVal">{latest["融資餘額_億"]} 億</span>
                        <span class="text-xs font-bold text-[#ff333a]" id="headMarginDiff">+{latest["融資增減_億"]} 億</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 桌面版快速期間切換與操作工具 -->
        <div class="flex items-center gap-2.5">
            <!-- 視圖切換 (四圖連動 vs 雙主圖對比) -->
            <div class="hidden md:flex items-center bg-[#111722] rounded-lg p-0.5 border border-[#1e2a3a] text-xs font-bold mr-1">
                <button id="viewAllCharts" class="px-2.5 py-1 rounded bg-sky-600 text-white shadow-xs">四圖連動總覽</button>
                <button id="viewDualMain" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">基金vs大盤對比</button>
            </div>

            <!-- 週期切換 -->
            <div class="flex items-center bg-[#111722] rounded-lg p-0.5 border border-[#1e2a3a] text-xs font-bold">
                <button class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition" data-days="22">近1月</button>
                <button class="px-2.5 py-1 rounded bg-sky-600 text-white shadow-xs" data-days="65">近3月</button>
                <button class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition" data-days="130">近半年</button>
                <button class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition" data-days="250">近1年</button>
                <button class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition" data-days="9999">全部</button>
            </div>

            <!-- 縮放與控制工具 -->
            <button id="btnZoomIn" class="w-8 h-8 rounded-lg bg-[#111722] border border-[#1e2a3a] text-slate-300 hover:text-white flex items-center justify-center text-sm font-bold shadow-xs" title="放大">＋</button>
            <button id="btnZoomOut" class="w-8 h-8 rounded-lg bg-[#111722] border border-[#1e2a3a] text-slate-300 hover:text-white flex items-center justify-center text-sm font-bold shadow-xs" title="縮小">－</button>
            <button id="btnReset" class="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-xs flex items-center gap-1">
                <i class="ph-bold ph-arrow-counter-clockwise"></i> 最新
            </button>
            <button id="btnToggleSide" class="px-2.5 py-1.5 rounded-lg bg-[#111722] border border-[#1e2a3a] text-slate-300 hover:text-white font-bold text-xs flex items-center gap-1" title="切換右側診斷面板">
                <i class="ph-bold ph-sidebar-simple"></i>
            </button>
        </div>
    </header>

    <!-- 2. 全域雙向查價即時資訊橫條 (桌面寬版 Info Bar) -->
    <div id="crossInfoBar" class="h-8 bg-[#040608] border-b border-[#151c24] px-4 flex items-center justify-between text-xs font-mono select-none shrink-0 z-20">
        <div class="flex items-center gap-3.5 overflow-x-auto whitespace-nowrap">
            <span class="color-yellow font-bold">時 <span id="infoDate">--/--</span> (<span id="infoDateIso" class="text-slate-400 text-[11px]">----</span>)</span>
            
            <!-- 基金數值 -->
            <span class="text-slate-400">基金淨值: <strong id="infoNav" class="font-bold">--</strong></span>
            <span class="text-slate-400">漲跌: <strong id="infoChange" class="font-bold">--</strong></span>
            
            <!-- 大盤數值 (緊鄰基金，對比最快) -->
            <span class="text-slate-400 pl-2 border-l border-slate-800">加權指數: <strong id="infoTaiex" class="font-bold text-[#ff333a]">--</strong></span>
            <span class="text-slate-400">大盤漲跌: <strong id="infoTaiexDiff" class="font-bold">--</strong></span>
            
            <!-- 布林通道 -->
            <span class="color-purple pl-2 border-l border-slate-800">中軌: <span id="infoMid">--</span></span>
            <span class="color-cyan">上軌: <span id="infoUpper">--</span></span>
            <span class="color-purple">下軌: <span id="infoLower">--</span></span>
            
            <!-- 融資籌碼數值 -->
            <span class="text-slate-400 pl-2 border-l border-slate-800">融資: <strong id="infoMargin" class="color-yellow">-- 億</strong></span>
            <span class="text-slate-400">增減: <strong id="infoMarginDiff">-- 億</strong></span>
            
            <!-- KD 數值 -->
            <span class="color-yellow pl-2 border-l border-slate-800">9K: <span id="infoK">--</span></span>
            <span class="color-cyan">9D: <span id="infoD">--</span></span>
        </div>
        <div class="text-[11px] text-slate-500 hidden sm:flex items-center gap-2">
            <span>🖱️ 滑鼠滾輪縮放 / 拖曳平移</span> • 
            <span>鍵盤 ◄ ► 逐日切換</span>
        </div>
    </div>

    <!-- 3. 主體內容區 (左側四圖獨立滾動畫布區 + 右側即時診斷側欄) -->
    <div class="flex-1 flex overflow-hidden relative">
        
        <!-- 左側繪圖容器 (支援流暢縱向展開，四個圖表高度黃金分配) -->
        <div class="flex-1 h-full bg-black relative flex flex-col overflow-y-auto overflow-x-hidden" id="chartWrapper">
            <div id="canvasContainer" class="w-full relative">
                <canvas id="mainCanvas" class="w-full"></canvas>
            </div>
        </div>

        <!-- 右側即時指標智能診斷側欄 (Desktop Pro Sidebar) -->
        <div id="sidePanel" class="w-80 bg-[#080d14] border-l border-[#141c26] flex flex-col p-3.5 overflow-y-auto shrink-0 select-none z-10 space-y-2.5">
            <div class="flex items-center justify-between pb-2 border-b border-slate-800">
                <span class="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <i class="ph-bold ph-gauge text-sky-400 text-sm"></i>
                    當日指標智能診斷看板
                </span>
                <span id="sideBadgeDate" class="text-[10px] font-mono text-sky-400 bg-sky-950 px-1.5 py-0.5 rounded border border-sky-800">--/--</span>
            </div>

            <!-- 卡片 1: 統一奔騰基金淨值位階 -->
            <div class="bg-[#0f151f] p-3 rounded-xl border border-slate-800">
                <div class="text-[11px] text-slate-400 font-bold mb-1 flex justify-between">
                    <span>統一奔騰基金 (淨值位階)</span>
                    <span class="text-[10px] text-sky-400">台股科技型</span>
                </div>
                <div class="flex items-baseline justify-between">
                    <span id="sideNav" class="text-2xl font-black text-white">--</span>
                    <span id="sideChange" class="text-xs font-bold">--</span>
                </div>
                <div class="mt-2 pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex justify-between">
                    <span>波段最低點: 264.02</span>
                    <span id="sideMinGap" class="font-bold text-sky-400">--</span>
                </div>
            </div>

            <!-- 卡片 2: 加權大盤指數即時狀態 -->
            <div class="bg-[#0f151f] p-3 rounded-xl border border-slate-800">
                <div class="text-[11px] text-slate-400 font-bold mb-1 flex justify-between items-center">
                    <span>加權大盤指數 (TAIEX)</span>
                    <span id="sideTaiexBias" class="text-[10px] font-mono">月線乖離: --%</span>
                </div>
                <div class="flex items-baseline justify-between">
                    <span id="sideTaiex" class="text-2xl font-black text-white">--</span>
                    <span id="sideTaiexChange" class="text-xs font-bold">--</span>
                </div>
                <div class="mt-2 pt-2 border-t border-slate-800/80 text-[10px] text-slate-300 font-mono space-y-1">
                    <div class="flex justify-between"><span>開盤 / 最高:</span> <span id="sideTaiexOH" class="text-slate-200">-- / --</span></div>
                    <div class="flex justify-between"><span>最低 / 收盤:</span> <span id="sideTaiexLC" class="text-slate-200">-- / --</span></div>
                    <div class="flex justify-between"><span>大盤 5MA / 20MA:</span> <span id="sideTaiexMA" class="text-amber-300">-- / --</span></div>
                </div>
            </div>

            <!-- 卡片 3: 布林通道 (BBAND) 診斷 -->
            <div class="bg-[#0f151f] p-3 rounded-xl border border-slate-800">
                <div class="text-[11px] text-slate-400 font-bold mb-1.5 flex justify-between items-center">
                    <span>布林通道 (20日, ±2SD)</span>
                    <span id="sideBandWidth" class="text-[10px] text-slate-300 font-mono">寬度 --%</span>
                </div>
                <div id="sideBbandBadge" class="text-[11px] font-bold px-2 py-1 rounded bg-slate-800 text-slate-300 mb-2 text-center">
                    --
                </div>
                <div class="text-[11px] space-y-1 font-mono text-slate-300">
                    <div class="flex justify-between"><span>上軌天花板:</span> <strong id="sideUpper" class="text-[#38bdf8]">--</strong></div>
                    <div class="flex justify-between"><span>中軌20日均:</span> <strong id="sideMid" class="text-[#ffd600]">--</strong></div>
                    <div class="flex justify-between"><span>下軌地板價:</span> <strong id="sideLower" class="text-[#d500f9]">--</strong></div>
                </div>
            </div>

            <!-- 卡片 4: 9日KD 體溫計 -->
            <div class="bg-[#0f151f] p-3 rounded-xl border border-slate-800">
                <div class="text-[11px] text-slate-400 font-bold mb-1.5 flex justify-between items-center">
                    <span>9日KD 體溫計</span>
                    <span id="sideRsv" class="text-[10px] text-slate-400 font-mono">RSV: --</span>
                </div>
                <div class="flex items-center justify-between mb-2 font-mono">
                    <span class="text-sm font-bold text-[#ffd600]">9K: <strong id="sideK" class="text-base font-black">--</strong></span>
                    <span class="text-sm font-bold text-[#00e5ff]">9D: <strong id="sideD" class="text-base font-black">--</strong></span>
                    <span id="sideKdDiff" class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800">--</span>
                </div>
                <div id="sideKdBadge" class="text-[11px] font-bold px-2 py-1 rounded bg-slate-800 text-slate-300 text-center">
                    --
                </div>
            </div>

            <!-- 卡片 5: 全市場融資籌碼 -->
            <div class="bg-[#0f151f] p-3 rounded-xl border border-slate-800">
                <div class="text-[11px] text-slate-400 font-bold mb-1.5 flex justify-between items-center">
                    <span>全市場融資籌碼統計</span>
                    <span class="text-[10px] text-amber-400 font-sans font-bold">市場主力指標</span>
                </div>
                <div class="text-[11px] space-y-1 font-mono text-slate-300">
                    <div class="flex justify-between"><span>融資今日餘額:</span> <strong id="sideMarginBal" class="text-[#ffd600] text-sm">-- 億</strong></div>
                    <div class="flex justify-between"><span>融資當日增減:</span> <strong id="sideMarginDiff" class="font-bold">-- 億</strong></div>
                    <div class="flex justify-between"><span>融資餘額張數:</span> <span id="sideMarginShares" class="text-slate-300">-- 張</span></div>
                </div>
            </div>

            <!-- 卡片 6: 均線隊形與交叉訊號 -->
            <div class="bg-[#0f151f] p-3 rounded-xl border border-slate-800">
                <div class="text-[11px] text-slate-400 font-bold mb-1.5">均線隊形與交叉訊號</div>
                <div id="sideAlignBadge" class="text-[11px] font-bold px-2 py-1 rounded bg-slate-800 text-slate-300 mb-2 text-center">
                    --
                </div>
                <div class="text-[11px] space-y-1 font-mono text-slate-300">
                    <div class="flex justify-between"><span>5MA / 10MA:</span> <span id="sideMA5_10" class="text-slate-200">-- / --</span></div>
                    <div class="flex justify-between"><span>20MA / 60MA:</span> <span id="sideMA20_60" class="text-slate-200">-- / --</span></div>
                    <div class="flex justify-between"><span>基金月線乖離:</span> <strong id="sideBias20" class="font-bold">--%</strong></div>
                </div>
            </div>

            <!-- 底部資料來源聲明 -->
            <div class="pt-2 border-t border-slate-800/80 text-[10px] text-slate-500 leading-relaxed">
                ※ 數據每日收盤後自統一投信與臺灣證券交易所 (TWSE) 同步，即時儲存於 SQLite 資料庫。
            </div>
        </div>
    </div>

    <!-- 高性能四圖聯動 Canvas 繪圖引擎 (新版排版：基金主圖 ➔ 大盤K線 ➔ 時間軸 ➔ 融資餘額 ➔ 9日KD) -->
    <script>
        const rawData = {json_data};
        const total = rawData.length;

        let canvas = document.getElementById("mainCanvas");
        let ctx = canvas.getContext("2d");

        // 視圖狀態
        let currentMode = "all";    // "all": 四圖總覽, "dual": 基金vs大盤
        let dotSpacing = 13.5;       // 預設寬度間距
        let dotRadius = 4.2;        // 淨值圓點半徑
        let offsetIndex = 0;        // 偏移量 (0 為最新)
        let selectedIndex = total - 1; // 預設選取最新
        let isDragging = false;
        let dragStartX = 0;
        let dragStartOffset = 0;
        let visibleCount = 65;

        // 計算 Canvas 邏輯高度 (自適應視窗高度，保障四圖一屏看清)
        function getRequiredCanvasHeight() {{
            const wrapper = document.getElementById("chartWrapper");
            const wH = wrapper.clientHeight;
            // 720px 為舒適保障下限，若視窗更大則 100% 滿版無捲動
            return Math.max(wH, 720);
        }}

        // 重繪尺寸
        function resizeCanvas() {{
            const wrapper = document.getElementById("chartWrapper");
            const dpr = window.devicePixelRatio || 1;
            const targetH = getRequiredCanvasHeight();
            const targetW = wrapper.clientWidth;

            canvas.style.width = targetW + "px";
            canvas.style.height = targetH + "px";
            canvas.width = targetW * dpr;
            canvas.height = targetH * dpr;

            ctx.resetTransform ? ctx.resetTransform() : ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.scale(dpr, dpr);
            render();
        }}

        window.addEventListener("resize", resizeCanvas);

        // 更新頂部查價橫條與右側指標診斷面板
        function updateInspectors(record) {{
            if (!record) return;
            const parts = record["西元日期"].split("-");
            document.getElementById("infoDate").textContent = `${{parts[1]}}/${{parts[2]}}`;
            document.getElementById("infoDateIso").textContent = record["西元日期"];

            // 基金指標
            const nav = record["基金淨值"];
            const diff = record["基金漲跌"];
            const pct = record["基金漲跌幅"];
            const mid = record["BBAND_中軌"] || 0;
            const upper = record["BBAND_上軌"] || 0;
            const lower = record["BBAND_下軌"] || 0;
            const k = record["K值"] || 50;
            const d = record["D值"] || 50;

            // 融資指標
            const mBal = record["融資餘額_億"] || 0;
            const mDiff = record["融資增減_億"] || 0;

            // 大盤指標
            const tClose = record["大盤收盤"];
            const tDiff = record["大盤漲跌"];
            const tPct = record["大盤漲跌幅"];
            const t5MA = record["大盤5MA"] || 0;
            const t20MA = record["大盤20MA"] || 0;

            // 1. 頂部查價欄更新
            const navEl = document.getElementById("infoNav");
            const changeEl = document.getElementById("infoChange");
            navEl.textContent = nav.toFixed(2);
            const sign = diff > 0 ? "+" : "";
            changeEl.textContent = `${{sign}}${{diff.toFixed(2)}} (${{sign}}${{pct.toFixed(2)}}%)`;
            const colorClass = diff > 0 ? "color-up" : (diff < 0 ? "color-down" : "text-slate-300");
            navEl.className = `font-bold ${{colorClass}}`;
            changeEl.className = `font-bold ${{colorClass}}`;

            const tEl = document.getElementById("infoTaiex");
            const tDiffEl = document.getElementById("infoTaiexDiff");
            tEl.textContent = tClose.toFixed(2);
            const tSign = tDiff > 0 ? "+" : "";
            tDiffEl.textContent = `${{tSign}}${{tDiff.toFixed(2)}} (${{tSign}}${{tPct.toFixed(2)}}%)`;
            const tColorClass = tDiff > 0 ? "color-up" : (tDiff < 0 ? "color-down" : "text-slate-300");
            tEl.className = `font-bold ${{tColorClass}}`;
            tDiffEl.className = `font-bold ${{tColorClass}}`;

            document.getElementById("infoMid").textContent = mid ? mid.toFixed(2) : "--";
            document.getElementById("infoUpper").textContent = upper ? upper.toFixed(2) : "--";
            document.getElementById("infoLower").textContent = lower ? lower.toFixed(2) : "--";
            document.getElementById("infoK").textContent = k.toFixed(2);
            document.getElementById("infoD").textContent = d.toFixed(2);

            document.getElementById("infoMargin").textContent = `${{mBal.toFixed(2)}} 億`;
            const mDiffEl = document.getElementById("infoMarginDiff");
            mDiffEl.textContent = `${{mDiff >= 0 ? "+" : ""}}${{mDiff.toFixed(2)}} 億`;
            mDiffEl.className = mDiff >= 0 ? "color-up font-bold" : "color-down font-bold";

            // 2. 右側側欄同步更新
            document.getElementById("sideBadgeDate").textContent = `${{record["日期"]}} (${{record["西元日期"]}})`;
            
            // 基金卡片
            document.getElementById("sideNav").textContent = nav.toFixed(2);
            const sideChangeEl = document.getElementById("sideChange");
            sideChangeEl.textContent = `${{sign}}${{diff.toFixed(2)}} (${{sign}}${{pct.toFixed(2)}}%)`;
            sideChangeEl.className = `text-xs font-bold ${{colorClass}}`;
            const minGap = +(nav - 264.02).toFixed(2);
            const minGapPct = +((minGap / 264.02) * 100).toFixed(2);
            document.getElementById("sideMinGap").textContent = `+${{minGap}} (+${{minGapPct}}%)`;

            // 大盤卡片
            document.getElementById("sideTaiex").textContent = tClose.toLocaleString("zh-TW", {{minimumFractionDigits: 2}});
            const sideTChangeEl = document.getElementById("sideTaiexChange");
            sideTChangeEl.textContent = `${{tSign}}${{tDiff.toFixed(2)}} (${{tSign}}${{tPct.toFixed(2)}}%)`;
            sideTChangeEl.className = `text-xs font-bold ${{tColorClass}}`;
            
            const tBias20 = t20MA > 0 ? (((tClose - t20MA) / t20MA) * 100).toFixed(2) : "0.00";
            const sTBiasEl = document.getElementById("sideTaiexBias");
            sTBiasEl.textContent = `月線乖離: ${{tBias20}}%`;
            sTBiasEl.className = tBias20 >= 0 ? "text-[10px] font-mono text-rose-400 font-bold" : "text-[10px] font-mono text-emerald-400 font-bold";
            
            document.getElementById("sideTaiexOH").textContent = `${{record["大盤開盤"].toFixed(1)}} / ${{record["大盤最高"].toFixed(1)}}`;
            document.getElementById("sideTaiexLC").textContent = `${{record["大盤最低"].toFixed(1)}} / ${{record["大盤收盤"].toFixed(1)}}`;
            document.getElementById("sideTaiexMA").textContent = `${{t5MA ? t5MA.toFixed(1) : "--"}} / ${{t20MA ? t20MA.toFixed(1) : "--"}}`;

            // 布林卡片
            document.getElementById("sideUpper").textContent = upper ? upper.toFixed(2) : "--";
            document.getElementById("sideMid").textContent = mid ? mid.toFixed(2) : "--";
            document.getElementById("sideLower").textContent = lower ? lower.toFixed(2) : "--";
            const bWidth = mid > 0 ? (((upper - lower) / mid) * 100).toFixed(2) : "0.00";
            document.getElementById("sideBandWidth").textContent = `寬度 ${{bWidth}}%`;

            const bBadge = document.getElementById("sideBbandBadge");
            if (nav < lower) {{
                bBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-rose-950 text-rose-300 border border-rose-800 mb-2 text-center";
                bBadge.textContent = "跌破下軌 (超跌特價區)";
            }} else if (nav <= lower + (upper - lower) * 0.15) {{
                bBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-amber-950 text-amber-300 border border-amber-800 mb-2 text-center";
                bBadge.textContent = "下軌支撐確立 (底部防禦)";
            }} else if (nav > upper) {{
                bBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-purple-950 text-purple-300 border border-purple-800 mb-2 text-center";
                bBadge.textContent = "突破上軌 (強勢創高)";
            }} else {{
                bBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-slate-800 text-slate-300 mb-2 text-center";
                bBadge.textContent = "布林通道區間震盪";
            }}

            // 9日KD卡片
            document.getElementById("sideK").textContent = k.toFixed(2);
            document.getElementById("sideD").textContent = d.toFixed(2);
            document.getElementById("sideRsv").textContent = `RSV: ${{record["RSV"]}}`;
            const kdDiffVal = +(k - d).toFixed(2);
            const kdDiffEl = document.getElementById("sideKdDiff");
            kdDiffEl.textContent = `K-D: ${{kdDiffVal >= 0 ? "+" : ""}}${{kdDiffVal}}`;
            kdDiffEl.className = `text-[10px] font-bold px-1.5 py-0.5 rounded ${{kdDiffVal >= 0 ? "bg-emerald-950 text-emerald-300 border border-emerald-800" : "bg-rose-950 text-rose-300 border border-rose-800"}}`;

            const kdBadge = document.getElementById("sideKdBadge");
            if (k < 20 && d < 20) {{
                kdBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-center";
                kdBadge.textContent = "KD 低檔極凍鈍化 (<20)";
            }} else if (k >= d && k < 40) {{
                kdBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-center";
                kdBadge.textContent = "KD 低檔黃金交叉向上";
            }} else if (k > 80 && d > 80) {{
                kdBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-rose-950 text-rose-300 border border-rose-800 text-center";
                kdBadge.textContent = "KD 高檔過熱警戒 (>80)";
            }} else {{
                kdBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-slate-800 text-slate-300 text-center";
                kdBadge.textContent = "KD 常態區間運行";
            }}

            // 融資籌碼卡片
            document.getElementById("sideMarginBal").textContent = `${{mBal.toFixed(2)}} 億`;
            const sDiffEl = document.getElementById("sideMarginDiff");
            sDiffEl.textContent = `${{mDiff >= 0 ? "+" : ""}}${{mDiff.toFixed(2)}} 億`;
            sDiffEl.className = mDiff >= 0 ? "font-bold text-[#ff333a]" : "font-bold text-[#00e676]";
            document.getElementById("sideMarginShares").textContent = `${{record["融資餘額_張"].toLocaleString()}} 張`;

            // 均線卡片
            const alignStr = record["均線排列"] || "常態排列";
            const alignBadge = document.getElementById("sideAlignBadge");
            if (alignStr.includes("進攻隊形")) {{
                alignBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 mb-2 text-center";
                alignBadge.textContent = "進攻隊形 (多頭排列)";
            }} else if (alignStr.includes("撤退隊形")) {{
                alignBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-rose-950 text-rose-300 border border-rose-800 mb-2 text-center";
                alignBadge.textContent = "撤退隊形 (空頭排列)";
            }} else {{
                alignBadge.className = "text-[11px] font-bold px-2 py-1 rounded bg-slate-800 text-slate-300 mb-2 text-center";
                alignBadge.textContent = "打結隊形 (盤整休息)";
            }}
            document.getElementById("sideMA5_10").textContent = `${{record["5MA"] || "--"}} / ${{record["10MA"] || "--"}}`;
            document.getElementById("sideMA20_60").textContent = `${{record["20MA"] || "--"}} / ${{record["60MA"] || "--"}}`;
            const bias20 = mid > 0 ? (((nav - mid) / mid) * 100).toFixed(2) : "0.00";
            const biasEl = document.getElementById("sideBias20");
            biasEl.textContent = `${{bias20}}%`;
            biasEl.className = bias20 >= 0 ? "font-bold text-emerald-400" : "font-bold text-rose-400";
        }}

        // 核心渲染函式 (全新垂直結構與比例分配)
        function render() {{
            if (total === 0) return;

            const dpr = window.devicePixelRatio || 1;
            const width = canvas.width / dpr;
            const height = canvas.height / dpr;

            ctx.clearRect(0, 0, width, height);

            const rightAxisWidth = 72; // 右側刻度欄寬度
            const chartW = width - rightAxisWidth;

            // 計算可視範圍
            visibleCount = Math.floor(chartW / dotSpacing);
            let endIndex = total - 1 - offsetIndex;
            endIndex = Math.max(visibleCount - 1, Math.min(total - 1, endIndex));
            let startIndex = Math.max(0, endIndex - visibleCount + 1);

            const visibleData = rawData.slice(startIndex, endIndex + 1);
            if (visibleData.length === 0) return;

            function getX(idxInVisible) {{
                return 18 + idxInVisible * dotSpacing;
            }}

            const curRecord = rawData[selectedIndex !== -1 ? selectedIndex : total - 1];

            // -----------------------------------------------------------------
            // 【全新優化版面高度分配與順序重組】
            // 順序：1. 基金主圖 ➔ 2. 大盤K線(往上提) ➔ 3. 時間軸 ➔ 4. 融資餘額 ➔ 5. 9日KD
            // -----------------------------------------------------------------
            let fundTop, fundH, bbandBarTop, bbandBarH;
            let taiexTop, taiexH, taiexBarTop, taiexBarH;
            let timeAxisTop, timeAxisH;
            let sub2BarTop, sub2BarH, sub2Top, sub2H;
            let sub1BarTop, sub1BarH, sub1Top, sub1H;

            if (currentMode === "all") {{
                // 【四圖模式：大盤指數上移至第二位核心視野，高度黃金比例分配】
                const fixedBarsH = 22 * 4 + 20; // 4 個 22px 資訊條 + 20px 時間軸 = 108px
                const padTop = 6;
                const availNetH = Math.max(540, height - fixedBarsH - padTop - 10);

                // 依黃金比例分配四大圖表高度：
                fundH = Math.round(availNetH * 0.34);      // 圖一：基金淨值圓點 (34%)
                taiexH = Math.round(availNetH * 0.34);     // 圖二：大盤指數 K 線 (34%，空間充裕，蠟燭棒與均線極清晰！)
                sub2H = Math.round(availNetH * 0.17);      // 圖三：融資籌碼統計 (17%，紅綠增減直方柱)
                sub1H = availNetH - fundH - taiexH - sub2H; // 圖四：9日KD體溫計 (15%，80/20著色帶)

                // 垂直座標依序緊湊銜接：
                // 1. 基金主圖
                fundTop = padTop;
                bbandBarTop = fundTop + fundH;
                bbandBarH = 22;

                // 2. 加權大盤指數 K 線圖 (上移至此，緊鄰基金主圖！)
                taiexTop = bbandBarTop + bbandBarH + 2;
                taiexBarTop = taiexTop + taiexH;
                taiexBarH = 22;

                // 時間軸 X 軸 (作為主圖與指標副圖的分水嶺)
                timeAxisTop = taiexBarTop + taiexBarH;
                timeAxisH = 20;

                // 3. 全市場融資籌碼統計圖
                sub2BarTop = timeAxisTop + timeAxisH + 2;
                sub2BarH = 22;
                sub2Top = sub2BarTop + sub2BarH;

                // 4. 9日KD 體溫計
                sub1BarTop = sub2Top + sub2H + 2;
                sub1BarH = 22;
                sub1Top = sub1BarTop + sub1BarH;
            }} else {{
                // 【基金 vs 大盤 雙主圖對比模式】
                const fixedBarsH = 22 * 2 + 20;
                const availNetH = Math.max(500, height - fixedBarsH - 16);
                fundH = Math.round(availNetH * 0.50);
                taiexH = availNetH - fundH;

                fundTop = 6;
                bbandBarTop = fundTop + fundH;
                bbandBarH = 22;

                taiexTop = bbandBarTop + bbandBarH + 2;
                taiexBarTop = taiexTop + taiexH;
                taiexBarH = 22;

                timeAxisTop = taiexBarTop + taiexBarH;
                timeAxisH = 20;
            }}

            // =================================================================
            // 1. 【圖一：統一奔騰基金 (淨值圓點 + 布林通道)】
            // =================================================================
            let maxNav = -Infinity, minNav = Infinity;
            let maxNavIdx = 0, minNavIdx = 0;

            visibleData.forEach((d, idx) => {{
                const h = Math.max(d["基金淨值"], d["BBAND_上軌"] || d["基金淨值"]);
                const l = Math.min(d["基金淨值"], d["BBAND_下軌"] || d["基金淨值"]);
                if (h > maxNav) {{ maxNav = h; maxNavIdx = idx; }}
                if (l < minNav) {{ minNav = l; minNavIdx = idx; }}
            }});
            const navPad = (maxNav - minNav) * 0.08 || 15.0;
            maxNav += navPad;
            minNav -= navPad;

            function getNavY(p) {{
                return fundTop + fundH - ((p - minNav) / (maxNav - minNav)) * fundH;
            }}

            // 主圖格線與價格刻度
            ctx.strokeStyle = "#141922";
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);
            for (let i = 0; i <= 4; i++) {{
                const pVal = minNav + (maxNav - minNav) * (i / 4);
                const yPos = getNavY(pVal);
                ctx.beginPath();
                ctx.moveTo(0, yPos);
                ctx.lineTo(chartW, yPos);
                ctx.stroke();

                ctx.fillStyle = "#8a99ad";
                ctx.font = "12px 'Roboto Mono', monospace";
                ctx.textAlign = "left";
                ctx.fillText(pVal.toFixed(1), chartW + 8, yPos + 4);
            }}
            ctx.setLineDash([]);

            // 布林通道著色帶
            ctx.fillStyle = "rgba(192, 132, 252, 0.07)";
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_上軌"]) {{
                    const x = getX(idx);
                    const y = getNavY(d["BBAND_上軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            for (let idx = visibleData.length - 1; idx >= 0; idx--) {{
                const d = visibleData[idx];
                if (d["BBAND_下軌"]) {{
                    const x = getX(idx);
                    const y = getNavY(d["BBAND_下軌"]);
                    ctx.lineTo(x, y);
                }}
            }}
            ctx.closePath();
            ctx.fill();

            // 布林上軌 (天藍)
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_上軌"]) {{
                    const x = getX(idx);
                    const y = getNavY(d["BBAND_上軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 布林中軌 (金黃)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_中軌"]) {{
                    const x = getX(idx);
                    const y = getNavY(d["BBAND_中軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 布林下軌 (紫紅)
            ctx.strokeStyle = "#d500f9";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_下軌"]) {{
                    const x = getX(idx);
                    const y = getNavY(d["BBAND_下軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 淨值走勢平滑折線
            ctx.strokeStyle = "rgba(56, 189, 248, 0.70)";
            ctx.lineWidth = 1.8;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getNavY(d["基金淨值"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 【核心淨值圓點 (Dots)】
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getNavY(d["基金淨值"]);
                const isUp = d["基金漲跌"] >= 0;
                const color = isUp ? "#ff333a" : "#00e676";

                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
                ctx.fill();

                ctx.fillStyle = "#ffffff";
                ctx.beginPath();
                ctx.arc(x, y, dotRadius * 0.4, 0, Math.PI * 2);
                ctx.fill();
            }});

            // 波段高低標註
            const highItem = visibleData[maxNavIdx];
            const highX = getX(maxNavIdx);
            const highY = getNavY(highItem["基金淨值"]);
            ctx.fillStyle = "#ff333a";
            ctx.font = "bold 13px 'Roboto Mono', sans-serif";
            ctx.textAlign = highX > chartW - 75 ? "right" : "left";
            ctx.fillText(highItem["基金淨值"].toFixed(2), highX + (highX > chartW - 75 ? -8 : 8), highY - 4);

            const lowItem = visibleData[minNavIdx];
            const lowX = getX(minNavIdx);
            const lowY = getNavY(lowItem["基金淨值"]);
            ctx.fillStyle = "#00e676";
            ctx.font = "bold 13px 'Roboto Mono', sans-serif";
            ctx.textAlign = lowX > chartW - 75 ? "right" : "left";
            ctx.fillText(lowItem["基金淨值"].toFixed(2), lowX + (lowX > chartW - 75 ? -8 : 8), lowY + 16);

            // 右側當前淨值金色高亮標籤
            const curNavY = getNavY(curRecord["基金淨值"]);
            const tagW = rightAxisWidth - 6;
            ctx.fillStyle = "#ffd600";
            ctx.fillRect(chartW + 3, curNavY - 10, tagW, 20);
            ctx.fillStyle = "#000000";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(curRecord["基金淨值"].toFixed(2), chartW + tagW / 2 + 3, curNavY + 4);

            // BBAND 狀態列
            ctx.fillStyle = "#0a0e14";
            ctx.fillRect(0, bbandBarTop, width, bbandBarH);
            ctx.strokeStyle = "#161d28";
            ctx.beginPath();
            ctx.moveTo(0, bbandBarTop);
            ctx.lineTo(width, bbandBarTop);
            ctx.stroke();

            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("BBAND  >", 12, bbandBarTop + 15);
            ctx.fillStyle = "#ffd600";
            ctx.fillText(`20日中軌: ${{curRecord["BBAND_中軌"] || "--"}} ⇂`, 88, bbandBarTop + 15);
            ctx.fillStyle = "#00e5ff";
            ctx.fillText(`上軌(天花板): ${{curRecord["BBAND_上軌"] || "--"}} ⇃`, 210, bbandBarTop + 15);
            ctx.fillStyle = "#d500f9";
            ctx.fillText(`下軌(地板): ${{curRecord["BBAND_下軌"] || "--"}} ⇂`, 370, bbandBarTop + 15);

            // =================================================================
            // 2. 【圖二：加權大盤指數 (TAIEX) K 線圖】 (上移至第二位核心區！充沛高度空間)
            // =================================================================
            let maxT = -Infinity, minT = Infinity;
            let maxTIdx = 0, minTIdx = 0;
            visibleData.forEach((d, idx) => {{
                if (d["大盤最高"] > maxT) {{ maxT = d["大盤最高"]; maxTIdx = idx; }}
                if (d["大盤最低"] < minT) {{ minT = d["大盤最低"]; minTIdx = idx; }}
            }});
            const tPad = (maxT - minT) * 0.08 || 300.0;
            maxT += tPad;
            minT -= tPad;

            function getTaiexY(val) {{
                return taiexTop + taiexH - ((val - minT) / (maxT - minT)) * taiexH;
            }}

            // 大盤刻度格線
            for (let i = 0; i <= 4; i++) {{
                const val = minT + (maxT - minT) * (i / 4);
                const y = getTaiexY(val);
                ctx.strokeStyle = "#141922";
                ctx.setLineDash([2, 4]);
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartW, y);
                ctx.stroke();

                ctx.fillStyle = "#8a99ad";
                ctx.font = "11px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillText(val.toFixed(0), chartW + 8, y + 4);
            }}
            ctx.setLineDash([]);

            // 繪製大盤 K 線 (蠟燭圖：厚實立體紅漲綠跌棒)
            const candleW = Math.max(3.2, Math.min(20, dotSpacing * 0.72));
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const o = d["大盤開盤"];
                const h = d["大盤最高"];
                const l = d["大盤最低"];
                const c = d["大盤收盤"];

                const yO = getTaiexY(o);
                const yH = getTaiexY(h);
                const yL = getTaiexY(l);
                const yC = getTaiexY(c);

                const isRed = c >= o;
                const candleColor = isRed ? "#ff333a" : "#00e676";

                // 上下影線
                ctx.strokeStyle = candleColor;
                ctx.lineWidth = 1.3;
                ctx.beginPath();
                ctx.moveTo(x, yH);
                ctx.lineTo(x, yL);
                ctx.stroke();

                // 實體柱狀
                ctx.fillStyle = candleColor;
                const topY = Math.min(yO, yC);
                const bodyH = Math.max(1.8, Math.abs(yO - yC));
                ctx.fillRect(x - candleW / 2, topY, candleW, bodyH);
            }});

            // 大盤 5MA (天藍色)
            ctx.strokeStyle = "#00e5ff";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["大盤5MA"]) {{
                    const x = getX(idx);
                    const y = getTaiexY(d["大盤5MA"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 大盤 20MA (金黃色)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["大盤20MA"]) {{
                    const x = getX(idx);
                    const y = getTaiexY(d["大盤20MA"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 大盤最高與最低點標註
            const tHighItem = visibleData[maxTIdx];
            const tHighX = getX(maxTIdx);
            const tHighY = getTaiexY(tHighItem["大盤最高"]);
            ctx.fillStyle = "#ff333a";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = tHighX > chartW - 75 ? "right" : "left";
            ctx.fillText(tHighItem["大盤最高"].toFixed(0), tHighX + (tHighX > chartW - 75 ? -8 : 8), tHighY - 4);

            const tLowItem = visibleData[minTIdx];
            const tLowX = getX(minTIdx);
            const tLowY = getTaiexY(tLowItem["大盤最低"]);
            ctx.fillStyle = "#00e676";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = tLowX > chartW - 75 ? "right" : "left";
            ctx.fillText(tLowItem["大盤最低"].toFixed(0), tLowX + (tLowX > chartW - 75 ? -8 : 8), tLowY + 15);

            // 右側大盤最新點位金色標籤
            const curTaiexY = getTaiexY(curRecord["大盤收盤"]);
            ctx.fillStyle = "#ffd600";
            ctx.fillRect(chartW + 3, curTaiexY - 10, tagW, 20);
            ctx.fillStyle = "#000000";
            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(curRecord["大盤收盤"].toFixed(0), chartW + tagW / 2 + 3, curTaiexY + 4);

            // 大盤狀態列
            ctx.fillStyle = "#0a0e14";
            ctx.fillRect(0, taiexBarTop, width, taiexBarH);
            ctx.strokeStyle = "#161d28";
            ctx.beginPath();
            ctx.moveTo(0, taiexBarTop);
            ctx.lineTo(width, taiexBarTop);
            ctx.stroke();

            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("加權大盤指數 (TAIEX)  >", 12, taiexBarTop + 15);

            const tClose = curRecord["大盤收盤"];
            const tDiff = curRecord["大盤漲跌"];
            const tPct = curRecord["大盤漲跌幅"];
            const tIsUp = tDiff >= 0;
            ctx.fillStyle = tIsUp ? "#ff333a" : "#00e676";
            ctx.fillText(`${{tClose.toFixed(2)}} (${{tDiff >= 0 ? "+" : ""}}${{tDiff.toFixed(2)}}, ${{tDiff >= 0 ? "+" : ""}}${{tPct.toFixed(2)}}%) ⇂`, 180, taiexBarTop + 15);

            ctx.fillStyle = "#00e5ff";
            ctx.fillText(`5MA: ${{curRecord["大盤5MA"] ? curRecord["大盤5MA"].toFixed(1) : "--"}}`, 405, taiexBarTop + 15);

            ctx.fillStyle = "#ffd600";
            ctx.fillText(`20MA: ${{curRecord["大盤20MA"] ? curRecord["大盤20MA"].toFixed(1) : "--"}}`, 510, taiexBarTop + 15);

            // =================================================================
            // 時間 X 軸標籤 (位於兩大主圖與下方兩大指標副圖的分水嶺)
            // =================================================================
            ctx.fillStyle = "#05070a";
            ctx.fillRect(0, timeAxisTop, width, timeAxisH);
            ctx.strokeStyle = "#141a22";
            ctx.strokeRect(0, timeAxisTop, width, timeAxisH);

            let lastMonthStr = "";
            ctx.font = "11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#708096";

            visibleData.forEach((d, idx) => {{
                const ym = d["西元日期"].slice(0, 7);
                if (ym !== lastMonthStr && idx > 3) {{
                    const x = getX(idx);
                    ctx.fillText(ym.replace("-", "/"), x, timeAxisTop + 14);
                    lastMonthStr = ym;
                }}
            }});

            if (currentMode === "all") {{
                // =============================================================
                // 3. 【圖三：全市場融資籌碼統計圖 (金黃折線 + 紅增綠減柱狀直方圖)】
                // =============================================================
                ctx.fillStyle = "#0a0e14";
                ctx.fillRect(0, sub2BarTop, width, sub2BarH);
                ctx.font = "bold 11px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillStyle = "#ffffff";
                ctx.fillText("融資餘額  >", 12, sub2BarTop + 15);

                const mBal = curRecord["融資餘額_億"] || 0;
                const mDiff = curRecord["融資增減_億"] || 0;
                const mShares = curRecord["融資餘額_張"] || 0;
                ctx.fillStyle = "#ffd600";
                ctx.fillText(`全市場融資餘額: ${{mBal.toFixed(2)}} 億 (${{mShares.toLocaleString()}} 張) ⇂`, 95, sub2BarTop + 15);

                ctx.fillStyle = mDiff >= 0 ? "#ff333a" : "#00e676";
                ctx.fillText(`當日增減: ${{mDiff >= 0 ? "+" : ""}}${{mDiff.toFixed(2)}} 億`, 375, sub2BarTop + 15);

                let maxM = -Infinity, minM = Infinity;
                visibleData.forEach(d => {{
                    const b = d["融資餘額_億"] || 0;
                    if (b > maxM) maxM = b;
                    if (b < minM) minM = b;
                }});
                const mPad = (maxM - minM) * 0.15 || 40.0;
                maxM += mPad;
                minM -= mPad;

                function getMarginY(val) {{
                    return sub2Top + sub2H - ((val - minM) / (maxM - minM)) * sub2H;
                }}

                // 融資 Y 軸刻度
                const mSteps = [maxM - mPad * 0.4, (maxM + minM) / 2, minM + mPad * 0.4];
                mSteps.forEach(val => {{
                    const y = getMarginY(val);
                    ctx.strokeStyle = "#141922";
                    ctx.setLineDash([2, 4]);
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(chartW, y);
                    ctx.stroke();

                    ctx.fillStyle = "#8a99ad";
                    ctx.font = "11px 'Roboto Mono', sans-serif";
                    ctx.textAlign = "left";
                    ctx.fillText(val.toFixed(0) + "億", chartW + 8, y + 4);
                }});
                ctx.setLineDash([]);

                // 融資增減柱狀圖 (零軸基準線)
                const zeroY = sub2Top + sub2H * 0.68;
                ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, zeroY);
                ctx.lineTo(chartW, zeroY);
                ctx.stroke();

                visibleData.forEach((d, idx) => {{
                    const x = getX(idx);
                    const diff = d["融資增減_億"] || 0;
                    const isPos = diff >= 0;
                    ctx.fillStyle = isPos ? "#ff333a" : "#00e676";
                    const barH = Math.min(sub2H * 0.45, Math.abs(diff) * 2.2);
                    const barW = Math.max(2.5, dotSpacing * 0.55);
                    if (isPos) {{
                        ctx.fillRect(x - barW / 2, zeroY - barH, barW, barH);
                    }} else {{
                        ctx.fillRect(x - barW / 2, zeroY, barW, barH);
                    }}
                }});

                // 融資餘額走勢折線 (三竹金黃色)
                ctx.strokeStyle = "#ffd600";
                ctx.lineWidth = 1.6;
                ctx.beginPath();
                visibleData.forEach((d, idx) => {{
                    const x = getX(idx);
                    const y = getMarginY(d["融資餘額_億"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }});
                ctx.stroke();

                // =============================================================
                // 4. 【圖四：9日KD 體溫計】
                // =============================================================
                ctx.fillStyle = "#0a0e14";
                ctx.fillRect(0, sub1BarTop, width, sub1BarH);
                ctx.font = "bold 11px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillStyle = "#ffffff";
                ctx.fillText("KD  >", 12, sub1BarTop + 15);

                const kVal = curRecord["K值"] || 50;
                const dVal = curRecord["D值"] || 50;
                ctx.fillStyle = "#ffd600";
                ctx.fillText(`9K: ${{kVal.toFixed(2)}} ⇂`, 65, sub1BarTop + 15);

                if (kVal < 20 && dVal < 20) {{
                    ctx.fillStyle = "#00e676";
                    ctx.fillText("低檔鈍化", 155, sub1BarTop + 15);
                }} else if (kVal > 80 && dVal > 80) {{
                    ctx.fillStyle = "#ff3b30";
                    ctx.fillText("高檔鈍化", 155, sub1BarTop + 15);
                }} else if (kVal >= dVal && kVal < 40) {{
                    ctx.fillStyle = "#00e676";
                    ctx.fillText("低檔黃金交叉", 155, sub1BarTop + 15);
                }} else if (kVal >= dVal) {{
                    ctx.fillStyle = "#00e676";
                    ctx.fillText("快線領先", 155, sub1BarTop + 15);
                }} else {{
                    ctx.fillStyle = "#ff3b30";
                    ctx.fillText("慢線壓制", 155, sub1BarTop + 15);
                }}

                ctx.fillStyle = "#00e5ff";
                ctx.fillText(`9D: ${{dVal.toFixed(2)}} ⇂`, 255, sub1BarTop + 15);

                function getKdY(val) {{
                    return sub1Top + sub1H - (Math.max(0, Math.min(100, val)) / 100) * sub1H;
                }}

                // 80, 50, 20 格線
                [80, 50, 20].forEach(val => {{
                    const y = getKdY(val);
                    ctx.strokeStyle = "#141922";
                    ctx.setLineDash([2, 4]);
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(chartW, y);
                    ctx.stroke();

                    ctx.fillStyle = "#64748b";
                    ctx.font = "11px 'Roboto Mono', sans-serif";
                    ctx.textAlign = "left";
                    ctx.fillText(val, chartW + 8, y + 4);
                }});
                ctx.setLineDash([]);

                // 80 超買與 20 超賣著色帶
                ctx.fillStyle = "rgba(220, 38, 38, 0.22)";
                const y80 = getKdY(80);
                ctx.fillRect(0, sub1Top, chartW, y80 - sub1Top);

                ctx.fillStyle = "rgba(16, 185, 129, 0.22)";
                const y20 = getKdY(20);
                ctx.fillRect(0, y20, chartW, sub1Top + sub1H - y20);

                // 9K 線
                ctx.strokeStyle = "#ffd600";
                ctx.lineWidth = 1.4;
                ctx.beginPath();
                visibleData.forEach((d, idx) => {{
                    const x = getX(idx);
                    const y = getKdY(d["K值"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }});
                ctx.stroke();

                // 9D 線
                ctx.strokeStyle = "#00e5ff";
                ctx.lineWidth = 1.4;
                ctx.beginPath();
                visibleData.forEach((d, idx) => {{
                    const x = getX(idx);
                    const y = getKdY(d["D值"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }});
                ctx.stroke();
            }}

            // =================================================================
            // 5. 【金色貫穿四圖查價十字線】
            // =================================================================
            if (selectedIndex !== -1) {{
                const targetIdxInVis = selectedIndex - startIndex;
                if (targetIdxInVis >= 0 && targetIdxInVis < visibleData.length) {{
                    const crossX = getX(targetIdxInVis);
                    const selRecord = visibleData[targetIdxInVis];

                    // 全域垂直金色查價線 (貫穿全部圖表)
                    ctx.strokeStyle = "#ffd600";
                    ctx.lineWidth = 1.2;
                    ctx.setLineDash([]);
                    ctx.beginPath();
                    ctx.moveTo(crossX, fundTop);
                    ctx.lineTo(crossX, height);
                    ctx.stroke();

                    // 基金水平查價線
                    const selNavY = getNavY(selRecord["基金淨值"]);
                    ctx.strokeStyle = "rgba(255, 214, 0, 0.4)";
                    ctx.setLineDash([3, 3]);
                    ctx.beginPath();
                    ctx.moveTo(0, selNavY);
                    ctx.lineTo(chartW, selNavY);
                    ctx.stroke();

                    // 大盤水平查價線 (現在大盤在上半部，查價超直觀！)
                    const selTaiexY = getTaiexY(selRecord["大盤收盤"]);
                    ctx.beginPath();
                    ctx.moveTo(0, selTaiexY);
                    ctx.lineTo(chartW, selTaiexY);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    // 選中之「淨值圓點」金色聚焦光圈
                    ctx.strokeStyle = "#ffd600";
                    ctx.lineWidth = 2.4;
                    ctx.beginPath();
                    ctx.arc(crossX, selNavY, dotRadius + 3.8, 0, Math.PI * 2);
                    ctx.stroke();

                    // 時間軸上的金色日期方塊標籤
                    ctx.fillStyle = "#ffd600";
                    ctx.fillRect(crossX - 44, timeAxisTop, 88, timeAxisH);
                    ctx.fillStyle = "#000000";
                    ctx.font = "bold 11px 'Roboto Mono', sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(selRecord["西元日期"].replace(/-/g, "/"), crossX, timeAxisTop + 14);
                }}
            }}
        }}

        // 查價計算
        function handlePointer(clientX) {{
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const x = clientX - rect.left;
            const rightAxisWidth = 72;
            const chartW = canvas.width / dpr - rightAxisWidth;

            if (x < 18 || x > chartW) return;

            const endIndex = total - 1 - offsetIndex;
            const startIndex = Math.max(0, endIndex - visibleCount + 1);
            const idxInVisible = Math.round((x - 18) / dotSpacing);

            if (idxInVisible >= 0 && startIndex + idxInVisible < total) {{
                selectedIndex = startIndex + idxInVisible;
                updateInspectors(rawData[selectedIndex]);
                render();
            }}
        }}

        // 滑鼠操作事件 (拖曳、點擊)
        canvas.addEventListener("mousedown", (e) => {{
            isDragging = true;
            dragStartX = e.clientX;
            dragStartOffset = offsetIndex;
            handlePointer(e.clientX);
        }});

        window.addEventListener("mousemove", (e) => {{
            if (isDragging) {{
                const dx = e.clientX - dragStartX;
                const shiftDots = Math.round(dx / dotSpacing);
                offsetIndex = Math.max(0, Math.min(total - visibleCount, dragStartOffset + shiftDots));
                render();
            }} else {{
                handlePointer(e.clientX);
            }}
        }});

        window.addEventListener("mouseup", () => {{
            isDragging = false;
        }});

        // 滑鼠滾輪縮放 (平滑縮放天數與間距)
        canvas.addEventListener("wheel", (e) => {{
            if (e.ctrlKey || Math.abs(e.deltaX) > 0 || e.altKey) {{
                e.preventDefault();
            }}
            if (e.deltaY < 0) {{
                // 放大 (更少天數，更寬間距)
                dotSpacing = Math.min(32, dotSpacing + 1.2);
                dotRadius = Math.min(6.5, dotRadius + 0.25);
            }} else if (e.deltaY > 0) {{
                // 縮小 (更多天數，更密間距)
                dotSpacing = Math.max(2.5, dotSpacing - 1.2);
                dotRadius = Math.max(1.8, dotRadius - 0.25);
            }}
            render();
        }}, {{ passive: false }});

        // 鍵盤方向鍵支援
        window.addEventListener("keydown", (e) => {{
            if (e.key === "ArrowLeft") {{
                selectedIndex = Math.max(0, selectedIndex - 1);
                updateInspectors(rawData[selectedIndex]);
                render();
            }} else if (e.key === "ArrowRight") {{
                selectedIndex = Math.min(total - 1, selectedIndex + 1);
                updateInspectors(rawData[selectedIndex]);
                render();
            }} else if (e.key === "Home") {{
                selectedIndex = 0;
                offsetIndex = total - visibleCount;
                updateInspectors(rawData[selectedIndex]);
                render();
            }} else if (e.key === "End") {{
                selectedIndex = total - 1;
                offsetIndex = 0;
                updateInspectors(rawData[selectedIndex]);
                render();
            }}
        }});

        // 週期切換按鈕
        document.querySelectorAll("[data-days]").forEach(btn => {{
            btn.addEventListener("click", (e) => {{
                document.querySelectorAll("[data-days]").forEach(b => {{
                    b.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white transition";
                }});
                e.target.className = "px-2.5 py-1 rounded bg-sky-600 text-white shadow-xs";

                const days = parseInt(e.target.dataset.days, 10);
                const dpr = window.devicePixelRatio || 1;
                const chartW = canvas.width / dpr - 72;
                
                const targetCount = Math.min(total, days);
                dotSpacing = Math.max(2.5, Math.min(32, chartW / targetCount));
                dotRadius = Math.max(1.8, Math.min(5.5, dotSpacing * 0.32));
                offsetIndex = 0;
                selectedIndex = total - 1;
                updateInspectors(rawData[selectedIndex]);
                render();
            }});
        }});

        // 視圖切換 (四圖連動 vs 雙主圖對比)
        const btnAll = document.getElementById("viewAllCharts");
        const btnDual = document.getElementById("viewDualMain");

        btnAll.addEventListener("click", () => {{
            currentMode = "all";
            btnAll.className = "px-2.5 py-1 rounded bg-sky-600 text-white shadow-xs";
            btnDual.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white transition";
            resizeCanvas();
        }});

        btnDual.addEventListener("click", () => {{
            currentMode = "dual";
            btnDual.className = "px-2.5 py-1 rounded bg-sky-600 text-white shadow-xs";
            btnAll.className = "px-2.5 py-1 rounded text-slate-400 hover:text-white transition";
            resizeCanvas();
        }});

        // 縮放與重設
        document.getElementById("btnZoomIn").addEventListener("click", () => {{
            dotSpacing = Math.min(32, dotSpacing + 2.0);
            dotRadius = Math.min(6.5, dotRadius + 0.3);
            render();
        }});

        document.getElementById("btnZoomOut").addEventListener("click", () => {{
            dotSpacing = Math.max(2.5, dotSpacing - 2.0);
            dotRadius = Math.max(1.8, dotRadius - 0.3);
            render();
        }});

        document.getElementById("btnReset").addEventListener("click", () => {{
            offsetIndex = 0;
            selectedIndex = total - 1;
            updateInspectors(rawData[selectedIndex]);
            render();
        }});

        // 切換側欄
        document.getElementById("btnToggleSide").addEventListener("click", () => {{
            const panel = document.getElementById("sidePanel");
            panel.classList.toggle("hidden");
            setTimeout(resizeCanvas, 30);
        }});

        // 初始化
        window.addEventListener("DOMContentLoaded", () => {{
            resizeCanvas();
            selectedIndex = total - 1;
            updateInspectors(rawData[selectedIndex]);
        }});
    </script>
</body>
</html>
'''
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    with open("code_artifact.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"成功產出全新排版四圖聯動看盤工作站：{output_path}、index.html 與 code_artifact.html！")

if __name__ == "__main__":
    generate_desktop_html()
