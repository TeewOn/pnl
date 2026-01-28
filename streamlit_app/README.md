# P&L 模拟器 - Streamlit 版本

实时更新的 P&L（损益）预估工具。调整参数后立即看到结果，无需点击按钮。

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动应用

```bash
streamlit run app.py
```

应用会自动在浏览器中打开：http://localhost:8501

## 特性

- ✅ **实时更新** - 参数调整后自动重新运行，立即显示结果
- ✅ **开箱即用** - 一个命令启动
- ✅ **便于迭代** - 修改 Python 代码，刷新浏览器即可看到效果
- ✅ **纯 Python** - 不需要前端代码

## 使用说明

1. **左侧参数面板** - 调整各种参数
   - 基础设置：模拟天数、开始日期、额外投放支出
   - 预算策略：基准预算比例、地区分配
   - 全局默认参数：初始 DAU、CPI、ARPU、运营成本等
   - 留存率配置：7 个关键留存率节点

2. **主区域** - 查看结果
   - 关键指标卡片：最终 DAU、累计收入、累计成本、净利润
   - 趋势图：DAU 和 DNU 趋势
   - P&L 曲线：累计利润曲线（标注盈亏平衡点）
   - 地区对比：各地区贡献度饼图

## 部署

### Streamlit Cloud（推荐）

1. 将代码推送到 GitHub
2. 访问 https://streamlit.io/cloud
3. 连接仓库，自动部署

### 本地部署

```bash
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### Docker 部署

```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 与 React 版本的对比

| 特性 | Streamlit 版本 | React 版本 |
|------|--------------|-----------|
| 实时更新 | ✅ 自动 | ❌ 需点击按钮 |
| 代码量 | ~500 行 | ~2000+ 行 |
| 部署 | 简单（一个命令） | 复杂（需要 Node.js） |
| 迭代速度 | 快（修改即生效） | 慢（需要编译） |
| UI 定制性 | 中等 | 高 |

## 目录结构

```
streamlit_app/
├── app.py              # 主应用（单文件）
├── requirements.txt    # 依赖
├── README.md          # 说明文档
└── utils/             # 符号链接到 backend/src
    ├── core/          # 核心计算逻辑
    └── models/        # 数据模型
```
