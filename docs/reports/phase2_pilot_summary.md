# Phase 2 试点报告：来源登记表（pilot 批次）

> 分支：`feat/phase2-source-registry`；登记与核对：2026-10-02 至 2026-10-03。
> 本报告的数字来自已提交的 `data/registry/*.csv`（提交 `6ccbb7e`）。`url_check.csv` 与 `review_pilot.md` 是不提交的工作文件。
> 本阶段没有抓取或保存任何项目页面的内容。访问大学网站的操作只有三类：读取 robots.txt；`check-urls` 的状态码与跳转检查（不读正文）；负责人要求的搜索引擎查询。

## 0. 概要

- **试点结果**：从工作表选出 19 个候选行，登记了 **37 条项目记录**。其中 **selected 21 个**（ds 4、analytics 5、stats 4、mgmt_sci 4、econ 4），excluded 10 个，backlog 6 个。
- **页面**：**63 个页面**，全部经负责人逐一核对，状态为 `confirmed`；分布在 **26 个域名**。selected 项目平均每个 **3.1 个页面**（2–5 个）。
- **准入检查**：`gradprog registry validate --ready --batch pilot` 结果为 **0 个错误，0 个警告**。
- **抓取可行性**：
  - 13 个项目（62%）的全部页面可以自动抓取（`fetch_method = auto`）。
  - 8 个项目（38%）的首页被拦截，改为人工取得（`fetch_method = manual`）。**人工取得的具体流程留到 P3 设计**。
  - 被拦截的页面有 24 个，占 38%。
- **测试**：`uv run pytest` 共 470 个测试，全部通过。

---

## 1. 试点项目清单（selected 21 个）

| 组 | 学校 | 项目 | CIP | 授课形式 | 取得方式 | 页面数 |
|---|---|---|---|---|---|---|
| ds | Columbia | MS in Data Science | 30.7001 | on_campus | manual | 2 |
| ds | NYU | Master of Science in Data Science | 30.7001 | on_campus | manual | 4 |
| ds | UNT | Master of Science in Data Science | 30.7001 | hybrid | auto | 3 |
| ds | UVA | M.S. in Data Science, Residential | 30.7001 | on_campus | auto | 4 |
| analytics | UT Dallas | MS BA & AI Flex | 30.7102 | hybrid | auto | 4 |
| analytics | UT Dallas | MS BA & AI Cohort | 30.7102 | on_campus | auto | 5 |
| analytics | UConn | MS Business Analytics and Project Management | 30.7102 | hybrid | auto | 4 |
| analytics | Boston University | MS in Business Analytics | 30.7102 | on_campus | auto | 2 |
| analytics | UChicago | Master's in Applied Data Science (In-Person) | 30.7101 | on_campus | auto | 3 |
| stats | UW-Madison | Statistics: Statistics, MS（Statistics 方向） | 27.0501 | on_campus | auto | 2 |
| stats | UW-Madison | Statistics: Statistics and Data Science, MS（MSDS 方向） | 27.0501 | on_campus | auto | 2 |
| stats | Columbia | M.A. in Statistics | 27.0501 | on_campus | manual | 5 |
| stats | UIUC | MS: Statistics（General Track） | 27.0501 | on_campus | manual | 2 |
| mgmt_sci | Duke | MQM: Business Analytics | 52.1399 | on_campus | auto | 4 |
| mgmt_sci | Rochester | Full-Time MS in Business Analytics | 52.1399 | on_campus | manual | 3 |
| mgmt_sci | Johns Hopkins | MS in Business Analytics and AI（全日制） | 52.1302 | on_campus | manual | 4 |
| mgmt_sci | WashU | Master of Science in Business Analytics | 52.1302 | on_campus | auto | 3 |
| econ | UW-Madison | MS in Quantitative Economics（MSQE） | 45.0603 | on_campus | auto | 2 |
| econ | USC | MS Applied Economics and Econometrics | 45.0603 | on_campus | manual | 2 |
| econ | Johns Hopkins | M.A. in Economics | 45.0603 | on_campus | manual | 3 |
| econ | UCLA | Master of Quantitative Economics（MQE） | 45.0603 | on_campus | auto | 3 |

几点说明：
- **analytics 组有 5 个项目**：UT Dallas 的 Flex 和 Cohort 都保留，用来测试"同校两个申请入口、共用页面"的情况。
- **UW-Madison MSQE**：项目还在等 SEVP 批准，批准前不录取 F-1 学生。保留在试点，是为了检验 P3/P4 能否发现批准后页面的变化。
- **stats 组**：Rutgers 的候选行移到了 main 批次。

