# 扩展批次审核清单 2026-11-23（第三轮补登：Columbia MSFE（按实际 CIP 登记））

填写方法：
- 每个新域名的“条款：”填 `no_restriction`、`prohibits_automated_access` 或 `unclear`，后面可加说明。
- 每个项目的“决定：”填 `select`、`exclude <原因> <说明>`（原因用 exclusion_reason 的取值，如 `online_only`、`certificate`、`mba`、`out_of_scope`、`duplicate`、`not_admitting`、`other`）或 `backup`。
- “用时（分钟）：”填审核这个项目实际花的时间，可空。
- 补登页面的“决定：”填 `confirm` 或 `reject`。
- “我要加的学校：”写本组要补充点名的学校，Claude 再为它们准备提议。
- 没有填写的项不会改动。填完后运行 `gradprog registry apply-review <本文件>`。

## 新域名条款

（没有新域名）

## 组 fin_eng

名额 10，已选 9；本清单提议 1 个项目（点名 1，按排序 0）。

我要加的学校：

### 点名

#### 项目 columbia-ms-financialengineering — Columbia University in the City of New York — MS in Financial Engineering
- IPEDS：CIP 14.3701（Operations Research.），硕士授予 326，国际学生 289，STEM：是，工作表排名 1
- 显示方向：fin_eng（按实际 CIP 登记，06 §2.8；CIP 来源：推测）
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Industrial Engineering and Operations Research
- 页面：
  - pg-0294 program_home（department）https://www.ieor.columbia.edu/financial-engineering-msfe — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0077（已登记，沿用） requirements（graduate_school）https://www.engineering.columbia.edu/admissions-aid/graduate-admissions/how-apply/application-requirements — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0051（已登记，沿用） admissions（graduate_school）https://www.engineering.columbia.edu/admissions-aid/graduate-admissions/apply-now — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0078（已登记，沿用） tuition（graduate_school）https://bulletin.columbia.edu/columbia-engineering/graduate-studies/graduate-tuition-fees-payments — robots no，条款 unclear，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：CIP not published (ISSO, Provost CIP page and CVN codes page 403; bulletin refused connection); 14.3701 set by owner, IEOR reports 14.3501 and 14.3701 in IPEDS, no 27.0305. STEM-certified per program page (search snippet). blocked: 403 on WebFetch; URL from search results, www host as for the registered MSOR page. intake_terms 未核实
决定：select
用时（分钟）：

## 补登页面

（没有补登页面）

## 汇总

- 本清单项目 1 个，页面 4 个（含沿用的已登记页面）。条款未判断的域名按不能抓取算。
- 按排序：项目 0 个，页面 0 个，不能自动抓取 0 个（0%）；若条款都判为 no_restriction：0 个（0%）。06 §2.8 上限 30%。
- 点名：项目 1 个，页面 4 个，不能自动抓取 4 个（100%）；若条款都判为 no_restriction：4 个（100%）。按需求选入，不受比例限制。

