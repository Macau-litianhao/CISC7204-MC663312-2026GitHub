# 美国国内航班延误成因研究（US Domestic Flight Delay Drivers）

**CISC7204 数据科学与数据可视化 — 学期项目 — Class K, Team 01**

AO KIT I（MC660004）· LI YING FANG（MC661599）· HO MAN HOU（MC661647）·
WU PEI YE（MC661846）· LI TIAN HAO（MC663312）· SAVIDI AVRAM（MC664364）

> 本文件为仓库根目录 `README.md` 的**中文对照版，仅供组内审阅**。技术标识（文件名、命令、字段名、库名）保留英文原文，便于与代码对照。

一个**端到端、可复现**的美国国内航空延误分析：延误分钟从哪里来、它们如何在同一运营日内被继承、存在哪些机场原型、哪些因素决定延误时长与严重延误风险，以及一个联动式网页工具如何把这些结论传达给非专业读者。

> **研究问题**
>
> **RQ1** 已报告的延误分钟在 BTS 五类原因之间如何分布？该构成在 2015–2024 年间有多稳定？
> **RQ2** 某一小时观测到的延误中，有多大比例继承自同一架飞机更早的航段？这种级联在哪些机场最集中？
> **RQ3** 把规模与原因构成一起考虑后，美国机场是否分成彼此不同的延误风险原型？区分它们的是什么？
> **RQ4** 给定航线、起飞小时与月份，延误风险能被多好地排序？一个联动网页工具能否让非专业用户据此行动？

---

## 状态

| 组成 | 当前状态 |
|---|---|
| 提案（PDF，10 页） | `docs/proposal/CISC7204-Team01-ProjectProposal.pdf` — 第 4 节已给出区域、领域类别与 5 个数据集 D1–D5 的完整链接 |
| 流水线（7 个阶段） | 已实现且可运行；在真实十年面板（`TEAM01_MODE=full`）上完成端到端运行 |
| 仪表板（8 面板） | 已实现；基于 Dash + Plotly 本地运行，含结论带、"乘客须知"收尾带、逐面板图注与方法/局限节 |
| 测试 | 53 个通过（`python -m pytest tests -q`） |
| 真实面板（2015–2024） | **已下载并分析**：63,079,392 行 / 61,689,698 完成航班、20 家承运人。`figures/`、`outputs/` 与仪表板的全部数字现均来自 `TEAM01_MODE=full` |

提案中引用的试点数字来自 Assignment 02 那一年（2024），**不是**从本仓库的合成数据复现出来的。凡在 `TEAM01_MODE=sample` 下产出的内容，都会标注为"版式演示"。

---

## 快速开始

```bash
python -m pip install -r requirements.txt      # 或：conda env create -f environment.yml

# 1. 十分钟、无需下载：构建合成数据并跑完全部阶段
python run_all.py --stage smoke

# 2. 用上个阶段的产出启动仪表板
python dashboard/app.py                        # http://127.0.0.1:8050

# 3. 真实数据（约 4 GB 下载，视网速 1–3 小时）
python run_all.py --stage data                 # BTS 月度压缩包 + OurAirports
python run_all.py --stage pipeline             # 运行全部分析阶段
```

`make` 目标与上面完全对应（`make smoke`、`make data`、`make pipeline`、`make dashboard`、`make test`）；之所以还提供 `run_all.py`，是因为默认的 Windows 机器上通常没装 `make`。

---

## 目录结构

```text
Team01-FlightDelay-Project/
├── README.md                     本文件
├── requirements.txt              pip 依赖
├── environment.yml               用于精确复现的 conda 环境
├── Makefile                      每个阶段一个目标
├── run_all.py                    不依赖 make 的同款阶段入口
├── config/
│   └── project.yaml              唯一参数源：年份、随机种子、路径、阈值
├── data/
│   ├── README.md                 数据字典、来源、许可、阈值
│   ├── raw/                      BTS 压缩包、OurAirports CSV（已被 Git 忽略）
│   ├── interim/                  合并与筛选的中间结果（已被 Git 忽略）
│   ├── processed/                flights.parquet、airport_features.parquet（已被 Git 忽略）
│   └── sample/                   供测试与演示用的合成数据
├── src/
│   ├── team01/                   可导入的包
│   │   ├── config.py             配置加载与路径解析
│   │   ├── schema.py             列模式、原因分类、颜色常量
│   │   ├── io.py                 下载、Parquet 读写、校验清单
│   │   ├── clean.py              类型转换、时间派生字段、校验
│   │   ├── features.py           级联重建、机场特征矩阵
│   │   ├── attribution.py        原因拆分、bootstrap 区间、稳定性
│   │   ├── tail.py               分位数、Lorenz、均值-尾部检验
│   │   ├── cluster.py            k 扫描、k-means、Ward 校验、稳定性、命名
│   │   ├── models.py             序贯 R²、分位数回归、风险模型
│   │   ├── viz.py                图库（一张图一个函数）
│   │   └── synth.py              与真实模式一致的合成数据
│   └── scripts/                  阶段入口 00–07
├── notebooks/                    七个叙事 notebook + build_notebooks.py（生成并执行）
├── dashboard/
│   ├── app.py                    入口
│   ├── layouts.py                静态版式
│   ├── callbacks.py              一组筛选器 → 八个面板
│   ├── narrative.py              随筛选重算的三条结论（含问题标签）
│   ├── captions.py               每个面板下方一句"这说明了什么"，与图形同源聚合
│   ├── panels/                   一面板一模块 + theme.py（共享颜色与版式）
│   ├── data_access.py            缓存数据帧、聚合、筛选
│   └── assets/                    style.css（框架与控件）+ narrative.css（结论条、页脚、chip）
├── figures/                      01–14，300 dpi，由阶段 03–07 重新生成
├── outputs/
│   ├── tables/                   报告中引用的 CSV 结果
│   └── metrics/                  仪表板读取的 JSON 摘要
├── docs/
│   ├── proposal/                 已提交 PDF 与源 DOCX
│   ├── meeting-minutes/          模板 + 第一次纪要
│   ├── video/                    五分钟视频脚本
│   ├── forum/                    两份必交的论坛发帖
│   ├── standards/                命名、代码风格、可视化规范
│   └── submission-checklist.md   提交前检查闸口
├── tests/                        53 个测试，覆盖数据层、分析层、图表层、面板图注与收尾建议
└── reports/                      最终报告（`report.md` 已起草）与导出的提交包
```

