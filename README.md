# Vehicle Test Analysis - 车载控制器测试数据分析与测试报告编写系统

## 项目简介

本系统是一个本地部署的测试数据分析与报告生成工具，支持 MIL/HIL/DVP/整车测试的数据分析与报告生成。

## 主要功能

- **多格式数据解析**: 支持 CAN 日志(.blf, .asc)、MDF(.mf4)、CSV、DBC 等多种格式
- **时间同步**: 多数据源时间对齐，精度达 10ms
- **指标计算**: 支持时域、统计、自定义公式等多种计算方式
- **报告生成**: 自动生成 Word/PDF 格式的测试报告
- **数据溯源**: 审核报告包含完整的数据溯源信息

## 技术栈

- Python 3.10+
- 数据处理: Pandas, NumPy, SciPy
- CAN 解析: cantools, python-can
- MDF 解析: asammdf
- 数据库: SQLite (SQLAlchemy)
- 报告: python-docx, reportlab
- 界面: PyQt6

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 10/11 或 Linux

### 安装

```bash
# 克隆或下载项目后，进入项目目录
cd vehicle_test_analysis

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装项目（开发模式）
pip install -e .
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html

# 只运行单元测试
pytest tests/unit/

# 只运行集成测试
pytest tests/integration/
```

### 启动应用

**命令行方式:**
```bash
# 命令行入口
python -m src.main

# 或使用安装后的命令
vta
```

**图形界面方式:**
```bash
# GUI 入口
python -m src.main --gui

# 或使用安装后的命令
vta-gui
```

## 项目结构

```
vehicle_test_analysis/
├── docs/               # 文档
│   └── requirements.md # 需求文档
├── config/             # 配置文件
├── data/               # 数据目录
├── database/           # 数据库文件
├── src/                # 源代码
│   ├── core/           # 核心模块
│   │   ├── indicator_engine.py  # 指标计算引擎
│   │   └── time_sync.py         # 时间同步模块
│   ├── parsers/        # 数据解析器
│   │   ├── base_parser.py       # 解析器基类
│   │   ├── can_parser.py        # CAN 日志解析
│   │   ├── csv_parser.py        # CSV 解析
│   │   ├── dbc_parser.py        # DBC 数据库解析
│   │   └── mdf_parser.py        # MDF 文件解析
│   ├── analyzers/      # 分析模块
│   │   ├── functional_analyzer.py  # 功能分析
│   │   └── performance_analyzer.py # 性能分析
│   ├── report/         # 报告模块
│   │   ├── pdf_report.py   # PDF 报告生成
│   │   └── word_report.py  # Word 报告生成
│   ├── database/       # 数据库模块
│   │   ├── models.py       # 数据模型
│   │   └── operations.py   # 数据库操作
│   ├── ui/             # 用户界面
│   │   └── main_window.py  # 主窗口
│   └── main.py         # 入口点
└── tests/              # 测试代码
    ├── unit/           # 单元测试
    └── integration/    # 集成测试
```

## 核心模块使用指南

### 1. 数据解析

```python
from pathlib import Path
from src.parsers.csv_parser import CSVParser
from src.parsers.can_parser import CANParser
from src.parsers.mdf_parser import MDFParser
from src.parsers.dbc_parser import DBCParser

# 解析 CSV 文件
csv_parser = CSVParser(Path("data.csv"), time_column="time")
result = csv_parser.parse()
if result.is_success:
    df = result.data
    print(f"解析成功，共 {len(df)} 行数据")

# 解析 CAN BLF 文件
can_parser = CANParser(Path("can.blf"))
result = can_parser.parse()

# 解析 MDF 文件
mdf_parser = MDFParser(Path("data.mf4"))
result = mdf_parser.parse()

# 解析 DBC 数据库
dbc_parser = DBCParser(Path("database.dbc"))
result = dbc_parser.parse()
messages = dbc_parser.get_all_messages()
```

### 2. 指标计算

```python
from src.core.indicator_engine import (
    IndicatorEngine,
    IndicatorDefinition,
    IndicatorType,
)

engine = IndicatorEngine()

# 单值指标
indicator = IndicatorDefinition(
    name="最大车速",
    signal_name="VehicleSpeed",
    indicator_type=IndicatorType.SINGLE_VALUE,
    upper_limit=120.0,
)
result = engine.calculate(indicator, df)

# 统计指标
indicator = IndicatorDefinition(
    name="平均转速",
    signal_name="EngineRPM",
    indicator_type=IndicatorType.STATISTICAL,
    formula="mean",
)
result = engine.calculate(indicator, df)

# 自定义公式
indicator = IndicatorDefinition(
    name="计算指标",
    indicator_type=IndicatorType.CALCULATED,
    formula="signal1[-1] * 2 + signal2[-1]",
)
result = engine.calculate(indicator, df)

# 时域分析
indicator = IndicatorDefinition(
    name="响应时间",
    signal_name="ResponseSignal",
    indicator_type=IndicatorType.TIME_DOMAIN,
    formula="response_time",
)
result = engine.calculate(indicator, df)
```

### 3. 时间同步

```python
from src.core.time_sync import TimeSynchronizer

sync = TimeSynchronizer(precision_ms=10.0)

# 对齐多个数据源
aligned_df = sync.align_to_common_time(
    [df1, df2, df3],
    ["time", "timestamp", "t"],
)
```

### 4. 报告生成

```python
from src.report.word_report import WordReportGenerator
from src.report.pdf_report import PDFReportGenerator

# Word 报告
word_gen = WordReportGenerator()
word_gen.add_title("测试报告")
word_gen.add_paragraph("测试概述...")
word_gen.add_table(headers, data)
word_gen.save("report.docx")

# PDF 报告
pdf_gen = PDFReportGenerator()
pdf_gen.add_title("测试报告")
pdf_gen.add_content("测试内容...")
pdf_gen.save("report.pdf")
```

## 开发指南

### 代码风格

项目使用以下工具保持代码质量：

```bash
# 格式化代码
black src tests

# 排序导入
isort src tests

# 类型检查
mypy src

# 代码检查
flake8 src tests
```

### 添加新的解析器

1. 继承 `BaseParser` 类
2. 实现 `parse()` 方法
3. 返回 `ParseResult` 对象
4. 添加对应的单元测试

### 添加新的指标类型

1. 在 `IndicatorType` 枚举中添加新类型
2. 在 `IndicatorEngine.calculate()` 中实现计算逻辑
3. 添加对应的单元测试

## 测试覆盖率

项目要求测试覆盖率不低于 80%。当前覆盖情况：

- 解析器模块: 完整覆盖
- 指标引擎: 完整覆盖
- 时间同步: 完整覆盖
- 数据库操作: 完整覆盖
- 报告生成: 完整覆盖

## 已知限制

1. **GUI 功能**: 当前 GUI 为框架实现，核心功能通过 API 使用
2. **TDMS 支持**: 已在依赖中包含 npTDMS，但解析器尚未实现
3. **大数据集**: 超大文件（>1GB）可能需要优化内存使用

## 许可证

MIT License

## 更新日志

### v0.1.0 (2024-03)
- 初始版本
- 支持主要数据格式解析
- 指标计算引擎
- 时间同步功能
- Word/PDF 报告生成
- 数据库存储
