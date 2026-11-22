# 扩展批次审核清单 2026-11-23（第三轮：点名补充）

填写方法：
- 每个新域名的“条款：”填 `no_restriction`、`prohibits_automated_access` 或 `unclear`，后面可加说明。
- 每个项目的“决定：”填 `select`、`exclude <原因> <说明>`（原因用 exclusion_reason 的取值，如 `online_only`、`certificate`、`mba`、`out_of_scope`、`duplicate`、`not_admitting`、`other`）或 `backup`。
- “用时（分钟）：”填审核这个项目实际花的时间，可空。
- 补登页面的“决定：”填 `confirm` 或 `reject`。
- “我要加的学校：”写本组要补充点名的学校，Claude 再为它们准备提议。
- 没有填写的项不会改动。填完后运行 `gradprog registry apply-review <本文件>`。

## 新域名条款

#### 域名 ece.ucsd.edu
- 条款页：https://ucsd.edu/about/terms-of-use.html
- Claude 初步判断：terms limit downloads to personal non-commercial use; nothing about automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 ece.duke.edu
- 条款页：https://oarc.duke.edu/privacy/duke-university-privacy-statement/
- Claude 初步判断：no terms page found in footer; only university privacy statement, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 gradschool.duke.edu
- 条款页：未找到
- Claude 初步判断：无
- robots.txt：fetched（yes）
条款：

#### 域名 mfe.haas.berkeley.edu
- 条款页：https://haas.berkeley.edu/technology-solutions/about/privacy-policy/
- Claude 初步判断：no terms page found; footer has only a privacy policy, no ban on automated access
- robots.txt：fetched（yes）
条款：

#### 域名 haas.berkeley.edu
- 条款页：https://haas.berkeley.edu/technology-solutions/about/privacy-policy/
- Claude 初步判断：no terms page found; privacy policy only, no ban on automated access
- robots.txt：fetched（yes）
条款：

#### 域名 www.isye.gatech.edu
- 条款页：https://www.gatech.edu/legal/
- Claude 初步判断：no ban on automated access or non-commercial limit found
- robots.txt：fetched（yes）
条款：

#### 域名 grad.gatech.edu
- 条款页：https://www.gatech.edu/legal/
- Claude 初步判断：no ban on automated access or non-commercial limit found
- robots.txt：fetched（yes）
条款：

#### 域名 ischool.uw.edu
- 条款页：https://www.washington.edu/online/terms/
- Claude 初步判断：no explicit ban on automated access; forbids unreasonable network load and reproduction without permission
- robots.txt：fetched（yes）
条款：

#### 域名 ischool.illinois.edu
- 条款页：https://www.vpaa.uillinois.edu/resources/terms_of_use/
- Claude 初步判断：system-wide Legal Notice and Terms of Use exists; 403 on fetch, content not checked
- robots.txt：fetched（yes）
条款：

#### 域名 www.si.umich.edu
- 条款页：https://si.umich.edu/privacy-statement
- Claude 初步判断：only privacy statement found, no terms page, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 hsph.harvard.edu
- 条款页：https://privsec.harvard.edu/harvard-university-umbrella-privacy-statement
- Claude 初步判断：no terms page in footer; only privacy statement, trademark and copyright notices
- robots.txt：error（no）
条款：

#### 域名 publichealth.jhu.edu
- 条款页：未找到
- Claude 初步判断：no terms page found (old jhsph.edu Web Policies may apply); 403 so footer not checked
- robots.txt：fetched（yes）
条款：

## 组 ece

名额 10，已选 7；本清单提议 3 个项目（点名 3，按排序 0）。

我要加的学校：

### 点名

