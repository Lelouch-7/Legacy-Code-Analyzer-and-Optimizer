"""
Legacy Code Analyzer & Optimizer - 模块集成入口

将所有 8 个分析模块整合为统一的 API 接口，
支持独立启用或组合使用各模块。

模块列表：
  - Module 1: scanner.py          (代码元数据与结构分析)
  - Module 2: semantic_analyzer.py (语义解析与设计意图推断)
  - Module 3: dependency_analyzer.py (依赖关系挖掘与耦合度分析)
  - Module 4: quality_evaluator.py  (代码质量评估与缺陷检测)
  - Module 5: risk_advisor.py       (风险预警与修改指导)
  - Module 6: test_generator.py     (自动化测试与重构辅助)
  - Module 7: interactive_explorer.py (交互式代码探索)
  - Module 8: requirement_tracer.py  (目标性评估与需求覆盖分析)
"""

from typing import Dict, List, Optional, Any
from pathlib import Path

# 导入各模块入口函数
from .scanner import scan_project, CodeScanner
from .semantic_analyzer import analyze_semantics, SemanticAnalyzer
from .dependency_analyzer import analyze_dependencies, analyze_impact, DependencyAnalyzer
from .quality_evaluator import evaluate_quality, QualityEvaluator
from .risk_advisor import generate_risk_advice, RiskAdvisor
from .test_generator import generate_tests, plan_refactoring, TestGenerator, RefactoringAssistant
from .interactive_explorer import explore_code, InteractiveExplorer
from .requirement_tracer import trace_requirements, RequirementTracer, TargetAssessmentReport
from .report_renderer import ReportRenderer
from .shared import Language, identify_language, EXCLUDE_DIRS


