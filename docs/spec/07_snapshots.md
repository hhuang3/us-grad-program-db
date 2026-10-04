# 07 快照与变化检测（Phase 3）

> 状态：v1.1（Phase 3a，2026-10-04 逐项确认）。原先标为待确认的设计均已确认；链接发现范围（§8）与条款受限域名的发布限制（§1）按答复修订。
> 本文件定义 05 数据模型的第一层 **snapshot**。不抽取字段，不判断申请季。P4 只处理分类为 `first_capture` 和 `changed` 的快照。

---

## 1. 原则

- **不绕过任何访问限制**（00 §6）：不伪装成浏览器，不执行 JavaScript 挑战，不使用无头浏览器，不轮换 IP。被拦截就记为被拦截。
- **条款受限域名的发布限制**（2026-10-04 确认）：`tos_status` 为 `prohibits_automated_access` 或 `unclear` 的域名，其页面信息在 P5 对外发布前，由负责人另行决定呈现方式（例如只给官网链接、请求许可或不发布）。P3、P4 照常保存与抽取，**仅限内部使用**。
- **包含页面正文的文件一律不进 git**（raw、normalized、diffs、运行报告、manual-due），只在本地保存。进 git 的只有元数据（`index.csv`、`runs.csv`），而且元数据中不得含有页面正文。
- **原始文件原样保存、不修改**；规范化和比较都可以由原始文件重新算出（§6.4）。

## 2. 已决定的事项

| 事项 | 决定 |
|---|---|
| 人工取得的格式 | Chrome“另存为 → 网页，单个文件（.mhtml）”；页面本身是 PDF 时接受 .pdf |
| 抓取频率 | 自动：每周一次。人工：距上次取得 ≥ 14 天即列为“待取得” |
| 定时运行 | 你的 Mac 上的 launchd，不用云服务器 |
| 快照存放 | 本地，不进 git；另提供备份命令，目的地由你指定 |
| JavaScript 渲染 | 不做，只取服务器直接返回的内容 |

## 3. 哪些页面自动抓取，哪些人工取得（按页面决定，2026-10-04 确认）

指令有两处说法不一致：§4.1 说自动抓取的对象是“`fetch_method=auto` 且 `crawl_allowed=true`”，而背景中给出的数字是 auto 39 页、manual 24 页。按项目的 `fetch_method` 划分，实际是 **auto 38 页、manual 25 页**。差别在 **pg-0006**（NYU GSAS 的项目页）：它可以抓取，但它所属的 NYU MS DS 是 manual 项目。

**按页面决定取得方式**，结果是自动 39 页、人工 24 页；同一项目可以同时有两种页面：

- **自动抓取**：页面“可抓取”，即 `crawl_allowed = true`，**且**不在 `url_check.csv` 最近一次为 HTTP 403 的名单中（06 §5.2 的定义），**且**至少关联一个 `status = selected` 的项目。项目的 `fetch_method` 不影响页面能否自动抓取。
- **人工取得**：关联 `fetch_method = manual` 的项目、且**不可抓取**的页面。
- 关联 `fetch_method = auto` 项目、但**不可抓取**的页面（例如 robots 未检查或条款不明的非首页页面）：两边都不纳入，在每次运行报告中列为“未纳入取得”，建议运行 `registry check-robots` 或把项目改为 manual（2026-10-04 补充）。
- 一个页面不会同时出现在两边；同一项目的页面可以分属两边（例如 NYU MS DS 的 pg-0006 自动抓取，其余 3 页人工取得）。`fetch_method` 继续表示“项目的首页能否自动抓取”（06 §3.1），不改它的定义。

## 4. 存储结构

### 4.1 目录

```
data/snapshots/
├── raw/<page_id>/<snapshot_id>.<ext>                 # 原始文件，原样保存（gitignore）；ext = html / pdf / mhtml
├── normalized/<page_id>/<snapshot_id>.v<N>.txt       # 规范化正文（gitignore）；文件名带 normalizer_version
├── diffs/<page_id>/<snapshot_id>.v<N>.diff           # 与上一版的差异（gitignore）；同上
├── reports/run-<run_id>.md                           # 运行报告（gitignore）
├── manual_due.md                                     # 人工待办（gitignore）
├── index.csv                                         # 快照索引（提交进 git）
└── runs.csv                                          # 运行汇总（提交进 git）
```

