# Legacy Code Analyzer & Optimizer

## 概述

**Legacy Code Analyzer & Optimizer** 是一款专为 TRAE SOLO 平台构建的专业级代码分析工具 Skill。

该 Skill 专门针对遗留代码、陌生代码库、非规范代码进行深度分析、可维护性优化与风险预警，解决开发者"看不懂、不敢改、改不好"的核心痛点。

**核心原则**：不做新代码生成，只聚焦已有代码的深度语义解读、设计意图推断、技术债务量化、修改风险评估及重构辅助。

---

## 技能目录结构

```
legacy-code-analyzer/
├── SKILL.md                       # 技能入口定义文件（YAML frontmatter + 21个 Mermaid 可视化图表）
├── analyzer-guideline.md          # 分析工作流详细指南
├── README.md                      # 使用说明
├── demo_visual.py                 # 可视化全流程演示脚本
├── demo_visual_report.md          # 演示报告输出
└── modules/
    ├── __init__.py                # 模块集成入口（LegacyCodeAnalyzer 类 + ReportRenderer）
    ├── shared.py                  # 共享基础层（Language 枚举、常量、安全模式）
    ├── scanner.py                 # 模块 1: 代码元数据与结构分析
    ├── semantic_analyzer.py       # 模块 2: 语义解析与设计意图推断
    ├── dependency_analyzer.py     # 模块 3: 依赖关系挖掘与耦合度分析
    ├── quality_evaluator.py       # 模块 4: 代码质量评估与缺陷检测
    ├── risk_advisor.py            # 模块 5: 风险预警与修改指导
    ├── test_generator.py          # 模块 6: 自动化测试与重构辅助
    ├── interactive_explorer.py    # 模块 7: 交互式代码探索
    ├── requirement_tracer.py      # 模块 8: 目标性评估与需求覆盖分析
    └── report_renderer.py         # 可视化报告渲染引擎（Mermaid + Markdown）
```

---

## 功能模块一览

| 模块 | 功能 | 入口函数 |
|------|------|----------|
| **1. 代码扫描** | 全量扫描、语言识别、元数据统计、3层架构Mermaid图、语言分布饼图、代码演化时间线 | `scan_project()` |
| **2. 语义解析** | AST拆解、控制流/数据流分析、5色流程图、设计模式思维导图、临时方案标记 | `analyze_semantics()` |
| **3. 依赖分析** | 显式/隐式依赖图谱、耦合度柱状图、循环检测、数据依赖时间线 | `analyze_dependencies()` |
| **4. 质量评估** | 圈复杂度/MI/DIT/CBO/LM-CC、缺陷饼图、5维质量评分雷达、CC/MI对比柱线图 | `evaluate_quality()` |
| **5. 风险预警** | 风险传播链Mermaid图、修改优先级时间线、连锁影响分析、重构优先级 | `generate_risk_advice()` |
| **6. 测试重构** | 测试覆盖类型饼图、重构前后架构对比Mermaid图、重构方案与验证检查点 | `generate_tests()` / `plan_refactoring()` |
| **7. 交互探索** | 自然语言查询、7色查询分类决策树、5色函数流程图、设计意图咨询 | `explore_code()` |
| **8. 需求覆盖** | 需求分类思维导图、覆盖度饼图、追溯工作流Mermaid图、RTM矩阵、偏离检测 | `trace_requirements()` |

---

## 如何在 TRAE SOLO 中加载并使用

### 步骤 1：安装技能文件

将 `legacy-code-analyzer/` 目录复制到 TRAE SOLO 的技能目录：

```bash
cp -r legacy-code-analyzer/ /data/user/builtin/code/default/skills/
```

### 步骤 2：验证技能注册

在 TRAE SOLO 中，技能通过 `SKILL.md` 的 YAML frontmatter 注册：

```yaml
---
name: "legacy-code-analyzer"
description: "Legacy Code Analyzer & Optimizer - ..."
---
```

技能加载后，AI Agent 在对话中可以通过 Skill 工具调用此技能。

### 步骤 3：在对话中使用

直接在 TRAE SOLO 对话中描述你的分析需求，技能会自动激活。例如：

```
"请分析 /path/to/my-project 这个代码库"
```

```
"帮我看看 src/services/order_service.py 的设计意图和风险"
```

```
"这是我的需求文档：[粘贴需求]，请对照代码库做目标性评估"
```

### 步骤 4：选择分析范围

技能激活后，AI Agent 会使用 `AskUserQuestion` 确认分析范围：

- **完整分析**（推荐）：执行所有 8 个模块
- **仅结构与元数据**：只执行模块 1
- **语义解析与设计意图**：只执行模块 2
- **依赖与耦合度分析**：只执行模块 3
- **代码质量评估**：只执行模块 4
- **风险预警与修改指导**：只执行模块 5
- **测试与重构辅助**：只执行模块 6
- **目标性评估**：只执行模块 8（需提供需求文档）

---

## 编程方式使用（Python API）

```python
from modules import LegacyCodeAnalyzer, quick_scan, quick_quality, full_analysis, ReportRenderer

# 初始化分析器
analyzer = LegacyCodeAnalyzer("/path/to/your/project")

# 方式 1：逐步分析
scan_result = analyzer.scan()                    # 模块 1
dependency_result = analyzer.analyze_dependencies()  # 模块 3
quality_result = analyzer.evaluate_quality()     # 模块 4

# 方式 2：生成精美可视化报告
scan = analyzer.scan()
quality = analyzer.evaluate_quality()
risk = analyzer.advise_risks()
renderer = ReportRenderer("My Project")
report_md = renderer.render_full_report(scan, quality, risk)

# 方式 3：完整分析（含 Markdown 报告）
report = analyzer.run_full_analysis(generate_markdown=True)
print(report["markdown_report"])  # 完整可视化的 Markdown 报告

# 方式 4：含需求对照的完整分析
report = analyzer.run_full_analysis(
    requirements="""
    FR-001: 用户注册功能，支持邮箱验证
    FR-002: 订单创建，含库存校验
    NFR-001: API 响应时间 < 200ms
    """,
    generate_markdown=True,
)

# 方式 5：便捷函数
scan = quick_scan("/path/to/project")
quality = quick_quality("/path/to/project")
full = full_analysis("/path/to/project", requirements="...")
```

