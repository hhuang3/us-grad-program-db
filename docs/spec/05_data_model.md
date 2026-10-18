# 05 数据模型（设计，Phase 1 不实现）

> 状态：v1.4（Phase 4a，2026-10-12；2026-10-18 补充：§4 新增 `referenced_elsewhere`、`mentioned_without_value`。observation 层与重抽规则按 `08_extraction.md` 补充）。v1.3：snapshot 层以 `07_snapshots.md` 为准。Phase 2 起所有阶段以本文件为准。字段取值见 `02_field_dictionary.md`（draft v0.2），STEM 规则见 `03_stem_logic.md`。

## 1. 四层数据状态

四层**分开存储、只追加、不互相覆盖**。下层永远不因上层的变化而改写。

| 层 | 是什么 | 主键 | 关键字段 | 谁写入 |
|---|---|---|---|---|
| `snapshot` | 一次原始取得（自动抓取或人工保存） | `snapshot_id` | **以 `07_snapshots.md` §4.2 为准**：`page_id, method, retrieved_at, requested_url, final_url, http_status, content_type, raw_sha256, normalizer_version, norm_sha256, classification, prev_snapshot_id` 等 | 抓取器 / 人工登记 |
| `observation` | 一次抽取的结果（每个字段一行） | `observation_id` | `snapshot_id, program_id, field, value, value_status, reference_target, valid_for_term, term_as_written, term_basis, stale, conflict_type, evidence_text, confidence, model_name, prompt_version, schema_version, extracted_at`（抽取规则见 `08_extraction.md`） | 抽取器 |
| `fact` | 经人工审核确认的当前值 | `(program_id, field, valid_for_term)` 的当前版本 + `fact_version` | `value, value_status, source_observation_id, review_status, reviewer, reviewed_at, evidence_url` | 人工审核 |
| `release` | 对外发布的数据集版本 | `release_id`（如 `v2027.1`） | `released_at, version, fact 版本集合` | 发布流程 |

### 1.1 snapshot

- `normalized_text`：去掉脚本、样式、导航等噪声后的正文，用于变化检测。只在内部保存，不发布（见 00 §2）。
- 取得结果由 07 §7.1 的 `classification` 表示（`first_capture / unchanged / changed / suspected_redesign / unavailable / blocked / fetch_error`），取代原先的 `fetch_status`。页面不可访问时也要写一条 snapshot，记录失败本身。
- 正文规范化与变化检测的规则见 07 §6–§7；规范化正文和原始文件只保存在本地，不进 git。
- 变化检测以 `normalized_text_sha256`（07 中的 `norm_sha256`）为准，不用原始 HTML 的 hash（页面上的时间戳、广告会让 HTML 每次都不同）。

### 1.2 observation

- 每条 observation 必须能追溯到 `snapshot_id`，并记录 `model_name`、`prompt_version`、`schema_version`。
- `evidence_text` ≤ 200 字符（与 02 §6 一致），只在内部保存。
- `valid_for_term`、`term_basis`、`stale`、`conflict_type` 由代码按 08 §7、§8 判断，不由 LLM 输出（2026-10-12）。
- 每次 LLM 调用另存一条页面级抽取记录（不是 observation）：`snapshot_id`、关联的 `program_id`、`terms_mentioned`（页面上出现的全部学期写法）、模型与版本信息、原始输出（08 §4）。

### 1.3 fact

- 只有人工审核（`approved` 或 `corrected`）后才会产生或更新 fact。
- **人工修正的值受保护**：`review_status = corrected` 的 fact，不会被后续自动抽取覆盖。只有当它的来源页面发生变化（新 snapshot 的 `normalized_text_sha256` 与该 fact 所依据的不同），新的 observation 才会进入审核队列；是否更新仍由人决定。
- fact 的每次变更都生成新的 `fact_version`，旧版本保留。

### 1.4 release

- 带版本号和日期，内容是一组确定的 fact 版本。
- **变化推送只基于两个 release 之间的 fact 差异**，不基于 snapshot 或 observation 的变化。

## 2. 申请季（term）是一等概念

