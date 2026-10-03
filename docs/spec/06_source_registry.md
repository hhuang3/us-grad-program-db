# 06 来源登记表（Phase 2）

> 状态：v1.1（Phase 2a，2026-10-01 逐项确认）。原先标为待确认的补充设计均已确认；第 7 项（抓取许可的粒度）与第 9 项（MBA 匹配）按答复修订。
> 登记表是 Phase 3 抓取的**唯一输入**。本阶段不抓取项目页面内容；唯一允许访问大学网站的操作是读取 `robots.txt`，以及你明确要求时用搜索引擎查找候选 URL。

---

## 1. 分工

| 谁 | 做什么 |
|---|---|
| Claude Code | 设计登记表结构、写校验、生成挑选工作表、检查 robots.txt、在你要求时提议候选 URL（`url_status = proposed`） |
| 你 | 决定挑哪些项目、确认每一个 URL（改为 `confirmed`）、判断使用条款（填写 `tos_status`） |

不自动决定选入或排除任何项目，不判断使用条款是否允许抓取。

---

## 2. 规则

### 2.1 项目的定义

- **一个申请入口 = 一个 `program_id`**。同一学位下的 track / concentration：共用同一个申请入口的，算一个项目；分别申请、要求不同的，拆成多个项目。（同时关闭 02 §7 第 3 项）
- **“申请入口”的判定**（2026-10-02 确认）：在学校申请系统中是**独立的项目选项**（各自录取、各自要求）的，即为不同项目；在同一项目选项下选择方向（track / concentration）或上课方式（面授 / 线上），或入学后再选择的，算**一个**项目。
- 一个候选行（`unitid × cip_code`）可以对应 0 个、1 个或多个项目；一个项目只对应一个候选行。
- **“0 个项目”也要留记录**：候选行经检查确实找不到对应的硕士项目时，登记一行 `status = excluded`、`exclusion_reason = not_found` 的占位记录，用来表明“查过了”。占位记录的规则：
  - `program_id` = `{学校简称}-none-{CIP 去掉点}`，如 `meharry-none-307099`；
  - `program_name`、`degree_type`、`department` 可以为空，`delivery_mode = unknown`；
  - 其他 `exclusion_reason` 的行，`program_name` 和 `degree_type` 都必须填写。

### 2.2 纳入与排除

| 情况 | 处理 | `exclusion_reason` |
|---|---|---|
| 学位不是硕士（MS / MA / MPS / MEng / MSc 等） | 排除 | `out_of_scope` |
| **MBA**：包括 STEM MBA，以及以 MBA 为主体、附加 analytics 方向的学位 | **一律排除** | `mba` |
| **纯线上项目**（通常不能办 F-1） | 排除 | `online_only` |
| 授课形式判断不了 | **不排除**，`delivery_mode = unknown`，留待你确认 | – |
| 证书项目（certificate） | 排除 | `certificate` |
| 双学位中的非独立部分 | 排除 | `out_of_scope` |
| 与已登记项目重复 | 排除 | `duplicate` |
| 查不到对应项目 | 排除（占位记录，见 2.1） | `not_found` |
| 停招（含暂停招生） | 排除，`selection_note` 中写明依据和起始学期（2026-10-03 新增） | `not_admitting` |
| 其他 | 排除，`selection_note` 中写明 | `other` |

只收 `delivery_mode ∈ {on_campus, hybrid}` 的项目；`unknown` 可以先选入，但进入 Phase 3 前必须确认（见 §5.2）。

### 2.3 名额（第一版目标）

| 组 | 名额 |
|---|---|
| ds | 25 |
| analytics | 25 |
| stats | 20 |
| mgmt_sci | 20 |
| econ | 10 |
| **合计** | **100** |

名额是目标值，最终数量以你的确认为准。校验只**报告**各组 selected 数量与名额的差距，不报错。

### 2.4 挑选工作表的排序

- 组内按 `completions_masters_nonresident` **降序**，并列时按 `completions_masters` 降序，再并列时按 `unitid` 升序（按整数比较）、`cip_code` 升序。
- 这只是工作表的展示顺序，不是自动挑选规则。

### 2.5 试点批次

