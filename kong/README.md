# 🦍 Qin Kong UI

這是一個專為 Kong Gateway 設計的超輕量級、跨節點 (Multi-Node) 獨立管理介面。
無須額外依賴大型資料庫，只需透過 SQLite 即可記錄所有操作日誌與節點資訊。提供一鍵複製、差異比對、拓樸檢視等核心維運功能。

## 🌟 核心功能

- **多節點管理**: 輕鬆註冊與切換不同的 Kong 節點（如 Dev、Staging、Prod）。
- **一鍵複製 (Clone)**: 將 Service 與關聯的 Routes 直接從節點 A 完整複製到節點 B。
- **差異比對 (Diff)**: 自動比對兩個節點之間缺少的 Services 或 Routes。
- **拓樸圖 (Topology)**: 直覺且可即時搜尋的 `Route ➡️ Service` 列表，釐清流量進入與出口點。
- **操作日誌 (Audit Log)**: 所有透過 UI 的新增、編輯、刪除操作皆紀錄 Payload 與 Response，提供安全稽核與備份。
- **編輯功能**: 支援直接修改原生的 JSON Payload (PATCH)，高度靈活。

---

## 🚀 如何運行與打包

### 方案 A：使用 Docker (推薦)

您可以將此 UI 打包為 Docker Image，在任何環境下皆可一鍵啟動。

**1. 建置 Docker Image**
```bash
cd kong
docker build -t qin-kong-ui:latest .
```

**2. 啟動 Container**
為了保留您註冊的節點與操作紀錄，建議將 SQLite 資料庫掛載 (Volume) 到本機。
```bash
docker run -d \
  --name qin-kong-ui \
  -p 8787:8787 \
  -v $(pwd)/kong_ops.db:/app/kong_ops.db \
  qin-kong-ui:latest
```
```powershell
# 在 PowerShell 中，掛載檔案必須提供絕對路徑
# 使用 ${PWD} 獲取目前目錄的絕對路徑
docker run -d `
  --name qin-kong-ui `
  -p 8787:8787 `
  -v "${PWD}/kong_ops.db:/app/kong_ops.db" `
  qin-kong-ui:latest
```


**3. 開啟網頁**
瀏覽器訪問：[http://localhost:8787](http://localhost:8787)

---

### 方案 B：使用 Python/UV (本地開發)

如果您有安裝 Python 3.10+ 或 `uv`，可以直接在本地端運行。

```bash
# 安裝依賴
pip install -r requirements.txt
# 或使用 uv 同步
uv pip install -r requirements.txt

# 啟動伺服器
python kong_ui.py
# 或使用 uv 直接運行 (腳本已包含 inline metadata)
uv run kong_ui.py
```

---

## 📖 Kong API 快速指引

Qin Kong UI 提供了原生的 JSON 編輯框。以下為常用格式參考：

### 建立 Service
```json
{
  "name": "my-payment-service",
  "url": "http://internal-payment-api.local:8080/v1"
}
```

### 建立 Route
```json
{
  "name": "my-payment-route",
  "paths": ["/api/v1/pay"],
  "methods": ["GET", "POST"],
  "strip_path": true
}
```
*更多資訊請參考介面右上角的 `📖 API 指南`。*