class LegacyCodeAnalyzer:
    """
    遗留代码分析器 - 顶层集成类

    使用示例：
        analyzer = LegacyCodeAnalyzer("/path/to/project")

        # 模块 1: 扫描项目
        scan_result = analyzer.scan()

        # 模块 2: 语义分析
        semantic_result = analyzer.analyze_semantics()

        # 模块 3: 依赖分析
        dependency_result = analyzer.analyze_dependencies()

        # 模块 4: 质量评估
        quality_result = analyzer.evaluate_quality()

        # 模块 5: 风险预警（依赖模块 4 的输出）
        risk_result = analyzer.advise_risks(quality_result["all_defects"],
                                             quality_result["module_reports"])

        # 模块 6: 测试生成
        test_result = analyzer.generate_tests()

        # 模块 7: 交互式探索
        exploration = analyzer.explore("这个函数是做什么的？")

        # 模块 8: 需求覆盖分析
        req_result = analyzer.trace_requirements("需求文本...")

        # 完整分析
        full_report = analyzer.run_full_analysis(requirements="需求文本...")
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        if not self.project_root.exists():
            raise FileNotFoundError(f"Project root not found: {project_root}")

        # 延迟初始化各模块实例
        self._scanner: Optional[CodeScanner] = None
        self._semantic: Optional[SemanticAnalyzer] = None
        self._dependency: Optional[DependencyAnalyzer] = None
        self._quality: Optional[QualityEvaluator] = None
        self._risk: Optional[RiskAdvisor] = None
        self._test_gen: Optional[TestGenerator] = None
        self._refactor: Optional[RefactoringAssistant] = None
        self._explorer: Optional[InteractiveExplorer] = None
        self._tracer: Optional[RequirementTracer] = None

        # 缓存分析结果
        self._cache: Dict[str, Any] = {}

    # ================================================================
    # 模块 1: 代码扫描
    # ================================================================

    def scan(self) -> Dict:
        """执行代码元数据与结构分析"""
        if "scan" not in self._cache:
            result = scan_project(str(self.project_root))
            self._cache["scan"] = result
        return self._cache["scan"]

    # ================================================================
    # 模块 2: 语义分析
    # ================================================================

    def analyze_semantics(self, target_files: List[str] = None) -> Dict:
        """执行语义解析与设计意图推断"""
        return analyze_semantics(str(self.project_root), target_files)

    # ================================================================
    # 模块 3: 依赖分析
    # ================================================================

    def analyze_dependencies(self) -> Dict:
        """执行依赖关系挖掘与耦合度分析"""
        if "dependencies" not in self._cache:
            result = analyze_dependencies(str(self.project_root))
            self._cache["dependencies"] = result
            # 初始化依赖分析器实例供后续模块使用
            self._dependency = DependencyAnalyzer(str(self.project_root))
            self._dependency.discover_modules()
            self._dependency.extract_explicit_dependencies()
            self._dependency.build_dependency_graph()
        return self._cache["dependencies"]

    def analyze_impact(self, target_module: str) -> Dict:
        """分析修改某个模块的影响范围"""
        return analyze_impact(str(self.project_root), target_module)

    # ================================================================
    # 模块 4: 质量评估
    # ================================================================

    def evaluate_quality(self) -> Dict:
        """执行代码质量评估与缺陷检测"""
        if "quality" not in self._cache:
            result = evaluate_quality(str(self.project_root))
            self._cache["quality"] = result
        return self._cache["quality"]

    # ================================================================
    # 模块 5: 风险预警
    # ================================================================

    def advise_risks(self, defects: List[Dict] = None,
                      module_reports: List = None) -> Dict:
        """生成风险预警与修改指导"""
        if defects is None or module_reports is None:
            quality = self.evaluate_quality()
            defects = quality.get("all_defects", [])
            module_reports = quality.get("module_reports", [])

        # 转换为字典格式
        defect_dicts = []
        for d in defects:
            if hasattr(d, "__dict__"):
                cat = getattr(d, "category", "")
                if hasattr(cat, "value"):
                    cat = cat.value
                rl = getattr(d, "risk_level", "low")
                if hasattr(rl, "value"):
                    rl = rl.value
                defect_dicts.append({
                    "category": str(cat),
                    "description": getattr(d, "description", ""),
                    "file_path": getattr(d, "file_path", ""),
                    "line_number": getattr(d, "line_number", 0),
                    "risk_level": str(rl),
                })
            else:
                defect_dicts.append(d)

        return generate_risk_advice(str(self.project_root), defect_dicts, module_reports)

    # ================================================================
    # 模块 6: 测试生成与重构辅助
    # ================================================================

    def generate_tests(self, target_file: str = None) -> Dict:
        """生成测试用例"""
        return generate_tests(str(self.project_root), target_file)

    def plan_refactoring(self, target_file: str,
                          metrics: Dict[str, float] = None) -> Any:
        """制定重构计划"""
        return plan_refactoring(str(self.project_root), target_file, metrics)

    # ================================================================
    # 模块 7: 交互式探索
    # ================================================================

    def explore(self, query: str) -> Any:
        """交互式代码探索"""
        # 确保依赖分析器可用
        if not self._dependency:
            self.analyze_dependencies()

        return explore_code(
            str(self.project_root), query,
            dependency=self._dependency,
        )

    # ================================================================
    # 模块 8: 需求覆盖分析
    # ================================================================

    def trace_requirements(self, requirements_text: str) -> TargetAssessmentReport:
        """执行目标性评估与需求覆盖分析"""
        return trace_requirements(str(self.project_root), requirements_text)

    # ================================================================
    # 模块 9: 报告渲染
    # ================================================================

    def generate_report(self,
                         theme: str = "professional",
                         trace_result: dict = None) -> str:
        """
        基于已缓存的分析结果生成专业的 Markdown 报告

        参数：
            theme: 主题风格 (professional / dark / minimal)
            trace_result: 可选的需求追踪结果

        返回：
            渲染后的 Markdown 报告文本
        """
        scan = self._cache.get("scan", self.scan())
        quality = self._cache.get("quality", self.evaluate_quality())
        risk = self._cache.get("risk", self.advise_risks())

        renderer = ReportRenderer(
            project_name=self.project_root.name,
            style_theme=theme,
        )

        return renderer.render_full_report(
            scan_result=scan,
            quality_result=quality,
            risk_result=risk,
            trace_result=trace_result,
        )

    # ================================================================
    # 完整分析流程
    # ================================================================

    def run_full_analysis(self,
                           requirements: str = None,
                           modules: List[int] = None,
                           generate_markdown: bool = True,
                           report_theme: str = "professional") -> Dict:
        """
        执行完整分析流程

        参数：
            requirements: 可选的需求文本，提供后自动激活模块 8
            modules: 可选，指定要执行的模块编号列表
                    默认执行 [1, 2, 3, 4, 5, 6]
            generate_markdown: 是否生成 Markdown 报告文本（默认 True）
            report_theme: 报告主题风格（professional / dark / minimal）

        返回：
            包含所有模块分析结果的完整报告字典。
            当 generate_markdown=True 时额外包含 'markdown_report' 字段。
        """
        if modules is None:
            modules = [1, 2, 3, 4, 5, 6]

        report = {
            "project_root": str(self.project_root),
            "modules_executed": modules,
            "report_generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 模块 1: 扫描
        if 1 in modules:
            report["scan"] = self.scan()

        # 模块 2: 语义分析
        if 2 in modules:
            report["semantic"] = self.analyze_semantics()

        # 模块 3: 依赖分析
        if 3 in modules:
            report["dependencies"] = self.analyze_dependencies()

        # 模块 4: 质量评估
        if 4 in modules:
            report["quality"] = self.evaluate_quality()

        # 模块 5: 风险预警（依赖模块 4）
        if 5 in modules:
            quality = report.get("quality", self.evaluate_quality())
            report["risk"] = self.advise_risks(
                quality.get("all_defects", []),
                quality.get("module_reports", []),
            )

        # 模块 6: 测试生成
        if 6 in modules:
            report["tests"] = self.generate_tests()

        # 模块 8: 需求覆盖（仅在提供需求文本时执行）
        trace_result = None
        if requirements:
            trace_result = self.trace_requirements(requirements)
            report["requirement_trace"] = trace_result

        # 生成 Markdown 报告
        if generate_markdown:
            report["markdown_report"] = self.generate_report(
                theme=report_theme,
                trace_result=trace_result,
            )

        return report


# ================================================================
# 便捷函数
# ================================================================

def quick_scan(project_root: str) -> Dict:
    """快速扫描：仅执行模块 1（代码结构分析）"""
    analyzer = LegacyCodeAnalyzer(project_root)
    return analyzer.scan()


def quick_quality(project_root: str) -> Dict:
    """快速质量检查：仅执行模块 4（代码质量评估）"""
    analyzer = LegacyCodeAnalyzer(project_root)
    return analyzer.evaluate_quality()


def full_analysis(project_root: str, requirements: str = None) -> Dict:
    """完整分析：执行所有模块"""
    analyzer = LegacyCodeAnalyzer(project_root)
    return analyzer.run_full_analysis(requirements=requirements)


def render_full_report(project_root: str,
                        scan_result: dict,
                        quality_result: dict,
                        risk_result: dict,
                        trace_result: dict = None,
                        project_name: str = None,
                        theme: str = "professional") -> str:
    """
    便捷函数：使用 ReportRenderer 将分析结果渲染为 Markdown 报告

    参数：
        project_root: 项目根路径
        scan_result: 扫描模块的结果字典
        quality_result: 质量评估模块的结果字典
        risk_result: 风险预警模块的结果字典
        trace_result: 可选的需求追踪结果字典
        project_name: 项目显示名称（默认使用根目录名）
        theme: 报告主题风格（professional / dark / minimal）

    返回：
        渲染后的 Markdown 报告文本
    """
    from pathlib import Path

    if project_name is None:
        project_name = Path(project_root).name

    renderer = ReportRenderer(project_name=project_name, style_theme=theme)
    return renderer.render_full_report(
        scan_result=scan_result,
        quality_result=quality_result,
        risk_result=risk_result,
        trace_result=trace_result,
    )