- 先完成 **20 个项目**（每组 4 个，`batch = pilot`）。登记表通过 Phase 3 就绪校验（§5.2）后，Phase 3 即可开始；其余 80 个（`batch = main`）随后补齐。
- 你选出的是 20 个**候选行**，而一个候选行可能对应 0 个或多个项目，所以 pilot 的项目数不一定正好是 20。每组凑满 4 个 selected 项目为准：不足时从工作表中补候选行，超出时由你决定哪些进入 pilot、哪些放到 main。

### 2.6 02 §7 其余待定项的处理

| 待定项 | 处理 |
|---|---|
| 研究生院页与系页数值冲突 | P2 只要求**两个页面都登记**（用 `owner_level` 区分），优先规则在 P4 决定 |
| 学费是否区分州内/州外 | 只记录国际学生适用的金额（公立校即州外学费）。已写入 02 |
| track / concentration 是否拆分 | 按 2.1 处理，已关闭 |
| 全量重抽日期（05 §5） | 暂定每年 **8 月 15 日**，已写入 05，可在 P4 调整 |

### 2.7 页面登记规则（2026-10-02 确认）

1. **一个规范网址**：同一项目、同一 `page_type` 只登记一个规范网址。指向同一内容的其他网址（别名、旧路径、门户站的介绍页等）不登记。
   **选法**：优先选学校招生流程实际链接到的页面，例如申请系统中的 Apply 链接、研究生院项目目录中的项目链接（2026-10-02 确认）。
2. **不借用其他项目的页面**：不得把其他项目的页面登记给本项目，**包括同一项目的线上版**。例如线上版专用的 admissions 页不能用于住校版。只有面向多个项目的共用页面（如研究生院统一的国际学生要求页、学院统一的申请页）可以由多个项目共用，并按其层级填写 `owner_level`。
3. **`hybrid` 的定义**：项目可以完全在校面授完成，同时提供线上课程或线上完成的选项。只能线上完成的是 `online`；只有面授的是 `on_campus`。

---

## 3. 登记表结构

所有表放在 `data/registry/`，CSV，UTF-8（无 BOM），`\n` 换行，**全部列按字符串读取**（`keep_default_na=False`）。日期为 `YYYY-MM-DD`，时间为 UTC `YYYY-MM-DDTHH:MM:SSZ`。

**行不删除**：不再需要的项目改为 `status = excluded`；页面和域名即使不再被引用也保留。这样 `program_id`、`page_id` 永远不会消失或被复用（§5.1 校验）。

### 3.1 `programs.csv`

| 列 | 含义 | 取值 / 规则 |
|---|---|---|
| `program_id` | 主键 | slug，见下；全表唯一；确定后不再改 |
| `unitid` | IPEDS 机构 ID | 与 `cip_code` 一起必须构成 `data/ref/candidates.csv` 中的一行 |
| `cip_code` | 对应的候选 CIP | `"NN.NNNN"` |
| `cip_group` | 组 | 必须等于 candidates.csv 中该行的 `cip_group` |
| `institution_name` | 校名 | 必须等于 candidates.csv 中该行的 `institution_name` |
| `program_name` | 官方项目名 | 原样；占位记录可空（2.1） |
| `degree_type` | 学位 | `ms / ma / mps / meng / msc / other`；占位记录可空 |
| `department` | 院系 | 原样；可空 |
| `delivery_mode` | 授课形式（初步判断） | `on_campus / hybrid / online / unknown` |
| `status` | 状态 | `selected / excluded / backlog` |
| `exclusion_reason` | 排除原因 | `mba / online_only / certificate / out_of_scope / duplicate / not_found / not_admitting / other`；`status = excluded` 时必填，否则必须为空 |
| `selection_note` | 选入或排除的理由 | 自由文本；`status ∈ {selected, excluded}` 时必填 |
| `batch` | 批次 | `pilot / main` |
| `fetch_method` | Phase 3 取得页面的方式（2026-10-03 新增） | `auto / manual`；`status = selected` 时必填，其他状态必须为空。`auto`：由抓取器自动抓取；`manual`：页面无法自动抓取（条款、robots.txt 或网站防护），由人工取得，具体流程在 P3 设计 |
| `added_at` | 登记日期 | `YYYY-MM-DD` |

**`program_id` 格式**：`{学校简称}-{学位}-{方向}`，如 `uwmadison-ms-statistics`。
- 正则：`^[a-z0-9]+(-[a-z0-9]+){2,}$`（全小写 ASCII 字母和数字，用 `-` 分隔，至少 3 段）。
- 第 2 段必须等于 `degree_type`；占位记录为 `none`。