---

## 2. 一个候选行对应几个项目，以及排除的项目

### 2.1 一个候选行对应的项目数

19 个候选行对应 37 条项目记录，平均 1.9 条：

| 一个候选行对应的项目数 | 1 个 | 2 个 | 3 个 | 4 个 |
|---|---|---|---|---|
| 候选行数 | 8 | 6 | 3 | 2 |

对应多个项目的原因：
- **同一学位有面授版和线上版，各自单独申请**：UVA、UChicago、UTD、Duke、JHU Carey、Rochester、WashU。
- **同一 CIP 下有多个独立申请入口**：UW-Madison 的 Statistics 方向（option）、UIUC 的 General Track 和 Analytics Concentration、UTD 的 Flex 和 Cohort。
- **同一学院有多个分析类硕士**：BU（MET）、Rochester（Marketing Analytics、AI in Business）、JHU（AAP 的 MS in Applied Economics）。这些先放进 backlog，到主批次再查证 CIP。

### 2.2 排除的项目（10 个）

| 原因 | 数量 | 项目 |
|---|---|---|
| `online_only` | **8** | UVA MSDS Online、UTD BA Online Cohort、UChicago MS-ADS Online、Duke MSQM Online、Duke Accelerated MSQM、JHU Carey MS BA&AI 在职版、Rochester Online MS BA & Applied AI、WashU OMSBA |
| `duplicate` | 1 | UW-Madison Biostatistics 方向：和 Statistics 方向共用一份申请，只在补充材料里勾选 |
| `not_admitting` | 1 | UIUC Statistics: Applied：从 2027 年春季起暂停招生 |
| `mba` | **0** | 试点里的 mgmt_sci 候选行（Duke、Rochester、JHU 52.1302、WashU）对应的都是非 MBA 的 MS 或 MQM 项目，这次没有遇到 MBA |

线上版的判断依据通常很明确，学校会直接写明不签发 I-20（UTD、JHU Carey），或者写明只有面授版能办签证（UChicago）。

### 2.3 backlog（6 个，都在 main 批次）

BU MET 的 MS in Applied Business Analytics；UW-Madison 的 Applied Statistics 方向；UIUC 的 Analytics Concentration；JHU AAP 的 MS in Applied Economics；Rochester 的 MS in Marketing Analytics 和 MS in AI in Business。它们是否属于同一候选行（CIP），到主批次再查证。

---

## 3. 页面

| 指标 | 数值 |
|---|---|
| selected 项目平均页面数 | **3.1**（最少 2，最多 5；项目与页面的关联共 66 条） |
| 不同的页面数 | 63 |
| 按层级 | 项目层级 46、**系/学院层级 9**、**研究生院层级 8** |
| 被多个项目共用的页面 | **3**：UTD 商学院的入学要求页和研究生院截止日期页（Flex 与 Cohort 共用），UW Statistics 系招生页（两个方向共用） |
| 按页面类型 | program_home 21、admissions 17、faq 8、requirements 6、deadlines 6、tuition 3、grad_school_intl 1、other 1 |
| 带 `scope_note` 的关联 | 3：UChicago 的 2 个面授版与线上版共用页面；JHU Carey 项目页中混入的其他项目内容 |

- 研究生院和学院层级的页面有 17 个，占 27%，但真正被多个**试点**项目共用的只有 3 个，因为试点项目分散在不同学校。主批次如果在同一所学校选多个项目，这类共用页面的比例会上升。
- **核对的效果**：我提议的页面共 66 个。最后结果如下：
  - 原样确认 **52 个（79%）**。
  - 修改网址 9 个：其中 5 个是 `check-urls` 发现的跳转或改域名（UConn 3 个、WashU 2 个），5 个由负责人改正（Columbia 3 个、UConn 1 个、UW 1 个）。UConn 的 pg-0021 被改了两次，所以两项合计 10，实际页面是 9 个。
  - 删除 5 个，原因分别是：失效、不适用于该项目、没有需要的信息、或会引入新域名。
  - 负责人新增 2 个。

---

## 4. robots.txt 与使用条款