normalized 和 diffs 的文件名带上规范化程序的版本号 `v<N>`：重新规范化（§6.4）时生成新文件，不覆盖旧文件，旧行仍然可以追溯到它当时的结果。

### 4.2 `index.csv`（只追加，不修改，不删除）

| 列 | 含义 |
|---|---|
| `snapshot_id` | `snap-<UTC 时间 YYYYMMDDTHHMMSSZ>-<page_id>`。时间取取得时间 `retrieved_at` |
| `page_id` | 关联 pages.csv |
| `run_id` | 所属运行，见 §4.3 |
| `method` | `auto / manual` |
| `retrieved_at` | UTC `YYYY-MM-DDTHH:MM:SSZ`；人工登记的规则见 §5.2 |
| `requested_url` | 请求或登记时 pages.csv 中的 URL |
| `final_url` | 跟随跳转后的最终 URL；人工取得时取 MHTML 头里的地址；PDF 人工登记时等于 `requested_url` |
| `http_status` | 自动抓取的最终状态码；网络错误时为空；人工为空 |
| `content_type` | `html / pdf / mhtml`；没有取得内容时为空 |
| `raw_sha256`、`raw_bytes` | 原始文件；没有保存原始文件时为空 |
| `normalizer_version` | 规范化程序版本号（整数）；没有规范化时为空 |
| `norm_sha256`、`norm_chars` | 规范化正文的哈希与字符数；取得失败时为空 |
| `classification` | 见 §7 |
| `prev_snapshot_id` | 用于比较的上一版（§7.2）；没有可比较的上一版时为空 |
| `added_lines`、`removed_lines` | 与上一版相比增删的行数（只有 `changed` / `suspected_redesign` 时填写）。指令要求报告写增删行数，这两个数放进索引，报告就能由索引生成 |
| `note` | 自由文本，**不得含页面正文**；固定标记有 `time_unknown`、`retrieved_at_from_mtime`、`renormalized`、`redirected`（见 §7.1），以及 `charset=<名称>`：自动抓取的 HTML 在 HTTP 头中声明了字符集时记录下来，重新规范化（§6.4）时按它解码，保证结果一致（2026-10-04 补充）。多个标记用 `; ` 分隔 |

- **键**：`(snapshot_id, normalizer_version)` 唯一。同一个原始快照在重新规范化后会出现第二行，两行的 `snapshot_id` 相同、`normalizer_version` 不同（§6.4）。
- 同一页面同一秒内出现两次取得时，`snapshot_id` 会重复，这时报错，不写入。
- 写入方式：以**追加模式**打开文件写入新行（UTF-8、`\n`），从不重写整个文件，所以已有行不会被改动。文件不存在时先写表头。表头和 §4.2 的列不一致时报错，拒绝写入。

### 4.3 `runs.csv`（每次运行一行）

| 列 | 含义 |
|---|---|
| `run_id` | `run-<开始时间 UTC YYYYMMDDTHHMMSSZ>-<auto/manual/renormalize>` |
| `method` | `auto / manual / renormalize` |
| `started_at`、`finished_at` | UTC |
| `first_capture` … `fetch_error` | 7 种分类各自的数量（7 列） |
| `anomaly_page_ids` | 异常页面（§7.1 中“进异常清单”的分类），按 page_id 排序，用 `;` 连接 |

- 人工登记一批文件（一次 `register-manual` 调用）算一次运行。
- `--dry-run` 不产生运行记录，也不写 index.csv。

## 5. 取得

### 5.1 自动抓取 `gradprog snapshot run`

- 对象：§3 中“自动抓取”的页面。`--page <page_id>`（可重复）只抓指定的页面（仍然必须属于自动抓取对象）；`--dry-run` 只列出将要请求的页面和它们的 robots.txt 地址，不发任何请求。
- 每次运行开始时，对涉及的每个域名重新读取一次 robots.txt（本次运行内缓存），判定规则同 06 §4.1：
  - 本次判定为禁止的页面 → `blocked`，不请求；
  - robots.txt 无法读取（06 §4.1 的 `error`）→ 该域名的页面都记为 `blocked`，不请求。
  - 运行**不修改**登记表（pages.csv、domains.csv）；robots 结果与登记表不一致时，在报告中建议运行 `gradprog registry check-robots`。
