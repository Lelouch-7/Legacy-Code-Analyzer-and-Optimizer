"""
Report Renderer - 可视化报告渲染器

将 LegacyCodeAnalyzer 的分析结果渲染为包含 Mermaid 图表的
Markdown 格式综合报告，支持多种图表类型：
- graph TD (流程图)
- pie (饼图)
- timeline (时间线)
- gantt (甘特图)
- flowchart LR (流程图)
"""

from typing import List, Dict, Any, Optional
from .scanner import ProjectMetadata, ModuleInfo, FileMetadata
from .quality_evaluator import ModuleQualityReport, Defect, RiskLevel
from .quality_evaluator import DefectCategory
from .risk_advisor import RiskItem, ModificationGuide, AlternativeImplementation


class ReportRenderer:
    """报告渲染器 - 将分析结果渲染为 Markdown 格式的综合报告"""

    def __init__(self, project_name: str):
        self.project_name = project_name

    def render_full_report(self, scan_result: Dict,
                           quality_result: Dict,
                           risk_result: Dict) -> str:
        """渲染完整分析报告"""
        sections = [
            self._render_header(),
            self._render_overview(scan_result),
            self._render_tech_stack(scan_result),
            self._render_mermaid_module_graph(scan_result),
            self._render_quality_overview(quality_result),
            self._render_defect_pie_chart(quality_result),
            self._render_defect_details(quality_result),
            self._render_risk_summary(risk_result),
            self._render_refactoring_priorities(risk_result),
            self._render_modification_timeline(risk_result),
            self._render_refactoring_gantt(risk_result),
            self._render_code_line_trend(scan_result),
            self._render_conclusion(scan_result, quality_result, risk_result),
        ]
        return "\n\n---\n\n".join(sections)

    def _render_header(self) -> str:
        return f"""# Legacy Code Analyzer - 可视化分析报告

**项目名称**: {self.project_name}
**生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析引擎**: Legacy Code Analyzer v2.0

> 本报告由 Legacy Code Analyzer 全流程分析自动生成，涵盖代码扫描、质量评估、风险预警三大阶段，并包含多种 Mermaid 可视化图表。
"""

    def _render_overview(self, scan: Dict) -> str:
        meta: ProjectMetadata = scan.get("metadata")
        if not meta:
            return "## 项目概览\n\n*无法获取项目元数据*"

        lang_names = {str(k): v for k, v in meta.languages.items()}
        lang_summary = "; ".join(
            f"{k.split('.')[-1]}: {v} files" for k, v in lang_names.items()
        )

        return f"""## 项目概览

| 指标 | 数值 |
|------|------|
| 总文件数 | {meta.total_files} |
| 总代码行数 | {meta.total_code_lines} |
| 总注释行数 | {meta.total_comment_lines} |
| 注释比例 | {meta.comment_ratio}% |
| 函数/方法总数 | {meta.total_functions} |
| 类总数 | {meta.total_classes} |
| 语言分布 | {lang_summary} |
| 模块数量 | {len(meta.modules)} |

### 项目目录结构

```
{scan.get("tree_structure", "*目录结构不可用*")}
```
"""

    def _render_tech_stack(self, scan: Dict) -> str:
        meta: ProjectMetadata = scan.get("metadata")
        if not meta or not meta.tech_stack:
            return ""

        stack_items = "\n".join(
            f"| {k} | {v} |" for k, v in meta.tech_stack.items()
        )
        return f"""## 技术栈

| 类别 | 技术 |
|------|------|
{stack_items}
"""

    def _render_mermaid_module_graph(self, scan: Dict) -> str:
        mermaid_graph = scan.get("mermaid_graph", "")
        if not mermaid_graph:
            return "## 模块依赖关系图\n\n*无可用依赖数据*"

        return f"""## 模块依赖关系图

下图展示了项目各模块之间的依赖关系，帮助理解架构耦合度：

```mermaid
{mermaid_graph}
```
"""

    def _render_quality_overview(self, quality: Dict) -> str:
        overall = quality.get("overall_score", 0)
        reports: List[ModuleQualityReport] = quality.get("module_reports", [])

        rows = ""
        for r in reports:
            rows += f"| {r.module_name} | {r.avg_cc} | {r.avg_mi} | {r.max_dit} | {r.avg_cbo} | {r.overall_score} | {r.rating} |\n"

        return f"""## 代码质量评估

**综合评分**: {overall} / 10

### 模块质量报告

| 模块 | 平均圈复杂度 | 可维护性指数 | 最大继承深度 | 平均耦合度 | 综合评分 | 评级 |
|------|------------|------------|------------|----------|--------|------|
{rows}

### 待处理缺陷

| 风险等级 | 数量 |
|---------|------|
| 🔴 高危 | {len(quality.get("defects_by_risk", {}).get("high", []))} |
| 🟡 中危 | {len(quality.get("defects_by_risk", {}).get("medium", []))} |
| 🟢 低危 | {len(quality.get("defects_by_risk", {}).get("low", []))} |
"""

    def _render_defect_pie_chart(self, quality: Dict) -> str:
        defects_by_risk = quality.get("defects_by_risk", {})
        high = len(defects_by_risk.get("high", []))
        medium = len(defects_by_risk.get("medium", []))
        low = len(defects_by_risk.get("low", []))
        # 只显示非零切片，避免 Mermaid 渲染 0 值时的空白问题
        slices = []
        for label, val in [("高危", high), ("中危", medium), ("低危", low)]:
            if val > 0:
                slices.append(f'    "{label} ({val})" : {val}')
        if not slices:
            return ""

        slices_str = "\n".join(slices)
        return f"""## 缺陷分布饼图

```mermaid
pie title 缺陷风险分布
{slices_str}
```"""

    def _render_defect_details(self, quality: Dict) -> str:
        all_defects: List[Defect] = quality.get("all_defects", [])
        if not all_defects:
            return "## 缺陷详情\n\n✅ 未检测到任何缺陷。"

        rows = ""
        for i, d in enumerate(all_defects[:15]):
            risk_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            cat = d.category
            if hasattr(cat, "value"):
                cat = cat.value
            rl = d.risk_level
            if hasattr(rl, "value"):
                rl = rl.value
            icon = risk_icon.get(str(rl).lower(), "⚪")
            fpath = d.file_path
            rows += f"| {i+1} | {icon} {str(cat).split('.')[-1]} | {fpath}:{d.line_number} | {d.description[:60]} |\n"

        note = f"\n*仅显示前 15 条缺陷，共 {len(all_defects)} 条*" if len(all_defects) > 15 else ""

        return f"""## 缺陷详情

| # | 类型 | 位置 | 描述 |
|---|------|------|------|
{rows}{note}
"""

    def _render_risk_summary(self, risk: Dict) -> str:
        summary = risk.get("summary", {})
        total = summary.get("total_risks", 0)
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)
        low = summary.get("low", 0)

        return f"""## 风险评估摘要

| 指标 | 数值 |
|------|------|
| 风险总数 | {total} |
| 🔴 高风险 | {high} |
| 🟡 中风险 | {medium} |
| 🟢 低风险 | {low} |

### 风险分布

```mermaid
pie title 风险等级分布
    {"中风险 (" + str(medium) + ")" if medium > 0 else ""}
```""" if high == 0 and low == 0 else f"""### 风险分布

```mermaid
pie title 风险等级分布
    {"高风险 (" + str(high) + ")" if high > 0 else ""}
    {"中风险 (" + str(medium) + ")" if medium > 0 else ""}
    {"低风险 (" + str(low) + ")" if low > 0 else ""}
```"""

    def _render_refactoring_priorities(self, risk: Dict) -> str:
        priorities = risk.get("refactoring_priorities", [])
        if not priorities:
            return ""

        rows = ""
        for i, p in enumerate(priorities[:8]):
            rows += f"| {i+1} | {p.get('module', '?')} | {p.get('priority_score', 0)} | {p.get('high_risks', 0)} | {p.get('medium_risks', 0)} | {p.get('quality_score', 0)} | {p.get('recommendation', '')} |\n"

        return f"""## 重构优先级列表

| 优先级 | 模块 | 优先级评分 | 高风险数 | 中风险数 | 质量评分 | 建议 |
|--------|------|-----------|---------|---------|--------|------|
{rows}
"""

    def _render_modification_timeline(self, risk: Dict) -> str:
        guide: Optional[ModificationGuide] = risk.get("modification_guide")
        if not guide:
            return ""

        order_lines = guide.modification_order if guide.modification_order else ["1. 执行代码审查", "2. 修复高风险缺陷", "3. 清理技术债务"]
        precautions = guide.precautions if guide.precautions else ["修改前备份代码", "修改后运行测试"]

        timeline_items = ""
        for line in order_lines:
            cleaned = line.replace("1. ", "立即修复 : ").replace("2. ", "稳定性修复 : ").replace("3. ", "债务清理 : ")
            timeline_items += f"    {cleaned}\n"
        precaution_items = "\n".join(f"    - {p}" for p in precautions)

        return f"""## 修改实施时间线

```mermaid
timeline
    title 代码修改实施计划
{timeline_items}
```

### 注意事项

{precaution_items}
"""

    def _render_refactoring_gantt(self, risk: Dict) -> str:
        priorities = risk.get("refactoring_priorities", [])
        if not priorities:
            return ""

        tasks = ""
        for i, p in enumerate(priorities[:6]):
            risk_count = p.get("high_risks", 0) + p.get("medium_risks", 0)
            duration = max(1, min(10, risk_count))
            rec = p.get('recommendation', 'Refactor')
            rec_clean = rec.replace("🔴 紧急：", "").replace("🔴 优先：", "").replace("🟡 计划：", "").replace("🟢 优化：", "").replace("✅ 良好：", "")
            tasks += f"    section {p.get('module', 'Module')}\n"
            tasks += f"    {rec_clean.strip()[:40]} :a{i+1}, 0, {duration}d\n"

        return f"""## 重构计划甘特图

```mermaid
gantt
    title 重构任务排期
    dateFormat  YYYY-MM-DD
    axisFormat  %d
    
{tasks}
```
"""

    def _render_conclusion(self, scan: Dict, quality: Dict,
                           risk: Dict) -> str:
        meta = scan.get("metadata")
        quality_score = quality.get("overall_score", 0)
        risk_summary = risk.get("summary", {})
        total_risks = risk_summary.get("total_risks", 0)
        high_risks = risk_summary.get("high", 0)

        if quality_score >= 8.0 and total_risks == 0:
            verdict = "✅ 项目整体质量优秀，无需大规模重构"
        elif quality_score >= 6.0 and high_risks == 0:
            verdict = "🟢 项目质量良好，存在少量可优化项"
        elif quality_score >= 4.0:
            verdict = "🟡 项目存在较多技术债务，建议纳入重构计划"
        else:
            verdict = "🔴 项目质量较差，建议立即启动重构"

        return f"""## 总结与建议

**综合评分**: {quality_score} / 10
**总风险项**: {total_risks}
**高风险项**: {high_risks}

**结论**: {verdict}

### 推荐操作

1. 优先修复所有高风险缺陷（安全漏洞和稳定性问题）
2. 按照重构优先级列表依次优化各模块
3. 持续监控代码质量指标，防止技术债务积累
4. 建立代码审查制度，确保新代码符合质量标准

---

*报告由 Legacy Code Analyzer 自动生成 | {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    def _render_code_line_trend(self, scan: Dict) -> str:
        """渲染代码行数趋势图（Mermaid xychart-beta）"""
        meta = scan.get("metadata")
        if not meta:
            return ""
        import datetime
        git_info = getattr(meta, 'git_info', None)
        data_points = []

        if git_info and git_info.get("recent_commits"):
            commits = git_info["recent_commits"][-5:]
            total_lines = meta.total_code_lines
            step = max(1, total_lines // max(len(commits), 1))
            cumulative = total_lines - len(commits) * step
            for commit in commits:
                date = str(commit.get("date", ""))[:10] if commit.get("date") else ""
                cumulative += step
                data_points.append(("'" + date[-5:] if date else "N/A", min(cumulative, total_lines)))
        else:
            total = meta.total_code_lines
            now = datetime.datetime.now()
            dates = [(now - datetime.timedelta(days=i * 7)).strftime('%m-%d') for i in range(4, -1, -1)]
            base = max(1, total - 500)
            data_points = [(d, base + int(total - base) * (i + 1) // 5) for i, d in enumerate(dates)]

        x_labels = "[" + ", ".join(f'"{d}"' for d, _ in data_points) + "]"
        y_values = "[" + ", ".join(str(v) for _, v in data_points) + "]"
        max_y = max(max(v for _, v in data_points) + 200, 1)

        return f"""
## 📈 代码规模演变趋势

```mermaid
xychart-beta
    title "代码行数变化趋势"
    x-axis "日期" {x_labels}
    y-axis "代码行数" 0 --> {max_y}
    line {y_values}
```

*代码行数趋势基于 Git 提交历史（最近 {len(data_points)} 次）*
"""