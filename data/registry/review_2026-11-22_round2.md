# 扩展批次审核清单 2026-11-22（第二轮：ece、fin_eng、ieor、info_sys、biostat）

填写方法：
- 每个新域名的“条款：”填 `no_restriction`、`prohibits_automated_access` 或 `unclear`，后面可加说明。
- 每个项目的“决定：”填 `select`、`exclude <原因> <说明>`（原因用 exclusion_reason 的取值，如 `online_only`、`certificate`、`mba`、`out_of_scope`、`duplicate`、`not_admitting`、`other`）或 `backup`。
- “用时（分钟）：”填审核这个项目实际花的时间，可空。
- 补登页面的“决定：”填 `confirm` 或 `reject`。
- “我要加的学校：”写本组要补充点名的学校，Claude 再为它们准备提议。
- 没有填写的项不会改动。填完后运行 `gradprog registry apply-review <本文件>`。

## 新域名条款

#### 域名 engineering.nyu.edu
- 条款页：https://www.nyu.edu/footer/copyright-and-fair-use.html
- Claude 初步判断：no terms link in engineering.nyu.edu footer; nyu.edu copyright page rendered empty, not verified
- robots.txt：fetched（yes）
条款：

#### 域名 www.nyu.edu
- 条款页：https://www.nyu.edu/footer/copyright-and-fair-use.html
- Claude 初步判断：same NYU copyright page; not verified (empty render)
- robots.txt：fetched（yes）
条款：

#### 域名 www.scu.edu
- 条款页：https://www.scu.edu/terms-and-conditions-of-use/
- Claude 初步判断：terms limit use to personal non-commercial; scraping barred where robots.txt disallows
- robots.txt：fetched（yes）
条款：

#### 域名 www.ece.cmu.edu
- 条款页：https://www.cmu.edu/legal/
- Claude 初步判断：terms limit use to personal viewing and non-commercial use; no explicit scraping ban
- robots.txt：fetched（yes）
条款：

#### 域名 ece.gatech.edu
- 条款页：https://www.gatech.edu/legal/
- Claude 初步判断：only disclaimers/copyright notices, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 ece.engin.umich.edu
- 条款页：https://www.umich.edu/privacy/
- Claude 初步判断：only privacy notice found, no terms page; not fetched
- robots.txt：error（no）
条款：

#### 域名 ro.umich.edu
- 条款页：https://www.umich.edu/privacy/
- Claude 初步判断：only privacy notice found, no terms page; not fetched
- robots.txt：fetched（yes）
条款：

#### 域名 ecee.engineering.asu.edu
- 条款页：https://www.asu.edu/about/terms-of-use
- Claude 初步判断：limits use to ASU-related purposes, bars commercial use; no scraping ban found
- robots.txt：fetched（yes）
条款：

#### 域名 admission.asu.edu
- 条款页：https://www.asu.edu/about/terms-of-use
- Claude 初步判断：same ASU terms
- robots.txt：fetched（yes）
条款：

#### 域名 msfe.illinois.edu
- 条款页：https://illinois.edu/copyright/
- Claude 初步判断：copyright notice linked in footer; fetch failed with certificate error, not checked
- robots.txt：fetched（yes）
条款：

#### 域名 damore-mckim.northeastern.edu
- 条款页：https://www.northeastern.edu/privacy-information
- Claude 初步判断：no terms page in footer; university privacy policy only, not checked for automated-access ban
- robots.txt：fetched（yes）
条款：

#### 域名 rady.ucsd.edu
- 条款页：https://ucsd.edu/about/terms-of-use.html
- Claude 初步判断：terms limit copying to one personal non-commercial download; no explicit bot/scraping clause
- robots.txt：fetched（yes）
条款：

#### 域名 mitsloan.mit.edu
- 条款页：https://mitsloan.mit.edu/licensing
- Claude 初步判断：only licensing and privacy notices, no ban on automated access found
- robots.txt：error（no）
条款：

#### 域名 fin.utdallas.edu
- 条款页：https://jindal.utdallas.edu/privacy-policy/
- Claude 初步判断：no terms page in footer; Jindal privacy policy only, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 merage.uci.edu
- 条款页：https://uci.edu/privacy/index.php
- Claude 初步判断：privacy and cookie notice only, no terms page found
- robots.txt：fetched（yes）
条款：

#### 域名 www.reg.uci.edu
- 条款页：https://uci.edu/privacy/index.php
- Claude 初步判断：same UCI privacy notice; no reg.uci.edu terms page found
- robots.txt：fetched（yes）
条款：

#### 域名 grad.uci.edu
- 条款页：未找到
- Claude 初步判断：not checked: grad.uci.edu returned 403
- robots.txt：fetched（yes）
条款：

#### 域名 www.ieor.columbia.edu
- 条款页：https://www.engineering.columbia.edu/terms-use
- Claude 初步判断：ieor host blocked, its own terms not checked; Columbia Engineering terms (already judged prohibits_automated_access) may apply
- robots.txt：fetched（yes）
条款：

#### 域名 engineering.tamu.edu
- 条款页：https://engineering.tamu.edu/policies.html
- Claude 初步判断：site policies cover privacy/logging and ban unauthorized uploads; no ban on automated access found
- robots.txt：not_found（yes）
条款：

#### 域名 admissions.tamu.edu
- 条款页：https://www.tamu.edu/statements/index.html
- Claude 初步判断：statements page lists site, linking, privacy and copyright policies; no ban on automated access seen
- robots.txt：not_found（yes）
条款：

