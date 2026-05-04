#!/bin/bash

echo "=== 1. 啟動 SonarQube 前置作業 ==="
dotnet sonarscanner begin /k:"$SONAR_PROJECT_KEY" /d:sonar.host.url="$SONAR_HOST_URL" /d:sonar.login="$SONAR_TOKEN"

echo ""
echo "=== 2. 執行 .NET 還原與發布 (Publish) ==="
dotnet publish -c Release -o /publish_out

echo ""
echo "=== 3. 完成 SonarQube 掃描並上傳結果 ==="
dotnet sonarscanner end /d:sonar.login="$SONAR_TOKEN"
