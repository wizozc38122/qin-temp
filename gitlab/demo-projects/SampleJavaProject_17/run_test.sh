#!/bin/bash

echo "=== 1. 執行 Maven 單元測試並產出 JaCoCo 覆蓋率報告 ==="
mvn clean test

echo ""
echo "=== 2. 執行 SonarQube 掃描 ==="
# 注意：這裡的 $SONAR_TOKEN 與 $SONAR_PROJECT_KEY 等環境變數會從 docker run 傳入
mvn org.sonarsource.scanner.maven:sonar-maven-plugin:5.0.0.4389:sonar \
  -Dsonar.token="$SONAR_TOKEN" \
  -Dsonar.projectKey="$SONAR_PROJECT_KEY" \
  -Dsonar.java.binaries=target/classes \
  -Dsonar.coverage.jacoco.xmlReportPaths=target/site/jacoco/jacoco.xml \
  -Dsonar.host.url="$SONAR_HOST_URL"

echo ""
echo "=== 3. 執行 Maven 打包 (跳過測試) ==="
mvn -B -DskipTests clean package

echo ""
echo "=== 4. 複製產出物至 /publish_out ==="
# 複製編譯好的 jar 檔到外部掛載的 PublishOutput 資料夾
cp target/*.jar /publish_out/app.jar
echo "Java 專案打包完成！"