| 项目 | 结果 |
|---|---|
| 域名数 | 26 |
| robots.txt | 已读取 21 个；**无法读取 5 个**（stat.illinois.edu、dornsife.usc.edu、econ.jhu.edu、krieger.jhu.edu、carey.jhu.edu；robots.txt 本身对我们的 User-Agent 返回 403） |
| robots.txt 明确禁止已登记页面 | 0 个 |
| `tos_status`（由负责人判断） | no_restriction 17；**unclear 7**（Columbia 的 datascience、ma.stat、gsas，JHU 的 econ、krieger、carey，UIUC stat）；**prohibits_automated_access 2**（www.engineering.columbia.edu、simon.rochester.edu） |
| `tos_status ≠ no_restriction` 的域名 | 上面 9 个 |

大多数学校没有一份适用于全站的使用条款，只有隐私、免责或版权声明。负责人把"未见禁止自动访问的条款"判为 `no_restriction`。负责人的判断写在 `domains.csv` 的 `tos_note` 中，以"负责人:"开头；我搜索时的说明以"Claude:"开头。

---

## 5. 抓取可行性

### 5.1 按域名

| 类别 | 域名 |
|---|---|
| 正常（robots 允许，页面可访问） | 16 个：nyu gsas、unt、virginia、utdallas ×3、uconn analytics、bu、uchicago、wisc stat / econ、ucla master.econ / grad、fuqua、rochester simon、olin.washu |
| robots.txt 无法读取 | 5 个：stat.illinois.edu、dornsife.usc.edu、econ.jhu.edu、krieger.jhu.edu、carey.jhu.edu |
| robots 允许，但页面返回 403（网站防护） | 5 个：datascience.columbia.edu、ma.stat.columbia.edu、www.gsas.columbia.edu、www.engineering.columbia.edu、cds.nyu.edu |
| robots 明确禁止 | 0 个 |

在此之上还有使用条款这一层：Columbia 的 4 个域名、JHU 的 3 个域名、UIUC stat 的条款都不是 `no_restriction`；rochester simon 的条款禁止自动访问。

### 5.2 按页面与项目（试点中 selected 的 21 个项目、63 个页面）

页面不可抓取的原因，按 06 §5.2 的顺序只取第一个成立的：

| 结果 | 页面数 | 占比 |
|---|---|---|
| 可抓取 | 39 | 62% |
| 条款（`tos`） | 10 | 16% |
| robots.txt 无法读取（`robots_unavailable`） | 11 | 17% |
| 网站防护 403（`site_blocked_403`） | 3 | 5% |
| robots 明确禁止 | 0 | 0% |
| **不可抓取合计** | **24** | **38%** |

一个页面常常同时有多个原因。不按顺序、每个原因都计入的话：条款不明 15、robots.txt 无法读取 11、网站防护 403 10、条款禁止 4。

| 项目 | 数量 | 占比 |
|---|---|---|
| 全部页面可抓取（`auto`） | 13 | 62% |
| 首页被拦截（`manual`） | 8 | 38% |
| 首页可抓、但部分页面被拦 | 0 | 0% |

- 8 个 manual 项目首页被拦的原因（按 06 §5.2 的顺序取第一个）：
  - 条款 3 个：Columbia DS、Columbia MA Stats、Rochester。
  - robots.txt 无法读取 4 个：UIUC、USC、JHU Econ、JHU Carey。其中 JHU 两个的条款也是 unclear。
  - 网站防护 403 1 个：NYU。
- 按组看可自动抓取的项目：ds 2/4、analytics **5/5**、stats 2/4、mgmt_sci 2/4、econ 2/4。被拦截的集中在 5 所学校：Columbia、NYU、UIUC、USC、JHU。另外 Rochester 是条款禁止。

### 5.3 被拦截项目的其他官方来源（只提议，未登记）

搜索到的替代来源基本都是**学位目录（catalog / bulletin）**，通常只有课程、学分和学位要求，**一般没有截止日期、申请材料和语言要求**。所以它们只能补充部分字段，不能替代招生页。下表的"可访问性"用 `check-urls` 同样的方式检查（遵守 robots.txt、不读正文），2026-10-03 在临时内存表中进行，没有写入登记表。