#### 项目 columbia-ms-electricalengineering — Columbia University in the City of New York — MS in Electrical Engineering
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 224，国际学生 178，STEM：是，工作表排名 9
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Department of Electrical Engineering
- 页面：
  - pg-0253 program_home（department）https://www.engineering.columbia.edu/academics/programs/masters-programs/master-science-programs/electrical-engineering-ms — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0077（已登记，沿用） requirements（graduate_school）https://www.engineering.columbia.edu/admissions-aid/graduate-admissions/how-apply/application-requirements — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0051（已登记，沿用） admissions（graduate_school）https://www.engineering.columbia.edu/admissions-aid/graduate-admissions/apply-now — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0078（已登记，沿用） tuition（graduate_school）https://bulletin.columbia.edu/columbia-engineering/graduate-studies/graduate-tuition-fees-payments — robots no，条款 unclear，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：blocked: 403 on WebFetch; URL from search results. Alternative MS Computer Engineering (14.0901). CVN online and MS Bridge track excluded. Spring intake only from search snippets; intake_terms 未核实
决定：
用时（分钟）：

#### 项目 ucsd-ms-electricalandcomputerengineering — University of California-San Diego — MS in Electrical and Computer Engineering
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 90，国际学生 69，STEM：是，工作表排名 34
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Electrical and Computer Engineering
- 页面：
  - pg-0254 program_home（department）https://ece.ucsd.edu/graduate/ms-degree-requirements — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0255 admissions（department）https://ece.ucsd.edu/graduate/graduate-admissions — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0094（已登记，沿用） grad_school_intl（graduate_school）https://grad.ucsd.edu/admissions/requirements/international-students/english-proficiency.html — robots yes，条款 unclear，网址检查 ok 200
  - pg-0095（已登记，沿用） tuition（university）https://students.ucsd.edu/finances/fees/registration/2026-27/graduate.html — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：No standalone MS landing page (overview page returned 403), so the M.S. degree requirements page is used as program home. Admission by discipline (some impacted). Alternative 14.0901 (Computer Engineering discipline). MAS program excluded. Full-time only
决定：
用时（分钟）：

#### 项目 duke-ms-electricalandcomputerengineering — Duke University — MS in Electrical and Computer Engineering
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 107，国际学生 84，STEM：是，工作表排名 26
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Electrical and Computer Engineering
- 页面：
  - pg-0256 program_home（department）https://ece.duke.edu/academics/masters/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0257 requirements（graduate_school）https://gradschool.duke.edu/academics/programs-degrees/electrical-and-computer-engineering-ms/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0258 grad_school_intl（graduate_school）https://gradschool.duke.edu/admissions/application-instructions/english-language-proficiency-test-scores/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0259 tuition（graduate_school）https://gradschool.duke.edu/financial-support/tuition-fees-and-phd-stipend-schedule/ — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：MEng ECE is a separate Pratt program; MS applications go through the Graduate School. Coursework, project or thesis options. Alternative 14.0901. Duke Kunshan option excluded
决定：
用时（分钟）：

## 组 fin_eng

名额 10，已选 5；本清单提议 5 个项目（点名 3，按排序 2）。

我要加的学校：

### 点名

#### 项目 cmu-ms-computationalfinance — Carnegie Mellon University — Master of Science in Computational Finance
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 93，国际学生 78，STEM：是，工作表排名 10
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Tepper School of Business (MSCF)
- 页面：
  - pg-0260 program_home（program）https://www.cmu.edu/mscf/ — robots yes，条款 unclear，网址检查 ok 200
  - pg-0261 admissions（program）https://www.cmu.edu/mscf/admissions/ — robots yes，条款 unclear，网址检查 ok 200
  - pg-0262 faq（program）https://www.cmu.edu/mscf/admissions/faq — robots yes，条款 unclear，网址检查 ok 200
  - pg-0230（已登记，沿用） tuition（university）https://www.cmu.edu/sfs/tuition/graduate/index.html — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Pittsburgh campus chosen; same degree also in New York City. FAQ says full-time, on-campus only. STEM not stated
决定：
用时（分钟）：

#### 项目 ucberkeley-other-financialengineering — University of California-Berkeley — Master of Financial Engineering (MFE)
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 82，国际学生 76，STEM：是，工作表排名 11
- 学位 / 授课 / 入学季：other MFE / on_campus / spring；院系：Haas School of Business
- 页面：
  - pg-0263 program_home（program）https://mfe.haas.berkeley.edu/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0264 requirements（program）https://mfe.haas.berkeley.edu/admissions/requirements — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0265 deadlines（program）https://mfe.haas.berkeley.edu/admissions — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0266 tuition（graduate_school）https://haas.berkeley.edu/financial-aid/master-of-financial-engineering/cost/ — robots yes，条款 not_checked，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：Full-time program used; part-time Flex option excluded. Starts in spring. STEM not stated
