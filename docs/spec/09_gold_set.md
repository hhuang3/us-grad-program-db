# 09 标准答案集（gold set）

> 状态：draft v0.2（Phase 4a，2026-10-18：§3.2 三种无值状态、GRE 映射、适用对象、共用总览页、多页证据、附带条件的截止日期）。v0.1（2026-10-12）。标注由负责人完成。字段与规则以 `08_extraction.md` 和 02 v0.3 为准。

## 1. 用途与工作量

- **用途**：人工标注的基准，用来衡量 08 的抽取结果。**按字段统计**：
  - 准确率：`found` 的 observation 中，值与标准答案一致的比例；
  - 漏抽率：标准答案为 `found`、抽取不是 `found` 的比例；
  - 无值状态正确率：标准答案为 `referenced_elsewhere`、`mentioned_without_value`、`not_mentioned` 时，抽取给出同一状态的比例；
  - 误报率：标准答案不是 `found`、抽取为 `found` 的比例（例如凭常识填了一个分数）；
  - 学期正确率：`valid_for_term` 与标准答案一致的比例；
  - 审核召回：标准答案中带 `contradictory`、`contamination`、`stale` 等标记的条目，被 08 §10 送进审核的比例。
  - 另用它定出 08 §10 第 6 条的 `confidence` 阈值。
- **标注对象是固定的一组快照**（§2 表中的 `snapshot_id`），不是实时网页。抽取也针对同一组快照运行，两边看的是同一份正文。快照以后变化时，标准答案集不随之更新；需要时另建 v2。
- **先标注，后看结果**：负责人在看到任何 LLM 抽取结果之前完成标注，避免受模型输出影响。
- **工作量估计**：
  - 6 个项目、18 个页面，规范化正文合计约 19.7 万字符（约 3 万英文词）。通读约 2.5 小时。
  - 行数：非截止日期字段每项目 15 行，共 90 行（模板已预填）；截止日期按轮次 × 类型另加，估计 40–50 行（Duke 一项就有 4 轮 × 申请、录取发布、押金 3 类，外加签证截止）。合计约 130–140 行。
  - 填写约每行 1–1.5 分钟，2–3.5 小时。
  - **合计约 5–6 小时**，可按项目分次完成。

## 2. 项目

| 项目 | 页面（快照） | 主要检验什么 |
|---|---|---|
| `unt-ms-datascience` | pg-0007（snap-20261011T005919Z）、pg-0008（snap-20261007T001931Z）、pg-0009（snap-20261011T010245Z） | 过期的截止日期（Fall 2026，08 §7.5）；有春季入学，学期推算受限（08 §7.2） |
| `duke-other-mqmbusinessanalytics` | pg-0054（snap-20261011T010442Z）、pg-0055（snap-20261011T010445Z）、pg-0056（snap-20261011T010449Z）、pg-0057（snap-20261011T010452Z） | 倒计时区块；2025 年签证截止日期；4 轮截止日期表与 `deadline_type` |
| `jhu-ms-businessanalyticsai` | pg-0061（snap-20261006T153726Z）、pg-0062（snap-20261004T150238Z）、pg-0063（snap-20261004T150247Z）、pg-0064（snap-20261004T150253Z） | 跨项目内容污染（08 §8.4）；面授与在职线上版写在同一页；scope_note |
| `bu-ms-businessanalytics` | pg-0025（snap-20261011T010347Z）、pg-0026（snap-20261011T010352Z） | 同一页内数值矛盾（托福 90 / 95）；跨页面轮次数不同；跨项目内容污染 |
| `ucla-other-quantitativeeconomics` | pg-0048（snap-20261011T010427Z）、pg-0049（snap-20261011T010431Z）、pg-0050（snap-20261011T010435Z） | 同一页多个学期；第一个有效变化实例；研究生院层级页（pg-0050） |
| `uwmadison-ms-statistics`（对照） | pg-0031（snap-20261011T010407Z）、pg-0033（snap-20261011T010414Z）、pg-0070（snap-20261018T101205Z，研究生院英语要求页，2026-10-18 补登） | 页面结构简单时的基线；`referenced_elsewhere` 与层级规则；有条件录取的英语分数区间 |

快照编号写的是 `snapshot_id` 的时间部分，完整写法为 `snap-<时间>-<page_id>`；模板中写完整编号。

**对照项目选 UW–Madison MS Statistics 的理由**：
- 可以自动抓取，条款无限制（stat.wisc.edu）。
- 页面结构简单：只有秋季入学（“no spring admissions”）；没有轮播、倒计时、活动列表；10-07、10-11 两次运行都是 unchanged。
- 项目页的英语要求指向研究生院；研究生院的英语要求页于 2026-10-18 补登，可检验 `referenced_elsewhere` 与层级规则（08 §8.1）。
- 对照项目的准确率应明显高于其他 5 个；如果不是，问题在提示词或 schema 的基本层面，而不在复杂页面。

