
# rule

```yaml
# 🧱 積木 A：負責推導 Registry 的規則
.rules_registry_mapping:
  rules:
    - if: '$DEPLOY_ENV == "production"'
      variables:
        TARGET_REGISTRY: "prod-harbor.yourcompany.com"
    - if: '$DEPLOY_ENV == "development"'
      variables:
        TARGET_REGISTRY: "dev-harbor.yourcompany.com"

# 🧱 積木 B：負責推導 K8s Cluster 地區的規則
.rules_cluster_mapping:
  rules:
    - if: '$DEPLOY_REGION == "us-east"'
      variables:
        TARGET_CLUSTER: "k8s-us-east-1"
    - if: '$DEPLOY_REGION == "ap-east"'
      variables:
        TARGET_CLUSTER: "k8s-ap-east-1"

# 🧱 積木 C：特定專案的特例規則 (例如夜間自動排程要加長 Timeout)
.rules_schedule_timeout:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
      variables:
        CUSTOM_TIMEOUT: "60m"
```

```yaml
include:
  - local: '/shared/rule-blocks.yml' # 🌟 引入積木庫

# 🌟 魔法展開：把多個規則積木無縫串接成一個大 Workflow
workflow:
  rules:
    - !reference [.rules_registry_mapping, rules]
    - !reference [.rules_cluster_mapping, rules]
    - !reference [.rules_schedule_timeout, rules]
    - when: always # 🌟 永遠把這個保底規則放在最後面！

stages:
  - build_and_push

Task:Node_Build_Component:
  stage: build_and_push
  trigger:
    include:
      - project: 'root/ci-cd-platform'
        file: '/specifics/node/components/build-and-push.yml'
        inputs:
          # 在這裡你可以直接拿到所有積木推導出來的變數！
          target_registry: "$TARGET_REGISTRY"
          target_cluster: "$TARGET_CLUSTER" 
# ... 以下省略
```

# 靜態腳本

```yaml
# ----------------------------------------
# 腳本模組：動態產生 Nuxt3 執行檔
# ----------------------------------------
.script_generate_node_sh:
  script:
    - echo "=== 1. 產生 Node.js 編譯與掃描腳本 ==="
    - |
      cat << 'EOF' > run_test.sh
      #!/bin/bash
      set -e
      export NUXT_TELEMETRY_DISABLED=1
      
      echo "--- 安裝依賴 ---"
      npm install
      
      # 🌟 透過 Bash 變數控制是否執行 SonarQube
      if [ "$ENABLE_SONAR" == "true" ]; then
        echo "--- 執行 SonarQube 掃描 ---"
        sonar-scanner \
          -Dsonar.token="$SONAR_TOKEN" \
          -Dsonar.projectKey="$SONAR_PROJECT_KEY" \
          -Dsonar.sources="." \
          -Dsonar.exclusions="**/node_modules/**,**/.output/**,**/.nuxt/**" \
          -Dsonar.host.url="$SONAR_HOST_URL" \
          -Dsonar.javascript.lcov.reportPaths="coverage/lcov.info"
      else
        echo "--- ⏩ 略過 SonarQube 掃描 ---"
      fi
      
      echo "--- 執行 Nuxt 3 打包 ---"
      npm run build
      
      mkdir -p /workspace/PublishOutput
      cp -r .output/* /workspace/PublishOutput/
      EOF
      chmod +x run_test.sh

# ----------------------------------------
# 腳本模組：執行 Docker 封裝與多目標推送
# ----------------------------------------
.script_docker_build_push:
  script:
    - echo "=== 6. 執行 Docker Build 與 Push ==="
    # TARGET_REGISTRY 從最外層的 Root Pipeline 決定
    - FULL_IMAGE_NAME="$TARGET_REGISTRY/$CI_PROJECT_NAME:$IMAGE_TAG"
    
    - echo "準備打包並推送至：$FULL_IMAGE_NAME"
    - docker build -t $FULL_IMAGE_NAME .
    - docker push $FULL_IMAGE_NAME
    
    # 打掃乾淨
    - docker rmi $FULL_IMAGE_NAME
```

```yaml
spec:
  inputs:
    node_version: { type: string }
    ci_image: { type: string }
    sonar_host: { type: string }
---
include:
  - local: '/shared/node-scripts.yml' # 🌟 引入靜態腳本庫

Task:Do_Node_Build_And_Push:
  tags:
    - shell
  script:
    - echo "=== 0. 切換至專案原始碼目錄 ==="
    - cd "${PROJECT_SUBDIR}"
    
    # 🌟 引用模組：產生 run_test.sh (裡面自帶了 Sonar 判斷)
    - !reference [.script_generate_node_sh, script]

    - echo "=== 2. 建立容器並注入程式碼 ==="
    - |
      CONTAINER_ID=$(docker create -w /workspace \
        -v "npm-cache:/root/.npm" \
        -e SONAR_PROJECT_KEY="$CI_PROJECT_NAME" \
        -e SONAR_HOST_URL="$[[ inputs.sonar_host ]]" \
        -e SONAR_TOKEN="$SONAR_TOKEN" \
        -e ENABLE_SONAR="$ENABLE_SONAR" \ # 將外部開關透傳給容器內
        $[[ inputs.ci_image ]] \
        bash /workspace/run_test.sh)
        
    - docker cp . $CONTAINER_ID:/workspace
    - docker start -a $CONTAINER_ID
    
    - echo "=== 4. 抽回成品 ==="
    - mkdir -p ./PublishOutput
    - docker cp $CONTAINER_ID:/workspace/PublishOutput/. ./PublishOutput/
    - docker rm $CONTAINER_ID

    - echo "=== 5. 產生 Dockerfile ==="
    - |
      cat <<EOF > Dockerfile
      FROM node:$[[ inputs.node_version ]] AS base
      WORKDIR /nuxt3/server
      ENV TZ=Asia/Taipei
      COPY PublishOutput/ /nuxt3/
      EXPOSE 3000
      ENTRYPOINT ["node", "index.mjs"]
      EOF

    # 🌟 引用模組：直接執行 Docker Build & Push
    - !reference [.script_docker_build_push, script]
```


# 變數推導

```yaml
workflow:
  rules:
    - if: '$DEPLOY_ENV == "production"'
      variables:
        TARGET_REGISTRY: "prod-harbor.yourcompany.com"
    - if: '$DEPLOY_ENV == "development"'
      variables:
        TARGET_REGISTRY: "dev-harbor.yourcompany.com"
    - when: always # 確保其他變數與執行條件正常通過
```

