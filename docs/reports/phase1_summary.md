# Phase 1 报告：参考数据层与候选项目清单

> 分支：`feat/phase1-reference-data`；数据取得日期：2026-09-30（UTC）。
> 本报告中的所有数字都来自已提交的 `data/ref/*.csv`，可用 `uv run gradprog build` 从 `data/manifest/manifest.csv` 登记的原始文件逐字节重现。

## 0. 概要

- 四份参考数据（DHS STEM 清单、CIP 2020、IPEDS Completions、College Scorecard Field of Study）以及附属的 IPEDS HD、Federal Register 公告，均已下载或人工登记，并记录在 manifest 中。
- 7 张派生表都可以通过 `derived.csv` 追溯到原始文件的 sha256。重新构建一遍，结果逐字节相同。`uv run pytest` 共 241 个测试，全部通过。
- 候选清单：**490 所学校，1,059 个（学校 × CIP）组合**，分 5 组、组内排序。
- 目标 CIP 共 17 个，其中 16 个在 STEM 清单上，只有 **30.7099 Data Science, Other.** 不在。

---

## 1. 各来源的版本、下载日期与行数

| source | 文件 | 版本 / 年份 | 取得方式与时间（UTC） | 原始行数 | 派生表（行数） |
|---|---|---|---|---|---|
| `dhs_stem` | `stemList2024.pdf`（428,790 B） | **Last Updated 2024-07-22** | 人工，2026-09-30T13:31Z（ice.gov 拒绝自动请求，返回 403） | 表格 540 行 | `stem_list.csv`（466）、`stem_core_series.csv`（4） |
| `federal_register` | `2024-16127.pdf`（govinfo，229,422 B） | 89 FR 59748，2024-07-23 | http，2026-09-30T14:05Z | – | 只存档，不生成派生表 |
| `cip2020` | `CIPCode2020.csv`（1,099,448 B） | CIP 2020（文件日期 2021-07-16） | http，2026-09-30T14:05Z | 2,848 | `cip2020.csv`（2,687 个有效代码） |
| `ipeds_completions` | `C2024_A.zip` 中的 `c2024_a_rv.csv`，另有 `C2024_A_Dict.zip` | **2023-24 学年，final（revised）版** | http，2026-09-30T14:08Z | 307,825 | `ipeds_masters_target_cip.csv`（1,061） |
| `ipeds_hd` | `HD2024.zip` 中的 `hd2024.csv` | HD2024 | http，2026-09-30T14:08Z | 6,072 | 用于 `candidates*.csv` |
| `scorecard_fos` | `Most-Recent-Cohorts-Field-of-Study_06102026.zip`，另有技术文档 PDF、数据字典 xlsx | 发布日期 2026-06-10 | http，2026-09-30T14:10Z | 227,980 | `scorecard_fos_masters_target.csv`（1,034） |

另有 `candidates.csv`（1,059 行）和 `candidates_by_institution.csv`（490 行）。

---

## 2. STEM 清单

- **版本**：DHS STEM Designated Degree Program List，**Last Updated: July 22, 2024**（全文 16 页，页眉与页脚的日期一致）。对应公告为 89 FR 59748（2024-07-23）。截至 2026-09-30，Federal Register 上没有更新的清单公告。
- **结构**：表格共 540 行，其中 466 行是 6 位代码。另外 74 行是核心系列 14/26/27/40 的分组标题：4 个系列标题行，加 70 个 4 位分组标题行（已丢弃）。
- **系列展开规则**：14/26/27/40 这四个系列按 2 位代码整体认定，新增代码自动计入。但 2024 版对这四个系列在 CIP 2020 中的全部 215 个有效代码都已逐条列出，所以展开规则目前不改变任何判断。这一点由 `expected_counts.yaml` 中的哨兵检查持续监控。
- **标题与 CIP 2020 不一致：2 处**（已人工确认，派生表保留 PDF 原文）：
  - `30.4801`：PDF 标题缺少末尾句点。
  - `45.0102`：PDF 标题多了 “Social Sciences, ” 前缀。

### 目标 CIP 与 STEM 清单