## 3. 标注说明

### 3.1 正确值

- 以 §2 表中的快照正文为准（本地 `data/snapshots/normalized/` 或原始文件），**不看实时网页**，也不用页面以外的知识。
- 一个项目的所有页面一起看：某字段在任何一页找到，就填 `found`；多页都有且值不同时，每个值各填一行（§3.3）。
- **共用总览页**（同一页面列出多个项目，例如统计系总览页列出 5 个项目的截止日期）：只采用明确标为本项目的那一行，其他项目的行（例如 MSDS 的春季截止日期）不采用，也不标 `contamination`。
- **同一个值出现在多个页面**：`evidence_page_id` 填所有写了这个值的页面，分号分隔，最具体的排在前面（项目页 > 系页 > 研究生院页）。值不同则按 §3.3 分行。
- **上级页面交出决定权**（2026-10-24）：上级页面只说“由项目决定”（例如研究生院写“研究生院不要求 GRE，由各项目决定”），不算同一个值出现在多个页面，`evidence_page_id` 只填给出值的页面，可在 `notes` 注明上级页面的说法。
- 值的写法按 02（含 08 §12 的修订）：
  - 学费：`tuition_amount_usd` 填页面原始口径下的金额，`tuition_basis` 填页面口径（每学分、每学期、每年、整个项目）；只填国际学生适用的金额，公立校即州外学费。**不要换算**。
  - 时长：换算成月（“1 year” → 12；“9 to 18 months” → min 9、max 18）。
  - 截止日期：`YYYY-MM-DD`。
  - TOEFL：旧制填 `toefl_min_legacy`，新制填 `toefl_min_new_scale`；两种都写了两行都填，`toefl_scale_on_page` 填 `both`。
  - 英语最低分只填**标准要求**。页面另给“有条件录取”的分数区间（低于最低要求、入学后须参加英语测试或修英语课）时，该区间写进 `notes`，不作为最低分数（2026-10-18）。
  - CIP：只填页面写明的 6 位代码；`stem_claim_on_page` 填页面是否声称 STEM。
- 原文片段只填在本地副本的 `evidence_text` 列（§4）。
- `notes` 可以引用 **10 个词以内**的原文用于说明（例如 “two-year”、“Tuition Rates”）；不得整句或整段粘贴（2026-10-24）。

### 3.2 没有给出值：三种状态

`value` 都留空，`value_status` 按下表区分（判断标准见 05 §4）：

| value_status | 什么时候用 | `notes` |
|---|---|---|
| `referenced_elsewhere` | 页面讲到该字段，但让读者去看别的页面，自己没给值（例如“见研究生院要求页面”） | 写明指向哪里（链接文字或网址） |
| `mentioned_without_value` | 页面提到有这项要求，但没给值，也没指向别处（例如“有不退还的申请费”“须提交英语成绩”“competitive TOEFL score”） | 可空 |
| `not_mentioned` | 所有页面都完全没提到 | – |

- **单纯的导航链接不算 `referenced_elsewhere`**（2026-10-24）：页面上只是列出一个链接（例如资源列表里的 “Tuition Rates”），正文没有说“详见某页面”，按 `not_mentioned` 填，`notes` 可写明有这个链接。只有正文明确让读者去看某页面获取该字段的信息（例如“see the Graduate School requirements page for additional information”）才算 `referenced_elsewhere`。
- 多个页面状态不同时，取信息最多的：`found` > `referenced_elsewhere` > `mentioned_without_value` > `not_mentioned`。
- `evidence_page_id` 照填（`not_mentioned` 除外）；本地副本的 `evidence_text` 照抄提到该字段的原文。

### 3.2a GRE / GMAT

按 02 的映射表：“not required”“do not require”且没说提交了是否会被考虑 → `not_required`；“optional”“may submit”“not required but will be considered” → `optional`；“not accepted” → `not_accepted`；有豁免条件 → `conditional_waiver`。

### 3.2b 适用对象

- 目标申请者：从校外申请本项目的新生，以国际学生（F-1）为主。
- 标注时**忽略**：已在本校读研的学生转入或加主修的流程；本校本科毕业生的快速通道（例如给本校本科毕业生的一年制路径）。这些内容不填，也不标 `contradictory`。
- 截止日期按适用对象分开的（国际 / 美国本土 / 奖助评选），用 `applicant_scope` 区分，照常标注。

### 3.3 页面自相矛盾

- 每个说法各填一行，`flags` 都写 `contradictory`。
- 你能判断哪个正确时，在正确那行的 `notes` 写 `correct`，另一行写 `incorrect` 和理由；判断不了就都不写。
- 内容属于其他项目（跨项目内容污染）时，`flags` 写 `contamination`，`notes` 写明属于哪个项目。按 scope_note 本就不采用的区块，同样标出，不要省略。

