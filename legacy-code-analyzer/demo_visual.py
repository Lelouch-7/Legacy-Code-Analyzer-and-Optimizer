#!/usr/bin/env python3
"""Legacy Code Analyzer - 可视化能力全流程演示"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import LegacyCodeAnalyzer, ReportRenderer


def main():
    # 1. 初始化分析器
    print("=== 初始化分析器 ===")
    analyzer = LegacyCodeAnalyzer("/workspace/demo-project")
    print(f"   项目根目录: {analyzer.project_root}")

    # 2. 执行完整分析
    print("=== 执行代码扫描 ===")
    scan = analyzer.scan()
    meta = scan.get("metadata")
    print(f"   发现 {meta.total_files} 个源文件, {meta.total_code_lines} 行代码, "
          f"{meta.total_functions} 个函数, {meta.total_classes} 个类")
    print(f"   注释比例: {meta.comment_ratio}%")

    print("=== 执行质量评估 ===")
    quality = analyzer.evaluate_quality()
    print(f"   综合评分: {quality['overall_score']} / 10")
    print(f"   缺陷总数: {len(quality['all_defects'])}")
    defects_by_risk = quality.get("defects_by_risk", {})
    print(f"   高危: {len(defects_by_risk.get('high', []))}, "
          f"中危: {len(defects_by_risk.get('medium', []))}, "
          f"低危: {len(defects_by_risk.get('low', []))}")

    print("=== 生成风险报告 ===")
    risk = analyzer.advise_risks()
    summary = risk.get("summary", {})
    print(f"   风险总数: {summary.get('total_risks', 0)}")
    print(f"   高风险: {summary.get('high', 0)}, "
          f"中风险: {summary.get('medium', 0)}, "
          f"低风险: {summary.get('low', 0)}")
    priorities = risk.get("refactoring_priorities", [])
    print(f"   重构优先级条目: {len(priorities)}")

    # 3. 生成 Markdown 报告
    print("=== 渲染可视化报告 ===")
    renderer = ReportRenderer("Demo Project")
    markdown_report = renderer.render_full_report(scan, quality, risk)
    print(f"   报告长度: {len(markdown_report)} 字符")

    # 4. 验证 Mermaid 图表完整性
    print("=== 验证 Mermaid 图表 ===")
    mermaid_count = markdown_report.count("```mermaid")
    print(f"   Mermaid 图表块数量: {mermaid_count}")

    mermaid_types = []
    for line in markdown_report.split("\n"):
        if "```mermaid" in line:
            continue
        if line.strip().startswith("graph") or line.strip().startswith("flowchart"):
            mermaid_types.append("graph/flowchart")
        elif line.strip().startswith("pie"):
            mermaid_types.append("pie")
        elif line.strip().startswith("timeline"):
            mermaid_types.append("timeline")
        elif line.strip().startswith("gantt"):
            mermaid_types.append("gantt")

    unique_types = list(set(mermaid_types))
    print(f"   图表类型: {', '.join(unique_types)}")

    # 验证节点标签引号包裹
    quoted_labels = 0
    for line in markdown_report.split("\n"):
        if '["' in line and ('"\\n' in line or '")' in line):
            quoted_labels += 1
    print(f"   引号包裹的节点标签数: {quoted_labels}")

    # 5. 保存报告
    output_path = "/workspace/legacy-code-analyzer/demo_visual_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    print(f"\n=== 演示完成 ===")
    print(f"   可视化报告已生成: {output_path}")
    print(f"   报告包含 {mermaid_count} 个 Mermaid 图表")
    print(f"   图表类型: {', '.join(unique_types)}")
    print(f"   报告结构: 头部 → 项目概览 → 技术栈 → 模块依赖图 → "
          f"质量评估 → 缺陷饼图 → 缺陷详情 → 风险评估 → 重构优先级 → "
          f"时间线 → 甘特图 → 总结")


if __name__ == "__main__":
    main()