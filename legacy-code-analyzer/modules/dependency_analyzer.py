"""
模块 3：依赖关系挖掘与耦合度分析 (Dependency Analyzer)

通过控制流与数据流分析构建依赖关系图谱，
识别显式依赖与隐式依赖，量化模块耦合度，检测依赖循环。

关键依赖：
- re: 正则表达式提取 import/include
- collections: defaultdict, deque 用于图遍历
"""

import logging
import re
from pathlib import Path
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple

from .shared import Language, DependencyType, identify_language, IMPORT_PATTERNS, IMPLICIT_PATTERNS


class DataDependencyType(Enum):
    RAW = "RAW"  # Read After Write - 正常数据依赖
    WAR = "WAR"  # Write After Read - 反依赖
    WAW = "WAW"  # Write After Write - 输出依赖


@dataclass
class DependencyEdge:
    source_module: str
    target_module: str
    dependency_type: DependencyType
    source_file: str
    source_line: int
    description: str
    is_circular: bool = False


@dataclass
class ModuleCouplingMetrics:
    module_name: str
    ca: int = 0      # Afferent Coupling: 有多少模块依赖我
    ce: int = 0      # Efferent Coupling: 我依赖多少模块
    abstract_classes: int = 0
    concrete_classes: int = 0
    instability: float = 0.0     # I = Ce / (Ca + Ce)
    abstractness: float = 0.0    # A = abstract / total
    distance: float = 0.0        # D = |A + I - 1|
    rating: str = ""


@dataclass
class DependencyCycle:
    modules: List[str]
    edges: List[DependencyEdge]
    severity: str  # "high", "medium", "low"


