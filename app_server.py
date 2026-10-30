# -*- coding: utf-8 -*-
"""
統一奔騰基金看盤工作站 - 本地整合伺服器
提供本地網頁瀏覽、即時圖表渲染、以及「一鍵抓取 TWSE 大盤資料更新寫入資料庫」之 API
完全採用 Python 標準庫，零額外依賴
"""

import http.server
import socketserver
import json
import os
import sys
import webbrowser
import urllib.parse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MitakeFundRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # 允許跨來源請求 (CORS)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # 根目錄自動對應 index.html
        if path == '/' or path == '':
            self.path = '/index.html'
            return super().do_GET()

        # 大盤更新 API 端點
        if path == '/api/update_taiex':
            self.handle_update_taiex()
            return

        return super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/api/update_taiex':
            self.handle_update_taiex()
            return
        self.send_error(404, "Endpoint not found")

    def handle_update_taiex(self):
        """執行近一星期 TWSE 大盤資料增量更新，寫入 SQLite 資料庫並返回結果"""
        try:
            import fetch_twse_taiex
            result = fetch_twse_taiex.update_recent_week_taiex()
            
            response_data = json.dumps(result, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            err_result = {
                "status": "error",
                "message": f"更新大盤資料時發生異常: {str(e)}"
            }
            err_data = json.dumps(err_result, ensure_ascii=False).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(err_data)))
            self.end_headers()
            self.wfile.write(err_data)

def run_server(port=PORT, auto_open=True):
    os.chdir(DIRECTORY)
    server_address = ('', port)
    
    # 允許地址立即重用
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, MitakeFundRequestHandler) as httpd:
        url = f"http://localhost:{port}/"
        print("=" * 60)
        print("🚀 統一奔騰看盤工作站本地伺服器已啟動！")
        print(f"📡 網頁服務位址: {url}")
        print("🔄 支援右上角【大盤更新】按鈕一鍵抓取 TWSE 並寫入股市資料庫.db")
        print("按 Ctrl+C 可隨時停止伺服器。")
        print("=" * 60)
        
        if auto_open:
            webbrowser.open(url)
            
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n伺服器已正常停止。")

if __name__ == '__main__':
    run_server(PORT, auto_open=False)
