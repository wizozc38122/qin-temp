# 測試 ci-image 與專案建置流程

是的，你的觀念完全正確！✨ 
你可以透過 Docker 運行 `ci-image` 時，利用 `-v` 掛載參數，將程式碼掛載進去掃描與編譯，也可以再掛載一個目錄專門用來「**把打包好 (Publish) 的檔案拿出來**」。這也是最不污染宿主機、純淨而且好驗證的做法。

這裡為你整理了**接下來的具體操作流程**與**腳本指令**。

## 1. 本地透過 Docker 模擬 CI 流程 (編譯 + SonarQube 掃描)

我們準備在本地測試你的 `ci-image`（目前終端機看到你正在打包 `ci-image:v1`）。你可以直接使用以下終端機指令在本地模擬一次完整的編譯與掃描流程。

> **前置準備：** 在終端機進入 `Lab/gitlab/SampleDotNetProject` 目錄下開啟 PowerShell。我們不需要手動 `mkdir` 因為 Docker 掛載時如果是新目錄會自動幫你建立。

```bash
docker run --rm \
  -v "${PWD}:/workspace" \
  -v "${PWD}/PublishOutput:/publish_out" \
  -w "/workspace" \
  -e SONAR_PROJECT_KEY="SampleDotNetProject" \
  -e SONAR_HOST_URL="http://<你的SonarQube_IP或網址>:9000" \
  -e SONAR_TOKEN="<你的_SONAR_TOKEN>" \
  ci-image:v1 \
  bash -c '
    echo "=== 1. 啟動 SonarQube 前置作業 ==="
    dotnet sonarscanner begin /k:"$SONAR_PROJECT_KEY" /d:sonar.host.url="$SONAR_HOST_URL" /d:sonar.login="$SONAR_TOKEN"
    
    echo "=== 2. 執行 .NET 還原與發布 (Publish) ==="
    # 這裡會同時編譯並輸出成品的 DLL/EXE
    dotnet publish -c Release -o /publish_out
    
    echo "=== 3. 完成 SonarQube 掃描並上傳結果 ==="
    dotnet sonarscanner end /d:sonar.login="$SONAR_TOKEN"
  '
```

*(註：上面如果在 Windows PowerShell 中執行，`${PWD}` 代表的就是你的當下完整路徑，它能夠順利將路徑對應到 Docker Container 內)*

### 👉 這段指令跑完後，發生了什麼事？
1. **專案被掃描**：`ci-image` 內的 SonarScanner 處理了程式碼分析，並嘗試把結果發往 `SONAR_HOST_URL`。這時候你登入你的 SonarQube 控制台應該就能看見剛才埋的「假 Code Smell」發報。
2. **打包檔案被完美移出**：容器銷毀結束後 (`--rm`)，打開你本地電腦的 `SampleDotNetProject/PublishOutput` 資料夾，你會看到乾淨的 `.dll` 和 `.exe` 等編譯好的專案檔案 🎉。

---

## 2. 實際導入到 GitLab CI YAML 的寫法範例

當你在本地終端機測試成功之後，後續要寫成 `.gitlab-ci.yml` 的時候邏輯是完全一模一樣的（已經幫你剝除了 Mend 無關的部分）：

```yaml
dotnet_pipeline_job:
  stage: security_and_build
  tags:
    - shell-runner
  script:
    - echo "🚀 啟動純淨的 God Image 容器執行編譯與掃描..."
    - |
      docker run --rm \
        -v "${CI_PROJECT_DIR}:/workspace" \
        -v "${CI_PROJECT_DIR}/PublishOutput:/publish_out" \
        -w "/workspace" \
        -e SONAR_PROJECT_KEY="${CI_PROJECT_NAME}" \
        -e SONAR_HOST_URL="${SONAR_HOST_URL}" \
        -e SONAR_TOKEN="${SONAR_TOKEN}" \
        ci-image:v1 \
        bash -c '
          echo "=== 1. 啟動 SonarQube 前置作業 ==="
          dotnet sonarscanner begin /k:"$SONAR_PROJECT_KEY" /d:sonar.host.url="$SONAR_HOST_URL" /d:sonar.login="$SONAR_TOKEN"
          
          echo "=== 2. 執行 .NET 發布並倒出檔案 ==="
          # 將成品編譯到 /publish_out，也就是會回到宿主機的 CI_PROJECT_DIR/PublishOutput
          dotnet publish -c Release -o /publish_out
          
          echo "=== 3. 完成 SonarQube 掃描 ==="
          dotnet sonarscanner end /d:sonar.login="$SONAR_TOKEN"
        '
  artifacts:
    name: "${CI_PROJECT_NAME}-Build-Output"
    paths:
      - PublishOutput/
    expire_in: 1 week
```