- 每条 observation 和 fact 都带 `valid_for_term`，格式为 `"<Season> <YYYY>"`，其中 Season ∈ {Fall, Spring, Summer}，如 `"Fall 2027"`；或者取特殊值 `term_unknown`。
- 判断不出页面描述的是哪个入学季时，标 `term_unknown` 并**进入审核**。**不得默认为当前季。**
- `term_unknown` 的 observation 不能直接变成 fact，审核人必须指定具体的 term 或驳回。
- 同一项目、同一字段、不同 term 的 fact 并存（例如 Fall 2026 与 Fall 2027 的截止日期）。

## 3. 项目身份

- `program_id` 在 Phase 2 的**登记表**中分配（slug），并绑定 IPEDS `unitid`。抓取和抽取的所有结果都挂在 `program_id` 上，抓取器和抽取器不创建 program_id。
- 页面与项目是多对多关系：表 `program_pages(program_id, page_id)`（结构见 `06_source_registry.md` §3.3）。例如研究生院统一的语言要求页会服务多个项目。`page_id` 与 snapshot 中的 `page_id` 是同一个键。
- 一个 snapshot 属于一个 page；一条 observation 属于一个 `(snapshot, program)` 组合。

## 4. `value_status`：取值状态的唯一权威表达

不能都存成 null。每条 observation 和 fact 都带 `value_status`（定义见 02 §6），它是字段取值状态的**唯一**权威表达；02 中各字段的枚举**不含** `not_mentioned`。

| value_status | 含义 | `value` |
|---|---|---|
| `found` | 页面可访问，且给出了可以直接使用的值 | 有值（符合 02 中的类型或枚举） |
| `referenced_elsewhere` | 页面讲到该字段，但让读者去看别的页面或来源，自己没给值（例如“见研究生院要求页面”）。指向哪里另存于 `reference_target`（页面上的链接文字或网址）（2026-10-18 新增） | null |
| `mentioned_without_value` | 页面提到有这项要求，但没给值，也没指向别处（例如“有不退还的申请费”“须提交英语成绩”“competitive TOEFL score”）（2026-10-18 新增） | null |
| `not_mentioned` | 页面可访问，抽取成功，且页面完全没提到该字段 | null |
| `extraction_failed` | 页面可访问，但抽取失败（模型报错、输出不合 schema、校验不通过） | null |
| `page_unavailable` | 页面不可访问（snapshot `classification ∈ {blocked, unavailable, fetch_error}`，见 07 §7.1） | null |

- 约束：`value_status = found` ⇔ `value` 非空。违反时校验报错，不写入。
- 抓取失败时，同样要为该 page 关联的每个 `(program_id, field)` 写一条 observation，`value_status = page_unavailable`，关联那条失败的 snapshot。这样“没有数据”也有记录可查。
- fact 层的 `value_status` 由审核人确认。例如一个项目的多个页面中，一个不可访问、另一个写明了该字段，审核后 fact 为 `found`。
- 一个项目的多个页面状态不同时，项目层默认取信息最多的：`found` > `referenced_elsewhere` > `mentioned_without_value` > `not_mentioned`。
- `referenced_elsewhere`：指向的页面已登记给该项目时，以那一页的值为准（08 §8.1）；没有登记时，列为来源登记的覆盖缺口，进入审核。
- `not_mentioned`、`mentioned_without_value`、`referenced_elsewhere` 也是事实，可以对外发布（分别为“官网未说明”“官网提到但未给出具体值”“官网指向其他页面”）；`extraction_failed` 和 `page_unavailable` 不能成为已发布的 fact，必须先重抓、重抽或人工处理。

## 5. 重跑规则（为后续阶段预留）

| 触发 | 动作 |
|---|---|
| 页面变化（`normalized_text_sha256` 变了） | 对该页面关联的所有 program 重抽 |
| 规范化版本变化（07 `normalizer_version`） | 新版本正文与旧版本不同的页面重抽 |
| `schema_version` 升级（含 v1 字段的类型、枚举、含义变化）或 `prompt_version` 升级；`model_name` 变化视同 `prompt_version` 升级 | 全量重抽 |
| 每个申请季开始时：**暂定每年 8 月 15 日**（2026-10-01 定，可在 P4 调整） | 全量重抓 + 重抽一次 |

重抽只产生新的 observation，不直接改 fact。进入审核的规则见 §1.3。

- 抽取的输入（2026-10-12，08 §2.1）：某页面首次抽取时，取它最新的成功快照，与 07 的分类无关；之后只在最新成功快照的 `norm_sha256` 与上次抽取所用快照不同时重抽。最新一次取得失败时写 `page_unavailable` 的 observation（§4）。
