# 04 候选（学校 × CIP）清单

> 状态：v1.1（Phase 1b，已按 2026-09-30 的逐项答复修订）。本清单只是 Phase 2 人工挑选 100 个项目的**起点**，不是最终项目清单。
> 本文件中的数字是 2026-09-30 用 CIP 2020 CSV、2024 版 STEM 清单和 C2024_A_RV 做的预检结果，仅供参考。正式数字以 1d 生成的表和 1e 报告为准。

## 1. 目标 CIP 的定义

目标定义写在配置文件 `config/target_cip.csv` 中（提交进 git），列为 `pattern, kind, cip_group, label`：

| pattern | kind | cip_group | label |
|---|---|---|---|
| `30.70` | prefix | `ds` | Data Science 系列 |
| `30.71` | prefix | `analytics` | Data Analytics 系列 |
| `27.05` | prefix | `stats` | Statistics 系列 |
| `27.0601` | exact | `stats` | Applied Statistics, General |
| `52.13` | prefix | `mgmt_sci` | Management Sciences and Quantitative Methods 系列 |
| `45.0603` | exact | `econ` | Econometrics and Quantitative Economics |

- `cip_group` 的取值只能是 `ds / analytics / stats / mgmt_sci / econ`，固定排序也按这个顺序。
- `econ` 组目前只有 45.0603 一个代码（2026-09-30 确认单独成组）。

另有一份“必须存在”的清单，对应指令中点名的代码：`30.7102 Business Analytics`、`30.7103 Data Visualization`、`30.7104 Financial Analytics`、`45.0603`、`27.0601`。

### 1.1 展开规则

- `prefix`（格式 `NN.NN`）：展开为 CIP 2020 中所有以它开头的**有效 6 位代码**（有效性定义见 `01` §2）。
- `exact`（格式 `NN.NNNN`）：必须是有效的 CIP 2020 6 位代码。
- 同一个 6 位代码不能被展开到两个不同的 `cip_group`；出现就报错。

### 1.2 存在性检查（`check_targets`）

以下任一情况都要抛 `TargetCipError`，错误信息**一次性列出全部问题**，而不是遇到第一个就停：

- `exact` 代码不是有效的 CIP 2020 6 位代码；
- `prefix` 在 CIP 2020 中展开为 0 个代码；
- “必须存在”清单中的某个代码不在展开结果里；
- `pattern` 格式错误，`kind` 不在 {prefix, exact} 中，或 `cip_group` 不在允许的取值中；
- 同一代码属于多个 group。

### 1.3 预检结果（CIP 2020 与 2024 版 STEM 清单）

所有目标都存在，共 **17** 个 6 位代码：

| CIP | 标题 | cip_group | 在 STEM 清单上 |
|---|---|---|---|
| 30.7001 | Data Science, General. | ds | ✅ |
| **30.7099** | **Data Science, Other.** | ds | **❌ 不在清单上**（仍保留在范围内，`on_stem_list = false`） |
| 30.7101 | Data Analytics, General. | analytics | ✅ |
| 30.7102 | Business Analytics. | analytics | ✅ |
| 30.7103 | Data Visualization. | analytics | ✅ |
| 30.7104 | Financial Analytics. | analytics | ✅ |
| 30.7199 | Data Analytics, Other. | analytics | ✅ |
| 27.0501 | Statistics, General. | stats | ✅（系列 27） |
| 27.0502 | Mathematical Statistics and Probability. | stats | ✅（系列 27） |
| 27.0503 | Mathematics and Statistics. | stats | ✅（系列 27） |
| 27.0599 | Statistics, Other. | stats | ✅（系列 27） |
| 27.0601 | Applied Statistics, General. | stats | ✅（系列 27） |
| 52.1301 | Management Science. | mgmt_sci | ✅ |
| 52.1302 | Business Statistics. | mgmt_sci | ✅ |
| 52.1304 | Actuarial Science. | mgmt_sci | ✅ |
| 52.1399 | Management Sciences and Quantitative Methods, Other. | mgmt_sci | ✅ |
| 45.0603 | Econometrics and Quantitative Economics. | econ | ✅ |

注：CIP 2020 中没有 52.1303，这个缺号不是我们的遗漏。

## 2. 第二版候选（本版不加入）

