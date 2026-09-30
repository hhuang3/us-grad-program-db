# 03 STEM 判断规则

> 状态：v1.1（Phase 1b）。§3（PDF 结构理解）与 §4.2（系列展开）已于 2026-09-30 确认；§5 按确认后的五值枚举修订。

## 0. 核心声明

**“CIP 在清单上”不等于“某个项目是 STEM 认定项目”。**
项目的 CIP 由学校决定，写在该学生的 I-20 上。DHS 清单只回答“这个 CIP 代码是不是 STEM 领域”。只有当学校自己声明了该项目的 CIP，并且这个 CIP 在清单上时，才能给出 `confirmed_by_school`。我们根据名称或 IPEDS 推断出的 CIP，永远不能得出 `confirmed_by_school`。

---

## 1. CIP 代码格式与归一化

### 1.1 标准格式

| 层级 | 标准格式 | 例 |
|---|---|---|
| 6 位 | 字符串 `"NN.NNNN"` | `"03.0204"` |
| 4 位 | 字符串 `"NN.NN"` | `"30.70"` |
| 2 位 | 字符串 `"NN"` | `"27"` |

前导零必须保留。所有表、所有函数都只使用这些格式。

### 1.2 `normalize_cip6(value) -> str`

只做**格式**归一化，不检查代码是否存在于 CIP 2020（那是 §1.4 的事）。按顺序执行：

1. 类型：
   - `str`：进入第 2 步。
   - `float`：先转为 `repr(value)` 再按字符串处理。例如 `3.0204` → `"3.0204"`。浮点数末尾的 0 会丢失（如 `27.05` 可能原本是 `27.0500`），这种情况会在第 4 步因小数位不足 4 位而报错。这是故意的：不猜。
   - `int`、`bool`、`None` 及其他类型：抛 `TypeError`。
2. 去掉首尾空白（含 ` ` 不换行空格、制表符、换行）。
3. 如果整体是 Excel 保护写法 `="…"`，取出引号内的内容，再去一次首尾空白。
4. 匹配以下规则之一（全串匹配）：

| 规则 | 正则 | 转换 | 例 |
|---|---|---|---|
| A | `^\d{2}\.\d{4}$` | 原样 | `"03.0204"` → `"03.0204"` |
| B | `^\d\.\d{4}$` | 左补一个 0 | `"3.0204"` → `"03.0204"` |
| C | `^\d{6}$` | 在第 2 位后插入点 | `"030204"` → `"03.0204"` |

5. 其他一律抛 `CipFormatError`（`ValueError` 的子类），错误信息里包含原始输入的 `repr`。以下都会报错：
   - 空串、`"99"`（IPEDS 合计行）、`"03.02"`（4 位代码不接受）、`"3.02"`、`"27.05"`
   - `"30204"`（5 位数字；可能是丢了前导零，也可能不是，不猜）
   - `"03-0204"`、`"03.0204a"`、`"03 .0204"`、`"03.02 04"`、`"０３.０２０４"`（全角数字）
   - `"003.0204"`、`"03.02040"`

### 1.3 `normalize_cip4(value) -> str`

用于 Scorecard 这类 4 位代码的来源。只接受 `str`；执行同 §1.2 的第 2、3 步；然后：

| 规则 | 正则 | 转换 | 例 |
|---|---|---|---|
| A | `^\d{2}\.\d{2}$` | 原样 | `"30.70"` |
| B | `^\d{4}$` | 在第 2 位后插入点 | `"3070"` → `"30.70"`，`"0110"` → `"01.10"` |

其他（含 `"3.70"`、`"370"`）抛 `CipFormatError`。

### 1.4 存在性

`is_valid_cip2020(code6, cip2020) -> bool`：`code6` 必须已经是标准 6 位格式，判断它是否属于 CIP 2020 的有效 6 位代码。有效的定义是 `Action ∉ {"Moved from", "Deleted"}`，见 `01_reference_data.md` §2。

---

## 2. 输入：解析后的 STEM 清单

- `data/ref/stem_list.csv`：`cip_code, title, series, page`，只包含 PDF 中**真正的 6 位 CIP 代码**行（定义见 §3.3）。`cip_code` 唯一，且都是标准 6 位格式。
- `data/ref/stem_core_series.csv`：`series, title, page`，即 PDF 中以 2 位代码认定的核心系列（预期为 14、26、27、40）。
- 两个文件都在 `derived.csv` 中登记，`input_sha256` = STEM PDF 的 sha256 + CIP 2020 CSV 的 sha256（解析时需要用 CIP 2020 区分真实代码和分组标题行，见 §3.3）。

---

## 3. STEM PDF 结构（已确认）

依据：`stemList2024.pdf`（Last Updated: July 22, 2024），2026-09-30 逐页查看文本与坐标。

### 3.1 页面组成

