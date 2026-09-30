# 01 参考数据来源

> 状态：v1.1（Phase 1b，已按 2026-09-30 的逐项答复修订）。下文“已确认”的 URL、文件名、编码值，均于 **2026-09-30** 从官方页面或官方文档核对，标注了出处。
> 共 5 个来源，另有 1 个附属记录。source 名（manifest 的 `source` 列、`data/raw/<source>/` 目录名）固定为：`dhs_stem`、`federal_register`（附属于 dhs_stem）、`cip2020`、`ipeds_completions`、`ipeds_hd`、`scorecard_fos`。

---

## 1. DHS STEM Designated Degree Program List（source = `dhs_stem`）

| 项 | 内容 |
|---|---|
| 发布机构 | DHS / U.S. Immigration and Customs Enforcement（ICE）/ SEVP |
| 官方入口页 | https://www.ice.gov/sevis/schools ，“DHS STEM Designated Degree Program List and CIP Code Nomination Process” 一节 |
| 实际下载 URL | https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf （入口页链接文字为 “Current STEM list”；另有 2023/2022/2020/2016 存档版） |
| 取得方式 | **人工**：用浏览器下载后，用 `register-manual` 登记（method = `manual`），见 §7 |
| 格式 | PDF 1.6，16 页；PDF 元数据 Title = “2024 DHS STEM Designated Degree Program List” |
| 清单版本日期 | 页眉与页脚：**Last Updated: July 22, 2024**；HTTP Last-Modified: Mon, 22 Jul 2024 13:55:40 GMT |
| 2026-09-30 观测到的文件 | 428,790 字节，sha256 `b8346f30cd6ab7702510f4837b339438323a96adfbd8133b6cb9d565e90b4336`（在浏览器中取得，仅作参照；登记时如果 sha256 不同，要在 1e 报告中说明） |
| 更新频率 | 不定期。提名截止日为每年 8 月 1 日，变更通过 Federal Register 公告发布（见入口页说明）。近几次：2022-01、2023-07、2024-07 |
| 我们用到的内容 | 表格三列：“Two-Digit Series”、“2020 CIP Code”、“CIP Code Title”；第 1 页关于 2 位系列的说明文字 |
| 已知限制 | ① 只是 CIP 清单，不是项目清单：某个项目是否 STEM 取决于学校给它定的 CIP（见 `03_stem_logic.md`）。② 标题换行、单词间距在 PDF 中不规则（见 `03_stem_logic.md` §3）。③ **ice.gov 拒绝非浏览器请求**：2026-09-30 用 curl 访问入口页和 PDF 均返回 HTTP 403。按 00 §6 不绕过，改为人工下载 |

### 1.1 Federal Register 最近一次更新公告（source = `federal_register`）

| 项 | 内容 |
|---|---|
| 标题 | Update to the Department of Homeland Security STEM Designated Degree Program List |
| 公布日期 / 引用 | 2024-07-23，**89 FR 59748**（pp. 59748–59750），FR Doc 2024-16127，Docket ICEB-2023-0018 |
| 页面 | https://www.federalregister.gov/documents/2024/07/23/2024-16127/update-to-the-department-of-homeland-security-stem-designated-degree-program-list |
| 下载（纯文本，入 manifest） | https://www.federalregister.gov/documents/full_text/text/2024/07/23/2024-16127.txt |
| 官方 PDF | https://www.govinfo.gov/content/pkg/FR-2024-07-23/pdf/2024-16127.pdf |
| 内容要点 | 生效日为 2024-07-23；新增 1 个 CIP：03.0204 Environmental/Natural Resource Economics；未删除任何代码。重申 14/26/27/40 四个核心系列按 2 位代码认定，“any new additions to those areas are automatically included” |
| 更早的公告 | 88 FR 44381（2023-07-12，FR Doc 2023-14807）；87 FR 3317（2022-01-21，FR Doc 2022-01188）；2016 年最终规则 81 FR 13040（FR Doc 2016-04828） |
| 核对方式 | 2026-09-30 查询 Federal Register API：检索词 “STEM Designated Degree Program List”，以及 2024-08-01 之后的 “STEM list”，均未发现晚于 2024-07-23 的清单更新公告 |

