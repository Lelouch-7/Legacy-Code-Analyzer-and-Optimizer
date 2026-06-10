"""
共享基础层 - Legacy Code Analyzer 统一常量与工具函数
"""

import re
from pathlib import Path
from enum import Enum
from typing import Optional


class Language(Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    UNKNOWN = "unknown"


class DependencyType(Enum):
    EXPLICIT_IMPORT = "explicit_import"
    FUNCTION_CALL = "function_call"
    CLASS_INHERITANCE = "class_inheritance"
    INTERFACE_IMPLEMENTATION = "interface_implementation"
    GLOBAL_VARIABLE = "global_variable"
    ENVIRONMENT_VARIABLE = "environment_variable"
    FILE_SYSTEM = "file_system"
    REFLECTION = "reflection"
    IMPLICIT_CROSS_MODULE = "implicit_cross_module"


# 语言识别特征映射
LANGUAGE_SIGNATURES = {
    Language.PYTHON: {
        "extensions": {".py", ".pyx", ".pyi"},
        "configs": {"requirements.txt", "setup.py", "setup.cfg", "pyproject.toml", "Pipfile"},
        "keywords": [r"^\s*def\s+\w+\s*\(", r"^\s*class\s+\w+.*:", r"^\s*import\s+\w+", r"^\s*from\s+\w+\s+import"],
    },
    Language.JAVA: {
        "extensions": {".java"},
        "configs": {"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"},
        "keywords": [r"public\s+class\s+\w+", r"private\s+\w+\s+\w+;", r"@Override", r"import\s+java\."],
    },
    Language.JAVASCRIPT: {
        "extensions": {".js", ".jsx", ".mjs", ".cjs"},
        "configs": {"package.json"},
        "keywords": [r"const\s+\w+\s*=", r"function\s+\w+\s*\(", r"require\(", r"module\.exports"],
    },
    Language.TYPESCRIPT: {
        "extensions": {".ts", ".tsx"},
        "configs": {"tsconfig.json", "package.json"},
        "keywords": [r"interface\s+\w+\s*\{", r":\s*(string|number|boolean)\b", r"import\s+\{[^}]+\}\s+from"],
    },
    Language.CPP: {
        "extensions": {".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h"},
        "configs": {"CMakeLists.txt", "Makefile"},
        "keywords": [r"#include\s*<", r"std::", r"template\s*<", r"namespace\s+\w+"],
    },
    Language.C: {
        "extensions": {".c", ".h"},
        "configs": {"Makefile"},
        "keywords": [r"#include\s*<", r"printf\(", r"malloc\(", r"typedef\s+struct"],
    },
    Language.CSHARP: {
        "extensions": {".cs"},
        "configs": {"*.csproj", "*.sln"},
        "keywords": [r"using\s+", r"namespace\s+", r"class\s+\w+"],
    },
}

# 排除目录集合
EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv",
                "target", "build", "dist", ".idea", ".vscode", "test", "tests"}

# OWASP Top 10 漏洞检测模式
OWASP_SECURITY_PATTERNS = {
    "A01:2021-Broken Access Control": [
        (r"if\s+True\s*:", "无条件通过的权限检查"),
        (r"@app\.route.*\n\s*def", "缺少 @login_required 装饰器的路由"),
    ],
    "A02:2021-Cryptographic Failures": [
        (r"md5\(", "使用已废弃的 MD5 哈希算法"),
        (r"sha1\(", "使用已废弃的 SHA1 哈希算法"),
        (r"base64\.(?:b64encode|encode)", "Base64 不是加密算法"),
        (r"=\s*['\"][^'\"]*(?:password|secret_key|api_key|token)\b", "硬编码的密钥/凭证"),
    ],
    "A03:2021-Injection": [
        (r"(?:execute|cursor)\(.*\+", "字符串拼接 SQL 查询 — SQL 注入风险"),
        (r"f['\"].*SELECT.*\{", "f-string SQL 查询 — SQL 注入风险"),
        (r"os\.system\(.*\+", "字符串拼接系统命令 — 命令注入风险"),
        (r"subprocess\.call\(.*\+", "字符串拼接子进程调用 — 命令注入风险"),
        (r"eval\(.*\+", "字符串拼接 eval — 代码注入风险"),
        (r"exec\(.*\+", "字符串拼接 exec — 代码注入风险"),
    ],
    "A04:2021-Insecure Design": [
        (r"TODO.*(?:security|auth|encrypt|hash)", "安全相关功能标记为 TODO"),
    ],
    "A05:2021-Security Misconfiguration": [
        (r"DEBUG\s*=\s*True", "生产环境开启 DEBUG 模式"),
        (r"CORS_ORIGIN\w*\s*=\s*['\"].*\*", "CORS 配置允许所有来源"),
    ],
    "A06:2021-Vulnerable Components": [
    ],
    "A07:2021-Authentication Failures": [
        (r"password\s*=\s*['\"][^'\"]+['\"]", "硬编码密码"),
        (r"token\s*=\s*['\"][^'\"]+['\"]", "硬编码 Token"),
        (r"api_key\s*=\s*['\"][^'\"]+['\"]", "硬编码 API Key"),
    ],
    "A08:2021-Software Integrity Failures": [
        (r"pickle\.loads?", "使用不安全的 pickle 反序列化"),
        (r"yaml\.load\(.*(?!SafeLoader)", "使用不安全的 YAML load"),
    ],
    "A09:2021-Logging Failures": [
        (r"except\s*:\s*\n\s*pass\b", "异常被静默吞掉，无日志记录"),
        (r"except\s+Exception\s*:\s*\n\s*pass\b", "宽泛 Exception 被静默吞掉"),
        (r"except\s*:\s*\n\s*$", "空异常处理块"),
    ],
    "A10:2021-SSRF": [
        (r"requests\.get\(.*user", "用户输入直接传入 HTTP 请求 — SSRF 风险"),
        (r"urllib\.request\.urlopen\(.*user", "用户输入直接传入 URL 请求 — SSRF 风险"),
    ],
}