决定：
用时（分钟）：

#### 项目 nyu-ms-financialengineering — New York University — MS in Financial Engineering
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 55，国际学生 50，STEM：是，工作表排名 16
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Finance and Risk Engineering (Tandon)
- 页面：
  - pg-0267 program_home（program）https://engineering.nyu.edu/academics/programs/financial-engineering-ms — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0155（已登记，沿用） admissions（graduate_school）https://engineering.nyu.edu/admissions/graduate/apply/admissions-requirements — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0268 deadlines（graduate_school）https://engineering.nyu.edu/admissions/graduate/apply/application-deadlines — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0156（已登记，沿用） tuition（university）https://www.nyu.edu/students/student-information-and-resources/bills-payments-and-refunds/tuition-and-fee-rates.html — robots yes，条款 unclear，网址检查 redirected 202 → https://www.nyu.edu/students/student-information-and-resources/bills-payments-and-refunds/tuition-and-fee-rates.html?challenge=d06e90d7-4d8f-4b88-9d8c-10b73beb60f1
- 建议：人工保存（按目前检查结果）
- 提示：on campus only; no spring intake per Tandon deadlines page
决定：
用时（分钟）：

### 按排序

（Claude 注：点名的 Columbia MSFE、Cornell MFE 在 IPEDS 候选里没有 27.0305 的记录，按 §2.1 不能登记到 fin_eng，所以这一轮 fin_eng 只能补 3 个，选入 8 个，距名额还差 2 个。下面两个是第二轮的备选，重新列出供考虑，改为 `select` 就能补满；两者的页面都要人工保存：MIT 被 robots 禁止，Northeastern 返回 403。也可以继续填 `backup`。）

#### 项目 mit-other-finance — Massachusetts Institute of Technology — Master of Finance (MFin)
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 128，国际学生 119，STEM：是，工作表排名 5
- 学位 / 授课 / 入学季：other MFin / on_campus / summer；院系：Sloan School of Management
- 页面：
  - pg-0185 program_home（program）https://mitsloan.mit.edu/mfin — robots no，条款 no_restriction，网址检查 robots_unavailable
  - pg-0186（已登记，沿用） admissions（program）https://mitsloan.mit.edu/mfin/admissions — robots no，条款 no_restriction，网址检查 robots_unavailable
  - pg-0187（已登记，沿用） requirements（program）https://mitsloan.mit.edu/mfin/apply/how-to-apply — robots no，条款 no_restriction，网址检查 robots_unavailable
  - pg-0188（已登记，沿用） tuition（program）https://mitsloan.mit.edu/mfin/admissions/tuition-and-financial-aid — robots no，条款 no_restriction，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：STEM-designated; two length formats. intake_terms 未核实 (tuition page lists summer as first term)
决定：
用时（分钟）：

#### 项目 northeastern-ms-quantitativefinance — Northeastern University — MS in Quantitative Finance
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 164，国际学生 157，STEM：是，工作表排名 3
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：D'Amore-McKim School of Business
- 页面：
  - pg-0179 program_home（program）https://damore-mckim.northeastern.edu/programs/ms-quantitative-finance/ — robots yes，条款 no_restriction，网址检查 error 403
  - pg-0180（已登记，沿用） admissions（graduate_school）https://damore-mckim.northeastern.edu/admissions/how-to-apply/ — robots yes，条款 no_restriction，网址检查 error 403
  - pg-0181（已登记，沿用） deadlines（graduate_school）https://damore-mckim.northeastern.edu/admissions/deadlines/ — robots yes，条款 no_restriction，网址检查 error 403
  - pg-0122（已登记，沿用） tuition（university）https://studentfinance.northeastern.edu/billing-payments/tuition-and-fees/ — robots yes，条款 no_restriction，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：Boston, full-time, STEM-designated. Exclude Oakland-campus MSQF and MSQF/MBA dual; alternative D'Amore-McKim MS Finance
决定：
用时（分钟）：

## 组 ieor

