"""
模块 1：代码元数据与结构分析 (Code Scanner)

负责全量扫描指定代码目录/文件，自动识别编程语言，
输出标准化元数据报告和代码结构图谱。

关键依赖：
- os, pathlib: 文件系统遍历
- re: 正则表达式匹配语言特征
- json, yaml: 配置文件解析
- collections: 统计计数器
"""

import logging
import os
import re
import json
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

from .shared import Language, LANGUAGE_SIGNATURES, EXCLUDE_DIRS


@dataclass
class FileMetadata:
    path: str
    language: Language
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    functions: int = 0
    classes: int = 0


@dataclass
class ModuleInfo:
    name: str
    path: str
    responsibility: str
    files: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)


@dataclass
class ProjectMetadata:
    name: str
    root_path: str
    languages: Dict[Language, int]
    total_files: int
    total_lines: int
    total_code_lines: int
    total_comment_lines: int
    total_functions: int
    total_classes: int
    comment_ratio: float
    tech_stack: Dict[str, str]
    modules: List[ModuleInfo]
    git_info: Optional[Dict] = None


class CodeScanner:
    """
    代码扫描器 - 模块 1 核心类

    工作流：
    1. discover_files()     → 发现所有源代码文件
    2. identify_language()  → 识别每个文件的编程语言
    3. analyze_file()       → 分析单个文件的元数据
    4. build_structure()    → 构建项目结构图
    5. generate_report()    → 生成元数据报告
    """

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.file_metadata: List[FileMetadata] = []
        self.modules: List[ModuleInfo] = []
        self.tech_stack: Dict[str, str] = {}

    def discover_files(self, patterns: Optional[List[str]] = None) -> List[Path]:
        """
        递归发现源代码文件

        参数：
            patterns: glob 匹配模式列表，默认覆盖所有支持的语言扩展名

        返回：
            匹配的文件路径列表
        """
        if patterns is None:
            extensions = set()
            for lang in Language:
                if lang in LANGUAGE_SIGNATURES:
                    extensions.update(LANGUAGE_SIGNATURES[lang]["extensions"])
            patterns = [f"**/*{ext}" for ext in extensions]

        discovered = []
        for pattern in patterns:
            discovered.extend(self.root_path.glob(pattern))

        return [p for p in discovered
                if not any(ex in p.parts for ex in EXCLUDE_DIRS)]

    def identify_language(self, file_path: Path) -> Language:
        """
        通过扩展名和内容特征识别编程语言

        优先级：
        1. 文件扩展名精确匹配
        2. 项目配置文件推断
        3. 代码内容关键词匹配

        返回：
            识别到的语言枚举
        """
        ext = file_path.suffix

        # 第一步：扩展名精确匹配
        for lang, sig in LANGUAGE_SIGNATURES.items():
            if ext in sig["extensions"]:
                return lang

        # 第二步：检查项目配置文件
        for lang, sig in LANGUAGE_SIGNATURES.items():
            for config in sig["configs"]:
                if (self.root_path / config).exists():
                    return lang

        return Language.UNKNOWN

    def analyze_file(self, file_path: Path) -> FileMetadata:
        """
        分析单个文件的元数据

        统计：
        - 总行数、有效代码行、注释行、空行
        - 函数/方法定义数量
        - 类/接口定义数量

        参数：
            file_path: 文件路径

        返回：
            文件的元数据对象
        """
        language = self.identify_language(file_path)
        metadata = FileMetadata(path=str(file_path), language=language)

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            logging.getLogger(__name__).warning(f"Failed to read {file_path} for file analysis")
            return metadata

        lines = content.split("\n")
        metadata.total_lines = len(lines)

        # 行分类统计
        in_block_comment = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                metadata.blank_lines += 1
                continue

            # 块注释处理
            if language in (Language.JAVA, Language.JAVASCRIPT, Language.TYPESCRIPT, Language.CPP, Language.C):
                if in_block_comment:
                    metadata.comment_lines += 1
                    if "*/" in stripped:
                        in_block_comment = False
                    continue
                if stripped.startswith("/*"):
                    metadata.comment_lines += 1
                    if "*/" not in stripped:
                        in_block_comment = True
                    continue
                if stripped.startswith("//"):
                    metadata.comment_lines += 1
                    continue

            elif language == Language.PYTHON:
                if stripped.startswith("#"):
                    metadata.comment_lines += 1
                    continue

            metadata.code_lines += 1

        # 函数/方法计数
        if language == Language.PYTHON:
            metadata.functions = len(re.findall(r"^\s*def\s+\w+\s*\(", content, re.MULTILINE))
            metadata.classes = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))
        elif language == Language.JAVA:
            metadata.functions = len(re.findall(r"(public|private|protected)\s+\w+\s+\w+\s*\(", content))
            metadata.classes = len(re.findall(r"(public\s+)?class\s+\w+", content))
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            metadata.functions = len(re.findall(r"function\s+\w+\s*\(|=>\s*\{", content))
            metadata.classes = len(re.findall(r"class\s+\w+", content))
        elif language in (Language.CPP, Language.C):
            metadata.functions = len(re.findall(r"\w+\s+\w+::\w+\s*\(|\w+\s+\w+\s*\([^)]*\)\s*\{", content))
            metadata.classes = len(re.findall(r"class\s+\w+|struct\s+\w+", content))

        return metadata

    def detect_tech_stack(self) -> Dict[str, str]:
        """
        检测项目技术栈

        通过读取配置文件识别：
        - 编程语言及版本
        - 框架和库
        - 构建工具
        - 测试框架
        - 数据库驱动

        返回：
            技术栈字典 {类别: 技术名称}
        """
        stack = {}

        # Python 项目检测
        if (self.root_path / "requirements.txt").exists():
            stack["language"] = "Python"
            content = (self.root_path / "requirements.txt").read_text()
            if "fastapi" in content.lower():
                stack["framework"] = "FastAPI"
            elif "flask" in content.lower():
                stack["framework"] = "Flask"
            elif "django" in content.lower():
                stack["framework"] = "Django"
            if "pytest" in content.lower():
                stack["testing"] = "pytest"
            if "sqlalchemy" in content.lower():
                stack["orm"] = "SQLAlchemy"

        # JavaScript/TypeScript 项目检测
        pkg_json = self.root_path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "typescript" in deps:
                    stack["language"] = "TypeScript"
                else:
                    stack["language"] = "JavaScript"
                if "react" in deps:
                    stack["framework"] = "React"
                elif "vue" in deps:
                    stack["framework"] = "Vue"
                elif "express" in deps:
                    stack["framework"] = "Express"
                if "jest" in deps:
                    stack["testing"] = "Jest"
                elif "vitest" in deps:
                    stack["testing"] = "Vitest"
            except json.JSONDecodeError:
                pass

        # Java 项目检测
        pom_xml = self.root_path / "pom.xml"
        if pom_xml.exists():
            stack["language"] = "Java"
            stack["build_tool"] = "Maven"
            content = pom_xml.read_text()
            if "spring-boot" in content:
                stack["framework"] = "Spring Boot"
            if "junit" in content:
                stack["testing"] = "JUnit"

        # C++ 项目检测
        cmake = self.root_path / "CMakeLists.txt"
        if cmake.exists():
            stack["language"] = "C++"
            stack["build_tool"] = "CMake"

        # 回退检测：通过扫描源代码文件推断技术栈
        if not stack:
            py_files = list(self.root_path.rglob("*.py"))
            js_files = list(self.root_path.rglob("*.js")) + list(self.root_path.rglob("*.jsx"))
            ts_files = list(self.root_path.rglob("*.ts")) + list(self.root_path.rglob("*.tsx"))
            java_files = list(self.root_path.rglob("*.java"))
            cpp_files = list(self.root_path.rglob("*.cpp")) + list(self.root_path.rglob("*.h"))

            if py_files:
                stack["language"] = "Python"
                stack["runtime"] = "CPython 3.x"
                if any("fastapi" in f.name.lower() for f in py_files):
                    stack["framework"] = "FastAPI"
                if any("pytest" in f.name.lower() for f in py_files):
                    stack["testing"] = "pytest"
            elif js_files:
                stack["language"] = "JavaScript"
            elif ts_files:
                stack["language"] = "TypeScript"
            elif java_files:
                stack["language"] = "Java"
            elif cpp_files:
                stack["language"] = "C++"

        return stack

    def build_module_structure(self) -> List[ModuleInfo]:
        """
        构建模块划分结构

        通过目录层级识别模块：
        - 一级子目录视为独立模块
        - 分析模块间 import 关系

        返回：
            模块信息列表
        """
        modules = []
        module_dirs = [d for d in self.root_path.iterdir()
                       if d.is_dir() and d.name not in EXCLUDE_DIRS]

        for mod_dir in module_dirs:
            files = list(mod_dir.rglob("*"))
            code_files = [f for f in files if f.suffix in
                          {".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".cs", ".cpp", ".h", ".c"}]

            if code_files:
                module = ModuleInfo(
                    name=mod_dir.name,
                    path=str(mod_dir),
                    responsibility=self._infer_responsibility(mod_dir.name),
                    files=[str(f.relative_to(self.root_path)) for f in code_files],
                )
                modules.append(module)

        # 分析模块间依赖
        self._analyze_module_dependencies(modules)

        return modules

    def _infer_responsibility(self, dir_name: str) -> str:
        """根据目录名推断模块职责"""
        responsibility_map = {
            "api": "API 路由层 / 控制器",
            "controllers": "请求控制器",
            "routes": "路由定义",
            "services": "业务逻辑层",
            "service": "业务逻辑层",
            "models": "数据模型定义",
            "model": "数据模型定义",
            "entities": "实体定义",
            "repositories": "数据访问层",
            "dao": "数据访问对象",
            "utils": "工具函数",
            "helpers": "辅助函数",
            "config": "配置管理",
            "middleware": "中间件",
            "tests": "测试代码",
            "migrations": "数据库迁移",
            "scripts": "脚本工具",
            "components": "UI 组件",
            "pages": "页面组件",
            "hooks": "React Hooks",
            "store": "状态管理",
            "lib": "库代码",
            "core": "核心逻辑",
            "common": "公共模块",
            "shared": "共享模块",
            "types": "类型定义",
            "interfaces": "接口定义",
            "db": "数据库相关",
            "database": "数据库相关",
            "modules": "核心分析模块",
            "src": "源代码根目录",
            "source": "源代码根目录",
        }
        return responsibility_map.get(dir_name.lower(), "未分类模块")

    def _analyze_module_dependencies(self, modules: List[ModuleInfo]):
        """分析模块间的 import 依赖关系"""
        import_patterns = {
            Language.PYTHON: re.compile(r"^(?:from|import)\s+([\w.]+)", re.MULTILINE),
            Language.JAVA: re.compile(r"^import\s+([\w.]+)", re.MULTILINE),
            Language.JAVASCRIPT: re.compile(r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))", re.MULTILINE),
            Language.TYPESCRIPT: re.compile(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
            Language.CPP: re.compile(r'#include\s+[<"]([^>"]+)[>"]', re.MULTILINE),
        }

        module_names = {m.name for m in modules}

        for module in modules:
            for file_path in module.files:
                full_path = self.root_path / file_path
                if not full_path.exists():
                    continue
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    logging.getLogger(__name__).warning(f"Failed to read {full_path} for module dependency analysis")
                    continue
                lang = self.identify_language(full_path)
                pattern = import_patterns.get(lang)
                if pattern:
                    for match in pattern.finditer(content):
                        imported = match.group(1) or match.group(2)
                        if imported:
                            # 提取模块名（取第一段）
                            top_module = imported.split(".")[0].split("/")[0]
                            if top_module in module_names and top_module != module.name:
                                module.dependencies.add(top_module)

    def scan_git_history(self, max_commits: int = 50) -> Optional[Dict]:
        """
        扫描 Git 提交历史（可选）

        分析：
        - 高频修改的热点文件
        - 近期结构调整
        - 缺陷修复相关的提交

        返回：
            Git 历史分析结果
        """
        import subprocess
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root_path), "log",
                 f"-{max_commits}", "--pretty=format:%h|%ai|%s", "--name-only"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                return None

            # 解析提交日志
            commits = []
            current_commit = None
            for line in result.stdout.split("\n"):
                if "|" in line and not line.startswith(" "):
                    if current_commit:
                        commits.append(current_commit)
                    parts = line.split("|", 2)
                    current_commit = {
                        "hash": parts[0],
                        "date": parts[1],
                        "message": parts[2] if len(parts) > 2 else "",
                        "files": [],
                    }
                elif current_commit and line.strip():
                    current_commit["files"].append(line.strip())
            if current_commit:
                commits.append(current_commit)

            # 热点文件分析
            file_changes = Counter()
            fix_commits = []
            for commit in commits:
                for f in commit["files"]:
                    file_changes[f] += 1
                if any(kw in commit["message"].lower()
                       for kw in ("fix", "bug", "hotfix", "patch", "漏洞", "修复")):
                    fix_commits.append(commit)

            return {
                "total_commits_analyzed": len(commits),
                "hot_files": file_changes.most_common(10),
                "fix_commits": fix_commits[:10],
                "recent_commits": commits[:5],
            }
        except (subprocess.SubprocessError, FileNotFoundError):
            return None

    def run_full_scan(self) -> ProjectMetadata:
        """
        执行完整扫描

        使用 ThreadPoolExecutor 并行分析所有源文件，
        然后汇总统计元数据、检测技术栈、构建模块结构。

        返回：
            完整的项目元数据
        """
        files = self.discover_files()

        # 并行分析文件
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        file_metadata_list = []
        lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=min(8, len(files) or 1)) as executor:
            future_to_file = {executor.submit(self.analyze_file, f): f for f in files}
            for future in as_completed(future_to_file):
                try:
                    metadata = future.result()
                    with lock:
                        file_metadata_list.append(metadata)
                except Exception as e:
                    logging.getLogger(__name__).warning(
                        f"Failed to analyze {future_to_file[future]}: {e}"
                    )

        self.file_metadata = file_metadata_list
        self.tech_stack = self.detect_tech_stack()
        self.modules = self.build_module_structure()

        # 汇总统计
        lang_counter = Counter(m.language for m in self.file_metadata)
        total_lines = sum(m.total_lines for m in self.file_metadata)
        total_code = sum(m.code_lines for m in self.file_metadata)
        total_comment = sum(m.comment_lines for m in self.file_metadata)
        total_funcs = sum(m.functions for m in self.file_metadata)
        total_classes = sum(m.classes for m in self.file_metadata)
        comment_ratio = (total_comment / max(total_lines, 1)) * 100

        return ProjectMetadata(
            name=self.root_path.name,
            root_path=str(self.root_path),
            languages=dict(lang_counter),
            total_files=len(files),
            total_lines=total_lines,
            total_code_lines=total_code,
            total_comment_lines=total_comment,
            total_functions=total_funcs,
            total_classes=total_classes,
            comment_ratio=round(comment_ratio, 1),
            tech_stack=self.tech_stack,
            modules=self.modules,
            git_info=self.scan_git_history(),
        )

    def generate_mermaid_graph(self) -> str:
        """
        生成 Mermaid 格式的模块依赖关系图

        返回：
            Mermaid graph TD 格式的字符串
        """
        lines = ["graph TD"]
        module_ids = {}

        for i, module in enumerate(self.modules):
            mod_id = f"M{i}"
            module_ids[module.name] = mod_id
            lines.append(f'    {mod_id}["{module.name}\\n({module.responsibility})"]')

        for module in self.modules:
            for dep in module.dependencies:
                if dep in module_ids and module.name in module_ids:
                    lines.append(f"    {module_ids[module.name]} --> {module_ids[dep]}")

        return "\n".join(lines)

    def generate_tree_structure(self) -> str:
        """
        生成文本树形目录结构

        返回：
            树形结构字符串
        """
        lines = [f"{self.root_path.name}/"]
        for module in self.modules:
            lines.append(f"├── {module.name}/  [{module.responsibility}]")
            for f in sorted(module.files):
                lines.append(f"│   ├── {f}")
        return "\n".join(lines)


# ============================================================
# 入口函数
# ============================================================

def scan_project(root_path: str) -> Dict:
    """
    模块 1 入口函数

    参数：
        root_path: 项目根目录路径

    返回：
        包含元数据、结构图、Git 历史等信息的字典
    """
    scanner = CodeScanner(root_path)
    metadata = scanner.run_full_scan()

    return {
        "metadata": metadata,
        "mermaid_graph": scanner.generate_mermaid_graph(),
        "tree_structure": scanner.generate_tree_structure(),
        "file_details": scanner.file_metadata,
    }