| 组 | CIP | 标题 | 在 STEM 清单上 |
|---|---|---|---|
| ds | 30.7001 | Data Science, General. | ✅ |
| ds | **30.7099** | **Data Science, Other.** | **❌** |
| analytics | 30.7101 | Data Analytics, General. | ✅ |
| analytics | 30.7102 | Business Analytics. | ✅ |
| analytics | 30.7103 | Data Visualization. | ✅ |
| analytics | 30.7104 | Financial Analytics. | ✅ |
| analytics | 30.7199 | Data Analytics, Other. | ✅ |
| stats | 27.0501 / 27.0502 / 27.0503 / 27.0599 | Statistics 系列 | ✅（系列 27） |
| stats | 27.0601 | Applied Statistics, General. | ✅（系列 27） |
| mgmt_sci | 52.1301 / 52.1302 / 52.1304 / 52.1399 | Management Sciences and Quantitative Methods 系列 | ✅ |
| econ | 45.0603 | Econometrics and Quantitative Economics. | ✅ |

再次强调（03 §0）：**CIP 在清单上 ≠ 项目是 STEM 认定项目。** 项目的 CIP 由学校在 I-20 上决定。

---

## 3. 候选清单

### 3.1 规模

- 参考表（含属地）：492 所学校，1,061 行。
- 候选清单（仅 50 州 + DC）：**490 所学校，1,059 个（学校 × CIP）组合**，覆盖 51 个州级单位。

| 组 | 行数 | 学校数 | 硕士授予数（第一专业） | 其中 U.S. Nonresident |
|---|---|---|---|---|
| ds | 96 | 95 | 4,327 | 2,177 |
| analytics | 144 | 133 | 8,340 | 5,536 |
| stats | 184 | 170 | 3,915 | 2,309 |
| mgmt_sci | 463 | 335 | **44,601** | 19,382 |
| econ | 172 | 172 | 4,199 | 2,734 |

按 CIP 细分（行数 / 授予数）：
- ds：30.7001（95 / 4,321），30.7099（1 / 6）
- analytics：30.7102（89 / 6,453），30.7101（32 / 930），30.7104（19 / 870），30.7199（3 / 70），30.7103（1 / 17）
- stats：27.0501（136 / 2,710），27.0503（13 / 549），27.0601（22 / 369），27.0502（7 / 172），27.0599（6 / 115）
- mgmt_sci：52.1301（230 / 23,714），52.1399（155 / 16,669），52.1302（60 / 3,986），52.1304（18 / 232）
- econ：45.0603（172 / 4,199）

同一学校出现在几个组中：1 个组 263 所，2 个组 102 所，3 个组 75 所，4 个组 37 所，5 个组 13 所。

### 3.2 各组前 10 名

> 原始指令要求列出“前 30 名”。按第 11 项的决定，候选清单**只在组内排序、不做跨组的总排名**，因此这里改为每组前 10 名，共 50 行。完整排名见 `data/ref/candidates.csv` 的 `rank_in_group` 列。授予数是 2023-24 学年的第一专业硕士学位授予数，括号内为其中 U.S. Nonresident 的人数。

**ds**（Data Science）
| # | 学校 | 州 | CIP | 授予数 |
|---|---|---|---|---|
| 1 | Eastern University | PA | 30.7001 | 664 (16) |
| 2 | University of North Texas | TX | 30.7001 | 344 (336) |
| 3 | Columbia University in the City of New York | NY | 30.7001 | 203 (153) |
| 4 | New Jersey Institute of Technology | NJ | 30.7001 | 201 (154) |
| 5 | The University of Texas at Austin | TX | 30.7001 | 174 (53) |
| 6 | San Jose State University | CA | 30.7001 | 171 (115) |
| 7 | New York University | NY | 30.7001 | 167 (134) |
| 8 | Saint Peter's University | NJ | 30.7001 | 154 (146) |
| 9 | Lewis University | IL | 30.7001 | 122 (108) |
| 10 | University of Virginia-Main Campus | VA | 30.7001 | 120 (10) |

