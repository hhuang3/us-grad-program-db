# 08 字段抽取（Phase 4）

> 状态：draft v0.2（Phase 4a，2026-10-12）。只定义规则，本阶段不写代码、不调用 LLM。v0.2：§7.2 学期推算改为秋季、春季两个区间并按 `intake_terms` 确定季节；§12 的改动已确认并写入 02、05、06、07。
> 依据：`02_field_dictionary.md` v0.2、`05_data_model.md` v1.3、`06_source_registry.md`、`07_snapshots.md`。本文件需要 02、05、06、07 配合修改的地方集中列在 §12，已于 2026-10-12 经负责人确认并写入（02 v0.3、05 v1.4）。

本文件定义 05 的第二层 **observation**：从 snapshot 的规范化正文中抽取字段，写成 observation。observation 不直接成为 fact，进入 fact 必须经过人工审核（05 §1.3）。

## 1. 方法

- **不用 RAG**。整页规范化正文（07 §6）直接作为输入，逐页抽取，**每页一次 LLM 调用**（共用页面的例外见 §2.3）。
  - 理由：页面正文最长约 3.7 万字符（UChicago pg-0028），在模型上下文之内；截止日期表、托福要求常与上下文（项目名、学期、适用对象）相隔较远，切块检索容易丢失这些上下文。
- **结构化输出**：用 JSON schema 约束输出（字段、类型、枚举与 §4 一致）；输出不合 schema 记为 `extraction_failed`，不重试修补。
- **温度 0**。
- 每条结果记录 `model_name`、`prompt_version`、`schema_version`、`extracted_at`（05 §1.2）。提示词和 schema 放在仓库中（git），带版本号；模型名不写死在代码里，由配置给出。
- 提示词中放入：页面 URL、page_type、owner_level、所属项目名称（`programs.csv` 的 `program_name`、`degree_type`）、该页面对该项目的 `scope_note`（原样）、规范化正文。
- LLM 只依据正文作答，不使用页面以外的知识（例如“这所学校一般要求托福 100”）。

## 2. 输入范围

### 2.1 抽取哪些快照

- **首次抽取**（某页面从未被抽取过）：取该页面**最新的成功快照**抽取，与它的分类无关。成功 = 07 §7.1 的 `first_capture / unchanged / changed / suspected_redesign`。
- **之后**：只抽取“规范化正文相对于上次抽取所用快照有变化”的页面，即最新成功快照的 `norm_sha256` 与上次抽取所用快照的 `norm_sha256` 不同。不按 07 的分类判断（`unchanged` 只是相对上一次取得，不是相对上一次抽取）。
- **最新一次取得失败**（`blocked / unavailable / fetch_error`）：不调用 LLM；按 05 §4，为该页面关联的每个 `(program_id, field)` 写一条 `value_status = page_unavailable` 的 observation，关联那条失败的 snapshot。上一次成功抽取的 observation 保留不动。
- 同一 `normalizer_version` 下比较 `norm_sha256`；规范化版本变化的处理见 §11。

### 2.2 哪些页面

- `pages.csv` 中 `url_status = confirmed`，且至少关联一个 `status = selected` 项目的页面。
- `url_status = retired` 的页面**不抽取**（06 §3.2）；`proposed` 的页面不抽取。
- 自动取得和人工取得的页面同样处理。

### 2.3 共用页面与 `scope_note`

- 一个页面关联多个项目时（例如研究生院统一的语言要求页），**默认一页一次调用**，抽取结果分别挂到每个关联项目上，各写一份 observation（05 §3：observation 属于一个 `(snapshot, program)` 组合）。
- 该页面在各项目的 program_pages 记录中，`scope_note` **不完全相同**（含一个为空、一个不为空）时，改为按“页面 × 项目”分别调用，每次只放入该项目的 `scope_note`。
- `scope_note` 原样放进提示词；LLM 必须按它取舍（例如 pg-0061：只取全日制面授版，不采用其他项目的 Admissions 与 Application Deadlines 区块）。

## 3. 字段范围（v1）

v1 只抽取下列字段。字段定义以 02 为准，新增和修改见 §12。