---

## 范围：区域与领域类别

| | |
|---|---|
| **区域** | 美利坚合众国——50 个州加哥伦比亚特区，含阿拉斯加、夏威夷，跨越四个时区。美国海外领地与国际航段均被排除，因此每一行都是"从美国机场起飞、在美国机场降落"的定期国内客运航班。描述性背景覆盖 2007–2024，分析面板覆盖 2015–2024。结果按全国、州（起飞州）、机场（起飞机场）三级报告。 |
| **领域类别** | 交通——商业航空（航空公司运营与空中交通绩效）。观测单位：一个航段。结果变量：到达延误分钟及其厚尾。候选驱动因素：执飞承运人、两端机场、航段在飞机当日排班中的位置、日历、地面气象。 |
| **简写形式** | United States（美国）与 transportation / commercial aviation（交通 / 商业航空）。 |

---

## 数据

五个公开数据集，均无需登录或 API 密钥。全部链接于 **2026 年 11 月 2 日**重新核验，均返回 HTTP 200。

| 编号 | 数据集与出版方 | 作用 | 覆盖范围 | 完整链接 |
|---|---|---|---|---|
| D1 | Reporting Carrier On-Time Performance, 1987–present — 美国运输统计局（BTS） | 主要航班级记录（公布 110 字段，保留 37 个） | 2015–2024 每年 12 个月度文件，共 63,079,392 行（其中 61,689,698 为已完成航班） | <https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGJ> |
| D2 | Airline On-Time Performance: Delay Cause — BTS | 对逐航班归因的全国口径交叉校验 | 月度聚合，2003 年至今 | <https://www.transtats.bts.gov/OT_Delay/OT_DelayCause1.asp> |
| D3 | Integrated Surface Database（逐时）— NOAA NCEI | 起飞机场逐时气象（风、能见度、降水、云底高、气温） | 40 个最繁忙起飞机场 × 10 年 | <https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database> · 直接获取：<https://www.ncei.noaa.gov/data/global-hourly/access/> |
| D4 | `airports.csv` — OurAirports（公有领域） | 经纬度、州、类型、定期服务标记，用于地图与枢纽分层 | 全球约 7.5 万机场，筛选为美国机场 | <https://davidmegginson.github.io/ourairports-data/airports.csv> |
| D5 | Air Traffic by the Numbers / Passenger Boarding — FAA | 验证由 D4 推导的枢纽分层 | 年度，美国商业服务机场 | <https://www.faa.gov/air_traffic/by_the_numbers> · <https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger> |

D1 的月度档案直链（替换年份与月份）：

```text
https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip
```

**报告阈值说明。** BTS **只对到达延误 ≥15 分钟**的航班公布五个原因分钟字段。试点已直接验证：阈值以上的 1,449,966 个航班中有 1,449,964 个带有完整原因拆分（99.9999%），阈值以下则完全没有。本项目的每一句原因相关陈述都限定在该"归因域"内；行数、均值与分位数使用全部已完成航班。`src/scripts/02_validate.py` 会逐年重做这项检查。

五个来源（D1–D5）全部公开、无需登录或密钥：D1、D2、D5 为美国联邦出版物，D3 为美国联邦数据（公有领域），D4 为公有领域奉献。**不处理任何个人数据。** 原始文件不纳入版本控制，可从文档化 URL 重新下载；`data/checksums.sha256` 清单记录任一报告结果背后的确切文件。

---

## 流水线如何运行

