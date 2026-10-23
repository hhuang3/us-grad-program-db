# 字段定义 draft v0.3

> 状态：草案。Phase 1 不实现，作为 Phase 2 之后的规格。
> 数据分层、申请季、项目身份等规则见 `05_data_model.md`，本文件只定义字段。
> 枚举值全部小写蛇形。字段是否在页面上找到，**只由**元数据 `value_status`（found / not_mentioned / mentioned_without_value / referenced_elsewhere / extraction_failed / page_unavailable，见 §6）表达，这是权威状态；各字段的枚举中不含 `not_mentioned`。`value_status ≠ found` 时字段值为 null。

## 1. 项目主表 `program`

| 字段 | 含义 | 类型 / 取值 | 官网通常位置 | 备注 |
|---|---|---|---|---|
| program_id | 内部 ID | str（slug），Phase 2 登记表中分配 | – | 主键 |
| unitid | IPEDS 机构 ID | int | – | 来自 IPEDS，绑定机构 |
| institution_name | 校名 | str | – | 以 IPEDS 名称为规范名，官网写法另存别名 |
| program_name | 官方项目名 | str | 项目首页 | 原样保留官方写法 |
| degree_type | 学位 | enum：ms / ma / mps / meng / msc / other | 项目首页 | other 时在备注写明 |
| department | 所属学院/系 | str | 项目首页 | |
| delivery_mode | 授课形式 | enum：on_campus / online / hybrid | 项目首页 | online 通常不能办 F-1 |
| length_months_min / length_months_max | 学制（月） | int，可空 | Program overview | 只写一个值时 min = max |
| start_terms | 入学季 | list enum：fall / spring / summer | Program overview / Admissions | |
| cip_code | CIP 代码 | str "NN.NNNN" | ISSO 的 STEM 项目列表、项目 FAQ | 格式规则见 `03_stem_logic.md` |
| cip_source | CIP 出处 | enum：school_stem_page / program_page / i20_statement / ipeds_inferred / unknown | – | 只有学校自己的声明才能用于 confirmed |
| stem_status | STEM 认定 | enum：confirmed_by_school / not_on_list / cip_on_list_unconfirmed / cip_not_on_list_unconfirmed / unknown | 同上 | 推导规则见 `03_stem_logic.md` |
| stem_claim_on_page | 页面是否声称本项目是 STEM | enum：yes / no | 项目首页、FAQ | 不影响 `stem_status`（没有 CIP 时 stem_status 仍为 unknown）；v0.3 新增，见 08 §3.2 |

## 2. 考试与语言要求

| 字段 | 含义 | 类型 / 取值 | 官网通常位置 | 备注 |
|---|---|---|---|---|
| gre_policy | GRE 要求 | enum：required / optional / not_required / not_accepted / conditional_waiver | Admissions / FAQ | 映射见下方说明（v0.3 新增 not_required） |
| gre_notes | GRE 补充说明 | str（短摘要） | 同上 | 如豁免条件 |
| gmat_policy | GMAT 要求 | 同 gre_policy 枚举 | 同上 | BA 项目常见 |
| toefl_min_legacy | TOEFL 最低总分（旧制） | int 0–120，可空 | 研究生院国际学生要求页 | |
| toefl_min_new_scale | TOEFL 最低总分（新制，2026-01-21 起） | float 1.0–6.0，步长 0.5，可空 | 同上 | 与旧制分开存 |
| toefl_scale_on_page | 页面使用的 TOEFL 分制 | enum：legacy / new / both | 同上 | |
| toefl_section_mins | 单项最低分 | json：{"scale": "legacy"\|"new", "reading":…, "listening":…, "speaking":…, "writing":…} | 同上 | |
| ielts_min_overall | 雅思最低总分 | float 0–9，步长 0.5，可空 | 同上 | |
| ielts_band_min | 雅思单项最低 | float 0–9，步长 0.5，可空 | 同上 | |
| duolingo_min | 多邻国最低分 | int，可空 | 同上 | |
| english_req_level | 语言要求的来源层级 | enum：program / graduate_school | 同上 | 很多项目直接沿用研究生院标准 |
| english_waiver | 语言豁免规则 | str（短摘要） | 同上 | |

