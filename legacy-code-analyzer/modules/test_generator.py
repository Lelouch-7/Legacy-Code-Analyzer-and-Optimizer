"""
模块 6：自动化测试与重构辅助 (Test Generator & Refactoring Assistant)

为核心函数自动生成回归测试用例（正常/边界/异常三类场景），
针对低质量模块生成最小化重构方案。

关键依赖：
- re: 函数签名提取
- typing: 类型推断辅助
"""

import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple


class TestCaseType:
    NORMAL = "normal"
    BOUNDARY = "boundary"
    EXCEPTION = "exception"


@dataclass
class TestCase:
    function_name: str
    case_type: str
    description: str
    code: str
    expected_behavior: str
    test_framework: str


@dataclass
class FunctionSignature:
    name: str
    params: List[Tuple[str, str]]
    return_type: Optional[str]
    decorators: List[str]
    docstring: Optional[str]
    start_line: int
    end_line: int


@dataclass
class RefactoringPlan:
    module_name: str
    current_problems: List[str]
    steps: List["RefactoringStep"]
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    verification_checkpoints: List[str]


@dataclass
class RefactoringStep:
    order: int
    action: str
    target: str
    description: str
    code_snippet: Optional[str] = None
    verification: str = ""


class TestGenerator:
    """
    测试用例生成器

    工作流：
    1. extract_function_signatures() → 提取函数签名
    2. generate_normal_cases()       → 生成正常场景用例
    3. generate_boundary_cases()     → 生成边界场景用例
    4. generate_exception_cases()    → 生成异常场景用例
    5. detect_test_framework()       → 检测项目测试框架
    """

    FRAMEWORK_TEMPLATES = {
        "pytest": {
            "import": "import pytest",
            "exception": "with pytest.raises({exception_type}):",
        },
        "unittest": {
            "import": "import unittest",
            "exception": "with self.assertRaises({exception_type}):",
        },
        "jest": {
            "import": "",
            "exception": "expect(() => {{ ... }}).toThrow({exception_type});",
        },
        "junit": {
            "import": "import org.junit.Test;\nimport static org.junit.Assert.*;",
            "exception": "@Test(expected = {ExceptionType}.class)",
        },
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.framework = self.detect_test_framework()

    def detect_test_framework(self) -> str:
        req_file = self.project_root / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text().lower()
            if "pytest" in content:
                return "pytest"
            if "unittest" in content:
                return "unittest"

        pkg_json = self.project_root / "package.json"
        if pkg_json.exists():
            import json
            try:
                pkg = json.loads(pkg_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "jest" in deps:
                    return "jest"
                if "vitest" in deps:
                    return "vitest"
            except json.JSONDecodeError:
                return "pytest"

        pom_xml = self.project_root / "pom.xml"
        if pom_xml.exists():
            if "junit" in pom_xml.read_text().lower():
                return "junit"

        return "pytest"

    def extract_function_signatures(self, file_path: Path) -> List[FunctionSignature]:
        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception:
            logging.getLogger(__name__).warning(f"Failed to read file {file_path} for extracting function signatures")
            return []

        functions = []
        if file_path.suffix == ".py":
            pattern = re.compile(
                r"^\s*(@\w+(?:\([^)]*\))?\s*)*"
                r"def\s+(\w+)\s*\((.*?)\)\s*"
                r"(?:->\s*(\w+(?:\[.*?\])?))?\s*:"
                r'(?:\s*"""([^"]*)""")?',
                re.MULTILINE | re.DOTALL,
            )
            for match in pattern.finditer(code):
                decorator_block = match.group(0).split("def")[0]
                decorators = re.findall(r"@(\w+)", decorator_block)
                func_name = match.group(2)
                params_str = match.group(3)
                return_type = match.group(4)
                docstring = match.group(5)
                params = []
                if params_str.strip():
                    for param in params_str.split(","):
                        param = param.strip()
                        if ":" in param:
                            name, type_hint = param.split(":", 1)
                            params.append((name.strip(), type_hint.strip()))
                        else:
                            params.append((param, ""))
                line_num = code[:match.start()].count("\n") + 1
                functions.append(FunctionSignature(
                    name=func_name, params=params, return_type=return_type,
                    decorators=decorators,
                    docstring=docstring.strip() if docstring else None,
                    start_line=line_num, end_line=line_num,
                ))
        return functions

    def generate_normal_cases(self, func: FunctionSignature,
                               file_path: Path) -> List[TestCase]:
        typical_values = []
        for name, type_hint in func.params:
            if name in ("self", "cls"):
                continue
            if "int" in type_hint.lower():
                typical_values.append("42")
            elif "float" in type_hint.lower():
                typical_values.append("3.14")
            elif "str" in type_hint.lower():
                typical_values.append(f'"test_{name}"')
            elif "bool" in type_hint.lower():
                typical_values.append("True")
            elif "list" in type_hint.lower():
                typical_values.append("[1, 2, 3]")
            elif "dict" in type_hint.lower():
                typical_values.append('{"key": "value"}')
            else:
                typical_values.append(f'"valid_{name}"')

        args_str = ", ".join(typical_values)

        code = (
            f"def test_{func.name}_normal():\n"
            f'    """正常场景：{func.name} 的基本功能验证"""\n'
            f"    from {file_path.stem} import {func.name}\n"
            f"    result = {func.name}({args_str})\n"
            f"    assert result is not None\n"
            f"    # TODO: 根据实际预期补充断言\n"
        )

        return [TestCase(
            function_name=func.name,
            case_type=TestCaseType.NORMAL,
            description=f"验证 {func.name} 的基本功能",
            code=code,
            expected_behavior=f"{func.name} 应返回预期结果，无异常抛出",
            test_framework=self.framework,
        )]

    def generate_boundary_cases(self, func: FunctionSignature) -> List[TestCase]:
        cases = []
        boundary_map = {
            "int": [("0", "零值"), ("-1", "负值"), ("sys.maxsize", "最大整数")],
            "float": [("0.0", "零值"), ("float('inf')", "正无穷")],
            "str": [('""', "空字符串"), ('"a" * 10000', "超长字符串")],
            "list": [("[]", "空列表")],
            "dict": [("{}", "空字典")],
        }

        for name, type_hint in func.params:
            if name in ("self", "cls"):
                continue
            for type_key, values in boundary_map.items():
                if type_key in type_hint.lower():
                    for val, desc in values:
                        other_args = []
                        for on, ot in func.params:
                            if on in ("self", "cls") or on == name:
                                continue
                            if "int" in ot.lower():
                                other_args.append("42")
                            elif "str" in ot.lower():
                                other_args.append('"test"')
                            elif "float" in ot.lower():
                                other_args.append("3.14")
                            else:
                                other_args.append("None")
                        all_args = ", ".join([val] + other_args)
                        code = (
                            f"def test_{func.name}_boundary_{name}_{desc}():\n"
                            f'    """边界场景：{func.name} 参数 {name}={desc}"""\n'
                            f"    from {func.name} import {func.name}\n"
                            f"    result = {func.name}({all_args})\n"
                            f"    assert True  # TODO: 补充具体断言\n"
                        )
                        cases.append(TestCase(
                            function_name=func.name,
                            case_type=TestCaseType.BOUNDARY,
                            description=f"参数 {name} 为 {desc}",
                            code=code,
                            expected_behavior="函数不应崩溃，应返回合理结果或抛出明确异常",
                            test_framework=self.framework,
                        ))
        return cases[:5]

    def _generate_exception_cases(self, func: FunctionSignature) -> List[TestCase]:
        """
        生成异常场景的测试用例

        根据函数参数类型生成 None、类型错误、溢出值等异常输入的测试代码
        """
        cases = []

        valid_params = [(name, type_hint) for name, type_hint in func.params
                        if name not in ("self", "cls")]
        if not valid_params:
            return cases

        framework = self.framework
        if framework == "pytest":
            import_stmt = "import pytest"
            exception_stmt = "with pytest.raises((TypeError, ValueError, AttributeError)):"
        elif framework == "unittest":
            import_stmt = "import unittest"
            exception_stmt = "with self.assertRaises((TypeError, ValueError, AttributeError)):"
        else:
            import_stmt = "import pytest"
            exception_stmt = "with pytest.raises((TypeError, ValueError, AttributeError)):"

        null_args = ["None"] * len(valid_params)
        args_str = ", ".join(null_args)
        code = (
            f"def test_{func.name}_exception_none():\n"
            f'    """异常场景：{func.name} 接收 None 参数"""\n'
            f"    {import_stmt}\n"
            f"    result = {func.name}({args_str})\n"
        )
        if framework == "pytest":
            code = (
                f"def test_{func.name}_exception_none():\n"
                f'    """异常场景：{func.name} 接收 None 参数"""\n'
                f"    {import_stmt}\n"
                f"    {exception_stmt}\n"
                f"        {func.name}({args_str})\n"
            )
        cases.append(TestCase(
            function_name=func.name,
            case_type=TestCaseType.EXCEPTION,
            description="所有参数为 None",
            code=code,
            expected_behavior="应抛出 TypeError 或 ValueError",
            test_framework=framework,
        ))

        type_error_map = {
            "int": ('"not_an_int"', "字符串代替整数"),
            "float": ('"not_a_float"', "字符串代替浮点数"),
            "str": ("42", "整数代替字符串"),
            "list": ('"not_a_list"', "字符串代替列表"),
        }

        type_error_count = 0
        for name, type_hint in valid_params:
            if type_error_count >= 3:
                break
            for type_key, (bad_val, desc) in type_error_map.items():
                if type_error_count >= 3:
                    break
                if type_key in type_hint.lower():
                    args_parts = []
                    for p_name, p_type in valid_params:
                        if p_name == name:
                            args_parts.append(bad_val)
                        else:
                            if "int" in p_type.lower():
                                args_parts.append("42")
                            elif "str" in p_type.lower():
                                args_parts.append('"test"')
                            elif "float" in p_type.lower():
                                args_parts.append("3.14")
                            elif "list" in p_type.lower():
                                args_parts.append("[1, 2]")
                            elif "bool" in p_type.lower():
                                args_parts.append("True")
                            else:
                                args_parts.append("None")
                    all_args_str = ", ".join(args_parts)
                    code = (
                        f"def test_{func.name}_exception_type_{name}():\n"
                        f'    """异常场景：{func.name} 参数 {name} 类型错误（{desc}）"""\n'
                        f"    {import_stmt}\n"
                        f"    {exception_stmt}\n"
                        f"        {func.name}({all_args_str})\n"
                    )
                    cases.append(TestCase(
                        function_name=func.name,
                        case_type=TestCaseType.EXCEPTION,
                        description=f"参数 {name} 类型错误：{desc}",
                        code=code,
                        expected_behavior="应抛出 TypeError",
                        test_framework=framework,
                    ))
                    type_error_count += 1
                    break

        if len(cases) < 5:
            for name, type_hint in valid_params:
                if len(cases) >= 5:
                    break
                if "int" in type_hint.lower() or "float" in type_hint.lower():
                    extreme_val = "sys.maxsize * 2"
                    args_parts = []
                    for p_name, p_type in valid_params:
                        if p_name == name:
                            args_parts.append(extreme_val)
                        else:
                            if "int" in p_type.lower():
                                args_parts.append("42")
                            elif "str" in p_type.lower():
                                args_parts.append('"test"')
                            elif "float" in p_type.lower():
                                args_parts.append("3.14")
                            else:
                                args_parts.append("None")
                    all_args_str = ", ".join(args_parts)
                    code = (
                        f"def test_{func.name}_exception_overflow_{name}():\n"
                        f'    """异常场景：{func.name} 参数 {name} 为极大值"""\n'
                        f"    import sys\n"
                        f"    {import_stmt}\n"
                        f"    {exception_stmt}\n"
                        f"        {func.name}({all_args_str})\n"
                    )
                    cases.append(TestCase(
                        function_name=func.name,
                        case_type=TestCaseType.EXCEPTION,
                        description=f"参数 {name} 为极大值（溢出测试）",
                        code=code,
                        expected_behavior="应抛出 OverflowError 或 ValueError",
                        test_framework=framework,
                    ))
                elif "str" in type_hint.lower():
                    args_parts = []
                    for p_name, p_type in valid_params:
                        if p_name == name:
                            args_parts.append('"x" * 10**6')
                        else:
                            if "int" in p_type.lower():
                                args_parts.append("42")
                            elif "str" in p_type.lower():
                                args_parts.append('"test"')
                            elif "float" in p_type.lower():
                                args_parts.append("3.14")
                            else:
                                args_parts.append("None")
                    all_args_str = ", ".join(args_parts)
                    code = (
                        f"def test_{func.name}_exception_longstring_{name}():\n"
                        f'    """异常场景：{func.name} 参数 {name} 为超长字符串"""\n'
                        f"    {import_stmt}\n"
                        f"    {exception_stmt}\n"
                        f"        {func.name}({all_args_str})\n"
                    )
                    cases.append(TestCase(
                        function_name=func.name,
                        case_type=TestCaseType.EXCEPTION,
                        description=f"参数 {name} 为超长字符串",
                        code=code,
                        expected_behavior="应抛出 ValueError 或 MemoryError",
                        test_framework=framework,
                    ))

        return cases[:5]

    def generate_all_tests(self, file_path: Path) -> Dict[str, List[TestCase]]:
        functions = self.extract_function_signatures(file_path)
        all_tests = {}
        for func in functions:
            tests = []
            tests.extend(self.generate_normal_cases(func, file_path))
            tests.extend(self.generate_boundary_cases(func))
            tests.extend(self._generate_exception_cases(func))
            all_tests[func.name] = tests
        return all_tests


class RefactoringAssistant:
    """
    重构辅助器

    工作流：
    1. identify_problems()      → 识别代码问题
    2. plan_refactoring()       → 制定重构计划
    3. generate_steps()         → 生成具体步骤
    4. estimate_improvement()   → 估算改进效果
    5. create_verification()    → 创建验证检查点
    """

    # 重构操作类型
    ACTIONS = {
        "split": "代码拆分 — 将大函数分解为多个小函数",
        "rename": "命名规范 — 统一变量/函数命名风格",
        "remove": "冗余清除 — 删除未使用的代码",
        "simplify": "逻辑简化 — 减少嵌套、使用早返回",
        "extract": "提取公共逻辑 — 消除重复代码",
        "decouple": "解耦 — 减少模块间直接依赖",
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def identify_problems(self, file_path: Path, metrics: Dict = None) -> List[str]:
        try:
            code = file_path.read_text(encoding="utf-8")
        except Exception:
            logging.getLogger(__name__).warning(f"Failed to read file {file_path} for identifying refactoring problems")
            return ["无法读取文件"]

        problems = []
        lines = code.split("\n")

        # 过长函数检测
        func_pattern = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)
        func_matches = list(func_pattern.finditer(code))
        for i, match in enumerate(func_matches):
            start = match.start()
            end = func_matches[i + 1].start() if i + 1 < len(func_matches) else len(code)
            func_lines = code[start:end].count("\n")
            if func_lines > 50:
                problems.append(f"函数 `{match.group(1)}` 过长（{func_lines}行），建议拆分")

        # 深层嵌套检测
        for i, line in enumerate(lines):
            indent = len(line) - len(line.lstrip())
            if indent > 16:  # 4层以上嵌套
                problems.append(f"第{i+1}行存在深层嵌套（{indent//4}层）")
                break

        # 命名不一致检测
        snake = re.findall(r"\b[a-z]+_[a-z]+\b", code)
        camel = re.findall(r"\b[a-z]+[A-Z][a-z]+\b", code)
        if snake and camel:
            problems.append("存在 snake_case 和 camelCase 混用，建议统一命名风格")

        # 重复代码检测（简化版）
        chunks = defaultdict(list)
        for i in range(len(lines) - 2):
            chunk = "\n".join(lines[i:i + 3])
            chunks[chunk].append(i + 1)
        for chunk, occurrences in chunks.items():
            if len(occurrences) >= 3 and len(chunk.strip()) > 30:
                problems.append(f"发现重复代码块（出现在行 {occurrences}）")

        return problems

    def plan_refactoring(self, module_name: str, problems: List[str],
                          current_metrics: Dict[str, float]) -> RefactoringPlan:
        steps = []
        for i, problem in enumerate(problems):
            if "过长" in problem:
                steps.append(RefactoringStep(
                    order=i + 1,
                    action="split",
                    target=problem.split("`")[1] if "`" in problem else "unknown",
                    description=problem,
                    verification="拆分后每个子函数行数 ≤ 30",
                ))
            elif "嵌套" in problem:
                steps.append(RefactoringStep(
                    order=i + 1,
                    action="simplify",
                    target=problem,
                    description=problem,
                    verification="最大嵌套深度 ≤ 3 层",
                ))
            elif "命名" in problem:
                steps.append(RefactoringStep(
                    order=i + 1,
                    action="rename",
                    target="变量/函数命名",
                    description=problem,
                    verification="统一使用 snake_case 命名风格",
                ))
            elif "重复" in problem:
                steps.append(RefactoringStep(
                    order=i + 1,
                    action="extract",
                    target="重复代码块",
                    description=problem,
                    verification="重复代码提取为公共函数",
                ))

        # 估算改进后指标
        cc_before = current_metrics.get("cyclomatic_complexity", 20)
        mi_before = current_metrics.get("maintainability_index", 50)
        loc_before = current_metrics.get("loc", 200)

        after_metrics = {
            "cyclomatic_complexity": max(1, cc_before * 0.3),
            "maintainability_index": min(100, mi_before * 1.6),
            "loc": max(10, loc_before * 0.4),
            "max_function_length": 30,
            "max_nesting_depth": 3,
        }

        verification_checkpoints = [
            "所有原有功能的行为保持不变",
            "所有现有测试继续通过",
            "输入校验行为不变",
            "输出格式一致",
            "异常处理行为不变",
            "边界条件处理一致",
        ]

        return RefactoringPlan(
            module_name=module_name,
            current_problems=problems,
            steps=steps,
            before_metrics=current_metrics,
            after_metrics=after_metrics,
            verification_checkpoints=verification_checkpoints,
        )


from collections import defaultdict


def generate_tests(project_root: str, target_file: str = None) -> Dict:
    generator = TestGenerator(project_root)
    root = Path(project_root)
    files = [root / target_file] if target_file else list(root.rglob("*.py"))
    results = {}
    for f in files:
        if f.exists():
            results[str(f)] = generator.generate_all_tests(f)
    return results


def plan_refactoring(project_root: str, target_file: str,
                      metrics: Dict[str, float] = None) -> RefactoringPlan:
    assistant = RefactoringAssistant(project_root)
    file_path = Path(project_root) / target_file
    problems = assistant.identify_problems(file_path, metrics)
    current_metrics = metrics or {
        "cyclomatic_complexity": 15,
        "maintainability_index": 60,
        "loc": 200,
    }
    return assistant.plan_refactoring(
        Path(target_file).stem, problems, current_metrics
    )