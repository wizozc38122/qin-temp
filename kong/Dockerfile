FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製 requirements 並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式原始碼
COPY . .

# 暴露 FastAPI 預設埠口
EXPOSE 8787

# 使用 Uvicorn 啟動
CMD ["uvicorn", "kong_ui:app", "--host", "0.0.0.0", "--port", "8787"]