**analytics**（Data Analytics / Business Analytics）
| # | 学校 | 州 | CIP | 授予数 |
|---|---|---|---|---|
| 1 | The University of Texas at Dallas | TX | 30.7102 | 1,033 (898) |
| 2 | Trine University-Regional/Non-Traditional Campuses | IN | 30.7102 | 737 (731) |
| 3 | University of North Texas | TX | 30.7102 | 356 (317) |
| 4 | University of Massachusetts-Amherst | MA | 30.7102 | 271 (115) |
| 5 | East Texas A&M University | TX | 30.7102 | 257 (186) |
| 6 | University of Pennsylvania | PA | 30.7104 | 255 (79) |
| 7 | Hult International Business School | MA | 30.7102 | 250 (244) |
| 8 | University of Chicago | IL | 30.7101 | 246 (164) |
| 9 | Boston University | MA | 30.7102 | 226 (199) |
| 10 | University of Connecticut | CT | 30.7102 | 216 (175) |

**stats**（Statistics / Applied Statistics）
| # | 学校 | 州 | CIP | 授予数 |
|---|---|---|---|---|
| 1 | University of North Texas | TX | 27.0503 | 431 (359) |
| 2 | Columbia University in the City of New York | NY | 27.0501 | 335 (309) |
| 3 | Johns Hopkins University | MD | 27.0501 | 135 (69) |
| 4 | Columbia University in the City of New York | NY | 27.0502 | 103 (95) |
| 5 | Rutgers University-New Brunswick | NJ | 27.0501 | 94 (76) |
| 6 | Texas A&M University-College Station | TX | 27.0501 | 90 (4) |
| 7 | University of Illinois Urbana-Champaign | IL | 27.0501 | 89 (73) |
| 8 | University of Wisconsin-Madison | WI | 27.0501 | 79 (69) |
| 9 | University of Michigan-Ann Arbor | MI | 27.0601 | 71 (61) |
| 10 | Boston University | MA | 27.0501 | 69 (63) |

**mgmt_sci**（Management Sciences and Quantitative Methods）
| # | 学校 | 州 | CIP | 授予数 |
|---|---|---|---|---|
| 1 | Columbia University in the City of New York | NY | 52.1399 | 1,621 (932) |
| 2 | Northwestern University | IL | 52.1301 | 1,617 (387) |
| 3 | Georgia Institute of Technology-Main Campus | GA | 52.1399 | 1,403 (457) |
| 4 | University of Chicago | IL | 52.1301 | 1,251 (439) |
| 5 | New York University | NY | 52.1301 | 1,134 (139) |
| 6 | Northeastern University Professional Programs | MA | 52.1301 | 1,132 (1,013) |
| 7 | Duke University | NC | 52.1399 | 1,062 (540) |
| 8 | University of Illinois Urbana-Champaign | IL | 52.1399 | 1,028 (287) |
| 9 | Harvard University | MA | 52.1399 | 1,010 (371) |
| 10 | University of North Carolina at Chapel Hill | NC | 52.1301 | 954 (113) |

**econ**（Econometrics and Quantitative Economics）
| # | 学校 | 州 | CIP | 授予数 |
|---|---|---|---|---|
| 1 | Johns Hopkins University | MD | 45.0603 | 559 (473) |
| 2 | Columbia University in the City of New York | NY | 45.0603 | 164 (143) |
| 3 | University of Southern California | CA | 45.0603 | 153 (140) |
| 4 | University of Wisconsin-Madison | WI | 45.0603 | 147 (129) |
| 5 | University of California-Los Angeles | CA | 45.0603 | 133 (105) |
| 6 | New York University | NY | 45.0603 | 108 (90) |
| 7 | Harvard University | MA | 45.0603 | 106 (82) |
| 8 | Boston University | MA | 45.0603 | 102 (74) |
| 9 | Texas A&M University-College Station | TX | 45.0603 | 99 (19) |
| 10 | University of Illinois Urbana-Champaign | IL | 45.0603 | 90 (69) |

### 3.3 mgmt_sci 组的规模与 Phase 2 的挑选

