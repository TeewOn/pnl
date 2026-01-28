# GitHub 部署指南

本指南将帮助你将这个 P&L 模拟器项目部署到 GitHub。

## 📋 前置要求

1. 已安装 Git
2. 拥有 GitHub 账号
3. 已在本地配置 Git（用户名和邮箱）

## 🚀 部署步骤

### 1. 初始化 Git 仓库（如果还没有）

```bash
cd /Users/bobbi/Library/Mobile\ Documents/com~apple~CloudDocs/codebase/Playground/20260128
git init
```

### 2. 创建 .gitignore 文件

项目根目录已包含 `.gitignore` 文件，会自动忽略：
- Python 缓存文件（`__pycache__/`, `*.pyc`）
- 虚拟环境（`venv/`, `env/`）
- IDE 配置文件（`.vscode/`, `.idea/`）
- 系统文件（`.DS_Store`）
- 日志文件（`*.log`）

### 3. 添加文件到 Git

```bash
# 添加所有文件
git add .

# 查看将要提交的文件
git status
```

### 4. 创建初始提交

```bash
git commit -m "Initial commit: P&L Simulator with Streamlit frontend"
```

### 5. 在 GitHub 上创建新仓库

1. 登录 GitHub
2. 点击右上角的 "+" 按钮，选择 "New repository"
3. 填写仓库信息：
   - **Repository name**: `pl-simulator`（或你喜欢的名字）
   - **Description**: "P&L 模拟器 - 基于 Streamlit 的损益预估工具"
   - **Visibility**: 选择 Public 或 Private
   - **不要**勾选 "Initialize this repository with a README"（因为我们已经有了）
4. 点击 "Create repository"

### 6. 连接本地仓库到 GitHub

GitHub 会显示仓库的 URL，使用 HTTPS 或 SSH。例如：

```bash
# HTTPS 方式（推荐，简单）
git remote add origin https://github.com/你的用户名/pl-simulator.git

# 或 SSH 方式（需要配置 SSH key）
git remote add origin git@github.com:你的用户名/pl-simulator.git
```

### 7. 推送代码到 GitHub

```bash
# 推送主分支
git branch -M main
git push -u origin main
```

如果这是第一次推送，GitHub 可能会要求你输入用户名和密码（或 Personal Access Token）。

### 8. 验证部署

访问你的 GitHub 仓库页面，应该能看到所有文件都已上传。

## 📝 后续更新代码

当你修改了代码后，使用以下命令更新 GitHub：

```bash
# 查看修改的文件
git status

# 添加修改的文件
git add .

# 提交修改
git commit -m "描述你的修改内容"

# 推送到 GitHub
git push
```

## 🔐 使用 Personal Access Token（推荐）

GitHub 已不再支持密码认证，需要使用 Personal Access Token：

1. 访问 GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token"
3. 设置权限：至少勾选 `repo` 权限
4. 生成后复制 token（只显示一次）
5. 推送时使用 token 作为密码

## 📦 项目结构说明

上传到 GitHub 的项目包含：

```
20260128/
├── backend/              # 后端代码
│   ├── src/             # 源代码
│   ├── examples/        # 示例配置
│   └── requirements.txt # Python 依赖
├── streamlit_app/       # Streamlit 前端应用
│   ├── app.py          # 主应用文件
│   ├── default_config.json  # 默认配置
│   └── requirements.txt # 前端依赖
├── spec.md             # 项目规范文档
├── README.md           # 项目说明
└── .gitignore          # Git 忽略文件
```

## ⚠️ 注意事项

1. **不要上传敏感信息**：
   - API 密钥
   - 密码
   - 个人数据
   - 这些已在 `.gitignore` 中排除

2. **虚拟环境**：
   - `venv/` 和 `env/` 目录不会被上传
   - 用户需要自己创建虚拟环境并安装依赖

3. **大文件**：
   - 如果项目中有大文件（>100MB），考虑使用 Git LFS

4. **私有仓库**：
   - 如果代码包含敏感信息，建议创建 Private 仓库

## 🔄 克隆项目

其他人可以通过以下命令克隆你的项目：

```bash
git clone https://github.com/你的用户名/pl-simulator.git
cd pl-simulator/20260128
```

## 📚 相关文档

- [Git 官方文档](https://git-scm.com/doc)
- [GitHub 帮助文档](https://docs.github.com/)
- [Streamlit 部署文档](https://docs.streamlit.io/deploy)

## 🆘 常见问题

### Q: 推送时提示 "remote: Support for password authentication was removed"

**A:** 需要使用 Personal Access Token，参考上面的说明。

### Q: 如何删除已上传的敏感文件？

**A:** 使用 `git rm --cached 文件名` 然后提交，但历史记录中仍会存在。如需完全删除，需要使用 `git filter-branch` 或 `git filter-repo`。

### Q: 如何添加 README.md？

**A:** 项目根目录已有 `README.md`，如果需要更新，直接编辑后提交即可。
