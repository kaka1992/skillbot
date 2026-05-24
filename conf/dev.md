# 配置说明

## 目录结构

```
conf/
├── .env                        # 全局环境变量（所有 agent 共享）
├── agent_conf/
│   ├── deer-flow/
│   │   ├── config.yaml         # deer-flow 配置
│   │   └── .env                # deer-flow 环境变量（API key）
│   ├── nanobot/
│   │   ├── config.json         # nanobot 配置
│   │   └── .env                # nanobot 环境变量
│   └── hermes-agent/
│       ├── config.yaml         # hermes-agent 配置
│       └── .env                # hermes-agent 环境变量
│   └── claude-code/
│       ├── .env.example        # HTTP server 配置模板
│       └── settings.json       # Claude Code 配置（同步到 agent_path/.claude/）
└── dev.md                      # 本文件
```

> `*.example` 文件来自 agent 官方仓库，仅供参考。**必须复制为正式配置文件才能生效**，详见下方「首次配置」。

## 首次配置

clone 仓库后 `conf/agent_conf/<agent>/` 目录下会包含 `*.example` 文件，
这些是 agent 官方的参考示例。需要将其复制为正式配置文件，并填入自己的 API key：

```bash
# deer-flow
cp conf/agent_conf/deer-flow/config.example.yaml conf/agent_conf/deer-flow/config.yaml
cp conf/agent_conf/deer-flow/.env.example        conf/agent_conf/deer-flow/.env

# nanobot
cp conf/agent_conf/nanobot/config.example.json   conf/agent_conf/nanobot/config.json
cp conf/agent_conf/nanobot/.env.example          conf/agent_conf/nanobot/.env

# hermes-agent
cp conf/agent_conf/hermes-agent/config.example.yaml conf/agent_conf/hermes-agent/config.yaml
cp conf/agent_conf/hermes-agent/.env.example        conf/agent_conf/hermes-agent/.env

# claude-code（配置复制到隔离目录，避免污染 ~/.claude/）
mkdir -p agents/claude-code/.claude
cp conf/agent_conf/claude-code/settings.json agents/claude-code/.claude/settings.json

# 编辑各 .env + config.*，填入 API key
```

配置完成后执行 `run.sh start <agent> <model>`，`cmd_start` 会自动将
`conf/agent_conf/<agent>/*` 同步到 agent 的实际配置目录。

## 加载机制

```
./scripts/run.sh start deer-flow deepseek-v4-flash
       │
       ├── main() → _load_env()        ← 加载 conf/.env（全局）
       │
       └── cmd_start()
             ├── config sync            ← conf/agent_conf/deer-flow/* → agents/deer-flow/
             ├── _set_model_in_config   ← 写入 model 到 config.yaml
             ├── _setup_deps            ← make install
             └── start daemon           ← nohup ...
```

### 全局配置 (conf/.env)

所有 agent 共享的环境变量，`install.sh` 和 `run.sh` 的 `main()` 入口自动加载。

**不会覆盖**已在环境中设置的变量（`_load_env` 逐行读取，跳过已存在的 key）。

```bash
# conf/.env
DEEPSEEK_API_KEY=sk-xxx                # LLM API key（deer-flow/nanobot/hermes 共用）
SKILL_BOT_SKILL_PATH=skills/*          # skill 同步默认路径
SKILL_BOT_SKILL_DIR=/custom/skills     # 可选，覆盖默认源目录
SKILL_BOT_AGENT_INSTALL_DIR=/opt/skillbot/agents  # 可选，覆盖安装目录
```

### Agent 配置 (conf/agent_conf/<agent>/)

`run.sh start` 启动时自动从 `conf/agent_conf/<agent>/` 同步到 agent 的实际配置目录。

| Agent | 模板路径 | 实际配置路径 | 操作 |
|-------|---------|------------|------|
| deer-flow | `conf/agent_conf/deer-flow/config.yaml` + `.env` | `agents/deer-flow/` | `cp` |
| nanobot | `conf/agent_conf/nanobot/config.json` + `.env` | `~/.nanobot/` | `cp` |
| hermes-agent | `conf/agent_conf/hermes-agent/config.yaml` + `.env` | `~/.hermes/` | `cp` |
| claude-code | `conf/agent_conf/claude-code/settings.json` | `${agent_path}/.claude/settings.json` | `cp` |

### 配置优先级

```
1. 命令行参数              run.sh start <agent> <model>
2. Agent .env             conf/agent_conf/<agent>/.env
3. 全局 .env              conf/.env
4. Agent config.yaml/json  conf/agent_conf/<agent>/config.*
```

## 各 Agent 配置要点

### deer-flow

**config.yaml** — `models` 列表配置 LLM provider：

```yaml
models:
  - name: deepseek-v4-flash
    display_name: deepseek-v4-flash
    use: deerflow.models.patched_deepseek:PatchedChatDeepSeek
    model: deepseek-v4-flash
    api_key: $DEEPSEEK_API_KEY
    supports_thinking: true
```

