# cisc7204-Assgn02-2026-MC663312

**CISC7204 Assignment 02 — Data Visualization with Python**
LI Tianhao ｜ Student ID: MC663312 ｜ Class K ｜ Pair 14 (with LI Yingfang, mc661599)
Due: 2026-OCT-25 23:00 ｜ UMMoodle HOME site Class K

---

## About this repository / 仓库说明

Public archive of my Assignment 02 artifacts: fifteen lab notebooks and Dash project
spaces from the five modules (Matplotlib / Seaborn / Folium / Plotly / Dash), together
with the revised pair project proposal and the analysis project behind it.

本仓库是本人 CISC7204 Assignment 02 的公开归档：五个模块共 15 个 lab 的
notebook 与 Dash 工程、配对项目提案（修订版 Word）、以及提案背后的完整分析工程。

> Raw/processed BTS data (~570 MB) is **not** committed — it is re-downloadable, and
> GitHub rejects files over 100 MB. 原始数据不入库，可用 `Analysis/run_all.py` 重新生成。

---

## 目录结构 / Layout

```
cisc7204-Assgn02-2026-MC663312/
├─ Module01/                     基础可视化（2 labs）
│   ├─ Lab01/                    executed .ipynb + Screen Shots/
│   └─ Lab02/
├─ Module02/                     专项图表工具（3 labs）
├─ Module03/                     高级可视化与地理数据（2 labs）
├─ Module04/                     Plotly 与 Dash（4 labs，Lab02–04 为 Dash 工程）
├─ Module05/
│   ├─ Practice Project/         Lab01 notebook + Lab02 Dash 工程
│   └─ Final Project/            Lab01 notebook + Lab02 Dash 工程
├─ CISC7204-Assgn02-Project Proposal/
│   ├─ CISC7204-Assgn02-Pair14-RevisedProjectProposal.docx   5 页 A4，11 节，5 表 2 图
│   └─ Analysis/                 提案分析工程（4 notebook / 16 图 / Dash app / run_all.py）
├─ .gitignore
└─ _README_工作空间说明.md       本文件
```

每个 `Lab0X/` 里放该 lab 的**已执行 notebook**（或 Dash 工程的源码与数据文件）
以及 `Screen Shots/` 截图目录（按 `01_`、`02_` … 递增编号）。

---

## 交付状态 / Status

| 项目 | 数量 | 说明 |
|---|---|---|
| 已执行 notebook | 10 个 | 全部有输出，**0 个 error 单元格** |
| Dash 工程 | 5 个 | Module 04 Lab02–04、Module 05 Practice/Final Lab02 |
| 截图 | **206 张** | 其中 204 张已用于 UMMoodle 个人论坛举证 |
| 提案文档 | 1 个 | 5 页 A4、2,116 词、References 4 条 APA 7 |
| 分析 notebook | 4 个 | 数据准备 / 归因 EDA / 右尾悖论 / 统计建模 |

UMMoodle 侧的交付已完成：五个模块个人论坛 37 条帖子（15 条举证帖 + 15 条逐 lab
上传帖 + 5 条模块汇总帖 + 提案帖）、协作论坛 2 条帖子（提案 + 协作细节）、
三个提交链接均已 `Submitted for grading`。

> 笔记：15 个 lab 中的 5 个以**项目归档 zip** 形式上传说，那些 zip 已随本次整理从
> 本地移除，其内容（`.py`、`.json`、`Screen Shots/`）保留在对应 `Lab0X/` 目录中，
> 需要时可重新打包；Moodle 上的副本不受影响。

---

## 复现 / Reproduce

```bash
# 1) 提案分析工程：自动下载 BTS 数据、清洗、出图、跑模型
python "CISC7204-Assgn02-Project Proposal/Analysis/run_all.py"

# 2) 单个 lab：直接用 Jupyter 打开对应 .ipynb 并 Run All
jupyter lab Module01/Lab01
```

环境：Python 3.13 + pandas / matplotlib / seaborn / folium / plotly / dash（原始 lab
在 Anaconda + Theia IDE 中完成；地理可视化部分需要 `geoplotlib`，另见
`Module03/Lab02` 内的兼容说明）。

---

## 学术诚信 / Academic integrity

Pair 14 的两人（MC663312 LI Tianhao、mc661599 LI Yingfang）按课程公告允许**共用同一套
artifacts**，并在提案首页、提案文档与协作论坛中声明了配对信息与分工。所有代码与图表
均由本人（或本人与搭档）完成，数据来源为公开的 BTS Airline On-Time Performance 数据集。