---

## 2. CIP 2020（source = `cip2020`）

| 项 | 内容 |
|---|---|
| 发布机构 | U.S. Department of Education / NCES |
| 官方入口页 | https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56 |
| 实际下载 URL | **https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv** |
| URL 说明 | 官方入口页上 CIP 2020 的下载按钮**只有 Excel 和 Word**（ASP.NET postback，没有静态链接），页面上没有直接链接这个 CSV。该 CSV 位于同一站点的 `Files/` 目录，与入口页上直接链接的 `Files/CIP2020_SOC2018_Crosswalk.xlsx` 同目录，2026-09-30 验证可下载。已确认采用 |
| 格式 | CSV（UTF-8），1,099,448 字节，HTTP Last-Modified: 2021-07-16。表头：`CIPFamily, CIPCode, Action, TextChange, CIPTitle, CIPDefinition, CrossReferences, Examples`。代码列采用 Excel 保护写法 `="01.0101"` |
| 更新频率 | 约每 10 年一版（1980/1985/1990/2000/2010/2020）。CIP 2020 自 2021-07 起未变 |
| 我们用到的字段 | `CIPCode`、`CIPTitle`、`CIPDefinition`、`Action` |
| 已知限制 | 文件同时包含 2 位、4 位、6 位代码，以及已迁出/删除的 2010 代码，需按下表过滤 |

**`Action` 取值与有效性规则（已用文件内容核对）：**

| Action | 行数 | 含义（依据 `CIPDefinition` 原文） | 是否为有效 CIP 2020 代码 |
|---|---|---|---|
| No substantive changes | 1994 | 沿用 | 是 |
| New | 544 | 2020 新增 | 是 |
| Moved to | 149 | 2020 中迁入此处的**新位置**（如 01.8105） | 是 |
| Moved from | 149 | 原 2010 代码，定义写着 “Moved from X to Y” | **否** |
| Deleted | 12 | 定义写着 “Deleted, Report under …” | **否** |

有效代码数：6 位 2,173 个，4 位 464 个，2 位 50 个。`Action` 出现上表以外的值时报错。

派生表 `data/ref/cip2020.csv`：`cip_code, level, title, definition, action`。其中 `level ∈ {2,4,6}`，只保留有效代码；`cip_code` 为 2 位写 `"NN"`，4 位写 `"NN.NN"`，6 位写 `"NN.NNNN"`。

---

## 3. IPEDS Completions（source = `ipeds_completions`）

| 项 | 内容 |
|---|---|
| 发布机构 | NCES，Integrated Postsecondary Education Data System |
| 官方入口页 | https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx （Survey = Completions） |
| 实际下载 URL | https://nces.ed.gov/ipeds/complete-data-files/C2024_A.zip （8,703,011 字节）；数据字典 https://nces.ed.gov/ipeds/complete-data-files/C2024_A_Dict.zip |
| 数据年份 | **C2024 = 2023-07-01 至 2024-06-30 授予的学位（2023-24 学年）** |
| 版本 | 使用 zip 内的 `c2024_a_rv.csv`，即**最终版（Final/revised release, September 2026）**。同一 zip 里的 `c2024_a.csv` 是临时版（Provisional, September 2025），不使用 |
| 为什么不用 2025 | `C2025_A.zip` 只含 `c2025_a.csv`（临时版，2026-07），没有 `_rv` 文件，因此不是最终版 |
| 格式 | CSV（UTF-8 with BOM），307,825 行 |
| 更新频率 | 每年一次。临时版在收集结束后约 7 个月发布，最终版约再晚一年 |
| 我们用到的字段 | `UNITID`、`CIPCODE`（`"NN.NNNN"`；`"99"` 为机构合计行）、`MAJORNUM`（1 = 第一专业，2 = 第二专业）、`AWLEVEL`、`CTOTALT`（总授予数）、`XCTOTALT`（插补标记）、`CNRALT`（U.S. Nonresident 授予数） |
| 硕士编码 | **`AWLEVEL = 7` → “Master's degree”**（出自 C2024_A_Dict 的 FrequenciesRV 工作表） |
| 已知限制 | ① zip 内修订版文件名的大小写因年份而异：2023 为 `c2023_a_RV.csv`，2024 为 `c2024_a_rv.csv`，按不区分大小写的 `_rv.csv` 匹配；找不到就报错，**不得回退到临时版**。② 有插补值（`XCTOTALT` 除 `R` = Reported 外还有 imputation 代码），保留该标记。③ IPEDS 按 6 位 CIP 汇总，**不等于“项目”**：一个 CIP 下可能有多个项目，一个项目也可能分报在多个 CIP 下 |