- 礼貌规则沿用 P1 下载器：User-Agent 相同，联系邮箱来自 `GRADPROG_CONTACT_EMAIL`（未设置则拒绝运行），单线程，所有请求（含 robots.txt）之间间隔 ≥ 3 秒。
- 跳转：最多跟随 5 次；记录 `final_url`；是否“跳转到不同页面”沿用 06 §4.4 的 `redirected_other` 规则。
- 超时 30 秒（连接与读取各 30 秒）。
- 大小上限：响应正文超过 10 MB（10 × 1024 × 1024 字节）即停止读取，记为 `fetch_error`，不保存原始文件。
- 只接受 HTML（`Content-Type` 为 `text/html` 或 `application/xhtml+xml`）和 PDF（`application/pdf`，或正文以 `%PDF-` 开头）；其他类型记为 `fetch_error`。
- 原始文件写入 `raw/` 后，再进行规范化、分类和写索引。写到一半失败时，不留下没有对应索引行的原始文件。

### 5.2 人工取得

**`gradprog snapshot manual-due`** → 生成 `data/snapshots/manual_due.md`：
- 列出 §3 中“人工取得”的页面里，距离上次**成功的**人工或自动取得 ≥ 14 天（按 `retrieved_at` 计算，以运行命令时的 UTC 日期为准）或从未取得过的页面。
- 列：page_id、项目、page_type、可点击的 URL、上次取得日期（没有则写“从未”）。按项目分组。末尾写待办总数。

**`gradprog snapshot register-manual --page <page_id> --file <路径> [--retrieved-at <时间>]`**：
- 接受 `.mhtml` 和 `.pdf`，其他扩展名报错。
- `.mhtml`：用标准库 `email` 解析，读取文件头中的 `Snapshot-Content-Location`；没有时，读主 HTML 部分的 `Content-Location`。两者都没有就报错。
  - 地址规范化（06 §3.5）后，必须等于该 page_id 登记的 URL，或等于该页面在 index.csv 中出现过的某个 `final_url`（“已知的跳转目标”）。不一致就报错，不登记。
  - 地址与登记的 URL 不同时（即保存的是跳转后的页面），`final_url` 记为该地址，note 加 `redirected`，与自动取得一致；报告中建议“确认后在登记表中改用最终网址”。
- **`--known-redirect <URL>`**（只能与 `--page`、`--file` 一起用；2026-10-05 补充）：网站把登记的网址跳转到新地址、而 index.csv 里还没有这个地址时，由所有者确认后用它把新地址加为该页面的已知跳转目标。
  - URL 必须能规范化（06 §3.5），且与登记 URL 属于同一个可注册域名（§8 的规则），否则报错。
  - 文件中的地址必须等于这个 URL（或原有的允许地址）。登记成功后该地址写进 index.csv 的 `final_url`，以后的登记（包括 `--from-dir`）自动认得它，不需要再给这个选项。
  - 不修改登记表（pages.csv）；改网址由所有者另行决定。
- `.pdf`：文件头必须是 `%PDF-`；没有地址可核对，以 `--page` 为准。
- 复制文件（不移动），写入 `raw/`，再规范化、比较、写索引。
- `--retrieved-at`：
  - `YYYY-MM-DDTHH:MM:SSZ`：照用。
  - 只给日期：记为当天 `00:00:00Z`，note 加 `time_unknown`。
  - 不给：用文件修改时间（转成 UTC，取到秒），note 加 `retrieved_at_from_mtime`。
- **`--from-dir <目录>`**（与 `--page`、`--file` 互斥）：
  - 处理目录中的全部 `.mhtml`，按文件里的地址自动匹配 page_id；匹配不上的全部列出来，不登记。
  - `.pdf` 没有地址，无法自动匹配，一律列出来要求用 `--page --file` 单独登记。
  - 有任何一个文件匹配到**非人工取得**的页面，也列出来，不登记。
  - `--retrieved-at` 对目录中所有文件生效；不给时每个文件各用自己的修改时间。

## 6. 规范化

### 6.1 库的选择

| 选项 | 优点 | 缺点 |
|---|---|---|
| trafilatura | 自动识别“正文”，省规则 | 启发式提取，可能把截止日期表、侧栏里的申请要求当成噪音丢掉；结果随库版本变化，较难解释 |
| selectolax | 很快 | API 较少，CSS 选择器支持比 soupsieve 弱 |
| **BeautifulSoup4 + lxml（推荐）** | 规则明确、可解释；soupsieve 支持完整的 CSS 选择器，方便写 §6.3 的按域名规则；能处理不规范的 HTML；确定性好 | 较慢，但页面只有几十个，可以忽略 |

