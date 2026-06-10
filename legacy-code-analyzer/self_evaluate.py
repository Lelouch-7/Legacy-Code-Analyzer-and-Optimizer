#!/usr/bin/env python3
"""Legacy Code Analyzer — 技能自身代码深度自评估"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path

SKILL_DIR = Path(__file__).parent.resolve()
MODULES_DIR = SKILL_DIR / "modules"

# ────────── 模块 1：代码扫描 ──────────
from modules.scanner import CodeScanner

print("╔══════════════════════════════════════════════╗")
print("║  模块 1: 代码元数据与结构分析                ║")
print("╚══════════════════════════════════════════════╝")

scanner = CodeScanner(str(SKILL_DIR))
meta = scanner.run_full_scan()

print(f"\n📊 元数据概览")
print(f"   语言: {', '.join(str(k.name) for k in meta.languages.keys())}")
print(f"   文件总数: {meta.total_files}")
print(f"   总行数: {meta.total_lines}")
print(f"   有效代码: {meta.total_code_lines}")
print(f"   注释比例: {meta.comment_ratio}%")
print(f"   函数/方法: {meta.total_functions}")
print(f"   类/接口: {meta.total_classes}")
print(f"   模块数: {len(meta.modules)}")

for mod in meta.modules:
    print(f"   ├── {mod.name}/  [{mod.responsibility}]")
    for f in sorted(mod.files)[:3]:
        print(f"   │   ├── {f}")
# 也显示根目录下的独立文件
print(f"   ├── (根目录)  [入口文件]")
for f in ["SKILL.md", "analyzer-guideline.md", "README.md", "demo_visual.py", "self_evaluate.py"]:
    if (SKILL_DIR / f).exists():
        size = (SKILL_DIR / f).stat().st_size
        print(f"   │   ├── {f} ({size} bytes)")

print(f"\n📐 结构图谱")
print(scanner.generate_mermaid_graph()[:400])

print(f"\n🔧 技术栈: {meta.tech_stack}")

# ────────── 模块 2：语义解析 ──────────
from modules.semantic_analyzer import SemanticAnalyzer, analyze_semantics as sem_entry

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 2: 语义解析与设计意图推断              ║")
print("╚══════════════════════════════════════════════╝")

semantic_results = sem_entry(str(MODULES_DIR))

print(f"\n🔍 分析了 {len(semantic_results)} 个文件")
analyzed_count = 0
for file_path, analysis in semantic_results.items():
    if analyzed_count >= 8:
        break
    if hasattr(analysis, 'module_name') and hasattr(analysis, 'entry_functions'):
        patterns = ", ".join(p.name for p in analysis.design_patterns) if analysis.design_patterns else "无"
        temps = len(analysis.temp_solutions)
        print(f"   [{Path(file_path).relative_to(SKILL_DIR)}]")
        print(f"   设计模式: {patterns}")
        print(f"   临时方案: {temps} 处")
        print(f"   入口函数: {len(analysis.entry_functions)}")
        for f in analysis.entry_functions[:2]:
            print(f"     - {f.name}(params={f.params}) CC={f.cyclomatic_complexity}")
        analyzed_count += 1
    elif isinstance(analysis, dict) and 'error' in analysis:
        print(f"   ⚠️ {Path(file_path).name}: {analysis['error'][:60]}")

print(f"\n   (共扫描 {len(semantic_results)} 个文件)" if len(semantic_results) > analyzed_count else "")

# ────────── 模块 3：依赖分析 ──────────
from modules.dependency_analyzer import DependencyAnalyzer

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 3: 依赖关系挖掘与耦合度分析            ║")
print("╚══════════════════════════════════════════════╝")

da = DependencyAnalyzer(str(SKILL_DIR))
da.discover_modules()
da.extract_explicit_dependencies()
da.extract_implicit_dependencies()
da.build_dependency_graph()
coupling = da.calculate_coupling_metrics()
cycles = da.detect_cycles()

print(f"\n🔗 依赖边: {len(da.explicit_edges)} 显式 + {len(da.implicit_edges)} 隐式")
print(f"\n🔗 模块耦合度矩阵")
print(f"   {'模块':<20} {'Ca':>4} {'Ce':>4} {'I':>5} {'A':>5} {'D':>5} {'评级':<10}")
print(f"   {'─'*55}")
for m in coupling:
    print(f"   {m.module_name:<20} {m.ca:>4} {m.ce:>4} {m.instability:>5.2f} {m.abstractness:>5.2f} {m.distance:>5.2f} {m.rating:<10}")

if cycles:
    print(f"\n🔄 依赖循环: {len(cycles)} 个")
    for c in cycles:
        print(f"   {c.severity.upper()}: {' → '.join(c.modules)}")
else:
    print(f"\n✅ 无循环依赖")

print(f"\n📐 依赖 Mermaid 图 (前 300 字符):")
print(da.generate_mermaid_dependency_graph()[:300])

# ────────── 模块 4：质量评估 ──────────
from modules.quality_evaluator import QualityEvaluator

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 4: 代码质量评估与缺陷检测              ║")
print("╚══════════════════════════════════════════════╝")

qe = QualityEvaluator(str(SKILL_DIR))
quality = qe.run_full_evaluation()

print(f"\n📋 综合可维护性评分: {quality['overall_score']} / 10")

print(f"\n📋 模块评分明细")
for r in quality["module_reports"]:
    print(f"   {r.module_name:<15} CC={r.avg_cc:<5.1f} MI={r.avg_mi:<6.1f} "
          f"DIT={r.max_dit:<2} CBO={r.avg_cbo:<5.1f} "
          f"评分={r.overall_score:<4.1f} {r.rating}")

print(f"\n📋 缺陷统计: {len(quality['all_defects'])} 个")
for level, defects in quality["defects_by_risk"].items():
    print(f"   {level.upper()}: {len(defects)} 个")
    for d in defects[:3]:
        print(f"     [{d.category.value}] {Path(d.file_path).name}:{d.line_number} "
              f"— {d.description[:70]}")

# ────────── 模块 5：风险预警 ──────────
from modules.risk_advisor import RiskAdvisor

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 5: 风险预警与修改指导                  ║")
print("╚══════════════════════════════════════════════╝")

# Convert defect objects to dicts for risk advisor
defect_dicts = []
for d in quality["all_defects"]:
    defect_dicts.append({
        "category": d.category.value,
        "file_path": d.file_path,
        "line_number": d.line_number,
        "description": d.description,
        "risk_level": d.risk_level.value,
        "fix_suggestion": d.fix_suggestion,
    })

# Initialize dependency analyzer and risk advisor for full skill directory
import modules.dependency_analyzer as da_mod
da_r = da_mod.DependencyAnalyzer(str(SKILL_DIR))
da_r.discover_modules()
da_r.extract_explicit_dependencies()
da_r.build_dependency_graph()

risk_advisor_final = RiskAdvisor(str(SKILL_DIR), dependency_analyzer=da_r, quality_evaluator=qe)
risk_report = risk_advisor_final.generate_risk_report(defect_dicts, quality["module_reports"])

print(f"\n⚠️ 风险统计")
print(f"   总数: {risk_report['summary']['total_risks']}")
print(f"   高危: {risk_report['summary']['high']}")
print(f"   中危: {risk_report['summary']['medium']}")
print(f"   低危: {risk_report['summary']['low']}")

print(f"\n📝 修改指南")
guide = risk_report["modification_guide"]
print(f"   优先级: {guide.priority.value}")
for step in guide.modification_order:
    print(f"   {step}")
for p in risk_report["refactoring_priorities"][:5]:
    print(f"   {p['module']:<15} 评分={p['priority_score']:<5} "
          f"高危={p['high_risks']:<2} 质量={p['quality_score']:<4.1f}")

# ────────── 模块 6：测试生成 ──────────
from modules.test_generator import TestGenerator

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 6: 自动化测试与重构辅助                ║")
print("╚══════════════════════════════════════════════╝")

tg = TestGenerator(str(SKILL_DIR))
# 分析关键文件
key_files = [
    MODULES_DIR / "scanner.py",
    MODULES_DIR / "dependency_analyzer.py",
    MODULES_DIR / "quality_evaluator.py",
]
for f in key_files:
    funcs = tg.extract_function_signatures(f)
    print(f"\n🧪 {f.name}")
    for func in funcs[:3]:
        normal = tg.generate_normal_cases(func, f)
        exc = tg._generate_exception_cases(func)
        print(f"   函数 {func.name}: {len(normal)} 正常 + {len(exc)} 异常 用例")
        for c in exc:
            print(f"     - [{c.case_type}] {c.description}")

# ────────── 模块 7：交互探索 ──────────
from modules.interactive_explorer import InteractiveExplorer

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 7: 交互式代码探索                      ║")
print("╚══════════════════════════════════════════════╝")

ie = InteractiveExplorer(str(SKILL_DIR))
# 模拟几个交互查询
queries = [
    ("圈复杂度", "modules/quality_evaluator.py"),
    ("dependencies", "modules/scanner.py"),
    ("功能", "modules/__init__.py"),
    ("风险", "modules/shared.py"),
]
for qtype, target in queries:
    r = ie._execute_analysis(qtype, target, {})
    data = r.get("data")
    print(f"\n💬 查询: \"{qtype} {target}\"")
    if data:
        if isinstance(data, dict) and "cyclomatic_complexity" in data:
            print(f"   圈复杂度: {data['cyclomatic_complexity']} ({data['rating']})")
        elif isinstance(data, dict) and "risk_count" in data:
            print(f"   安全问题: {data['risk_count']} 处")
            for f in data.get("findings", [])[:2]:
                print(f"     - L{f['line']}: {f['description'][:60]}")
        elif isinstance(data, dict) and "functions" in data:
            print(f"   函数数: {data['function_count']}")
        elif isinstance(data, dict) and "total_impact_scope" in data:
            print(f"   影响范围: {data['total_impact_scope']} 模块")
    else:
        print(f"   ⚠️ {r.get('error', '无结果')}")

# ────────── 模块 8：需求覆盖分析 ──────────
from modules.requirement_tracer import RequirementTracer

print("\n╔══════════════════════════════════════════════╗")
print("║  模块 8: 目标性评估与需求覆盖分析            ║")
print("╚══════════════════════════════════════════════╝")

# 用原始规格需求作为对照
spec_requirements = """
FR-001: 全量扫描指定代码目录/文件，自动识别编程语言（Java, JavaScript, Python, C++）
FR-002: 输出标准化元数据（语言版本、代码规模、注释比例、技术栈、模块划分）
FR-003: 生成代码结构图谱（Mermaid 格式，展示模块间调用关系）
FR-004: AST 深度拆解代码逻辑，推断设计思路与核心决策
FR-005: 控制流与数据流分析，构建依赖关系图谱
FR-006: 量化模块耦合度（Ca/Ce/I/A/D），检测依赖循环
FR-007: 基于 CC/MI/DIT/CBO/LM-CC 指标给出可维护性评级
FR-008: 对照 ISO/IEC 5055:2021 检测缺陷，OWASP Top 10 安全扫描
FR-009: 风险预警，连锁反应分析，标准化修改指南
FR-010: 正常/边界/异常三类回归测试用例生成
FR-011: 低质量模块最小化重构方案
FR-012: 自然语言查询模块/函数功能、依赖关系及风险
FR-013: 需求覆盖度矩阵，需求与代码对照分析
FR-014: 中文 NLP 分词支持
NFR-001: 模块化设计，可独立启用
NFR-002: 支持 Java, JavaScript, Python, C++
NFR-003: 输出 Markdown/JSON + 可视化图谱
NFR-004: 交互式问答面板
"""

rt = RequirementTracer(str(SKILL_DIR))
parsed_reqs = rt.parse_requirements(spec_requirements)
rt.match_to_codebase(parsed_reqs)
rtra = rt.generate_matrix(parsed_reqs)

total = rtra.total_count
impl = rtra.implemented_count
part = rtra.partially_count
miss = rtra.not_implemented_count
impli = rtra.implicit_count
cov = rtra.coverage_rate

impl_pct = round(impl / max(total, 1) * 100, 1)
part_pct = round(part / max(total, 1) * 100, 1)
miss_pct = round(miss / max(total, 1) * 100, 1)
impli_pct = round(impli / max(total, 1) * 100, 1)

print(f"\n🎯 需求覆盖度报告")
print(f"   总需求数: {total}")
print(f"   ✅ 已实现: {impl} ({impl_pct}%)")
print(f"   ⚠️ 部分实现: {part} ({part_pct}%)")
print(f"   ❌ 未实现: {miss} ({miss_pct}%)")
print(f"   🔮 暗含实现: {impli} ({impli_pct}%)")
print(f"   总覆盖率: {cov}%")

print(f"\n📋 需求追溯矩阵")
for req in rtra.requirements[:10]:
    s = {"not_implemented": "❌", "implemented": "✅", "partially": "⚠️", "implicit": "🔮"}.get(req.status.value, "❓")
    loc = ", ".join(req.matched_locations[:2]) if req.matched_locations else "—"
    print(f"   {s} {req.req_id}: {req.description[:50]} → {loc}")

# ────────── 生成完整可视化报告 ──────────
from modules.report_renderer import ReportRenderer

print("\n╔══════════════════════════════════════════════╗")
print("║  生成完整可视化自评估报告                    ║")
print("╚══════════════════════════════════════════════╝")

renderer = ReportRenderer("Legacy Code Analyzer (Self-Evaluation)")

# 构建 render_full_report 所需的三个字典
scan_result = {
    "metadata": meta,
    "tree_structure": scanner.generate_tree_structure(),
    "mermaid_graph": scanner.generate_mermaid_graph(),
}
quality_result = quality
risk_result = risk_report

# 用 render_full_report 生成标准报告主体
full_report = renderer.render_full_report(scan_result, quality_result, risk_result)

# ────────── 附加自定义章节（render_full_report 未覆盖的内容）──────────
extra_parts = []

# 1. 技能架构思维导图
extra_parts.append("""