| 类别 | 字段 | 说明 |
|---|---|---|
| 截止日期 | 子表 `deadline`：`term`、`round_name`、`deadline_type`（新增）、`deadline_date`、`deadline_tz`、`applicant_scope`、`is_rolling` | 每个轮次 × 类型一行 |
| 英语 | `toefl_min_legacy`、`toefl_min_new_scale`、`toefl_scale_on_page`、`ielts_min_overall` | 分制规则见 §9 |
| 考试 | `gre_policy`、`gmat_policy` | |
| 学费 | `tuition_basis`、`tuition_amount_usd`、`tuition_year`，以及换算用的 `credits_required` | 见 §3.1 |
| 项目时长 | `length_months_min`、`length_months_max` | |
| STEM | `cip_code`、`stem_claim_on_page`（新增） | `cip_source` 与 `stem_status` 由代码推导，见 §3.2 |
| 申请费 | `app_fee_usd` | |

### 3.1 学费：保留原始口径，换算另存

- `tuition_basis` 取值改为 `per_credit / per_term / per_year / program_total`（新增 `per_year`）。
- `tuition_amount_usd` 存**页面原始口径下的原始金额**，与 `tuition_basis` 配套；页面写的是什么口径就存什么口径，LLM 不换算。
- 只记国际学生适用的金额（公立校即州外学费，02 §4）。学费以外的杂费不并入；页面只给“学费 + 杂费”合计时照原样存，并在 observation 中标 `includes_fees`（§4）。
- **换算由代码完成，另存为 `tuition_program_total_usd_est`**（新增派生字段，不是 LLM 输出），同时记录换算方法和用到的输入：
  - `per_credit` × `credits_required`；
  - `per_term` × 学期数（由 `length_months_*` 推得的学期数由审核人确认，代码不猜）；
  - `per_year` × 年数（同上）；
  - `program_total` 原样。
  - 缺少任何输入就不换算（值为空），不进审核。
- `credits_required` 只为换算而抽取；它在 02 中已有定义。

### 3.2 STEM

- LLM 抽取：页面上写明的 `cip_code`（原样，6 位 CIP），以及页面是否声称本项目是 STEM（`stem_claim_on_page`：yes / no；页面没提就是 `not_mentioned`）。另输出 CIP 出现的语境（STEM 项目列表、项目介绍、I-20 说明、其他）。
- 代码推导：
  - `cip_source`：语境为 STEM 项目列表或页面 `page_type = isso_stem_list` → `school_stem_page`；I-20 说明 → `i20_statement`；其他学校页面 → `program_page`；页面没有 CIP 而用 IPEDS 推断 → `ipeds_inferred`。
  - `stem_status`：调用 03 §5.2 `derive_stem_status`，不让 LLM 判断。
- 页面只写“STEM-designated”而没有 CIP 时，按 03 `stem_status = unknown`（没有 CIP 信息），`stem_claim_on_page = yes` 另行保存，供审核和发布参考。
- 测试用例：JHU MA Economics pg-0045 写明 CIP 45.0603 → `cip_source = program_page` → `confirmed_by_school`（P2 报告 §6.1）。

### 3.3 推迟的字段及理由

| 字段 | 推迟理由 |
|---|---|
| `toefl_section_mins`、`ielts_band_min`、`duolingo_min` | 单项要求写法差异大（按项、按总分档、按申请类别），同一页面常有几套标准；先做总分 |
| `english_waiver`、`gre_notes`、`fee_waiver_conditions` | 自由文本摘要，难以客观评测准确率 |
| `rec_letters_required`、`documents_required`、`prerequisites` | 页面写法松散（“two or three letters”“recommended”），判断标准需另行定义 |
| `interview`、`funding`、`three_year_bachelor`、`min_gpa`、`fee_waiver` | 大量学校不写，`not_mentioned` 与抽取失败难以区分；先用 v1 字段测出漏抽率再扩展 |
| `start_terms`、`delivery_mode`、`degree_type` 等主表字段 | 已在 P2 登记表中由负责人确认，不重复抽取 |
| `f1_eligible`（P2 报告 §6.1 提议） | 试点只有 1 例（UW-Madison MSQE），先积累主批次实例再定义 |

