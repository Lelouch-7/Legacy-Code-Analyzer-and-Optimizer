"""
模块 8：目标性评估与需求覆盖分析 (Requirement Tracer)

将用户输入的功能需求、技术规格与代码库实际实现进行系统性对照，
输出需求覆盖度矩阵和偏离分析报告。

关键依赖：
- re: 需求文本解析
- difflib: 文本相似度匹配
- 模块 2 (SemanticAnalyzer): 语义分析辅助
"""

import logging
import re
import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple


class RequirementStatus(Enum):
    IMPLEMENTED = "implemented"       # ✅ 已实现
    PARTIALLY = "partially"           # ⚠️ 部分实现
    NOT_IMPLEMENTED = "not_implemented"  # ❌ 未实现
    IMPLICIT = "implicit"             # 🔮 暗含实现


class RequirementType(Enum):
    FUNCTIONAL = "FR"
    NON_FUNCTIONAL = "NFR"
    BUSINESS_RULE = "BR"
    CONSTRAINT = "CN"


@dataclass
class Requirement:
    req_id: str
    req_type: RequirementType
    description: str
    keywords: List[str]
    acceptance_criteria: List[str]
    status: RequirementStatus = RequirementStatus.NOT_IMPLEMENTED
    matched_locations: List[str] = field(default_factory=list)
    implementation_notes: str = ""
    deviation_notes: str = ""
    impact_assessment: str = ""


@dataclass
class RequirementTraceabilityMatrix:
    project_name: str
    requirements: List[Requirement]
    total_count: int
    implemented_count: int
    partially_count: int
    not_implemented_count: int
    implicit_count: int
    coverage_rate: float


@dataclass
class DeviationReport:
    req_id: str
    expected: str
    actual: str
    deviation_level: str  # "high", "medium", "low"
    impact: str


@dataclass
class TargetAssessmentReport:
    matrix: RequirementTraceabilityMatrix
    deviations: List[DeviationReport]
    priority_list: List[Dict]
    completion_suggestions: List[str]
    overall_assessment: str