#### 域名 catalog.tamu.edu
- 条款页：https://www.tamu.edu/statements/index.html
- Claude 初步判断：catalog terms not checked (connection refused); university statements page has no ban
- robots.txt：error（no）
条款：

#### 域名 ieor.berkeley.edu
- 条款页：https://security.berkeley.edu/policy/privacy-statement-uc-berkeley-websites
- Claude 初步判断：only privacy/nondiscrimination/copyright notices, no terms page or ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 grad.berkeley.edu
- 条款页：https://security.berkeley.edu/policy/privacy-statement-uc-berkeley-websites
- Claude 初步判断：only privacy/nondiscrimination/accessibility links, no terms page found
- robots.txt：fetched（yes）
条款：

#### 域名 funginstitute.berkeley.edu
- 条款页：https://funginstitute.berkeley.edu/privacy-statement/
- Claude 初步判断：only privacy statement and UC copyright notice, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 www.duffield.cornell.edu
- 条款页：https://privacy.cornell.edu/
- Claude 初步判断：only privacy policy linked, no terms page found
- robots.txt：error（no）
条款：

#### 域名 gradschool.cornell.edu
- 条款页：未找到
- Claude 初步判断：no footer or terms links found
- robots.txt：error（no）
条款：

#### 域名 mie.northeastern.edu
- 条款页：https://www.northeastern.edu/privacy-information/
- Claude 初步判断：no site-wide terms of use page found; only privacy policies
- robots.txt：fetched（yes）
条款：

#### 域名 coe.northeastern.edu
- 条款页：https://www.northeastern.edu/privacy-information/
- Claude 初步判断：no site-wide terms of use page found; only privacy policies
- robots.txt：fetched（yes）
条款：

#### 域名 www.trine.edu
- 条款页：https://www.trine.edu/about/policies/privacy.aspx
- Claude 初步判断：no terms page found; privacy policy only, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 www.ucumberlands.edu
- 条款页：https://www.ucumberlands.edu/privacy-policy
- Claude 初步判断：no terms page found; privacy policy only, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 www.business.uc.edu
- 条款页：https://www.uc.edu/about/ucit/about/copyright.html
- Claude 初步判断：copyright/privacy notices only, no terms page, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 www.uc.edu
- 条款页：未找到
- Claude 初步判断：无
- robots.txt：fetched（yes）
条款：

#### 域名 cob.unt.edu
- 条款页：https://www.unt.edu/required-links.html
- Claude 初步判断：disclaimer/privacy/linking notice only, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 www.heinz.cmu.edu
- 条款页：https://www.cmu.edu/legal
- Claude 初步判断：terms limit use to personal non-commercial viewing; no explicit bot/scraping clause
- robots.txt：fetched（yes）
条款：

#### 域名 www.cmich.edu
- 条款页：https://www.cmich.edu/copyright
- Claude 初步判断：copyright notice only, no terms page, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 cmich.smartcatalogiq.com
- 条款页：未找到
- Claude 初步判断：no terms page checked for smartcatalogiq host
- robots.txt：fetched（yes）
条款：

#### 域名 publichealth.nyu.edu
- 条款页：未找到
- Claude 初步判断：no terms page in footer; only copyright notice and EO policy, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 www.publichealth.columbia.edu
- 条款页：https://www.cuimc.columbia.edu/terms-and-conditions-use
- Claude 初步判断：terms limit use to personal non-commercial purposes; no explicit automated-access clause
- robots.txt：fetched（yes）
条款：

#### 域名 sph.umich.edu
- 条款页：未找到
- Claude 初步判断：no terms page found (site blocked our fetch)
- robots.txt：fetched（yes）
条款：

#### 域名 rackham.umich.edu
- 条款页：未找到
- Claude 初步判断：no terms page found (site blocked our fetch)
- robots.txt：fetched（yes）
条款：

#### 域名 sph.emory.edu
- 条款页：https://ethicsandcompliance.emory.edu/privacy/
- Claude 初步判断：only privacy policy and copyright notice in footer, no ban on automated access found
- robots.txt：fetched（yes）
条款：

#### 域名 sph.unc.edu
- 条款页：https://unc.edu/about/privacy-statement/
- Claude 初步判断：privacy statement refers to a binding UNC-Chapel Hill Terms of Use; terms page itself not located
- robots.txt：error（no）
条款：

#### 域名 gradschool.unc.edu
- 条款页：未找到
- Claude 初步判断：无
- robots.txt：error（no）
条款：

#### 域名 cashier.unc.edu
- 条款页：未找到
- Claude 初步判断：无
- robots.txt：error（no）
条款：

## 组 ece

名额 10，已选 0；本清单提议 7 个项目（点名 0，按排序 7）。

我要加的学校：

### 按排序

#### 项目 nyu-ms-computerengineering — New York University — MS in Computer Engineering
- IPEDS：CIP 14.0901（Computer Engineering, General.），硕士授予 464，国际学生 454，STEM：是，工作表排名 1
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Electrical and Computer Engineering (Tandon)
- 页面：
  - pg-0154 program_home（program）https://engineering.nyu.edu/academics/programs/computer-engineering-ms — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0155 admissions（graduate_school）https://engineering.nyu.edu/admissions/graduate/apply/admissions-requirements — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0156 tuition（university）https://www.nyu.edu/students/student-information-and-resources/bills-payments-and-refunds/tuition-and-fee-rates.html — robots yes，条款 not_checked，网址检查 redirected 202 → https://www.nyu.edu/students/student-information-and-resources/bills-payments-and-refunds/tuition-and-fee-rates.html?challenge=d06e90d7-4d8f-4b88-9d8c-10b73beb60f1