## 4. 输出格式

LLM 对每个页面输出一个 JSON 对象：

- **页面级**：`terms_mentioned`——页面上出现的所有学期写法，按原文列出（如 `"Fall 2027"`、`"fall semester"`、`"2026 applications"`）；页面没有任何学期写法时为空列表。
- **字段级**（每个 v1 字段一项；截止日期为数组，每个轮次 × 类型一项）：

| 键 | 含义 |
|---|---|
| `value` | 字段值，类型与枚举按 02（§12 修订后）；`value_status ≠ found` 时为 null |
| `value_status` | `found / not_mentioned`（LLM 只输出这两种；`extraction_failed`、`page_unavailable` 由代码写） |
| `evidence_text` | 支持该值的原文片段，≤ 200 字符，从正文中原样复制 |
| `term_as_written` | 该条目所对应学期在页面上的原文写法；页面没写就为 null |
| `confidence` | 0–1 |
| 附加标记 | `includes_fees`（学费含杂费）；其他标记见 §8 |

- 代码补全每条 observation 的 `evidence_url`（快照的 `final_url`）、`snapshot_id`、`retrieved_at`、`program_id`、`model_name`、`prompt_version`、`schema_version`、`extracted_at`，以及 §7 得出的 `valid_for_term` 和 `term_basis`（§12）。
- 同一字段在页面上出现多个不同的值（例如托福 90 和 95）时，LLM 每个值输出一项，不自行选择；代码按 §8.3 处理。
- **`confidence` 只用于排序和触发审核**（§10），不作为准确率指标，也不对外发布。
- **存储**：observation 含 `evidence_text`（页面原文），按 00 §2 只保存在本地，不进 git，目录 `data/extraction/`（加入 .gitignore）。git 中只放提示词、schema、配置，以及不含原文的汇总统计。

## 5. 分工：LLM 只记录观察，判断交给代码

| 由 LLM 输出 | 由代码完成（规则写在本文件） |
|---|---|
| 页面上写了什么值、原文证据、该条目对应的学期原文、页面出现的所有学期写法 | `valid_for_term` 的换算与推算（§7） |
| CIP 原文与出现语境、是否声称 STEM | 过期判断（§7.3） |
| 同一字段的多个不同值（全部列出） | 页面内与跨页面冲突判断（§8） |
| | `cip_source`、`stem_status` 推导（§3.2）；学费换算（§3.1） |
| | 证据校验（§6）、审核分流（§10） |

LLM 不做推理：不推算学期、不判断是否过期、不比较页面、不换算金额和分制。

## 6. 证据校验

每条 `value_status = found` 的结果，写入前依次检查，任何一项不通过：该条作废，记为 `value_status = extraction_failed`（值为空），并进入审核（§10）。原始输出另存，供审核查看。

1. **逐字出现**：`evidence_text` 与规范化正文各自做空白规范化（连续空白合并为一个空格、去掉首尾空白）后，`evidence_text` 必须是正文的子串。不做大小写或标点的模糊匹配。
2. **长度**：≤ 200 字符。
3. **值与证据一致**：数值、日期、金额必须能在 `evidence_text` 中找到对应写法（例如 `toefl_min_legacy = 100` 时证据中有 “100”；日期按常见写法比对：`October 7, 2026`、`Oct. 7, 2026`、`10/07/2026`、`2026-10-07`）。枚举字段（`gre_policy` 等）不做此项。
4. **类型与范围**：符合 02 的类型和取值范围（例如 `toefl_min_legacy` 为 0–120 的整数，`toefl_min_new_scale` 为 1.0–6.0、步长 0.5，`ielts_min_overall` 为 0–9、步长 0.5）。

## 7. `valid_for_term` 的判断

按**每一条 observation** 判断，不按页面判断（P2 报告 §6.2.1）。`valid_for_term` 的格式见 05 §2（`"Fall 2027"` 或 `term_unknown`）。代码记录判断依据 `term_basis`：`stated`（页面写明）/ `inferred_from_date`（由日期推算）/ `recurring_no_year`（日期没写年份，按每年固定日期推算，§7.2）/ `unknown`。