名额 8，已选 6；本清单提议 2 个项目（点名 1，按排序 1）。

我要加的学校：

### 点名

#### 项目 gatech-ms-industrialengineering — Georgia Institute of Technology-Main Campus — Master of Science in Industrial Engineering
- IPEDS：CIP 14.3501（Industrial Engineering.），硕士授予 70，国际学生 61，STEM：是，工作表排名 12
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：H. Milton Stewart School of Industrial and Systems Engineering
- 页面：
  - pg-0269 program_home（program）https://www.isye.gatech.edu/academics/masters/degrees/ms-industrial-engineering — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0270 admissions（graduate_school）https://grad.gatech.edu/admissions/international/ready-to-apply — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0271 grad_school_intl（graduate_school）https://grad.gatech.edu/english-proficiency — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0089（已登记，沿用） tuition（university）https://bursar.gatech.edu/tuition-fees — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Also holds requirements, deadlines and entry term (on-campus fall only). Distance-learning MSIE excluded. Alternative MS Operations Research (14.3701). STEM not stated
决定：
用时（分钟）：

### 按排序

#### 项目 uta-ms-industrialengineering — The University of Texas at Arlington — Master of Science in Industrial Engineering
- IPEDS：CIP 14.3501（Industrial Engineering.），硕士授予 97，国际学生 92，STEM：是，工作表排名 8
- 学位 / 授课 / 入学季：ms / hybrid / fall;spring;summer；院系：Department of Industrial, Manufacturing, and Systems Engineering
- 页面：
  - pg-0272 program_home（department）https://www.uta.edu/academics/schools-colleges/engineering/academics/masters/industrial — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0273 deadlines（university）https://www.uta.edu/academics/programs/industrial-engineering-ms — robots yes，条款 no_restriction，网址检查 redirected 200 → https://www.uta.edu/academics/programs/industrial-engineering-ms?level=mas&program=indusengm
  - pg-0113（已登记，沿用） grad_school_intl（graduate_school）https://www.uta.edu/admissions/apply/international-graduate — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0114（已登记，沿用） tuition（university）https://www.uta.edu/business-affairs/student-accounts/about-tuition — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：自动抓取（按目前检查结果）
- 提示：Also holds requirements (background, GPA, English and test minimums); most classes also online, hence hybrid. Department page and a catalog snippet disagree on whether GRE is required - owner check
决定：
用时（分钟）：

## 组 info_sys

名额 8，已选 5；本清单提议 3 个项目（点名 3，按排序 0）。

我要加的学校：

### 点名

#### 项目 uw-ms-informationmanagement — University of Washington-Seattle Campus — Master of Science in Information Management (MSIM)
- IPEDS：CIP 11.0401（Information Science/Studies.），硕士授予 275，国际学生 126，STEM：是，工作表排名 26
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Information School
- 页面：
  - pg-0274 program_home（program）https://ischool.uw.edu/programs/msim — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0275 admissions（program）https://ischool.uw.edu/programs/msim/admissions — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0276 requirements（program）https://ischool.uw.edu/programs/msim/admissions/application-materials — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0277 deadlines（program）https://ischool.uw.edu/programs/msim/admissions/apply — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0278 tuition（program）https://ischool.uw.edu/programs/msim/tuition-financial-aid — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Residential option only; online MSIM is a separate modality, excluded. Tracks: Early-Career, Early-Career Accelerated, Mid-Career. STEM-designated per page. Residential admits autumn only
决定：
用时（分钟）：

#### 项目 uiuc-ms-informationmanagement — University of Illinois Urbana-Champaign — MS in Information Management
- IPEDS：CIP 11.0401（Information Science/Studies.），硕士授予 368，国际学生 108，STEM：是，工作表排名 35
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：School of Information Sciences
- 页面：
  - pg-0279 program_home（program）https://ischool.illinois.edu/academics/graduate/ms-information-management — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0280 admissions（program）https://ischool.illinois.edu/academics/graduate/ms-information-management/apply — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0145（已登记，沿用） tuition（university）https://www.registrar.illinois.edu/g-tuition-rates-2627/ — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Online MSIM suspended; only on-campus applicants accepted. STEM-designated per page. intake_terms 未核实