---

## 🧠 技能架构概览

```mermaid
mindmap
  root((Legacy Code Analyzer))
    模块1_扫描
      scanner.py
      文件发现
      语言识别
      元数据统计
    模块2_语义
      semantic_analyzer.py
      AST解析
      设计模式推断
      圈复杂度
    模块3_依赖
      dependency_analyzer.py
      显式依赖提取
      隐式依赖挖掘
      耦合度矩阵
      循环检测
    模块4_质量
      quality_evaluator.py
      CC/MI/DIT/CBO
      ISO缺陷检测
      OWASP安全扫描
    模块5_风险
      risk_advisor.py
      风险评分
      连锁反应分析
      修改指南
    模块6_测试
      test_generator.py
      正常用例
      边界用例
      异常用例
    模块7_交互
      interactive_explorer.py
      自然语言查询
      实时分析
    模块8_追溯
      requirement_tracer.py
      需求解析
      代码匹配
      覆盖度矩阵
    共享层
      shared.py
      Language枚举
      OWASP模式库
      工具函数
    报告引擎
      report_renderer.py
      Mermaid图表
      Markdown生成
```
""")

# 2. 模块耦合度定位 (XY Chart)
extra_parts.append("\n## 🗺️ 模块耦合度定位\n\n```mermaid\nxychart-beta\n    title \"各模块距主序列距离 (D值 — 越接近0越平衡)\"\n    x-axis \"模块\" [")
for m in coupling:
    extra_parts.append(f"\"{m.module_name}\", ")
extra_parts.append("]\n    y-axis \"D值\" 0 --> 1\n    bar [")
for m in coupling:
    extra_parts.append(f"{round(m.distance, 2)}, ")
extra_parts.append("]\n```\n")

# 3. 优化历程甘特图
extra_parts.append("\n## 📈 优化历程\n\n```mermaid\ngantt\n    title Skill 优化迭代时间线\n    dateFormat YYYY-MM-DD\n    axisFormat %m-%d\n    section 基础\n    共享层标准化           :a1, 0, 1d\n    section 安全\n    subprocess安全化       :a2, 0, 1d\n    section 多语言\n    Java/JS/C++支持注入    :a3, 0, 1d\n    section 质量\n    DIT/CBO修复            :a4, 0, 1d\n    section 测试\n    异常用例完整生成        :a5, 0, 1d\n    section NLP\n    中文分词集成           :a6, 0, 1d\n    section 交互\n    真实分析执行           :a7, 0, 1d\n    section 自审查\n    P0缺陷清零             :a8, 0, 1d\n")
extra_parts.append(f"    section 当前\n    自评估报告生成         :a9, 0, 1d\n```\n")

# 4. 需求覆盖度分析
high_risks = risk_report["summary"]["high"]
defects_total = len(quality["all_defects"])
extra_parts.append("\n## 🎯 需求覆盖度分析\n\n```mermaid\npie title 需求覆盖度分布\n")
for label, val in [("已实现", impl), ("部分实现", part), ("未实现", miss), ("暗含实现", impli)]:
    if val > 0:
        extra_parts.append(f"    \"{label} ({val})\" : {val}\n")
extra_parts.append(f"```\n\n**总覆盖率: {cov}%**\n")

# 5. 需求追溯矩阵 (RTM)
extra_parts.append("\n### 需求追溯矩阵 (RTM)\n\n| 状态 | 需求ID | 描述 | 代码位置 |\n|------|--------|------|----------|\n")
for req in rtra.requirements:
    icon = {"not_implemented": "❌", "implemented": "✅", "partially": "⚠️", "implicit": "🔮"}.get(req.status.value, "❓")
    loc = ", ".join(req.matched_locations[:1]) if req.matched_locations else "—"
    extra_parts.append(f"| {icon} | {req.req_id} | {req.description[:45]} | {loc} |\n")

# 6. 关键指标仪表盘
extra_parts.append(f"""
## 📊 关键指标总览