### 7.1 页面写明了学期（`term_as_written` 非空）

- 能确定季节和年份的写法（`Fall 2027`、`Fall semester 2027`、`2027 fall entry` 等）→ 换算为标准格式，`term_basis = stated`。
- 只写季节、没写年份（如 “for the fall semester”）→ 季节按写明的，年份按 §7.2 的区间由日期推算，`term_basis = inferred_from_date`。季节为夏季，或没有日期可用时 → `term_unknown`，进入审核。
- 写法含糊、无法确定是入学季还是申请年份（如 Columbia DS 的 “GRE optional for the 2026 applications”）→ `term_unknown`。
- 学年写法（如 `2026-27`、`AY 2026-2027`）→ 秋季入学项目换算为该学年的秋季（`2026-27` → `Fall 2026`），`term_basis = inferred_from_date`。

### 7.2 由日期推算学期

**推算区间**（2026-10-12 修订：试点中有春季入学的项目，“只有秋季入学”的前提不成立）：

| 季节 | 截止日期落在 | 推算为 |
|---|---|---|
| 秋季 | Y−1 年 9 月 1 日至 Y 年 8 月 31 日 | `Fall Y` |
| 春季 | Y−1 年 3 月 1 日至 Y 年 2 月最后一天 | `Spring Y` |
| 夏季 | 不定义区间 | 不推算 |

- 例：秋季 2026-08-15 → Fall 2026；秋季 2026-10-07 → Fall 2027；春季 2026-11-09 → Spring 2027；春季 2026-02-15 → Spring 2026。
- 两个区间有重叠（例如 10 月的截止日期既可能是 Fall Y+1 的，也可能是 Spring Y+1 的），所以**必须先确定季节**，再按该季节的区间推算年份。季节的来源只有两个：
  1. 页面写明了季节（§7.1 第二条）；
  2. 页面没写季节，而该项目**只有一个入学季**（登记表 `intake_terms` 只有一个值，见 06）→ 按该季节推算。
- 季节和年份都没写、而项目**有多个入学季** → `term_unknown`，进入审核，不按日期猜季节。
- 季节为夏季、没写年份 → `term_unknown`，进入审核。
- 由完整日期推算出的学期 `term_basis = inferred_from_date`，进入审核（§10 第 2 条）；没写年份的按下一条处理。
- 没有日期的字段（托福、学费等）且页面没有任何学期写法 → `term_unknown`。
- **截止日期没写年份**（如 “January 2”“MS Spring Admission – September 15”）→ 按**每年固定日期**处理（2026-10-12 确认）：
  - 年份推算为该月日在快照 `retrieved_at` 之后（含当天）的**下一次出现**。例：2026-10-11 取得、页面写 “January 2” → 2027-01-02。
  - 再按上面的季节区间确定学期；季节的确定方式不变。
  - `deadline_date` 填推算出的完整日期，`term_basis = recurring_no_year`；月日原文仍在 `evidence_text` 中。
  - **不因没写年份而进审核**；只有季节无法确定（季节没写、且项目有多个入学季）时才进审核。
  - 理由：这类写法通常表示每年固定的截止日期，试点中有 4 个项目使用（UW–Madison、UIUC、JHU Krieger、Rochester）；如果页面已经过期、日期实际已改，风险由每年 8 月 15 日的全量重新取得和重抽兜底（§11）。
- `intake_terms` 由负责人在登记表中维护，不由 LLM 判断。

**试点 21 个项目的 `intake_terms`**（2026-10-12 按已存快照正文检索，结果写入 programs.csv；“未核实”的在 `selection_note` 中注明，主批次登记时由负责人核对）：