推荐 **BeautifulSoup4 + lxml 解析器 + 明确规则**。宁可多留一些噪音，再按域名补规则，也不能让启发式提取悄悄丢掉申请要求。PDF 用已经在用的 pdfplumber。

### 6.2 处理步骤（`normalizer_version = 1`）

1. **取得 HTML**：
   - HTML：按 `Content-Type` 的 charset 解码；没有时按 `<meta charset>`；都没有时按 UTF-8，无法解码的字节替换为 U+FFFD。
   - MHTML：解出 `text/html` 主部分（与 `Snapshot-Content-Location` 对应的部分，没有对应时取第一个 `text/html` 部分），处理 quoted-printable 和 base64 编码。
   - PDF：用 pdfplumber 逐页 `extract_text()`，页与页之间用一个空行分隔；然后跳到第 5 步。
2. **只处理 `<body>`**：`<head>` 中的内容（`title`、`meta` 等）不进入正文；没有 `<body>` 时处理整个文档。
3. **删除元素**：
   - 标签：`script`、`style`、`noscript`、`template`、`svg`、`iframe`、`header`、`nav`、`footer`、`form`、HTML 注释。
   - ARIA 角色：`role` 为 `banner`、`navigation`、`contentinfo`、`search` 的元素。
   - **不按可见性删除任何元素**（2026-10-04 确认）：`aria-hidden="true"`、`hidden` 属性、内联 `display:none` 或 `visibility:hidden` 的元素一律保留。招生页常用折叠面板（accordion）收起 FAQ、申请要求和截止日期，收起的内容就是靠这些方式隐藏的；我们不执行 JavaScript，拿到的是全部收起的状态，按可见性删除会丢掉正文。只按结构删除（本步其余各条）。可见性造成的噪音，3e 按域名在 §6.3 的规则中处理。
   - Cookie 提示：`id` 或 `class` 中含有 `cookie`、`consent`、`gdpr`（不区分大小写）的元素。这是按名称猜的，误删时用 §6.3 的规则覆盖。
   - `config/normalize_rules.yaml` 中该域名的额外规则（§6.3）。
4. **转为文本**：
   - 块级元素（`p`、`div`、`li`、`h1`–`h6`、`section`、`article`、`br`、`dt`、`dd` 等）前后换行。
   - 表格：每个 `<tr>` 一行，单元格按文档顺序用 ` | ` 连接，保留单元格顺序。
   - 链接只保留文字，不保留 href。
5. **统一空白**：
   - 换行统一为 `\n`。
   - 每行内的连续空白（含不换行空格）合并为一个空格，去掉行首行尾空白。
   - 删除空行（连续空行也全部删除，所以“空行”不承载信息）。
   - 文件以一个 `\n` 结尾。
   - Unicode 做 NFC 规范化。
6. **已知噪音**：
   - v1 **不做**通用的时间戳或令牌删除。会话令牌、版本号参数之类的噪音都在 URL（href、src）里，第 4 步已经丢掉了 href，不会进入正文。
   - 正文里的时间戳（例如“Last updated …”）可能是有意义的信息，按域名在 §6.3 中处理，3e 根据实际噪音再补。
- **确定性**：同一个原始文件、同一个 normalizer_version，必须得到逐字节相同的输出。依赖库的版本锁在 uv.lock 中。

### 6.3 按域名的额外规则 `config/normalize_rules.yaml`

```yaml
# domain: list of rules; applied after the generic rules of step 3
# - {remove_selector: "<CSS selector>"}       # remove matching elements (step 3)
# - {remove_line_regex: "<Python regex>"}     # after step 5, remove whole lines that match
{}
```

- 初始为空（`{}`）。键是完整域名（与 domains.csv 一致）。
- 只有两种规则：`remove_selector`（第 3 步删除元素）、`remove_line_regex`（第 5 步之后删除整行）。
- 规则内容（或任何会改变输出的代码、依赖库）变化时，**必须升 `normalizer_version`**。测试会检查：规则文件内容的哈希写在代码中，和当前版本号对应；规则变了而版本号没变，测试失败。

### 6.4 重新规范化 `gradprog snapshot renormalize`

