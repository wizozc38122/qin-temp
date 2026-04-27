# Kong Admin API 簡易管理 UI 開發規格書

## 1. 系統架構目標
使用 Python 開發一個輕量級的管理介面，透過呼叫本地端的 Kong Admin API (預設 `http://localhost:28001`) 來管理 Service 與 Route。
* 使用 SQLite 作為本地快取/同步儲存，減少頻繁打 Kong API 的延遲，並可記錄變更歷史。

## 2. 核心領域模型 (Domain Model)

Kong 的資源關聯屬於強關聯：`Route` 必須屬於某一個 `Service`。

### SQLite 建議 Schema 關聯
* **Table: `services`**
  * `id` (String/UUID, PK)
  * `name` (String, 可為空)
  * `protocol` (String, 通常為 http/https)
  * `host` (String, 後端目標位址)
  * `port` (Integer)
  * `path` (String)
  * `created_at` (Integer/Timestamp)

* **Table: `routes`**
  * `id` (String/UUID, PK)
  * `name` (String, 可為空)
  * `protocols` (JSON Array, 預設 ["http", "https"])
  * `paths` (JSON Array, 觸發路由的路徑)
  * `service_id` (String/UUID, FK 對應 services.id)
  * `created_at` (Integer/Timestamp)

## 3. Kong Admin API 操作指南

Base URL: `http://localhost:28001`

### A. 全域分頁邏輯 (Pagination)
當請求清單 API 時，務必加上 `?size=1000`。
若回傳的 JSON 中含有 `offset` 欄位 (字串)，代表有下一頁。
* **下一頁請求方式**: `GET /services?size=1000&offset=<上一頁回傳的offset值>`
* **注意**: 開發 Python 同步腳本時，請使用 `while` 迴圈處理 offset，直到 `offset` 為 null 才存入 SQLite。

### B. Service 相關 API

#### 1. 取得所有 Service (Sync to SQLite)
* **GET** `/services`
* **Response**:
```json
{
  "data": [
    {
      "id": "1234-uuid",
      "name": "order-module",
      "host": "backend.k8s.svc",
      "port": 80,
      "protocol": "http"
    }
  ],
  "offset": "abcde-next-page-token"
}