`.env` — API key 通过 `$VAR` 引用：

```bash
DEEPSEEK_API_KEY=sk-xxx
```

`run.sh start deer-flow <model>` 会调用 `sed` 更新 `name` 和 `model` 字段，保留其余配置。

### nanobot

**config.json** — JSON 格式，`${VAR}` 引用环境变量：

```json
{
  "agents": { "defaults": { "model": "deepseek-v4-flash" } },
  "providers": {
    "deepseek": { "apiKey": "${DEEPSEEK_API_KEY}" }
  },
  "tools": {
    "web": {
      "search": { "provider": "tavily" }
    }
  }
}
```

`.env` — API key + 服务配置：

```bash
DEEPSEEK_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx
VITE_GATEWAY_URL=http://localhost:18790
```

### hermes-agent

**config.yaml** — YAML 格式，顶层 `model` 字段：

```yaml
model: deepseek-v4-flash
providers:
  deepseek: {}
```

**注意**：hermes 的 `/v1/chat/completions` API 忽略请求体中的 `model` 参数，实际使用 `~/.hermes/config.yaml` 中的 `model` 字段。切换模型必须通过 `run.sh start hermes-agent <model>` 修改配置文件。

`.env` — API key + 服务开关：

```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=1234
GATEWAY_ALLOW_ALL_USERS=true
DEEPSEEK_API_KEY=sk-xxx
```

### claude-code

Claude Code 通过 `.claude/settings.json` 配置。skillbot 使用 `agents/claude-code/.claude/` 作为隔离目录（由 `get_agent_path` 解析），与 `~/.claude/` 完全隔离。

**settings.json** — 核心配置：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "sk-your-deepseek-api-key",
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "CLAUDE_CODE_EFFORT_LEVEL": "max"
  },
  "alwaysThinkingEnabled": false,
  "permissions": {
    "allow": ["Bash(curl:*)", "Bash(python3:*)", "Bash(git:*)"],
    "deny": ["Bash(rm -rf /*)", "Bash(sudo:*)"]
  }
}
```

| 配置项 | 说明 |
|--------|------|
| `ANTHROPIC_BASE_URL` | 后端 API 地址（DeepSeek/OpenRouter 等兼容端点） |
| `ANTHROPIC_AUTH_TOKEN` | API key |
| `ANTHROPIC_MODEL` | 默认模型 |
| `ANTHROPIC_DEFAULT_*_MODEL` | 各模式对应模型（Opus/Sonnet/Haiku） |
| `CLAUDE_CODE_EFFORT_LEVEL` | 推理强度：min/medium/max |
| `permissions.allow` | 允许的工具白名单 |
| `permissions.deny` | 禁止的工具黑名单 |

配置文件位于 `conf/agent_conf/claude-code/settings.json`，`run.sh start` 会自动同步到 agent 目录。

## 快速配置指南

### 首次配置

```bash
# 1. 设置全局 API key
echo "DEEPSEEK_API_KEY=sk-xxx" >> conf/.env

# 2. 设置 skill 同步路径
echo "SKILL_BOT_SKILL_PATH=skills/*" >> conf/.env

# 3. 在各 agent .env 中填入 API key
echo "DEEPSEEK_API_KEY=sk-xxx" >> conf/agent_conf/deer-flow/.env
echo "DEEPSEEK_API_KEY=sk-xxx" >> conf/agent_conf/nanobot/.env
echo "DEEPSEEK_API_KEY=sk-xxx" >> conf/agent_conf/hermes-agent/.env

# 4. 配置 Claude Code（自动写入 agents/claude-code/.claude/）
run.sh start claude-code                    # 自动同步 config + 启动 HTTP Server

# 5. 安装并启动
install.sh install deer-flow
run.sh start deer-flow deepseek-v4-flash
```

### 切换模型

```bash
# deer-flow / nanobot：REST API 支持动态切换，或通过 run.sh start 修改
run.sh start deer-flow deepseek-v4-flash
run.sh start nanobot deepseek-v4-flash

# hermes-agent：必须通过 run.sh start 修改 config.yaml
run.sh start hermes-agent deepseek-v4-flash

# claude-code：编辑 conf/agent_conf/claude-code/settings.json，重启 server 生效
# "ANTHROPIC_MODEL": "deepseek-v4-flash"
```

### 配置 Web UI / 服务

| Agent | WebUI | 默认端口 | 启动方式 |
|-------|-------|:---:|------|
| deer-flow | Next.js（集成） | 3000 / 2026 | `make dev-daemon` |
| nanobot | Vite | 5173 | `cd webui && npm run dev` |
| hermes-agent | Vite + Dashboard | 5173 / 9119 | `hermes dashboard` + `npm run dev` |
| claude-code | HTTP Server | 9000 | `run.sh start claude-code` |

`run.sh start <agent>` 默认启动全栈（含 WebUI），`--no-webui` 可跳过前端。