依据：在 CIP 2020 的标题和定义中搜索 data / analytics / statistics / quantitative / informatics / machine learning 等关键词，再人工筛选。“硕士授予数”是 C2024_A_RV 中 AWLEVEL=7、第一专业的合计。**第一版不使用这些代码**，只作记录。

| CIP | 标题 | STEM 清单 | 有授予的机构数 | 硕士授予数 | 备注 |
|---|---|---|---|---|---|
| 26.1102 | Biostatistics. | ✅ | 76 | 1,075 | 统计方向，偏公共卫生 |
| 27.0305 | Financial Mathematics. | ✅ | 100 | 4,598 | 常见于金融工程/量化金融硕士 |
| 26.1311 | Epidemiology and Biostatistics. | ✅ | 8 | 91 | |
| 27.0304 | Computational and Applied Mathematics. | ✅ | 15 | 376 | |
| 11.0102 | Artificial Intelligence. | ✅ | 46 | 1,122 | |
| 11.0104 | Informatics. | ✅ | 30 | 1,358 | |
| 11.0802 | Data Modeling/Warehousing and Database Administration. | ✅ | 28 | 2,786 | |
| 11.0401 | Information Science/Studies. | ✅ | 139 | 10,359 | 范围较宽 |
| 14.3701 | Operations Research. | ✅（系列 14） | 23 | 1,047 | |
| 30.0801 | Mathematics and Computer Science. | ✅ | 14 | 375 | |
| 30.3001 | Computational Science. | ✅ | 44 | 1,682 | |
| 30.3901 | Economics and Computer Science. | ✅ | 4 | 42 | |
| 30.4901 | Mathematical Economics. | ✅ | 1 | 8 | |
| 45.0102 | Research Methodology and Quantitative Methods. | ✅ | 22 | 1,558 | |
| 42.2708 | Psychometrics and Quantitative Psychology. | ✅ | 4 | 42 | |
| 13.0603 | Educational Statistics and Research Methods. | ✅ | 21 | 164 | |
| 51.2706 | Medical Informatics. | ✅ | 105 | 2,506 | |
| 52.1201 | Management Information Systems, General. | ❌ | 44 | 1,162 | 部分商业分析项目用这个代码；不在清单上 |
| 11.0701 | Computer Science. | ✅ | 274 | 25,545 | 太宽，仅供参考 |

## 3. IPEDS 过滤规则（输入 C2024_A_RV）→ 参考表

1. 去掉 `CIPCODE == "99"`（机构合计行）；其余 `CIPCODE` 用 `normalize_cip6` 处理，失败则报错。
2. `AWLEVEL == "7"`（Master's degree，出处见 `01` §3）。
3. `CIPCODE ∈` 展开后的目标集合（§1）。
4. 按 `(UNITID, CIPCODE)` 汇总：
   - `completions_masters` = `MAJORNUM == "1"` 行的 `CTOTALT`（排序只用这一列）；
   - `completions_masters_second_major` = `MAJORNUM == "2"` 行的 `CTOTALT`，没有这一行时为 0；
   - `completions_masters_nonresident` = `MAJORNUM == "1"` 行的 `CNRALT`（只作参考，不参与排序）；
   - `imputation_flag` = `MAJORNUM == "1"` 行的 `XCTOTALT`。
   - 同一 `(UNITID, CIPCODE, MAJORNUM)` 出现多行时报错。
   - `MAJORNUM` 不在 {1, 2} 中时报错。
5. 去掉 `completions_masters == 0` 的行（包括没有第一专业行、只有第二专业行的情况）。
6. **参考表保留所有州和属地**（包括 PR）。

派生表 `data/ref/ipeds_masters_target_cip.csv`：`unitid, state, cip_code, cip_group, completions_masters, completions_masters_second_major, completions_masters_nonresident, imputation_flag, data_year`，按 `unitid, cip_code` 升序排列。`data_year = "2023-24"`。

## 4. 候选清单 `data/ref/candidates.csv`

输入是 §3 的参考表，再关联 `ipeds_hd`（`institution_name` = `INSTNM`，`state` = `STABBR`）、`cip2020`（`cip_title`），以及 `cip_on_stem_list`。

### 4.1 地域排除规则

