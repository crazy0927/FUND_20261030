# -*- coding: utf-8 -*-
"""
從 SQLite「股市資料庫.db」的「基金」Table 讀取真實資料，
產出高互動性、雙圖連動之 Plotly.js 統計看盤系統 HTML 頁面。
"""

import sqlite3
import json
import os
import pandas as pd

DB_FILE = "股市資料庫.db"
TABLE_NAME = "基金"
OUTPUT_HTML = "fund_interactive_chart.html"

def generate_html_from_db(db_path=DB_FILE, table_name=TABLE_NAME, output_path=OUTPUT_HTML):
    conn = sqlite3.connect(db_path)
    # 按日期由舊到新排序讀取
    query = f'SELECT * FROM "{table_name}" WHERE 基金名稱 = "統一奔騰" ORDER BY 西元日期 ASC;'
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("未在資料庫中找到資料！")
        return
        
    print(f"成功自資料庫讀取 {len(df)} 筆真實指標資料！")
    
    # 轉換成 JSON 物件以注入 HTML
    # 處理 None / NaN
    df_clean = df.where(pd.notnull(df), None)
    records = df_clean.to_dict(orient="records")
    json_data = json.dumps(records, ensure_ascii=False)
    
    latest_date_tw = df["日期"].iloc[-1]
    latest_date_iso = df["西元日期"].iloc[-1]
    total_records = len(df)
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統一奔騰基金 - 雙圖連動看盤系統 (資料庫真實數據)</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Plotly.js CDN -->
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <!-- Phosphor Icons -->
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');
        body {{
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            background-color: #f1f5f9;
            color: #0f172a;
        }}
        ::-webkit-scrollbar {{
            width: 6px;
            height: 6px;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #cbd5e1;
            border-radius: 3px;
        }}
        .js-plotly-plot .plotly .modebar {{
            top: 4px !important;
            right: 8px !important;
        }}
    </style>