决定：
用时（分钟）：

#### 项目 umich-ms-information — University of Michigan-Ann Arbor — Master of Science in Information (MSI)
- IPEDS：CIP 11.0401（Information Science/Studies.），硕士授予 295，国际学生 163，STEM：是，工作表排名 17
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：School of Information
- 页面：
  - pg-0281 program_home（program）https://www.si.umich.edu/programs/degree-programs/master-science-information — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0282 admissions（program）https://www.si.umich.edu/admissions-aid/apply/how-do-i-apply-master-science-information — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0283 tuition（program）https://www.si.umich.edu/admissions-aid/tuition-and-funding/master-science-information-tuition-and-funding — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Official name Master of Science in Information. Onsite, North Campus. Online MADS is a different program, excluded
决定：
用时（分钟）：

## 组 biostat

名额 6，已选 4；本清单提议 2 个项目（点名 2，按排序 0）。

我要加的学校：

### 点名

#### 项目 harvard-other-biostatistics — Harvard University — Master of Science in Biostatistics (SM)
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 42，国际学生 16，STEM：是，工作表排名 11
- 学位 / 授课 / 入学季：other SM / on_campus / fall；院系：Department of Biostatistics
- 页面：
  - pg-0284 program_home（department）https://hsph.harvard.edu/program/sm-biostatistics/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0285 requirements（graduate_school）https://hsph.harvard.edu/admissions/applying-to-a-degree-program/application-requirements/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0286 tuition（graduate_school）https://hsph.harvard.edu/tuition-and-financial-aid/tuition-fees-and-annual-cost-of-attendance/ — robots no，条款 not_checked，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：One program with three tracks; the doctorate-holder track is not relevant, the two standard tracks are. SOPHAS application
决定：
用时（分钟）：

#### 项目 jhu-other-biostatistics — Johns Hopkins University — Master of Science in Biostatistics (ScM)
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 26，国际学生 20，STEM：是，工作表排名 9
- 学位 / 授课 / 入学季：other ScM / on_campus / fall；院系：Department of Biostatistics
- 页面：
  - pg-0287 program_home（department）https://publichealth.jhu.edu/academics/scm-dept-of-biostatistics — robots yes，条款 not_checked，网址检查 error 403
  - pg-0288 admissions（graduate_school）https://publichealth.jhu.edu/offices-and-services/office-of-admissions-services/how-to-apply — robots yes，条款 not_checked，网址检查 error 403
  - pg-0289 deadlines（graduate_school）https://publichealth.jhu.edu/offices-and-services/office-of-admissions-services/how-to-apply/application-deadlines — robots yes，条款 not_checked，网址检查 error 403
  - pg-0290 grad_school_intl（graduate_school）https://publichealth.jhu.edu/offices-and-services/office-of-admissions-services/international-applicants — robots yes，条款 not_checked，网址检查 error 403
  - pg-0291 tuition（graduate_school）https://publichealth.jhu.edu/offices-and-services/office-of-student-affairs/financial-aid/cost-of-attendance — robots yes，条款 not_checked，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：blocked: 403. ScM chosen (onsite full-time, thesis); MHS needs a prior doctorate or concurrent JHU doctoral enrollment. intake_terms 未核实
决定：
用时（分钟）：

## 补登页面

#### 页面 pg-0292 — asu-other-electricalengineering（ASU Electrical Engineering (MSE)）
  - pg-0292 admissions（graduate_school）https://admission.asu.edu/apply/international/graduate — robots yes，条款 unclear，网址检查 ok 200
- 提示：admissions page missing after round 2 (validate error); application steps, transcripts, accepted English tests, I-20 and financial documents
决定：

## 汇总

- 本清单项目 15 个，页面 59 个（含沿用的已登记页面）。条款未判断的域名按不能抓取算。
- 按排序：项目 3 个，页面 12 个，不能自动抓取 8 个（67%）；若条款都判为 no_restriction：8 个（67%）。06 §2.8 上限 30%。
- 点名：项目 12 个，页面 47 个，不能自动抓取 43 个（91%）；若条款都判为 no_restriction：21 个（45%）。按需求选入，不受比例限制。

