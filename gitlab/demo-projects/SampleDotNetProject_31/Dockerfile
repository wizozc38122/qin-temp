# 專案改成 Web API 之後，這裡需換成包含網頁伺服器依賴的 aspnet 而不是純 runtime
FROM mcr.microsoft.com/dotnet/aspnet:3.1 AS base
WORKDIR /app

# 將上個步驟產出的 PublishOutput 複製進來這個生產環境的映像檔中
COPY PublishOutput/ .

# Web 專案預設跑在 80 ( .NET 3.1 預設行為)
EXPOSE 80

# 設定終端執行進入點
ENTRYPOINT ["dotnet", "SampleDotNetProject.dll"]