- `candidates.csv` 和 `candidates_by_institution.csv` **只保留** `state` 属于 50 个州 + `DC` 的行。其他（`PR`，以及 `GU`、`VI`、`AS`、`MP`、`FM`、`MH`、`PW` 等属地和自由联系国代码）一律排除。
- 采用白名单（50 州 + DC），而不是只排除 PR 的黑名单，这样将来出现新属地也不会漏过。预检中受影响的只有 PR 的 2 行。
- 被排除的行数按 state 计数，写入 1e 报告。
- UNITID 在 HD 中找不到时报错，不能留空。

### 4.2 列

| 列 | 说明 |
|---|---|
| `cip_group` | `ds / analytics / stats / mgmt_sci / econ` |
| `rank_in_group` | 组内排名，从 1 开始，按 §4.3 的顺序逐行递增（并列也不共享名次） |
| `unitid` | IPEDS UNITID（字符串形式的整数） |
| `institution_name` | HD2024 的 `INSTNM` |
| `state` | HD2024 的 `STABBR` |
| `cip_code` | `"NN.NNNN"` |
| `cip_title` | CIP 2020 官方标题 |
| `on_stem_list` | `true` / `false`（由 `cip_on_stem_list` 得出） |
| `completions_masters` | 第一专业授予数 |
| `completions_masters_second_major` | 第二专业授予数，只作参考 |
| `completions_masters_nonresident` | 第一专业中 U.S. Nonresident 的授予数，只作参考，不参与排序 |
| `institution_target_cip_count` | 这所学校（排除后）有授予的目标 CIP 个数，跨所有组计 |
| `data_year` | `"2023-24"`（IPEDS C2024，final） |

### 4.3 排序（组内各自排序，不做跨组的总排名）

- 文件行序：`cip_group`（按 ds → analytics → stats → mgmt_sci → econ 的固定顺序）→ `completions_masters` 降序 → `unitid` 升序（按整数比较）→ `cip_code` 升序。
- `rank_in_group` 在每个 `cip_group` 内按上述顺序从 1 开始重新编号。
- 同一所学校在同一组有多个 CIP 时（如 30.7101 和 30.7102），各自占一行、各自排名。

### 4.4 `data/ref/candidates_by_institution.csv`

按学校汇总（同样排除 §4.1 的行），**不排名**：

`unitid, institution_name, state, institution_target_cip_count, cip_codes, completions_ds, completions_analytics, completions_stats, completions_mgmt_sci, completions_econ`

- `cip_codes`：该校有授予的目标 CIP，按字典序用 `;` 连接。
- `completions_<group>`：该校在该组的第一专业授予数合计，没有则为 0。
- 行序：`unitid` 升序（按整数比较）。不提供跨组总和，以免被当成总排名使用。

### 4.5 关于 52.13（mgmt_sci 组）

预检中 52.1301 Management Science 有 23,719 个硕士授予，52.1399 有 16,669 个，远高于 30.70（约 4,300）。**52.13 可能包含 STEM 化的 MBA 或管理类硕士，IPEDS 无法区分**（IPEDS 只到 6 位 CIP，不到项目）。这就是分组排序、不做总排名的原因。是否属于“数据科学/统计/商业分析”，留到 Phase 2 人工挑选时逐个项目判断。

预检规模（第一专业、授予数大于 0、排除前）：491 所机构、1,039 个（学校 × CIP）组合，`(unitid, cip_code)` 无重复。以上不含 27.0601，正式数字以 1d 为准。

## 5. 30.7099 的说明

30.7099 Data Science, Other. 不在 STEM 清单上，但仍在目标范围内（预检中只有 1 所机构，6 个授予）。它在 `candidates.csv` 中的 `on_stem_list = false`，不会被排除。

## 6. Scorecard 的对应关系

目标集合的 4 位父级：`30.70, 30.71, 27.05, 27.06, 52.13, 45.06`。`scorecard_fos_masters_target.csv` 保留 `CREDLEV == "5"`、且 `normalize_cip4(CIPCODE)` 属于这些父级的行。

- `cip4_broader_than_target`：该 4 位父级下，是否存在**不在目标集合中**的有效 CIP 2020 6 位代码。按 CIP 2020 计算，不写死。预期 `45.06` 为 true（Economics 系列中只有 45.0603 是目标），其余为 false。
- `30.70` 包括不在清单上的 30.7099，所以 Scorecard 行一律不用于 STEM 判断。
- 参考表保留所有州和属地；Scorecard 数据**不进入** `candidates.csv`，在 1e 报告中只报告覆盖率。