### 3.2 `pages.csv`

| 列 | 含义 | 取值 / 规则 |
|---|---|---|
| `page_id` | 主键 | `pg-` 加 4 位以上的流水号（如 `pg-0001`），由 `gradprog registry add-page` 分配：取现有最大号 + 1；确定后不再改 |
| `url` | 页面 URL | 必须是 `https`；必须已经是规范形式（§3.5）；全表唯一 |
| `domain` | 域名 | 由 `url` 导出（§3.5）；必须存在于 domains.csv |
| `page_type` | 页面类型 | `program_home / admissions / deadlines / requirements / tuition / funding / faq / grad_school_intl / isso_stem_list / other` |
| `owner_level` | 页面所属层级 | `program / department / graduate_school / university` |
| `url_status` | URL 状态 | `proposed`（Claude Code 提议）/ `confirmed`（你已确认） |
| `content_format` | 内容格式 | `html / pdf` |
| `robots_allowed` | robots.txt 是否允许抓取本页 | `yes / no / not_checked`；由 `check-robots` 写入，新页面为 `not_checked` |
| `crawl_allowed` | 是否允许 Phase 3 抓取本页 | **导出列**，`true / false`，规则见 §4.3 |
| `added_at` | 登记日期 | `YYYY-MM-DD` |

用流水号而不用 URL 的 hash，是为了在 URL 变化（学校改版、重定向）时保持 `page_id` 不变，Phase 3 的快照历史才能连续。

### 3.3 `program_pages.csv`（多对多）

| 列 | 含义 |
|---|---|
| `program_id` | 关联 programs.csv |
| `page_id` | 关联 pages.csv |
| `scope_note` | 可空。该页面对**这个项目**的适用范围说明，单行文本（不含换行）。例如共用页面同时包含其他版本的内容时写明“页面同时包含线上版内容，抽取时只取面授版”。Phase 3/4 抽取时按此说明限定范围（2026-10-02 新增） |

`(program_id, page_id)` 组合唯一（与 `scope_note` 无关）。一个页面可以服务多个项目（例如研究生院统一的国际学生语言要求页）。

### 3.4 `domains.csv`（每个域名检查一次）

| 列 | 含义 | 取值 / 规则 |
|---|---|---|
| `domain` | 主键 | 小写主机名，如 `grad.wisc.edu` |
| `robots_url` | robots.txt 地址 | `https://{domain}/robots.txt` |
| `robots_checked_at` | 检查时间 | UTC ISO 8601；未检查时为空 |
| `robots_status` | 结果 | `fetched / not_found / error`；未检查时为空 |
| `robots_allows_registered_paths` | 汇总：该域名下已登记页面的 `robots_allowed` | `yes / no / partial / no_pages`；未检查时为空 |
| `tos_url` | 使用条款页面 | 可空；Claude Code 找到后填入 |
| `tos_status` | 条款判断（由你填写） | `no_restriction / prohibits_automated_access / unclear / not_checked`；新域名默认 `not_checked` |
| `tos_note` | 备注 | 可空 |

两层判断：**使用条款按域名**（`tos_status`），**robots 按页面**（pages.csv 的 `robots_allowed`）。抓取许可 `crawl_allowed` 在 pages.csv 中按页面给出（§4.3）。

### 3.5 URL 规范化与域名导出

`normalize_url(url) -> str`，以下规则依次执行：

1. 去掉首尾空白。scheme 必须是 `https`，否则报错（`http` **不自动升级**，要人工确认 https 版本可用）。
2. 主机名转小写；去掉末尾的 `.`；去掉默认端口 `:443`；带用户名或密码的 URL 报错。
3. 去掉锚点（`#…`）。
4. 删除跟踪参数：`utm_*`（任何以 `utm_` 开头的参数）、`gclid`、`fbclid`、`msclkid`、`mc_cid`、`mc_eid`、`_ga`、`_gl`、`hsa_*`。比较参数名时不区分大小写。其他参数**保留原顺序和原值**；删完后没有参数就去掉 `?`。
5. 路径为空时补成 `/`。路径的大小写和末尾的 `/` **保持原样**（同一站点上它们可能指向不同页面，不猜）。
6. 不做百分号编码的重新编码。

- `domain_of(url)` = 规范化后 URL 的主机名。
- 存进 pages.csv 的 `url` 必须等于 `normalize_url(url)`，否则校验报错。

---

