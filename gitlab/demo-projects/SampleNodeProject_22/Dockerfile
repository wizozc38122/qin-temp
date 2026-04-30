# 使用輕量級的 Alpine 版 Node.js 作為生產環境
FROM node:22-alpine AS base

WORKDIR /nuxt3/server
ENV TZ=Asia/Taipei
# 根據原專案需求，注入需要的環境變數
ARG NUXT3_ENV
ENV NUXT3_ENV=${NUXT3_ENV}

# 把從 ci-image 打包好並複製出來的 .output 目錄內容，放進映像檔的 /nuxt3
COPY PublishOutput/ /nuxt3/

# Nuxt 3 的預設 port
EXPOSE 3000

# Nuxt 3 server 啟動進入點
ENTRYPOINT ["node", "index.mjs"]