</head>
<body class="min-h-screen flex flex-col p-2.5 sm:p-4 md:p-6 bg-[#f1f5f9]">

    <!-- 主容器 -->
    <div class="max-w-[1600px] w-full mx-auto bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
        
        <!-- 1. 頂部導覽列 (Header Bar) -->
        <header class="px-4 sm:px-6 py-3.5 bg-white border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 select-none">
            <!-- 左側標題 -->
            <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-sm">
                    <i class="ph-bold ph-chart-line-up text-xl"></i>
                </div>
                <div>
                    <h1 class="text-base sm:text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
                        統一奔騰基金 - 雙圖連動看盤系統
                        <span class="text-[11px] font-semibold bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            SQLite 資料庫即時連動中 ({total_records} 筆)
                        </span>
                    </h1>
                    <div class="text-[11px] text-slate-500 mt-0.5">
                        資料庫：<code class="text-slate-700 bg-slate-100 px-1 py-0.5 rounded font-mono">股市資料庫.db</code> ➔ 資料表：<code class="text-slate-700 bg-slate-100 px-1 py-0.5 rounded font-mono">基金</code>
                    </div>
                </div>
            </div>

            <!-- 右側控制項 (日期切換器) -->
            <div class="flex items-center flex-wrap gap-2 text-xs sm:text-sm">
                <button id="firstBtn" class="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 active:bg-slate-100 font-semibold text-slate-700 transition shadow-xs" title="回到最初日期">
                    <i class="ph-bold ph-caret-double-left"></i> 首日
                </button>

                <button id="prevBtn" class="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 active:bg-slate-100 font-semibold text-slate-700 transition shadow-xs">
                    <i class="ph-bold ph-caret-left"></i> 前一日
                </button>

                <div class="flex items-center gap-1.5">
                    <label for="dateSelect" class="text-slate-600 font-medium whitespace-nowrap hidden sm:inline">鎖定日期：</label>
                    <select id="dateSelect" class="bg-sky-50/60 border border-sky-300 text-sky-950 font-bold rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-sky-500 cursor-pointer shadow-inner">
                        <!-- 動態填充所有真實交易日 -->
                    </select>
                </div>

                <button id="nextBtn" class="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 active:bg-slate-100 font-semibold text-slate-700 transition shadow-xs">
                    後一日 <i class="ph-bold ph-caret-right"></i>
                </button>

                <button id="latestBtn" class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 active:bg-sky-800 text-white font-bold transition shadow-sm">
                    <i class="ph-bold ph-arrow-fat-line-right"></i> 跳至最新 ({latest_date_tw})
                </button>
            </div>
        </header>

        <!-- 圖例列 (Legend Bar) -->
        <div class="px-4 py-2.5 bg-slate-50/80 border-b border-slate-100 flex flex-wrap items-center justify-center gap-x-5 gap-y-1.5 text-[11px] font-medium text-slate-600 select-none">
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2.5px] bg-[#334155] rounded-full"></span> 9D (慢線)</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2.5px] bg-[#ec4899] rounded-full"></span> 9K (快線)</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-[#0284c7] inline-block shadow-xs"></span> 基金淨值</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2px] bg-[#ef4444]"></span> 60MA (季線)</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2px] bg-[#8b5cf6]"></span> 20MA (中軌)</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2px] bg-[#06b6d4]"></span> 10MA</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2px] bg-[#f59e0b]"></span> 5MA</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2px] border-b-2 border-dotted border-[#38bdf8]"></span> 布林上軌(天花板)</span>
            <span class="flex items-center gap-1.5"><span class="w-3.5 h-[2px] border-b-2 border-dotted border-[#c084fc]"></span> 布林下軌(地板)</span>
        </div>

        <!-- 2. 雙圖連動繪圖區 -->
        <div class="p-2 sm:p-4 bg-white relative">
            <div id="chartContainer" class="w-full h-[540px] sm:h-[600px] md:h-[650px]"></div>
        </div>

        <!-- 3. 下方重要參數詳情卡片 -->
        <div class="px-4 sm:px-6 py-4 bg-slate-50 border-t border-slate-200">
            <!-- 詳情標題列 -->
            <div class="flex flex-wrap items-center justify-between gap-2 mb-3.5">
                <div class="flex items-center gap-2">
                    <span class="text-sm sm:text-base font-bold text-slate-800 flex items-center gap-1.5">
                        <i class="ph-fill ph-push-pin text-rose-500 text-lg"></i>
                        <span id="detailTitleDate">--/--/-- (----)</span> 重要參數詳情
                    </span>
                </div>
                <div class="text-[11px] sm:text-xs text-slate-500 flex items-center gap-1">
                    <i class="ph-bold ph-cursor-click text-sky-500"></i>
                    提示：點擊上方圖表任何一點或使用快捷按鈕，雙圖將同步更新紅色基準線與下方數據卡片
                </div>
            </div>

            <!-- 4 大參數卡片網格 -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                
                <!-- 卡片 1: 當日基金淨值 -->
                <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between transition hover:shadow-md hover:border-slate-300">
                    <div>
                        <div class="text-[11px] font-semibold text-slate-500 mb-1 flex items-center justify-between">
                            <span>當日基金淨值</span>
                            <span class="text-[10px] text-slate-400">新台幣</span>
                        </div>
                        <div class="flex items-baseline gap-1.5">
                            <span id="cardNav" class="text-3xl font-black text-slate-900 tracking-tight">--</span>
                            <span class="text-xs font-semibold text-slate-500">元</span>
                        </div>
                        <div id="cardChange" class="text-xs font-bold mt-1.5 flex items-center gap-1 text-slate-600">
                            --
                        </div>
                    </div>
                    <div class="mt-3 pt-2.5 border-t border-slate-100 text-[11px] text-slate-500 flex justify-between items-center">
                        <span>全區間最低: <strong id="valAllMin" class="text-slate-700">--</strong></span>
                        <span id="cardMinGap" class="font-bold text-sky-600">--</span>
                    </div>
                </div>

                <!-- 卡片 2: 布林通道位置 -->
                <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between transition hover:shadow-md hover:border-slate-300">
                    <div>
                        <div class="text-[11px] font-semibold text-slate-500 mb-1 flex items-center justify-between">
                            <span>布林通道 (BBand) 狀態</span>
                            <span class="text-[10px] text-slate-400">20日 / ±2SD</span>
                        </div>
                        <div id="cardBbandBadge" class="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 mb-2">
                            --
                        </div>
                        <div class="text-[11px] text-slate-600 space-y-1 font-medium bg-slate-50 p-2 rounded-lg border border-slate-100">
                            <div class="flex justify-between"><span>天花板(上軌):</span> <strong id="valBBUpper" class="text-sky-700">--</strong></div>
                            <div class="flex justify-between"><span>中軌(20MA):</span> <strong id="valBBMid" class="text-purple-700">--</strong></div>
                            <div class="flex justify-between"><span>地板(下軌):</span> <strong id="valBBLower" class="text-rose-700">--</strong></div>
                        </div>
                    </div>
                    <div class="mt-2.5 pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex justify-between items-center">
                        <span>通道帶寬 (BandWidth):</span>
                        <strong id="valBBWidth" class="text-slate-700 font-bold">--%</strong>
                    </div>
                </div>

                <!-- 卡片 3: 9日KD指標 -->
                <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between transition hover:shadow-md hover:border-slate-300">
                    <div>
                        <div class="text-[11px] font-semibold text-slate-500 mb-1 flex items-center justify-between">
                            <span>9日KD 指標 (體溫計)</span>
                            <span class="text-[10px] text-slate-400">RSV: <span id="valRSV" class="font-bold text-slate-600">--</span></span>
                        </div>
                        <div class="flex items-baseline gap-2 mb-2">
                            <span class="text-xl font-black text-slate-900 tracking-tight">
                                K: <span id="valK" class="text-pink-600">--</span> | D: <span id="valD" class="text-slate-700">--</span>
                            </span>
                        </div>
                        <div id="cardKdBadge" class="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                            --
                        </div>
                    </div>
                    <div class="mt-2.5 pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex justify-between items-center">
                        <span id="kdStatusText">超賣 &lt;20 / 超買 &gt;80</span>
                        <span id="kdDiff" class="font-bold text-emerald-600">--</span>
                    </div>
                </div>

                <!-- 卡片 4: 均線排列與轉折訊號 -->
                <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between transition hover:shadow-md hover:border-slate-300">
                    <div>
                        <div class="text-[11px] font-semibold text-slate-500 mb-1 flex items-center justify-between">
                            <span>均線排列與轉折訊號</span>
                            <span class="text-[10px] text-slate-400">5MA / 10MA / 20MA</span>
                        </div>
                        <div id="cardMaBadge" class="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 mb-1.5">
                            --
                        </div>
                        <div id="cardSignalText" class="text-[11px] text-slate-700 leading-snug font-medium min-h-[34px] flex items-center">
                            --
                        </div>
                    </div>
                    <div class="mt-2.5 pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex justify-between items-center">
                        <span>月線乖離 (BIAS20):</span>
                        <strong id="valBias20" class="text-slate-800 font-bold">--%</strong>
                    </div>
                </div>

            </div>
        </div>

        <!-- 底部版權與註解 -->
        <footer class="px-4 sm:px-6 py-3 bg-slate-100/80 border-t border-slate-200 flex flex-wrap items-center justify-between text-[11px] text-slate-500">
            <span class="flex items-center gap-1.5">
                <i class="ph-bold ph-database text-sky-600"></i>
                資料庫來源：股市資料庫.db ➔ 基金 Table (包含完整 440 筆歷史淨值與奔騰02指標)
            </span>
            <span>更新狀態：{latest_date_tw} ({latest_date_iso}) 盤後最新指標結算</span>
        </footer>

    </div>

    <!-- 內建來自 SQLite 資料庫真實數據 -->
    <script>
        const rawDatabaseRecords = {json_data};

        // 提取各指標時間序列
        const dates = rawDatabaseRecords.map(r => r["西元日期"]);
        const dates_tw = rawDatabaseRecords.map(r => r["日期"]);
        const nets = rawDatabaseRecords.map(r => r["基金淨值"]);
        const ma5 = rawDatabaseRecords.map(r => r["5MA"]);
        const ma10 = rawDatabaseRecords.map(r => r["10MA"]);
        const ma20 = rawDatabaseRecords.map(r => r["20MA"]);
        const ma60 = rawDatabaseRecords.map(r => r["60MA"]);
        const bbUpper = rawDatabaseRecords.map(r => r["布林上軌(天花板)"]);
        const bbLower = rawDatabaseRecords.map(r => r["布林下軌(地板)"]);
        const bbMid = rawDatabaseRecords.map(r => r["20日平均(中軌)"]);
        const bbStd = rawDatabaseRecords.map(r => r["標準差(波動度)"]);
        const kList = rawDatabaseRecords.map(r => r["K值(快線)"]);
        const dList = rawDatabaseRecords.map(r => r["D值(慢線)"]);
        const rsvList = rawDatabaseRecords.map(r => r["RSV(今日成績排名)"]);
        const alignments = rawDatabaseRecords.map(r => r["均線排列"]);
        const signals = rawDatabaseRecords.map(r => r["交叉訊號"]);

        // 全區間最低點
        const minNetVal = Math.min(...nets);

        // UI 狀態管理 (預設指向最新一筆)
        let selectedIndex = rawDatabaseRecords.length - 1;

        // 初始化日期下拉選單
        const dateSelect = document.getElementById('dateSelect');
        rawDatabaseRecords.forEach((item, idx) => {{
            const opt = document.createElement('option');
            opt.value = idx;
            opt.textContent = `${{item["日期"]}} (${{item["西元日期"]}}) - ${{item["基金淨值"].toFixed(2)}}元`;
            dateSelect.appendChild(opt);
        }});

        // 繪製 Plotly.js 雙圖連動
        function renderSyncedCharts() {{
            const targetDate = dates[selectedIndex];
            const targetNet = nets[selectedIndex];

            // 1. 上圖：布林帶填充 (地板)
            const traceBBLower = {{
                x: dates,
                y: bbLower,
                name: '布林下軌(地板)',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#c084fc', width: 1.2, dash: 'dot' }},
                fill: 'tonexty',
                fillcolor: 'rgba(238, 242, 255, 0.40)',
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 2. 上圖：布林上軌 (天花板)
            const traceBBUpper = {{
                x: dates,
                y: bbUpper,
                name: '布林上軌(天花板)',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#38bdf8', width: 1.2, dash: 'dot' }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 3. 上圖：60MA (季線)
            const traceMA60 = {{
                x: dates,
                y: ma60,
                name: '60MA (季線)',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#ef4444', width: 1.5 }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 4. 上圖：20MA (中軌)
            const traceMA20 = {{
                x: dates,
                y: ma20,
                name: '20MA (中軌)',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#8b5cf6', width: 1.5 }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 5. 上圖：10MA
            const traceMA10 = {{
                x: dates,
                y: ma10,
                name: '10MA',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#06b6d4', width: 1.2 }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 6. 上圖：5MA
            const traceMA5 = {{
                x: dates,
                y: ma5,
                name: '5MA',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#f59e0b', width: 1.2 }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 7. 上圖：基金淨值
            const traceNet = {{
                x: dates,
                y: nets,
                name: '基金淨值',
                type: 'scatter',
                mode: 'lines+markers',
                marker: {{ size: 3, color: '#0284c7' }},
                line: {{ color: '#0284c7', width: 2.2 }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 交叉訊號標註點 (黃金交叉與死亡交叉)
            const goldCrossX = [];
            const goldCrossY = [];
            const deathCrossX = [];
            const deathCrossY = [];

            for (let i = 0; i < signals.length; i++) {{
                if (signals[i] && signals[i].includes("黃金交叉")) {{
                    goldCrossX.push(dates[i]);
                    goldCrossY.push(nets[i] * 0.985); // 標在淨值下方
                }} else if (signals[i] && signals[i].includes("死亡交叉")) {{
                    deathCrossX.push(dates[i]);
                    deathCrossY.push(nets[i] * 1.015); // 標在淨值上方
                }}
            }}

            const traceGoldCross = {{
                x: goldCrossX,
                y: goldCrossY,
                name: '黃金交叉買訊',
                type: 'scatter',
                mode: 'markers+text',
                text: '★',
                textposition: 'bottom center',
                textfont: {{ color: '#16a34a', size: 14 }},
                marker: {{ symbol: 'triangle-up', size: 9, color: '#16a34a' }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            const traceDeathCross = {{
                x: deathCrossX,
                y: deathCrossY,
                name: '死亡交叉賣訊',
                type: 'scatter',
                mode: 'markers+text',
                text: '▲',
                textposition: 'top center',
                textfont: {{ color: '#dc2626', size: 14 }},
                marker: {{ symbol: 'triangle-down', size: 9, color: '#dc2626' }},
                xaxis: 'x',
                yaxis: 'y1'
            }};

            // 8. 下圖：9K 快線 (桃粉色)
            const traceK = {{
                x: dates,
                y: kList,
                name: '9K (快線)',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#ec4899', width: 1.8 }},
                xaxis: 'x',
                yaxis: 'y2'
            }};

            // 9. 下圖：9D 慢線 (深岩灰色)
            const traceD = {{
                x: dates,
                y: dList,
                name: '9D (慢線)',
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#334155', width: 1.8 }},
                xaxis: 'x',
                yaxis: 'y2'
            }};

            const chartData = [
                traceBBUpper, traceBBLower,
                traceMA60, traceMA20, traceMA10, traceMA5,
                traceNet,
                traceGoldCross, traceDeathCross,
                traceK, traceD
            ];

            // 雙圖連動 Layout
            const layout = {{
                grid: {{ rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom' }},
                autosize: true,
                margin: {{ l: 50, r: 40, t: 15, b: 25 }},
                showlegend: false,
                hovermode: 'x unified',
                dragmode: 'pan',
                // 上圖 (淨值 + 均線 + 布林)
                yaxis: {{
                    domain: [0.38, 1.0],
                    title: {{ text: '基金淨值 (新台幣)', font: {{ size: 11, color: '#64748b' }} }},
                    gridcolor: '#f1f5f9',
                    zeroline: false,
                    tickfont: {{ size: 10, color: '#64748b' }}
                }},
                // 下圖 (9日KD 體溫計)
                yaxis2: {{
                    domain: [0.0, 0.30],
                    title: {{ text: '9日KD 體溫', font: {{ size: 11, color: '#64748b' }} }},
                    range: [-5, 105],
                    tickvals: [0, 20, 50, 80, 100],
                    gridcolor: '#f1f5f9',
                    zeroline: false,
                    tickfont: {{ size: 10, color: '#64748b' }}
                }},
                // 共享時間 X 軸
                xaxis: {{
                    anchor: 'y2',
                    matches: 'x2',
                    type: 'date',
                    gridcolor: '#f8fafc',
                    tickformat: '%Y/%m',
                    tickfont: {{ size: 10, color: '#64748b' }}
                }},
                xaxis2: {{
                    anchor: 'y2',
                    type: 'date',
                    visible: false
                }},
                // 標記線 (紅色垂直十字線 + 80超買/20超賣線)
                shapes: [
                    // 貫穿兩圖的當前選取日期紅色垂直標線
                    {{
                        type: 'line',
                        xref: 'x',
                        yref: 'paper',
                        x0: targetDate,
                        x1: targetDate,
                        y0: 0,
                        y1: 1,
                        line: {{
                            color: '#ef4444',
                            width: 1.8,
                            dash: 'solid'
                        }}
                    }},
                    // 下圖 80 超買警戒線
                    {{
                        type: 'line',
                        xref: 'x',
                        yref: 'y2',
                        x0: dates[0],
                        x1: dates[dates.length - 1],
                        y0: 80,
                        y1: 80,
                        line: {{ color: 'rgba(244, 63, 94, 0.7)', width: 1.2, dash: 'dot' }}
                    }},
                    // 下圖 50 中性平衡線
                    {{
                        type: 'line',
                        xref: 'x',
                        yref: 'y2',
                        x0: dates[0],
                        x1: dates[dates.length - 1],
                        y0: 50,
                        y1: 50,
                        line: {{ color: 'rgba(148, 163, 184, 0.5)', width: 1.0, dash: 'dash' }}
                    }},
                    // 下圖 20 超賣冰凍線
                    {{
                        type: 'line',
                        xref: 'x',
                        yref: 'y2',
                        x0: dates[0],
                        x1: dates[dates.length - 1],
                        y0: 20,
                        y1: 20,
                        line: {{ color: 'rgba(16, 185, 129, 0.75)', width: 1.2, dash: 'dot' }}
                    }}
                ],
                // 數值浮水印標籤
                annotations: [
                    {{
                        xref: 'x',
                        yref: 'y2',
                        x: targetDate,
                        y: 15,
                        text: `D: ${{dList[selectedIndex] ? dList[selectedIndex].toFixed(2) : '--'}}<br>K: ${{kList[selectedIndex] ? kList[selectedIndex].toFixed(2) : '--'}}`,
                        showarrow: false,
                        align: 'right',
                        xanchor: 'left',
                        bgcolor: 'rgba(255, 255, 255, 0.92)',
                        bordercolor: '#cbd5e1',
                        borderwidth: 1,
                        borderpad: 3,
                        font: {{ size: 9, color: '#1e293b' }}
                    }}
                ]
            }};

            const config = {{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            }};

            Plotly.newPlot('chartContainer', chartData, layout, config);

            // 綁定圖表點擊事件 (點擊直接連動選取該日)
            const chartDiv = document.getElementById('chartContainer');
            chartDiv.on('plotly_click', function(evtData) {{
                if (evtData && evtData.points && evtData.points.length > 0) {{
                    const clickedX = evtData.points[0].x;
                    const newIndex = dates.indexOf(clickedX);
                    if (newIndex !== -1) {{
                        updateSelectedDay(newIndex);
                    }}
                }}
            }});
        }}

        // 5. 更新卡片詳情數據
        function updateCards() {{
            const curRecord = rawDatabaseRecords[selectedIndex];
            const curDate = curRecord["西元日期"];
            const curDateTw = curRecord["日期"];
            const curNet = curRecord["基金淨值"];
            const diff = curRecord["基金漲跌"];
            const diffPct = +(curRecord["基金漲跌幅"] * 100).toFixed(2);

            // 標題日期更新
            document.getElementById('detailTitleDate').textContent = `${{curDateTw}} (${{curDate}})`;
            dateSelect.value = selectedIndex;

            // 卡片 1: 當日基金淨值
            document.getElementById('cardNav').textContent = curNet.toFixed(2);
            const changeEl = document.getElementById('cardChange');
            const sign = diff > 0 ? '+' : '';
            changeEl.textContent = `${{sign}}${{diff}} (${{sign}}${{diffPct}}%)`;
            if (diff > 0) {{
                changeEl.className = 'text-xs font-bold mt-1.5 flex items-center gap-1 text-emerald-600';
            }} else if (diff < 0) {{
                changeEl.className = 'text-xs font-bold mt-1.5 flex items-center gap-1 text-rose-600';
            }} else {{
                changeEl.className = 'text-xs font-bold mt-1.5 flex items-center gap-1 text-slate-500';
            }}
            
            // 距離全區間最低點差距
            document.getElementById('valAllMin').textContent = `${{minNetVal.toFixed(2)}}`;
            const gap = +(curNet - minNetVal).toFixed(2);
            const gapPct = +((gap / minNetVal) * 100).toFixed(2);
            const gapEl = document.getElementById('cardMinGap');
            gapEl.textContent = `+${{gap}} (+${{gapPct}}%)`;

            // 卡片 2: 布林通道
            const upper = curRecord["布林上軌(天花板)"] || 0;
            const mid = curRecord["20日平均(中軌)"] || 0;
            const lower = curRecord["布林下軌(地板)"] || 0;
            document.getElementById('valBBUpper').textContent = upper ? upper.toFixed(2) : '--';
            document.getElementById('valBBMid').textContent = mid ? mid.toFixed(2) : '--';
            document.getElementById('valBBLower').textContent = lower ? lower.toFixed(2) : '--';
            
            const bWidth = mid > 0 ? (((upper - lower) / mid) * 100).toFixed(2) : '0.00';
            document.getElementById('valBBWidth').textContent = `${{bWidth}}%`;

            const bbandBadge = document.getElementById('cardBbandBadge');
            if (curNet < lower) {{
                bbandBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200 mb-2';
                bbandBadge.innerHTML = '<i class="ph-bold ph-warning"></i> 跌穿布林地板 (極限超跌/特價區)';
            }} else if (curNet <= lower + 15) {{
                bbandBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-amber-50 text-amber-700 border border-amber-200 mb-2';
                bbandBadge.innerHTML = '<i class="ph-bold ph-shield-check"></i> 踩穩布林地板 (底部防禦區)';
            }} else if (curNet > upper) {{
                bbandBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-purple-50 text-purple-700 border border-purple-200 mb-2';
                bbandBadge.innerHTML = '<i class="ph-bold ph-fire"></i> 突破布林天花板 (強勢創高)';
            }} else {{
                bbandBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 mb-2';
                bbandBadge.innerHTML = '<i class="ph-bold ph-arrows-left-right"></i> 布林通道常態箱型震盪';
            }}

            // 卡片 3: 9日KD指標
            const k = curRecord["K值(快線)"] || 50;
            const d = curRecord["D值(慢線)"] || 50;
            const rsv = curRecord["RSV(今日成績排名)"] || 50;
            document.getElementById('valK').textContent = k.toFixed(2);
            document.getElementById('valD').textContent = d.toFixed(2);
            document.getElementById('valRSV').textContent = rsv.toFixed(1);
            
            const kdDiffVal = +(k - d).toFixed(2);
            const kdDiffEl = document.getElementById('kdDiff');
            kdDiffEl.textContent = `K-D: ${{kdDiffVal >= 0 ? '+' : ''}}${{kdDiffVal}} (${{kdDiffVal >= 0 ? '快線領先' : '慢線壓制'}})`;
            kdDiffEl.className = kdDiffVal >= 0 ? 'font-bold text-emerald-600' : 'font-bold text-rose-600';

            const kdBadge = document.getElementById('cardKdBadge');
            if (k < 20 && d < 20) {{
                kdBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-cyan-50 text-cyan-700 border border-cyan-200';
                kdBadge.innerHTML = '<i class="ph-bold ph-snowflake"></i> KD 低檔極凍鈍化 (&lt;20)';
            }} else if (k >= d && k < 40) {{
                kdBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200';
                kdBadge.innerHTML = '<i class="ph-bold ph-sparkle"></i> KD 低檔向上黃金打勾';
            }} else if (k > 80 && d > 80) {{
                kdBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200';
                kdBadge.innerHTML = '<i class="ph-bold ph-flame"></i> KD 高檔過熱警戒 (&gt;80)';
            }} else {{
                kdBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200';
                kdBadge.innerHTML = '<i class="ph-bold ph-activity"></i> KD 常態區間運行';
            }}

            // 卡片 4: 均線排列與交叉轉折
            const bias20 = mid > 0 ? (((curNet - mid) / mid) * 100).toFixed(2) : '0.00';
            const biasEl = document.getElementById('valBias20');
            biasEl.textContent = `${{bias20}}%`;
            biasEl.className = bias20 >= 0 ? 'text-slate-800 font-bold text-emerald-600' : 'text-slate-800 font-bold text-rose-600';

            const maBadge = document.getElementById('cardMaBadge');
            const sigText = document.getElementById('cardSignalText');
            const alignStr = curRecord["均線排列"] || "";
            const sigStr = curRecord["交叉訊號"] || "";

            if (alignStr.includes("進攻隊形")) {{
                maBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 mb-1.5';
                maBadge.innerHTML = '<i class="ph-bold ph-arrow-fat-line-up"></i> ' + alignStr;
            }} else if (alignStr.includes("撤退隊形")) {{
                maBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200 mb-1.5';
                maBadge.innerHTML = '<i class="ph-bold ph-arrow-fat-line-down"></i> ' + alignStr;
            }} else {{
                maBadge.className = 'inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 mb-1.5';
                maBadge.innerHTML = '<i class="ph-bold ph-arrows-left-right"></i> ' + alignStr;
            }}

            let signalMsg = '';
            if (sigStr) {{
                signalMsg = `<span class="font-bold text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200 mr-1">${{sigStr}}</span> `;
            }}
            
            const ma60Val = curRecord["60MA"] || 0;
            const seasonMsg = curNet >= ma60Val ? '<span class="text-emerald-700">季線(60MA)之上偏多</span>' : '<span class="text-rose-600">跌破季線(60MA)轉保守</span>';
            sigText.innerHTML = signalMsg + seasonMsg;
        }}

        // 6. 控制按鈕事件
        function updateSelectedDay(newIdx) {{
            if (newIdx < 0 || newIdx >= rawDatabaseRecords.length) return;
            selectedIndex = newIdx;
            updateCards();
            renderSyncedCharts();
        }}

        document.getElementById('firstBtn').addEventListener('click', () => {{
            updateSelectedDay(0);
        }});

        document.getElementById('prevBtn').addEventListener('click', () => {{
            updateSelectedDay(selectedIndex - 1);
        }});

        document.getElementById('nextBtn').addEventListener('click', () => {{
            updateSelectedDay(selectedIndex + 1);
        }});

        document.getElementById('latestBtn').addEventListener('click', () => {{
            updateSelectedDay(rawDatabaseRecords.length - 1);
        }});

        dateSelect.addEventListener('change', (e) => {{
            updateSelectedDay(parseInt(e.target.value, 10));
        }});

        window.addEventListener('resize', () => {{
            Plotly.Plots.resize('chartContainer');
        }});

        window.addEventListener('DOMContentLoaded', () => {{
            updateCards();
            renderSyncedCharts();
        }});
    </script>
</body>
</html>
'''
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # 同步寫一份到 code_artifact.html，方便使用者直接覆蓋檢視
    with open("code_artifact.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"成功產出互動統計圖網頁：{output_path} 與 code_artifact.html！")

if __name__ == "__main__":
    generate_html_from_db()