class RequirementParser:
    """
    需求解析器

    工作流：
    1. parse_text()        → 从自然语言文本提取需求
    2. extract_keywords()  → 提取关键词
    3. classify_type()     → 分类需求类型
    4. normalize()         → 标准化需求格式
    """

    # 需求类型识别关键词
    TYPE_KEYWORDS = {
        RequirementType.FUNCTIONAL: [
            "功能", "feature", "function", "实现", "提供", "支持",
            "能够", "可以", "should", "must", "shall",
        ],
        RequirementType.NON_FUNCTIONAL: [
            "性能", "performance", "响应", "response", "并发", "concurrent",
            "可用", "availability", "安全", "security", "可靠", "reliability",
            "吞吐", "throughput", "延迟", "latency",
        ],
        RequirementType.BUSINESS_RULE: [
            "规则", "rule", "计算", "calculate", "校验", "validate",
            "折扣", "discount", "税率", "tax", "权限", "permission",
        ],
        RequirementType.CONSTRAINT: [
            "约束", "constraint", "限制", "limit", "必须", "required",
            "不能", "cannot", "禁止", "prohibit", "仅限", "only",
        ],
    }

    def parse_text(self, text: str) -> List[Requirement]:
        """
        从自然语言文本中提取需求列表

        支持格式：
        - 编号列表（FR-001: 描述）
        - 项目符号（- 需求描述）
        - 用户故事（As a... I want... So that...）
        - 验收标准（Given... When... Then...）

        参数：
            text: 需求文本

        返回：
            需求列表
        """
        requirements = []

        # 尝试匹配编号格式
        numbered_pattern = re.compile(
            r"(FR|NFR|BR|CN)[-_](\d+)[:\s]+(.+?)(?=(?:FR|NFR|BR|CN)[-_]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        numbered_matches = numbered_pattern.findall(text)
        if numbered_matches:
            for prefix, num, desc in numbered_matches:
                req_type = self._map_prefix(prefix.upper())
                requirements.append(self._create_requirement(
                    f"{prefix.upper()}-{num}", req_type, desc.strip()
                ))
            return requirements

        # 尝试匹配项目符号格式
        bullet_pattern = re.compile(
            r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+(.+?)(?=\n\s*(?:[-*•]|\d+[.)])|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        bullet_matches = bullet_pattern.findall(text)
        if bullet_matches:
            for i, desc in enumerate(bullet_matches):
                desc = desc.strip()
                if desc:
                    req_type = self.classify_type(desc)
                    requirements.append(self._create_requirement(
                        f"{req_type.value}-{i+1:03d}", req_type, desc
                    ))
            return requirements

        # 尝试匹配用户故事格式
        user_story_pattern = re.compile(
            r"As\s+(?:an?\s+)?(.+?),\s*I\s+(?:want|need|would like)\s+to\s+(.+?)"
            r"(?:,\s*so\s+that\s+(.+?))?(?:\.|$)",
            re.IGNORECASE,
        )
        user_stories = user_story_pattern.findall(text)
        if user_stories:
            for i, (role, action, reason) in enumerate(user_stories):
                desc = f"作为{role.strip()}，我需要{action.strip()}"
                if reason:
                    desc += f"，以便{reason.strip()}"
                requirements.append(self._create_requirement(
                    f"FR-{i+1:03d}", RequirementType.FUNCTIONAL, desc
                ))
            return requirements

        # 回退：按句子分割
        sentences = re.split(r"[。.!！?\n]+", text)
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:
                req_type = self.classify_type(sentence)
                requirements.append(self._create_requirement(
                    f"{req_type.value}-{i+1:03d}", req_type, sentence
                ))

        return requirements

    def _map_prefix(self, prefix: str) -> RequirementType:
        mapping = {
            "FR": RequirementType.FUNCTIONAL,
            "NFR": RequirementType.NON_FUNCTIONAL,
            "BR": RequirementType.BUSINESS_RULE,
            "CN": RequirementType.CONSTRAINT,
        }
        return mapping.get(prefix, RequirementType.FUNCTIONAL)

    def _create_requirement(self, req_id: str, req_type: RequirementType,
                             description: str) -> Requirement:
        keywords = self.extract_keywords(description)
        return Requirement(
            req_id=req_id,
            req_type=req_type,
            description=description,
            keywords=keywords,
            acceptance_criteria=[],
        )

    def extract_keywords(self, text: str) -> List[str]:
        """
        从需求文本提取关键词

        使用简单的 NLP 预处理：
        1. 分词（按空格和标点）
        2. 去除停用词
        3. 提取名词和动词短语

        参数：
            text: 需求文本

        返回：
            关键词列表
        """
        # 停用词
        stopwords = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "the", "a", "an",
            "is", "are", "was", "were", "be", "been", "being", "have",
            "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "through",
        }

        # 分词（中英文混合）
        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z_]\w*", text.lower())

        # 过滤停用词和短词
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        # 合并相邻英文词为短语
        phrases = []
        i = 0
        kw_len = len(keywords)
        while i < kw_len:
            kw = keywords[i]
            if re.match(r"[a-z]", kw) and i + 1 < kw_len:
                nxt = keywords[i + 1]
                if re.match(r"[a-z]", nxt):
                    phrases.append(f"{kw}_{nxt}")
                    i += 2
                    continue
            phrases.append(kw)
            i += 1

        # 中文分词处理
        if re.search(r'[\u4e00-\u9fff]', text):
            chinese_tokens = self._tokenize_chinese(text)
            for ct in chinese_tokens:
                if ct not in phrases:
                    phrases.append(ct)

        return phrases[:15]

    def classify_type(self, description: str) -> RequirementType:
        """
        根据描述文本分类需求类型

        参数：
            description: 需求描述

        返回：
            需求类型
        """
        scores = defaultdict(int)
        for req_type, keywords in self.TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in description.lower():
                    scores[req_type] += 1

        if scores:
            return max(scores, key=scores.get)
        return RequirementType.FUNCTIONAL

    def _tokenize_chinese(self, text: str) -> list:
        try:
            import jieba
            tokens = list(jieba.cut(text))
            tokens = [t.strip() for t in tokens if len(t.strip()) >= 2 and re.search(r'[\u4e00-\u9fff]', t)]
            return tokens
        except ImportError:
            # 正向最大匹配（FMM）词典分词
            dictionary = self._load_chinese_dict()
            if dictionary:
                return self._fmm_segment(text, dictionary)

            # 兜底：改进的 bigram + 去重
            clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
            if not clean:
                return []
            tokens = []
            for i in range(len(clean) - 1):
                token = clean[i:i+2]
                if any(c.isdigit() for c in token):
                    continue  # 跳过包含数字的token
                tokens.append(token)
            # 去重，保持顺序
            seen = set()
            result = []
            for t in tokens:
                if t not in seen:
                    seen.add(t)
                    result.append(t)
            return result

    @staticmethod
    def _load_chinese_dict():
        """加载常见中文词表（内置常见软件工程中文词）"""
        return [
            "实现", "功能", "接口", "模块", "系统", "配置", "管理", "支持",
            "处理", "返回", "获取", "设置", "更新", "删除", "创建", "查询",
            "数据", "文件", "目录", "路径", "名称", "版本", "代码", "测试",
            "部署", "构建", "编译", "运行", "启动", "停止", "加载", "保存",
            "分析", "检测", "扫描", "评估", "监控", "跟踪", "日志", "错误",
            "异常", "警告", "信息", "调试", "优化", "重构", "迁移", "升级",
            "用户", "权限", "角色", "组织", "部门", "项目", "任务", "工单",
            "资源", "网络", "安全", "认证", "授权", "加密", "解密", "签名",
            "请求", "响应", "路由", "中间件", "控制器", "模型", "视图", "模板",
            "数据库", "缓存", "队列", "调度", "定时", "异步", "同步",
            "序列化", "反序列", "校验", "验证", "转换", "映射", "绑定", "注入",
            "迭代", "递归", "排序", "查找", "过滤", "聚合", "统计", "计算",
        ]

    def _fmm_segment(self, text: str, dictionary: list) -> list:
        """正向最大匹配（FMM）分词"""
        clean = re.sub(r'[^\u4e00-\u9fff]', '', text)
        if not clean:
            return []
        max_len = max(len(w) for w in dictionary) if dictionary else 4
        max_len = min(max_len, 8)
        tokens = []
        pos = 0
        while pos < len(clean):
            matched = False
            for end in range(min(pos + max_len, len(clean)), pos, -1):
                word = clean[pos:end]
                if word in dictionary:
                    tokens.append(word)
                    pos = end
                    matched = True
                    break
            if not matched:
                pos += 1  # 跳过单个未匹配字符
        # 去重
        seen = set()
        result = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result


