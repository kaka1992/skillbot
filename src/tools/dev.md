# 通用 Python Tool 框架

## 设计目标

提供一套标准的 tool 接口与注册机制，支持：

- **接口与实现分离** — `ToolPreset` 定义工具契约（名称、参数 schema、返回值），`ToolDef` 绑定具体实现
- **多实现共存** — 同一 preset 下可注册多个实现（如 `"default"` / `"databricks"`），通过偏好机制路由
- **运行时依赖检查** — `ToolRequirement` 声明 env / import 依赖，`discover()` 启动时自动检测并跳过不可用工具
- **动态发现** — `discover()` 自动扫描目录加载 tool 模块，输出冲突检测 warning
- **装饰器注册** — `@register` 全量注册，`@impl` preset 绑定注册

## Python API

```python
from tools import ToolRegistry, ToolPreset, ToolResult, ToolRequirement, ReturnProperty, register, impl

# ---- 定义接口 ----
ANALYZE = ToolPreset(
    name="analyze",
    description="Analyze a SQL query",
    parameters={
        "type": "object",
        "properties": {"sql": {"type": "str", "description": "SQL statement"}},
        "required": ["sql"],
    },
    returns={
        "plan": ReturnProperty(type="str", description="Execution plan"),
    },
    group="spark",
)

# ---- 注册默认实现（带运行时依赖） ----
@impl(ANALYZE, requires=[
    ToolRequirement(type="env", key="SPARK_REMOTE", description="Spark Connect endpoint"),
    ToolRequirement(type="import", key="pyspark", description="PySpark library"),
])
async def analyze_query(params: dict) -> ToolResult:
    return ToolResult(data={"plan": "..."})

# ---- 注册备选实现 ----
@impl(ANALYZE, impl_name="databricks")
async def analyze_databricks(params: dict) -> ToolResult:
    return ToolResult(data={"plan": "[Databricks] ..."})

# ---- 查询 ----
tool = ToolRegistry.get("analyze")               # → 默认实现
tool = ToolRegistry.get("analyze", impl="databricks")  # → 指定实现

# ---- 偏好切换 ----
ToolRegistry.set_preferred_for_group("spark", "databricks")
tool = ToolRegistry.get("analyze")               # → 自动路由到 databricks

# ---- 依赖检查 ----
ToolRegistry.check_all()                         # → {tool_name: [errors]} 或 {}
errors = tool.check_requirements()               # → [error_msg, ...]
```

## 架构

```
┌─────────────────────────────────────────────────────┐
│  ToolPreset (接口)                                   │
│  name, description, parameters, returns, group      │
│  纯数据，零依赖                                       │
└──────────┬──────────────────────────────────────────┘
           │ 1:N 绑定
           ▼
┌─────────────────────────────────────────────────────┐
│  ToolDef = ToolPreset + execute + requires           │
│  一个 preset 可有多个 ToolDef（不同 impl_name）        │
│  requires: list[ToolRequirement] 运行时依赖           │
│  check_requirements() → list[str]                    │
└──────────┬──────────────────────────────────────────┘
           │ 注册到
           ▼
┌─────────────────────────────────────────────────────┐
│  ToolRegistry                                       │
│  _presets:       name → ToolPreset                  │
│  _implementations: name → {impl_name → ToolDef}     │
│  _preferred:     name → impl_name (路由偏好)         │
│                                                     │
│  register_preset()  /  register_impl()              │
│  get(name, impl)    /  list(group)                  │
│  set_preferred()    /  reset_preferred()            │
│  check_all()        /  discover(path)               │
└─────────────────────────────────────────────────────┘
```

## 文件结构

```
src/tools/
├── __init__.py              # 导出: ToolDef, ToolPreset, ToolRegistry, ToolResult,
│                            #       ToolRequirement, ReturnProperty, impl, register
├── interface.py             # ToolResult + ToolPreset + ToolDef + ReturnProperty
│                            #   + ToolRequirement + ParamProperty + ParamsSchema
├── registry.py              # ToolRegistry + @register + @impl 装饰器
│                            #   + _wrap_with_defaults + _warn_discover_conflicts
├── builtin/
│   ├── __init__.py
│   ├── _spark_sql_presets.py  # Spark SQL 接口定义（纯 preset，discover 跳过）
│   ├── spark_sql.py           # Spark SQL 默认 PySpark 实现
│   ├── file_read.py           # 内置文件读取工具
│   ├── json_extract.py        # 内置 JSON 提取工具
│   └── web_search.py          # 内置网页搜索工具
└── dev.md                    # 设计文档
```

## 核心接口

### ToolResult

```python
@dataclass
class ToolResult:
    data: dict[str, Any]       # 成功时的返回数据
    error: str | None = None   # 失败时的错误信息
```

### ToolPreset

```python
@dataclass
class ToolPreset:
    name: str                                      # 工具名称（全局唯一）
    description: str                               # 工具描述（给 LLM 阅读）
    parameters: ParamsSchema                       # JSON Schema 参数定义
    returns: dict[str, ReturnProperty]             # 返回值 schema
    group: str = "custom"                          # 分组（用于批量查询 / 偏好设置）
```