- **每页页眉**（3 行）：“Homeland Security Investigations” / “National Security Division” / “Student and Exchange Visitor Program”。
- **第 1 页正文说明**：标题 “DHS STEM Designated Degree Program List”，“Last Updated: July 22, 2024”。随后是两段关键说明：
  - 第一段（第 1 页第 3 段）：“this list designates the following four primary CIP series at the 2-digit CIP code level: Engineering (14), Biological and Biomedical Sciences (26), Mathematics and Statistics (27) and Physical Sciences (40). Any new additions to those areas will automatically be included on this STEM Designated Degree Program List.”
  - 第二段：“This list also includes CIPs from the following 18 related CIP series at the 6-digit CIP code level: …”，列出 01, 03, 04, 09, 10, 11, 13, 15, 28, 29, 30, 41, 42, 43, 45, 49, 51, 52。
- **每页的表头**（多行）：“Two-Digit Series” | “2020 CIP Code” | “CIP Code Title”。
- **每页页脚**：“Last updated: July 22, 2024”加页码（“1 | P a g e”）。
- 数据行共 540 行、16 页；三列的 x 坐标大致为：系列 ≈ 79pt，代码 ≈ 144pt，标题 ≈ 216pt 起。

### 3.2 行的解析

- 一行数据 = 同一基线（y 坐标相差 ≤ 2pt）上，系列列有 2 位数字，代码列有 `NN.NNNN`。
- **标题换行**：标题较长时会折成多行，并且**上下分布在代码行两侧**（代码行本身可能没有标题文字）。例如 14.0201 的标题 “Aerospace, Aeronautical, and Astronautical/Space Engineering, General.” 第一段在代码行上方、第二段在下方。规则：标题列里所有不在代码行基线上的文字片段，归入**垂直距离最近**的代码行，并按 y 坐标从上到下拼接。距离相等时报错，不猜。
- **词间距**：PDF 中的字符间距不规则（如 “Pre - Engineering”）。标题的处理：合并连续空白为一个空格，去掉首尾空白，**其他不做修改**（不改标点、不修正连字符两边的空格）。解析时另外对比 CIP 2020 的官方标题，比较前把两边都去掉所有空白并转小写；不一致的写进解析报告，但不修改 PDF 标题。
- **代码被拆开**：至少一处代码被拆成多个文本片段（“43 . 0407”）。规则：代码列内的片段先去掉空白再拼接，然后再匹配 `NN.NNNN`。
- 系列列的值必须等于代码的前两位，否则报错。

### 3.3 真正的 6 位代码行 vs 分组标题行

核心系列（14/26/27/40）在表中还列出了 2 位和 4 位的**分组标题**，写成 6 位格式：如 `14.0000 ENGINEERING.`（2 位，标题全大写）、`14.0100 Engineering, General.`（4 位）。这些不是 CIP 2020 中的 6 位代码。与此同时，`15.0000`、`41.0000` 在 CIP 2020 中**是**真实的 6 位代码。所以不能只看末尾是不是 00。

每一行按顺序判定：

1. `cip_code` 是 CIP 2020 的有效 6 位代码 → **6 位代码行**，写入 `stem_list.csv`。
2. 否则，若形如 `NN.0000` 且 `NN` 是 CIP 2020 的有效 2 位代码 → **系列标题行**，写入 `stem_core_series.csv`。
3. 否则，若形如 `NN.NN00` 且 `NN.NN` 是 CIP 2020 的有效 4 位代码 → **4 位分组标题行**，丢弃（只计数）。
4. 否则 → 报错（清单中出现了 CIP 2020 没有的代码，需要人工处理）。

用 2024 版清单核对的结果：540 行 = **466** 个 6 位代码 + **74** 个分组标题（4 个系列标题 + 70 个 4 位标题，全部属于 14/26/27/40）。没有无法解释的行。

### 3.4 一致性校验（任何一项不符就报错，交人工处理）

- 从第 1 页说明文字中解析出的 2 位核心系列集合（正则 `\((\d{2})\)`，只在 “at the 2-digit CIP code level” 这句到 “Any new additions” 这句之间取值）必须等于 §3.3 得到的系列标题集合。2024 版两者都是 {14, 26, 27, 40}。
- 6 位代码无重复。
- 页眉或页脚中的 “Last Updated” 日期要全文一致，写进解析报告，作为清单版本日期。

---

## 4. `cip_on_stem_list(cip, ref) -> bool`

`ref` 是由 `stem_list.csv`、`stem_core_series.csv`、`cip2020.csv` 构成的只读对象。

### 4.1 规则

1. `code = normalize_cip6(cip)`，格式错误时直接向上抛出。
2. 若 `code` 不是有效的 CIP 2020 6 位代码 → 抛 `UnknownCipError`（`ValueError` 的子类）。不返回 False，因为“不存在的代码”和“不在清单上”是两回事。
3. 若 `code` 在 `stem_list.csv` 中（6 位精确匹配） → `True`。
4. 若 `code` 的前两位在 `stem_core_series.csv` 中 → `True`（系列展开，见 §4.2）。
5. 其他 → `False`。

### 4.2 系列展开的依据（已确认，照原文实现）