class RequirementTracer:
    """
    需求追踪器

    工作流：
    1. parse_requirements()     → 解析需求列表
    2. match_to_codebase()      → 将需求与代码匹配
    3. detect_deviations()      → 检测偏离
    4. detect_implicit()        → 检测暗含实现
    5. generate_matrix()        → 生成追溯矩阵
    6. generate_report()        → 生成评估报告
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.parser = RequirementParser()

    def _tokenize_chinese(self, text: str) -> list:
        return self.parser._tokenize_chinese(text)

    def parse_requirements(self, text: str) -> List[Requirement]:
        return self.parser.parse_text(text)

    def match_to_codebase(self, requirements: List[Requirement]) -> List[Requirement]:
        """
        将需求列表与代码库进行匹配

        匹配策略：
        1. 关键词搜索：在代码中搜索需求关键词
        2. 函数名匹配：检查函数名是否包含关键词
        3. 注释匹配：检查注释/文档是否提及需求
        4. 语义匹配：基于业务逻辑语义推断

        参数：
            requirements: 需求列表

        返回：
            更新了状态的 requirements 列表
        """
        # 收集所有源文件
        code_files = list(self.project_root.rglob("*"))
        extensions = {".py", ".java", ".js", ".jsx", ".ts", ".tsx", ".cs", ".cpp", ".h", ".c"}
        exclude = {"node_modules", ".git", "__pycache__", "venv", "target", "build"}
        code_files = [f for f in code_files
                      if f.suffix in extensions
                      and not any(ex in f.parts for ex in exclude)]

        for req in requirements:
            matched_files = []
            matched_details = []

            for file_path in code_files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    logging.getLogger(__name__).warning(f"Failed to read {file_path} for requirement matching")
                    continue

                match_count = 0
                detail_lines = []

                # 关键词匹配
                for kw in req.keywords:
                    kw_clean = kw.replace("_", " ")
                    # 搜索关键词在代码中的出现
                    for match in re.finditer(
                        re.escape(kw_clean), content, re.IGNORECASE
                    ):
                        line_num = content[:match.start()].count("\n") + 1
                        context = content.split("\n")[line_num - 1].strip()[:80]
                        detail_lines.append(f"L{line_num}: {context}")
                        match_count += 1

                    # 也搜索函数名匹配
                    func_pattern = re.compile(
                        rf"(?:def|function|class)\s+\w*{re.escape(kw_clean)}\w*",
                        re.IGNORECASE,
                    )
                    for match in func_pattern.finditer(content):
                        line_num = content[:match.start()].count("\n") + 1
                        detail_lines.append(
                            f"L{line_num}: 函数/类匹配 `{match.group()}`"
                        )
                        match_count += 1

                if match_count > 0:
                    matched_files.append(str(file_path.relative_to(self.project_root)))
                    matched_details.extend(detail_lines[:3])

            # 判定实现状态
            req.matched_locations = matched_details[:5]

            if len(matched_files) >= 2 and len(matched_details) >= 5:
                req.status = RequirementStatus.IMPLEMENTED
                req.implementation_notes = f"在 {len(matched_files)} 个文件中找到相关实现"
            elif len(matched_files) >= 1:
                req.status = RequirementStatus.PARTIALLY
                req.implementation_notes = (
                    f"仅在 {matched_files[0]} 中找到部分实现，"
                    f"匹配关键词: {req.keywords[:3]}"
                )
            else:
                req.status = RequirementStatus.NOT_IMPLEMENTED
                req.implementation_notes = "未在代码库中找到对应实现"

        return requirements

    def detect_deviations(self, requirements: List[Requirement]) -> List[DeviationReport]:
        """
        检测需求与实现之间的偏离

        检查：
        - 实现方式与描述不符
        - 缺失的关键逻辑
        - 额外未定义的代码

        参数：
            requirements: 已匹配的需求列表

        返回：
            偏离报告列表
        """
        deviations = []

        for req in requirements:
            if req.status == RequirementStatus.PARTIALLY:
                # 检查部分实现的具体缺失
                missing_keywords = []
                for kw in req.keywords:
                    found = any(kw.replace("_", " ").lower() in loc.lower()
                                for loc in req.matched_locations)
                    if not found:
                        missing_keywords.append(kw)

                if missing_keywords:
                    deviations.append(DeviationReport(
                        req_id=req.req_id,
                        expected=req.description,
                        actual=f"缺少关键词: {missing_keywords}",
                        deviation_level="medium",
                        impact=f"功能 {req.req_id} 未完整实现，可能影响业务流程",
                    ))

            elif req.status == RequirementStatus.NOT_IMPLEMENTED:
                deviations.append(DeviationReport(
                    req_id=req.req_id,
                    expected=req.description,
                    actual="代码库中未找到对应实现",
                    deviation_level="high",
                    impact=f"功能 {req.req_id} 完全缺失，可能导致业务流程中断",
                ))

        return deviations

    def detect_implicit_implementations(self,
                                         requirements: List[Requirement]) -> List[Requirement]:
        """
        检测暗含实现

        暗含实现：代码中存在某个功能的完整实现，
        但需求文档未显式声明。

        策略：
        1. 查找代码中实现了但不在需求列表中的功能
        2. 基于函数名和注释语义推断

        参数：
            requirements: 需求列表

        返回：
            更新后的 requirements（含暗含实现标记）
        """
        # 收集所有已匹配的功能
        matched_functions = set()
        for req in requirements:
            for loc in req.matched_locations:
                func_match = re.search(r"函数/类匹配 `(\w+)`", loc)
                if func_match:
                    matched_functions.add(func_match.group(1))

        # 扫描代码中未匹配但有业务含义的函数
        code_files = list(self.project_root.rglob("*.py"))
        exclude = {"__pycache__", "venv", "tests", "test"}
        code_files = [f for f in code_files
                      if not any(ex in f.parts for ex in exclude)]

        implicit_candidates = []
        for file_path in code_files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                logging.getLogger(__name__).warning(f"Failed to read {file_path} for implicit implementation detection")
                continue

            # 查找导出级别的函数
            func_pattern = re.compile(
                r"^def\s+(\w+)\s*\([^)]*\)\s*(?:->.*?)?:\s*\n\s*\"\"\"([^\"]*)\"\"\"",
                re.MULTILINE,
            )
            for match in func_pattern.finditer(content):
                func_name = match.group(1)
                docstring = match.group(2)

                # 跳过测试和私有函数
                if func_name.startswith("_") or func_name.startswith("test"):
                    continue

                # 检查是否已被匹配
                if func_name not in matched_functions:
                    implicit_candidates.append({
                        "function": func_name,
                        "docstring": docstring.strip(),
                        "file": str(file_path.relative_to(self.project_root)),
                    })

        # 将显著的暗含实现添加到需求列表
        for candidate in implicit_candidates[:3]:  # 限制数量
            desc = f"暗含实现：{candidate['function']} — {candidate['docstring'][:80]}"
            keywords = self.parser.extract_keywords(desc)

            implicit_req = Requirement(
                req_id=f"IMPLICIT-{len(requirements)+1:03d}",
                req_type=RequirementType.FUNCTIONAL,
                description=desc,
                keywords=keywords,
                acceptance_criteria=[],
                status=RequirementStatus.IMPLICIT,
                matched_locations=[f"{candidate['file']}: {candidate['function']}"],
                implementation_notes="此功能已实现但需求文档未显式声明",
            )
            requirements.append(implicit_req)

        return requirements

    def generate_matrix(self, requirements: List[Requirement]) -> RequirementTraceabilityMatrix:
        """
        生成需求追溯矩阵

        参数：
            requirements: 需求列表

        返回：
            需求追溯矩阵
        """
        total = len(requirements)
        implemented = sum(1 for r in requirements
                          if r.status == RequirementStatus.IMPLEMENTED)
        partially = sum(1 for r in requirements
                        if r.status == RequirementStatus.PARTIALLY)
        not_impl = sum(1 for r in requirements
                       if r.status == RequirementStatus.NOT_IMPLEMENTED)
        implicit = sum(1 for r in requirements
                       if r.status == RequirementStatus.IMPLICIT)

        coverage = (implemented + partially) / max(total - implicit, 1) * 100

        return RequirementTraceabilityMatrix(
            project_name=self.project_root.name,
            requirements=requirements,
            total_count=total,
            implemented_count=implemented,
            partially_count=partially,
            not_implemented_count=not_impl,
            implicit_count=implicit,
            coverage_rate=round(coverage, 1),
        )

    def generate_priority_list(self,
                                requirements: List[Requirement]) -> List[Dict]:
        """
        生成缺失功能优先级清单

        优先级规则：
        - P0: 核心功能缺失（FR 类型 + 高关键词密度）
        - P1: 重要功能部分缺失
        - P2: 非关键功能缺失

        参数：
            requirements: 需求列表

        返回：
            优先级排序的功能清单
        """
        priority_list = []

        for req in requirements:
            if req.status == RequirementStatus.IMPLEMENTED:
                continue

            priority = "P2"
            cost = "低"
            impact_scope = "局部"

            if req.status == RequirementStatus.NOT_IMPLEMENTED:
                if req.req_type == RequirementType.FUNCTIONAL:
                    priority = "P0"
                    cost = "高"
                    impact_scope = "核心业务流程"
                elif req.req_type == RequirementType.BUSINESS_RULE:
                    priority = "P1"
                    cost = "中"
                    impact_scope = "业务规则执行"
                else:
                    priority = "P2"
                    cost = "低"
                    impact_scope = "非关键功能"
            elif req.status == RequirementStatus.PARTIALLY:
                priority = "P1"
                cost = "中"
                impact_scope = "功能完整性"

            priority_list.append({
                "priority": priority,
                "req_id": req.req_id,
                "description": req.description[:80],
                "status": req.status.value,
                "cost": cost,
                "impact": impact_scope,
            })

        # 排序：P0 → P1 → P2
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        return sorted(priority_list, key=lambda x: priority_order.get(x["priority"], 99))

    def generate_completion_suggestions(self,
                                         requirements: List[Requirement],
                                         deviations: List[DeviationReport]) -> List[str]:
        """
        生成补全建议

        参数：
            requirements: 需求列表
            deviations: 偏离列表

        返回：
            补全建议列表
        """
        suggestions = []

        # P0 级建议
        p0_items = [r for r in requirements
                    if r.status == RequirementStatus.NOT_IMPLEMENTED
                    and r.req_type == RequirementType.FUNCTIONAL]
        if p0_items:
            suggestions.append(
                f"优先补全 {len(p0_items)} 个核心功能："
                f"{', '.join(r.req_id for r in p0_items[:3])}"
            )

        # P1 级建议
        partials = [r for r in requirements
                    if r.status == RequirementStatus.PARTIALLY]
        if partials:
            suggestions.append(
                f"增强 {len(partials)} 个部分实现的功能："
                f"{', '.join(r.req_id for r in partials[:3])}"
            )

        # 偏离修正
        if deviations:
            high_devs = [d for d in deviations if d.deviation_level == "high"]
            if high_devs:
                suggestions.append(
                    f"修正 {len(high_devs)} 个严重偏离："
                    f"{', '.join(d.req_id for d in high_devs[:3])}"
                )

        # 暗含实现确认
        implicit = [r for r in requirements
                    if r.status == RequirementStatus.IMPLICIT]
        if implicit:
            suggestions.append(
                f"确认 {len(implicit)} 个暗含实现，建议更新需求文档以覆盖"
            )

        # 通用建议
        suggestions.append("建议建立需求-代码的双向追溯机制，确保后续变更的可追踪性")

        return suggestions

    def run_full_assessment(self, requirements_text: str) -> TargetAssessmentReport:
        """
        执行完整的目标性评估

        参数：
            requirements_text: 用户提供的需求文本

        返回：
            目标评估报告
        """
        # 解析需求
        requirements = self.parse_requirements(requirements_text)

        # 匹配代码
        requirements = self.match_to_codebase(requirements)

        # 检测偏离
        deviations = self.detect_deviations(requirements)

        # 检测暗含实现
        requirements = self.detect_implicit_implementations(requirements)

        # 生成矩阵
        matrix = self.generate_matrix(requirements)

        # 生成优先级
        priority_list = self.generate_priority_list(requirements)

        # 生成建议
        suggestions = self.generate_completion_suggestions(requirements, deviations)

        # 总体评估
        if matrix.coverage_rate >= 90:
            overall = "代码实现与需求高度匹配，项目处于健康状态"
        elif matrix.coverage_rate >= 70:
            overall = "大部分需求已实现，存在部分缺失和偏离需要关注"
        elif matrix.coverage_rate >= 50:
            overall = "约半数需求已实现，建议优先补全核心功能"
        else:
            overall = "需求覆盖率较低，代码实现与原始目标存在显著差距"

        return TargetAssessmentReport(
            matrix=matrix,
            deviations=deviations,
            priority_list=priority_list,
            completion_suggestions=suggestions,
            overall_assessment=overall,
        )


# ============================================================
# 入口函数
# ============================================================

def trace_requirements(project_root: str,
                        requirements_text: str) -> TargetAssessmentReport:
    """
    模块 8 入口函数

    参数：
        project_root: 项目根目录
        requirements_text: 需求文本

    返回：
        目标评估报告
    """
    tracer = RequirementTracer(project_root)
    return tracer.run_full_assessment(requirements_text)