| intake_terms | 项目 | 依据（页面） |
|---|---|---|
| `fall;spring;summer` | unt-ms-datascience | pg-0008：Spring 2027、Summer 2027（夏季仅限美国本土申请者）、Fall 2027 同时开放 |
| `fall;spring;summer` | utd-ms-businessanalytics | pg-0015：秋、春、夏三季入学 |
| `fall;spring;summer` | uconn-ms-businessanalyticsprojectmanagement | pg-0021、pg-0023（春季仅 Hartford；签证学生只在秋季、春季入学） |
| `fall;spring` | uwmadison-ms-statisticsdatascience | pg-0032：有春季入学的申请截止日期 |
| `fall;spring` | uiuc-ms-statistics | pg-0039：MS Spring Admission 截止日期 |
| `fall;spring` | rochester-ms-businessanalytics | pg-0058、pg-0059、pg-0060：MS BA 接受 1 月春季入学 |
| `fall` | nyu-ms-datascience | pg-0004：明确没有春季入学 |
| `fall` | uwmadison-ms-statistics | pg-0031、pg-0033：“no spring admissions” |
| `fall` | jhu-ma-economics | pg-0045 明确只招秋季。pg-0046（文理学院总表）的春季、夏季截止日期属于 Cognitive Science，不是本项目；本项目在总表中只有一个 MA 截止日期（3 月 1 日），与项目页的“3 月 1 日优先、5 月 1 日最终”不同（§8.2 的实例） |
| `fall` | washu-ms-businessanalytics | pg-0065 写明 Start: Fall。pg-0068 的 “starting in Spring 2026” 所在表格标题为 Academic Year 2026-27，表下注 “Posted Spring 2026”，应指收费标准的发布时间，不是入学季 |
| `fall`（未核实） | columbia-ms-datascience、uva-ms-datascience、utd-ms-businessanalyticscohort、bu-ms-businessanalytics、uchicago-ms-applieddatascience、uwmadison-ms-quantitativeeconomics、usc-ms-appliedeconomicseconometrics、ucla-other-quantitativeeconomics、duke-other-mqmbusinessanalytics、jhu-ms-businessanalyticsai、columbia-ma-statistics | 已存页面没有春季、夏季入学的写法；未提及不等于没有。其中 uva（pg-0011 “requiring a fall start for all students”）、columbia-ma-statistics（pg-0037 只有 Fall Admission 截止日期）、ucla（pg-0049 只有 Fall 2027）、jhu-ms-businessanalyticsai（pg-0061 “Fall Term”）有支持秋季的写法 |

columbia-ma-statistics 最初被误判为有春季入学：pg-0053 是 GSAS 所有项目共用的截止日期表，“Spring Admission Deadline” 是表头，Statistics MA 一行的春季栏为空。

### 7.3 过期

- 截止日期早于该快照的 `retrieved_at`（按日期比较）→ observation 标 `stale`。
- 过期的条目**仍记在它本来的学期下**，不改成下一季，也不因过期而丢弃。
- 代码为某个目标学期（例如 Fall 2027）汇总时，只使用 `valid_for_term` 等于该学期的 observation；`stale` 的条目不得被当作下一季的数据。
- 一个项目在目标学期下没有任何未过期的截止日期，而存在上一季的过期截止日期时，进入审核（页面可能尚未更新）。

### 7.4 同一页面出现多个学期

- 每条 observation 各自判断，同一页面上可以同时有 Fall 2026 和 Fall 2027 的 observation（05 §2：不同 term 的 fact 并存）。
- `terms_mentioned` 中有两个或以上不同学期、而某条 observation 的 `term_as_written` 为空时，该条不按“页面唯一学期”套用，按 §7.2 处理。

### 7.5 测试用例

