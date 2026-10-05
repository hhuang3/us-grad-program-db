# 00 基本原则

> 状态：v1（Phase 1b）。所有后续 spec、测试、代码都受本文件约束；冲突时以本文件为准，并先提出来讨论。

## 1. 人工审核是系统的一部分

- 自动流程（抓取、抽取、对齐）只产出**候选值**（observation），不直接产出对外数据。
- 对外数据（fact → release）必须经过人工审核。审核结果（approved / corrected / rejected）是数据的一部分，要留存。
- 人工修正过的值不会被后续自动抽取静默覆盖（细则见 `05_data_model.md`）。
- Phase 1 没有抽取环节，但“候选清单”同样只是候选：最终 100 个项目由人工在 Phase 2 挑选。

## 2. 只存事实与链接，不对外发布原文

- 对外发布的只有**结构化事实 + 来源链接**（evidence_url）。
- 网页原文、快照正文、`evidence_text` 片段只在内部保存，用于审核与追溯，**不对外发布**。
- 参考数据（DHS STEM 清单、CIP、IPEDS、College Scorecard）都是美国联邦政府公开数据，可以存派生表。但原始文件不提交进 git，改由 manifest 记录出处（URL、时间、sha256）。

## 3. 来源准入

- **一手资料优先**。Phase 1 只使用以下官方域名的资料作为依据：
  - `ice.gov`、`studyinthestates.dhs.gov`（DHS/ICE/SEVP）
  - `nces.ed.gov`（CIP、IPEDS）
  - `collegescorecard.ed.gov` 及其官方下载域 `ed-public-download.scorecard.network`（College Scorecard 页面上直接链接的官方下载地址）
  - `federalregister.gov`（含其链接的 `govinfo.gov` 官方 PDF）
  - `studentaid.gov`（U.S. Department of Education, Federal Student Aid；联邦学生资助资格规则）
- 大学官网（Phase 2 起）：只用学校自己的页面（`.edu` 或学校官方域名）。
- 二手来源（博客、论坛、留学中介、排名网站）只能作为线索，**不得作为依据写进数据**。
- **明确排除**、连线索也不用的来源：一亩三分地、GradCafe，以及其他明确禁止复用、或以用户生成内容为主的站点。新增排除项写进本节。

## 4. 不确定就标注，不猜

- 下载 URL、文件名、字段名、编码值、数据年份，一律在运行时从官方页面或官方文档确认，并在 `01_reference_data.md` 中记录确认时间。
- 无法确认的值：**标记为待确认并停下来问**，不填默认值、不按经验补全。
- 代码层面：输入不符合规则时**抛异常**，不静默修正、不静默丢弃。确需丢弃的行，要按规则丢弃并在日志或报告里计数。
- 规则与官方资料冲突（例如清单格式和说明文字对不上）时，先停下来讨论，不自行取舍。

## 5. 可复现与可追溯

- 每个原始文件在 `data/manifest/manifest.csv` 中占一行（URL、UTC 取得时间、sha256、字节数、备注）。
- 每个派生表在 `data/manifest/derived.csv` 中占一行，记录它由哪些原始文件（sha256）生成。
- 同样的原始文件加上同样的代码，必须生成逐字节相同的派生表（排序规则固定、不依赖运行时间）。

## 6. 安全与礼貌

- 密钥只从环境变量读（`SCORECARD_API_KEY`），不写入代码、日志、manifest 或 git。
- 下载器单线程，请求间隔至少 3 秒，User-Agent 中带联系邮箱（取自 `GRADPROG_CONTACT_EMAIL`，未设置则拒绝运行）。
- 网站明确拒绝自动化访问时（例如返回 HTTP 403），不设法绕过（不伪装浏览器 UA、不破解反爬）。改为人工下载后登记，见 `01_reference_data.md` §7。
- **不绕过任何访问限制**（2026-10-04 补充，Phase 3）：不伪装成浏览器，不执行 JavaScript 挑战，不使用无头浏览器，不轮换 IP 或代理，不重试被拦截的请求来“碰运气”。被拦截就记录为被拦截（`07_snapshots.md` §7.1 的 `blocked`）。
- 使用条款或 robots.txt 不允许自动访问的页面，由负责人本人在浏览器中正常浏览并保存，再登记（`07_snapshots.md` §5.2）。保存的页面同样只在本地保存，不对外发布（见 §2）。
- **条款受限域名的发布**（2026-10-04 补充）：`tos_status` 为 `prohibits_automated_access` 或 `unclear` 的域名（`06_source_registry.md` §3.4），其页面信息在 P5 对外发布前，由负责人另行决定呈现方式（例如只给官网链接、请求许可或不发布）。P3、P4 阶段照常保存与抽取，仅限内部使用。