| 阶段 | 脚本 | 产出 |
|---|---|---|
| 0 | `00_make_sample.py` | 真实模式下的合成数据（`TEAM01_MODE=sample`） |
| 1 | `01_acquire.py` | 原始压缩包 → 带类型的 Parquet，逐文件校验，校验清单 |
| 2 | `02_validate.py` | 逐年行数、重复、缺失率、阈值覆盖率 |
| 3 | `03_attribution.py` | 原因拆分 + bootstrap 区间、逐年稳定性、图 01–03、07 |
| 4 | `04_tail.py` | 分位数、Lorenz 曲线、均值-尾部检验、级联、图 04–06、08、14 |
| 5 | `05_clusters.py` | 机场特征矩阵、k 扫描、聚类、Ward 校验、图 09–10 |
| 6 | `06_models.py` | 序贯 R²、OLS(HC1)、p90 分位数、风险分类器、图 11–12 |
| 7 | `07_figures.py` | 图表清点检查与拼版缩略图（图 13） |

每个阶段都读取 `config/project.yaml`，并写入 `outputs/tables`、`outputs/metrics` 与 `figures`。阶段 3–6 还会写一份 JSON 指标文件供仪表板读取，因此**屏幕上的数字与报告里的数字来自同一次计算**。

### 模型声明了什么，没声明什么

- **序贯 R²** 对五个可观测因素排序。它描述的是**解释方差**，不是因果：BTS 原因分钟是由承运人指定的报告分区。
- **p90 分位数回归**回答"是什么在推动尾部"。
- **风险分类器**给航班**排序**。试点的天花板（R² 0.029、AUC 0.679）说明五个可观测因素无法承诺一个到达时刻——报告把这一点写进"局限"，而不是藏进脚注。
- **聚类**连同轮廓系数选出的 k、Ward 交叉校验、cophenetic 相关系数与子样本稳定性分数一起报告。不稳定的解会**被标注为不稳定**，而不是包装成一套机场分类学。

---

## 可复现性契约

1. **参数只有一个地方。** 年份、种子、阈值、样本量与路径都在 `config/project.yaml`。没有任何阶段硬编码路径。
2. **固定种子。** 每个抽样与每个随机模型都从配置取种子，两次运行产生完全相同的数字。
3. **数据溯源。** `data/checksums.sha256` 记录每个原始文件的 SHA-256。
4. **提交前必须测试。** `python -m pytest tests -q` 必须通过；测试套件保护的是**结论**（阈值口径、级联算术、集中度、矩阵对齐），不只是语法。
5. **干净运行声明。** `python run_all.py --stage smoke` 能在两分钟内从空的 `outputs/` 重建全部产出——这是过期的图表在进入报告之前被抓住的方式。

---

## 规范

命名、代码风格与可视化规则都是**写下来的**，而不是默认的：
[`docs/standards/naming-conventions.md`](docs/standards/naming-conventions.md)、
[`docs/standards/code-style.md`](docs/standards/code-style.md)、
[`docs/standards/viz-guidelines.md`](docs/standards/viz-guidelines.md)。

简而言之：处处 `snake_case`；阶段编号 `00`–`07`；图表按其在报告中的出现顺序编号；每类延误原因固定一个颜色；**不允许出现"只给均值、不给分布"的图**。

---

## 团队与角色

| 成员 | 角色 | 职责 |
|---|---|---|
| AO KIT I | 团队协调人、项目跟踪 | 议程与主持、任务板、里程碑、依赖图、风险日志、推动提交 |
| LI YING FANG | 项目开发（主导） | 数据流水线、notebook 与仓库结构、可复现脚本、仪表板工程、主导代码评审 |
| HO MAN HOU | 团队记录员 | 纪要、决策日志、范围变更日志、仓库目录约定与命名 |
| WU PEI YE | 团队报告人、团队联络人 | 提案叙事、介绍视频脚本、教师联络、最终提交包 |
| LI TIAN HAO | 项目分析员、质量评审 | 研究问题、数据来源、数据准备与分析、解读与局限；质量关卡 |
| SAVIDI AVRAM | 项目开发 | 图表、可视化与交互输出（地图、原型）、十年扩展、天气连接、介绍视频录制与剪辑 |

角色在项目**中期轮换**。

---

## 局限

1. **观察性，非因果。** BTS 原因分钟是一种报告分区。
2. **一个面板，一个国家。** 仅美国国内，不含国际航段。
3. **气象不完整。** 逐时观测只挂到最繁忙机场，较小机场的气象效应被吸收进残差。
4. **预测是排序。** R² 与 AUC 数值如实报告，不隐去。
5. **2020 年保留但加标记**，头条结果会以"剔除 2020"的形式重做一遍作为敏感性分析。

---

## 版权与致谢

澳门大学 CISC7204 课程作业，2026/2027 学年。数据版权归各美国联邦机构与 OurAirports 贡献者所有。代码由 Team 01 在课程学术诚信规则下编写；第三方库的引用见提案的参考文献列表。
