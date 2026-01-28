# 项目文件结构说明

本文档说明项目中哪些文件应该保留在 GitHub 上。

## 📁 项目结构

```
20260128/
├── .gitignore                    ✅ 保留 - Git 忽略规则
├── README.md                     ✅ 保留 - 项目主说明文档
├── GITHUB_DEPLOYMENT.md          ✅ 保留 - GitHub 部署指南
├── CLEANUP.md                    ✅ 保留 - 清理说明文档
├── PROJECT_STRUCTURE.md          ✅ 保留 - 本文件
├── spec.md                       ✅ 保留 - 需求规范文档
├── ARCHITECTURE_RECOMMENDATION.md ✅ 保留 - 架构建议文档
│
├── backend/                       ✅ 保留整个目录
│   ├── src/                      ✅ 保留 - 核心代码
│   │   ├── models/               ✅ 保留 - 数据模型
│   │   ├── core/                 ✅ 保留 - 计算引擎
│   │   ├── api/                  ✅ 保留 - FastAPI 路由
│   │   └── utils/                ✅ 保留 - 工具函数
│   ├── tests/                    ✅ 保留 - 测试代码
│   ├── examples/                 ✅ 保留 - 示例代码
│   ├── main.py                   ✅ 保留 - FastAPI 入口
│   ├── requirements.txt          ✅ 保留 - Python 依赖
│   ├── BACKEND_DOCS.md           ✅ 保留 - 后端文档
│   ├── venv/                     ❌ 忽略 - 虚拟环境（已在 .gitignore）
│   └── __pycache__/              ❌ 忽略 - Python 缓存（已在 .gitignore）
│
├── streamlit_app/                ✅ 保留整个目录
│   ├── app.py                    ✅ 保留 - Streamlit 主应用
│   ├── default_config.json       ✅ 保留 - 默认配置
│   ├── requirements.txt          ✅ 保留 - Python 依赖
│   ├── README.md                 ✅ 保留 - Streamlit 版本说明
│   ├── DEPLOYMENT.md             ✅ 保留 - 部署指南
│   ├── QUICK_START.md            ✅ 保留 - 快速开始指南
│   ├── run.sh                    ✅ 保留 - 启动脚本
│   ├── Dockerfile                ✅ 保留 - Docker 配置
│   ├── docker-compose.yml        ✅ 保留 - Docker Compose 配置
│   └── .streamlit/               ✅ 保留 - Streamlit 配置
│       └── config.toml          ✅ 保留 - Streamlit 配置文件
```

## ✅ 应该保留的文件类型

1. **源代码文件**
   - `*.py` - Python 源代码
   - `*.json` - 配置文件（requirements.txt 等）

2. **文档文件**
   - `*.md` - Markdown 文档
   - `*.txt` - 文本文件（requirements.txt 等）

3. **配置文件**
   - `.gitignore` - Git 忽略规则
   - `*.toml` - 配置文件
   - `*.sh` - Shell 脚本
   - `Dockerfile`, `docker-compose.yml` - Docker 配置

4. **示例和测试**
   - `examples/` - 示例代码
   - `tests/` - 测试代码

## ❌ 应该被忽略的文件（已在 .gitignore 中）

1. **虚拟环境和依赖**
   - `venv/`, `env/`, `.venv/` - Python 虚拟环境

2. **缓存和编译文件**
   - `__pycache__/` - Python 缓存
   - `*.pyc`, `*.pyo` - Python 编译文件
   - `dist/`, `build/` - 构建产物

3. **系统文件**
   - `.DS_Store` - macOS 系统文件
   - `Thumbs.db` - Windows 系统文件

4. **IDE 和编辑器**
   - `.vscode/`, `.idea/` - IDE 配置
   - `*.swp`, `*.swo` - 编辑器临时文件

5. **日志和环境变量**
   - `*.log` - 日志文件
   - `.env`, `.env.local` - 环境变量文件

## 🧹 已清理的内容

以下文件/目录已被清理（如果存在）：
- `backend/__pycache__/` - Python 缓存目录
- `backend/**/*.pyc` - Python 编译文件
- `.DS_Store` - macOS 系统文件

这些文件不会被提交到 GitHub（已在 .gitignore 中配置）。

## 📝 提交前检查

在提交到 GitHub 前，运行：

```bash
# 检查哪些文件会被提交
git status

# 检查哪些文件会被忽略
git status --ignored

# 确认没有敏感信息
grep -r "password\|secret\|api_key" . --exclude-dir=venv --exclude-dir=node_modules
```

## 🎯 推荐的文件组织

对于 GitHub 仓库，建议：

1. **保留所有源代码** - 让用户可以运行项目
2. **保留所有文档** - 帮助用户理解和使用
3. **保留配置文件** - 让项目可以正常启动
4. **忽略所有依赖** - 用户需要自己安装
5. **忽略所有缓存** - 这些文件会自动生成

当前配置已符合这些原则！