class DependencyAnalyzer:
    """
    依赖分析器 - 模块 3 核心类

    工作流：
    1. extract_explicit_deps()   → 提取显式依赖
    2. extract_implicit_deps()   → 提取隐式依赖
    3. build_dependency_graph()  → 构建依赖图
    4. calculate_coupling()      → 计算耦合度指标
    5. detect_cycles()           → 检测依赖循环
    6. classify_data_deps()      → 分类数据依赖
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.modules: Dict[str, Set[str]] = defaultdict(set)  # module → files
        self.explicit_edges: List[DependencyEdge] = []
        self.implicit_edges: List[DependencyEdge] = []
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)

    def discover_modules(self) -> Dict[str, Set[str]]:
        """
        发现项目中的模块

        模块定义：根目录下的一级子目录（排除隐藏目录和构建目录）

        返回：
            {模块名: {文件路径集合}}
        """
        exclude = {".git", "node_modules", "__pycache__", "venv", ".venv",
                   "target", "build", "dist", ".idea", ".vscode", "test", "tests"}

        modules = defaultdict(set)

        for item in self.project_root.iterdir():
            if item.is_dir() and item.name not in exclude:
                code_files = list(item.rglob("*"))
                for f in code_files:
                    if f.is_file() and f.suffix in {
                        ".py", ".java", ".js", ".jsx", ".ts", ".tsx",
                        ".cs", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h", ".c"
                    }:
                        modules[item.name].add(str(f.relative_to(self.project_root)))
            elif item.is_file() and item.suffix in {
                ".py", ".java", ".js", ".jsx", ".ts", ".tsx",
                ".cs", ".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h", ".c"
            }:
                # 根目录下的独立文件归入 "root" 模块
                modules["root"].add(item.name)

        self.modules = dict(modules)
        return self.modules

    def extract_explicit_dependencies(self) -> List[DependencyEdge]:
        """
        提取显式依赖

        扫描所有源文件的 import/include 语句，
        构建模块间的显式依赖关系。

        返回：
            显式依赖边列表
        """
        edges = []
        module_names = set(self.modules.keys())

        for module_name, files in self.modules.items():
            for file_rel in files:
                file_path = self.project_root / file_rel
                if not file_path.exists():
                    continue

                language = identify_language(file_path)
                pattern = IMPORT_PATTERNS.get(language)
                if not pattern:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    logging.getLogger(__name__).warning(f"Failed to read {file_path} for explicit dependency analysis")
                    continue

                for match in pattern.finditer(content):
                    imported = match.group(1) or match.group(2)
                    if not imported:
                        continue

                    # 提取顶级模块名
                    top_module = imported.split(".")[0].split("/")[0]
                    if top_module in module_names and top_module != module_name:
                        line_num = content[:match.start()].count("\n") + 1
                        edge = DependencyEdge(
                            source_module=module_name,
                            target_module=top_module,
                            dependency_type=DependencyType.EXPLICIT_IMPORT,
                            source_file=str(file_rel),
                            source_line=line_num,
                            description=f"import {imported}",
                        )
                        edges.append(edge)

        self.explicit_edges = edges
        return edges

    def extract_implicit_dependencies(self) -> List[DependencyEdge]:
        """
        提取隐式依赖

        检测：
        - 全局变量访问
        - 环境变量读取
        - 文件系统操作
        - 反射/eval 调用

        返回：
            隐式依赖边列表
        """
        edges = []

        for module_name, files in self.modules.items():
            for file_rel in files:
                file_path = self.project_root / file_rel
                if not file_path.exists():
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    logging.getLogger(__name__).warning(f"Failed to read {file_path} for implicit dependency analysis")
                    continue

                for dep_type, patterns in IMPLICIT_PATTERNS.items():
                    if dep_type == "__dynamic_import__":
                        actual_type = DependencyType.IMPLICIT_CROSS_MODULE
                    elif dep_type == "__db_connection__":
                        actual_type = DependencyType.IMPLICIT_CROSS_MODULE
                    else:
                        actual_type = dep_type
                    for pattern in patterns:
                        for match in re.finditer(pattern, content, re.IGNORECASE):
                            line_num = content[:match.start()].count("\n") + 1
                            edge = DependencyEdge(
                                source_module=module_name,
                                target_module="__implicit__",  # 隐式依赖目标标记
                                dependency_type=actual_type,
                                source_file=str(file_rel),
                                source_line=line_num,
                                description=f"{actual_type.value}: {match.group()[:60]}",
                            )
                            edges.append(edge)

        self.implicit_edges = edges
        return edges

    def build_dependency_graph(self) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """
        构建模块依赖图（邻接表表示）

        返回：
            (正向邻接表, 反向邻接表)
        """
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        reverse: Dict[str, Set[str]] = defaultdict(set)

        for edge in self.explicit_edges:
            adjacency[edge.source_module].add(edge.target_module)
            reverse[edge.target_module].add(edge.source_module)

        # 确保所有模块都在图中
        for module in self.modules:
            if module not in adjacency:
                adjacency[module] = set()
            if module not in reverse:
                reverse[module] = set()

        self.adjacency = dict(adjacency)
        self.reverse_adjacency = dict(reverse)
        return self.adjacency, self.reverse_adjacency

    def calculate_coupling_metrics(self) -> List[ModuleCouplingMetrics]:
        """
        计算每个模块的耦合度指标

        指标：
        - Ca (Afferent Coupling): 传入耦合 — 依赖本模块的其他模块数
        - Ce (Efferent Coupling): 传出耦合 — 本模块依赖的其他模块数
        - I (Instability): I = Ce / (Ca + Ce), 0=稳定, 1=不稳定
        - A (Abstractness): 抽象类占比
        - D (Distance): D = |A + I - 1|, 越小越平衡

        返回：
            模块耦合度指标列表
        """
        metrics = []

        for module in self.modules:
            ca = len(self.reverse_adjacency.get(module, set()))
            ce = len(self.adjacency.get(module, set()))

            # 不稳定性
            total = ca + ce
            instability = ce / total if total > 0 else 0.0

            # 抽象度（简化计算：基于文件中的抽象关键词）
            abstractness = self._calculate_abstractness(module)

            # 距主序列距离
            distance = abs(abstractness + instability - 1.0)

            # 评级
            if distance < 0.2:
                rating = "✅ 平衡"
            elif distance < 0.5:
                rating = "⚠️ 略偏离"
            else:
                rating = "🔴 偏离主序列"

            metrics.append(ModuleCouplingMetrics(
                module_name=module,
                ca=ca,
                ce=ce,
                instability=round(instability, 2),
                abstractness=round(abstractness, 2),
                distance=round(distance, 2),
                rating=rating,
            ))

        return metrics

    def _calculate_abstractness(self, module_name: str) -> float:
        """计算模块的抽象度（抽象类/接口占比）"""
        total_classes = 0
        abstract_classes = 0

        for file_rel in self.modules.get(module_name, set()):
            file_path = self.project_root / file_rel
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                logging.getLogger(__name__).warning(f"Failed to read {file_path} for abstractness calculation")
                continue

            # 统计类和抽象类
            class_pattern = re.compile(
                r"(?:abstract\s+)?class\s+\w+|interface\s+\w+|"
                r"class\s+\w+.*ABC|class\s+\w+.*abstractmethod",
                re.IGNORECASE
            )
            matches = class_pattern.findall(content)
            total_classes += len(matches)

            abstract_pattern = re.compile(
                r"abstract\s+class|interface\s+|ABC|abstractmethod",
                re.IGNORECASE
            )
            abstract_classes += len(abstract_pattern.findall(content))

        if total_classes == 0:
            return 0.0
        return abstract_classes / total_classes

    def detect_cycles(self) -> List[DependencyCycle]:
        """
        使用 DFS 检测依赖图中的循环

        算法：
        1. 对每个未访问的节点执行 DFS
        2. 维护访问栈（当前 DFS 路径）
        3. 如果遇到栈中已有的节点 → 发现循环
        4. 记录完整循环路径

        返回：
            依赖循环列表
        """
        cycles = []
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {m: WHITE for m in self.modules}
        parent: Dict[str, Optional[str]] = {m: None for m in self.modules}

        def dfs(node: str, stack: List[str]):
            color[node] = GRAY
            stack.append(node)

            for neighbor in self.adjacency.get(node, set()):
                if color.get(neighbor) == GRAY:
                    # 发现循环
                    cycle_start = stack.index(neighbor)
                    cycle_modules = stack[cycle_start:] + [neighbor]

                    # 构建循环边
                    cycle_edges = []
                    for i in range(len(cycle_modules) - 1):
                        src = cycle_modules[i]
                        tgt = cycle_modules[i + 1]
                        matching = [e for e in self.explicit_edges
                                    if e.source_module == src and e.target_module == tgt]
                        if matching:
                            cycle_edges.append(matching[0])
                            matching[0].is_circular = True

                    severity = "low"
                    if len(cycle_modules) > 3:
                        severity = "high"
                    elif len(cycle_modules) > 2:
                        severity = "medium"

                    cycles.append(DependencyCycle(
                        modules=cycle_modules[:-1],
                        edges=cycle_edges,
                        severity=severity,
                    ))

                elif color.get(neighbor) == WHITE:
                    dfs(neighbor, stack)

            stack.pop()
            color[node] = BLACK

        for module in self.modules:
            if color.get(module) == WHITE:
                dfs(module, [])

        return cycles

    def classify_data_dependencies(self, file_path: Path) -> List[Tuple[str, str, str]]:
        """
        分类数据依赖类型

        - RAW (Read After Write): 变量先写入后被读取 → 正常数据流
        - WAR (Write After Read): 变量先被读取后被写入 → 反依赖（潜在问题）
        - WAW (Write After Write): 变量被多次写入 → 输出依赖（需检查中间读取）

        参数：
            file_path: 源文件路径

        返回：
            [(变量名, 依赖类型, 描述), ...]
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            logging.getLogger(__name__).warning(f"Failed to read {file_path} for data dependency classification")
            return []

        dependencies = []
        variable_events: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        # (行号, 事件类型: "read" | "write")

        # 简化实现：基于赋值和引用模式
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # 检测写入（赋值）
            assign_match = re.match(r"^\s*(\w+)\s*=", line)
            if assign_match:
                var = assign_match.group(1)
                variable_events[var].append((i + 1, "write"))

            # 检测读取
            for var in list(variable_events.keys()):
                if re.search(rf"\b{re.escape(var)}\b", line):
                    # 检查是否在同一行有赋值（排除自身）
                    if not re.match(rf"^\s*{re.escape(var)}\s*=", line):
                        events = variable_events.get(var)
                        if events is not None:
                            events.append((i + 1, "read"))

        # 分类
        for var, events in variable_events.items():
            reads = [e for e in events if e[1] == "read"]
            writes = [e for e in events if e[1] == "write"]

            if reads and writes:
                last_read = max(r[0] for r in reads)
                last_write = max(w[0] for w in writes)
                first_write = min(w[0] for w in writes)

                if first_write < min(r[0] for r in reads):
                    dependencies.append((var, "RAW", "正常数据依赖"))
                elif last_read < last_write:
                    dependencies.append((var, "WAR", "⚠️ 反依赖：写入前有读取"))
                elif len(writes) > 1:
                    dependencies.append((var, "WAW", "⚠️ 输出依赖：多次写入"))

        return dependencies

    def generate_impact_analysis(self, target_module: str) -> Dict:
        """
        生成模块修改的影响范围分析

        参数：
            target_module: 目标模块名

        返回：
            影响分析结果
        """
        # 直接依赖（我依赖的模块）
        direct_deps = list(self.adjacency.get(target_module, set()))

        # 直接被依赖（依赖我的模块）
        direct_dependents = list(self.reverse_adjacency.get(target_module, set()))

        # 间接被依赖（BFS 两层）
        indirect_dependents = set()
        queue = deque(direct_dependents)
        visited = {target_module}
        depth = 0
        while queue and depth < 2:
            for _ in range(len(queue)):
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                if depth > 0:
                    indirect_dependents.add(current)
                for dep in self.reverse_adjacency.get(current, set()):
                    if dep not in visited:
                        queue.append(dep)
            depth += 1

        return {
            "target_module": target_module,
            "direct_dependencies": direct_deps,
            "direct_dependents": direct_dependents,
            "indirect_dependents": list(indirect_dependents),
            "total_impact_scope": len(direct_dependents) + len(indirect_dependents),
            "risk_level": "high" if len(direct_dependents) > 5 else
                          "medium" if len(direct_dependents) > 2 else "low",
        }

    def generate_mermaid_dependency_graph(self) -> str:
        """
        生成 Mermaid 格式的依赖关系图

        包含：
        - 模块节点（标注耦合度）
        - 依赖边（标注依赖类型）
        - 循环依赖高亮

        返回：
            Mermaid graph 字符串
        """
        lines = ["graph LR"]
        module_ids = {}

        for i, module in enumerate(sorted(self.modules.keys())):
            mod_id = f"M{i}"
            module_ids[module] = mod_id
            ce = len(self.adjacency.get(module, set()))
            lines.append(f'    {mod_id}["{module}\\n(Ce={ce})"]')

        for edge in self.explicit_edges:
            src_id = module_ids.get(edge.source_module)
            tgt_id = module_ids.get(edge.target_module)
            if src_id and tgt_id:
                style = " ==> " if edge.is_circular else " --> "
                lines.append(f"    {src_id}{style}|{edge.dependency_type.value[:10]}| {tgt_id}")

        return "\n".join(lines)

    def run_full_analysis(self) -> Dict:
        """
        执行完整的依赖分析

        返回：
            包含所有分析结果的字典
        """
        self.discover_modules()
        explicit = self.extract_explicit_dependencies()
        implicit = self.extract_implicit_dependencies()
        self.build_dependency_graph()
        coupling = self.calculate_coupling_metrics()
        cycles = self.detect_cycles()

        return {
            "modules": dict(self.modules),
            "explicit_dependencies": explicit,
            "implicit_dependencies": implicit,
            "coupling_metrics": coupling,
            "dependency_cycles": cycles,
            "mermaid_graph": self.generate_mermaid_dependency_graph(),
        }


# ============================================================
# 入口函数
# ============================================================

def analyze_dependencies(project_root: str) -> Dict:
    """
    模块 3 入口函数

    参数：
        project_root: 项目根目录

    返回：
        依赖分析结果字典
    """
    analyzer = DependencyAnalyzer(project_root)
    return analyzer.run_full_analysis()


def analyze_impact(project_root: str, target_module: str) -> Dict:
    """
    分析修改某个模块的影响范围

    参数：
        project_root: 项目根目录
        target_module: 目标模块名

    返回：
        影响分析结果
    """
    analyzer = DependencyAnalyzer(project_root)
    analyzer.discover_modules()
    analyzer.extract_explicit_dependencies()
    analyzer.build_dependency_graph()
    return analyzer.generate_impact_analysis(target_module)