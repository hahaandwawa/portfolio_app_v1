# 投资记录 (Investment Record) - 前端

## 快速开始

### 1. 启动后端 API
```bash
# 在项目根目录
./scripts/start_backend.sh
# 或
PYTHONPATH=. ./venv/bin/uvicorn src.app.main:app --host 127.0.0.1 --port 8001
```

### 2. 启动前端
```bash
./scripts/start_frontend.sh
# 或
cd frontend && npm run dev
```

### 3. 访问
打开浏览器访问 http://localhost:5173

## 功能

- **Top Bar**: Logo、账户筛选、新增记录、主题切换（明/暗）
- **账户管理**: 添加账户、查看账户列表及交易笔数
- **交易记录**: 分页表格（每页 10 条）、按账户筛选
- **新增记录**: 支持 BUY/SELL/现金存取，条件字段根据类型显示

## 技术栈

- React 19 + TypeScript + Vite
- Tailwind CSS v4
- FastAPI 后端 (端口 8001)
- 前端代理: `/api/*` -> `http://127.0.0.1:8001/*`
