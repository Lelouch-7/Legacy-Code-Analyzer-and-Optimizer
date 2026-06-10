"""
模块 5：风险预警与修改指导 (Risk Advisor)

针对高风险代码，输出详细的风险说明、连锁反应分析、
标准化修改指南和重构优先级列表。

关键依赖：
- 模块 3 (DependencyAnalyzer): 影响范围分析
- 模块 4 (QualityEvaluator): 缺陷数据来源
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path


class RiskLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ModificationPriority(Enum):
    P0 = "P0 - 安全漏洞修复"
    P1 = "P1 - 稳定性修复"
    P2 = "P2 - 技术债务清理"
    P3 = "P3 - 架构优化"


@dataclass
class RiskItem:
    risk_id: str
    name: str
    level: RiskLevel
    file_path: str
    line_number: int
    description: str
    potential_impact: str
    trigger_conditions: List[str]
    affected_modules: List[str]
    chain_reaction: List["ChainReaction"]


@dataclass
class ChainReaction:
    affected_module: str
    reason: str
    impact_degree: str  # "direct" | "indirect"
    required_changes: List[str]


@dataclass
class ModificationGuide:
    priority: ModificationPriority
    risk_items: List[RiskItem]
    modification_order: List[str]
    precautions: List[str]
    alternative_implementations: List["AlternativeImplementation"]


@dataclass
class AlternativeImplementation:
    original: str
    problem: str
    recommendation: str
    risk_reduction: str  # "high" | "medium" | "low"
    code_example: Optional[str] = None


class RiskAdvisor:
    """
    风险顾问 - 模块 5 核心类

    工作流：
    1. assess_risk()              → 评估单个缺陷的风险等级
    2. analyze_chain_reaction()   → 分析修改的连锁影响
    3. generate_modification_guide() → 生成修改指南
    4. prioritize_refactoring()   → 生成重构优先级列表
    5. suggest_alternatives()     → 推荐替代实现方案
    """

    def __init__(self, project_root: str,
                 dependency_analyzer=None,
                 quality_evaluator=None):
        self.project_root = Path(project_root)
        self.dependency_analyzer = dependency_analyzer
        self.quality_evaluator = quality_evaluator

    def assess_risk(self, defect: Dict) -> RiskItem:
        """
        评估单个缺陷的风险

        综合考虑：
        - 缺陷类型（安全 > 稳定性 > 可维护性）
        - 代码位置（核心模块 > 边缘模块）
        - 依赖广度（被依赖越多，风险越高）
        - 触发频率

        参数：
            defect: 缺陷信息字典

        返回：
            风险项对象
        """
        # 风险等级判断
        category = defect.get("category", "")
        level = RiskLevel.LOW

        if "security" in category.lower() or "vulnerability" in category.lower():
            level = RiskLevel.HIGH
        elif any(kw in category.lower() for kw in
                 ("missing_exception", "boundary", "logic_flaw")):
            level = RiskLevel.MEDIUM
        elif any(kw in category.lower() for kw in
                 ("redundant", "deprecated", "syntax")):
            level = RiskLevel.LOW

        # 潜在影响分析
        impact = self._assess_impact(defect)

        # 触发条件分析
        triggers = self._analyze_triggers(defect)

        return RiskItem(
            risk_id=f"RISK-{defect.get('line_number', 0):04d}",
            name=defect.get("description", "Unknown Risk")[:80],
            level=level,
            file_path=defect.get("file_path", ""),
            line_number=defect.get("line_number", 0),
            description=defect.get("description", ""),
            potential_impact=impact,
            trigger_conditions=triggers,
            affected_modules=[],
            chain_reaction=[],
        )

    def _assess_impact(self, defect: Dict) -> str:
        """评估缺陷的潜在影响"""
        category = defect.get("category", "")
        impacts = {
            "security_vulnerability": "可能导致数据泄露、未授权访问或系统被攻击者控制",
            "syntax_error": "代码无法正常编译/运行，阻塞开发和部署流程",
            "logic_flaw": "在特定条件下产生错误的计算结果或业务流程",
            "missing_exception": "运行时错误可能导致程序崩溃或数据不一致",
            "boundary_coverage": "极端输入可能触发未定义行为或系统崩溃",
            "deprecated_dependency": "依赖库停止维护，可能包含已知安全漏洞",
            "redundant_code": "增加代码维护成本，可能隐藏未修复的 Bug",
        }
        return impacts.get(category, "可能影响代码的可维护性和稳定性")

    def _analyze_triggers(self, defect: Dict) -> List[str]:
        """分析触发条件"""
        category = defect.get("category", "")
        triggers = {
            "security_vulnerability": [
                "恶意用户构造特殊输入",
                "系统暴露在公网环境中",
                "未启用 WAF 或其他安全防护",
            ],
            "logic_flaw": [
                "输入特定边界值",
                "并发访问时的竞态条件",
                "特定业务状态组合",
            ],
            "missing_exception": [
                "外部依赖不可用（数据库、API）",
                "输入数据格式不符合预期",
                "文件系统权限不足",
            ],
            "boundary_coverage": [
                "输入为空字符串或 None",
                "数组/列表长度为 0",
                "数值超出预期范围",
            ],
        }
        return triggers.get(category, ["代码被执行时"])

    def analyze_chain_reaction(self, risk_item: RiskItem) -> List[ChainReaction]:
        """
        分析修改某个文件可能引发的连锁反应

        使用依赖分析器追踪：
        1. 直接依赖该文件的所有模块
        2. 间接依赖（通过中间模块传递）
        3. 每个受影响模块需要的调整

        参数：
            risk_item: 风险项

        返回：
            连锁反应列表
        """
        reactions = []

        if self.dependency_analyzer:
            file_path = risk_item.file_path
            module = Path(file_path).parent.name

            impact = self.dependency_analyzer.generate_impact_analysis(module)

            # 直接影响
            for dep in impact.get("direct_dependents", []):
                reactions.append(ChainReaction(
                    affected_module=dep,
                    reason=f"模块 `{dep}` 直接依赖 `{module}`",
                    impact_degree="direct",
                    required_changes=[
                        f"检查 `{dep}` 中对 `{module}` 的 import 和函数调用",
                        f"验证 `{dep}` 的接口契约是否仍然满足",
                    ],
                ))

            # 间接影响
            for dep in impact.get("indirect_dependents", []):
                reactions.append(ChainReaction(
                    affected_module=dep,
                    reason=f"模块 `{dep}` 通过中间模块间接依赖 `{module}`",
                    impact_degree="indirect",
                    required_changes=[
                        f"确认 `{dep}` 与 `{module}` 之间的数据格式兼容性",
                        f"回归测试 `{dep}` 的核心功能",
                    ],
                ))

        return reactions

    def generate_modification_guide(self, risks: List[RiskItem]) -> ModificationGuide:
        """
        生成标准化修改指南

        包括：
        - 修改顺序（安全 → 稳定 → 可维护 → 架构）
        - 每步的注意事项
        - 验证检查点

        参数：
            risks: 风险项列表

        返回：
            修改指南对象
        """
        # 按优先级排序
        sorted_risks = sorted(risks, key=lambda r: (
            0 if r.level == RiskLevel.HIGH else
            1 if r.level == RiskLevel.MEDIUM else 2
        ))

        # 分类
        p0_risks = [r for r in sorted_risks if r.level == RiskLevel.HIGH]
        p1_risks = [r for r in sorted_risks if r.level == RiskLevel.MEDIUM]
        p2_risks = [r for r in sorted_risks if r.level == RiskLevel.LOW]

        # 修改顺序
        order = []
        if p0_risks:
            order.append(f"1. 优先修复 {len(p0_risks)} 个高风险安全漏洞")
        if p1_risks:
            order.append(f"2. 修复 {len(p1_risks)} 个稳定性问题")
        if p2_risks:
            order.append(f"3. 清理 {len(p2_risks)} 个技术债务")

        # 注意事项
        precautions = [
            "每次修改前创建代码备份或 Git commit",
            "每次修改后运行回归测试",
            "高风险修改先在隔离环境验证",
            "修改涉及接口变更时，通知所有依赖方",
            "避免同时修改多个高风险区域",
            "保留原始代码注释记录修改原因",
        ]

        # 替代方案
        alternatives = self.suggest_alternatives(p0_risks + p1_risks)

        priority = ModificationPriority.P0 if p0_risks else \
                   ModificationPriority.P1 if p1_risks else \
                   ModificationPriority.P2 if p2_risks else \
                   ModificationPriority.P3

        return ModificationGuide(
            priority=priority,
            risk_items=sorted_risks,
            modification_order=order,
            precautions=precautions,
            alternative_implementations=alternatives,
        )

    def suggest_alternatives(self, risks: List[RiskItem]) -> List[AlternativeImplementation]:
        """
        推荐替代实现方案

        参数：
            risks: 风险项列表

        返回：
            替代方案列表
        """
        alternatives = []

        alt_map = {
            "SQL": AlternativeImplementation(
                original="字符串拼接 SQL 查询",
                problem="SQL 注入漏洞",
                recommendation="使用 ORM 参数化查询（如 SQLAlchemy、JPA）",
                risk_reduction="high",
            ),
            "XSS": AlternativeImplementation(
                original="直接设置 innerHTML / 危险的 HTML 属性",
                problem="跨站脚本攻击 (XSS)",
                recommendation="使用 textContent 或 React 的 JSX 自动转义",
                risk_reduction="high",
            ),
            "pickle": AlternativeImplementation(
                original="pickle 反序列化",
                problem="不安全的反序列化可导致远程代码执行",
                recommendation="使用 JSON 或 protobuf 进行序列化",
                risk_reduction="high",
            ),
            "global": AlternativeImplementation(
                original="全局变量存储配置",
                problem="隐式耦合，难以测试和追踪",
                recommendation="使用依赖注入或配置对象传递",
                risk_reduction="medium",
            ),
            "hardcoded": AlternativeImplementation(
                original="硬编码常量",
                problem="环境变化时需要修改代码",
                recommendation="提取到配置文件或环境变量",
                risk_reduction="medium",
            ),
        }

        for risk in risks:
            for key, alt in alt_map.items():
                if key.lower() in risk.description.lower():
                    if alt not in alternatives:
                        alternatives.append(alt)

        return alternatives

    def prioritize_refactoring(self, module_reports: List,
                                risk_items: List[RiskItem]) -> List[Dict]:
        """
        生成重构优先级列表

        聚焦高价值且高风险的模块

        排序规则：
        1. 包含高风险缺陷的模块优先
        2. 可维护性评分低的模块优先
        3. 被依赖多的模块优先

        参数：
            module_reports: 模块质量报告列表
            risk_items: 风险项列表

        返回：
            重构优先级列表
        """
        priorities = []

        for report in module_reports:
            module_risks = [
                r for r in risk_items
                if Path(r.file_path).parent.name == report.module_name
            ]

            high_risks = sum(1 for r in module_risks if r.level == RiskLevel.HIGH)
            medium_risks = sum(1 for r in module_risks if r.level == RiskLevel.MEDIUM)

            priority_score = (
                high_risks * 100 +
                medium_risks * 30 +
                (10 - report.overall_score) * 10
            )

            if priority_score > 0:
                priorities.append({
                    "module": report.module_name,
                    "priority_score": priority_score,
                    "high_risks": high_risks,
                    "medium_risks": medium_risks,
                    "quality_score": report.overall_score,
                    "rating": report.rating,
                    "recommendation": self._get_refactoring_recommendation(
                        high_risks, report.overall_score
                    ),
                })

        return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)

    def _get_refactoring_recommendation(self, high_risks: int,
                                         quality_score: float) -> str:
        """生成重构建议"""
        if high_risks > 0:
            return "🔴 紧急：包含安全漏洞，建议立即修复"
        elif quality_score < 4.0:
            return "🔴 优先：可维护性极差，建议尽快重构"
        elif quality_score < 6.0:
            return "🟡 计划：建议纳入下个迭代的重构计划"
        elif quality_score < 8.0:
            return "🟢 优化：可逐步改进代码质量"
        else:
            return "✅ 良好：保持现状即可"

    def generate_risk_report(self, defects: List[Dict],
                              module_reports: List) -> Dict:
        """
        生成完整的风险预警报告

        参数：
            defects: 缺陷列表（来自模块 4）
            module_reports: 模块质量报告（来自模块 4）

        返回：
            风险报告字典
        """
        # 评估每个缺陷的风险
        risk_items = [self.assess_risk(d) for d in defects]

        # 分析连锁反应
        for risk in risk_items:
            risk.chain_reaction = self.analyze_chain_reaction(risk)

        # 生成修改指南
        guide = self.generate_modification_guide(risk_items)

        # 重构优先级
        priorities = self.prioritize_refactoring(module_reports, risk_items)

        # 高风险统计
        high_risks = [r for r in risk_items if r.level == RiskLevel.HIGH]
        medium_risks = [r for r in risk_items if r.level == RiskLevel.MEDIUM]

        return {
            "summary": {
                "total_risks": len(risk_items),
                "high": len(high_risks),
                "medium": len(medium_risks),
                "low": len(risk_items) - len(high_risks) - len(medium_risks),
            },
            "high_risk_items": high_risks,
            "medium_risk_items": medium_risks,
            "modification_guide": guide,
            "refactoring_priorities": priorities,
        }


# ============================================================
# 入口函数
# ============================================================

def generate_risk_advice(project_root: str,
                          defects: List[Dict],
                          module_reports: List) -> Dict:
    """
    模块 5 入口函数

    参数：
        project_root: 项目根目录
        defects: 模块 4 输出的缺陷列表
        module_reports: 模块 4 输出的模块质量报告

    返回：
        风险预警报告字典
    """
    advisor = RiskAdvisor(project_root)
    return advisor.generate_risk_report(defects, module_reports)