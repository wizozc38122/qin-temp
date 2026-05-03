# 1

```
docker compose up -d
```

# 2


```
# C:\Windows\System32\drivers\etc\hosts
127.0.0.1   gitlab.local
```

# 3

```
docker-compose up -d

# root
docker exec -it local-gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

# 4

Admin Area -> Instance Runners -> New instance runner -> Copy token

```
docker exec -it local-runner gitlab-runner register
```

# 5 Test

建立一個專案 -> .gitlab-ci.yml

```yaml
stages:
  - setup
  - test

Task:Setup:
  stage: setup
  tags:
    - shell
  script:
    - echo "TEST_VAR=HelloWorld" >> build.env
  artifacts:
    reports:
      dotenv: build.env

Task:DockerCheck:
  stage: test
  tags:
    - shell
  needs: ["Task:Setup"]
  script:
    - echo "驗證拿到上游變數：$TEST_VAR"
    - echo "測試在 Shell 模式下呼叫 Docker："
    # 🌟 建議作法：將複雜指令拆開，或使用單引號包裹 shell 指令
    - docker run --rm alpine sh -c "echo 我在容器內印出變數：$TEST_VAR"
```

```
docker exec -it -u root local-runner chmod 666 /var/run/docker.sock
```