- 建议：人工保存（按目前检查结果）
- 提示：Brooklyn, on campus; deadlines in page FAQ; sibling MS Electrical Engineering (14.1001); STEM not stated
决定：
用时（分钟）：

#### 项目 usc-ms-electricalandcomputerengineering — University of Southern California — Master of Science in Electrical and Computer Engineering
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 342，国际学生 287，STEM：是，工作表排名 2
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Ming Hsieh Department of Electrical and Computer Engineering
- 页面：
  - pg-0157 program_home（graduate_school）https://viterbigradadmission.usc.edu/programs/masters/msprograms/electrical-engineering/ms-electrical-and-computer-engineering/ — robots yes，条款 no_restriction，网址检查 error 403
  - pg-0098（已登记，沿用） admissions（graduate_school）https://viterbigradadmission.usc.edu/programs/masters/apply/ready-to-apply/ — robots yes，条款 no_restriction，网址检查 error 403
  - pg-0100（已登记，沿用） grad_school_intl（graduate_school）https://gradadm.usc.edu/lightboxes/international-students-english-proficiency/ — robots no，条款 no_restriction，网址检查 robots_unavailable
  - pg-0101（已登记，沿用） tuition（graduate_school）https://viterbigradadmission.usc.edu/tuition-funding-masters/ — robots yes，条款 no_restriction，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：formerly MSEE, so CIP 14.1001 assumed; siblings MS Computer Engineering (14.0901) and specialized MS tracks; DEN@Viterbi online excluded; viterbigradadmission.usc.edu returns 403 to our checker
决定：
用时（分钟）：

#### 项目 scu-ms-computerscienceandengineering — Santa Clara University — M.S. in Computer Science and Engineering
- IPEDS：CIP 14.0901（Computer Engineering, General.），硕士授予 282，国际学生 259，STEM：是，工作表排名 3
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Computer Science and Engineering
- 页面：
  - pg-0158 program_home（program）https://www.scu.edu/engineering/academic-programs/department-of-computer-engineering/graduate/ms-in-computer-science-and-engineering/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0159 admissions（graduate_school）https://www.scu.edu/engineering/academic-programs/graduate-admissions/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0160 tuition（university）https://www.scu.edu/bulletin/graduate/school-of-engineering/chapter-4-financial-information.html — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：quarter system, winter intake also offered (not expressible in intake_terms); CIP 14.0901 assumed; sibling MS ECE in ECE dept; delivery not stated
决定：
用时（分钟）：

#### 项目 cmu-ms-electricalandcomputerengineering — Carnegie Mellon University — MS in Electrical and Computer Engineering
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 333，国际学生 237，STEM：是，工作表排名 4
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Electrical and Computer Engineering
- 页面：
  - pg-0161 program_home（program）https://www.ece.cmu.edu/academics/ms-ece/index.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0162 requirements（department）https://www.ece.cmu.edu/admissions/graduate-requirements.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0163 faq（department）https://www.ece.cmu.edu/admissions/graduate-faq.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0164 deadlines（department）https://www.ece.cmu.edu/admissions/graduate-application-deadlines.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0165 tuition（university）https://www.cmu.edu/sfs/tuition/graduate/cit.html — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Pittsburgh flagship; also Silicon Valley, Africa, Thailand; Standard vs Advanced Study tracks; siblings MS AI Engineering, MS Software Engineering
决定：
用时（分钟）：

#### 项目 gatech-ms-electricalandcomputerengineering — Georgia Institute of Technology-Main Campus — Master of Science in Electrical and Computer Engineering
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 372，国际学生 228，STEM：是，工作表排名 5
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：School of Electrical and Computer Engineering
- 页面：
  - pg-0166 program_home（department）https://ece.gatech.edu/graduate/masters-degrees — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0167 admissions（department）https://ece.gatech.edu/future-students/graduate-admissions — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0089（已登记，沿用） tuition（university）https://bursar.gatech.edu/tuition-fees — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Atlanta on-campus MSECE, thesis/non-thesis; online MSECE, GT-Europe and BS/MS excluded
决定：
用时（分钟）：

#### 项目 umich-ms-electricalandcomputerengineering — University of Michigan-Ann Arbor — Master of Science in Electrical and Computer Engineering
- IPEDS：CIP 14.4701（Electrical and Computer Engineering.），硕士授予 321，国际学生 224，STEM：是，工作表排名 6
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Electrical and Computer Engineering
- 页面：
  - pg-0168 program_home（department）https://ece.engin.umich.edu/academics/graduate-programs/prospective-grad-students/about-the-masters-program/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0169 admissions（department）https://ece.engin.umich.edu/academics/graduate-programs/prospective-grad-students/apply-for-grad/grad-school-admissions-requirements/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0170 tuition（university）https://ro.umich.edu/tuition-residency/tuition-fees/2026-2027/graduate/full-term/college-engineering-graduate-full-term — robots yes，条款 not_checked，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：blocked: 403 to WebFetch; URL from search; MS and MSE same requirements; sibling MEng in ECE (maybe the 14.0901 count); intake_terms 未核实
决定：
用时（分钟）：