- 原文位置：2024 版清单 PDF 第 1 页正文第 3 段（引文见 §3.1）；89 FR 59748 第 59749 页 “How does DHS assess nominations?” 一节：“any new additions to those areas are automatically included on the STEM list”；法规依据 8 CFR 214.2(f)(10)(ii)(C)(2)(i)。
- 含义：14/26/27/40 系列中**任何**有效的 CIP 2020 6 位代码都在清单上，即使 PDF 表格没有逐条列出。
- 现状：2024 版 PDF 对这四个系列的 215 个有效 6 位代码**已全部逐条列出**。所以对 CIP 2020 而言，规则 4 目前不会改变任何结果，只是为了与原文一致而保留。
- 不展开的系列：其余 18 个相关系列只按 6 位精确匹配。例如 `30.7099 Data Science, Other.` 是有效的 CIP 2020 代码，但不在清单上 → `False`。

### 4.3 “展开规则不改变结果”的哨兵检查

目的：清单或 CIP 更新时，第一时间发现展开规则开始产生实际影响。

- 定义 `cip_on_stem_list_exact(code)`：只执行 §4.1 的第 1–3 步，然后返回 False（即不做系列展开）。
- 断言：对 `data/ref/cip2020.csv` 中**每一个**有效 6 位代码，`cip_on_stem_list(code) == cip_on_stem_list_exact(code)`。
- 该断言针对**已提交的真实派生表**（2024 版清单 + CIP 2020），作为数据测试运行；派生表不存在时测试失败，不跳过。
- 断言失败时，要列出所有“只因展开才为 True”的代码。此时不要改测试，先停下来讨论。

---

## 5. 项目层面的 `stem_status`（Phase 1 只定义并测试推导函数）

### 5.1 枚举（五个值）

| 值 | 含义 |
|---|---|
| `confirmed_by_school` | 学校官方页面（国际学生办公室的 STEM 项目列表、项目页、I-20 说明等）明确写出该项目的 CIP，且该 CIP 在清单上 |
| `not_on_list` | 学校声明的 CIP 不在清单上 |
| `cip_on_list_unconfirmed` | 该项目的 CIP 不是学校声明的（我们推断的，或来源不明），且在清单上 |
| `cip_not_on_list_unconfirmed` | 该项目的 CIP 不是学校声明的（我们推断的，或来源不明），且不在清单上 |
| `unknown` | 没有任何 CIP 信息 |

### 5.2 `derive_stem_status(cip_code, cip_source, ref) -> str`

- `cip_source` 的取值沿用 `02_field_dictionary.md`：`school_stem_page / program_page / i20_statement / ipeds_inferred / unknown`。
- 学校声明集合 `SCHOOL_DECLARED = {school_stem_page, program_page, i20_statement}`；非学校声明集合 `NOT_DECLARED = {ipeds_inferred, unknown}`。
- “cip_code 为空”指 `None`，或去掉首尾空白后为空串。
- `on_list = cip_on_stem_list(cip_code, ref)`，只在 cip_code 非空时计算。

**完整真值表**（按行号顺序判定，先命中者生效；共覆盖 5 种 cip_source × {空, 非空} × {在清单, 不在清单}，外加异常输入）：

| # | cip_source | cip_code | on_list | 结果 |
|---|---|---|---|---|
| 1 | 不在上述 5 个取值中（含 None） | 任意 | – | 抛 `ValueError` |
| 2 | 任意合法值 | 非空但格式错误 | – | 抛 `CipFormatError`（来自 `normalize_cip6`） |
| 3 | 任意合法值 | 格式正确但不是有效的 CIP 2020 代码 | – | 抛 `UnknownCipError` |
| 4 | `school_stem_page` | 非空 | True | `confirmed_by_school` |
| 5 | `school_stem_page` | 非空 | False | `not_on_list` |
| 6 | `program_page` | 非空 | True | `confirmed_by_school` |
| 7 | `program_page` | 非空 | False | `not_on_list` |
| 8 | `i20_statement` | 非空 | True | `confirmed_by_school` |
| 9 | `i20_statement` | 非空 | False | `not_on_list` |
| 10 | `ipeds_inferred` | 非空 | True | `cip_on_list_unconfirmed` |
| 11 | `ipeds_inferred` | 非空 | False | `cip_not_on_list_unconfirmed` |
| 12 | `unknown` | 非空 | True | `cip_on_list_unconfirmed` |
| 13 | `unknown` | 非空 | False | `cip_not_on_list_unconfirmed` |
| 14 | `unknown` | 空 | – | `unknown` |
| 15 | `school_stem_page` / `program_page` / `i20_statement` / `ipeds_inferred` | 空 | – | 抛 `ValueError`（声称有来源却没有代码，数据自相矛盾） |

- 第 12、13 行：有 CIP 但来源不明，按“非学校声明”处理，永远不能得出 `confirmed_by_school` 或 `not_on_list`。
- 第 15 行：不静默降级为 `unknown`，而是报错，交人工处理。
- 异常照常向上抛出，不转成 `unknown`（不静默吞掉错误）。
