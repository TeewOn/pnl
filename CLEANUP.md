# 代码库清理说明

本文件说明了哪些文件应该保留在 GitHub 上，哪些应该被忽略。

## ✅ 应该保留的文件

### 核心代码
- `backend/src/` - 后端核心代码（计算引擎）
- `backend/main.py` - FastAPI 入口（可选，用于 API 调用）
- `backend/requirements.txt` - Python 依赖
- `backend/examples/` - 示例代码
- `backend/tests/` - 测试代码
- `streamlit_app/app.py` - Streamlit 主应用
- `streamlit_app/default_config.json` - 默认配置
- `streamlit_app/requirements.txt` - Streamlit 依赖

### 配置文件
- `.gitignore` - Git 忽略规则
- `streamlit_app/.streamlit/config.toml` - Streamlit 配置

### 文档
- `README.md` - 项目说明
- `spec.md` - 需求规范文档
- `GITHUB_DEPLOYMENT.md` - GitHub 部署指南
- `streamlit_app/README.md` - Streamlit 版本说明
- `streamlit_app/DEPLOYMENT.md` - 部署指南
- `streamlit_app/QUICK_START.md` - 快速开始指南
- `backend/BACKEND_DOCS.md` - 后端文档
- `ARCHITECTURE_RECOMMENDATION.md` - 架构建议文档

### 脚本和 Docker
- `streamlit_app/run.sh` - Streamlit 启动脚本
- `streamlit_app/Dockerfile` - Docker 配置
- `streamlit_app/docker-compose.yml` - Docker Compose 配置

## ❌ 应该被忽略的文件（已在 .gitignore 中）

### Python 相关
- `__pycache__/` - Python 缓存目录
- `*.pyc`, `*.pyo` - Python 编译文件
- `venv/`, `env/`, `.venv/` - 虚拟环境
- `*.egg-info/` - Python 包信息

### 构建产物
- `dist/`, `build/` - 构建产物
- `*.log` - 日志文件

### IDE 和系统文件
- `.vscode/`, `.idea/` - IDE 配置
- `.DS_Store` - macOS 系统文件
- `*.swp`, `*.swo` - 编辑器临时文件

### 其他
- `.env`, `.env.local` - 环境变量文件
- `*.log` - 日志文件
- `.pytest_cache/` - 测试缓存

## 🧹 清理命令

如果需要手动清理已存在的缓存文件：

```bash
# 清理 Python 缓存
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# 清理系统文件
find . -name ".DS_Store" -delete

# 注意：不要删除 venv/，它会被 .gitignore 自动忽略
```

## 📝 提交前检查清单

在提交到 GitHub 前，请确认：

- [ ] 已更新 `.gitignore` 文件
- [ ] 没有提交敏感信息（API 密钥、密码等）
- [ ] 没有提交虚拟环境（venv/）
- [ ] 没有提交构建产物（dist/, build/）
- [ ] 没有提交日志文件（*.log）
- [ ] 没有提交系统文件（.DS_Store）

## 🔍 验证 .gitignore

使用以下命令检查哪些文件会被 Git 忽略：

```bash
git status --ignored
```
