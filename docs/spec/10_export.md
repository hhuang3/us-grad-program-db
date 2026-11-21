# 10 给留学顾问的导出（P5 最小版本）

> 状态：draft v0.2（2026-11-20，负责人看过第一份导出后：方向、学校简称、学位名称、排序、“见其他页面”的链接、与标准答案集不一致时标待核实）。v0.1（2026-11-20）。目的是拿给留学顾问看，验证需求；形式以后可能改。依据：02 v0.7、05、08 v0.8。

## 1. 命令与范围

- `gradprog export [--out <路径>] [--on <YYYY-MM-DD>] [--include-holdout]` → 一个 xlsx，默认写到 `data/exports/advisor_<日期>.xlsx`（不进 git）。
- 只读当前结果（`data/extraction/derived/current.csv`）、登记表、快照索引和变化记录，**不调用 API，不放任何页面原文**，只放链接。
- 项目：登记表中 `status = selected`、且至少有一个未停用页面的项目。
- 独立抽检集（09 §6）的项目默认不导出：负责人交答案前不看它们的抽取结果。`--include-holdout` 时导出。
- `--on`：判断“已过期”所用的日期，默认当天（UTC）。

## 2. 说明表

导出日期；页面检查日期的范围；免责声明“数据整理自各校官网，申请前请以官网最新信息为准。”；各标记的含义：
- **待核实**：这个值进了审核队列（08 §10，另加 §5 的规则），或有多个不同的值，还没有人工核对。单元格标黄，原因写在“待核实说明”列。
- **已过期**：截止日期早于导出日期。标灰，排在最后。
- 只招秋季的项目，学期按日期推算。

## 3. 项目总表

每个项目一行，中文表头：方向、学校简称、学校、项目、学位、STEM、时长、托福（旧制）、托福（新制）、雅思、GRE、GMAT、申请费、学费、入学季、官网链接、最后检查日期、待核实说明。

### 3.1 取值写法

| 列 | 写法 |
|---|---|
| 方向 | 登记表 `cip_group`：ds 数据科学、analytics 商业分析、stats 统计、econ 经济、mgmt_sci 管理科学 |
| 学校简称 | “简称 / 中文名”（登记表 `institution_short`、`institution_name_zh`，06 §3.1）；未填时写英文校名 |
| 学位 | 登记表 `degree_label`（如 MQE、MQM）；没有时写 `degree_type` 大写（MS、MA） |
| STEM | `stem_claim_on_page`：yes →“是（页面声称）”，no →“否（页面写明）”；页面写了 CIP 时加“，CIP 30.7001” |
| 时长 | 最短、最长相同 →“12 个月”；不同 →“9–18 个月” |
| 托福、雅思 | 数字原样；有条件录取区间不放 |
| GRE、GMAT | required 必需、optional 可选、not_required 不要求、not_accepted 不接受、conditional_waiver 可申请豁免 |
| 申请费 | “$125”；0 →“免申请费” |
| 学费 | “$1,288 / 学分（2026-2027）”，学年中的长破折号统一为连字符；口径：每学分、每学期、每年、项目总额；没写口径时只写金额；含杂费时加“，含杂费”；多条学费用“；”分隔 |
| 入学季 | 登记表 `intake_terms`：秋季、春季、夏季 |
| 官网链接 | 项目首页（`page_type = program_home`）的网址 |
| 最后检查日期 | 该项目各页面最近一次成功取得的日期中最早的一个 |

按方向（上表顺序）、学校简称、项目名排序。

没有值时：`referenced_elsewhere` →“见其他页面：<链接文字或网址>”，单元格链接到该页面：页面写的是网址时直接用；写的是链接文字时，在给出这句话的页面的原始快照中找文字相同或相互包含的链接，只有一个时用它，找不到或不唯一时链接到给出这句话的页面；`mentioned_without_value` →“提到但未给值”；`not_mentioned` →“未提及”；`extraction_failed` →“待核实（抽取失败）”；`page_unavailable` →“待核实（页面无法访问）”。

每个有值的单元格链接到给出该值的页面。

### 3.2 多个值时怎么选