## 4. robots.txt 与抓取许可

### 4.1 `gradprog registry check-robots`

- 对 domains.csv 中的每个域名请求 `robots_url`。单线程，每个请求间隔 ≥ 3 秒，User-Agent 与 Phase 1 下载器相同：`gradprog-refdata/<版本> (+mailto:<GRADPROG_CONTACT_EMAIL>)`。环境变量未设置则拒绝运行。
- 用 Python 标准库 `urllib.robotparser.RobotFileParser`（`parse()` 读入内容）判断。判断时使用的 user-agent 标记是 `gradprog-refdata`。

| HTTP 结果 | `robots_status` | 判断方式 |
|---|---|---|
| 2xx | `fetched` | 对该域名下每个已登记页面 URL 调用 `can_fetch` |
| 404 / 410 | `not_found` | 按惯例视为全部允许 |
| 401 / 403 | `error` | 视为全部禁止（保守） |
| 其他 4xx、5xx、网络错误、超时 | `error` | 视为全部禁止（保守） |

RFC 9309 规定其他 4xx 视为“可以抓取”，`urllib.robotparser` 也是这样处理的。这里刻意更保守：只有 404/410 视为允许，其余 4xx 一律按禁止处理（2026-10-01 确认）。

区分两种“不允许”（2026-10-03 确认）：`robots_status = error` 表示 **robots.txt 本身无法读取**（4xx 中除 404/410 外、5xx、网络错误），与 `fetched` 后 robots.txt **明确禁止**不同。两者在抓取许可上同样视为不允许（`robots_allowed = no`），但在命令输出和报告中分开显示。

- 每个已登记页面的 `robots_allowed`（写回 pages.csv）：
  - `fetched`：`can_fetch("gradprog-refdata", url)` 为真 → `yes`，否则 → `no`；
  - `not_found` → `yes`；`error` → `no`。
- 域名汇总 `robots_allows_registered_paths`（写回 domains.csv）：该域名下已登记页面全部 `yes` → `yes`；全部 `no` → `no`；有 `yes` 也有 `no` → `partial`。该域名下没有已登记页面时 → `no_pages`（2026-10-01 确认，不记为 `yes`）。
- 同时写回 `robots_checked_at`、`robots_status`，并重算 pages.csv 的 `crawl_allowed`。robots.txt 的内容**不保存**。
- 检查之后再登记的新页面，`robots_allowed = not_checked`，`crawl_allowed = false`，直到下次运行 `check-robots`。
- 重定向：跟随（最多 5 次）。最终落在其他域名时，仍按最终响应判断，并把重定向信息打印到命令输出，不写进表里。

### 4.2 `gradprog registry derive`

重新计算所有导出列：pages.csv 的 `domain` 和 `crawl_allowed`，并为 pages.csv 中出现、但 domains.csv 中没有的域名补一行（`robots_url` 按 §3.4 生成，`tos_status = not_checked`，其余为空）。不改 `robots_allowed`（只有 `check-robots` 写它）。你修改 `tos_status` 之后运行一次即可。`validate` 只检查、不改表。

### 4.3 `crawl_allowed` 的推导（按页面）

pages.csv 中某页 `crawl_allowed = true` 当且仅当：
- 该页 `robots_allowed = yes`，**且**
- 该页所属域名的 `tos_status = no_restriction`。

其余一律 `false`（包括 `not_checked`、`no`、`unclear`、`prohibits_automated_access`）。domains.csv 不再有 `crawl_allowed`；`robots_allows_registered_paths` 只是汇总，不参与推导。

### 4.4 `gradprog registry check-urls`（2026-10-03 新增）

目的：在你核对之前，先把失效网址和旧网址找出来。**只记录状态，不保存页面内容，不修改 pages.csv**。

- 对象：pages.csv 中 `url_status = proposed` 的页面（`confirmed` 的不检查）。可以用 `--page pg-0021 --page pg-0023 …` 只检查指定页面（仍然只限 proposed）；指定了不存在或非 proposed 的 page_id 时报错。
- 只检查部分页面时，`url_check.csv` 中这些页面的行被替换，其他页面的行保留。
- 礼貌规则与 §4.1 相同：单线程，所有请求（含 robots.txt）之间间隔 ≥ 3 秒，User-Agent 与 Phase 1 下载器相同，未设置 `GRADPROG_CONTACT_EMAIL` 则拒绝运行。
- **先遵守 robots.txt**：对涉及的每个域名先读一次 robots.txt，按 §4.1 的规则判断（含 404/410 视为允许、其他错误视为禁止）。被禁止的页面**不请求**，结果记为 `robots_disallowed`。
- 请求方式：`GET`，跟随重定向（最多 5 次），**不读取响应正文**（流式请求，只取状态码和最终 URL 后立即关闭）。超时 120 秒。
- 结果分类（按顺序取第一个成立的）：