- 对 index.csv 中每个**有原始文件**、且还没有当前 normalizer_version 结果的快照，重新规范化、重新分类、重新生成 diff。
- 原始文件不动。新结果写到带新版本号的 normalized 和 diffs 文件（§4.1）。
- index.csv 追加新行：`snapshot_id`、`retrieved_at` 等取得信息照抄，`normalizer_version` 为新版本，`run_id` 为本次 renormalize 运行，note 加 `renormalized`。**旧行不改。**
- 重新分类时，“上一版”只在**同一 normalizer_version** 的结果之间选取（§7.2），按 `retrieved_at` 顺序逐页重算。
- 取得失败的快照（没有原始文件）不重新分类，也不追加新行。

## 7. 分类与差异

### 7.1 分类（每个页面每次取得都归入且只归入一类）

判定顺序：先看取得是否成功，再看内容。

| # | classification | 判定 | 后续 |
|---|---|---|---|
| 1 | `blocked` | 本次 robots.txt 禁止或无法读取（不请求）；或最终状态码为 401、403 | 进异常清单 |
| 2 | `unavailable` | 最终状态码为 404、410；或跳转判定为 `redirected_other` | 进异常清单 |
| 3 | `fetch_error` | 网络错误、超时、5xx、其他非 2xx、超过大小上限、内容类型不支持；规范化后正文为空（0 字符）也算，note 写“可能需要 JavaScript 渲染” | 进异常清单；同一页面**连续 2 次**才在报告中列为“需要处理” |
| 4 | `first_capture` | 取得成功，且没有可比较的上一版（§7.2） | 交给 P4 |
| 5 | `unchanged` | `norm_sha256` 与上一版相同 | 无 |
| 6 | `suspected_redesign` | 正文不同，且（字符数比上一版**减少超过** `char_drop`，**或**相似度**低于** `min_similarity`） | 生成 diff；进异常清单 |
| 7 | `changed` | 正文不同，且不属于 6 | 生成 diff；交给 P4 |

- **普通跳转**（跳到别的网址，但不是 `redirected_other`）：按内容分类，不另设分类；note 加 `redirected`，报告中建议“确认后在登记表中改用最终网址”。
- 人工取得只会出现 4–7 和 `fetch_error`（文件无法解析或正文为空）。
- 阈值 `config/snapshot_thresholds.yaml`：

```yaml
char_drop: 0.5        # (prev_chars - new_chars) / prev_chars > char_drop
min_similarity: 0.3   # line ratio < min_similarity
```

- 相似度 = `difflib.SequenceMatcher(None, prev_lines, new_lines, autojunk=False).ratio()`，按行比较。`autojunk=False` 是为了保证结果稳定。
- 边界：字符数恰好减少 50%、或相似度恰好 0.3，都**不算**疑似改版（判定条件是严格的大于和小于）。

### 7.2 “上一版”的选取

- 同一 `page_id`、同一 `normalizer_version` 中，`retrieved_at` 早于本次的快照里，分类为 `first_capture`、`unchanged`、`changed`、`suspected_redesign` 的**最近一个**。
- `retrieved_at` 相同时，按 `snapshot_id` 比较先后。
- 人工和自动快照放在一起比较。人工登记的 `retrieved_at` 可能早于已有的自动快照（例如补登更早保存的文件）。这时只与它之前的快照比较，**不回头改写**之后快照的分类。报告中提示存在“补登”。

### 7.3 差异

- `changed` 和 `suspected_redesign`：用 `difflib.unified_diff` 生成两版规范化正文之间的 diff（上下文 3 行，文件头标 `prev_snapshot_id` 和 `snapshot_id`），存入 `diffs/`。
- 增删行数：diff 中以 `+` 或 `-` 开头、且不是文件头的行数，写入 index.csv 的 `added_lines` 和 `removed_lines`。报告只写行数，不写 diff 内容。

## 8. 链接发现