#### 项目 asu-other-electricalengineering — Arizona State University Campus Immersion — Electrical Engineering (MSE)
- IPEDS：CIP 14.1001（Electrical and Electronics Engineering.），硕士授予 256，国际学生 216，STEM：是，工作表排名 7
- 学位 / 授课 / 入学季：other MSE / on_campus / fall;spring；院系：School of Electrical, Computer and Energy Engineering
- 页面：
  - pg-0171 program_home（university）https://degrees.asu.edu/masters-phd/major/ASU00/ESEEMSE/electrical-engineering-mse — robots yes，条款 unclear，网址检查 ok 200
  - pg-0172 deadlines（department）https://ecee.engineering.asu.edu/degrees/graduate/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0173 grad_school_intl（graduate_school）https://admission.asu.edu/apply/international/graduate/english-proficiency — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0125（已登记，沿用） tuition（university）https://catalog.asu.edu/tuitionandfees/fall26graduate — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：all EE master's applicants enter the MSE; MS EE (thesis) only by transfer after admission; page lists Tempe and Online, use Tempe; sibling MS Computer Engineering (14.0901)
决定：
用时（分钟）：

## 组 fin_eng

名额 10，已选 0；本清单提议 7 个项目（点名 0，按排序 7）。

我要加的学校：

### 按排序

#### 项目 washu-ms-quantitativefinance — Washington University in St Louis — MS in Finance - Quantitative
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 231，国际学生 230，STEM：是，工作表排名 1
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Olin Business School
- 页面：
  - pg-0174 program_home（program）https://olin.washu.edu/programs/specialized-masters/ms-in-quantitative-finance/index.php — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0066（已登记，沿用） admissions（department）https://olin.washu.edu/programs/specialized-masters/on-campus-smp-apply.php — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0175 tuition（program）https://olin.washu.edu/programs/specialized-masters/ms-in-quantitative-finance/cost-aid-scholarships.php — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：自动抓取（按目前检查结果）
- 提示：STEM-designated per page; full-time day program. CIP not stated; the 230 completers may fit the larger MS in Finance better (check IPEDS). Alternatives: MS in Finance, MSF Corporate Finance, MSF Wealth & Asset Management, Flex MSF (exclude)
决定：
用时（分钟）：

#### 项目 uiuc-ms-financialengineering — University of Illinois Urbana-Champaign — MS in Financial Engineering
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 170，国际学生 165，STEM：是，工作表排名 2
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Gies College of Business / Grainger College of Engineering (joint)
- 页面：
  - pg-0176 program_home（program）https://msfe.illinois.edu/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0177 requirements（program）https://msfe.illinois.edu/admissions/requirements — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0178 admissions（program）https://msfe.illinois.edu/admissions/process — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0145（已登记，沿用） tuition（university）https://www.registrar.illinois.edu/g-tuition-rates-2627/ — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：STEM-designated professional master's; a longer option exists. Alternative: Gies MS Finance
决定：
用时（分钟）：

#### 项目 northeastern-ms-quantitativefinance — Northeastern University — MS in Quantitative Finance
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 164，国际学生 157，STEM：是，工作表排名 3
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：D'Amore-McKim School of Business
- 页面：
  - pg-0179 program_home（program）https://damore-mckim.northeastern.edu/programs/ms-quantitative-finance/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0180 admissions（graduate_school）https://damore-mckim.northeastern.edu/admissions/how-to-apply/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0181 deadlines（graduate_school）https://damore-mckim.northeastern.edu/admissions/deadlines/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0122（已登记，沿用） tuition（university）https://studentfinance.northeastern.edu/billing-payments/tuition-and-fees/ — robots yes，条款 no_restriction，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：Boston, full-time, STEM-designated. Exclude Oakland-campus MSQF and MSQF/MBA dual; alternative D'Amore-McKim MS Finance
决定：
用时（分钟）：

#### 项目 ucsd-other-quantitativefinance — University of California-San Diego — Master of Quantitative Finance (MQF)
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 133，国际学生 121，STEM：是，工作表排名 4
- 学位 / 授课 / 入学季：other MQF / on_campus / fall；院系：Rady School of Management
- 页面：
  - pg-0182 program_home（program）https://rady.ucsd.edu/programs/master-quantitative-finance/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0183 admissions（program）https://rady.ucsd.edu/programs/master-quantitative-finance/admissions/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0184 tuition（university）https://students.ucsd.edu/finances/fees/registration/2026-27/rady.html — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：formerly Master of Finance; STEM-designated; two length options. Full-time/on-campus not stated explicitly
决定：
用时（分钟）：

#### 项目 mit-other-finance — Massachusetts Institute of Technology — Master of Finance (MFin)
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 128，国际学生 119，STEM：是，工作表排名 5
- 学位 / 授课 / 入学季：other MFin / on_campus / summer；院系：Sloan School of Management
- 页面：
  - pg-0185 program_home（program）https://mitsloan.mit.edu/mfin — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0186 admissions（program）https://mitsloan.mit.edu/mfin/admissions — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0187 requirements（program）https://mitsloan.mit.edu/mfin/apply/how-to-apply — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0188 tuition（program）https://mitsloan.mit.edu/mfin/admissions/tuition-and-financial-aid — robots no，条款 not_checked，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：STEM-designated; two length formats. intake_terms 未核实 (tuition page lists summer as first term)
决定：
用时（分钟）：