### 3.4 适用学期

- 按 08 §7 的规则填 `valid_for_term`（`Fall 2027`、`term_unknown` 或留空，见下）。
- 两个推算标记的区别：
  - `inferred_term`：**日期有年份**，按日期落在哪个季节区间推算学期。例：页面写 “Priority deadline: November 9, 2026”、页面没写季节、项目只有秋季入学 → Fall 2027。
  - `recurring_no_year`：**日期没有年份**，按每年固定日期推算（取快照取得日期之后该月日的下一次出现），再定学期。例：页面写 “January 2 for a fall term start”、10 月取得 → 2027-01-02，Fall 2027。
  - 两者不同时用。
- 截止日期早于快照的取得日期，`flags` 加 `stale`，学期仍填它本来的学期（例如 UNT 填 Fall 2026）。
- **没有日期的字段**（托福、雅思、GRE、GMAT、学费、时长、学分、CIP、STEM、申请费）：页面没写学期时 `valid_for_term` **留空**，视为抓取时点的现行要求（2026-10-24）。页面写了学期或学年（例如 2026-27）时照填或按 08 §7.1 换算。
- `term_unknown` 只用于：截止日期无法确定学期；页面写了学期但无法确定是哪一季（例如 “for the 2026 applications”）。`notes` 写原因。

### 3.5 截止日期

- 每个“轮次 × 类型 × 适用对象”一行：复制模板中该项目的 `deadline` 行，填 `round_name`（原样）、`deadline_type`、`applicant_scope`、`value`（日期）。
- 默认值（2026-10-24）：页面没有轮次名 → `round_name` 留空；页面没有区分适用对象 → `applicant_scope = all`；页面没提滚动录取 → `is_rolling = false`。
- 倒计时区块里的轮次和日期照常标注，剩余时间不标。
- **附带条件的截止日期**：条件日期与申请截止日期相同（例如“材料须在秋季截止日期前送达，才能参加助教岗位评选”）→ 不单独建行，在申请截止那一行的 `notes` 里记录条件；日期不同 → 单独一行，`applicant_scope = funding_consideration`。
- 页面写“rolling”而没有日期：`is_rolling = true`，`value` 留空，`value_status = found`。
- 日期没写年份（如 “January 2”）：按每年固定日期，年份取快照取得日期之后该月日的下一次出现，再按季节区间填 `valid_for_term`（08 §7.2）；`flags` 加 `recurring_no_year`。

## 4. 文件

| 文件 | 进 git | 内容 |
|---|---|---|
| `data/gold/gold_set_v1.csv` | 是 | 标准答案，不含原文 |
| `data/gold/local/gold_set_v1_with_evidence.csv` | 否（gitignore） | 同样的行，多一列 `evidence_text`，供标注和审核时对照 |

两份文件行的顺序、`row_id` 一致。标注时建议只填本地副本，填完后由脚本去掉 `evidence_text` 列生成 git 版（脚本在 P4 实现阶段写）；在那之前两份手工同步。

**列**（模板已预填 `row_id`、`program_id`、`field`、`snapshot_ids`；其余由负责人填写）：

| 列 | 填写 | 说明 |
|---|---|---|
| `row_id` | 预填 | `<program_id>:<field>:<序号>`；新增的截止日期行按序号续编 |
| `program_id` | 预填 | |
| `field` | 预填 | v1 字段名（08 §3）；截止日期为 `deadline` |
| `snapshot_ids` | 预填 | 该项目标注所依据的全部快照，分号分隔 |
| `value` | 负责人 | 按 §3.1 |
| `value_status` | 负责人 | `found` / `referenced_elsewhere` / `mentioned_without_value` / `not_mentioned`（§3.2） |
| `valid_for_term` | 负责人 | §3.4 |
| `round_name` | 负责人 | 仅 deadline |
| `deadline_type` | 负责人 | 仅 deadline：`application / international_docs / deposit / decision_release / other` |
| `applicant_scope` | 负责人 | 仅 deadline：`all / international / domestic / funding_consideration` |
| `deadline_tz` | 负责人 | 仅 deadline，页面写了才填 |
| `is_rolling` | 负责人 | 仅 deadline：`true / false` |
| `evidence_page_id` | 负责人 | 依据的页面；同一个值出现在多页时全部填，分号分隔，最具体的在前（§3.1） |
| `flags` | 负责人 | `contradictory`、`contamination`、`stale`、`inferred_term`、`recurring_no_year`，分号分隔 |
| `notes` | 负责人 | 自由文本；可引用 10 个词以内的原文，不得整句或整段粘贴（§3.1） |
| `annotated_by` | 负责人 | |
| `annotated_at` | 负责人 | `YYYY-MM-DD` |
| `evidence_text` | 负责人 | **仅本地副本**，≤ 200 字符 |