# 过期 API 模式
DEPRECATED_PATTERNS = {
    Language.PYTHON: [
        (r"\.has_key\(", "dict.has_key() → 使用 'in' 操作符"),
        (r"thread\.\w+", "thread 模块 → 使用 threading 模块"),
        (r"commands\.", "commands 模块 → 使用 subprocess 模块"),
    ],
    Language.JAVASCRIPT: [
        (r"var\s+\w+\s*=", "var → 使用 const/let"),
        (r"\.substr\(", ".substr() → 使用 .substring() 或 .slice()"),
        (r"new\s+XMLHttpRequest", "XMLHttpRequest → 使用 fetch API"),
    ],
    Language.JAVA: [
        (r"new\s+Date\(\)", "Date() → 使用 java.time API"),
        (r"Vector\s*<", "Vector → 使用 ArrayList"),
        (r"Hashtable\s*<", "Hashtable → 使用 HashMap"),
    ],
    Language.CSHARP: [
        (r"ArrayList\s*<", "ArrayList → 使用 List<T>"),
        (r"Hashtable\s*<", "Hashtable → 使用 Dictionary<TKey, TValue>"),
        (r"\.DataTable\b", "DataTable → 使用 ORM (Entity Framework)"),
    ],
}

# 各语言的 import/include 模式
IMPORT_PATTERNS = {
    Language.PYTHON: re.compile(
        r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
    ),
    Language.JAVA: re.compile(
        r"^import\s+(?:static\s+)?([\w.]+)", re.MULTILINE
    ),
    Language.JAVASCRIPT: re.compile(
        r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|"
        r"(?:const|let|var)\s+.*?=\s*require\(['\"]([^'\"]+)['\"]\))",
        re.MULTILINE
    ),
    Language.TYPESCRIPT: re.compile(
        r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE
    ),
    Language.CPP: re.compile(
        r'#include\s+[<"]([^>"]+)[>"]', re.MULTILINE
    ),
    Language.CSHARP: re.compile(
        r"^using\s+([\w.]+)", re.MULTILINE
    ),
}

# 隐式依赖检测模式
IMPLICIT_PATTERNS = {
    DependencyType.GLOBAL_VARIABLE: [
        r"(?:global\s+|window\.|GLOBAL_|global_|_global)",
    ],
    DependencyType.ENVIRONMENT_VARIABLE: [
        r"(?:process\.env|os\.environ|System\.getenv|getenv|os\.getenv)",
        r"os\.getenv\s*\(",            # ← 新增
        r"os\.environ\.get\s*\(",      # ← 新增
    ],
    DependencyType.FILE_SYSTEM: [
        r"(?:open\(|fs\.|File\(|fstream|ofstream|ifstream|"
        r"readFile|writeFile|fs\.readFileSync|fs\.writeFileSync)",
    ],
    DependencyType.REFLECTION: [
        r"(?:eval\(|exec\(|reflect|Class\.forName|getattr\(|setattr\(|"
        r"call_user_func|invoke)",
    ],
    "__dynamic_import__": [
        r"__import__\s*\(",              # 动态导入
        r"importlib\.import_module\s*\(",  # importlib
    ],
    "__db_connection__": [
        r"postgresql://",                # PostgreSQL 连接串
        r"mysql://",                     # MySQL 连接串
        r"sqlite://",                    # SQLite 连接串
        r"mongodb://",                   # MongoDB 连接串
        r"redis://",                     # Redis 连接串
        r"jdbc:",                        # JDBC 连接串（Java）
    ],
}


def identify_language(file_path: Path, project_root: Optional[Path] = None) -> Language:
    """
    通过扩展名和内容特征识别编程语言

    优先级：
    1. 文件扩展名精确匹配
    2. 项目配置文件推断

    返回：
        识别到的语言枚举
    """
    ext = file_path.suffix

    for lang, sig in LANGUAGE_SIGNATURES.items():
        if ext in sig["extensions"]:
            return lang

    if project_root is not None:
        for lang, sig in LANGUAGE_SIGNATURES.items():
            for config in sig["configs"]:
                if (project_root / config).exists():
                    return lang

    return Language.UNKNOWN