---

## 4. IPEDS 机构目录（source = `ipeds_hd`）

`candidates.csv` 需要的 `institution_name`、`state` 只在这个文件中有。年份与 C2024 对齐，使用 **HD2024**。

| 项 | 内容 |
|---|---|
| 发布机构 | NCES，IPEDS，Institutional Characteristics – Directory information |
| 官方入口页 | https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx （Survey = Institutional Characteristics） |
| 实际下载 URL | https://nces.ed.gov/ipeds/complete-data-files/HD2024.zip （1,033,802 字节，内含 `hd2024.csv`，UTF-8 with BOM，6,072 行） |
| 更新频率 | 每年一次 |
| 用到的字段 | `UNITID`、`INSTNM`、`STABBR` |
| 核对结果 | 目标 CIP 下的硕士行（C2024_A_RV）都能在 HD2024 中找到 UNITID，0 行未匹配 |
| 已知限制 | HD 描述的是 2024-25 年度的机构目录；个别机构可能在 2023-24 授予学位后改名或合并。以 HD2024 的名称为准 |

派生表：不单独输出，只在生成 `candidates*.csv` 时读取（在 `derived.csv` 中计入 `input_sha256`）。

---

## 5. College Scorecard – Field of Study（source = `scorecard_fos`）

| 项 | 内容 |
|---|---|
| 发布机构 | U.S. Department of Education |
| 官方入口页 | https://collegescorecard.ed.gov/data/ |
| 实际下载 URL（bulk） | https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_06102026.zip （17,188,590 字节；内含 `Most-Recent-Cohorts-Field-of-Study.csv`，227,980 行 × 178 列） |
| 数据发布日期 | **2026-06-10**（入口页及数据字典 README：“Released June 10, 2026”） |
| 官方文档 | 技术文档 https://collegescorecard.ed.gov/files/FieldOfStudyDataDocumentation.pdf （版本标注 “September 2025”）；数据字典 https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx （工作表 `FieldOfStudy_Data_Dictionary`、`FieldOfStudy_Cohort_Map`）。文档也作为原始文件登记进 manifest |
| API | 只作补充，Phase 1 不调用；如需调用，key 取自 `SCORECARD_API_KEY` |
| 更新频率 | 约每年一次 |

**必须核实的三项（均已从官方文档核实）：**

1. **CIP 粒度 = 4 位**。技术文档 “Defining field of study”：分析单位是 “unique combination of institutional identifiers, a four-digit CIP code, and a credential level”。文件中 `CIPCODE` 为 4 位数字字符串，如 `"3070"`（保留前导零，如 `"0110"`），归一化为 `"30.70"`。Cohort Map 注明 “Uses CIP2020 codes”。
2. **硕士 credential level：`CREDLEV = 5` → “Master's Degree”**（技术文档与数据字典一致）。
3. **收入与债务指标的样本范围：仅覆盖领取 Title IV 联邦学生资助的毕业生。**
   - Scorecard 技术文档 “Federally aided students” 一节：earnings 和 debt “describe only those students who received federal financial aid in the form of Title IV grants and loans”，并提醒不要假设这些数值能代表该领域的全体毕业生。
   - F-1 学生不具备联邦学生资助资格：studentaid.gov “Eligibility for Non-U.S. Citizens”（https://studentaid.gov/understand-aid/eligibility/requirements/non-us-citizens ，2026-09-30 查阅）的 “Other Documentation Not Listed Above” 一节列明，持 F-1、F-2、M-1 学生签证或 J-1、J-2 交流访问签证在美者**不是** eligible noncitizen，不能领取联邦学生资助。
   - → **因此本项目所有使用 Scorecard 收入/债务的地方都要标注：“不代表国际学生”。**

