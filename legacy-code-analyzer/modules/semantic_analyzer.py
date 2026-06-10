"""
模块 2：语义解析与设计意图推断 (Semantic Analyzer)

基于 AST 深度拆解代码逻辑，结合变量命名、注释语义与常见设计模式，
推断原开发者的设计思路与核心决策。

关键依赖：
- ast (Python 内置): Python AST 解析
- tree-sitter: 通用多语言 AST 解析 (Java, JavaScript, C++)
- re: 正则表达式辅助分析
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple, Any
from pathlib import Path

from .shared import Language


class RiskLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DesignPattern(Enum):
    SINGLETON = "singleton"
    FACTORY = "factory"
    OBSERVER = "observer"
    STRATEGY = "strategy"
    DECORATOR = "decorator"
    CHAIN_OF_RESPONSIBILITY = "chain_of_responsibility"
    ADAPTER = "adapter"
    PROXY = "proxy"
    TEMPLATE_METHOD = "template_method"
    BUILDER = "builder"
    MVC = "mvc"
    REPOSITORY = "repository"


@dataclass
class ControlFlowNode:
    type: str
    line: int
    condition: Optional[str] = None
    body_start: int = 0
    body_end: int = 0
    children: List["ControlFlowNode"] = field(default_factory=list)


@dataclass
class DataFlowEdge:
    source_var: str
    source_line: int
    target_var: str
    target_line: int
    dependency_type: str


@dataclass
class FunctionAnalysis:
    name: str
    file_path: str
    start_line: int
    end_line: int
    params: List[str]
    return_type: Optional[str]
    control_flow: List[ControlFlowNode] = field(default_factory=list)
    data_flow: List[DataFlowEdge] = field(default_factory=list)
    cyclomatic_complexity: int = 0
    design_patterns: List[DesignPattern] = field(default_factory=list)
    temp_solutions: List[Dict] = field(default_factory=list)


@dataclass
class ModuleSemanticAnalysis:
    module_name: str
    original_intent: str
    core_logic_description: str
    entry_functions: List[FunctionAnalysis]
    error_handling_summary: str
    dependency_rationale: Dict[str, str]
    temp_solutions: List[Dict]
    design_patterns: List[DesignPattern]
    inferred_constraints: List[str]


class SemanticAnalyzer:
    """
    语义解析器 - 模块 2 核心类

    工作流：
    1. parse_file()            → 读取并解析源码
    2. analyze_control_flow()  → 分析控制流
    3. analyze_data_flow()     → 分析数据流
    4. detect_design_patterns() → 识别设计模式
    5. infer_design_intent()   → 推断设计意图
    6. detect_temp_solutions() → 检测临时方案
    """

    # 设计模式特征检测规则
    DESIGN_PATTERN_RULES = {
        DesignPattern.SINGLETON: {
            "keywords": ["getInstance", "get_instance", "instance", "_instance"],
            "patterns": [r"static\s+\w+\s+\*\s*instance", r"__new__", r"private\s+constructor"],
        },
        DesignPattern.FACTORY: {
            "keywords": ["factory", "create", "build", "make"],
            "patterns": [r"def\s+create_\w+", r"class\s+\w+Factory", r"static\s+\w+\s+create"],
        },
        DesignPattern.OBSERVER: {
            "keywords": ["observer", "listener", "subscribe", "notify", "emit", "on_"],
            "patterns": [r"addObserver", r"addListener", r"\.subscribe\(", r"\.on\("],
        },
        DesignPattern.STRATEGY: {
            "keywords": ["strategy", "algorithm"],
            "patterns": [r"interface\s+\w+Strategy", r"class\s+\w+Strategy"],
        },
        DesignPattern.DECORATOR: {
            "keywords": ["decorator", "wrapper", "wrap"],
            "patterns": [r"@\w+", r"class\s+\w+Decorator", r"class\s+\w+Wrapper"],
        },
        DesignPattern.REPOSITORY: {
            "keywords": ["repository", "dao", "data_access"],
            "patterns": [r"class\s+\w+Repository", r"class\s+\w+DAO", r"interface\s+\w+Repository"],
        },
        DesignPattern.MVC: {
            "keywords": ["controller", "model", "view"],
            "patterns": [r"@Controller", r"@RestController", r"class\s+\w+Controller"],
        },
    }

    # 临时方案检测规则
    TEMP_SOLUTION_PATTERNS = {
        "硬编码": [r'(?:TIMEOUT|MAX_RETRIES|API_KEY|SECRET)\s*=\s*["\']?\w+["\']?'],
        "TODO标记": [r'TODO|FIXME|HACK|XXX|TEMP|WORKAROUND'],
        "紧急修复": [r'hotfix|quick.?fix|patch|workaround|bypass'],
        "注释代码": [r'^\s*#.*\b(?:def |class |function )', r'^\s*//.*\b(?:function |class )'],
        "魔法数字": [r'(?<![\w.])(?!0\b|1\b)\d{2,}(?![\w.])'],
        "过深嵌套": [],  # 由控制流分析计算
        "过长函数": [],  # 由行数统计计算
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analyses: Dict[str, ModuleSemanticAnalysis] = {}

    def parse_file_python(self, file_path: Path) -> ast.AST:
        """使用 Python 内置 ast 模块解析 Python 文件"""
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))

    def parse_file_generic(self, file_path: Path, language: str) -> Dict:
        """
        使用 tree-sitter 解析非 Python 文件

        依赖：
            pip install tree-sitter tree-sitter-java tree-sitter-javascript tree-sitter-cpp

        参数：
            file_path: 文件路径
            language: 编程语言

        返回：
            简化的 AST 字典表示
        """
        try:
            from tree_sitter import Language, Parser

            # 语言库映射
            language_map = {
                "java": "tree-sitter-java.so",
                "javascript": "tree-sitter-javascript.so",
                "typescript": "tree-sitter-typescript.so",
                "cpp": "tree-sitter-cpp.so",
                "c": "tree-sitter-c.so",
            }

            lib_path = language_map.get(language)
            if not lib_path:
                raise ValueError(f"Unsupported language: {language}")

            parser = Parser()
            parser.set_language(Language(lib_path, language))

            content = file_path.read_bytes()
            tree = parser.parse(content)

            return self._tree_sitter_to_dict(tree.root_node)
        except ImportError:
            # tree-sitter 未安装时的回退方案
            return {"error": "tree-sitter not installed", "file": str(file_path)}

    def _tree_sitter_to_dict(self, node) -> Dict:
        """将 tree-sitter 节点转换为字典"""
        result = {
            "type": node.type,
            "start_point": node.start_point,
            "end_point": node.end_point,
            "children": [],
        }
        for child in node.children:
            result["children"].append(self._tree_sitter_to_dict(child))
        return result

    def analyze_control_flow_python(self, func_node: ast.FunctionDef) -> List[ControlFlowNode]:
        """
        分析 Python 函数的控制流

        识别：
        - 条件分支（if/elif/else）
        - 循环（for/while）
        - 异常处理（try/except/finally）
        - 跳转（return/break/continue）
        - 推导式（list/dict/set comprehension）

        参数：
            func_node: AST 函数定义节点

        返回：
            控制流节点列表
        """
        flow_nodes = []
        visitor = _ControlFlowVisitor()
        visitor.visit(func_node)
        return visitor.nodes

    def analyze_data_flow_python(self, func_node: ast.FunctionDef) -> List[DataFlowEdge]:
        """
        分析 Python 函数的数据流

        追踪：
        - 变量定义位置
        - 变量赋值和修改
        - 变量使用位置
        - 函数参数传递

        返回：
            数据流边列表
        """
        edges = []
        visitor = _DataFlowVisitor()
        visitor.visit(func_node)
        return visitor.edges

    def detect_design_patterns(self, code: str, file_path: str) -> List[DesignPattern]:
        """
        检测代码中使用的设计模式

        通过关键词匹配和结构特征识别常见设计模式

        参数：
            code: 源代码内容
            file_path: 文件路径

        返回：
            检测到的设计模式列表
        """
        detected = []
        for pattern, rules in self.DESIGN_PATTERN_RULES.items():
            score = 0
            for kw in rules["keywords"]:
                if kw.lower() in code.lower():
                    score += 1
            for pat in rules["patterns"]:
                if re.search(pat, code, re.IGNORECASE):
                    score += 2
            if score >= 2:
                detected.append(pattern)
        return detected

    def detect_temp_solutions(self, code: str, func_analysis: FunctionAnalysis) -> List[Dict]:
        """
        检测代码中的临时方案和紧急修复痕迹

        检测类型：
        - 硬编码常量
        - TODO/FIXME 标记
        - 紧急修复（绕过逻辑）
        - 注释掉的代码
        - 魔法数字
        - 过深嵌套（CC > 10）
        - 过长函数（> 50 行）

        返回：
            临时方案列表，每个包含类型、位置、内容、风险等级
        """
        solutions = []

        for sol_type, patterns in self.TEMP_SOLUTION_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, code, re.MULTILINE):
                    line_num = code[:match.start()].count("\n") + 1
                    risk = RiskLevel.LOW
                    if sol_type in ("紧急修复", "硬编码"):
                        risk = RiskLevel.HIGH
                    elif sol_type in ("魔法数字", "过深嵌套"):
                        risk = RiskLevel.MEDIUM

                    solutions.append({
                        "type": sol_type,
                        "line": line_num,
                        "content": match.group().strip()[:80],
                        "risk": risk.value,
                    })

        # 检查函数复杂度
        if func_analysis.cyclomatic_complexity > 10:
            solutions.append({
                "type": "过深嵌套",
                "line": func_analysis.start_line,
                "content": f"圈复杂度={func_analysis.cyclomatic_complexity}",
                "risk": RiskLevel.MEDIUM.value,
            })

        # 检查函数长度
        func_len = func_analysis.end_line - func_analysis.start_line + 1
        if func_len > 50:
            solutions.append({
                "type": "过长函数",
                "line": func_analysis.start_line,
                "content": f"函数长度={func_len}行",
                "risk": RiskLevel.MEDIUM.value,
            })

        return solutions

    def _extract_functions_fallback(self, code: str, language, file_path: Path) -> List[FunctionAnalysis]:
        if isinstance(language, Language):
            lang_str = language.value
        else:
            lang_str = str(language)

        functions = []

        if lang_str == "java":
            func_pattern = re.compile(
                r'(public|private|protected)\s+(static\s+)?(\w+(?:<.*?>)?)\s+(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(4)
                start_line = code[:match.start()].count('\n') + 1
                params_str = match.group(5)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                return_type = match.group(3)
                remaining = code[match.end():]
                end_line = start_line + min(remaining.count('\n'), 50)
                functions.append(FunctionAnalysis(
                    name=func_name, file_path=str(file_path),
                    start_line=start_line, end_line=end_line,
                    params=params, return_type=return_type,
                ))

        elif lang_str == "csharp":
            func_pattern = re.compile(
                r'(public|private|protected|internal)\s+(static\s+)?(async\s+)?(\w+(?:<.*?>)?)\s+(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(5)
                start_line = code[:match.start()].count('\n') + 1
                params_str = match.group(6)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                return_type = match.group(4)
                remaining = code[match.end():]
                end_line = start_line + min(remaining.count('\n'), 50)
                functions.append(FunctionAnalysis(
                    name=func_name, file_path=str(file_path),
                    start_line=start_line, end_line=end_line,
                    params=params, return_type=return_type,
                ))

        elif lang_str in ("javascript", "typescript"):
            func_pattern = re.compile(
                r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(1)
                start_line = code[:match.start()].count('\n') + 1
                params_str = match.group(2)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                remaining = code[match.end():]
                end_line = start_line + min(remaining.count('\n'), 50)
                functions.append(FunctionAnalysis(
                    name=func_name, file_path=str(file_path),
                    start_line=start_line, end_line=end_line,
                    params=params, return_type=None,
                ))

            arrow_pattern = re.compile(
                r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
                re.MULTILINE
            )
            for match in arrow_pattern.finditer(code):
                func_name = match.group(1)
                start_line = code[:match.start()].count('\n') + 1
                params_str = match.group(2)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                remaining = code[match.end():]
                end_line = start_line + min(remaining.count('\n'), 50)
                functions.append(FunctionAnalysis(
                    name=func_name, file_path=str(file_path),
                    start_line=start_line, end_line=end_line,
                    params=params, return_type=None,
                ))

        elif lang_str in ("cpp", "c"):
            class_pattern = re.compile(
                r'(\w+(?:::\w+)?)\s+(\w+)::(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in class_pattern.finditer(code):
                func_name = f"{match.group(2)}::{match.group(3)}"
                start_line = code[:match.start()].count('\n') + 1
                params_str = match.group(4)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                remaining = code[match.end():]
                end_line = start_line + min(remaining.count('\n'), 50)
                functions.append(FunctionAnalysis(
                    name=func_name, file_path=str(file_path),
                    start_line=start_line, end_line=end_line,
                    params=params, return_type=match.group(1),
                ))

            free_pattern = re.compile(
                r'(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{',
                re.MULTILINE
            )
            for match in free_pattern.finditer(code):
                func_name = match.group(2)
                start_line = code[:match.start()].count('\n') + 1
                params_str = match.group(3)
                params = [p.strip() for p in params_str.split(',') if p.strip()]
                remaining = code[match.end():]
                end_line = start_line + min(remaining.count('\n'), 50)
                functions.append(FunctionAnalysis(
                    name=func_name, file_path=str(file_path),
                    start_line=start_line, end_line=end_line,
                    params=params, return_type=match.group(1),
                ))

        return functions

    def infer_design_intent(self, module_name: str, functions: List[FunctionAnalysis],
                            code: str, imports: List[str]) -> ModuleSemanticAnalysis:
        """
        推断模块的设计意图

        综合以下信息进行推断：
        1. 模块名称和目录位置
        2. 函数命名模式
        3. 使用的设计模式
        4. 依赖关系
        5. 注释和文档字符串
        6. 代码组织方式

        参数：
            module_name: 模块名称
            functions: 函数分析列表
            code: 完整源代码
            imports: import 列表

        返回：
            模块语义分析结果
        """
        # 推断功能初衷（基于模块名和函数命名模式）
        intent = self._infer_original_intent(module_name, functions)

        # 分析核心逻辑
        core_logic = self._describe_core_logic(functions)

        # 分析异常处理
        error_handling = self._analyze_error_handling(code)

        # 推断依赖选择原因
        dep_rationale = self._infer_dependency_rationale(imports, module_name)

        # 汇总设计模式
        all_patterns = []
        for f in functions:
            all_patterns.extend(f.design_patterns)

        # 汇总临时方案
        all_temp = []
        for f in functions:
            all_temp.extend(f.temp_solutions)

        # 推断约束
        constraints = self._infer_constraints(code, functions)

        return ModuleSemanticAnalysis(
            module_name=module_name,
            original_intent=intent,
            core_logic_description=core_logic,
            entry_functions=functions,
            error_handling_summary=error_handling,
            dependency_rationale=dep_rationale,
            temp_solutions=all_temp,
            design_patterns=list(set(all_patterns)),
            inferred_constraints=constraints,
        )

    def _infer_original_intent(self, module_name: str,
                                functions: List[FunctionAnalysis]) -> str:
        """基于函数名和模块名推断设计意图"""
        intent_parts = []

        # 从模块名推断
        module_intent_map = {
            "auth": "负责用户认证与授权管理",
            "api": "对外提供 RESTful API 接口",
            "service": "封装核心业务逻辑，作为控制器与数据层之间的桥梁",
            "model": "定义数据结构和数据库映射关系",
            "utils": "提供跨模块的通用工具函数",
            "middleware": "在请求/响应管道中执行横切关注点处理",
            "config": "集中管理系统配置参数和环境变量",
            "handler": "处理特定类型的事件或请求",
            "controller": "接收 HTTP 请求并协调服务层响应",
            "repository": "封装数据访问逻辑，隔离业务层与持久化层",
        }
        if module_name.lower() in module_intent_map:
            intent_parts.append(module_intent_map[module_name.lower()])

        # 从函数命名模式推断
        func_names = [f.name for f in functions]
        patterns = {
            "validate": "包含输入校验逻辑",
            "parse": "负责数据解析与格式转换",
            "convert": "处理不同格式间的数据转换",
            "calculate": "包含数值计算或业务规则运算",
            "fetch": "从外部数据源获取数据",
            "send": "向外部系统发送数据或通知",
            "build": "采用 Builder 模式构造复杂对象",
            "process": "执行多步骤数据处理流程",
            "handle": "集中处理特定类型的事件或异常",
            "resolve": "实现依赖解析或冲突处理",
        }
        for name in func_names:
            for kw, desc in patterns.items():
                if kw in name.lower():
                    intent_parts.append(desc)
                    break

        if not intent_parts:
            intent_parts.append(f"该模块提供 {module_name} 相关的功能实现")

        return "；".join(intent_parts[:3])

    def _describe_core_logic(self, functions: List[FunctionAnalysis]) -> str:
        """描述核心逻辑实现方式"""
        descriptions = []
        for func in functions:
            if func.cyclomatic_complexity > 5:
                complexity_note = f"（圈复杂度={func.cyclomatic_complexity}，逻辑较复杂）"
            else:
                complexity_note = ""

            desc = (f"函数 `{func.name}` (L{func.start_line}-L{func.end_line}) "
                    f"接收参数 {func.params}{complexity_note}")
            descriptions.append(desc)

        if not descriptions:
            return "未检测到显著的核心逻辑函数"
        return "\n".join(descriptions)

    def _analyze_error_handling(self, code: str) -> str:
        """分析异常处理思路"""
        has_try = "try" in code or "except" in code or "catch" in code
        has_finally = "finally" in code
        has_empty_catch = bool(re.search(r"except\s*:", code) or
                               re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", code))
        has_logging = bool(re.search(r"(log|logger|logging)\.(error|warn|exception)", code))

        parts = []
        if has_try:
            parts.append("✅ 包含异常捕获机制")
        else:
            parts.append("❌ 未发现异常捕获机制")

        if has_finally:
            parts.append("✅ 使用 finally 确保资源释放")
        if has_empty_catch:
            parts.append("⚠️ 存在空异常捕获块（可能吞掉重要错误）")
        if has_logging:
            parts.append("✅ 异常处理中包含日志记录")
        else:
            parts.append("⚠️ 异常处理中缺少日志记录")

        return "；".join(parts)

    def _infer_dependency_rationale(self, imports: List[str],
                                     module_name: str) -> Dict[str, str]:
        """推断依赖选择的原因"""
        rationale = {}
        common_rationales = {
            "os": "需要操作系统级别的功能（文件路径、环境变量）",
            "sys": "需要 Python 运行时环境交互",
            "json": "需要 JSON 数据序列化/反序列化",
            "re": "需要正则表达式进行文本模式匹配",
            "logging": "需要标准化的日志记录能力",
            "datetime": "需要日期时间处理功能",
            "collections": "需要高级数据结构（defaultdict, Counter 等）",
            "typing": "需要类型注解支持以提高代码可读性",
            "flask": "选择了轻量级 Web 框架以降低复杂度",
            "django": "需要全栈 Web 框架提供完整的开箱即用功能",
            "fastapi": "选择了高性能异步 Web 框架以支持并发",
            "sqlalchemy": "需要 ORM 层以简化数据库操作",
            "pytest": "选择了功能丰富的测试框架",
            "requests": "需要 HTTP 客户端进行外部 API 调用",
            "numpy": "需要高效的数值计算能力",
            "pandas": "需要结构化数据处理能力",
            "react": "选择了组件化的前端框架",
            "spring": "需要企业级 Java 应用框架",
        }
        for imp in imports:
            base = imp.split(".")[0]
            if base in common_rationales:
                rationale[imp] = common_rationales[base]
            else:
                rationale[imp] = f"推断为 {module_name} 模块所需的{base}库"

        return rationale

    def _infer_constraints(self, code: str,
                            functions: List[FunctionAnalysis]) -> List[str]:
        """推断设计约束"""
        constraints = []

        # 检查同步/异步约束
        if "async def" in code or "async " in code:
            constraints.append("模块设计为异步模式，调用方需在异步上下文中使用")
        else:
            constraints.append("模块设计为同步模式，不适合在高并发场景直接使用")

        # 检查状态管理
        if re.search(r"(global |self\.\w+ =)", code):
            constraints.append("模块包含可变状态，非线程安全，需注意并发访问")

        # 检查硬编码
        if re.search(r'(?:URL|PATH|HOST|PORT)\s*=\s*["\']', code):
            constraints.append("存在硬编码的外部资源地址，部署时需要环境特定的配置")

        # 检查文件依赖
        if re.search(r'(?:open|read|write)\(["\']', code):
            constraints.append("依赖本地文件系统，在容器化环境中需确保文件路径可访问")

        return constraints


class _ControlFlowVisitor(ast.NodeVisitor):
    """AST 遍历器 - 提取控制流节点"""

    def __init__(self):
        self.nodes: List[ControlFlowNode] = []

    def visit_If(self, node: ast.If):
        condition = ast.unparse(node.test) if hasattr(ast, "unparse") else "condition"
        cf_node = ControlFlowNode(
            type="if",
            line=node.lineno,
            condition=condition,
        )
        self.nodes.append(cf_node)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        target = ast.unparse(node.target) if hasattr(ast, "unparse") else "iterator"
        cf_node = ControlFlowNode(
            type="for",
            line=node.lineno,
            condition=f"for {target} in iterable",
        )
        self.nodes.append(cf_node)
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        condition = ast.unparse(node.test) if hasattr(ast, "unparse") else "condition"
        cf_node = ControlFlowNode(
            type="while",
            line=node.lineno,
            condition=condition,
        )
        self.nodes.append(cf_node)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        cf_node = ControlFlowNode(
            type="try",
            line=node.lineno,
            condition=f"handles {len(node.handlers)} exception(s)",
        )
        self.nodes.append(cf_node)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        cf_node = ControlFlowNode(
            type="return",
            line=node.lineno,
            condition="exit_point",
        )
        self.nodes.append(cf_node)
        self.generic_visit(node)


class _DataFlowVisitor(ast.NodeVisitor):
    """AST 遍历器 - 提取数据流"""

    def __init__(self):
        self.edges: List[DataFlowEdge] = []
        self._assignments: Dict[str, int] = {}

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                self._assignments[var_name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load) and node.id in self._assignments:
            edge = DataFlowEdge(
                source_var=node.id,
                source_line=self._assignments[node.id],
                target_var=node.id,
                target_line=node.lineno,
                dependency_type="RAW",
            )
            self.edges.append(edge)
        self.generic_visit(node)


# ============================================================
# 入口函数
# ============================================================

def analyze_semantics(project_root: str, target_files: List[str] = None) -> Dict:
    """
    模块 2 入口函数

    参数：
        project_root: 项目根目录
        target_files: 可选，指定要分析的文件列表

    返回：
        语义分析结果字典
    """
    analyzer = SemanticAnalyzer(project_root)
    results = {}

    # 确定要分析的文件
    root = Path(project_root)
    if target_files:
        files = [root / f for f in target_files]
    else:
        files = []
        for ext in (".py", ".java", ".js", ".ts", ".cs", ".cpp", ".h", ".c"):
            files.extend(root.rglob(f"*{ext}"))

    for file_path in files:
        if not file_path.exists():
            continue

        try:
            code = file_path.read_text(encoding="utf-8")
            module_name = file_path.parent.name

            if file_path.suffix == ".py":
                tree = analyzer.parse_file_python(file_path)

                functions = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func = FunctionAnalysis(
                            name=node.name,
                            file_path=str(file_path),
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            params=[arg.arg for arg in node.args.args],
                            return_type=None,
                        )
                        func.control_flow = analyzer.analyze_control_flow_python(node)
                        func.data_flow = analyzer.analyze_data_flow_python(node)
                        func.cyclomatic_complexity = _calculate_cc(node)
                        func.design_patterns = analyzer.detect_design_patterns(code, str(file_path))
                        func.temp_solutions = analyzer.detect_temp_solutions(code, func)
                        functions.append(func)

                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                analysis = analyzer.infer_design_intent(
                    module_name, functions, code, imports
                )
                results[str(file_path)] = analysis
                analyzer.analyses[module_name] = analysis

            elif file_path.suffix in (".java", ".js", ".ts", ".cpp", ".h", ".c"):
                lang_map = {
                    ".java": "java", ".js": "javascript", ".ts": "typescript",
                    ".cpp": "cpp", ".h": "cpp", ".c": "c"
                }
                lang = lang_map[file_path.suffix]

                result = analyzer.parse_file_generic(file_path, lang)
                functions = analyzer._extract_functions_fallback(code, lang, file_path)

                for func in functions:
                    func.design_patterns = analyzer.detect_design_patterns(code, str(file_path))
                    func.temp_solutions = analyzer.detect_temp_solutions(code, func)

                analysis = analyzer.infer_design_intent(
                    module_name, functions, code, []
                )
                results[str(file_path)] = analysis
                analyzer.analyses[module_name] = analysis

        except SyntaxError as e:
            results[str(file_path)] = {"error": f"Syntax error: {e}"}
        except (IOError, UnicodeDecodeError, MemoryError) as e:
            results[str(file_path)] = {"error": f"File processing error: {e}"}
        except Exception as e:
            # 最外层兜底：确保单个文件的分析失败不会阻塞整个批处理
            logging.getLogger(__name__).warning(f"Unexpected error analyzing {file_path}: {e}")
            results[str(file_path)] = {"error": str(e)}

    return results


def _calculate_cc(func_node: ast.FunctionDef) -> int:
    """计算函数的圈复杂度"""
    cc = 1  # 基础复杂度
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            cc += len(node.values) - 1
        elif isinstance(node, ast.Match):
            cc += len(node.cases)
    return cc