| result | 条件 | 核对清单中的标注 |
|---|---|---|
| `robots_unavailable` | robots.txt 本身无法读取（§4.1 的 `error`：除 404/410 外的 4xx、5xx、网络错误） | robots.txt 无法读取，未请求 |
| `robots_disallowed` | robots.txt 已读取且明确禁止该页 | robots 禁止，未请求 |
| `broken` | 最终状态码 404 或 410 | **失效** |
| `error` | 其他非 2xx 状态码、网络错误、超时、重定向次数超限 | 请求失败（附状态码或错误类型） |
| `redirected_other` | 2xx，最终 URL 与登记的 url 不同，且最终页面明显不是同一页面（规则见下） | **跳转到不同页面，需人工确认**（不建议直接改用） |
| `redirected` | 2xx，且 `normalize_url(最终 URL) ≠ 登记的 url`（最终 URL 无法规范化时也算） | **已跳转，建议改用最终网址** |
| `ok` | 2xx，且最终 URL 规范化后等于登记的 url | 正常 |

- “明显不是同一页面”（`redirected_other`，2026-10-03 新增），满足任一条即是：
  1. 登记的路径不是 `/`，而最终路径是 `/`（跳到首页）；
  2. 最终路径的最后一段是 `index.*`、`default.*` 或 `home.*`，且去掉这一段后最多只剩 1 级目录（如 `/index.php`、`/programs/index.php`，即站点或栏目的列表页）；
  3. 最终 URL 的查询参数中有名称包含 `redirect` 的参数（不区分大小写，如 `redirectid=103`）。
  实例：WashU Olin 旧网址跳到 `olin.washu.edu/programs/index.php?redirectid=103`（通用项目列表，HTTP 200）。
- 输出：`data/registry/url_check.csv`（不提交进 git），列为 `page_id, url, result, http_status, final_url, checked_at`；`http_status` 在未请求或网络错误时为空，`final_url` 只在发生跳转时填写。按 `page_id` 排序。
- 核对清单 `review_pilot.md` 读取 `url_check.csv`，在每个页面旁标注上表的结果。
- 是否改用最终网址、是否删除失效页面，由你决定；命令本身不改任何登记表。

---

## 5. 校验（`gradprog registry validate`）

一次性列出全部问题，分为 **error**（返回码非 0）和 **warning**（只提示）。

### 5.1 结构校验（始终执行，全部为 error）

- 4 张表的列名和列顺序与 §3 完全一致。
- 主键唯一：`programs.program_id`、`pages.page_id`、`pages.url`、`domains.domain`、`program_pages` 的 `(program_id, page_id)`。
- 外键：
  - `(unitid, cip_code)` ∈ candidates.csv；`cip_group`、`institution_name` 与 candidates.csv 一致；
  - `pages.domain` ∈ domains.csv；
  - program_pages 的两端都存在。
- `program_pages.scope_note` 不得包含换行符。
- 枚举值合法；日期、时间格式合法。
- `status` 与 `exclusion_reason`、`selection_note` 的组合合法（§3.1）。
- `program_id` 格式合法（§3.1）；占位记录规则（§2.1）。
- `url` 为 https 且等于 `normalize_url(url)`；`domain = domain_of(url)`；`page_id` 格式合法。
- 枚举：`robots_allowed ∈ {yes, no, not_checked}`，`crawl_allowed ∈ {true, false}`。
- 导出列不过期：pages.csv 的 `crawl_allowed` 等于 §4.3 的推导结果（过期时提示运行 `registry derive`）。
- 不删除：与 git `HEAD` 中已提交的登记表相比，已有的 `program_id`、`page_id`、`domain` 不能消失；已有 `page_id` 对应的 `added_at` 不能改变。
  - **首次提交**：HEAD 中还没有某张登记表（`git show HEAD:<path>` 失败）时，跳过该表的这项检查，校验照常通过。有对应测试。
  - 不在 git 仓库中、或找不到 git 时：同样跳过，并给出一条 warning。