**我们用到的字段：** `UNITID, OPEID6, INSTNM, CONTROL, CIPCODE, CIPDESC, CREDLEV, CREDDESC, IPEDSCOUNT1, IPEDSCOUNT2, EARN_MDN_1YR, EARN_MDN_4YR, EARN_MDN_5YR, EARN_COUNT_WNE_1YR, DEBT_ALL_STGP_EVAL_MDN`。其他列在 Phase 1 不用。

**这些指标所属的年份（出自 `FieldOfStudy_Cohort_Map` 的 MostRecent 列）：**

| 字段 | 覆盖的队列 |
|---|---|
| CIPCODE / CREDLEV | AY2022-23（IPEDS DCY2023-24）或 NSLDS 合并队列 AY2021-22、AY2022-23 |
| IPEDSCOUNT1 / IPEDSCOUNT2 | AY2021-22 / AY2022-23 |
| EARN_MDN_1YR | AY2018-19、AY2019-20 合并队列，在 CY2020–21 测量，以 2022 年美元计 |
| EARN_MDN_4YR | AY2017-18、AY2018-19 合并队列，在 CY2022–23 测量，以 2024 年美元计 |
| EARN_MDN_5YR | AY2014-15、AY2015-16 合并队列，在 CY2020–21 测量，以 2022 年美元计 |
| DEBT_ALL_STGP_EVAL_MDN | NSLDS 合并队列 AY2018-19、AY2019-20 |

**缺失值处理：**

- 原始文件原样保留（`data/raw/` 不做任何改动）。
- 派生表中的数值列（`IPEDSCOUNT1, IPEDSCOUNT2, EARN_MDN_1YR, EARN_MDN_4YR, EARN_MDN_5YR, EARN_COUNT_WNE_1YR, DEBT_ALL_STGP_EVAL_MDN`）：

| 原始值 | 派生值 | `{列名}_status` |
|---|---|---|
| 数字（整数或小数） | 数值 | `reported` |
| `PS` | null（CSV 中为空） | `privacy_suppressed` |
| `NA` | null | `not_available` |
| 其他任何字符串（含空串） | — | **报错** |

**已知限制：**
- ① **4 位粒度无法区分 STEM 与非 STEM 的 6 位代码**：`30.70` 同时包含 30.7001（在 STEM 清单上）和 30.7099（不在）；`45.06` 是整个 Economics 系列，只有 45.0603 在清单上。所以 Scorecard 行**不能**用来判断 STEM，也不能等同于 45.0603。
- ② 收入队列（AY2014–2020）早于大多数 30.70/30.71 项目（CIP 2020 新代码）开设的时间，所以这两个系列在硕士层级上的收入覆盖率很低（见 `phase1_summary.md`）。
- ③ 机构按 OPEID6 汇总后，数值会在同一 OPEID6 下的各分校 UNITID 之间重复。
- ④ **缺失编码与文档不一致**：技术文档（“Privacy protection” 一节末尾）写的是隐私抑制用 “PrivacySuppressed” 表示；而 2026-06-10 的 CSV 中，上述数值列实际出现的非数值只有 `PS` 和 `NA`，没有 “PrivacySuppressed”。数据字典的 Glossary 中也没有找到 `PS`/`NA` 的定义。`PS` → `privacy_suppressed`、`NA` → `not_available` 是按字面含义做的对应。
- ⑤ 技术文档版本（2025-09）早于数据发布（2026-06），可能没有随新数据更新。

派生表 `data/ref/scorecard_fos_masters_target.csv`：保留 `CREDLEV == "5"` 且 4 位 CIP 属于目标 CIP 的 4 位父级的行（见 `04_candidate_selection.md` §6）。

