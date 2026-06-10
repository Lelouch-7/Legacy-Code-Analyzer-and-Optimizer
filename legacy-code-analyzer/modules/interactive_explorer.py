"""
模块 7：交互式代码探索 (Interactive Explorer)

支持开发者通过自然语言查询具体模块/函数的功能、
逻辑细节、依赖关系及风险，并提供 Mermaid 流程图生成。

关键依赖：
- re: 查询意图解析
- 模块 2-5: 语义、依赖、质量、风险数据源
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path


class QueryIntent(Enum):
    FUNCTION_EXPLAIN = "function_explain"
    DESIGN_INTENT = "design_intent"
    DEPENDENCY_QUERY = "dependency_query"
    RISK_ASSESSMENT = "risk_assessment"
    CODE_LOCATION = "code_location"
    REFACTORING_ADVICE = "refactoring_advice"
    GENERAL_QA = "general_qa"


@dataclass
class ParsedQuery:
    intent: QueryIntent
    target: str
    context: Dict
    original_query: str


@dataclass
class QueryResponse:
    intent: QueryIntent
    summary: str
    details: List[str]
    mermaid_diagram: Optional[str] = None
    code_references: List[str] = field(default_factory=list)
    risk_level: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class QueryParser:
    """
    查询解析器

    将自然语言查询解析为结构化的查询意图
    """

    INTENT_PATTERNS = {
        QueryIntent.FUNCTION_EXPLAIN: [
            r"(做什么|功能|作用|干什么|怎么用|how\s+does|what\s+does|explain)",
            r"(解释|说明|describe|explanation)",
        ],
        QueryIntent.DESIGN_INTENT: [
            r"(为什么|why|设计|design|意图|intent|初衷|思路)",
            r"(这样写|这种|这种设计|这种实现)",
        ],
        QueryIntent.DEPENDENCY_QUERY: [
            r"(依赖|depend|影响|affect|impact|调用|call)",
            r"(谁在用|谁依赖|who\s+uses|what\s+depends)",
        ],
        QueryIntent.RISK_ASSESSMENT: [
            r"(风险|risk|危险|danger|问题|problem|漏洞|vulnerability)",
            r"(安全|security|bug|缺陷)",
        ],
        QueryIntent.CODE_LOCATION: [
            r"(在哪里|where|位置|location|文件|file)",
            r"(哪个文件|which\s+file|locate)",
        ],
        QueryIntent.REFACTORING_ADVICE: [
            r"(重构|refactor|优化|optimize|改进|improve)",
            r"(建议|advice|推荐|recommend)",
        ],
    }

    def parse(self, query: str) -> ParsedQuery:
        """
        解析自然语言查询

        参数：
            query: 用户的自然语言查询

        返回：
            解析后的查询对象
        """
        query_lower = query.lower()
        intent_scores = {}

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            intent_scores[intent] = score

        # 选择最高分的意图
        best_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[best_intent] == 0:
            best_intent = QueryIntent.GENERAL_QA

        # 提取目标（函数名、模块名、文件名）
        target = self._extract_target(query)

        return ParsedQuery(
            intent=best_intent,
            target=target,
            context={"raw_query": query, "intent_scores": intent_scores},
            original_query=query,
        )

    def _extract_target(self, query: str) -> str:
        """
        从查询中提取目标标识符

        匹配模式：
        - 驼峰命名：UserService, getUserData
        - 蛇形命名：user_service, get_user_data
        - 文件名：api.py, UserController.java

        参数：
            query: 查询文本

        返回：
            目标标识符
        """
        # 匹配代码标识符
        patterns = [
            r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b",      # PascalCase
            r"\b([a-z]+_[a-z]+(?:_[a-z]+)*)\b",         # snake_case
            r"\b([a-z]+[A-Z][a-z]+(?:[A-Z][a-z]+)*)\b", # camelCase
            r"\b([\w]+\.(?:py|java|js|ts|cpp))\b",      # 文件名
        ]

        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)

        return ""


class FlowchartGenerator:
    """
    Mermaid 流程图生成器

    根据函数逻辑生成 Mermaid flowchart 格式的流程图
    """

    def generate_from_code(self, code: str, function_name: str) -> str:
        """
        从源代码生成流程图

        参数：
            code: 函数源代码
            function_name: 函数名

        返回：
            Mermaid flowchart 字符串
        """
        lines = ["flowchart TD"]

        # 开始节点
        lines.append(f'    S["Start: {function_name}()"]')

        # 分析代码生成节点
        nodes = self._extract_flow_nodes(code)
        node_ids = {}
        prev_id = "S"

        for i, node in enumerate(nodes):
            node_id = f"N{i}"
            node_ids[i] = node_id

            if node["type"] == "condition":
                lines.append(f'    {node_id}{{{{"{node["label"]}"}}}}')
                lines.append(f"    {prev_id} --> {node_id}")
                prev_id = node_id
            elif node["type"] == "action":
                lines.append(f'    {node_id}["{node["label"]}"]')
                lines.append(f"    {prev_id} --> {node_id}")
                prev_id = node_id
            elif node["type"] == "return":
                lines.append(f'    {node_id}["{node["label"]}"]')
                lines.append(f"    {prev_id} --> {node_id}")

        # 结束节点
        lines.append(f'    E["End"]')
        if prev_id:
            lines.append(f"    {prev_id} --> E")

        return "\n".join(lines)

    def _extract_flow_nodes(self, code: str) -> List[Dict]:
        """从代码提取流程节点"""
        nodes = []
        lines = code.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("if ") or stripped.startswith("elif "):
                condition = stripped[3:].rstrip(":")
                nodes.append({
                    "type": "condition",
                    "label": condition[:30],
                    "line": i + 1,
                })
            elif stripped.startswith("for ") or stripped.startswith("while "):
                nodes.append({
                    "type": "condition",
                    "label": stripped[:30],
                    "line": i + 1,
                })
            elif stripped.startswith("return "):
                nodes.append({
                    "type": "return",
                    "label": stripped[:30],
                    "line": i + 1,
                })
            elif "=" in stripped and not stripped.startswith(("if", "for", "while", "return")):
                nodes.append({
                    "type": "action",
                    "label": stripped[:30],
                    "line": i + 1,
                })

        return nodes[:10]


class InteractiveExplorer:
    """
    交互式代码探索器 - 模块 7 核心类

    工作流：
    1. parse_query()         → 解析用户查询
    2. locate_code()         → 定位相关代码
    3. analyze_context()     → 分析代码上下文
    4. generate_response()   → 生成自然语言响应
    5. generate_flowchart()  → 生成流程图
    """

    def __init__(self, project_root: str,
                 semantic_analyzer=None,
                 dependency_analyzer=None,
                 quality_evaluator=None,
                 risk_advisor=None):
        self.project_root = Path(project_root)
        self.semantic = semantic_analyzer
        self.dependency = dependency_analyzer
        self.quality = quality_evaluator
        self.risk = risk_advisor
        self.parser = QueryParser()
        self.flowchart_gen = FlowchartGenerator()

    INTENT_TO_ANALYSIS_TYPE = {
        QueryIntent.FUNCTION_EXPLAIN: "explain",
        QueryIntent.DEPENDENCY_QUERY: "dependencies",
        QueryIntent.RISK_ASSESSMENT: "risk",
        QueryIntent.REFACTORING_ADVICE: "cyclomatic_complexity",
    }

    def process_query(self, query: str) -> QueryResponse:
        """
        处理自然语言查询

        参数：
            query: 用户的自然语言查询

        返回：
            查询响应对象
        """
        parsed = self.parser.parse(query)

        analysis_type = self.INTENT_TO_ANALYSIS_TYPE.get(parsed.intent)
        if analysis_type and parsed.target:
            analysis_result = self._execute_analysis(analysis_type, parsed.target, parsed.context)
            if analysis_result.get("data") is not None:
                return self._build_response_from_analysis(parsed, analysis_result)

        if parsed.intent == QueryIntent.FUNCTION_EXPLAIN:
            return self._handle_function_explain(parsed)
        elif parsed.intent == QueryIntent.DESIGN_INTENT:
            return self._handle_design_intent(parsed)
        elif parsed.intent == QueryIntent.DEPENDENCY_QUERY:
            return self._handle_dependency_query(parsed)
        elif parsed.intent == QueryIntent.RISK_ASSESSMENT:
            return self._handle_risk_assessment(parsed)
        elif parsed.intent == QueryIntent.REFACTORING_ADVICE:
            return self._handle_refactoring_advice(parsed)
        else:
            return self._handle_general_qa(parsed)

    def _build_response_from_analysis(self, parsed: ParsedQuery, analysis_result: dict) -> QueryResponse:
        data = analysis_result.get("data", {})
        analysis_type = analysis_result.get("type", "")

        if analysis_type in ("cyclomatic_complexity", "cc", "圈复杂度", "复杂度"):
            return QueryResponse(
                intent=QueryIntent.REFACTORING_ADVICE,
                summary=f"**{parsed.target}** 的代码复杂度分析：",
                details=[
                    f"圈复杂度：{data.get('cyclomatic_complexity', 'N/A')}",
                    f"Halstead 容量：{data.get('halstead_volume', 'N/A')}",
                    f"评级：{data.get('rating', 'N/A')}",
                ],
                suggestions=[
                    "圈复杂度 > 20 时建议拆分函数",
                    "减少嵌套层级和条件分支数量",
                ],
            )

        elif analysis_type in ("dependencies", "dependency", "impact", "依赖", "影响"):
            direct = data.get("direct_dependents", [])
            indirect = data.get("indirect_dependents", [])
            return QueryResponse(
                intent=QueryIntent.DEPENDENCY_QUERY,
                summary=f"修改 `{parsed.target}` 的影响范围分析：",
                details=[
                    f"**直接依赖方** ({len(direct)} 个)：{', '.join(direct[:5])}",
                    f"**间接影响范围** ({len(indirect)} 个)：{', '.join(indirect[:5])}",
                    f"**风险等级**：{data.get('risk_level', 'unknown')}",
                ],
                risk_level="medium",
                suggestions=[
                    "修改前检查所有直接调用者",
                    "运行完整回归测试",
                ],
            )

        elif analysis_type in ("risk", "security", "风险", "安全"):
            risk_count = data.get("risk_count", 0)
            findings = data.get("findings", [])
            details = [f"发现 {risk_count} 个潜在安全问题"]
            for f in findings[:5]:
                details.append(f"L{f['line']}: [{f['category']}] {f['description']}")
            return QueryResponse(
                intent=QueryIntent.RISK_ASSESSMENT,
                summary=f"**{parsed.target}** 的安全风险扫描结果：",
                details=details,
                risk_level="high" if risk_count > 3 else "medium" if risk_count > 0 else "low",
                suggestions=[
                    "优先修复高风险安全漏洞",
                    "参考 OWASP 修复指南进行整改",
                ],
            )

        elif analysis_type in ("explain", "function", "功能", "解释"):
            funcs = data.get("functions", [])
            return QueryResponse(
                intent=QueryIntent.FUNCTION_EXPLAIN,
                summary=f"**{parsed.target}** 的功能分析：",
                details=[
                    f"文件：{data.get('file', 'N/A')}",
                    f"函数数量：{data.get('function_count', 0)}",
                ] + [f"`{f['name']}` (L{f['line']}, 参数: {f['params']})" for f in funcs[:5]],
                suggestions=[
                    "查看函数内部的注释和文档字符串",
                    "追踪函数调用链以理解数据流",
                ],
            )

        return self._handle_general_qa(parsed)

    def _handle_function_explain(self, query: ParsedQuery) -> QueryResponse:
        """处理功能解释类查询"""
        target = query.target or "目标代码"

        # 搜索目标函数
        code_refs = self._search_code(target)

        # 尝试生成流程图
        flowchart = None
        if code_refs:
            try:
                code = Path(self.project_root / code_refs[0]).read_text()
                flowchart = self.flowchart_gen.generate_from_code(code, target)
            except Exception:
                logging.getLogger(__name__).warning(f"Failed to generate flowchart for {target}")

        return QueryResponse(
            intent=QueryIntent.FUNCTION_EXPLAIN,
            summary=f"**{target}** 的功能分析：",
            details=[
                f"位置：{ref}" for ref in code_refs[:3]
            ] if code_refs else [
                f"在代码库中搜索 `{target}` 以获取更多信息",
                "分析控制流和数据流以理解核心逻辑",
            ],
            mermaid_diagram=flowchart,
            code_references=code_refs[:5],
            suggestions=[
                "查看函数内部的注释和文档字符串",
                "追踪函数调用链以理解数据流",
                "查看单元测试了解预期行为",
            ],
        )

    def _handle_design_intent(self, query: ParsedQuery) -> QueryResponse:
        """处理设计意图类查询"""
        return QueryResponse(
            intent=QueryIntent.DESIGN_INTENT,
            summary="设计意图推断：",
            details=[
                "基于代码结构和命名模式推断原始设计意图",
                "分析设计模式的使用（Singleton、Factory 等）",
                "检查临时方案和 TODO 标记以了解演进过程",
                "通过依赖关系推断架构决策",
            ],
            suggestions=[
                "查看 Git 提交历史了解设计演进",
                "检查是否存在设计文档或 README",
                "关注模块间的接口契约设计",
            ],
        )

    def _handle_dependency_query(self, query: ParsedQuery) -> QueryResponse:
        """处理依赖查询"""
        target = query.target or "目标模块"

        impact_info = []
        if self.dependency:
            impact = self.dependency.generate_impact_analysis(target)
            direct = impact.get("direct_dependents", [])
            indirect = impact.get("indirect_dependents", [])
            impact_info = [
                f"**直接依赖方** ({len(direct)} 个)：{', '.join(direct[:5])}",
                f"**间接影响范围** ({len(indirect)} 个)：{', '.join(indirect[:5])}",
                f"**风险等级**：{impact.get('risk_level', 'unknown')}",
            ]

        return QueryResponse(
            intent=QueryIntent.DEPENDENCY_QUERY,
            summary=f"修改 `{target}` 的影响范围分析：",
            details=impact_info or [
                "使用依赖分析器追踪调用关系",
                "检查显式 import 和隐式依赖",
                "评估循环依赖的影响",
            ],
            risk_level="medium",
            suggestions=[
                "修改前检查所有直接调用者",
                "运行完整回归测试",
                "考虑向后兼容的过渡方案",
            ],
        )

    def _handle_risk_assessment(self, query: ParsedQuery) -> QueryResponse:
        """处理风险评估查询"""
        target = query.target or "目标代码"
        return QueryResponse(
            intent=QueryIntent.RISK_ASSESSMENT,
            summary=f"**{target}** 的风险评估：",
            details=[
                "🔴 高风险：检查安全漏洞（SQL注入、XSS等）",
                "🟡 中风险：检查异常处理和边界条件",
                "🟢 低风险：检查代码规范和命名一致性",
            ],
            risk_level="high" if "sql" in query.original_query.lower() else "medium",
            suggestions=[
                "优先修复高风险安全漏洞",
                "添加缺失的异常处理",
                "补充边界条件检查",
            ],
        )

    def _handle_refactoring_advice(self, query: ParsedQuery) -> QueryResponse:
        """处理重构建议查询"""
        return QueryResponse(
            intent=QueryIntent.REFACTORING_ADVICE,
            summary="重构建议：",
            details=[
                "1. 拆分过长函数（>50行）为多个单一职责的小函数",
                "2. 提取重复代码为公共函数",
                "3. 统一命名风格（建议使用 snake_case）",
                "4. 减少嵌套层级（>3层需要重构）",
                "5. 引入依赖注入替代全局变量",
            ],
            suggestions=[
                "每次重构后运行回归测试",
                "使用 IDE 的重构工具减少手动错误",
                "优先重构高耦合低内聚的模块",
            ],
        )

    def _handle_general_qa(self, query: ParsedQuery) -> QueryResponse:
        """处理通用问答"""
        return QueryResponse(
            intent=QueryIntent.GENERAL_QA,
            summary=f"关于 `{query.original_query[:50]}...` 的回答：",
            details=[
                "建议使用更具体的查询方式",
                "可以指定函数名、模块名或文件名",
                "支持以下查询类型：功能解释、设计意图、依赖关系、风险评估、重构建议",
            ],
            suggestions=[
                '试试："`[函数名]` 的功能是什么？"',
                '试试："修改 `[模块名]` 会影响哪些地方？"',
                '试试："`[文件]` 存在哪些风险？"',
            ],
        )

    def _search_code(self, target: str) -> List[str]:
        """在代码库中搜索目标"""
        if not target:
            return []

        found = []
        for f in self.project_root.rglob("*.py"):
            try:
                content = f.read_text(encoding="utf-8")
                if target in content:
                    rel_path = str(f.relative_to(self.project_root))
                    # 找到具体行号
                    for i, line in enumerate(content.split("\n"), 1):
                        if target in line:
                            found.append(f"{rel_path}:L{i}")
                            break
            except Exception:
                logging.getLogger(__name__).warning(f"Failed to search code in {f}")
                continue

        return found[:10]

    def _execute_analysis(self, query_type: str, target: str, context: dict) -> dict:
        result = {"type": query_type, "target": target, "data": None, "error": None}

        try:
            file_path = self.project_root / target

            QUERY_HANDLERS = {
                "cyclomatic_complexity": self._handle_complexity_query,
                "cc": self._handle_complexity_query,
                "complexity": self._handle_complexity_query,
                "圈复杂度": self._handle_complexity_query,
                "复杂度": self._handle_complexity_query,
                "dependencies": self._handle_dependency_query,
                "dependency": self._handle_dependency_query,
                "依赖": self._handle_dependency_query,
                "impact": self._handle_impact_query,
                "影响": self._handle_impact_query,
                "risk": self._handle_risk_query,
                "security": self._handle_risk_query,
                "风险": self._handle_risk_query,
                "安全": self._handle_risk_query,
                "explain": self._handle_explain_query,
                "function": self._handle_function_query,
                "功能": self._handle_function_query,
                "解释": self._handle_explain_query,
            }

            handler = QUERY_HANDLERS.get(query_type)
            if handler:
                result["data"] = handler(query_type, file_path)
            else:
                result["error"] = f"Unsupported query type: {query_type}"

        except (FileNotFoundError, PermissionError, OSError) as e:
            logging.getLogger(__name__).warning(f"File access error in analysis query '{query_type}' for '{target}': {e}")
            result["error"] = f"File error: {e}"
        except Exception as e:  # 最外层兜底：确保分析失败不阻塞后续查询
            logging.getLogger(__name__).warning(f"Unexpected error in analysis query '{query_type}' for '{target}': {e}")
            result["error"] = str(e)

        return result

    def _handle_complexity_query(self, query: str, file_path: Path) -> Optional[dict]:
        """处理圈复杂度查询：分析指定文件的圈复杂度和 Halstead 容量"""
        from .quality_evaluator import QualityEvaluator
        qe = QualityEvaluator(str(self.project_root))
        if file_path.exists():
            code = file_path.read_text(encoding='utf-8', errors='ignore')
            cc = qe.calculate_cyclomatic_complexity(code)
            hv = qe.calculate_halstead_volume(code)
            return {
                "cyclomatic_complexity": cc,
                "halstead_volume": round(hv, 2),
                "rating": "优秀" if cc <= 10 else "良好" if cc <= 20 else "较差" if cc <= 50 else "极差"
            }
        return None

    def _handle_dependency_query(self, query: str, file_path: Path) -> Optional[dict]:
        """处理依赖关系查询：分析指定模块的直接和间接依赖方"""
        from .dependency_analyzer import DependencyAnalyzer
        da = DependencyAnalyzer(str(self.project_root))
        da.discover_modules()
        da.extract_explicit_dependencies()
        da.build_dependency_graph()
        target_name = str(file_path.relative_to(self.project_root))
        return da.generate_impact_analysis(target_name)

    def _handle_impact_query(self, query: str, file_path: Path) -> Optional[dict]:
        """处理影响范围查询：分析修改指定模块的影响范围"""
        from .dependency_analyzer import DependencyAnalyzer
        da = DependencyAnalyzer(str(self.project_root))
        da.discover_modules()
        da.extract_explicit_dependencies()
        da.build_dependency_graph()
        target_name = str(file_path.relative_to(self.project_root))
        return da.generate_impact_analysis(target_name)

    def _handle_risk_query(self, query: str, file_path: Path) -> Optional[dict]:
        """处理安全风险查询：扫描指定文件中的 OWASP 安全漏洞模式"""
        from .shared import OWASP_SECURITY_PATTERNS
        if file_path.exists():
            code = file_path.read_text(encoding='utf-8', errors='ignore')
            findings = []
            for category, patterns in OWASP_SECURITY_PATTERNS.items():
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, code, re.IGNORECASE):
                        findings.append({
                            "category": category,
                            "line": code[:match.start()].count('\n') + 1,
                            "description": desc,
                            "match": match.group()[:60]
                        })
            return {"risk_count": len(findings), "findings": findings[:15]}
        return None

    def _handle_function_query(self, query: str, file_path: Path) -> Optional[dict]:
        """处理功能分析查询：提取指定文件中的函数列表及其参数信息"""
        from .semantic_analyzer import SemanticAnalyzer
        from .shared import identify_language
        target_rel = str(file_path.relative_to(self.project_root))
        resolved_path = self.project_root / target_rel if '/' in target_rel or '.' in target_rel else None
        if resolved_path and resolved_path.exists():
            code = resolved_path.read_text(encoding='utf-8', errors='ignore')
            sa = SemanticAnalyzer(str(self.project_root))
            funcs = sa._extract_functions_fallback(code, identify_language(resolved_path, str(self.project_root)), resolved_path) if hasattr(sa, '_extract_functions_fallback') else []
            return {
                "file": str(resolved_path),
                "function_count": len(funcs),
                "functions": [{"name": f.name, "line": f.start_line, "params": f.params} for f in funcs[:10]]
            }
        return None

    def _handle_explain_query(self, query: str, file_path: Path) -> Optional[dict]:
        """处理代码解释查询：提取指定文件中的函数信息以辅助代码解释"""
        from .semantic_analyzer import SemanticAnalyzer
        from .shared import identify_language
        target_rel = str(file_path.relative_to(self.project_root))
        resolved_path = self.project_root / target_rel if '/' in target_rel or '.' in target_rel else None
        if resolved_path and resolved_path.exists():
            code = resolved_path.read_text(encoding='utf-8', errors='ignore')
            sa = SemanticAnalyzer(str(self.project_root))
            funcs = sa._extract_functions_fallback(code, identify_language(resolved_path, str(self.project_root)), resolved_path) if hasattr(sa, '_extract_functions_fallback') else []
            return {
                "file": str(resolved_path),
                "function_count": len(funcs),
                "functions": [{"name": f.name, "line": f.start_line, "params": f.params} for f in funcs[:10]]
            }
        return None

    def generate_call_graph(self, function_name: str) -> str:
        """
        生成函数调用关系 Mermaid 图

        参数：
            function_name: 目标函数名

        返回：
            Mermaid graph 字符串
        """
        lines = ["graph TD"]
        lines.append(f'    F["{function_name}()"]')

        # 搜索调用关系
        callers = []
        callees = []

        for f in self.project_root.rglob("*.py"):
            try:
                content = f.read_text(encoding="utf-8")
                if function_name in content:
                    rel = str(f.relative_to(self.project_root))
                    callers.append(rel)
            except Exception:
                logging.getLogger(__name__).warning(f"Failed to read {f} for call graph generation")
                continue

        for i, caller in enumerate(callers[:5]):
            lines.append(f'    C{i}["{caller}"]')
            lines.append(f"    C{i} --> F")

        return "\n".join(lines)


import re


# ============================================================
# 入口函数
# ============================================================

def explore_code(project_root: str, query: str,
                  semantic=None, dependency=None,
                  quality=None, risk=None) -> QueryResponse:
    """
    模块 7 入口函数

    参数：
        project_root: 项目根目录
        query: 用户的自然语言查询
        semantic: 语义分析器实例（可选）
        dependency: 依赖分析器实例（可选）
        quality: 质量评估器实例（可选）
        risk: 风险顾问实例（可选）

    返回：
        查询响应对象
    """
    explorer = InteractiveExplorer(
        project_root, semantic, dependency, quality, risk
    )
    return explorer.process_query(query)