**`gre_policy` / `gmat_policy` 的映射**（v0.3）：

| 页面写法 | 取值 |
|---|---|
| “required” | `required` |
| “optional”“may submit”“not required but will be considered” | `optional` |
| “not required”“do not require”，没说提交了是否会被考虑 | `not_required` |
| “not accepted”“will not be considered” | `not_accepted` |
| “required unless …”、有豁免条件 | `conditional_waiver` |

## 3. 申请材料与费用

| 字段 | 含义 | 类型 / 取值 | 官网通常位置 | 备注 |
|---|---|---|---|---|
| app_fee_usd | 申请费 | float，可空 | Apply 页 | |
| fee_waiver | 申请费减免 | enum：available / not_available | Apply 页 | |
| fee_waiver_conditions | 减免条件 | str（短摘要） | Apply 页 | |
| rec_letters_required | 推荐信数量 | int，可空 | Apply 页 | |
| three_year_bachelor | 是否接受三年制本科 | enum：accepted / case_by_case / not_accepted | 研究生院国际学位认定页 | 印度申请者极关心 |
| min_gpa | 最低 GPA | float，可空；另存 gpa_scale | Admissions | |
| prerequisites | 先修要求 | list：calculus / linear_algebra / probability / statistics / programming / other | Admissions | |
| documents_required | 申请材料 | list：sop / resume / transcript / video_essay / writing_sample / other | Apply 页 | |
| interview | 面试 | enum：required / by_invitation / none | Admissions | |

## 4. 学费与资助

| 字段 | 含义 | 类型 / 取值 | 官网通常位置 | 备注 |
|---|---|---|---|---|
| tuition_basis | 学费计费方式 | enum：per_credit / per_term / per_year / program_total | Bursar / Cost 页 | 页面原始口径；v0.3 新增 per_year |
| tuition_amount_usd | 学费金额 | float，可空 | 同上 | **页面原始口径下的原始金额**，与 tuition_basis 配套，不换算；**只记录国际学生适用的金额**（公立校即州外学费），不记州内学费 |
| tuition_program_total_usd_est | 整个项目学费估算 | float，可空 | – | **派生字段**，由代码按 08 §3.1 换算，记录换算方法和输入；缺少输入时为空。v0.3 新增 |
| credits_required | 总学分 | int，可空 | Curriculum | per_credit 时用于估算总额 |
| tuition_year | 学费适用年度 | str，如 "2026-27" | 同上 | |
| funding | 资助情况 | enum：none_typical / partial_scholarship / ta_ra_possible | Funding / FAQ | |

## 5. 截止日期子表 `deadline`（一个项目多行）

| 字段 | 含义 | 类型 / 取值 | 备注 |
|---|---|---|---|
| program_id | 关联主表 | str | |
| term | 入学季 | str，如 "Fall 2027" | 必填；判断不出则 term_unknown 并进审核 |
| round_name | 轮次 | str，如 Priority / Round 1 | 原样保留官方写法 |
| deadline_type | 日期类型 | enum：application / international_docs / deposit / decision_release / other | v0.3 新增。international_docs：国际学生材料（签证文件、I-20 申请等）的截止 |
| deadline_date | 截止日期 | date | 页面没写年份时按每年固定日期推算（08 §7.2，`term_basis = recurring_no_year`） |
| deadline_tz | 时区 | str（IANA），可空 | 如 America/New_York |
| applicant_scope | 适用对象 | enum：all / international / domestic / funding_consideration | |
| is_rolling | 是否滚动录取 | bool | |

## 6. 每个字段都附带的元数据