#### 项目 utd-ms-finance — The University of Texas at Dallas — MS in Finance
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 148，国际学生 108，STEM：是，工作表排名 6
- 学位 / 授课 / 入学季：ms / hybrid / fall;spring;summer；院系：Naveen Jindal School of Management
- 页面：
  - pg-0189 program_home（program）https://fin.utdallas.edu/ms-finance-flex/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0019（已登记，沿用） requirements（department）https://jindal.utdallas.edu/admission-requirements/masters/ — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0142（已登记，沿用） grad_school_intl（graduate_school）https://graduate-admissions.utdallas.edu/apply-to-ut-dallas/international-students/ — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0147（已登记，沿用） tuition（university）https://bursar.utdallas.edu/tuition/tuition-rates/ — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：STEM-designated. Flex format, cannot be done fully online. Same degree also as one-year Cohort (summer start). Alternative 27.0305 candidate: MS Financial Technology and Analytics. CIP not stated; intake terms from search snippets
决定：
用时（分钟）：

#### 项目 uci-other-finance — University of California-Irvine — Master of Finance (MFin)
- IPEDS：CIP 27.0305（Financial Mathematics.），硕士授予 127，国际学生 99，STEM：是，工作表排名 7
- 学位 / 授课 / 入学季：other MFin / on_campus / fall；院系：The Paul Merage School of Business
- 页面：
  - pg-0190 program_home（program）https://merage.uci.edu/programs/masters/master-finance/index.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0191 admissions（program）https://merage.uci.edu/programs/masters/master-finance/admissions.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0192 tuition（university）https://www.reg.uci.edu/fees/2026-2027/finance.pdf — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0193 grad_school_intl（graduate_school）https://grad.uci.edu/admissions/applying-to-uci/ — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：STEM-designated; full-time, begins each fall. On-campus not stated explicitly
决定：
用时（分钟）：

## 组 ieor

名额 8，已选 0；本清单提议 6 个项目（点名 0，按排序 6）。

我要加的学校：

### 按排序

#### 项目 columbia-ms-operationsresearch — Columbia University in the City of New York — MS in Operations Research
- IPEDS：CIP 14.3701（Operations Research.），硕士授予 326，国际学生 289，STEM：是，工作表排名 1
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Industrial Engineering and Operations Research
- 页面：
  - pg-0194 program_home（department）https://www.ieor.columbia.edu/masters/operations-research — robots yes，条款 not_checked，网址检查 error 403
  - pg-0077（已登记，沿用） requirements（graduate_school）https://www.engineering.columbia.edu/admissions-aid/graduate-admissions/how-apply/application-requirements — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0051（已登记，沿用） admissions（graduate_school）https://www.engineering.columbia.edu/admissions-aid/graduate-admissions/apply-now — robots yes，条款 prohibits_automated_access，网址检查 error 403
  - pg-0078（已登记，沿用） tuition（graduate_school）https://bulletin.columbia.edu/columbia-engineering/graduate-studies/graduate-tuition-fees-payments — robots no，条款 unclear，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：blocked: 403 on WebFetch; URL from search results; older path ieor.columbia.edu/operations-research-msor also indexed. Siblings: MS IEOR, MS IE, MS Business Analytics, MS Financial Engineering, MS MS&E; online MSOR (CVN) excluded. Per search: full- or part-time, STEM, fall and spring entry
决定：
用时（分钟）：

#### 项目 tamu-ms-industrialengineering — Texas A&M University-College Station — MS in Industrial Engineering
- IPEDS：CIP 14.3501（Industrial Engineering.），硕士授予 265，国际学生 225，STEM：是，工作表排名 2
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Industrial and Systems Engineering
- 页面：
  - pg-0195 program_home（department）https://engineering.tamu.edu/industrial/academics/degrees/graduate/ms-ie.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0196 requirements（department）https://engineering.tamu.edu/industrial/admission-and-aid/graduate-admissions/index.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0197 grad_school_intl（university）https://admissions.tamu.edu/apply/international/international-graduate.html — robots yes，条款 not_checked，网址检查 broken 404
  - pg-0198 tuition（university）https://catalog.tamu.edu/graduate/tuition-fees-financial-information/tuition-required-fees — robots no，条款 not_checked，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：Thesis and non-thesis; not offered online. Sibling MEng IE (on campus plus online), MS Engineering Management, MEng Systems Engineering. Which of MS IE / MEng IE has more international students not verified
决定：
用时（分钟）：

#### 项目 ucberkeley-meng-ieor — University of California-Berkeley — Master of Engineering in Industrial Engineering and Operations Research
- IPEDS：CIP 14.3701（Operations Research.），硕士授予 219，国际学生 181，STEM：是，工作表排名 3
- 学位 / 授课 / 入学季：meng / on_campus / fall；院系：Industrial Engineering and Operations Research
- 页面：
  - pg-0199 program_home（department）https://ieor.berkeley.edu/academics/master-of-engineering/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0200 requirements（department）https://ieor.berkeley.edu/academics/master-of-engineering/how-to-apply/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0201 grad_school_intl（graduate_school）https://grad.berkeley.edu/admissions/application-process/requirements/ — robots yes，条款 not_checked，网址检查 error 403
  - pg-0202 tuition（graduate_school）https://funginstitute.berkeley.edu/programs-centers/full-time-program/learn-more/tuition-financial-aid/ — robots yes，条款 not_checked，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：Full-time professional MEng with Fung Institute core. Sibling MS IEOR (also full-time terminal) ieor.berkeley.edu/academics/master-of-science/ - owner may prefer it. intake_terms 未核实
决定：
用时（分钟）：