| 用例 | 期望 |
|---|---|
| pg-0007（UNT MSDS 首页，2026-10 快照）：“August 15, 2026 … for the fall semester” | 季节写明、年份由日期推算：`Fall 2026`，`term_basis = inferred_from_date`，`stale`。不得作为 Fall 2027 的截止日期 |
| pg-0055（Duke）：签证截止日期表为 2025 年日期 | `deadline_type = international_docs`；按 §7.2 区间推算为 Fall 2025，`stale`。不得作为 Fall 2027 的签证截止日期 |
| Duke 倒计时区块（pg-0055、pg-0056）：轮次名、起止日期、剩余时间 | 抽取轮次名和截止日期（与 pg-0056 的轮次表一致）；剩余时间文字（“N days N hours” 等）不是任何字段的值，不得出现在 evidence 以外的地方 |
| UCLA MQE pg-0048、pg-0049（2026-10-11 快照）：Fall 2026 已关闭、Fall 2027 开放 | Fall 2027 的截止日期 `stated`；关于 Fall 2026 的内容不进入 Fall 2027 |
| Columbia DS：“GRE optional for the 2026 applications” | `term_unknown`，进入审核 |
| UNT pg-0008（10-07 快照）：Spring 2027 截止日期（国际申请者 2026-11-09） | `Spring 2027`，`term_basis = stated`；与春季区间推算结果一致。不得因项目有秋季入学而记为 Fall 2027 |
| UW–Madison MS Statistics pg-0031（10-11 快照，`intake_terms = fall`）：“January 2 for a fall term start”（无年份） | 每年固定日期：2027-01-02，`Fall 2027`，`term_basis = recurring_no_year`，不进审核 |
| UIUC pg-0039（10-04 快照）：“MS Spring Admission – September 15”（无年份） | 每年固定日期：取得日 2026-10-04 之后的下一次 9 月 15 日是 2027-09-15，按春季区间为 `Spring 2028`，`term_basis = recurring_no_year`，不进审核。Spring 2027 的截止日期（2026-09-15）在取得时已过，不得据此记为 Spring 2027 |
| WashU pg-0065 “October 2026 Start”（上一季延期入学） | 不得记为 Fall 2027 |
| WashU pg-0068：“starting in Spring 2026”（收费标准发布时间） | 学费 `tuition_year = 2026-27`；不得据此产生 Spring 2026 的入学季 |

## 8. 冲突处理

所有冲突都**不自动选择**：各方 observation 都保留，标出冲突类型，进入审核；审核时给出默认建议。冲突标记写在 observation 上（`conflict_type`，§12）。

### 8.1 研究生院页与系页（项目页）数值不同

- 层级由 `pages.owner_level` 给出：`program` > `department` > `graduate_school` > `university`（越具体越优先）。
- 审核默认建议：采用更具体层级的值。
- 例外一：更具体层级的页面写的是“按研究生院要求”（没有自己的数值）→ 采用研究生院的值。
- 例外二：**研究生院要求视为下限**。项目页（或系页）的数值**低于**研究生院下限时（例如项目页托福 79、研究生院 80），不自动采用，进入审核，冲突类型 `below_graduate_school_minimum`。“低于”按字段方向判断：最低分类字段（托福、雅思）数值更低即为低于；`gre_policy` 等枚举字段不做下限比较。
- 冲突类型：`level_mismatch`、`below_graduate_school_minimum`。

### 8.2 同一项目的截止日期有多个来源

- 截止日期按 `(valid_for_term, deadline_type, applicant_scope, round_name)` 分组；不同组并存，不算冲突（例如研究生院的“提前截止”与项目的“Round 1”）。
- 同一组内日期不同才算冲突，冲突类型 `deadline_mismatch`；审核默认建议按 §8.1 的层级。
- 案例：UTD 商学院页有一套截止日期，研究生院页另有“提前截止”和“常规截止”两张表（P2 报告 §6.2.3）。

### 8.3 同一页面内数值矛盾

- 同一页面、同一字段、同一学期出现两个及以上不同的值 → 冲突类型 `in_page_contradiction`，全部保留，进入审核。
- 案例：
  - BU：同一页上托福写了 90 和 95；首页列 6 轮截止、申请页列 5 轮（后者为跨页面，按 §8.2）；学制写法不一致（P2 报告 §6.2.2）。
  - WashU pg-0066：新制托福写法自相矛盾（§9）。

### 8.4 跨项目内容污染