| 字段 | 含义 | 类型 / 取值 |
|---|---|---|
| value_status | 取值状态（权威） | enum：found / not_mentioned / mentioned_without_value / referenced_elsewhere / extraction_failed / page_unavailable；判断标准见 05 §4 |
| evidence_url | 来源页面 URL | str |
| evidence_text | 来源原文片段（仅内部保存，不对外发布） | str，≤ 200 字符 |
| snapshot_id | 来源快照 | str |
| retrieved_at | 抓取时间 | datetime（UTC） |
| confidence | 抽取置信度 | float 0–1 |
| review_status | 审核状态 | enum：auto / approved / corrected / rejected |
| reference_target | `value_status = referenced_elsewhere` 时页面指向的链接文字或网址 | str，可空 |
| valid_for_term | 适用入学季 | str，如 "Fall 2027"，或 term_unknown；没有日期的字段页面没写学期时为空（05 §2） |
| term_as_written | 条目对应学期在页面上的原文 | str，可空 | 
| term_basis | valid_for_term 的依据 | enum：stated / inferred_from_date / recurring_no_year / unknown |
| stale | 截止日期早于取得日期 | bool |
| conflict_type | 冲突类型（可多值） | list enum：level_mismatch / below_graduate_school_minimum / deadline_mismatch / in_page_contradiction / cross_program_contamination |
| includes_fees | 学费金额含杂费 | bool，只用于学费字段 |

## 7. 待定事项

- ~~同一项目在研究生院页与系页数值冲突时的优先规则~~：**已关闭**（2026-10-12）。见 `08_extraction.md` §8.1：越具体的层级优先；项目页写“按研究生院要求”时用研究生院的值；研究生院要求视为下限，项目页低于下限时进审核。
- ~~学费是否区分州内/州外~~：**已关闭**（2026-10-01）。只记录国际学生适用的金额，公立校即州外学费（见 §4 `tuition_amount_usd`）。
- ~~多个专业方向（track/concentration）是否拆成多个 program_id~~：**已关闭**（2026-10-01）。一个申请入口 = 一个 `program_id`：共用申请入口的 track 算一个项目，分别申请、要求不同的拆开（见 `06_source_registry.md` §2.1）。

## 8. 修订记录

- v0.3 补充（2026-10-18）：`value_status` 新增 `mentioned_without_value`、`referenced_elsewhere`（判断标准见 05 §4）；`gre_policy` / `gmat_policy` 新增 `not_required` 并给出映射表。
- v0.3（2026-10-12，Phase 4a）：按 `08_extraction.md` §12 修订。新增 `stem_claim_on_page`、`tuition_program_total_usd_est`（派生）、截止日期子表 `deadline_type`；`tuition_basis` 新增 per_year，`tuition_amount_usd` 改为页面原始口径；没写年份的 `deadline_date` 按每年固定日期推算；元数据新增 `term_as_written`、`term_basis`（含 recurring_no_year）、`stale`、`conflict_type`、`includes_fees`；§7 关闭“研究生院页与系页冲突”。
- v0.2（2026-10-01，Phase 2a）：学费只记国际学生适用金额（公立校即州外学费）；§7 关闭“学费是否区分州内/州外”与“track/concentration 是否拆分”两项，“研究生院页与系页冲突”改为 P2 两页都登记、P4 定优先规则。
- v0.1（2026-09-30，Phase 1b，按逐项答复修订）：
  - 新增元数据 `value_status`（found / not_mentioned / extraction_failed / page_unavailable），作为所有字段的权威状态；从各枚举中删除 `not_mentioned`（delivery_mode、gre_policy、gmat_policy、toefl_scale_on_page、fee_waiver、three_year_bachelor、interview、tuition_basis、funding）。
  - `stem_status` 改为五个值，新增 `cip_not_on_list_unconfirmed`；真值表见 `03_stem_logic.md` §5。
  - `toefl_min_band` 改名为 `toefl_min_new_scale`；`toefl_scale_on_page` 取值改为 legacy / new / both；`toefl_section_mins` 的 `scale` 取值同步改为 legacy / new。`ielts_band_min` 不变。
- v0（草案原文）。
