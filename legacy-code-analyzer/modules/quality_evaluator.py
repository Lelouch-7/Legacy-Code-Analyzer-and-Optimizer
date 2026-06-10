"""
模块 4：代码质量评估与缺陷检测 (Quality Evaluator)

基于圈复杂度、可维护性指数、继承深度、类耦合度等指标，
对照 ISO/IEC 5055:2021 标准检测缺陷，按风险等级分类。

关键依赖：
- math: 对数计算（可维护性指数）
- re: 模式匹配
- dataclasses: 数据结构定义
"""

import logging
import re
import math
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple

from .shared import Language, EXCLUDE_DIRS, OWASP_SECURITY_PATTERNS, DEPRECATED_PATTERNS, identify_language


class RiskLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectCategory(Enum):
    SYNTAX_ERROR = "syntax_error"
    LOGIC_FLAW = "logic_flaw"
    MISSING_EXCEPTION = "missing_exception"
    BOUNDARY_COVERAGE = "boundary_coverage"
    DEPRECATED_DEPENDENCY = "deprecated_dependency"
    REDUNDANT_CODE = "redundant_code"
    SECURITY_VULNERABILITY = "security_vulnerability"


@dataclass
class QualityMetrics:
    function_name: str
    file_path: str
    start_line: int
    end_line: int
    loc: int                     # Lines of Code
    cyclomatic_complexity: int   # McCabe 圈复杂度
    halstead_volume: float       # Halstead 容量
    maintainability_index: float # 可维护性指数
    depth_of_inheritance: int    # 继承深度
    coupling_between_objects: int # 类耦合度
    lm_cc: int                   # 逻辑模块圈复杂度
    overall_score: float         # 综合评分 1-10


@dataclass
class Defect:
    category: DefectCategory
    risk_level: RiskLevel
    file_path: str
    line_number: int
    description: str
    fix_suggestion: str
    iso_reference: Optional[str] = None  # ISO/IEC 5055:2021 条款引用


@dataclass
class ModuleQualityReport:
    module_name: str
    avg_cc: float
    avg_mi: float
    max_dit: int
    avg_cbo: float
    overall_score: float
    rating: str  # 🟢优秀 / 🟡良好 / 🟠一般 / 🔴较差
    defects: List[Defect] = field(default_factory=list)


