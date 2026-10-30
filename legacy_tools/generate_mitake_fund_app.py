# -*- coding: utf-8 -*-
"""
從 SQLite「股市資料庫.db」讀取：
1. 基金 Table: 統一奔騰基金淨值、布林通道 (20日中軌/上軌/下軌)、9日KD (K值/D值/RSV)
2. 融資餘額 Table: 全市場融資餘額、融資增減
產出 100% 仿三竹 APP 風格的「統一奔騰基金」專用看盤系統：
- 主圖捨棄 K 線，以「淨值圓點 (Dots) + 走勢線 + 布林通道 (BBAND)」呈現
- 副圖一為 9日KD 體溫計
- 副圖二為市場融資餘額與增減柱狀圖
- 金色垂直穿透十字查價線，支援手機外殼模擬與全螢幕展開模式
"""

import sqlite3
import json
import pandas as pd

DB_FILE = "股市資料庫.db"
OUTPUT_HTML = "mitake_fund_interactive.html"

def generate_fund_mitake_html(output_path=OUTPUT_HTML):
    conn = sqlite3.connect(DB_FILE)
    
    # 1. 讀取「基金」Table 中的統一奔騰資料
    df_fund = pd.read_sql_query('SELECT * FROM "基金" WHERE 基金名稱 = "統一奔騰" ORDER BY 西元日期 ASC;', conn)
    
    # 2. 讀取「融資餘額」Table
    df_margin = pd.read_sql_query('SELECT 西元日期, 融資今日餘額_張, 融資今日餘額_仟元, 融資增減_仟元 FROM "融資餘額" ORDER BY 西元日期 ASC;', conn)
    conn.close()
    
    if df_fund.empty:
        print("未在資料庫中找到基金資料！")
        return
        
    # 合併兩表 (以西元日期進行 LEFT JOIN)
    df_merged = pd.merge(df_fund, df_margin, on="西元日期", how="left")
    
    # 處理空值
    df_merged["融資今日餘額_仟元"] = df_merged["融資今日餘額_仟元"].ffill().fillna(0)
    df_merged["融資增減_仟元"] = df_merged["融資增減_仟元"].fillna(0)
    df_merged["融資今日餘額_張"] = df_merged["融資今日餘額_張"].ffill().fillna(0)
    
    # 整理為前端所需的欄位
    records = []
    for _, row in df_merged.iterrows():
        # 融資金額轉換為億元顯示
        margin_yi = round(float(row["融資今日餘額_仟元"]) / 100000.0, 2)
        diff_yi = round(float(row["融資增減_仟元"]) / 100000.0, 2)
        
        records.append({
            "西元日期": str(row["西元日期"]),
            "日期": str(row["日期"]),
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
            "融資餘額_億": margin_yi,
            "融資增減_億": diff_yi,
            "融資餘額_張": int(row["融資今日餘額_張"])
        })
        
    json_data = json.dumps(records, ensure_ascii=False)
    total_records = len(records)
    latest = records[-1]
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>三竹股市 APP - 統一奔騰基金 (淨值圓點+布林通道+KD+融資餘額)</title>
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
            background-color: #0b0d11;
            color: #ffffff;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
        }}
        
        /* 三竹 APP 經典高對比配色 */
        .color-up {{
            color: #ff333a !important; /* 三竹漲紅 */
        }}
        .color-down {{
            color: #00e676 !important; /* 三竹跌綠 */
        }}
        .color-yellow {{
            color: #ffd600 !important; /* 三竹金黃 */
        }}
        .color-cyan {{
            color: #00e5ff !important; /* 三竹天藍 */
        }}
        .color-purple {{
            color: #d500f9 !important; /* 三竹下軌紫 */
        }}
        
        /* 手機外殼容器 */
        .phone-wrapper {{
            max-width: 440px;
            width: 100%;
            height: 920px;
            background: #000000;
            border-radius: 40px;
            box-shadow: 0 25px 65px -15px rgba(0, 0, 0, 0.95), 0 0 0 10px #20242b, 0 0 0 12px #323842;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            position: relative;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        /* 全螢幕桌面模式 */
        .full-mode {{
            max-width: 100% !important;
            height: 100vh !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }}

        canvas {{
            display: block;
            touch-action: none;
        }}
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-0 sm:p-4 md:p-6 bg-[#08090c]">

    <!-- 主容器 -->
    <div id="appContainer" class="phone-wrapper mx-auto">
        
        <!-- 頂部手機狀態列 (Status Bar) -->
        <div class="h-6 px-5 flex items-center justify-between text-[11px] font-bold text-slate-300 bg-black tracking-tight select-none z-30">
            <span>11:05</span>
            <div class="flex items-center gap-1.5 text-[10px]">
                <span class="text-[9px] text-slate-400 font-mono">0.12 KB/s</span>
                <i class="ph-fill ph-cell-signal-full text-white"></i>
                <span class="text-[9px] font-extrabold text-white">4G+</span>
                <div class="flex items-center border border-slate-400 rounded-sm px-0.5 text-[9px] leading-tight">38</div>
            </div>
        </div>

        <!-- 頂部 APP 導覽列 (三竹風格) -->
        <div class="h-11 px-3 bg-[#001728] border-b border-[#0f2d48] flex items-center justify-between z-20 select-none">
            <button id="btnBack" class="p-1 text-slate-300 hover:text-white transition">
                <i class="ph-bold ph-caret-left text-2xl"></i>
            </button>

            <!-- 標的名稱與代碼 -->
            <div class="text-center cursor-pointer">
                <div class="text-sm font-black text-white leading-tight tracking-wide flex items-center justify-center gap-1.5">
                    統一奔騰基金
                    <span class="text-[9px] px-1.5 py-0.2 rounded bg-sky-950 text-sky-300 border border-sky-800">淨值圓點</span>
                </div>
                <div class="text-[11px] font-bold text-[#00e5ff] leading-none mt-0.5">10YTW (國內股票科技型)</div>
            </div>

            <div class="flex items-center gap-1">
                <!-- 滿版全螢幕切換 -->
                <button id="btnToggleMode" class="p-1.5 text-slate-300 hover:text-white text-xs bg-[#0b2844] rounded border border-[#1b436c]" title="切換手機/滿版模式">
                    <i class="ph-bold ph-arrows-out-simple"></i>
                </button>
                <button class="p-1 text-slate-300 hover:text-white">
                    <i class="ph-bold ph-list text-xl"></i>
                </button>
            </div>
        </div>

        <!-- 查價資訊欄 (Crosshair Info Bar) - 專為基金設計 -->
        <div id="crossInfoBar" class="h-8 px-2.5 bg-[#05070a] border-b border-[#1a1f26] flex items-center justify-between text-[11px] font-mono select-none z-20">
            <div class="flex items-center gap-2 overflow-x-auto whitespace-nowrap">
                <span class="color-yellow font-bold">時 <span id="infoDate">10/29</span></span>
                <span>淨值 <span id="infoNav" class="color-down">726.38</span></span>
                <span>漲跌 <span id="infoChange" class="color-down">-21.58</span></span>
                <span>幅度 <span id="infoPct" class="color-down">-2.89%</span></span>
                <span class="color-purple">20日均 <span id="infoMA20">792.24</span></span>
                <span class="color-cyan">前低距 <span id="infoGap">+14.41</span></span>
            </div>
            <button id="btnCloseCross" class="w-4 h-4 rounded-full bg-[#1e232a] text-slate-400 hover:text-white flex items-center justify-center text-[10px] ml-1">✕</button>
        </div>

        <!-- 畫布滾動繪圖區 (三圖連動：主圖淨值圓點+布林通道、副圖一KD、副圖二融資餘額) -->
        <div class="flex-1 bg-black relative overflow-hidden flex flex-col" id="chartWrapper">
            <canvas id="mainCanvas" class="w-full flex-1"></canvas>
            
            <!-- 懸浮半透明手動控制器 (◀ 平移、＋ 放大、息 標示、－ 縮小、▶ 平移) -->
            <div class="absolute top-[48%] left-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-1.5 bg-[#14171dc0] backdrop-blur-xs px-2.5 py-1 rounded-full border border-slate-700/60 shadow-lg pointer-events-auto opacity-70 hover:opacity-100 transition z-10">
                <button id="btnScrollLeft" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs">◀</button>
                <button id="btnZoomIn" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs font-bold">＋</button>
                <div class="w-5 h-5 rounded-full border border-sky-500/70 text-[10px] text-sky-300 flex items-center justify-center font-bold">點</div>
                <button id="btnZoomOut" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs font-bold">－</button>
                <button id="btnScrollRight" class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 hover:text-white flex items-center justify-center text-xs">▶</button>
            </div>
        </div>

        <!-- 底部狀態列 -->
        <div class="h-8 bg-[#090d13] border-t border-[#1e242d] px-3 flex items-center justify-between text-[11px] text-slate-400 select-none z-20">
            <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span class="font-bold text-slate-300">股市資料庫.db ➔ 基金Table & 融資餘額Table</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-[10px] text-slate-400 font-mono">共 {total_records} 筆</span>
                <button id="btnResetView" class="text-sky-400 hover:text-sky-300 font-bold text-[10px] bg-[#121820] px-2 py-0.5 rounded border border-[#232d3b]">最新淨值</button>
            </div>
        </div>

    </div>

    <!-- 高性能 Canvas 繪圖引擎 (淨值圓點 + 布林帶 + KD + 融資餘額) -->
    <script>
        const rawDatabaseRecords = {json_data};

        let canvas = document.getElementById("mainCanvas");
        let ctx = canvas.getContext("2d");
        
        let dotSpacing = 8.5;       // 每個圓點水平間距
        let dotRadius = 3.2;        // 圓點基本半徑
        let visibleCount = 55;      // 視野內顯示之天數
        let offsetIndex = 0;        // 偏移量 (0 代表最新，向左推移為正)
        let selectedIndex = -1;     // 十字線選取的索引 (-1 為最新一筆)
        let isDragging = false;
        let dragStartX = 0;
        let dragStartOffset = 0;

        // 更新視窗大小
        function resizeCanvas() {{
            const wrapper = document.getElementById("chartWrapper");
            const dpr = window.devicePixelRatio || 1;
            canvas.width = wrapper.clientWidth * dpr;
            canvas.height = wrapper.clientHeight * dpr;
            ctx.scale(dpr, dpr);
            render();
        }}

        window.addEventListener("resize", resizeCanvas);

        // 更新頂部查價資訊
        function updateTopBar(record) {{
            if (!record) return;
            const parts = record["西元日期"].split("-");
            document.getElementById("infoDate").textContent = `${{parts[1]}}/${{parts[2]}}`;
            
            const nav = record["基金淨值"];
            const diff = record["基金漲跌"];
            const pct = record["基金漲跌幅"];
            const ma20 = record["20MA"] || record["BBAND_中軌"] || 0;

            const navEl = document.getElementById("infoNav");
            const changeEl = document.getElementById("infoChange");
            const pctEl = document.getElementById("infoPct");
            const ma20El = document.getElementById("infoMA20");
            const gapEl = document.getElementById("infoGap");

            navEl.textContent = nav.toFixed(2);
            
            const sign = diff > 0 ? "+" : "";
            changeEl.textContent = `${{sign}}${{diff.toFixed(2)}}`;
            pctEl.textContent = `${{sign}}${{pct.toFixed(2)}}%`;
            ma20El.textContent = ma20 ? ma20.toFixed(2) : "--";

            // 距離全波段低點 (711.97) 差距
            const baseLowest = 711.97;
            const gapVal = +(nav - baseLowest).toFixed(2);
            gapEl.textContent = `${{gapVal >= 0 ? "+" : ""}}${{gapVal.toFixed(2)}}`;
            gapEl.className = gapVal >= 0 ? "color-cyan font-bold" : "color-down font-bold";

            const colorClass = diff > 0 ? "color-up" : (diff < 0 ? "color-down" : "text-slate-300");
            navEl.className = colorClass;
            changeEl.className = colorClass;
            pctEl.className = colorClass;
        }}

        // 主繪圖函式
        function render() {{
            const total = rawDatabaseRecords.length;
            if (total === 0) return;

            const dpr = window.devicePixelRatio || 1;
            const width = canvas.width / dpr;
            const height = canvas.height / dpr;

            ctx.clearRect(0, 0, width, height);

            // 比例分區
            // 主圖 (淨值圓點 + 布林通道): 48%
            // BBAND 資訊條: 22px
            // 時間 X 軸: 18px
            // 副圖一 KD: 22% (含標題條 20px)
            // 副圖二 融資餘額: 22% (含標題條 20px)
            
            const rightAxisWidth = 54;
            const chartW = width - rightAxisWidth;

            const mainTop = 8;
            const mainH = height * 0.44;
            const bbandBarTop = mainTop + mainH;
            const bbandBarH = 22;

            const timeAxisTop = bbandBarTop + bbandBarH;
            const timeAxisH = 18;

            const sub1BarTop = timeAxisTop + timeAxisH;
            const sub1BarH = 20;
            const sub1Top = sub1BarTop + sub1BarH;
            const sub1H = height * 0.19;

            const sub2BarTop = sub1Top + sub1H + 4;
            const sub2BarH = 20;
            const sub2Top = sub2BarTop + sub2BarH;
            const sub2H = height - sub2Top - 4;

            // 計算可視天數
            visibleCount = Math.floor(chartW / dotSpacing);
            let endIndex = total - 1 - offsetIndex;
            endIndex = Math.max(visibleCount - 1, Math.min(total - 1, endIndex));
            let startIndex = Math.max(0, endIndex - visibleCount + 1);

            const visibleData = rawDatabaseRecords.slice(startIndex, endIndex + 1);
            if (visibleData.length === 0) return;

            // 尋找主圖最高、最低淨值 (包含 BBAND)
            let maxP = -Infinity;
            let minP = Infinity;
            let maxIdx = 0;
            let minIdx = 0;

            visibleData.forEach((d, idx) => {{
                const h = Math.max(d["基金淨值"], d["BBAND_上軌"] || d["基金淨值"]);
                const l = Math.min(d["基金淨值"], d["BBAND_下軌"] || d["基金淨值"]);
                if (h > maxP) {{ maxP = h; maxIdx = idx; }}
                if (l < minP) {{ minP = l; minIdx = idx; }}
            }});

            const pricePad = (maxP - minP) * 0.08 || 10.0;
            maxP += pricePad;
            minP -= pricePad;

            function getY(p) {{
                return mainTop + mainH - ((p - minP) / (maxP - minP)) * mainH;
            }}

            function getX(idxInVisible) {{
                return 12 + idxInVisible * dotSpacing;
            }}

            // 1. 主圖水平網格線
            ctx.strokeStyle = "#161a22";
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 4]);

            const pSteps = 4;
            for (let i = 0; i <= pSteps; i++) {{
                const pVal = minP + (maxP - minP) * (i / pSteps);
                const yPos = getY(pVal);
                ctx.beginPath();
                ctx.moveTo(0, yPos);
                ctx.lineTo(chartW, yPos);
                ctx.stroke();

                // 右側刻度文字
                ctx.fillStyle = "#8292a4";
                ctx.font = "11px 'Roboto Mono', monospace";
                ctx.textAlign = "left";
                ctx.fillText(pVal.toFixed(0), chartW + 6, yPos + 4);
            }}
            ctx.setLineDash([]);

            // 2. 繪製布林通道 (BBAND)
            // 布林通道背景漸層填充
            ctx.fillStyle = "rgba(192, 132, 252, 0.06)";
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_上軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_上軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            for (let idx = visibleData.length - 1; idx >= 0; idx--) {{
                const d = visibleData[idx];
                if (d["BBAND_下軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_下軌"]);
                    ctx.lineTo(x, y);
                }}
            }}
            ctx.closePath();
            ctx.fill();

            // 上軌 (天藍色)
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_上軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_上軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 中軌 (金黃色)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_中軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_中軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 下軌 (紫紅色)
            ctx.strokeStyle = "#d500f9";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                if (d["BBAND_下軌"]) {{
                    const x = getX(idx);
                    const y = getY(d["BBAND_下軌"]);
                    idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }}
            }});
            ctx.stroke();

            // 3. 繪製基金淨值走勢折線 (細緻天藍色半透明連線)
            ctx.strokeStyle = "rgba(56, 189, 248, 0.65)";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getY(d["基金淨值"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 4. 【核心需求】：繪製「淨值圓點 (Dots)」
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getY(d["基金淨值"]);
                const diff = d["基金漲跌"];
                
                // 漲紅跌綠
                const dotColor = diff >= 0 ? "#ff333a" : "#00e676";
                
                // 圓點光暈底層
                ctx.fillStyle = dotColor;
                ctx.beginPath();
                ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
                ctx.fill();

                // 內芯微高光
                ctx.fillStyle = "#ffffff";
                ctx.beginPath();
                ctx.arc(x, y, dotRadius * 0.45, 0, Math.PI * 2);
                ctx.fill();
            }});

            // 5. 波段極值標註 (最高點與最低點)
            const highItem = visibleData[maxIdx];
            const highX = getX(maxIdx);
            const highY = getY(highItem["基金淨值"]);
            ctx.fillStyle = "#ff333a";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = highX > chartW - 50 ? "right" : "left";
            ctx.fillText(highItem["基金淨值"].toFixed(2), highX + (highX > chartW - 50 ? -6 : 6), highY - 4);

            const lowItem = visibleData[minIdx];
            const lowX = getX(minIdx);
            const lowY = getY(lowItem["基金淨值"]);
            ctx.fillStyle = "#00e676";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = lowX > chartW - 50 ? "right" : "left";
            ctx.fillText(lowItem["基金淨值"].toFixed(2), lowX + (lowX > chartW - 50 ? -6 : 6), lowY + 14);

            // 6. 右側 Y 軸上的黃底黑字當前淨值標籤
            const curRecord = rawDatabaseRecords[selectedIndex !== -1 ? selectedIndex : total - 1];
            const curY = getY(curRecord["基金淨值"]);
            const tagW = rightAxisWidth - 2;
            const tagH = 18;

            ctx.fillStyle = "#ffd600";
            ctx.fillRect(chartW + 2, curY - tagH / 2, tagW, tagH);
            ctx.fillStyle = "#000000";
            ctx.font = "bold 12px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(curRecord["基金淨值"].toFixed(2), chartW + tagW / 2 + 2, curY + 4);

            // 下方漲跌色塊標籤
            const diffVal = curRecord["基金漲跌"];
            const pctVal = curRecord["基金漲跌幅"];
            ctx.fillStyle = diffVal >= 0 ? "#ff333a" : "#00e676";
            ctx.font = "bold 9px 'Roboto Mono', sans-serif";
            const signStr = diffVal >= 0 ? "▲+" : "▼";
            ctx.fillText(`${{signStr}}${{Math.abs(diffVal).toFixed(2)}}`, chartW + tagW / 2 + 2, curY + tagH / 2 + 10);
            ctx.fillText(`${{pctVal >= 0 ? "+" : ""}}${{pctVal.toFixed(2)}}%`, chartW + tagW / 2 + 2, curY + tagH / 2 + 20);

            // 7. BBAND 資訊條 (中軌、上軌、下軌數值)
            ctx.fillStyle = "#0d1117";
            ctx.fillRect(0, bbandBarTop, width, bbandBarH);
            ctx.strokeStyle = "#1a222d";
            ctx.beginPath();
            ctx.moveTo(0, bbandBarTop);
            ctx.lineTo(width, bbandBarTop);
            ctx.stroke();

            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("BBAND >", 8, bbandBarTop + 15);

            ctx.fillStyle = "#ffd600";
            ctx.fillText(`中軌:${{curRecord["BBAND_中軌"] || "--"}}⇂`, 72, bbandBarTop + 15);

            ctx.fillStyle = "#00e5ff";
            ctx.fillText(`上軌:${{curRecord["BBAND_上軌"] || "--"}}⇃`, 150, bbandBarTop + 15);

            ctx.fillStyle = "#d500f9";
            ctx.fillText(`下軌:${{curRecord["BBAND_下軌"] || "--"}}⇂`, 225, bbandBarTop + 15);

            // 右側「絕對值」按鈕
            ctx.fillStyle = "#222730";
            ctx.fillRect(width - 50, bbandBarTop + 2, 44, 18);
            ctx.strokeStyle = "#38414e";
            ctx.strokeRect(width - 50, bbandBarTop + 2, 44, 18);
            ctx.fillStyle = "#cbd5e1";
            ctx.font = "10px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("絕對值", width - 28, bbandBarTop + 14);

            // 8. 時間 X 軸 (月份與日期刻度)
            ctx.fillStyle = "#05070a";
            ctx.fillRect(0, timeAxisTop, width, timeAxisH);
            ctx.strokeStyle = "#1a1f26";
            ctx.strokeRect(0, timeAxisTop, width, timeAxisH);

            let lastMonth = "";
            ctx.font = "10px 'Roboto Mono', sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = "#64748b";

            visibleData.forEach((d, idx) => {{
                const m = d["西元日期"].split("-")[1];
                if (m !== lastMonth && idx > 4) {{
                    const x = getX(idx);
                    ctx.fillText(m, x, timeAxisTop + 13);
                    lastMonth = m;
                }}
            }});

            // 9. 副圖一：9日KD 指標 (來自基金 Table)
            ctx.fillStyle = "#0d1117";
            ctx.fillRect(0, sub1BarTop, width, sub1BarH);
            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("KD  >", 8, sub1BarTop + 14);

            const kVal = curRecord["K值"] || 50;
            const dVal = curRecord["D值"] || 50;

            ctx.fillStyle = "#ffd600";
            ctx.fillText(`9K:${{kVal.toFixed(2)}}⇂`, 50, sub1BarTop + 14);

            // KD 狀態判定文字 (三竹截圖綠色/紅色標籤)
            if (kVal < 20 && dVal < 20) {{
                ctx.fillStyle = "#00e676";
                ctx.fillText("低檔鈍化", 125, sub1BarTop + 14);
            }} else if (kVal > 80 && dVal > 80) {{
                ctx.fillStyle = "#ff3b30";
                ctx.fillText("高檔鈍化", 125, sub1BarTop + 14);
            }} else if (kVal >= dVal && kVal < 40) {{
                ctx.fillStyle = "#00e676";
                ctx.fillText("低檔黃金交叉", 125, sub1BarTop + 14);
            }} else if (kVal >= dVal) {{
                ctx.fillStyle = "#00e676";
                ctx.fillText("快線領先", 125, sub1BarTop + 14);
            }} else {{
                ctx.fillStyle = "#ff3b30";
                ctx.fillText("慢線壓制", 125, sub1BarTop + 14);
            }}

            ctx.fillStyle = "#00e5ff";
            ctx.fillText(`9D:${{dVal.toFixed(2)}}⇂`, 205, sub1BarTop + 14);

            // 右側 KD 刻度 (20, 50, 80)
            [80, 50, 20].forEach(val => {{
                const y = sub1Top + sub1H - (val / 100) * sub1H;
                ctx.strokeStyle = "#161b22";
                ctx.setLineDash([2, 4]);
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartW, y);
                ctx.stroke();

                ctx.fillStyle = "#64748b";
                ctx.font = "10px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillText(val, chartW + 6, y + 3);
            }});
            ctx.setLineDash([]);

            function getKdY(val) {{
                return sub1Top + sub1H - (Math.max(0, Math.min(100, val)) / 100) * sub1H;
            }}

            // 80 超買與 20 超賣背景著色帶
            ctx.fillStyle = "rgba(220, 38, 38, 0.22)";
            const y80 = getKdY(80);
            ctx.fillRect(0, sub1Top, chartW, y80 - sub1Top);

            ctx.fillStyle = "rgba(16, 185, 129, 0.22)";
            const y20 = getKdY(20);
            ctx.fillRect(0, y20, chartW, sub1Top + sub1H - y20);

            // 9K 線 (金黃色)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getKdY(d["K值"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 9D 線 (天藍色)
            ctx.strokeStyle = "#00e5ff";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getKdY(d["D值"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 10. 副圖二：全市場融資餘額 (來自融資餘額 Table)
            ctx.fillStyle = "#0d1117";
            ctx.fillRect(0, sub2BarTop, width, sub2BarH);
            ctx.font = "bold 11px 'Roboto Mono', sans-serif";
            ctx.textAlign = "left";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("融資餘額 >", 8, sub2BarTop + 14);

            const mBal = curRecord["融資餘額_億"] || 0;
            const mDiff = curRecord["融資增減_億"] || 0;
            ctx.fillStyle = "#ffd600";
            ctx.fillText(`融資餘額:${{mBal.toFixed(2)}}億⇂`, 74, sub2BarTop + 14);

            ctx.fillStyle = mDiff >= 0 ? "#ff333a" : "#00e676";
            ctx.fillText(`融資增減:${{mDiff >= 0 ? "+" : ""}}${{mDiff.toFixed(2)}}億`, 215, sub2BarTop + 14);

            // 計算融資金額範圍
            let maxM = -Infinity;
            let minM = Infinity;
            visibleData.forEach(d => {{
                const b = d["融資餘額_億"] || 0;
                if (b > maxM) maxM = b;
                if (b < minM) minM = b;
            }});
            const mPad = (maxM - minM) * 0.15 || 50.0;
            maxM += mPad;
            minM -= mPad;

            function getMarginY(val) {{
                return sub2Top + sub2H - ((val - minM) / (maxM - minM)) * sub2H;
            }}

            // 融資網格刻度
            const mSteps = [maxM - mPad*0.5, (maxM + minM)/2, minM + mPad*0.5];
            mSteps.forEach(val => {{
                const y = getMarginY(val);
                ctx.strokeStyle = "#161b22";
                ctx.setLineDash([2, 4]);
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(chartW, y);
                ctx.stroke();

                ctx.fillStyle = "#64748b";
                ctx.font = "10px 'Roboto Mono', sans-serif";
                ctx.textAlign = "left";
                ctx.fillText(val.toFixed(0) + "億", chartW + 2, y + 3);
            }});
            ctx.setLineDash([]);

            // 融資增減柱狀圖
            const zeroY = sub2Top + sub2H * 0.65;
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const diff = d["融資增減_億"] || 0;
                const isPos = diff >= 0;
                ctx.fillStyle = isPos ? "#ff333a" : "#00e676";
                const barH = Math.min(sub2H * 0.45, Math.abs(diff) * 1.5);
                if (isPos) {{
                    ctx.fillRect(x - dotRadius, zeroY - barH, dotRadius * 2, barH);
                }} else {{
                    ctx.fillRect(x - dotRadius, zeroY, dotRadius * 2, barH);
                }}
            }});

            // 融資餘額走勢折線 (金黃色)
            ctx.strokeStyle = "#ffd600";
            ctx.lineWidth = 1.3;
            ctx.beginPath();
            visibleData.forEach((d, idx) => {{
                const x = getX(idx);
                const y = getMarginY(d["融資餘額_億"]);
                idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // 11. 垂直金色查價十字線 (選取時貫穿三圖)
            if (selectedIndex !== -1) {{
                const targetIdxInVis = selectedIndex - startIndex;
                if (targetIdxInVis >= 0 && targetIdxInVis < visibleData.length) {{
                    const crossX = getX(targetIdxInVis);
                    ctx.strokeStyle = "#ffd600";
                    ctx.lineWidth = 1.0;
                    ctx.setLineDash([]);
                    ctx.beginPath();
                    ctx.moveTo(crossX, mainTop);
                    ctx.lineTo(crossX, height);
                    ctx.stroke();

                    // 高亮當前被選取的「淨值圓點」
                    const selRecord = visibleData[targetIdxInVis];
                    const selY = getY(selRecord["基金淨值"]);
                    
                    ctx.strokeStyle = "#ffd600";
                    ctx.lineWidth = 2.0;
                    ctx.beginPath();
                    ctx.arc(crossX, selY, dotRadius + 3.0, 0, Math.PI * 2);
                    ctx.stroke();

                    // 時間軸上的金色日期小標籤
                    ctx.fillStyle = "#ffd600";
                    ctx.fillRect(crossX - 35, timeAxisTop, 70, timeAxisH);
                    ctx.fillStyle = "#000000";
                    ctx.font = "bold 10px 'Roboto Mono', sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(selRecord["西元日期"].replace(/-/g, "/"), crossX, timeAxisTop + 13);
                }}
            }}
        }}

        // 觸控與滑鼠事件 (平移與查價)
        function handlePointerMove(clientX) {{
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const x = clientX - rect.left;
            const rightAxisWidth = 54;
            const chartW = canvas.width / dpr - rightAxisWidth;

            if (x < 10 || x > chartW) return;

            const total = rawDatabaseRecords.length;
            const endIndex = total - 1 - offsetIndex;
            const startIndex = Math.max(0, endIndex - visibleCount + 1);
            const idxInVisible = Math.round((x - 12) / dotSpacing);

            if (idxInVisible >= 0 && startIndex + idxInVisible < total) {{
                selectedIndex = startIndex + idxInVisible;
                updateTopBar(rawDatabaseRecords[selectedIndex]);
                render();
            }}
        }}

        canvas.addEventListener("mousedown", (e) => {{
            isDragging = true;
            dragStartX = e.clientX;
            dragStartOffset = offsetIndex;
            handlePointerMove(e.clientX);
        }});

        window.addEventListener("mousemove", (e) => {{
            if (isDragging) {{
                const dx = e.clientX - dragStartX;
                const shiftDots = Math.round(dx / dotSpacing);
                offsetIndex = Math.max(0, Math.min(rawDatabaseRecords.length - visibleCount, dragStartOffset + shiftDots));
                render();
            }} else {{
                handlePointerMove(e.clientX);
            }}
        }});

        window.addEventListener("mouseup", () => {{
            isDragging = false;
        }});

        // 觸控支援
        canvas.addEventListener("touchstart", (e) => {{
            if (e.touches.length === 1) {{
                isDragging = true;
                dragStartX = e.touches[0].clientX;
                dragStartOffset = offsetIndex;
                handlePointerMove(e.touches[0].clientX);
            }}
        }}, {{ passive: true }});

        canvas.addEventListener("touchmove", (e) => {{
            if (e.touches.length === 1) {{
                const dx = e.touches[0].clientX - dragStartX;
                if (Math.abs(dx) > 8) {{
                    const shiftDots = Math.round(dx / dotSpacing);
                    offsetIndex = Math.max(0, Math.min(rawDatabaseRecords.length - visibleCount, dragStartOffset + shiftDots));
                }}
                handlePointerMove(e.touches[0].clientX);
            }}
        }}, {{ passive: true }});

        canvas.addEventListener("touchend", () => {{
            isDragging = false;
        }});

        // 懸浮按鈕操作
        document.getElementById("btnScrollLeft").addEventListener("click", () => {{
            offsetIndex = Math.min(rawDatabaseRecords.length - visibleCount, offsetIndex + 12);
            render();
        }});

        document.getElementById("btnScrollRight").addEventListener("click", () => {{
            offsetIndex = Math.max(0, offsetIndex - 12);
            render();
        }});

        document.getElementById("btnZoomIn").addEventListener("click", () => {{
            dotSpacing = Math.min(18, dotSpacing + 1.5);
            dotRadius = Math.min(5.5, dotRadius + 0.4);
            render();
        }});

        document.getElementById("btnZoomOut").addEventListener("click", () => {{
            dotSpacing = Math.max(3.5, dotSpacing - 1.5);
            dotRadius = Math.max(2.0, dotRadius - 0.4);
            render();
        }});

        // 重設視圖 (最新位置)
        document.getElementById("btnResetView").addEventListener("click", () => {{
            offsetIndex = 0;
            selectedIndex = rawDatabaseRecords.length - 1;
            updateTopBar(rawDatabaseRecords[selectedIndex]);
            render();
        }});

        // 關閉查價鈕
        document.getElementById("btnCloseCross").addEventListener("click", () => {{
            selectedIndex = rawDatabaseRecords.length - 1;
            updateTopBar(rawDatabaseRecords[selectedIndex]);
            render();
        }});

        // 切換手機外殼 / 桌面全螢幕滿版模式
        document.getElementById("btnToggleMode").addEventListener("click", () => {{
            const app = document.getElementById("appContainer");
            app.classList.toggle("full-mode");
            setTimeout(resizeCanvas, 50);
        }});

        // 頁面加載完成時初始化
        window.addEventListener("DOMContentLoaded", () => {{
            resizeCanvas();
            selectedIndex = rawDatabaseRecords.length - 1;
            updateTopBar(rawDatabaseRecords[selectedIndex]);
        }});
    </script>
</body>
</html>
'''
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"成功產出基金專用三竹看盤互動網頁：{output_path}！")

if __name__ == "__main__":
    generate_fund_mitake_html()
