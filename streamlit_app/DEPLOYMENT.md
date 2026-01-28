# 局域网部署指南

## ✅ 支持局域网部署

Streamlit 应用**完全支持**在公司局域网内部署，团队成员可以通过内网 IP 访问。

## 🚀 部署方案

### 方案一：单机部署（最简单）

**适用场景：** 小团队，临时使用

**步骤：**

1. **在一台可访问的服务器/电脑上运行：**
   ```bash
   cd streamlit_app
   streamlit run app.py --server.address=0.0.0.0 --server.port=8501
   ```

2. **获取服务器 IP 地址：**
   ```bash
   # Linux/Mac
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```

3. **团队成员访问：**
   - 在浏览器中输入：`http://服务器IP:8501`
   - 例如：`http://192.168.1.100:8501`

**优点：**
- ✅ 零配置，立即可用
- ✅ 不需要额外服务器
- ✅ 适合快速测试和演示

**缺点：**
- ⚠️ 服务器关机后无法访问
- ⚠️ 没有用户认证
- ⚠️ 性能受服务器硬件限制

---

### 方案二：Docker 部署（推荐）

**适用场景：** 需要稳定运行，便于管理

**步骤：**

1. **创建 Dockerfile：**
   ```dockerfile
   FROM python:3.10-slim
   
   WORKDIR /app
   
   # 复制依赖文件
   COPY streamlit_app/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # 复制应用代码
   COPY backend/ ./backend/
   COPY streamlit_app/app.py .
   
   # 暴露端口
   EXPOSE 8501
   
   # 启动命令
   CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
   ```

2. **构建镜像：**
   ```bash
   docker build -t pl-simulator .
   ```

3. **运行容器：**
   ```bash
   docker run -d \
     --name pl-simulator \
     -p 8501:8501 \
     --restart unless-stopped \
     pl-simulator
   ```

4. **访问：**
   - `http://服务器IP:8501`

**优点：**
- ✅ 环境隔离，不污染系统
- ✅ 易于迁移和备份
- ✅ 可以设置自动重启

---

### 方案三：内网服务器部署

**适用场景：** 公司有内网服务器，需要长期运行

**步骤：**

1. **在服务器上安装依赖：**
   ```bash
   cd /path/to/pl-simulator/streamlit_app
   pip install -r requirements.txt
   ```

2. **使用 systemd 创建服务（Linux）：**
   
   创建 `/etc/systemd/system/pl-simulator.service`：
   ```ini
   [Unit]
   Description=P&L Simulator Streamlit App
   After=network.target
   
   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/path/to/pl-simulator/streamlit_app
   ExecStart=/usr/bin/streamlit run app.py --server.address=0.0.0.0 --server.port=8501
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **启动服务：**
   ```bash
   sudo systemctl enable pl-simulator
   sudo systemctl start pl-simulator
   ```

4. **查看状态：**
   ```bash
   sudo systemctl status pl-simulator
   ```

**优点：**
- ✅ 开机自启动
- ✅ 自动重启
- ✅ 适合生产环境

---

## 🔒 安全配置（可选）

### 1. 添加密码保护

创建 `.streamlit/config.toml`：
```toml
[server]
address = "0.0.0.0"
port = 8501

[server.enableCORS]
false

[server.enableXsrfProtection]
true
```

然后使用环境变量设置密码：
```bash
export STREAMLIT_SERVER_HEADLESS=true
streamlit run app.py --server.address=0.0.0.0
```

### 2. 使用 Nginx 反向代理（推荐）

**配置 Nginx：**
```nginx
server {
    listen 80;
    server_name pl-simulator.internal.company.com;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

**优点：**
- ✅ 可以使用域名访问（如 `http://pl-simulator.internal.company.com`）
- ✅ 可以添加 SSL 证书
- ✅ 可以配置访问控制

---

## 📋 部署检查清单

- [ ] 确认服务器 IP 地址
- [ ] 确认端口 8501 未被占用
- [ ] 确认防火墙允许 8501 端口访问
- [ ] 测试从其他电脑访问
- [ ] 配置开机自启动（如需要）
- [ ] 设置日志记录（如需要）

---

## 🔍 常见问题

### Q1: 其他电脑无法访问？

**检查：**
1. 防火墙是否开放 8501 端口
2. 启动时是否使用了 `--server.address=0.0.0.0`
3. 服务器和客户端是否在同一网段

**Linux 防火墙配置：**
```bash
# Ubuntu/Debian
sudo ufw allow 8501

# CentOS/RHEL
sudo firewall-cmd --add-port=8501/tcp --permanent
sudo firewall-cmd --reload
```

### Q2: 如何限制访问 IP？

可以在 Nginx 中配置：
```nginx
location / {
    allow 192.168.1.0/24;  # 允许内网访问
    deny all;              # 拒绝其他访问
    proxy_pass http://127.0.0.1:8501;
}
```

### Q3: 性能如何？

- **单用户：** 完全流畅
- **10 用户并发：** 无压力
- **50+ 用户并发：** 建议使用多实例 + 负载均衡

---

## 📊 部署方案对比

| 方案 | 复杂度 | 稳定性 | 适用场景 |
|------|--------|--------|----------|
| 单机部署 | ⭐ 简单 | ⭐⭐ | 临时使用、演示 |
| Docker | ⭐⭐ 中等 | ⭐⭐⭐ | 开发、测试环境 |
| 服务器部署 | ⭐⭐⭐ 复杂 | ⭐⭐⭐⭐ | 生产环境 |

---

## 🎯 推荐方案

**对于公司局域网部署，推荐：**

1. **快速测试：** 单机部署（方案一）
2. **稳定运行：** Docker 部署（方案二）
3. **生产环境：** 服务器部署 + Nginx（方案三）

所有方案都支持局域网访问，团队成员可以通过内网 IP 或域名访问应用。
