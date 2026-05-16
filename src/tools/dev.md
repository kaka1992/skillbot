# 通用 Python Tool 框架

## 设计目标

提供一套标准的 tool 接口与注册机制，支持：

- **接口与实现分离** — `ToolPreset` 定义工具契约（名称、参数 schema、返回值），`ToolDef` 绑定具体实现
- **多实现共存** — 同一 preset 下可注册多个实现（如 `"default"` / `"databricks"`），通过偏好机制路由
- **动态发现** — `discover()` 自动扫描目录加载 tool 模块
- **装饰器注册** — `@register` 全量注册，`@impl` preset 绑定注册

## Python API

```python
from tools import ToolRegistry, ToolPreset, ToolResult, register, impl

# ---- 定义接口 ----
ANALYZE = ToolPreset(
    name="analyze",
    description="Analyze a SQL query",
    parameters={
        "type": "object",
        "properties": {"sql": {"type": "string"}},
        "required": ["sql"],
    },
    group="spark",
)

# ---- 注册默认实现 ----
@impl(ANALYZE)
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

# reset
ToolRegistry.reset_preferred()                   # → 回到 default
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
│  ToolDef = ToolPreset + execute                     │
│  一个 preset 可有多个 ToolDef（不同 impl_name）        │
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
│  discover(path)                                     │
└─────────────────────────────────────────────────────┘
```

## 文件结构

```
src/tools/
├── __init__.py              # 导出: ToolDef, ToolPreset, ToolRegistry, ToolResult, impl, register
├── interface.py             # ToolResult + ToolPreset + ToolDef 数据模型
├── registry.py              # ToolRegistry + @register + @impl 装饰器
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
    name: str                  # 工具名称（全局唯一）
    description: str           # 工具描述（给 LLM 阅读）
    parameters: dict[str, Any] # JSON Schema 参数定义
    returns: dict[str, str]    # 返回值 key → 类型提示
    group: str = "custom"      # 分组（用于批量查询 / 偏好设置）
```

### ToolDef

```python
@dataclass
class ToolDef:
    preset: ToolPreset         # 绑定的接口
    execute: Callable[[dict], Coroutine]  # 实现函数

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
    register_impl(preset_name: str, impl_name: str, execute: Callable) -> ToolDef
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
| `ToolRegistry.register_preset()` + `register_impl()` | 手动注册（非装饰器场景） | 动态生成工具 |

`@register` 内部自动创建 `ToolPreset` 并调用 `ToolRegistry.add()`，接口与实现不分离。
`@impl` 接收一个已定义的 `ToolPreset`，仅负责绑定实现。

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

## 偏好机制

```python
# 单个 preset 偏好
ToolRegistry.set_preferred("spark_analyze_query", "databricks")

# 整组偏好（所有 group="spark" 的 preset 统一切换）
ToolRegistry.set_preferred_for_group("spark", "databricks")

# 查询当前偏好
ToolRegistry.get_preferred("spark_analyze_query")  # → "databricks"

# 重置
ToolRegistry.reset_preferred("spark_analyze_query")  # 单重置
ToolRegistry.reset_preferred()                        # 全部重置
```

`set_preferred` 的前置条件：preset 和 impl 必须已注册，否则抛出 `KeyError`。

## discover 机制

`discover(path)` 扫描目录下所有不以 `_` 开头的 `.py` 文件，`importlib.import_module` 导入。

被跳过：`_spark_sql_presets.py`、`__init__.py`（但不是通过 `_` 前缀，而是 `discover` 内部只取 `.stem`）

```python
new_tools = ToolRegistry.discover("src/tools/builtin")
# 返回本次 discover 新注册的 ToolDef 列表
```

## Spark SQL 集成示例

### 定义接口（`_spark_sql_presets.py`）

```python
from tools.interface import ToolPreset

SPARK_ANALYZE_QUERY = ToolPreset(
    name="spark_analyze_query",
    description="Validate a Spark SQL query and show its execution plan",
    parameters={...},
    group="spark",
)
```

### 默认实现（`spark_sql.py`）

```python
from tools import impl
from tools.builtin._spark_sql_presets import SPARK_ANALYZE_QUERY

@impl(SPARK_ANALYZE_QUERY)
async def spark_analyze_query(params: dict) -> ToolResult:
    spark = _get_spark()
    ...
```

### 备选实现（外部模块）

```python
from tools import ToolRegistry, impl
from tools.builtin._spark_sql_presets import SPARK_ANALYZE_QUERY

@impl(SPARK_ANALYZE_QUERY, impl_name="databricks")
async def databricks_analyze(params: dict) -> ToolResult:
    ...
```

### 消费者选择

```python
from tools import ToolRegistry

# 方式 A: 显式指定
tool = ToolRegistry.get("spark_analyze_query", impl="databricks")

# 方式 B: 全局偏好
ToolRegistry.set_preferred_for_group("spark", "databricks")
tool = ToolRegistry.get("spark_analyze_query")  # → databricks
```

## 测试

### 测试文件结构

```
tests/tools/
├── test_registry.py       # ToolRegistry 注册 / 查询 / 偏好 / discover
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
| 显式 impl="default" 忽略偏好 | `test_registry.py::TestPreferredImpl` |
| 偏好不存在的 preset/impl 抛错 | `test_registry.py::TestPreferredImpl` |
| spark_analyze_query 返回执行计划 | `test_spark_sql.py` |
| spark_submit_query 异步提交 | `test_spark_sql.py` |
| spark_get_job_status 状态查询 | `test_spark_sql.py` |
| spark_get_query_result 结果获取 | `test_spark_sql.py` |
| spark_download_result_file CSV 导出 | `test_spark_sql.py` |
| spark_cancel_job 取消查询 | `test_spark_sql.py` |

### 运行测试

```bash
cd $PROJECT_DIR
pytest tests/tools/ -v
```

测试无需外部依赖（spark_sql 测试通过 mock 模拟 pyspark）。

## 【troubleshooting】

- **discover 没有加载我的工具** → 检查文件名是否以 `_` 开头（会被跳过），确认模块 import 时内部调用了 `@register` / `@impl` / `ToolRegistry.register_*`
- **`set_preferred` 抛出 `KeyError`** → preset 或 impl 必须先注册。确保 `discover()` 或 `register_preset()` + `register_impl()` 已执行
- **`get("x", impl="default")` 仍然返回偏好实现** → 显式传 `impl="default"` 会绕过偏好。如果仍需默认，确认调用方式正确
- **`@impl(PRESET)` 后 `get()` 返回 None** → 检查 `ToolRegistry.get()` 是否传了 `impl` 参数。`@impl(PRESET)` 注册为 `"default"` 实现，`@impl(PRESET, impl_name="v2")` 注册为命名实现
