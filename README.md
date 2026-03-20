# Vehicle Test Analysis - 车载控制器测试数据分析与测试报告编写系统

## 项目简介

本系统是一个本地部署的测试数据分析与报告生成工具，支持 MIL/HIL/DVP/整车测试的数据分析与报告生成。

## 主要功能

- **多格式数据解析**: 支持 CAN 日志(.blf, .asc)、MDF(.mf4)、CSV、TDMS 等多种格式
- **时间同步**: 多数据源时间对齐，精度达 10ms
- **指标计算**: 支持时域、统计、自定义公式等多种计算方式
- **报告生成**: 自动生成 Word/PDF 格式的测试报告
- **数据溯源**: 审核报告包含完整的数据溯源信息

## 技术栈

- Python 3.10+
- 数据处理: Pandas, NumPy, SciPy
- CAN 解析: cantools, python-can
- MDF 解析: asammdf
- 数据库: SQLite
- 报告: python-docx, reportlab
- 界面: PyQt6

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行测试

```bash
pytest
```

### 启动应用

```bash
python -m src.main
```

## 项目结构

```
vehicle_test_analysis/
├── docs/               # 文档
├── config/             # 配置文件
├── data/               # 数据目录
├── database/           # 数据库文件
├── src/                # 源代码
│   ├── core/           # 核心模块
│   ├── parsers/        # 数据解析器
│   ├── analyzers/      # 分析模块
│   ├── report/         # 报告模块
│   ├── database/       # 数据库模块
│   └── ui/             # 用户界面
└── tests/              # 测试代码
```

## 开发指南

详见 [docs/requirements.md](docs/requirements.md)

## 许可证

MIT License
