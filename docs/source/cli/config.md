# 配置管理 (`uniqc config`)

管理云平台的 API 密钥和配置。

## 初始化配置

```bash
# 创建默认配置文件
uniqc config init
```

配置文件位置：`~/.uniqc/config.yaml`

## 设置配置项

```bash
# 设置平台 Token
uniqc config set originq.token YOUR_TOKEN
uniqc config set quafu.token YOUR_TOKEN
uniqc config set ibm.token YOUR_TOKEN

# IBM Quantum 如需代理，可以写入嵌套 proxy 配置
uniqc config set ibm.proxy.https http://127.0.0.1:7890
uniqc config set ibm.proxy.http http://127.0.0.1:7890

# 在指定 profile 下设置
uniqc config set originq.token YOUR_TOKEN --profile production
```

`uniqc config set` 会保留同一平台下已有字段；例如设置 `ibm.token` 不会清空 `ibm.proxy`。

## 查看配置

```bash
# 查看特定平台配置
uniqc config get originq

# 列出所有平台配置状态
uniqc config list

# 以 JSON 格式输出
uniqc config list --format json
```

## 验证配置

```bash
# 验证当前配置是否有效
uniqc config validate
```

> **配置文件同时对 CLI 和 Python API 生效**：`~/.uniqc/config.yaml` 中的 token 配置不仅支持 `uniqc config set` 写入的 CLI 命令，也被 Python 云的 `OriginQAdapter`、`QuafuAdapter` 等适配器直接读取（通过 `uniqc config` 模块 fallback）。使用 Python API 时无需额外设置环境变量。

## AI 工作流提示

所有支持 AI 提示的 CLI 命令都可以临时加 `--ai-hints` 或 `--ai-hint`。如果希望 AI agent 每次调用 CLI 时都自动看到下一步提示，可以一键打开默认提示：

```bash
# 默认显示 AI workflow hints
uniqc config always-ai-hint on

# 查看状态
uniqc config always-ai-hint status

# 关闭默认提示
uniqc config always-ai-hint off
```

也可以用环境变量临时开启：

```bash
UNIQC_AI_HINTS=1 uniqc backend list
```

## 配置 Profile 管理

```bash
# 列出所有 profile
uniqc config profile list

# 切换 profile
uniqc config profile use production

# 创建新 profile
uniqc config profile create testing
```