- mgmt_sci 组的授予数（**44,601**）远大于其他各组，约为 ds、analytics、stats、econ 四组之和（20,781）的 2 倍。**推测其中包含 STEM 化的 MBA 或管理类硕士**。IPEDS 只到 6 位 CIP，不到项目，无法区分，需要在 **P2 挑选时逐个项目处理**。
- 候选共 **1,059 行**，远多于第一版目标的 100 个项目。**挑选方法待 P2 决定**。本清单只提供起点（组内排序、学校的 CIP 覆盖、国际学生授予数参考），不代表任何取舍。

---

## 4. College Scorecard 在目标 CIP × 硕士层级上的覆盖率

口径：`scorecard_fos_masters_target.csv` 共 1,034 行，即 `CREDLEV = 5`、4 位 CIP 属于目标父级、且有 UNITID 的行。表中每格为 **reported / privacy_suppressed（PS）/ not_available（NA）** 的行数。

| 4 位 CIP | 行数 | IPEDSCOUNT2 | EARN_MDN_1YR | EARN_MDN_4YR | EARN_MDN_5YR | DEBT_ALL_STGP_EVAL_MDN |
|---|---|---|---|---|---|---|
| 27.05 | 180 | 172 / 0 / 8 | 25 / 152 / 3 | 18 / 162 / 0 | 9 / 168 / 3 | 7 / 164 / 9 |
| 27.06 | 21 | 20 / 0 / 1 | 0 / 18 / 3 | 0 / 21 / 0 | 0 / 18 / 3 | 0 / 14 / 7 |
| 30.70 | 90 | 89 / 0 / 1 | **0** / 32 / 58 | **0** / 90 / 0 | **0** / 32 / 58 | 0 / 17 / 73 |
| 30.71 | 123 | 118 / 0 / 5 | **0** / 31 / 92 | **0** / 123 / 0 | **0** / 31 / 92 | 0 / 18 / 105 |
| 45.06 ⚠ | 251 | 243 / 0 / 8 | 24 / 218 / 9 | 22 / 229 / 0 | 16 / 226 / 9 | 13 / 227 / 11 |
| 52.13 | 369 | 351 / 0 / 18 | 121 / 193 / 55 | 92 / 277 / 0 | 37 / 277 / 55 | 93 / 193 / 83 |
| **合计** | **1,034** | 993 / 0 / 41 | **170 (16%)** / 644 / 220 | **132 (13%)** / 902 / 0 | **62 (6%)** / 752 / 220 | 113 (11%) / 633 / 288 |

- ⚠ 45.06 是整个 Economics 系列（`cip4_broader_than_target = true`），不能等同于 45.0603。
- **30.70 和 30.71（data science 与 analytics 两组的全部 CIP）没有任何一行有已报告的收入数据**。原因是收入队列（AY2014–2020）早于这些 CIP 2020 新代码的普及。
- 另外排除了 **57 行 UNITID = NA** 的记录（全文件共 7,020 行），主要是参与 Title IV 的外国学校，如 LSE、UBC、Oxford 各学院，另有已关闭的 Mills College 等。
- 候选清单中的（学校 × 4 位 CIP）组合共 913 个，其中 825 个能在 Scorecard 中找到对应行。

**结论**：Scorecard 在硕士层级的收入覆盖率只有 **6–16%**，而且**只统计 Title IV 联邦资助受助者**。F-1 等学生签证持有者不具备联邦资助资格（studentaid.gov “Eligibility for Non-U.S. Citizens”），所以这些数据**不代表国际学生**。因此，**第一版不做基于 Scorecard 的项目级 ROI，列为第二版待定，届时再评估其他数据源**。第一版中 Scorecard 只作为参考表保留，不进入候选排序。

---

## 5. 排除项与异常记录