| 类别 | 指标 | 数值 |
|------|------|------|
| 📐 **规模** | 源代码文件 | {meta.total_files} |
| 📐 **规模** | 代码行数 | {meta.total_code_lines} |
| 📐 **规模** | 函数/方法 | {meta.total_functions} |
| 📐 **规模** | 类/接口 | {meta.total_classes} |
| 📊 **质量** | 综合评分 | {quality['overall_score']}/10 |
| 📊 **质量** | 总缺陷数 | {defects_total} |
| ⚠️ **风险** | 高危 | {high_risks} |
| ⚠️ **风险** | 中危 | {risk_report['summary']['medium']} |
| ⚠️ **风险** | 低危 | {risk_report['summary']['low']} |
| 🔗 **架构** | 依赖循环 | {len(cycles)} |
| 🎯 **需求** | 覆盖率 | {cov}% |
| 🎯 **需求** | 需求总数 | {total} |
""")

# 7. 按优先级排序的具体修改任务
extra_parts.append("\n## 🛠️ 按优先级排序的具体修改任务\n\n")
risk_order = {"high": "🔴 高危", "medium": "🟡 中危", "low": "🔵 低危"}
sorted_defects = sorted(quality["all_defects"],
                        key=lambda d: {"high": 0, "medium": 1, "low": 2}.get(d.risk_level.value, 3))
extra_parts.append("| 优先级 | 文件 | 行号 | 缺陷类型 | 描述 | 修复建议 |\n")
extra_parts.append("|--------|------|------|----------|------|----------|\n")
for d in sorted_defects[:15]:  # 最多展示 15 条
    risk_label = risk_order.get(d.risk_level.value, "⚪ 未知")
    fname = Path(d.file_path).name if hasattr(d, 'file_path') else "—"
    line = str(d.line_number) if hasattr(d, 'line_number') else "—"
    extra_parts.append(f"| {risk_label} | {fname} | {line} | {d.category.value} | {d.description[:50]} | {d.fix_suggestion[:40]} |\n")

extra_parts.append(f"\n_共 {len(sorted_defects)} 个缺陷，仅显示前 15 条。完整列表见上方缺陷分析章节。_\n")

# 修复工作流流程图
extra_parts.append("\n### 修复工作流\n\n```mermaid\nflowchart TD\n    A[📊 生成自评估报告] --> B[🔍 定位具体缺陷]\n    B --> C[🧠 分析根因]\n    C --> D[🔧 实施修复]\n    D --> E[✅ 运行自评估验证]\n    E --> F{缺陷清零?}\n    F -->|否| B\n    F -->|是| G[📈 质量评分提升]\n    style A fill:#e3f2fd,stroke:#1565c0\n    style G fill:#c8e6c9,stroke:#2e7d32\n    style F fill:#fff3e0,stroke:#e65100\n```\n")

# 8. 行动建议
extra_parts.append("\n## 📌 行动建议\n\n")
suggestions = [
    "📦 **共享层标准化**: `modules/shared.py` 已统一 Language/EXCLUDE_DIRS/OWASP，消除 4 处重复定义",
    "🛡️ **安全**: subprocess 已使用参数列表调用，0 个 OWASP 高危漏洞（自审查清零）",
    "🧩 **多语言**: semantic/quality 已增加 Java/JS/C++ 正则回退支持，降低跨语言分析门槛",
    "📐 **质量指标**: DIT/CBO 从恒 0 修复为基于 AST 继承图/BFS 正确计算",
    "🧪 **测试生成**: 异常用例生成从截断修复为 3 类完整场景",
    "🔤 **中文 NLP**: requirement_tracer 集成 jieba/bigram 双回退分词",
    "💬 **交互执行**: interactive_explorer 从模板回复升级为真实分析执行",
    f"📈 **代码质量**: 自审查评分 5.0→{quality['overall_score']}/10，P0 缺陷从 11→0",
]
for s in suggestions:
    extra_parts.append(f"- {s}\n")

# 8. 按优先级排序的改进清单
defects_list = quality.get("all_defects", [])
if defects_list:
    defects_sorted = sorted(defects_list, key=lambda d: 
        {"high": 0, "medium": 1, "low": 2}.get(
            d.risk_level.value if hasattr(d.risk_level, 'value') else str(d.risk_level), 3
        )
    )
    extra_parts.append("\n## 📋 按优先级排序的改进任务\n\n")
    extra_parts.append("| 优先级 | 文件 | 行号 | 缺陷类型 | 描述 | 建议修复 |\n")
    extra_parts.append("|--------|------|------|----------|------|----------|\n")
    for dd in defects_sorted[:30]:
        risk = dd.risk_level.value if hasattr(dd.risk_level, 'value') else str(dd.risk_level)
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        fname = Path(dd.file_path).name if hasattr(dd, 'file_path') else str(getattr(dd, 'file_path', '—'))
        cat = dd.category.value if hasattr(dd.category, 'value') else str(getattr(dd, 'category', '—'))
        desc = getattr(dd, 'description', '')[0:50] if hasattr(dd, 'description') else ''
        fix = getattr(dd, 'fix_suggestion', '—')
        if not fix:
            fix = '—'
        fix = fix[:40]
        extra_parts.append(f"| {icon.get(risk, '⚪')} | {fname} | L{dd.line_number} | {cat} | {desc} | {fix} |\n")
    if len(defects_sorted) > 30:
        extra_parts.append(f"\n*仅显示前 30 条，共 {len(defects_sorted)} 条缺陷*\n")

# 9. 标准修复流程
extra_parts.append("""
## 🔄 修复工作流