| 项目 | 替代来源 | 可访问性 | 备注 |
|---|---|---|---|
| Columbia MS DS | [Columbia Engineering 学位目录：Master of Science Degree](https://bulletin.columbia.edu/columbia-engineering/graduate-studies/graduate-programs/master-science-degree/) | 200 | 是工学院 MS 的通用页，不是 DS 专页；Columbia 的条款问题同样适用 |
| Columbia MA Stats | [GSAS Requirements for the MA Degree](https://www.gsas.columbia.edu/content/requirements-ma-degree) | **403** | 和已登记的 GSAS 页面同一个域名，同样被拦 |
| NYU MS DS | [NYU Bulletins：Data Science (MS)](https://bulletins.nyu.edu/graduate/arts-science/programs/data-science-ms/) | 200 | 另一个域名 bulletins.nyu.edu，可访问 |
| UIUC MS Stats | [Illinois Graduate Catalog：Statistics, MS](https://catalog.illinois.edu/graduate/las/statistics-ms/) | 200 | 可访问；UIUC 的条款仍是 unclear |
| USC MS AEE | [USC Catalogue：Applied Economics and Econometrics (MS)](https://catalogue.usc.edu/preview_program.php?catoid=16&poid=21800&returnto=6417) | **202** | 202 可能是机器人验证页，不一定是真实内容，需要人工确认；`catoid=16` 可能是旧版目录 |
| JHU MA Econ | [JHU e-catalogue：Economics, Master of Arts](https://e-catalogue.jhu.edu/arts-sciences/full-time-residential-programs/degree-programs/economics/economics-master-arts/) | 200 | 可访问；但 JHU 的条款判断（仅限非营利用途）对整个 jhu.edu 同样适用 |
| JHU Carey MS BA&AI | [JHU e-catalogue PDF：BA & AI, MS](https://e-catalogue.jhu.edu/business/degrees-certificates/business-analytics-artificial-intelligence-master-science/business-analytics-artificial-intelligence-master-science.pdf) | 200 | 同上 |
| Rochester MS BA | 未找到 rochester.edu 以外的官方来源 | – | Rochester 的条款对整个 rochester.edu 禁止抓取，同一域名内的替代来源同样受限 |

**结论**：替代来源能缓解"网站防护"和"robots.txt 无法读取"这两类问题（NYU、UIUC，以及有待确认的 USC），但解决不了"条款"问题（Columbia、JHU、Rochester），而且字段覆盖不完整。这 8 个项目在 P3 怎么取得，按负责人的决定留到 **P3 设计人工取得流程**时一并处理。

---

## 6. 字段定义（02）与数据模型（05）需要调整的地方

以下都是在登记和核对中遇到的实例。**02 和 05 现在都没有修改**，留给 P4 设计时决定。

### 6.1 02（字段）
1. **新增 `f1_eligible` 字段**（yes / no / pending_sevp / not_mentioned）。实例：UW-Madison MSQE 在等 SEVP 批准，批准前不录取 F-1 学生。
2. **`cip_source` 应放在 observation/fact 层，不进登记表**。负责人的理由：CIP 及其出处是从页面抽取的事实，放进登记表会和 05 的分层重复。P4 实现时，以 **JHU MA Economics**（pg-0045 写明了 45.0603，应判为 `confirmed_by_school`）作为测试用例。
3. **`degree_type = other` 时 `program_id` 不好读**（UCLA MQE、Duke MQM）。可以考虑增加 `mqe`、`mqm` 等取值。
4. **TOEFL 新旧分制分开存的设计得到了印证**：UConn 写"79（旧制）或 4.5（新制）"；WashU pg-0066 写的是"5.0 overall (new scale) OR 4.5 ≥ 90 overall (old scale)"，新制要求自相矛盾，是官网排版错误。

### 6.2 05（数据模型与抽取规则）
1. **`valid_for_term` 必须按条目判断，不能按页面判断**：
   - Columbia DS 写着"GRE optional for the 2026 applications"，无法判断指 Fall 2026 入学，还是 2026 年提交的申请。
   - UCLA MQE 同一页上，Fall 2026 已关闭、Fall 2027 于 10 月 1 日开放，两个申请季并存。
   - Duke pg-0055 的签证截止日期表仍是 2025 年的日期，和同页 Fall 2027 的内容并存。
   - WashU pg-0065 有上一申请季的"October 2026 Start"延期入学信息。
   - WashU pg-0068 写"candidates starting in Spring 2026"，但这个项目只有秋季入学。
2. **需要检测页面之间、页面内部的冲突，单一页面不能全信**：
   - BU：首页列 6 轮截止日期，申请页列 5 轮；学制写 9/12/16 个月和 12/16 个月两种；申请页底部有"January 7, 2026"的笔误；同一页上托福要求写了 90 和 95 两个数。
   - JHU Carey：项目页（pg-0061）混入了其他项目（MBA/BS in Engineering 双学位）的申请要求，以及 Fall 2026 的旧截止日期，和 How to apply 页（pg-0062）矛盾；关于 GMAT/GRE，一个说必需，一个说可选。
3. **截止日期有多个来源**：UTD 商学院页有一套，研究生院的提前截止和常规截止又是两张表。这呼应 02 §7"研究生院页与系页冲突"的待定规则，**P4 需要定一个优先顺序**。
4. **面授版和线上版写在同一页面上**：UChicago 面授版有 6 轮截止（含国际学生 1 月 26 日），线上版只有 6 月 23 日一轮。抽取时**必须遵守 `program_pages.scope_note`**。
5. **页面受众判断容易出错**：Columbia 的 `/ma-student-faqs/` 是给在读学生的 FAQ，不是招生 FAQ。UW 经济系的硕士申请页和 FAQ 属于另一个经济学硕士项目。标题相近的页面需要人工区分。
6. **IPEDS 授予数可能来自已经改名或停办的旧项目**：UW-Madison 45.0603 在 2023-24 学年有 147 个学位，但现在的 MSQE 是新项目。候选清单的授予数只能作为参考。
7. **学校会改版、改域名**：Columbia DS 改版后旧网址跳转、Admissions 子页 404；UConn 的 msbapm 子站整体并入 analytics 子站；WashU Olin 从 olin.wustl.edu 迁到 olin.washu.edu，旧网址跳到通用列表页（状态码 200，实际是失效）。这说明 **P3 的变化检测必须能处理"跳转到不同页面"**（06 §4.4 的 `redirected_other`）。

---

## 7. 剩余 80 个项目的建议做法

还需要补的名额（目标数减去试点数）：ds 21、analytics 20、stats 16、mgmt_sci 16、econ 6，合计 79。试点中平均每个候选行产生约 1.1 个 selected 项目，所以主批次大约需要 70–80 个候选行。

1. **先按学校预筛抓取可行性**：robots.txt 和使用条款是按域名或按学校定的。挑选候选行时，先看工作表里这所学校是否已知被拦截（目前已知 Columbia、NYU、UIUC、USC、JHU、Rochester），再决定是否接受较高比例的 manual 项目。建议在工作表中加一列"已知抓取状况"，这需要改 06 §7。
2. **按学校批量处理**：同一所学校的研究生院页、学院招生页、条款页只需要查一次，可以同时服务多个项目。
3. **先查线上版和 MBA**：试点的 10 个排除项里有 8 个是线上版。每个候选行先搜"online"和"MBA"，能更早发现一行对应多个项目的情况。
4. **把临时脚本变成命令**：
   - 试点中项目记录是用临时 Python 脚本写进 `programs.csv` 的，没有对应的 CLI。建议增加 `registry add-program`，在写入时就检查候选行、`program_id` 格式和状态组合。
   - 核对清单 `review_pilot.md` 目前由我的临时脚本生成。建议改成 `registry review` 命令，把每页的"依据要点"存进一个不提交的备注文件。
   - 这两个命令在主批次开始前实现，**不阻塞 P3**。
5. **在提议阶段就跑 `check-urls`**：试点中改域名、失效、跳到不同页面的情况，都是负责人核对之前由 `check-urls` 发现的。主批次每一批提议后先运行它，可以减少负责人点开失效网址的次数。
6. **复用已确认的共用页面**：学院层级的招生页和截止日期页，在同校新项目中优先复用；如果不适用（比如属于另一个项目），在 `scope_note` 中写明。
7. **manual 项目的人工取得流程在 P3 设计**：主批次照常把 `fetch_method` 设为 manual，不因此排除项目。第 5.3 节的学位目录可以作为部分字段的补充来源，届时再评估。

---

## 8. 本阶段的规则与工具变更（都已提交）

| 变更 | spec |
|---|---|
| 申请入口的定义（在申请系统中是独立的项目选项，就是不同项目） | 06 §2.1 |
| 页面登记规则：每个页面类型只登记一个规范网址；不借用其他项目（含线上版）的页面；hybrid 的定义 | 06 §2.7 |
| `program_pages.scope_note`；`exclusion_reason = not_admitting` | 06 §3.1、§3.3 |
| `fetch_method`（auto / manual） | 06 §3.1、§5.2 |
| `check-urls`：`robots_unavailable`、`redirected_other`、`--page` | 06 §4.4 |
| 准入检查：把 HTTP 403 算作不可抓取，区分 robots.txt 无法读取和明确禁止 | 06 §5.2 |
| 学费只记国际学生适用的金额；02 §7 关闭两项；全量重抽日期暂定 8 月 15 日 | 02、05 |
| IPEDS 和 Scorecard 的期望值按数据版本锁定 | 01 §8 |
