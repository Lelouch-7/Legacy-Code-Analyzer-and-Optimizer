#!/usr/bin/env python3
"""Legacy Code Analyzer — 一键导出打包脚本

用法：
    python export_skill.py                    # 默认导出到当前目录
    python export_skill.py --output /path/to  # 导出到指定目录
    python export_skill.py --no-report        # 不包含自评估报告

导出的 .zip 文件可直接上传到 TRAE SOLO 平台或分享给他人。
"""

import argparse
import os
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).parent.resolve()
EXPORT_NAME = "legacy-code-analyzer"

ESSENTIAL_FILES = [
    # 技能入口
    "SKILL.md",
    "analyzer-guideline.md",
    "README.md",
    # 核心模块
    "modules/__init__.py",
    "modules/shared.py",
    "modules/scanner.py",
    "modules/semantic_analyzer.py",
    "modules/dependency_analyzer.py",
    "modules/quality_evaluator.py",
    "modules/risk_advisor.py",
    "modules/test_generator.py",
    "modules/interactive_explorer.py",
    "modules/requirement_tracer.py",
    "modules/report_renderer.py",
    # 演示
    "demo_visual.py",
    "demo_visual_report.md",
]

OPTIONAL_REPORT_FILES = [
    "self_evaluate.py",
    "self-evaluation-report.md",
    "export_skill.py",
]


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024 / 1024:.1f} MB"


def collect_files(include_report: bool) -> list:
    files = []
    for rel_path in ESSENTIAL_FILES:
        abs_path = SKILL_DIR / rel_path
        if abs_path.exists():
            files.append((rel_path, abs_path))
        else:
            print(f"  ⚠️  警告: 未找到 {rel_path}")

    if include_report:
        for rel_path in OPTIONAL_REPORT_FILES:
            abs_path = SKILL_DIR / rel_path
            if abs_path.exists():
                files.append((rel_path, abs_path))

    return files


def create_export(output_dir: str, include_report: bool) -> Path:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    zip_name = f"{EXPORT_NAME}-skill.zip"
    zip_path = output_path / zip_name

    files_to_pack = collect_files(include_report)
    total_size = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, abs_path in files_to_pack:
            # Store with the skill directory prefix
            archive_name = f"{EXPORT_NAME}/{rel_path}"
            zf.write(abs_path, archive_name)
            total_size += abs_path.stat().st_size

    return zip_path, len(files_to_pack), total_size


def print_tree(output_dir: str, include_report: bool):
    files_to_pack = [f for f, _ in collect_files(include_report)]
    rel_dir = Path(output_dir).resolve()

    modules_files = [f for f in files_to_pack if f.startswith("modules/")]
    root_files = [f for f in files_to_pack if not f.startswith("modules/")]

    print(f"📦  {EXPORT_NAME}/")
    for f in sorted(root_files):
        size = format_size((SKILL_DIR / f).stat().st_size)
        print(f"   ├── {f}  ({size})")
    print(f"   ├── modules/")
    for f in sorted(modules_files):
        name = f.replace("modules/", "", 1)
        size = format_size((SKILL_DIR / f).stat().st_size)
        print(f"   │   ├── {name}  ({size})")
    print()
    if not include_report:
        print("   (自评估和导出脚本已排除)")
    else:
        print("   (包含自评估和导出脚本)")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Legacy Code Analyzer — 一键导出打包工具"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(SKILL_DIR),
        help=f"导出目录 (默认: {SKILL_DIR})",
    )
    parser.add_argument(
        "--no-report", action="store_true",
        help="不包含自评估报告文件 (self_evaluate.py / self-evaluation-report.md)",
    )
    args = parser.parse_args()

    include_report = not args.no_report

    print("=" * 60)
    print("  Legacy Code Analyzer — 技能导出工具")
    print("=" * 60)
    print()

    # 展示目录结构
    print("📂 导出的文件结构:")
    print_tree(args.output, include_report)

    # 打包
    print("🔨 正在打包...")
    zip_path, file_count, total_size = create_export(args.output, include_report)

    print(f"✅ 导出完成!")
    print(f"   导出路径: {zip_path}")
    print(f"   文件数:   {file_count}")
    print(f"   大小:     {format_size(total_size)} (压缩后: {format_size(zip_path.stat().st_size)})")
    print()
    print("📋 下一步:")
    print(f"   1. 将 {zip_path.name} 下载到本地")
    print(f"   2. 在 TRAE SOLO 平台的工作区中解压")
    print(f"   3. 确保 SKILL.md 在项目根目录")
    print("=" * 60)


if __name__ == "__main__":
    main()