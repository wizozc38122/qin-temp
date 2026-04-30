FROM eclipse-temurin:17-jdk-alpine AS base
WORKDIR /app
ENV TZ=Asia/Taipei

# 將 God-CI-Image 產出的 /publish_out/app.jar 複製進來這個生產環境的映像檔中
COPY PublishOutput/app.jar /app/app.jar

# Web 專案預設可以自訂 port，例如 8080
EXPOSE 8080

# 設定終端執行進入點
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
