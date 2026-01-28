# P&L 模拟器

基于天级数据的 P&L（损益）预估仿真工具。支持多地区、多维度参数配置的 DAU 和财务模拟。

## 功能特性

- 📊 **DAU 预测**: 基于留存率曲线的用户规模预测
- 💰 **财务模拟**: 收入、成本、利润的多维度计算
- 🌍 **多地区支持**: 支持 JP、US、EMEA、LATAM、CN、OTHER 六个地区
- 📈 **可视化**: 交互式图表展示趋势和对比
- ⚡ **实时更新**: 参数调整后自动重新计算，立即显示结果

## 快速开始

**环境要求:**
- Python 3.10+

**启动步骤:**

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

应用会自动在浏览器中打开：http://localhost:8501

**优点:**
- ✅ 实时更新，参数调整后立即看到结果
- ✅ 开箱即用，一个命令启动
- ✅ 纯 Python，不需要前端代码
- ✅ 便于迭代和调试

## 项目结构

```
20260128/
├── spec.md                    # 需求规范文档
├── README.md                  # 项目说明（本文件）
├── GITHUB_DEPLOYMENT.md       # GitHub 部署指南
│
├── streamlit_app/             # Streamlit 应用
│   ├── app.py                 # Streamlit 主应用
│   ├── default_config.json    # 默认配置文件
│   ├── requirements.txt       # Python 依赖
│   ├── README.md              # Streamlit 版本说明
│   ├── DEPLOYMENT.md          # 部署指南
│   └── .streamlit/            # Streamlit 配置
│
└── backend/                   # 核心计算引擎
    ├── src/
    │   ├── models/            # Pydantic 数据模型
    │   ├── core/              # 核心计算引擎
    │   │   ├── simulator.py  # 模拟器主逻辑
    │   │   ├── retention.py   # 留存率拟合
    │   │   └── dau.py         # DAU 计算
    │   ├── api/               # FastAPI 路由（可选，用于 API 调用）
    │   └── utils/             # 工具函数
    ├── tests/                 # 测试
    ├── examples/              # 示例
    ├── main.py                # FastAPI 入口文件（可选）
    └── requirements.txt
```

## API 接口（可选）

如果需要通过 API 调用后端计算引擎，可以启动 FastAPI 服务：

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

主要接口：
- `POST /api/simulate` - 运行模拟，返回完整结果
- `POST /api/validate` - 校验配置参数有效性
- `POST /api/export` - 导出模拟数据（支持 CSV/JSON）
- `GET /api/default-config` - 获取默认配置
- `GET /health` - 健康检查

## 核心算法

### 留存率拟合

- **Day 1-30**: 幂函数拟合 `R(d) = α × d^β`
- **Day 31+**: 指数衰减 `R(d) = R₃₀ × γ^(d-30)`

### DAU 计算

```
DAU_t = DNU_t + Σ(DNU_t-i × R_new(i)) + (DAU_initial × R_active(t))
```

### 预算计算

```
Budget_t = (Revenue_after_tax,t-1 × base_ratio) + additional_budget
```

## 技术栈

**核心计算引擎（backend）:**
- Python 3.10+
- Pydantic（数据模型）
- NumPy / SciPy（数值计算）

**Streamlit 应用:**
- Streamlit（UI 框架）
- Plotly（图表可视化）

**后端 API（可选）:**
- FastAPI（用于 API 调用）

## 开发

### 运行测试

```bash
cd backend
pytest tests/ -v
```

### 运行示例

```bash
cd backend
python examples/basic_example.py
```

## 许可证

MIT License