| 事项 | 数量 | 处理 | 依据 |
|---|---|---|---|
| 候选清单排除的属地行 | PR 2 行（2 所学校） | 参考表保留，候选清单排除 | 04 §4.1 |
| Scorecard 中 UNITID = NA 的行 | 目标父级 × 硕士 57 行（全文件 7,020 行） | 从派生表中排除，并计数 | 01 §5，2026-09-30 确认 |
| IPEDS 授予数为 0，或只有第二专业的行 | – | 剔除 | 04 §3 |
| STEM PDF 标题与 CIP 2020 不一致 | 2 处 | 保留 PDF 原文，写入 `expected_counts.yaml` 监控 | 03 §3.2 |
| Federal Register 纯文本链接返回 HTML 页面 | 1 | 下载器拒绝，改用 govinfo 官方 PDF | 01 §1.1 |
| ice.gov 拒绝自动下载（403） | 1 | 人工下载并登记，manifest 中 `method = manual` | 01 §7.2 |
| IPEDS 插补值 | 0（目标行的 `XCTOTALT` 全部为 R） | – | – |
| 第二专业授予数大于 0 的行 | 34 | 单独成列，不参与排序 | 04 §3 |

---

## 6. 待确认与待定事项

**Phase 2 需要决定**
1. **从 1,059 个候选中挑选 100 个项目的方法**（名额是否按组分配、如何对待多校区或非传统校区的 UNITID 等）。
2. **mgmt_sci 组（52.13）中 STEM 化 MBA 的识别与取舍**：需要逐个项目查看学校页面，IPEDS 无法区分。
3. **授课形式**：IPEDS 不区分线上和线下。Trine University-Regional/Non-Traditional Campuses、Northeastern University Professional Programs 这类 UNITID 可能以线上或非传统项目为主。02 中的 `delivery_mode` 要在 P2 从学校页面确认（online 项目通常不能办 F-1）。
4. **02 草案 §7 的三项待定**：研究生院页与系页数值冲突时的优先规则；学费是否区分州内和州外；track/concentration 是否拆成多个 `program_id`。
5. **每个申请季开始时全量重抽的具体日期**（05 §5）。

**第二版待定**
6. **基于 Scorecard 的项目级 ROI**：第一版不做，到时再评估其他数据源（见 §4）。
7. **第二版候选 CIP**（04 §2，共 19 个）：26.1102 Biostatistics、27.0305 Financial Mathematics 等。

**关于官方数据的已知不确定性**（已记入 01，目前不影响结果）
8. Scorecard CSV 用 `PS`/`NA` 表示缺失，文档写的却是 “PrivacySuppressed”，数据字典中也找不到 `PS`/`NA` 的定义。目前按字面含义解释。
9. Scorecard 技术文档的版本（2025-09）早于数据发布（2026-06），可能没有随新数据更新。
10. CIP 2020 CSV 并没有在 NCES 页面上直接链接，页面上只有 Excel 和 Word 按钮。已确认采用这个 CSV。
11. 学校名称取自 HD2024（2024-25 年度目录），授予数据是 2023-24 学年。其间改名或合并的学校以 HD2024 的名称为准。

**维护事项**
12. **数据更新的监控**：
    - STEM 清单每年 8 月 1 日截止提名，之后可能在 Federal Register 公告更新。
    - IPEDS C2025 目前只有临时版，按 NCES 发布周期推断，最终版约在一年后发布。
    - 任何更新都会让 `config/expected_counts.yaml` 相关的测试失败，需要人工确认后再修改该文件。
13. **期望值覆盖面**：`expected_counts.yaml` 目前只锁定了 STEM、CIP 和目标 CIP 的数量。IPEDS 和 Scorecard 的行数将在 **P2 中实施**锁定，按数据年份（如 C2024）分别记录。
14. **下载器的联系邮箱**：`GRADPROG_CONTACT_EMAIL` 在本次会话的 shell 中读取不到，这次是在命令中临时传入的。建议写进 shell 配置文件，但不要提交进 git。

---

## 7. 复现方法

```bash
uv sync
uv run gradprog register-manual --source dhs_stem --url https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf \
  --file <浏览器下载的 PDF> --retrieved-at <UTC 时间> --notes "automated request returned HTTP 403; ..."
GRADPROG_CONTACT_EMAIL=<联系邮箱> uv run gradprog download federal_register cip2020 ipeds_completions ipeds_hd scorecard_fos
uv run gradprog build
uv run pytest
```

新下载的文件如果与本报告使用的版本不同，它们的 sha256 会变，`derived.csv` 中会记录新的输入。数量上的变化会被 `config/expected_counts.yaml` 相关的测试捕获。
