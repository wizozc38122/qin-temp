# Kong Light UI — 快速測試指南

## 前置需求

- Docker & Docker Compose
- Python 3.10+ & [uv](https://docs.astral.sh/uv/)

---

## Step 1: 啟動雙節點 Kong

```powershell
cd infra

# 啟動 Kong-A (Admin: 8001, Proxy: 8000)
docker compose -f docker-compose-kong-a.yaml -p kong-a up -d

# 啟動 Kong-B (Admin: 9001, Proxy: 9000)
docker compose -f docker-compose-kong-b.yaml -p kong-b up -d
```

> ⏳ 等待約 30 秒讓 DB 初始化與 migration 完成。

### 驗證節點

```powershell
curl http://localhost:8001/status   # Kong-A
curl http://localhost:9001/status   # Kong-B
```

---

## Step 2: 灌入範例資料

```powershell
cd infra

# Kong-A: 3 個範例 Service + Route
uv run seed_kong_a.py

# Kong-B: 1 個範例 Service + Route (模擬差異)
uv run seed_kong_b.py
```

### (可選) 大量資料測試 (1050 筆)

```powershell
# 驗證分頁查詢 (size=1000 邊界)，約需數分鐘
uv run seed_kong_a_bulk.py
```

---

## Step 3: 啟動 UI

```powershell
cd ..   # 回到 kong/ 根目錄
uv run kong_ui.py
```

開啟瀏覽器：**http://localhost:8787**

---

## Step 4: 首次設定 — 註冊節點

啟動後 UI 會自動跳轉到「🌐 節點管理」頁面（因為尚未註冊任何節點）。

| 欄位 | Kong-A | Kong-B |
|------|--------|--------|
| 名稱 | `Kong-A` | `Kong-B` |
| URL  | `http://localhost:8001` | `http://localhost:9001` |

分別填入並點「✅ 新增」。

---

## 功能測試清單

### ✅ 1. 節點管理 (`/nodes`)
- 新增 / 移除節點
- 即時偵測連線狀態與 Kong 版本

### ✅ 2. 儀表板 (`/`)
- 切換節點，查看所有 Services 與 Routes
- **Service 展開 Routes**: 點擊「📂 N 個」展開該 Service 下的所有 Routes
- 支援超過 1000 筆資料（自動分頁拉取）

### ✅ 3. 差異比對 (在儀表板操作)
- 在頂部選擇「🔀 比較差異」的目標節點，點擊「🔍 查看 / 比較」
- 顯示**僅有差異**的 Service / Route（誰多了什麼、誰少了什麼）
- 每個差異項目旁邊都有「📋 Clone →」按鈕，可一鍵複製到另一個節點

### ✅ 4. 跨節點複製
- 在 Service 列表選擇目標節點 + 📋 按鈕 = 一鍵複製
- 在差異比對區直接 Clone 缺少的項目
- ID/時間戳記自動清除

### ✅ 5. 刪除 + 備份
- 點 🗑️ → 出現黃底二次確認 → ✅ 確認刪除
- 自動備份完整設定 JSON 到操作紀錄（含關聯 Routes）
- 可在「📋 操作紀錄」找到 BACKUP 分類，展開即可復原

### ✅ 6. 匯出
- 點擊頂部的「📥 匯出全部 JSON」下載該節點所有 Services + Routes 的完整 JSON

### ✅ 7. 操作紀錄 (`/history`)
- 分類篩選：建立 / 刪除 / 備份
- 關鍵字搜尋

### ✅ 8. 健康檢查 (`/health`)
- 查看所有節點的 DB / Memory / Connections 狀態

---

## 清理環境

```powershell
cd infra
docker compose -f docker-compose-kong-a.yaml -p kong-a down -v
docker compose -f docker-compose-kong-b.yaml -p kong-b down -v
```

---

## 目錄結構

```
kong/
├── kong_ui.py                      # UI 主程式
├── kong_ops.db                     # SQLite (節點 + 操作紀錄, 自動生成)
├── templates/
│   ├── base.html
│   ├── index.html                  # 儀表板 + 差異比對
│   ├── nodes.html                  # 節點管理
│   ├── history.html                # 操作紀錄
│   ├── health.html                 # 健康檢查
│   └── compare.html                # (舊版比對, 保留)
└── infra/
    ├── docker-compose-kong-a.yaml  # Kong-A (Port 8001)
    ├── docker-compose-kong-b.yaml  # Kong-B (Port 9001)
    ├── seed_kong_a.py              # Kong-A 範例資料 (3 筆)
    ├── seed_kong_b.py              # Kong-B 範例資料 (1 筆)
    ├── seed_kong_a_bulk.py         # Kong-A 大量資料 (1050 筆)
    └── TESTING.md                  # 本文件
```