按“项目 × 字段”处理：
1. 只看 `found` 的值，去掉带 `cross_program_contamination` 的。
2. 冲突处理给出了默认建议（`suggested_observation_id`，08 §8.1），只用建议的那条。
3. 否则只用层级最具体的页面：项目页 > 系页 > 研究生院页。
4. 剩下的不同值都列出，用“ / ”分隔，并标待核实（原因“页面上有多个不同的值”）。学费不按这一条判断：不同口径的学费可以并存，是否矛盾由 08 §8 判断。
5. 没有 `found` 时，状态取 `found` > `referenced_elsewhere` > `mentioned_without_value` > `not_mentioned` > `extraction_failed` > `page_unavailable` 中最靠前的。

### 3.3 待核实

选中的值（或选中的无值状态）所在的行有审核原因（08 §10，按 §5 调整后），或 §3.2 第 4 条剩下多个值，就在值后加“（待核实）”，单元格标黄，原因用中文写进“待核实说明”，例如“托福（旧制）：同一页面的数值互相矛盾”。

## 4. 截止日期表

每行一个日期：学校简称、学校、项目、学期、轮次（页面原文）、类型、适用对象、日期、状态、待核实说明、来源链接。

- 来源：`found` 的截止日期，去掉带 `cross_program_contamination` 的。
- 类型：application 申请截止、deposit 押金、decision_release 录取结果、international_docs 签证材料、other 其他。适用对象：all 全部、international 国际学生、domestic 美国本土、funding_consideration 奖助评选。
- 只写滚动录取、没有日期的：日期写“滚动录取”。学期为 `term_unknown` 时写“未确定”。
- 同一项目、日期、类型、适用对象出现在多个页面时只留一行：层级最具体的页面；层级相同时优先写明了学期的那一条。
- 状态：日期早于 `--on` →“已过期”（标灰，排在最后）；否则有审核原因 →“待核实”（标黄）；否则留空。排序：未过期的按学校简称、学期（同一年按春、夏、秋）、日期，已过期的随后，顺序相同；学期未确定的排在该校最后。

## 5. 导出层的审核调整（2026-11-20）

- 只招秋季的项目（`intake_terms = fall`），`term_inferred`（08 §10 第 2 条）不算待核实。
- 截止日期所属学期的季节不在该项目 `intake_terms` 里时，标待核实，原因“该学期不在项目入学季内”（例如 UW MSDS 取消春季入学后，系页仍列春季截止日期）。
- 标准答案集（09）中的项目：导出的值与标准答案不一致时，标待核实，原因“抽取结果与人工标注不一致”。项目总表比较选中的值（或无值状态）与该字段的标准答案；截止日期表中，“日期 + 类型”不在标准答案中的行标出。抽取所用快照的正文与标准答案的快照不同的页面不比较，因为页面可能已经更新。
- 这三条只影响导出，不改 08 的审核队列。

## 6. 最近变化表

- 来源：`data/changes/change_log.csv`（进 git）。列：`date`、`page_id`、`program_id`、`application_info`（yes / no）、`description`（中文一句话，不含页面原文）。每次分析快照运行的 changed 页面时追加；从 2026-10-25（规范化 v2 后第一次正式运行）开始记录，之前的变化大多是规范化调整期的噪音，不回填。
- 导出 `application_info = yes` 的行，按日期倒序：日期、学校简称、学校、项目、变化、页面链接。

## 7. 待核实原因的中文

| 原因 | 中文 |
|---|---|
| term_unknown | 无法确定适用学期 |
| term_inferred | 学期由日期推算 |
| season_undetermined | 无法确定是哪一季 |
| term_date_mismatch | 写明的学期与日期不一致 |
| summer_date_unverified | 夏季日期没写年份 |
| evidence_failed:* | 抽取结果未通过原文核对 |
| toefl_scale_unrecognized | 无法判断托福分制 |
| conflict:in_page_contradiction | 同一页面的数值互相矛盾 |
| conflict:level_mismatch | 不同层级页面的数值不同 |
| conflict:below_graduate_school_minimum | 低于研究生院的最低要求 |
| conflict:deadline_mismatch | 不同页面的截止日期不同 |
| conflict:cross_program_contamination | 可能属于其他项目 |
| only_stale_deadlines | 项目只有已过期的截止日期 |
| suspected_redesign | 页面疑似改版 |
| audience_doubtful | 页面可能不是写给申请者的 |
| coverage_gap | 指向的页面尚未收录 |
| repeated_call_failure | 多次抽取失败 |
| tuition_basis_missing | 学费没写口径 |
| term_outside_intake | 该学期不在项目入学季内 |
| multiple_values | 页面上有多个不同的值 |
| gold_mismatch | 抽取结果与人工标注不一致 |

未列出的原因原样显示。