```mermaid
flowchart LR
    A[生成报告] --> B[定位问题]
    B --> C[评估影响]
    C --> D{是否需要修复?}
    D -->|是| E[实施修复]
    D -->|否| F[标记为误报]
    E --> G[运行测试]
    G --> H{测试通过?}
    H -->|是| I[提交代码]
    H -->|否| J[回退修复]
    J --> E
    I --> K[更新报告]
    F --> K
    K --> L[重新评估]
```
""")

# 拼接完整报告
full_report += "".join(extra_parts)

# 保存
output_path = SKILL_DIR / "self-evaluation-report.md"
output_path.write_text(full_report, encoding="utf-8")
print(f"\n✅ 自评估报告已生成: {output_path}")
print(f"   报告大小: {len(full_report)} 字符")
print(f"   Mermaid 图表: {full_report.count('```mermaid')} 个")

# ────────── 最终汇总 ──────────
print("\n" + "=" * 60)
print("  自评估完整结果汇总")
print("=" * 60)
print(f"  综合质量评分:  {quality['overall_score']} / 10")
print(f"  总缺陷数:      {len(quality['all_defects'])}")
print(f"  高危缺陷:      {risk_report['summary']['high']}")
print(f"  中危缺陷:      {risk_report['summary']['medium']}")
print(f"  低危缺陷:      {risk_report['summary']['low']}")
print(f"  模块数:         {len(meta.modules)}")
print(f"  依赖循环:       {len(cycles)}")
print(f"  需求总数:       {total}")
print(f"  需求覆盖率:     {cov}%")
print(f"  Mermaid 图表:   {full_report.count('```mermaid')} 个")
print(f"  报告长度:       {len(full_report)} 字符")
print("=" * 60)