---

## 支持的语言

| 语言 | 识别特征 | 分析重点 |
|------|----------|----------|
| **Python** | .py, requirements.txt, setup.py | 动态类型、装饰器、生成器 |
| **Java** | .java, pom.xml, build.gradle | 继承深度、接口设计、Spring 注解 |
| **JavaScript** | .js, .jsx, .ts, package.json | 异步处理、闭包、原型链 |
| **C++** | .cpp, .h, CMakeLists.txt | 内存管理、指针安全、模板 |

---

## 输出形式

技能输出包含以下结构化内容（含 **21 种 Mermaid 可视化图表**）：

1. **分析报告**：Markdown 格式，结构化分段，含表格和 Mermaid 图表
2. **Mermaid 可视化图谱（7 种图表类型）**：
   - `flowchart` / `graph` — 分层架构图、函数控制流、依赖拓扑图、重构对比图
   - `pie` — 语言分布、缺陷风险分布、测试覆盖类型、需求覆盖度
   - `timeline` — 代码演化时间线、修改优先级时间线、数据依赖流
   - `mindmap` — 设计模式分类树、需求分类结构
   - `xychart-beta` — 模块耦合度对比柱状图、CC/MI 对比柱线图
   - `gantt` — 重构任务排期甘特图
   - `block-beta` — 需求追溯工作流
3. **需求覆盖矩阵 (RTM)**：Markdown 表格，含状态图标（✅ ⚠️ ❌ 🔮）
4. **代码引用**：`文件路径:L行号` 格式精确标注
5. **风险等级**：统一使用 🔴高 / 🟡中 / 🟢低 标识
6. **配色规范**：所有 Mermaid 图使用 `classDef` 专业配色 — 🔵蓝(发现层) 🟠橙(分析层) 🟢绿(建议层) 🔴红(风险) 🟣紫(目标)

---

## 关键依赖参考

本技能在分析过程中参考以下标准：

| 标准 | 用途 |
|------|------|
| ISO/IEC 5055:2021 | 软件质量度量标准 — 缺陷检测对照基准 |
| OWASP Top 10:2021 | Web 安全漏洞分类 — 安全漏洞检测 |
| McCabe 圈复杂度 | 复杂度度量 — 可维护性评分 |
| LM-CC | 逻辑模块复杂度 — 新型复杂度度量补充 |
| tree-sitter | 通用 AST 解析 — 多语言语法树构建 |
| jieba | 中文分词（可选）— 中文 NLP 预处理 |
| Mermaid | 图表渲染 — 支持 flowchart/graph/pie/timeline/mindmap/xychart/gantt/block-beta 7类图表 |
| classDef | Mermaid 节点样式 — 使用 `fill`/`stroke`/`color`/`stroke-width` 属性实现专业配色 |

---

## 常见使用场景

### 场景 1：接手陌生代码库

```
"我刚接手这个项目，帮我全面分析一下 /path/to/project"
```

技能输出：元数据报告 + 结构图谱 + 语义分析 + 质量评估 + 风险预警

### 场景 2：评估代码质量

```
"帮我检查 /path/to/project 的代码质量，重点关注安全问题"
```

技能输出：质量评分 + 缺陷清单（按风险等级分类）+ OWASP 安全扫描结果

### 场景 3：重构前评估

```
"我打算重构 src/services/ 模块，帮我评估风险和影响范围"
```

技能输出：风险预警 + 连锁影响分析 + 修改指南 + 重构方案

### 场景 4：需求验收

```
"这是我的需求文档：[粘贴]，帮我看看代码实现了多少"
```

技能输出：需求覆盖矩阵 (RTM) + 偏离分析 + 缺失功能优先级清单 + 补全建议

### 场景 5：理解特定代码

```
"src/utils/auth.py 里的 verify_token 函数是做什么的？为什么这样设计？"
```

技能输出：功能解释 + 设计意图推断 + 流程图 + 风险标注

---

## 模块独立性

各模块相互解耦，可独立启用或组合使用。模块间通过明确定义的接口传递数据：

```
Module 1 (scanner) ────→ 元数据
Module 2 (semantic) ───→ 语义分析结果
Module 3 (dependency) ─→ 依赖图 + 耦合度
Module 4 (quality) ────→ 质量指标 + 缺陷列表
Module 5 (risk) ───────→ 风险报告（依赖 Module 3 + 4）
Module 6 (test_gen) ───→ 测试用例 + 重构方案
Module 7 (explorer) ───→ 交互响应（依赖 Module 2-5）
Module 8 (req_tracer) ─→ RTM 矩阵 + 偏离报告
```

---

## 注意事项

1. **安全性**：本技能仅读取和分析代码，不会修改任何源文件
2. **隐私性**：所有分析在本地执行，代码不会上传到外部服务
3. **性能**：大型项目（>10万行）的分析可能需要较长时间，建议分模块执行
4. **语言限制**：非 Python/Java/JavaScript/C++ 的语言仅提供基础分析
5. **准确性**：设计意图推断基于启发式规则，建议结合人工确认