- 所有行的 `CIPCODE` 都先经 `normalize_cip4` 处理，格式错误即报错；数值列只在保留下来的行上解析。
- 列顺序：`unitid, opeid6, instnm, control, cip4, cipdesc, credlev, creddesc, cip4_broader_than_target`，然后按 `ipedscount1, ipedscount2, earn_mdn_1yr, earn_mdn_4yr, earn_mdn_5yr, earn_count_wne_1yr, debt_all_stgp_eval_mdn` 的顺序，每个数值列后面紧跟它的 `_status` 列。`cip4`（`"NN.NN"`）取代原始的 `CIPCODE`。
- 标识列（`unitid, opeid6` 等）保持字符串，保留前导零。
- 行序：`unitid` 升序（按整数比较）→ `cip4` 升序。

---

## 6. Manifest 规范

### 6.1 原始文件：`data/manifest/manifest.csv`

每个原始文件、每次取得占一行（追加写入，不覆盖历史）：

| 列 | 规则 |
|---|---|
| `source` | 上面固定的 source 名之一 |
| `url` | 官方原始 URL（手工登记时也填官方链接，不填本地路径） |
| `method` | `http`（下载器自动下载）或 `manual`（人工下载后用 `register-manual` 登记） |
| `retrieved_at` | UTC ISO 8601，精确到秒，以 `Z` 结尾，如 `2026-09-30T18:22:05Z`。`http`：下载完成的时间；`manual`：人工下载的时间（由登记命令的参数提供，见 §7） |
| `sha256` | 文件内容的 sha256，64 位小写十六进制 |
| `bytes` | 文件字节数（整数） |
| `notes` | 自由文本；`manual` 行必须写明原因，如 `automated request returned HTTP 403` |

- 原始文件存放路径是确定的：`data/raw/<source>/<retrieved_at 的 UTC 日期 YYYY-MM-DD>/<URL 路径的最后一段>`。
- 同一 `sha256` 可以出现多次（重复下载），但同一 `(source, retrieved_at, url)` 不能重复。
- CSV 用 UTF-8（无 BOM）、`\n` 换行，逗号分隔，需要时加双引号。

### 6.2 派生表：`data/manifest/derived.csv`

| 列 | 规则 |
|---|---|
| `table` | 派生表文件名，如 `stem_list.csv` |
| `sha256` | 派生表文件的 sha256 |
| `rows` | 数据行数（不含表头） |
| `input_sha256` | 生成它所用的原始文件 sha256，多个时按字典序排列、用 `;` 连接；每一个都必须能在 `manifest.csv` 中找到 |
| `generated_at` | UTC ISO 8601 |

追溯规则（对应测试）：`data/ref/` 下每个 `.csv` 在 `derived.csv` 中都恰好有一行“当前”记录（同一 table 取最后一行），其 `sha256` 与文件实际内容一致，且每个 `input_sha256` 都在 `manifest.csv` 中。

---

## 7. 下载器与人工登记

### 7.1 下载器（method = `http`）

- User-Agent：`gradprog-refdata/<版本> (+mailto:<GRADPROG_CONTACT_EMAIL>)`；环境变量未设置则报错退出。
- 单线程；两次请求间隔 ≥ 3 秒；超时 120 秒；跟随重定向；非 2xx 状态码直接报错，不重试超过 2 次。
- 下载后校验文件类型：`.pdf` 必须以 `%PDF-` 开头，`.zip` 必须以 `PK\x03\x04` 开头。不符（例如拿到了 HTML 错误页）则删除文件并报错，不写 manifest。

### 7.2 人工登记（method = `manual`）

用于 ice.gov 的 STEM PDF。

```
uv run gradprog register-manual --source dhs_stem \
  --url https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf \
  --file ~/Downloads/stemList2024.pdf \
  --retrieved-at 2026-10-01T15:04:00Z \
  --notes "automated request returned HTTP 403"
```

- `--retrieved-at` 必填，填人工下载的时间（UTC）。只给日期时按 `YYYY-MM-DDT00:00:00Z` 记录，并在 notes 末尾追加 `time_unknown`。
- 做同样的文件类型校验（§7.1）。
- 把文件**复制**（不移动）到 `data/raw/<source>/<日期>/<URL 最后一段>`，计算 sha256 和字节数，追加一行 manifest，`method = manual`。
- 目标路径已存在且内容不同 → 报错，不覆盖。