### Artifacts (工件) 的小技巧：
在 GitLab CI 中，由於你在 Docker Container 內把打包好的成品掛載輸出給宿主機 (`CI_PROJECT_DIR/PublishOutput`)。
GitLab CI 透過最後面定義的 `artifacts`，會自動把 `PublishOutput/` 資料夾裡的內容打包成 Zip，這讓你：
1. 可以直接在 GitLab 網頁界面上下載打包這包 DLL。
2. 自動傳遞這些成品，讓 Pipeline 的「下一個階段」（例如 `Deploy`）無縫接軌拿去佈署。

---

# 未來切換 Docker Executor

```yaml
dotnet_build_and_scan_job:
  image: ci-image:v1 
  stage: security_and_build
  tags:
    - docker-runner # 指向你設定為 docker executor 的 Runner
  script:
    # --- 底下這裡，你已經「身處在」Container 裡面了！ ---
    # GitLab 會自動把你的專案原始碼掛載進來
    # 所以你只要直接敲指令即可：
    
    - echo "=== 1. 啟動 SonarQube 前置作業 ==="
    - dotnet sonarscanner begin /k:"$SONAR_PROJECT_KEY" /d:sonar.host.url="$SONAR_HOST_URL" /d:sonar.login="$SONAR_TOKEN"
    
    - echo "=== 2. 執行 .NET 還原與發布 (Publish) ==="
    - dotnet publish -c Release -o ./PublishOutput
    
    - echo "=== 3. 完成 SonarQube 掃描並上傳結果 ==="
    - dotnet sonarscanner end /d:sonar.login="$SONAR_TOKEN"

  artifacts:
    name: "DotNet-Build-Output-${CI_PIPELINE_ID}"
    paths:
      # 將打包結果傳遞給下一個佈署階段 (例如 Docker Build )
      - ./PublishOutput/

```

or

```dockerfile
# ==========================================
# 階段 1：使用 God Image (ci-image) 進行編譯與掃描
# ==========================================
FROM ci-image:v1 AS builder
WORKDIR /workspace/src

# 設定構建參數 (為了從 docker build 指令接收密碼與網址)
ARG SONAR_PROJECT_KEY
ARG SONAR_HOST_URL
ARG SONAR_TOKEN

# 將專案原始碼全部複製進容器內
COPY . .

# 一口氣完成前置作業、編譯、打包與 Sonar 掃描結果上傳
# (因為這在 build 時就會執行)
RUN dotnet sonarscanner begin /k:"${SONAR_PROJECT_KEY}" /d:sonar.host.url="${SONAR_HOST_URL}" /d:sonar.login="${SONAR_TOKEN}" \
    && dotnet publish -c Release -o /publish_out \
    && dotnet sonarscanner end /d:sonar.login="${SONAR_TOKEN}"

# ==========================================
# 階段 2：製作最終極小化 Runtime 映像檔
# ==========================================
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

# 🔑 重點在這裡：直接從上面的 builder 階段把打包好的成品偷過來！
# 不必透過宿主機，也不必透過 GitLab Artifacts 搬家了
COPY --from=builder /publish_out .

EXPOSE 8080
ENTRYPOINT ["dotnet", "SampleDotNetProject.dll"]
```