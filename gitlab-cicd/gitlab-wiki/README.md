
# 條件

```
when: 決定行動。
never: 絕對不要執行。
always: 自動執行。
manual: 顯示在畫面上，等待人員點擊播放鍵 ▶️。
  allow_failure: true: 手動任務不按也不會當作 Pipeline 失敗
```

# 選擇條件 Sub Job

只會顯示一種不用擔心

```yaml
# 檔案：ci-cd-platform/.gitlab-ci.yml

stages:
  - setup            # 負責變數推導
  - trigger-routing  # 負責派發任務

# ==========================================
# 🌟 階段一：全域變數推導 (The Brain)
# ==========================================
Task:Derive_Variables:
  stage: setup
  script:
    - echo "開始進行動態變數推導..."
    # 邏輯 1：根據分支決定部署環境
    - |
      if [ "$CI_COMMIT_BRANCH" == "main" ]; then
        echo "DEPLOY_ENV=production" >> build.env
        echo "IMAGE_TAG=prod-$CI_COMMIT_SHORT_SHA" >> build.env
      else
        echo "DEPLOY_ENV=development" >> build.env
        echo "IMAGE_TAG=dev-$CI_COMMIT_SHORT_SHA" >> build.env
      fi
    # 邏輯 2：根據專案名稱動態產生 ArgoCD 的 App 名稱
    - echo "ARGO_APP_NAME=argo-sync-$PROJECT_NAME" >> build.env
  artifacts:
    reports:
      dotenv: build.env  # 將計算結果打包，準備往下游送

# ==========================================
# 🌟 階段二：任務派發 (The Router)
# ==========================================
Call_Dotnet:
  stage: trigger-routing
  needs: ["Task:Derive_Variables"] # 確保拿到上游推導的變數
  rules:
    - if: '$LANGUAGE_TYPE == "dotnet"'
  trigger:
    include: '/dotnet/pipeline.yml'
    strategy: depend
    forward:
      pipeline_variables: true # 🔑 核心關鍵：將推導出來的變數(DEPLOY_ENV等)往下傳給子管線

Call_Java:
  stage: trigger-routing
  needs: ["Task:Derive_Variables"]
  rules:
    - if: '$LANGUAGE_TYPE == "java"'
  trigger:
    include: '/java/pipeline.yml'
    strategy: depend
    forward:
      pipeline_variables: true
```