### ReturnProperty

```python
@dataclass
class ReturnProperty:
    type: str                                      # "str" | "int" | "float" | "bool" | "array" | "object"
    description: str = ""                          # 字段说明
    items: ReturnProperty | None = None            # array 元素 schema
    properties: dict[str, ReturnProperty] | None = None  # object 嵌套字段
```

### ToolRequirement

```python
@dataclass
class ToolRequirement:
    type: str                                      # "env" | "import"
    key: str                                       # env var name / package name
    description: str = ""                          # human-readable，显示在 error 中
```

### ToolDef

```python
@dataclass
class ToolDef:
    preset: ToolPreset
    execute: Callable[[dict], Coroutine]
    requires: list[ToolRequirement] = field(default_factory=list)

    def check_requirements(self) -> list[str]: ...

    # backward-compat 属性（委托到 preset）
    name: str                  # → preset.name
    description: str           # → preset.description
    parameters: dict           # → preset.parameters
    group: str                 # → preset.group
```

### ToolRegistry

```python
class ToolRegistry:
    # 注册
    register_preset(preset: ToolPreset) -> None
    register_impl(preset_name: str, impl_name: str, execute: Callable,
                  requires: list[ToolRequirement] | None = None) -> ToolDef
    add(tool: ToolDef) -> None           # 兼容旧 @register 装饰器

    # 查询
    get(name: str, impl: str | None = None) -> ToolDef | None
    list(group: str | None = None) -> list[ToolDef]
    list_presets(group: str | None = None) -> list[ToolPreset]
    list_impls(preset_name: str) -> list[str]
    get_preset(name: str) -> ToolPreset | None

    # 偏好
    set_preferred(preset_name: str, impl_name: str) -> None
    set_preferred_for_group(group: str, impl_name: str) -> None
    get_preferred(preset_name: str) -> str | None
    reset_preferred(preset_name: str | None = None) -> None

    # 依赖
    check_all() -> dict[str, list[str]]

    # 生命周期
    remove(name: str) -> bool
    clear() -> None
    discover(path: str) -> list[ToolDef]
```

## 注册方式对比

| 方式 | 使用场景 | 示例 |
|------|---------|------|
| `@register(name=, description=, parameters=)` | 简单工具，只有一种实现 | `@register(name="read", ...)` |
| `@impl(PRESET)` | preset 已定义，绑定默认实现 | `@impl(SPARK_ANALYZE_QUERY)` |
| `@impl(PRESET, impl_name="v2")` | preset 的备选实现 | `@impl(PRESET, impl_name="databricks")` |
| `@impl(PRESET, requires=[...])` | 声明运行时依赖 | `@impl(PRESET, requires=[ToolRequirement(...)])` |
| `ToolRegistry.register_preset()` + `register_impl()` | 手动注册（非装饰器场景） | 动态生成工具 |

## get() 路由规则

| 调用 | 有偏好 | 无偏好 |
|------|--------|--------|
| `get("t")` | 返回偏好实现 | 返回 default（`_tools[name]`） |
| `get("t", impl="default")` | 强制返回 default，忽略偏好 | 返回 default |
| `get("t", impl="databricks")` | 返回 databricks | 返回 databricks |

规则总结：
- `impl=None`（未传）→ 尊重 `_preferred`，无偏好则回退到 `"default"`
- `impl="default"` → 显式指定默认，**绕过**偏好机制
- `impl="<name>"` → 精确查找，不走偏好

## 运行时依赖检查

```python
# 声明依赖
@impl(SPARK_ANALYZE_QUERY, requires=[
    ToolRequirement(type="env", key="SPARK_REMOTE", description="Spark Connect endpoint"),
    ToolRequirement(type="import", key="pyspark", description="PySpark library"),
])

# discover() 自动检查
ToolRegistry.discover("src/tools/builtin")
# [ToolRegistry] spark_analyze_query skipped due to missing dependencies:
#   - env var 'SPARK_REMOTE' is not set (Spark Connect endpoint)

# 编程式查询
ToolRegistry.check_all()          # → {tool_name: [errors]}

# 单个 tool 检查
tool.check_requirements()         # → [] (ok) or [error_msg, ...]
```

同组多个 tool 共享依赖声明：
```python
_SPARK_REQUIRES = [
    ToolRequirement(type="env", key="SPARK_REMOTE", description="Spark Connect endpoint"),
    ToolRequirement(type="import", key="pyspark", description="PySpark library"),
]

@impl(SPARK_ANALYZE_QUERY, requires=_SPARK_REQUIRES)
async def spark_analyze_query(params): ...

@impl(SPARK_SUBMIT_QUERY, requires=_SPARK_REQUIRES)
async def spark_submit_query(params): ...
```

## discover 机制

`discover(path)` 扫描目录下所有不以 `_` 开头的 `.py` 文件，`importlib.import_module` 导入。

被跳过：`_spark_sql_presets.py`、`__init__.py`

discover 末尾自动执行：
1. `check_requirements()` → 不满足的 tool 打印 warning 并移除
2. `_warn_discover_conflicts()` → 检测重名冲突