#### 项目 ub-ms-industrialengineering — University at Buffalo — MS in Industrial Engineering
- IPEDS：CIP 14.3501（Industrial Engineering.），硕士授予 139，国际学生 130，STEM：是，工作表排名 4
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Industrial and Systems Engineering
- 页面：
  - pg-0203 program_home（department）https://engineering.buffalo.edu/industrial-systems/masters-programs/ms-industrial-engineering.html — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0204 requirements（department）https://engineering.buffalo.edu/industrial-systems/masters-programs/admissions.html — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0134（已登记，沿用） tuition（university）https://www.buffalo.edu/studentaccounts/tuition-and-fees/fall.non-resident-full-time.html — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：自动抓取（按目前检查结果）
- 提示：Concentrations incl. Operations Research, Data Analytics Engineering; thesis/exam/capstone tracks. Online sibling ME Engineering Management excluded. Page does not state full-time/on-campus
决定：
用时（分钟）：

#### 项目 cornell-meng-orie — Cornell University — Master of Engineering in Operations Research and Information Engineering
- IPEDS：CIP 14.3701（Operations Research.），硕士授予 149，国际学生 113，STEM：是，工作表排名 5
- 学位 / 授课 / 入学季：meng / on_campus / fall；院系：Operations Research and Information Engineering
- 页面：
  - pg-0205 program_home（department）https://www.duffield.cornell.edu/orie/meng/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0206 requirements（department）https://www.duffield.cornell.edu/orie/meng/meng-admissions-requirements-ithaca/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0207 grad_school_intl（graduate_school）https://gradschool.cornell.edu/admissions/application-steps/required-tests/english-language-proficiency-requirement-2/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0081（已登记，沿用） tuition（university）https://bursar.cornell.edu/students-parents/tuition-rates-and-fees — robots no，条款 no_restriction，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：Ithaca, full-time; several concentrations (Financial Engineering has a semester in Manhattan). Spring entry only for Cornell undergrads. Cornell Tech ORIE MEng excluded
决定：
用时（分钟）：

#### 项目 northeastern-ms-industrialengineering — Northeastern University — MS in Industrial Engineering
- IPEDS：CIP 14.3501（Industrial Engineering.），硕士授予 99，国际学生 93，STEM：是，工作表排名 7
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：Mechanical and Industrial Engineering
- 页面：
  - pg-0208 program_home（department）https://mie.northeastern.edu/academics/graduate-studies/ms-inde/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0209 admissions（graduate_school）https://graduate.northeastern.edu/programs/msie-industrial-engineering/master-of-science-in-industrial-engineering/ — robots yes，条款 no_restriction，网址检查 error 403
  - pg-0210 grad_school_intl（graduate_school）https://coe.northeastern.edu/academics-experiential-learning/graduate-school-of-engineering/graduate-admissions/ — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0122（已登记，沿用） tuition（university）https://studentfinance.northeastern.edu/billing-payments/tuition-and-fees/ — robots yes，条款 no_restriction，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：blocked: certificate rejected on WebFetch; URL from search results. Boston; full- or part-time; co-op. Sibling MS Operations Research (14.3701), PlusOne excluded
决定：
用时（分钟）：

## 组 info_sys

名额 8，已选 0；本清单提议 7 个项目（点名 0，按排序 7）。

我要加的学校：

### 按排序

#### 项目 trine-ms-informationstudies — Trine University-Regional/Non-Traditional Campuses — Master of Science in Information Studies
- IPEDS：CIP 11.0401（Information Science/Studies.），硕士授予 1377，国际学生 1372，STEM：是，工作表排名 1
- 学位 / 授课 / 入学季：ms / hybrid / fall;spring;summer；院系：College of Graduate and Professional Studies
- 页面：
  - pg-0211 program_home（program）https://www.trine.edu/international/hybrid/degree-programs/master-information-studies.aspx — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0212 admissions（graduate_school）https://www.trine.edu/international/hybrid/index.aspx — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0213 tuition（graduate_school）https://www.trine.edu/international/hybrid/tuition.aspx — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0214 faq（graduate_school）https://www.trine.edu/international/hybrid/after-admission/faq.aspx — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：EXCLUSION CHECK: international students take it only as hybrid at education centers in Detroit, Phoenix or Reston (not main campus); seated classes on assigned dates; also fully online via TrineOnline; CPT can start from the first day of classes. STEM not stated. Accelerated terms; intake_terms 未核实
决定：
用时（分钟）：

#### 项目 cumberlands-ms-informationtechnology — University of the Cumberlands — Executive Master of Science in Information Technology
- IPEDS：CIP 11.0103（Information Technology.），硕士授予 941，国际学生 766，STEM：是，工作表排名 2
- 学位 / 授课 / 入学季：ms / hybrid / fall;spring;summer；院系：Executive Programs (International Graduate Services)
- 页面：
  - pg-0215 program_home（program）https://www.ucumberlands.edu/academics/executive/masters-information-technology — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0216 requirements（university）https://www.ucumberlands.edu/admissions/admission-requirements — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0217 tuition（university）https://www.ucumberlands.edu/tuition-aid/tuition — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：EXCLUSION CHECK: executive format for F-1 students, coursework mostly online plus a mandatory residency weekend per course each term at sites in several cities; every term includes an applied learning practicum (CPT from the first term). Cannot be done fully in person; a fully online MSIT also exists. Page shows outdated term dates
决定：
用时（分钟）：