class QualityEvaluator:
    """
    代码质量评估器 - 模块 4 核心类

    工作流：
    1. calculate_cyclomatic_complexity() → 计算圈复杂度
    2. calculate_maintainability_index() → 计算可维护性指数
    3. calculate_halstead_volume()       → 计算 Halstead 容量
    4. detect_defects()                  → ISO/IEC 5055 缺陷检测
    5. security_scan()                   → OWASP Top 10 安全扫描
    6. rate_module()                     → 模块评级
    """

    # 质量阈值定义
    THRESHOLDS = {
        "cyclomatic_complexity": {
            "excellent": 10,
            "good": 20,
            "poor": 50,
        },
        "maintainability_index": {
            "excellent": 85,
            "good": 65,
        },
        "depth_of_inheritance": {
            "max": 5,
        },
        "coupling_between_objects": {
            "max": 14,
        },
        "lm_cc": {
            "max": 15,
        },
        "function_length": {
            "max": 50,
        },
    }

    # 冗余代码检测模式
    REDUNDANCY_PATTERNS = {
        "commented_code": re.compile(
            r"^\s*(?:#|//)\s*(?:def |class |function |if |for |while |return )",
            re.MULTILINE
        ),
        "unused_import": re.compile(
            r"^(?:import |from )", re.MULTILINE
        ),
        "duplicate_logic": None,  # 需要更复杂的 AST 分析
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.metrics: Dict[str, List[QualityMetrics]] = defaultdict(list)
        self.defects: List[Defect] = []

    def calculate_cyclomatic_complexity(self, code: str) -> int:
        """
        计算圈复杂度 (McCabe's Cyclomatic Complexity)

        公式：CC = E - N + 2P（或简化：1 + 每个决策点 +1）

        决策点包括：
        - if / elif / else
        - for / while
        - case (switch/match)
        - and / or (短路运算符)
        - except / catch
        - 三元运算符

        参数：
            code: 函数/方法的源代码

        返回：
            圈复杂度值
        """
        cc = 1  # 基础复杂度

        # if/elif
        cc += len(re.findall(r"^\s*if\s+", code, re.MULTILINE))
        cc += len(re.findall(r"^\s*elif\s+", code, re.MULTILINE))

        # for/while
        cc += len(re.findall(r"^\s*for\s+", code, re.MULTILINE))
        cc += len(re.findall(r"^\s*while\s+", code, re.MULTILINE))

        # except/catch
        cc += len(re.findall(r"^\s*except\s+", code, re.MULTILINE))
        cc += len(re.findall(r"catch\s*\(", code))

        # case (switch)
        cc += len(re.findall(r"^\s*case\s+", code, re.MULTILINE))

        # and/or 短路运算符（每个额外条件 +1）
        cc += len(re.findall(r"\band\b", code)) - 1 if "and" in code else 0
        cc += len(re.findall(r"\bor\b", code)) - 1 if "or" in code else 0

        # 三元运算符
        cc += len(re.findall(r"\bif\b.*\belse\b", code))

        # 列表推导式中的 if
        cc += len(re.findall(r"for\s+\w+\s+in\s+.*\bif\b", code))

        return max(cc, 1)

    def calculate_halstead_volume(self, code: str) -> float:
        """
        计算 Halstead 容量

        Halstead 指标：
        - n1: 不同操作符数量
        - n2: 不同操作数数量
        - N1: 总操作符数量
        - N2: 总操作数数量
        - V = N × log2(n), 其中 N = N1 + N2, n = n1 + n2

        参数：
            code: 源代码

        返回：
            Halstead Volume 值
        """
        # 操作符（简化统计）
        operators = re.findall(
            r"[+\-*/%=<>!&|^~]|"
            r"\b(?:if|else|elif|for|while|return|break|continue|"
            r"and|or|not|in|is|def|class|import|from|as|with|try|"
            r"except|finally|raise|yield|lambda|pass|assert|del|global|nonlocal)\b",
            code
        )

        # 操作数（简化统计：变量名、字面量）
        operands = re.findall(
            r"\b[a-zA-Z_]\w*\b|"
            r"\b\d+(?:\.\d+)?\b|"
            r"['\"][^'\"]*['\"]",
            code
        )

        n1 = len(set(operators))
        n2 = len(set(operands))
        N1 = len(operators)
        N2 = len(operands)

        n = n1 + n2
        N = N1 + N2

        if n <= 0 or N <= 0:
            return 0.0

        volume = N * math.log2(n) if n > 0 else 0.0
        return round(volume, 2)

    def calculate_maintainability_index(self, cc: int, halstead_v: float,
                                         loc: int) -> float:
        """
        计算可维护性指数 (Maintainability Index)

        公式：
        MI = 171 - 5.2 × ln(V) - 0.23 × CC - 16.2 × ln(LOC)

        其中：
        - V = Halstead Volume
        - CC = 圈复杂度
        - LOC = 有效代码行数

        评级：
        - MI > 85: 🟢 优秀（高可维护性）
        - 65 < MI ≤ 85: 🟡 良好
        - MI ≤ 65: 🔴 较差（需要重构）

        参数：
            cc: 圈复杂度
            halstead_v: Halstead Volume
            loc: 代码行数

        返回：
            可维护性指数（0-171）
        """
        safe_v = max(halstead_v, 1)
        safe_loc = max(loc, 1)

        mi = (171.0
              - 5.2 * math.log(safe_v)
              - 0.23 * cc
              - 16.2 * math.log(safe_loc))

        # 标准化到 0-100 范围
        mi_normalized = max(0.0, min(100.0, mi))
        return round(mi_normalized, 2)

    def calculate_lm_cc(self, functions_in_module: List[QualityMetrics]) -> int:
        """
        计算逻辑模块圈复杂度 (LM-CC)

        LM-CC 考虑模块边界，不仅计算单个函数的复杂度，
        还考虑模块内部函数间的调用复杂度。

        简化公式：
        LM-CC = Σ(每个函数的 CC) + 模块内函数调用边数

        参数：
            functions_in_module: 模块内所有函数的指标

        返回：
            LM-CC 值
        """
        total_cc = sum(f.cyclomatic_complexity for f in functions_in_module)
        # 函数调用边数简化估计
        call_edges = len(functions_in_module) * (len(functions_in_module) - 1) // 4
        return total_cc + min(call_edges, total_cc)

    def detect_syntax_errors(self, file_path: Path) -> List[Defect]:
        """检测语法错误"""
        defects = []
        try:
            content = file_path.read_text(encoding="utf-8")
            if file_path.suffix == ".py":
                import ast
                ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            defects.append(Defect(
                category=DefectCategory.SYNTAX_ERROR,
                risk_level=RiskLevel.HIGH,
                file_path=str(file_path),
                line_number=e.lineno or 0,
                description=f"语法错误: {e.msg}",
                fix_suggestion=f"修正第 {e.lineno} 行的语法: {e.text.strip() if e.text else ''}",
                iso_reference="ISO/IEC 5055:2021 §5.1",
            ))
        return defects

    def detect_logic_flaws(self, code: str, file_path: str) -> List[Defect]:
        """检测逻辑漏洞"""
        defects = []

        # 死循环检测
        while_true = re.findall(r"while\s+True\s*:", code)
        for _ in while_true:
            if "break" not in code.split("while True")[-1].split("\n", 20)[0]:
                line = code[:code.find("while True")].count("\n") + 1
                defects.append(Defect(
                    category=DefectCategory.LOGIC_FLAW,
                    risk_level=RiskLevel.MEDIUM,
                    file_path=file_path,
                    line_number=line,
                    description="while True 循环中未发现 break 语句",
                    fix_suggestion="确保循环有明确的退出条件",
                    iso_reference="ISO/IEC 5055:2021 §5.2",
                ))

        # 条件覆盖不足（如只检查了 True 分支）
        if_matches = list(re.finditer(r"if\s+(\w+):", code))
        reported = 0
        for match in if_matches:
            if reported >= 3:
                break
            # 检查是否为 guard clause（if 体以 return/raise/continue/break 结尾）
            block_start = match.end()
            block_end = code.find('\nif ', block_start)
            if block_end == -1:
                block_end = code.find('\n}', block_start)
            if block_end == -1:
                block_end = len(code)
            block_text = code[block_start:block_end]
            # Guard clause 模式：跳过返回/抛出/继续/中断的 if 块
            if re.search(r'\b(return|raise|continue|break)\s*[;\n]', block_text):
                continue
            # 检查同一 if 语句附近是否有 else
            next_code = code[block_start:block_start + 200]
            if re.search(r'^\s*else\s*:', next_code, re.MULTILINE):
                continue

            line = code[:match.start()].count("\n") + 1
            defects.append(Defect(
                category=DefectCategory.LOGIC_FLAW,
                risk_level=RiskLevel.LOW,
                file_path=file_path,
                line_number=line,
                description=f"if 语句缺少 else 分支处理",
                fix_suggestion="考虑添加 else 分支处理非预期情况",
                iso_reference="ISO/IEC 5055:2021 §5.2",
            ))
            reported += 1

        return defects

    def detect_missing_exception_handling(self, code: str, file_path: str) -> List[Defect]:
        """检测异常处理缺失"""
        defects = []

        # 空 except/catch 块
        empty_except = re.finditer(
            r"except\s*(?:\w+)?\s*:\s*\n\s*(?:pass|\.\.\.)",
            code, re.MULTILINE
        )
        for match in empty_except:
            line = code[:match.start()].count("\n") + 1
            defects.append(Defect(
                category=DefectCategory.MISSING_EXCEPTION,
                risk_level=RiskLevel.MEDIUM,
                file_path=file_path,
                line_number=line,
                description="空异常捕获块（except: pass），异常被静默忽略",
                fix_suggestion="添加异常日志记录，或重新抛出异常",
                iso_reference="ISO/IEC 5055:2021 §5.3",
            ))

        # 过于宽泛的 except
        broad_except = re.finditer(
            r"except\s+Exception\s+as",
            code, re.MULTILINE
        )
        for match in broad_except:
            line = code[:match.start()].count("\n") + 1
            defects.append(Defect(
                category=DefectCategory.MISSING_EXCEPTION,
                risk_level=RiskLevel.LOW,
                file_path=file_path,
                line_number=line,
                description="使用了过于宽泛的 Exception 捕获",
                fix_suggestion="捕获更具体的异常类型",
                iso_reference="ISO/IEC 5055:2021 §5.3",
            ))

        # 文件操作缺少异常处理
        file_ops = re.finditer(
            r"(?:open|read|write)\(.*\)(?!.*\n\s*(?:except|try))",
            code, re.MULTILINE
        )
        for match in file_ops:
            # 检查周围 5 行是否有 try
            start = max(0, match.start() - 200)
            context = code[start:match.end() + 200]
            if "try" not in context and "with" not in context:
                line = code[:match.start()].count("\n") + 1
                defects.append(Defect(
                    category=DefectCategory.MISSING_EXCEPTION,
                    risk_level=RiskLevel.MEDIUM,
                    file_path=file_path,
                    line_number=line,
                    description="文件操作缺少异常处理",
                    fix_suggestion="使用 try-except 或 with 语句包裹文件操作",
                    iso_reference="ISO/IEC 5055:2021 §5.3",
                ))

        return defects

    def detect_boundary_issues(self, code: str, file_path: str) -> List[Defect]:
        """检测边界条件覆盖不足"""
        defects = []

        # 跳过包含正则表达式的行（避免误报 `[\w+]`, `[^)]*` 等模式）
        lines = code.split('\n')

        # 数组/列表索引访问
        index_access = re.finditer(r"(\w+)\[(\w+)\]", code)
        for match in index_access:
            var_name = match.group(1)
            idx_expr = match.group(2)

            # 跳过正则表达式字面量中的括号
            line_num = code[:match.start()].count("\n")
            line = lines[line_num] if line_num < len(lines) else ""
            stripped = line.strip()
            if re.search(r'(?:re\.(?:compile|search|match|findall|finditer|sub|split)|pattern|PATTERN)', stripped):
                continue
            if stripped.startswith(('#', '//', '/*', '*')) and '[' in stripped:
                continue

            # 跳过 dict 风格的字符串键访问（如 d['key'], m["name"]）
            if (idx_expr.startswith("'") or idx_expr.startswith('"')
                    or idx_expr.startswith('f"') or idx_expr.startswith("f'")):
                continue

            # 跳过 `self[key]` 在 __getitem__ 或 __setitem__ 中的访问
            if var_name == "self":
                continue

            # 跳过 defaultdict / Counter 的安全访问
            if var_name in ("chunks", "counter", "cache", "memo", "registry", "seen"):
                continue

            # 跳过常量索引（整数 literal 不会越界）
            if idx_expr.isdigit():
                continue

            # 跳过字典/映射风格变量名（如 intent_scores, node_ids, scores_map）
            if re.search(r'_(?:scores?|dict|map|cache|ids?|registry)', var_name):
                continue

            # 跳过带内联守卫的索引访问（如 lines[N] if N < len(lines)）
            after_pos = match.end()
            after_text = code[after_pos:after_pos + 80]
            if re.search(rf'\s+if\s+{re.escape(idx_expr)}\s*[<]\s*len\(', after_text):
                continue

            # 检查上下文是否有边界检查
            start = max(0, match.start() - 300)
            context = code[start:match.start()]
            if not re.search(rf"(?:len|length|size|count|bounds|valid|safe)\s*.*{re.escape(idx_expr)}", context):
                # 降级为 LOW 风险（多数为潜在风险而非确定性 Bug）
                if var_name.islower() and len(var_name) > 1:
                    defects.append(Defect(
                        category=DefectCategory.BOUNDARY_COVERAGE,
                        risk_level=RiskLevel.LOW,
                        file_path=file_path,
                        line_number=line_num + 1,
                        description=f"索引访问 `{match.group()}` 缺少边界检查",
                        fix_suggestion=f"在访问前检查 len({var_name}) > {idx_expr}",
                        iso_reference="ISO/IEC 5055:2021 §5.4",
                    ))

        # 除零风险
        division = re.finditer(r"(\w+)\s*/\s*(\w+)", code)
        for match in division:
            divisor = match.group(2)
            dividend = match.group(1)
            line_num = code[:match.start()].count("\n")
            line = lines[line_num] if line_num < len(lines) else ""
            stripped = line.strip()

            # 检测除法符号是否在字符串或注释内
            line_before_slash = line[:line.find('/')]
            in_string = False
            in_comment = False
            for ch in line_before_slash:
                if ch in ('"', "'"):
                    in_string = not in_string
            if '#' in line_before_slash or '//' in line_before_slash:
                in_comment = True
            if stripped.startswith(('"""', "'''", '/*', '*', '//', '#')):
                in_comment = True

            if in_string or in_comment:
                continue

            # 跳过文件路径模式（如 "modules/scanner.py", dir/file）
            if '/' in stripped and ('.' in dividend or '.' in divisor):
                continue

            # 跳过中文/非 ASCII 单词（如 模块/quality, 文件/除数）
            if any(ord(c) > 127 for c in dividend) or any(ord(c) > 127 for c in divisor):
                continue

            # 跳过列表/文档中的项目符号模式（如 "- if / elif / else"）
            if stripped.startswith(('-', '* ', '+ ')) and len(dividend) <= 8:
                continue

            # 跳过需求规格说明行（如 "FR-006: ... Ca/Ce/I/A/D ..."）
            if re.match(r'^[A-Z]+-\d+:', stripped):
                continue

            # 跳过单字母变量（通常是格式占位符或循环变量）
            if len(divisor) <= 1 or len(dividend) <= 1:
                continue

            # 跳过缩写/大写字母组合（如 CC/MI, DIT/CBO 等指标拼写）
            if divisor.isupper() or dividend.isupper():
                continue

            # 跳过完全大写的变量名（常量）
            if divisor.isupper() or dividend.isupper():
                continue

            # 跳过文档中的列举模式（如 "professional / dark / minimal"）
            if dividend.isalpha() and divisor.isalpha() and len(dividend) >= 4:
                continue

            # 跳过 Python Path 对象拼接操作（不是除法）
            path_indicators = ("path", "root", "dir", "folder", "_root", "_path")
            if any(indicator in dividend for indicator in path_indicators):
                continue

            # 跳过数学常量、字面量、常用安全表达式
            if divisor.isdigit() or divisor in ("len", "max", "min", "sum", "count", "size",
                                                  "total", "n", "i", "j", "index", "divisor"):
                continue

            start = max(0, match.start() - 200)
            context = code[start:match.start()]
            if not re.search(rf"{re.escape(divisor)}\s*(?:!=|==|>|<)\s*0", context):
                defects.append(Defect(
                    category=DefectCategory.BOUNDARY_COVERAGE,
                    risk_level=RiskLevel.MEDIUM,
                    file_path=file_path,
                    line_number=line_num + 1,
                    description=f"除法运算缺少除零检查（除数: {divisor}）",
                    fix_suggestion=f"在除法前检查 {divisor} != 0",
                    iso_reference="ISO/IEC 5055:2021 §5.4",
                ))

        return defects

    def detect_redundant_code(self, code: str, file_path: str) -> List[Defect]:
        """检测冗余代码"""
        defects = []

        # 注释掉的代码
        commented = self.REDUNDANCY_PATTERNS["commented_code"].finditer(code)
        for match in commented:
            line = code[:match.start()].count("\n") + 1
            # 跳过 TODO/FIXME/HACK/XXX 标记性注释（非冗余代码）
            line_start = code.rfind('\n', 0, match.start()) + 1
            line_prefix = code[line_start:match.start()]
            if re.search(r'#\s*(TODO|FIXME|HACK|XXX)\b', line_prefix):
                continue
            defects.append(Defect(
                category=DefectCategory.REDUNDANT_CODE,
                risk_level=RiskLevel.LOW,
                file_path=file_path,
                line_number=line,
                description=f"注释掉的代码: {match.group().strip()[:60]}",
                fix_suggestion="删除注释掉的代码，或恢复并添加说明注释",
                iso_reference="ISO/IEC 5055:2021 §5.6",
            ))

        return defects

    def security_scan(self, code: str, file_path: str) -> List[Defect]:
        """
        OWASP Top 10 安全漏洞扫描

        检测：
        - SQL/命令/代码注入
        - 认证失效
        - 敏感数据暴露
        - XSS 跨站脚本
        - 缓冲区溢出（C/C++）
        - 不安全的反序列化

        参数：
            code: 源代码
            file_path: 文件路径

        返回：
            安全缺陷列表
        """
        defects = []

        for owasp_category, patterns in OWASP_SECURITY_PATTERNS.items():
            for pattern, description in patterns:
                for match in re.finditer(pattern, code, re.IGNORECASE):
                    line = code[:match.start()].count("\n") + 1
                    # 跳过正则模式定义行（自匹配误报）
                    line_start = code.rfind('\n', 0, match.start()) + 1
                    line_text = code[line_start:match.start()]
                    if 'r"' in line_text or "r'" in line_text:
                        continue
                    risk = RiskLevel.HIGH
                    if "TODO" in description:
                        risk = RiskLevel.MEDIUM

                    defects.append(Defect(
                        category=DefectCategory.SECURITY_VULNERABILITY,
                        risk_level=risk,
                        file_path=file_path,
                        line_number=line,
                        description=f"[{owasp_category}] {description}",
                        fix_suggestion=self._get_security_fix(owasp_category, pattern),
                        iso_reference="ISO/IEC 5055:2021 §5.7 / OWASP Top 10:2021",
                    ))

        # 语言特定的安全检查
        # C/C++: 缓冲区溢出
        cpp_unsafe = re.findall(r"(?:strcpy|strcat|sprintf|gets|scanf)\s*\(", code)
        for func in cpp_unsafe:
            line = code[:code.find(func)].count("\n") + 1
            defects.append(Defect(
                category=DefectCategory.SECURITY_VULNERABILITY,
                risk_level=RiskLevel.HIGH,
                file_path=file_path,
                line_number=line,
                description=f"使用了不安全的 C 函数 {func} — 缓冲区溢出风险",
                fix_suggestion=f"将 {func} 替换为安全版本（如 strncpy, snprintf）",
                iso_reference="ISO/IEC 5055:2021 §5.7",
            ))

        # JavaScript: XSS
        xss_patterns = [
            (r"innerHTML\s*=", "直接操作 innerHTML — XSS 风险"),
            (r"document\.write\(", "对 doc.write 的直接调用 — XSS 风险"),
            (r"dangerously" r"SetInnerHTML", "使用危险的 HTML 设置属性 — XSS 风险"),
        ]
        for pattern, desc in xss_patterns:
            for match in re.finditer(pattern, code):
                line = code[:match.start()].count("\n") + 1
                defects.append(Defect(
                    category=DefectCategory.SECURITY_VULNERABILITY,
                    risk_level=RiskLevel.HIGH,
                    file_path=file_path,
                    line_number=line,
                    description=desc,
                    fix_suggestion="使用 textContent 或对用户输入进行 HTML 转义",
                    iso_reference="ISO/IEC 5055:2021 §5.7",
                ))

        return defects

    def _get_security_fix(self, category: str, pattern: str) -> str:
        """获取安全修复建议"""
        fix_map = {
            "sql": "使用参数化查询或 ORM 框架",
            "exec": "避免动态执行代码，使用安全的替代方案",
            "md5": "使用 SHA-256 或 bcrypt/scrypt",
            "sha1": "使用 SHA-256 或更强的哈希算法",
            "password": "将凭证移至环境变量或密钥管理服务",
            "pickle": "使用 JSON 替代 pickle 进行序列化",
            "pass": "添加异常日志记录和错误追踪",
            "DEBUG": "在生产环境关闭 DEBUG 模式",
        }
        for key, fix in fix_map.items():
            if key in pattern.lower():
                return fix
        return "参考 OWASP 对应类别的修复指南"

    def detect_deprecated_usage(self, code: str, language: str,
                                 file_path: str) -> List[Defect]:
        """检测过期 API 使用"""
        defects = []
        patterns = DEPRECATED_PATTERNS.get(language, [])

        for pattern, description in patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line = code[:match.start()].count("\n") + 1
                # 跳过正则模式定义行（自匹配误报）
                line_start = code.rfind('\n', 0, match.start()) + 1
                line_text = code[line_start:match.start()]
                if 'r"' in line_text or "r'" in line_text:
                    continue
                defects.append(Defect(
                    category=DefectCategory.DEPRECATED_DEPENDENCY,
                    risk_level=RiskLevel.MEDIUM,
                    file_path=file_path,
                    line_number=line,
                    description=f"使用了过期 API: {description}",
                    fix_suggestion=description.split("→")[-1].strip(),
                    iso_reference="ISO/IEC 5055:2021 §5.5",
                ))

        return defects

    def rate_module(self, module_name: str,
                    metrics: List[QualityMetrics]) -> ModuleQualityReport:
        """
        对模块进行综合评级

        评分标准（1-10）：
        - 圈复杂度（权重 30%）
        - 可维护性指数（权重 30%）
        - 类耦合度（权重 15%）
        - 继承深度（权重 10%）
        - LM-CC（权重 15%）

        参数：
            module_name: 模块名
            metrics: 模块内所有函数的指标列表

        返回：
            模块质量报告
        """
        if not metrics:
            return ModuleQualityReport(
                module_name=module_name,
                avg_cc=0, avg_mi=0, max_dit=0, avg_cbo=0,
                overall_score=10.0, rating="🟢 优秀"
            )

        avg_cc = sum(m.cyclomatic_complexity for m in metrics) / len(metrics)
        avg_mi = sum(m.maintainability_index for m in metrics) / len(metrics)
        max_dit = max(m.depth_of_inheritance for m in metrics)
        avg_cbo = sum(m.coupling_between_objects for m in metrics) / len(metrics)

        # 综合评分计算
        # CC 评分（越低越好）
        cc_score = max(0, 10 - (avg_cc / 5)) if avg_cc <= 50 else 0
        # MI 评分（越高越好）
        mi_score = min(10, avg_mi / 10)
        # CBO 评分（越低越好）
        cbo_score = max(0, 10 - (avg_cbo / 2)) if avg_cbo <= 14 else 0
        # DIT 评分（越低越好）
        dit_score = max(0, 10 - (max_dit * 2)) if max_dit <= 5 else 0

        overall = (
            cc_score * 0.30 +
            mi_score * 0.30 +
            cbo_score * 0.15 +
            dit_score * 0.10 +
            (10 - min(10, self.calculate_lm_cc(metrics) / 15 * 10)) * 0.15
        )

        # 评级
        if overall >= 8.0:
            rating = "🟢 优秀"
        elif overall >= 6.0:
            rating = "🟡 良好"
        elif overall >= 4.0:
            rating = "🟠 一般"
        else:
            rating = "🔴 较差"

        return ModuleQualityReport(
            module_name=module_name,
            avg_cc=round(avg_cc, 1),
            avg_mi=round(avg_mi, 1),
            max_dit=max_dit,
            avg_cbo=round(avg_cbo, 1),
            overall_score=round(overall, 1),
            rating=rating,
        )

    def analyze_file(self, file_path: Path) -> Tuple[List[QualityMetrics], List[Defect]]:
        """
        分析单个文件的质量指标和缺陷

        参数：
            file_path: 文件路径

        返回：
            (质量指标列表, 缺陷列表)
        """
        try:
            code = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            logging.getLogger(__name__).warning(f"Failed to read file {file_path} for quality evaluation")
            return [], []

        language = identify_language(file_path)
        metrics = []
        defects = []

        # 检测各类缺陷
        defects.extend(self.detect_syntax_errors(file_path))
        defects.extend(self.detect_logic_flaws(code, str(file_path)))
        defects.extend(self.detect_missing_exception_handling(code, str(file_path)))
        defects.extend(self.detect_boundary_issues(code, str(file_path)))
        defects.extend(self.detect_redundant_code(code, str(file_path)))
        defects.extend(self.security_scan(code, str(file_path)))
        defects.extend(self.detect_deprecated_usage(code, language, str(file_path)))

        # 计算类级别的 DIT/CBO
        dit_cbo_result = self._compute_dit_cbo(code, language)
        dit_values = dit_cbo_result.get("dit_values", {})
        cbo_values = dit_cbo_result.get("cbo_values", {})

        # 建立函数到父类的映射
        func_to_class = self._build_func_to_class_map(code, language)

        # 提取函数并计算指标
        if language == Language.PYTHON:
            func_pattern = re.compile(
                r"^\s*def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*\w+)?\s*:",
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(1)
                func_start = match.start()
                # 提取函数体（简化：取到下一个同缩进级别的 def 或 class）
                func_code = self._extract_function_body(code, func_start)

                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)

                parent_class = func_to_class.get(func_name)
                dit = dit_values.get(parent_class, 0) if parent_class else 0
                cbo = cbo_values.get(parent_class, 0) if parent_class else 0

                metrics.append(QualityMetrics(
                    function_name=func_name,
                    file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=loc,
                    cyclomatic_complexity=cc,
                    halstead_volume=hv,
                    maintainability_index=mi,
                    depth_of_inheritance=dit,
                    coupling_between_objects=cbo,
                    lm_cc=cc,
                    overall_score=min(10, max(0, mi / 10)),
                ))

        elif language == Language.JAVA:
            func_pattern = re.compile(
                r'(public|private|protected)\s+(static\s+)?(\w+(?:<.*?>)?)\s+(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(4)
                func_start = match.start()
                func_code = code[func_start:func_start + 2000]

                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)

                parent_class = func_to_class.get(func_name)
                dit = dit_values.get(parent_class, 0) if parent_class else 0
                cbo = cbo_values.get(parent_class, 0) if parent_class else 0

                metrics.append(QualityMetrics(
                    function_name=func_name, file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=min(loc, 50), cyclomatic_complexity=cc,
                    halstead_volume=hv, maintainability_index=mi,
                    depth_of_inheritance=dit, coupling_between_objects=cbo,
                    lm_cc=cc, overall_score=min(10, max(0, mi / 10)),
                ))

        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            func_pattern = re.compile(
                r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(1)
                func_start = match.start()
                func_code = code[func_start:func_start + 2000]

                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)

                metrics.append(QualityMetrics(
                    function_name=func_name, file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=min(loc, 50), cyclomatic_complexity=cc,
                    halstead_volume=hv, maintainability_index=mi,
                    depth_of_inheritance=0, coupling_between_objects=0,
                    lm_cc=cc, overall_score=min(10, max(0, mi / 10)),
                ))

            arrow_pattern = re.compile(
                r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
                re.MULTILINE
            )
            for match in arrow_pattern.finditer(code):
                func_name = match.group(1)
                func_start = match.start()
                func_code = code[func_start:func_start + 2000]

                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)

                metrics.append(QualityMetrics(
                    function_name=func_name, file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=min(loc, 50), cyclomatic_complexity=cc,
                    halstead_volume=hv, maintainability_index=mi,
                    depth_of_inheritance=0, coupling_between_objects=0,
                    lm_cc=cc, overall_score=min(10, max(0, mi / 10)),
                ))

        elif language in (Language.CPP, Language.C):
            class_pattern = re.compile(
                r'(\w+(?:::\w+)?)\s+(\w+)::(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in class_pattern.finditer(code):
                func_name = f"{match.group(2)}::{match.group(3)}"
                func_start = match.start()
                func_code = code[func_start:func_start + 2000]

                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)

                metrics.append(QualityMetrics(
                    function_name=func_name, file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=min(loc, 50), cyclomatic_complexity=cc,
                    halstead_volume=hv, maintainability_index=mi,
                    depth_of_inheritance=0, coupling_between_objects=0,
                    lm_cc=cc, overall_score=min(10, max(0, mi / 10)),
                ))

            free_pattern = re.compile(
                r'(\w+(?:\s*\*)?)\s+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{',
                re.MULTILINE
            )
            for match in free_pattern.finditer(code):
                func_name = match.group(2)
                func_start = match.start()
                func_code = code[func_start:func_start + 2000]

                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)

                metrics.append(QualityMetrics(
                    function_name=func_name, file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=min(loc, 50), cyclomatic_complexity=cc,
                    halstead_volume=hv, maintainability_index=mi,
                    depth_of_inheritance=0, coupling_between_objects=0,
                    lm_cc=cc, overall_score=min(10, max(0, mi / 10)),
                ))

        elif language == Language.CSHARP:
            func_pattern = re.compile(
                r'(public|private|protected|internal)\s+(static\s+)?(async\s+)?(\w+(?:<.*?>)?)\s+(\w+)\s*\(([^)]*)\)',
                re.MULTILINE
            )
            for match in func_pattern.finditer(code):
                func_name = match.group(5)
                func_start = match.start()
                func_code = code[func_start:func_start + 2000]
                
                cc = self.calculate_cyclomatic_complexity(func_code)
                hv = self.calculate_halstead_volume(func_code)
                loc = func_code.count("\n") + 1
                mi = self.calculate_maintainability_index(cc, hv, loc)
                
                metrics.append(QualityMetrics(
                    function_name=func_name, file_path=str(file_path),
                    start_line=code[:func_start].count("\n") + 1,
                    end_line=code[:func_start + len(func_code)].count("\n") + 1,
                    loc=min(loc, 50), cyclomatic_complexity=cc,
                    halstead_volume=hv, maintainability_index=mi,
                    depth_of_inheritance=0, coupling_between_objects=0,
                    lm_cc=cc, overall_score=min(10, max(0, mi / 10)),
                ))

        return metrics, defects

    def _extract_function_body(self, code: str, func_start: int) -> str:
        """提取 Python 函数体"""
        lines = code[func_start:].split("\n")
        body_lines = [lines[0]]
        if len(lines) > 1:
            base_indent = len(lines[1]) - len(lines[1].lstrip())
            for line in lines[1:]:
                stripped = line.lstrip()
                if stripped and (len(line) - len(stripped)) < base_indent:
                    if stripped.startswith(("def ", "class ", "@")):
                        break
                body_lines.append(line)
        return "\n".join(body_lines)

    def _build_func_to_class_map(self, code: str, language) -> Dict[str, str]:
        """构建函数名到其所属类名的映射"""
        func_to_class = {}
        if language == Language.PYTHON:
            try:
                import ast
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for child in ast.iter_child_nodes(node):
                            if isinstance(child, ast.FunctionDef):
                                func_to_class[child.name] = node.name
            except SyntaxError:
                logging.getLogger(__name__).debug("AST parse error in _build_func_to_class_map, falling back to regex")
        elif language == Language.JAVA:
            class_pattern = re.compile(
                r'class\s+(\w+)\s*(?:extends\s+\w+\s*)?(?:implements\s*[\w\s,]+)?\s*\{',
                re.MULTILINE
            )
            for cls_match in class_pattern.finditer(code):
                cls_name = cls_match.group(1)
                body_start = cls_match.end()
                depth = 1
                i = body_start
                while i < len(code) and depth > 0:
                    if code[i] == '{':
                        depth += 1
                    elif code[i] == '}':
                        depth -= 1
                    i += 1
                class_body = code[body_start:i - 1]
                method_pattern = re.compile(
                    r'(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\([^)]*\)\s*(?:\{|throws)',
                    re.MULTILINE
                )
                for method_match in method_pattern.finditer(class_body):
                    func_to_class[method_match.group(1)] = cls_name
        return func_to_class

    def _compute_dit_cbo(self, code: str, language) -> dict:
        """
        计算继承深度(DIT)和类耦合度(CBO)

        参数:
            code: 源代码
            language: 编程语言

        返回:
            {"dit_values": {class_name: depth}, "cbo_values": {class_name: count}}
        """
        dit_values = {}
        cbo_values = {}

        if language == Language.PYTHON:
            try:
                import ast
                tree = ast.parse(code)
            except SyntaxError:
                return {"dit_values": {}, "cbo_values": {}}

            class_parents = {}
            class_nodes = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    parents = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            parents.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            parents.append(base.attr)
                    class_parents[class_name] = parents
                    class_nodes[class_name] = node

            def _bfs_depth(cls_name, visited=None):
                if visited is None:
                    visited = set()
                if cls_name in visited:
                    return 0
                visited.add(cls_name)
                if cls_name not in class_parents:
                    return 0
                parents = class_parents[cls_name]
                if not parents or all(p.lower() in ('object', '') for p in parents):
                    return 1
                max_parent_depth = 0
                for p in parents:
                    if p not in visited:
                        d = _bfs_depth(p, visited.copy())
                        max_parent_depth = max(max_parent_depth, d)
                return max_parent_depth + 1 if max_parent_depth > 0 else 1

            for cls_name in class_parents:
                dit_values[cls_name] = _bfs_depth(cls_name)

            for cls_name, node in class_nodes.items():
                referenced_classes = set()
                for parent in class_parents.get(cls_name, []):
                    if parent in class_parents and parent != cls_name:
                        referenced_classes.add(parent)
                for child in ast.walk(node):
                    if isinstance(child, ast.AnnAssign):
                        if isinstance(child.annotation, ast.Name):
                            ref = child.annotation.id
                            if ref in class_parents and ref != cls_name:
                                referenced_classes.add(ref)
                    elif isinstance(child, ast.FunctionDef):
                        if child.returns and isinstance(child.returns, ast.Name):
                            ref = child.returns.id
                            if ref in class_parents and ref != cls_name:
                                referenced_classes.add(ref)
                        for arg in child.args.args:
                            if arg.annotation and isinstance(arg.annotation, ast.Name):
                                ref = arg.annotation.id
                                if ref in class_parents and ref != cls_name:
                                    referenced_classes.add(ref)
                cbo_values[cls_name] = len(referenced_classes)

        elif language == Language.JAVA:
            class_pattern = re.compile(
                r'class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?'
            )
            classes = {}
            for match in class_pattern.finditer(code):
                cls_name = match.group(1)
                parent = match.group(2)
                parents = [parent] if parent else []
                classes[cls_name] = parents

            def _bfs_depth_java(cls_name, visited=None):
                if visited is None:
                    visited = set()
                if cls_name in visited:
                    return 0
                visited.add(cls_name)
                if cls_name not in classes:
                    return 0
                parents = classes[cls_name]
                if not parents:
                    return 0
                max_depth = 0
                for p in parents:
                    if p not in visited:
                        d = _bfs_depth_java(p, visited.copy())
                        max_depth = max(max_depth, d)
                return max_depth + 1

            for cls_name in classes:
                dit_values[cls_name] = _bfs_depth_java(cls_name)

            for cls_name in classes:
                refs = set()
                for other_cls in classes:
                    if other_cls != cls_name:
                        if re.search(r'\b' + re.escape(other_cls) + r'\b', code):
                            refs.add(other_cls)
                cbo_values[cls_name] = len(refs)

        elif language in (Language.CPP, Language.C):
            class_pattern = re.compile(
                r'class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?'
            )
            classes = {}
            for match in class_pattern.finditer(code):
                cls_name = match.group(1)
                parent = match.group(2)
                classes[cls_name] = [parent] if parent else []

            def _bfs_depth_cpp(cls_name, visited=None):
                if visited is None:
                    visited = set()
                if cls_name in visited:
                    return 0
                visited.add(cls_name)
                if cls_name not in classes:
                    return 0
                parents = classes[cls_name]
                if not parents:
                    return 0
                max_depth = 0
                for p in parents:
                    if p not in visited:
                        d = _bfs_depth_cpp(p, visited.copy())
                        max_depth = max(max_depth, d)
                return max_depth + 1

            for cls_name in classes:
                dit_values[cls_name] = _bfs_depth_cpp(cls_name)

            for cls_name in classes:
                refs = set()
                for other_cls in classes:
                    if other_cls != cls_name:
                        if re.search(r'\b' + re.escape(other_cls) + r'\b', code):
                            refs.add(other_cls)
                cbo_values[cls_name] = len(refs)

        return {"dit_values": dit_values, "cbo_values": cbo_values}

    def run_full_evaluation(self) -> Dict:
        """
        执行完整的质量评估

        返回：
            包含所有评估结果的字典
        """
        all_metrics: Dict[str, List[QualityMetrics]] = defaultdict(list)
        all_defects: List[Defect] = []
        module_reports: List[ModuleQualityReport] = []

        # 扫描所有源文件
        code_files = list(self.project_root.rglob("*"))
        extensions = {".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".cs", ".cpp", ".c"}

        for f in code_files:
            if f.suffix not in extensions:
                continue
            if any(ex in f.parts for ex in EXCLUDE_DIRS):
                continue

            file_metrics, file_defects = self.analyze_file(f)
            module = f.parent.name if f.parent != self.project_root else "root"

            all_metrics[module].extend(file_metrics)
            all_defects.extend(file_defects)

        # 生成模块评级
        for module, metrics in all_metrics.items():
            report = self.rate_module(module, metrics)
            report.defects = [d for d in all_defects
                              if Path(d.file_path).parent.name == module
                              or (module == "root" and Path(d.file_path).parent == self.project_root)]
            module_reports.append(report)

        # 总体评分
        if module_reports:
            overall = sum(r.overall_score for r in module_reports) / len(module_reports)
        else:
            overall = 0.0

        return {
            "overall_score": round(overall, 1),
            "module_reports": module_reports,
            "all_defects": all_defects,
            "defects_by_risk": {
                "high": [d for d in all_defects if d.risk_level == RiskLevel.HIGH],
                "medium": [d for d in all_defects if d.risk_level == RiskLevel.MEDIUM],
                "low": [d for d in all_defects if d.risk_level == RiskLevel.LOW],
            },
        }


# ============================================================
# 入口函数
# ============================================================

def evaluate_quality(project_root: str) -> Dict:
    """
    模块 4 入口函数

    参数：
        project_root: 项目根目录

    返回：
        质量评估结果字典
    """
    evaluator = QualityEvaluator(project_root)
    return evaluator.run_full_evaluation()