- **定义**：登记给某项目的页面中，混入了其他项目（其他学位、其他版本）的申请内容。这是已知的一类问题，作为专门的冲突类型 `cross_program_contamination` 处理。
- **案例**：
  - **JHU Carey pg-0061**（`jhu-ms-businessanalyticsai`）：P2 核对时，页面的 Admissions 与 Application Deadlines 区块是 MBA/BS in Engineering 双学位的内容，且为 Fall 2026 旧数据，与 How to apply 页（pg-0062）矛盾（GMAT/GRE 一个说必需、一个说可选）。2026-10 `/full-time` 并入项目总页，P4 抽取时需确认这些内容是否已修正。scope_note 已写明不采用。
  - **BU pg-0026**（`bu-ms-businessanalytics`）：liberal arts 申请通道区块写明属于 MSBA，但“如何申请”一句指向 MiM 项目，疑似从 MiM 页面复制；该区块在 2026-10-11 的快照中已被删除。
- **检测信号**（任一命中即标记，进入审核，不自动采用该条）：
  1. LLM 在该条目的 `evidence_text` 或其所在区块中看到其他项目或学位的名称——提示词要求 LLM 对每条输出 `other_program_mentioned`（页面原文中的其他项目名，或 null），只记录、不判断；
  2. 该条目落在 `scope_note` 声明不采用的区块（LLM 依 scope_note 输出 `excluded_by_scope_note`，代码仍保留该条以备审核）；
  3. 与同一项目其他页面的同一字段、同一学期的值不同（与 §8.1、§8.2 同时成立时，两个冲突类型都标）。
- 审核默认建议：采用没有污染信号的页面的值；所有页面都有污染信号时，不给建议。

### 8.5 面授版与线上版写在同一页面

- 按 `scope_note` 取舍（§2.3）。scope_note 未说明、而 LLM 报告同一字段有面授、线上两个值时，按 §8.3 处理。
- 案例：UChicago（面授 6 轮截止、线上 1 轮）；JHU Carey pg-0061（同时介绍在职线上版）。

## 9. TOEFL 新旧分制

- 旧制：总分 0–120 的整数 → `toefl_min_legacy`。新制（2026-01-21 起）：1.0–6.0、步长 0.5 → `toefl_min_new_scale`（02 §2）。
- 由代码识别分制，LLM 只抽数字和证据中的原文：
  1. 证据中写明分制（“new scale”“new TOEFL”“band”“old scale”“legacy”“iBT total”等）→ 按写明的；
  2. 没写明时按数值：1.0–6.0 之间且为 0.5 的倍数 → 新制；7–120 的整数 → 旧制；
  3. 都不满足（例如 6.5、0）→ `extraction_failed`，进入审核。
- 同一要求两种分制都写了（UConn：“79（旧制）或 4.5（新制）”）→ 两个字段各存一条，`toefl_scale_on_page = both`。
- 写明的分制与数值范围不符，或同一分制内自相矛盾（WashU pg-0066：“5.0 overall (new scale) OR 4.5 ≥ 90 overall (old scale)”）→ `in_page_contradiction`，进入审核。
- `toefl_scale_on_page`：页面只出现旧制 → `legacy`，只出现新制 → `new`，两者都有 → `both`。

## 10. 必须进入人工审核的情况

| # | 条件 |
|---|---|
| 1 | `valid_for_term = term_unknown` |
| 2 | `term_basis = inferred_from_date`（由完整日期推算出的学期；`recurring_no_year` 不在此列） |
| 3 | 证据校验不通过（§6），或值不合类型、范围 |
| 4 | 任何冲突类型（§8）：`level_mismatch`、`below_graduate_school_minimum`、`deadline_mismatch`、`in_page_contradiction`、`cross_program_contamination` |
| 5 | 目标学期没有未过期的截止日期、只有上一季的过期截止日期（§7.3） |
| 6 | `confidence` 低于阈值（阈值用 09 标准答案集定出，确定前默认 0.7） |
| 7 | 新 observation 的值与 `review_status = corrected` 的 fact 不同（05 §1.3） |
| 8 | 来源快照分类为 `suspected_redesign` |
| 9 | 季节和年份都没写、且项目有多个入学季；或季节为夏季、没写年份（§7.2） |
| 10 | TOEFL 分制无法识别（§9） |
| 11 | 页面受众存疑：LLM 报告页面是给在读学生或其他项目的（P2 报告 §6.2.5，例如 Columbia `/ma-student-faqs/`） |