#### 项目 utd-ms-informationtechnologyandmanagement — The University of Texas at Dallas — MS in Information Technology and Management
- IPEDS：CIP 11.0401（Information Science/Studies.），硕士授予 800，国际学生 709，STEM：是，工作表排名 3
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring;summer；院系：Naveen Jindal School of Management
- 页面：
  - pg-0218 program_home（program）https://infosystems.utdallas.edu/ms-information-technology/ — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0019（已登记，沿用） requirements（department）https://jindal.utdallas.edu/admission-requirements/masters/ — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0219 faq（program）https://jindal.utdallas.edu/ms-itm-faq/ — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0020（已登记，沿用） deadlines（graduate_school）https://graduate-admissions.utdallas.edu/apply-to-ut-dallas/deadlines-and-fees/ — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0147（已登记，沿用） tuition（university）https://bursar.utdallas.edu/tuition/tuition-rates/ — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：自动抓取（按目前检查结果）
- 提示：STEM-designated. Evening classes, large part-time share; separate MS ITM Online and cohort versions exist (do not use). Siblings: MS Business Analytics and AI, MS Management Science
决定：
用时（分钟）：

#### 项目 cincinnati-ms-informationsystems — University of Cincinnati-Main Campus — MS in Information Systems
- IPEDS：CIP 11.0103（Information Technology.），硕士授予 773，国际学生 706，STEM：是，工作表排名 4
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Carl H. Lindner College of Business
- 页面：
  - pg-0220 program_home（program）https://www.business.uc.edu/programs-degrees/graduate/specialized-masters/information-systems.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0221 admissions（program）https://www.business.uc.edu/future-students/admissions-requirements/graduate/application-checklist.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0222 deadlines（graduate_school）https://www.business.uc.edu/future-students/admissions-requirements/graduate/application-deadlines.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0223 tuition（university）https://www.uc.edu/about/bursar/tuition-fees/graduate---professional-students.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0224 other（university）https://www.uc.edu/about/bursar/tuition-fees/non-resident-surcharges.html — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：STEM-designated; full-time or part-time. Separate online MSIS at online.uc.edu (do not use). Applicants abroad: fall full-time only
决定：
用时（分钟）：

#### 项目 unt-ms-informationsystemsandtechnologies — University of North Texas — M.S. in Information Systems & Technologies
- IPEDS：CIP 11.0103（Information Technology.），硕士授予 457，国际学生 450，STEM：是，工作表排名 5
- 学位 / 授课 / 入学季：ms / hybrid / fall;spring；院系：G. Brint Ryan College of Business (ITDS department)
- 页面：
  - pg-0225 program_home（program）https://cob.unt.edu/masters/programs/ms-information-systems.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0226 admissions（graduate_school）https://cob.unt.edu/masters/prospective-students/index.html — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0117（已登记，沿用） grad_school_intl（university）https://www.unt.edu/admissions/international/english-language-requirements.html — robots yes，条款 no_restriction，网址检查 ok 200
  - pg-0149（已登记，沿用） tuition（university）https://studentaccounting.unt.edu/tuition-and-fees — robots yes，条款 no_restriction，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：STEM. On campus, online and hybrid. CIP 11.0103 vs 11.0401 not confirmed; sibling MS Information Science (College of Information) may be the 11.0401 one or the larger. Also MS Business Analytics
决定：
用时（分钟）：

#### 项目 cmu-other-informationsystemsmanagement — Carnegie Mellon University — Master of Information Systems Management (MISM)
- IPEDS：CIP 11.0103（Information Technology.），硕士授予 632，国际学生 441，STEM：是，工作表排名 6
- 学位 / 授课 / 入学季：other MISM / on_campus / fall；院系：Heinz College
- 页面：
  - pg-0227 program_home（program）https://www.heinz.cmu.edu/programs/information-systems-management-master — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0228 admissions（program）https://www.heinz.cmu.edu/programs/information-systems-management-master/admissions-how-to-apply — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0229 grad_school_intl（graduate_school）https://www.heinz.cmu.edu/admissions/checklist/exam-results — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0230 tuition（university）https://www.cmu.edu/sfs/tuition/graduate/index.html — robots yes，条款 unclear，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Chosen over MSISPM (too small for the IPEDS count); CIP 11.0103 not confirmed for either - owner check. Full-time in person, Pittsburgh; tracks Traditional and BIDA; STEM-designated; internship required. Siblings: MSISPM, MSIT (mostly part-time), Adelaide MISM
决定：
用时（分钟）：

#### 项目 cmich-ms-informationsystems — Central Michigan University — Master of Science in Information Systems (MSIS)
- IPEDS：CIP 11.0103（Information Technology.），硕士授予 407，国际学生 388，STEM：是，工作表排名 7
- 学位 / 授课 / 入学季：ms / on_campus / fall;spring；院系：College of Business Administration - Department of Business Information Systems
- 页面：
  - pg-0231 program_home（program）https://www.cmich.edu/program/information-systems-ms — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0232 requirements（university）https://cmich.smartcatalogiq.com/2026-2027/graduate-bulletin/colleges-and-departments/business-information-systems-department-of/information-systems-m-s — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0233 admissions（graduate_school）https://www.cmich.edu/international-admissions/graduate/apply-international — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0234 grad_school_intl（university）https://www.cmich.edu/international-admissions/contact/english-proficiency — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0235 tuition（university）https://www.cmich.edu/offices-departments/finance-administrative-services/financial-services-reporting/student-account-services-university-billing/tuition-and-fee-rates — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：On campus (Mount Pleasant) and online via CMU Online (do not use online). Tracks: SAP enterprise systems, cybersecurity, project management, business data analytics. STEM not stated
决定：
用时（分钟）：

## 组 biostat

名额 6，已选 0；本清单提议 5 个项目（点名 0，按排序 5）。

我要加的学校：

### 按排序