### 5.2 `status = selected` 的项目

| 检查 | 默认 | `--ready` 模式 |
|---|---|---|
| `delivery_mode ≠ online` | error | error |
| `delivery_mode = unknown` | warning | error |
| `program_name` 或 `degree_type` 疑似 MBA：大小写不敏感地匹配 `\bMBA\b`、`M.B.A.`（带句点，末尾句点可省略）或 `master of business administration` | warning（由你确认） | warning |
| 至少关联一个 `page_type = program_home` 页面，以及一个 `admissions` 或 `requirements` 页面 | error | error |
| 所有关联页面 `url_status = confirmed` | warning | error |
| 关联页面中“不可抓取”的（见下） | – | **列出报告**（页面、所属域名、原因） |
| `fetch_method` 为空 | error | error |
| `fetch_method = auto`：关联的 `program_home` 页面可抓取 | – | error |
| `fetch_method = manual`：不要求可抓取（仍要求页面全部 `confirmed`） | – | 在报告中单独列出（`ready_manual_programs`） |

`--ready --batch pilot` 是 Phase 3 的准入检查：只检查 `batch = pilot` 的 selected 项目。2d 过程中允许出现 proposed 页面（只给 warning），否则提议阶段就无法通过校验。

**“可抓取”**（准入检查与报告使用，2026-10-03 修订）：`crawl_allowed = true`，**且**该页在 `data/registry/url_check.csv` 中最近一次的检查结果不是 HTTP 403（`result = error` 且 `http_status = 403`，即网站防护拦截）。`url_check.csv` 不存在时无法判断网站防护，给出一条 warning，只按 `crawl_allowed` 判断。

“不可抓取”的原因按以下顺序取第一个成立的：
1. `robots_allowed = not_checked` → `not_checked`（未检查）
2. `robots_allowed = no` 且所属域名 `robots_status = error` → `robots_unavailable`（robots.txt 无法读取）
3. `robots_allowed = no` → `robots_disallowed`（robots.txt 明确禁止）
4. `tos_status ≠ no_restriction` → `tos`（条款）
5. url_check 中最近一次为 HTTP 403 → `site_blocked_403`（网站防护 403）

### 5.3 报告（不报错）

- 各组 selected 数量与 §2.3 名额的对比（含 pilot / main 分开计数）。
- 各组 selected / excluded / backlog 数量；各 `exclusion_reason` 的数量。
- `crawl_allowed = false` 的页面清单，以及原因（未检查 / robots / tos）；`tos_status ≠ no_restriction` 的域名清单。
- 被多个项目共用的页面数，以及 `owner_level = graduate_school` 的页面数。

---

## 6. 命令一览

| 命令 | 作用 |
|---|---|
| `gradprog registry init` | 建立 4 张空表（只有表头）；已存在则报错，不覆盖 |
| `gradprog registry worksheet` | 从 candidates.csv 生成 `data/registry/selection_worksheet.csv`（§7） |
| `gradprog registry add-page` | 登记一个页面：规范化 URL、分配 `page_id`、导出 `domain`、需要时补 domains 行、写入 program_pages 关联 |
| `gradprog registry derive` | 重算导出列（§4.2） |
| `gradprog registry check-robots` | §4.1 |
| `gradprog registry check-urls` | §4.4：检查 proposed 页面的状态码与跳转，写 `url_check.csv`，不改登记表 |
| `gradprog registry validate [--ready --batch pilot]` | §5 |

---

## 7. 挑选工作表 `selection_worksheet.csv`

- 输入：`data/ref/candidates.csv`。
- 每个候选行一行，按 §2.4 排序。列：
  `cip_group, worksheet_rank, unitid, institution_name, state, cip_code, cip_title, on_stem_list, completions_masters_nonresident, completions_masters, institution_group_count, decision, note`
  - `worksheet_rank`：组内按 §2.4 排序后从 1 开始的序号。
  - `institution_group_count`：该校在 candidates.csv 中出现在几个不同的 `cip_group`（1–5）。
  - `decision`、`note`：留空，给你填写（例如 `pilot` / `main` / `skip`）。
- 这份工作表**不是校验输入**，`validate` 不读它。
- 已存在时拒绝覆盖（防止你填写的内容丢失），需要 `--force` 才覆盖。
- 生成结果是确定的（同样的 candidates.csv → 逐字节相同的文件）。
