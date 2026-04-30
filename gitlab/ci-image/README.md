```powershell
docker build -t ci-image:latest .
```

## Required Binaries
在執行 `docker build` 之前，請確保 `binaries/` 目錄下包含以下離線安裝檔：

```yaml
binaries:
  - openjdk-17-jdk.tar.gz
  - apache-maven-3.9.9-bin.tar.gz
  - dotnet-sdk-5.0.tar.gz
  - dotnet-sdk-3.1.tar.gz
  - dotnet-sonarscanner.nupkg
  - node-v20.17.0-linux-x64.tar.xz
  - node-v22.14.0-linux-x64.tar.xz
  - sonar-scanner-cli.tar.gz
```