- 对象：本次成功取得（分类为 4–7）的 `page_type = program_home` 页面。
- 从**原始 HTML**（不是规范化正文）中提取 `<a href>`。提取前先按 §6.2 **第 3 步的结构规则**删除页头、导航、页脚等区域：`header`、`nav`、`footer`、`form` 等标签，`role` 为 `banner` / `navigation` / `contentinfo` / `search` 的元素，Cookie 提示，以及该域名在 `config/normalize_rules.yaml` 中的 `remove_selector`。这样只留正文区域内的链接（2026-10-04 修订：第一次运行中，87 个候选大多来自导航菜单）。
- 解析为绝对 URL，再规范化（06 §3.5）。规范化失败的（例如 http、mailto）忽略。**路径中含 `@` 的链接忽略**：这通常是邮箱地址被误写成相对链接，例如 `visp-msds@stat.wisc.edu`。
- 范围（2026-10-04 修订）：与该首页属于**同一所大学注册域名**的链接，包括所有子域名（例如首页在 `cds.nyu.edu`，`gsas.nyu.edu` 上的链接也算）。注册域名 = 主机名以 `.edu` 结尾时取最后两段（如 `nyu.edu`、`utdallas.edu`）；不以 `.edu` 结尾时退回为完全相同的主机名。理由：申请和截止日期页面常在研究生院子域名上。
- 筛选：链接文字或 URL 路径中含 `config/link_keywords.yaml` 的任一关键词（不区分大小写）。初始关键词：admission、apply、deadline、requirement、tuition、cost、fee、faq、international、i-20、visa。
- 与该项目在 program_pages 中已登记页面的 URL 比较；**没有登记的列为候选**，写进运行报告（项目、链接文字、URL），同一候选在同一报告中只列一次。
- 只提示，不自动登记。
- 备注：若将来出现同一所学校的页面分布在多个注册域名下（例如 WashU 的 `washu.edu` 与 `wustl.edu`），再增加“同校域名别名”配置。目前 WashU 的已登记页面已全部迁到 `washu.edu`，暂不处理。

## 9. 运行报告 `data/snapshots/reports/run-<run_id>.md`

- 各分类数量。
- 异常清单：page_id、项目、分类、原因（状态码或错误类型），以及建议动作。建议动作的映射：

| 情况 | 建议动作 |
|---|---|
| `unavailable`（404 / 410） | 找新网址 |
| `unavailable`（`redirected_other`） | 确认最终页面；必要时找新网址 |
| `blocked`（robots） | 运行 `registry check-robots`，考虑改为人工取得 |
| `blocked`（401 / 403） | 考虑改为人工取得 |
| `fetch_error`（连续 2 次） | 检查网址或网站状态 |
| `fetch_error`（首次） | 下次运行再看（列出，不需要处理） |
| `suspected_redesign` | 人工查看 diff，确认是否改版；必要时调整规范化规则 |

- 有变化的页面：page_id、项目、增删行数。
- 链接发现的候选。
- 人工取得的待办数量（同 manual-due 的规则）。
- “未纳入取得”的页面（§3）：page_id、项目、不可抓取的原因。
- 普通跳转与“补登”的提示。
- 报告不得含页面正文；`runs.csv` 同时追加一行。

## 10. 定时运行与备份

### 10.1 launchd

- `ops/launchd/` 下提供 plist 模板和 README：
  - 每周一 07:00 运行 `gradprog snapshot run`。launchd 的 `StartCalendarInterval` 使用 **Mac 的系统时区**；README 写明这一点（Mac 时区为东京时就是东京时间 07:00）。
  - 联系邮箱：launchd 不读 `~/.zshrc`。由一个包装脚本 `ops/launchd/run-snapshot.sh` 读取 `~/.config/gradprog/env`（仓库外，`KEY=value` 格式，权限 600），只导出 `GRADPROG_CONTACT_EMAIL`，再调用 `uv run gradprog snapshot run`。
  - 日志：`data/snapshots/logs/`（gitignore）。
- **不自动安装**：模板里的路径用占位符，README 写明替换与 `launchctl` 安装步骤，由你手动安装。

### 10.2 备份 `gradprog snapshot backup --dest <目录>`

- 把 `data/snapshots/` 增量复制到 `--dest`。目的地没有默认值，不写死在代码里。
- 原始文件、规范化文件和 diff 一经写入就不再改变：
  - 目的地没有的 → 复制；
  - 已有且内容相同 → 跳过；
  - 已有但内容不同 → 报错，不覆盖。
- `index.csv`、`runs.csv` 会不断追加（不是“新增文件”），按“只复制新增文件”的字面意思就永远不会更新：
  - 目的地版本是本地版本的前缀时（只追加），用本地版本覆盖；
  - 否则报错，不覆盖。
- 运行报告、manual_due.md、日志：同名文件已存在且内容不同时覆盖（这些是可重新生成的工作文件）。
- 不删除目的地的任何文件。结束时输出复制、跳过、覆盖的文件数。

## 11. 与其他 spec 的关系

- 05 §1.1 的 snapshot 层以本文件为准：`fetch_status` 由本文件的 `classification` 取代；05 §4 中“页面不可访问”对应 `classification ∈ {blocked, unavailable, fetch_error}`。
- 06：本阶段只读登记表，不修改。