不进入审核的 observation 仍然不会自动成为 fact（05 §1.3）；“进入审核”指在审核队列中优先列出并标明原因。

## 11. 重新抽取的触发条件

| 触发 | 动作 |
|---|---|
| 页面变化：最新成功快照的 `norm_sha256` ≠ 上次抽取所用快照 | 对该页面关联的所有项目重抽 |
| 规范化版本变化（07 `NORMALIZER_VERSION` 升级并重新规范化） | 新版本规范化正文与旧版本不同的页面重抽；相同的不重抽 |
| `prompt_version` 升级 | 全量重抽 |
| `schema_version` 升级（含字段定义变化：02 中 v1 字段的类型、枚举、含义改变） | 全量重抽 |
| 新申请季：每年 8 月 15 日（05 §5） | 全量重新取得 + 全量重抽 |

- 重抽只产生新的 observation，不直接改 fact（05 §5）。
- `model_name` 变化视同 `prompt_version` 升级。

## 12. 对其他 spec 的改动（2026-10-12 已确认并写入）

以下改动已写入对应文件；涉及代码的（06 `intake_terms`）按 spec → 测试 → 代码的顺序同步。

### 12.1 02_field_dictionary.md（v0.2 → v0.3）

1. 新增 `stem_claim_on_page`（§1）：页面是否声称本项目是 STEM，enum `yes / no`。
2. `tuition_basis` 取值加 `per_year`（§4）；`tuition_amount_usd` 说明改为“页面原始口径下的金额”；新增派生字段 `tuition_program_total_usd_est`（代码换算，记录换算方法）。
3. 截止日期子表（§5）新增 `deadline_type`：`application / international_docs / deposit / decision_release / other`。
4. 元数据（§6）新增：`term_as_written`（学期原文）、`term_basis`（`stated / inferred_from_date / unknown`）、`stale`（bool）、`conflict_type`（§8 的五种，可多值）、`includes_fees`（学费含杂费）。
5. §7 待定事项：“研究生院页与系页冲突的优先规则”关闭，指向 08 §8.1。

### 12.2 05_data_model.md（v1.3 → v1.4）

1. §1 observation 关键字段补 `term_as_written`、`term_basis`、`stale`、`conflict_type`。
2. §5 重跑规则补两项：规范化版本变化（只重抽正文变化的页面）、字段定义变化（随 `schema_version`）；`model_name` 变化视同 `prompt_version` 升级。
3. §5 新增：首次抽取取最新成功快照，与分类无关；之后按 `norm_sha256` 与上次抽取比较（08 §2.1）。
4. 新增：页面级抽取记录 `terms_mentioned`（每次调用一条，不是 observation）。

### 12.3 06_source_registry.md

1. programs.csv 新增列 `intake_terms`（在 `fetch_method` 之后）：`fall / spring / summer` 中的一个或多个，分号分隔、按 fall、spring、summer 的顺序、不重复；`status = selected` 时必填，其他状态可空。`validate` 检查漏填和取值。用途：08 §7.2 确定推算学期用的季节。试点 21 个项目的值见 08 §7.2 的表。

### 12.4 07_snapshots.md

1. 开头说明“P4 只处理分类为 `first_capture` 或 `changed` 的快照”改为“P4 的输入规则见 08 §2”。
2. §7.1 表格“后续处理”一列中的“交给 P4”改为“可被 P4 抽取（见 08 §2）”，`unchanged` 与 `suspected_redesign` 同样可能被抽取。

### 12.5 .gitignore

1. 新增 `data/extraction/`（observation 含原文）与 `data/gold/local/`（标准答案集的带原文副本，09 §4）。

## 13. 留给 P5 的事项

- `term_basis = recurring_no_year` 的截止日期（页面没写年份、按每年固定日期推算，§7.2），对用户展示时要标明“按往年推算”，与页面写明年份的日期区分显示（2026-10-12 负责人要求）。