### 冲突检测

| 冲突类型 | 行为 |
|---------|------|
| preset 重名（同一 name 被多个模块注册） | stderr warning，后者覆盖 |
| group/preset 名碰撞（group 名与另一个 preset name 相同） | stderr warning，提示使用 explicit presets:/groups: |

## Spark SQL 集成示例

### 定义接口（`_spark_sql_presets.py`）

```python
from tools.interface import ReturnProperty, ToolPreset

SPARK_GET_QUERY_RESULT = ToolPreset(
    name="spark_get_query_result",
    description="Get the result rows of a completed Spark query",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "str", "description": "Job ID"},
            "limit": {"type": "int", "description": "Max rows", "default": 100},
        },
        "required": ["job_id"],
    },
    returns={
        "success": ReturnProperty(type="str"),
        "command": ReturnProperty(type="str"),
        "data": ReturnProperty(type="object", properties={
            "sample_data": ReturnProperty(type="array", items=ReturnProperty(type="array",
                items=ReturnProperty(type="str"))),
            "content_row_count": ReturnProperty(type="int"),
        }),
    },
    group="spark",
)
```

### 默认实现 + 备选实现

```python
# spark_sql.py — 默认 PySpark 实现
_SPARK_REQUIRES = [
    ToolRequirement(type="env", key="SPARK_REMOTE", description="Spark Connect endpoint"),
    ToolRequirement(type="import", key="pyspark", description="PySpark library"),
]

@impl(SPARK_GET_QUERY_RESULT, requires=_SPARK_REQUIRES)
async def spark_get_query_result(params: dict) -> ToolResult:
    ...

# databricks_tools.py — 第三方 Databricks 实现
@impl(SPARK_GET_QUERY_RESULT, impl_name="databricks")
async def databricks_get_result(params: dict) -> ToolResult:
    ...
```

### 消费者选择

```python
from tools import ToolRegistry

# 加载第三方工具目录
ToolRegistry.discover("/path/to/databricks_tools/")

# 方式 A: 显式指定
tool = ToolRegistry.get("spark_get_query_result", impl="databricks")

# 方式 B: 全局偏好
ToolRegistry.set_preferred_for_group("spark", "databricks")
tool = ToolRegistry.get("spark_get_query_result")  # → databricks
```

## 测试

### 测试文件结构

```
tests/tools/
├── test_registry.py       # ToolRegistry 注册 / 查询 / 偏好 / discover / 依赖
├── test_builtin.py        # 内置工具（file_read, json_extract, web_search）功能测试
└── test_spark_sql.py      # Spark SQL 工具测试（mock pyspark）
```

### 测试覆盖

| 测试场景 | 文件 |
|---------|------|
| ToolDef 创建 & backward-compat 属性 | `test_registry.py::TestToolDef` |
| ToolPreset 创建 & register_preset / register_impl | `test_registry.py::TestToolPreset` |
| ToolPreset list_presets / list_impls | `test_registry.py::TestToolPreset` |
| ToolRegistry add / get / remove / list | `test_registry.py::TestToolRegistry` |
| @register 装饰器注册 & 执行 | `test_registry.py::TestRegisterDecorator` |
| discover 扫描目录 | `test_registry.py::TestDiscover` |
| set_preferred 路由 | `test_registry.py::TestPreferredImpl` |
| set_preferred_for_group 批量 | `test_registry.py::TestPreferredImpl` |
| reset_preferred 回退 | `test_registry.py::TestPreferredImpl` |
| ToolRequirement env/import 检查 | `test_registry.py::TestToolRequirements` |
| check_all 批量依赖检查 | `test_registry.py::TestToolRequirements` |
| 参数 default 值注入 | `test_registry.py::TestParameterDefaults` |
| spark_analyze_query 返回执行计划 | `test_spark_sql.py` |
| spark_submit_query 异步提交 | `test_spark_sql.py` |
| spark_get_job_status 状态查询 | `test_spark_sql.py` |
| spark_get_query_result 结果获取 | `test_spark_sql.py` |
| spark_cancel_job 取消查询 | `test_spark_sql.py` |

### 运行测试

```bash
cd $PROJECT_DIR
pytest tests/tools/ -v
```

测试无需外部依赖（spark_sql 测试通过 mock 模拟 pyspark）。

## 【troubleshooting】

- **discover 没有加载我的工具** → 检查文件名是否以 `_` 开头（会被跳过），确认模块 import 时内部调用了 `@register` / `@impl`
- **discover 加载后工具被跳过** → 检查 `check_requirements()`，确认依赖的 env var / package 已就绪
- **`set_preferred` 抛出 `KeyError`** → preset 或 impl 必须先注册。确保 `discover()` 或 `register_preset()` + `register_impl()` 已执行
- **`get("x", impl="default")` 仍然返回偏好实现** → 显式传 `impl="default"` 会绕过偏好
- **discover 出现 preset name conflict warning** → 同一 preset name 被多个模块注册，检查是否重复加载
- **discover 出现 group/preset collision warning** → group 名与 preset 名冲突，在 preferences 中用 `presets:` / `groups:` 显式区分
