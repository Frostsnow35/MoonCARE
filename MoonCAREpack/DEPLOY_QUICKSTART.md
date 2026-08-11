# MoonCARE 一键部署快速指引（IP + HTTP 先用起来）

> 面向"现在没有服务器，先改好代码，拿到服务器后一键部署"的场景。
> 本文按**手机直接用 IP+端口访问**（无域名、无 HTTPS）的最简方式编写。
> 想用域名 + HTTPS（PWA 可安装、体验最好）时，见文末"升级到 HTTPS"。

## 0. 需要准备的东西

| 项目 | 说明 |
| --- | --- |
| 一台 Linux 服务器 | 腾讯云/阿里云/轻量云均可，2C4G 起步（本项目需 Docker 构建，内存建议 ≥4G） |
| 服务器公网 IP | 记下它，手机和 APK 都要用 |
| Docker 与 Docker Compose | 服务器安装，见下方"服务器准备" |
| NVIDIA API Key | 填进 `.env` 后 AI 聊天可用（不填则聊天返回"LLM 未配置"提示，服务不崩） |
| SMTP 邮箱授权码 | 用于注册/找回密码的邮箱验证码（不填则注册/找回暂不可用，登录可用） |

## 1. 服务器准备（一次性）

以 Ubuntu/Debian 为例，`ssh` 登录后执行：

```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装 Docker + Compose 插件（官方脚本）
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
docker compose version        # 应显示 v2.x
```

如果是国内服务器拉镜像慢，配置镜像加速（可选，各云厂商有各自的加速地址）。

开放端口（以 UFW 为例，或直接在云控制台安全组放行 TCP）：

```bash
sudo ufw allow 18000/tcp     # MoonCARE 应用端口
sudo ufw allow 22/tcp        # SSH
sudo ufw enable
```

> 如果选择 Nginx 反代方案（更安全），则改为放行 80/443，不需要放行 18000。

## 2. 上传文件夹并改名

把整个 `MoonCAREpack` 文件夹上传到服务器 `/www/wwwroot`：

```bash
sudo mkdir -p /www/wwwroot
sudo chown -R $USER /www/wwwroot

# 上传方式任选其一：
#  - scp:  scp -r MoonCAREpack user@你的IP:/www/wwwroot/
#  - 宝塔面板/云控制台直接上传压缩包后解压
#  - 若已压缩：unzip MoonCAREpack.zip -d /www/wwwroot/

cd /www/wwwroot
mv MoonCAREpack MoonCARE      # 目录名改为 MoonCARE
cd /www/wwwroot/MoonCARE
```

## 3. 生成并填写 .env（唯一需要手动编辑的步骤）

```bash
cp .env.example .env
chmod 600 .env
vi .env
```

必须确认/修改的项：

```env
DEBUG=false                        # 公网必须 false
APP_BIND_ADDR=0.0.0.0              # IP+端口直连模式，手机才能访问
APP_PORT=18000                     # 手机访问端口

# 下面两项 deploy.sh 会在留空时自动生成，但建议自己设强值并长期保持不变
DB_PASSWORD=这里填强密码
SECRET_KEY=这里填64位随机串

# AI 聊天
NVIDIA_API_KEY=填你的真实 Key        # 不填聊天会降级提示，服务不崩

# 邮箱验证码（注册/找回密码需要）
AUTH_EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USERNAME=你发件邮箱
SMTP_PASSWORD=你的邮箱授权码
SMTP_FROM_EMAIL=你发件邮箱
SMTP_USE_TLS=false
SMTP_USE_SSL=true
```

## 4. 一键部署

```bash
cd /www/wwwroot/MoonCARE
bash deploy.sh
```

脚本会自动：
- 校验包完整性
- 补齐 `DB_PASSWORD` / `SECRET_KEY`（如果留空）
- 清空 SMTP / NVIDIA 占位符（避免把字面量 `REPLACE_WITH_*` 当真实配置）
- `docker compose config` 校验
- 构建并启动 PostgreSQL + 应用
- 等待 `/health` 通过

看到 `MoonCARE health check passed.` 即部署成功。

## 5. 手机验证

1. 手机和服务器在同一网络（或公网 IP 已放行 18000 端口）。
2. 手机浏览器打开：`http://你的服务器IP:18000`
3. 注册账号 → 填邮箱收验证码（SMTP 已配好）→ 登录。
4. 进入"聊聊"发消息，验证 AI 对话（WebSocket + SSE）。
5. 进入"我的"→ 查看"服务器地址"是否显示当前连接。

> 公网 HTTP 下浏览器会提示"不安全"，属正常。功能（登录/聊天/日记/周期/音乐）全部可用；
> PWA"添加到主屏幕"在纯 HTTP 下不可用，这是浏览器安全限制，用 APK 即可获得原生体验。

## 6. 常用运维命令

```bash
cd /www/wwwroot/MoonCARE
docker compose ps                       # 查看容器状态
curl -fsS http://127.0.0.1:18000/health # 健康检查
bash diagnose.sh                        # 一键诊断
docker compose logs -f app              # 看应用日志
bash deploy.sh                          # 再次部署（不会清数据库）
FORCE_REBUILD=1 bash deploy.sh          # 强制重建镜像（改代码后）
```

## 7. 常见问题

| 现象 | 处理 |
| --- | --- |
| 手机打不开 `http://IP:18000` | 检查安全组/防火墙是否放行 18000；`APP_BIND_ADDR=0.0.0.0` |
| 登录提示"邮箱或密码错误" | 先在手机浏览器注册账号；或确认数据库 volume 未被误删 |
| 聊天提示"LLM 未配置" | 在 `.env` 填 `NVIDIA_API_KEY` 后 `bash deploy.sh` |
| 注册提示"验证码邮件无法发送" | 检查 SMTP 配置；临时可用 `AUTH_EMAIL_DELIVERY_MODE=log`（仅 DEBUG=true 开发用） |
| pip 下载超时 | `.env` 里已默认清华镜像；可换阿里云：`PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple` 后 `FORCE_REBUILD=1 bash deploy.sh` |
| `ModuleNotFoundError: No module named 'app'` | 旧镜像残留，`FORCE_REBUILD=1 bash deploy.sh` |

## 8. 升级到 HTTPS（推荐，正式使用前做）

有了域名后，用 Nginx + Let's Encrypt（certbot）即可启用 HTTPS：

```bash
# 1. 改回 127.0.0.1，用 Nginx 反代
sed -i 's/^APP_BIND_ADDR=.*/APP_BIND_ADDR=127.0.0.1/' .env
bash deploy.sh

# 2. 安装并启用反代配置（已含 WebSocket / SSE）
sudo cp deploy/nginx/mooncare-ip.conf /etc/nginx/conf.d/mooncare.conf
sudo nginx -t && sudo systemctl reload nginx

# 3. 申请证书（域名需已解析到服务器）
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名
```

HTTPS 生效后：手机浏览器可正常"添加到主屏幕"（PWA），聊天 WebSocket 自动走 `wss://`，无需改前端代码。

## 9. 数据备份

```bash
mkdir -p /www/backup
docker exec mooncare-postgres pg_dump -U mooncare mooncare > /www/backup/mooncare_$(date +%Y%m%d%H%M%S).sql
# 保留最近 30 天
find /www/backup -name 'mooncare_*.sql' -mtime +30 -delete
```