#### 项目 nyu-ms-biostatistics — New York University — MS in Biostatistics
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 107，国际学生 94，STEM：是，工作表排名 1
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Biostatistics (School of Global Public Health)
- 页面：
  - pg-0236 program_home（program）https://publichealth.nyu.edu/programs/master-science-biostatistics — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0237 admissions（graduate_school）https://publichealth.nyu.edu/admissions/apply/ms-biostatistics — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：In person, full-time or part-time, STEM-designated. Sibling: MPH Biostatistics concentration. No tuition page found (GPH points to Bursar lookup tool). intake_terms 未核实
决定：
用时（分钟）：

#### 项目 columbia-ms-biostatistics — Columbia University in the City of New York — MS in Biostatistics (Theory and Methods track)
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 119，国际学生 92，STEM：是，工作表排名 2
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Biostatistics (Mailman School of Public Health)
- 页面：
  - pg-0238 program_home（program）https://www.publichealth.columbia.edu/academics/degrees/master-science/theory-methods — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0239 admissions（graduate_school）https://www.publichealth.columbia.edu/become-student/how-apply/process/application-components — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0240 deadlines（graduate_school）https://www.publichealth.columbia.edu/become-student/how-apply/deadlines — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0241 tuition（graduate_school）https://www.publichealth.columbia.edu/become-student/how-apply/financial-aid/tuition-fees — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：Tracks: Theory and Methods (chosen), Public Health Data Science, Pharmaceutical Statistics, Statistical Genetics, Clinical Research Methods; check whether tracks are separate application options (06 §2.1). Also MPH Biostatistics. STEM not stated
决定：
用时（分钟）：

#### 项目 umich-ms-biostatistics — University of Michigan-Ann Arbor — MS in Biostatistics
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 80，国际学生 58，STEM：是，工作表排名 3
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Biostatistics (School of Public Health)
- 页面：
  - pg-0242 program_home（program）https://sph.umich.edu/biostat/programs/masters-biostat.html — robots yes，条款 not_checked，网址检查 error 403
  - pg-0243 admissions（department）https://sph.umich.edu/biostat/apply-ms-biostatistics.html — robots yes，条款 not_checked，网址检查 error 403
  - pg-0244 tuition（graduate_school）https://sph.umich.edu/admissions/tuition-fees.html — robots yes，条款 not_checked，网址检查 error 403
  - pg-0245 grad_school_intl（graduate_school）https://rackham.umich.edu/admissions/tests — robots yes，条款 not_checked，网址检查 error 403
- 建议：人工保存（按目前检查结果）
- 提示：blocked: HTTP 403 on WebFetch; URL from search results. Siblings: MS Health Data Science (separate MS), Accelerated MS (UMich undergrads only). intake_terms 未核实
决定：
用时（分钟）：

#### 项目 emory-other-biostatistics — Emory University — Master of Science in Public Health in Biostatistics (MSPH)
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 53，国际学生 34，STEM：是，工作表排名 4
- 学位 / 授课 / 入学季：other MSPH / on_campus / fall；院系：Department of Biostatistics and Bioinformatics (Rollins School of Public Health)
- 页面：
  - pg-0246 program_home（program）https://sph.emory.edu/degrees-programs/msph/biostatistics — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0247 admissions（graduate_school）https://sph.emory.edu/admissions/how-to-apply/masters-programs — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0248 tuition（graduate_school）https://sph.emory.edu/admissions/tuition-funding — robots yes，条款 not_checked，网址检查 ok 200
  - pg-0249 grad_school_intl（graduate_school）https://sph.emory.edu/admissions/how-to-apply/international-applicants — robots yes，条款 not_checked，网址检查 ok 200
- 建议：人工保存（按目前检查结果）
- 提示：FLAG: no MS exists; MSPH is the research-track flagship. Full-time, in person. Siblings: MPH Biostatistics, BA/BS-MSPH (Emory undergrads only). STEM not stated. intake_terms 未核实
决定：
用时（分钟）：

#### 项目 unc-ms-biostatistics — University of North Carolina at Chapel Hill — MS in Biostatistics
- IPEDS：CIP 26.1102（Biostatistics.），硕士授予 48，国际学生 30，STEM：是，工作表排名 5
- 学位 / 授课 / 入学季：ms / on_campus / fall；院系：Department of Biostatistics (Gillings School of Global Public Health)
- 页面：
  - pg-0250 program_home（program）https://sph.unc.edu/bios/ms/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0251 admissions（graduate_school）https://gradschool.unc.edu/admissions/instructions/ — robots no，条款 not_checked，网址检查 robots_unavailable
  - pg-0252 tuition（university）https://cashier.unc.edu/tuition-fees/graduate-programs — robots no，条款 not_checked，网址检查 robots_unavailable
- 建议：人工保存（按目前检查结果）
- 提示：blocked: HTTP 403 on sph.unc.edu; URL from search results. Residential, STEM-designated per search. Sibling: BSPH/MS dual (UNC undergrads only). intake_terms 未核实
决定：
用时（分钟）：

## 补登页面

（没有补登页面）

## 汇总

- 本清单项目 32 个，页面 118 个（含沿用的已登记页面）。条款未判断的域名按不能抓取算。
- 按排序：项目 32 个，页面 118 个，不能自动抓取 103 个（87%）；若条款都判为 no_restriction：44 个（37%）。06 §2.8 上限 30%。
- 点名：项目 0 个，页面 0 个，不能自动抓取 0 个（0%）；若条款都判为 no_restriction：0 个（0%）。按需求选入，不受比例限制。

