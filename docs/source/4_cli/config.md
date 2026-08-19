# 配置管理 (`uniqc config`)

管理 UnifiedQuantum 的项目级配置，包括云平台 API 密钥、代理、profile、AI workflow hints 等。

## 初始化配置

```bash
# 创建默认配置文件
uniqc config init
```

配置文件位置：`~/.uniqc/config.yaml`

## Schema 版本与自动迁移

配置文件带有顶层 `config_version` 字段（当前为 `1`），用于标识 schema 版本：

```yaml
config_version: 1
active_profile: default
default:
  originq:
    token: xxx
```

- **自动迁移**：当 uniqc 升级、配置 schema 发生变化时，`load_config`（CLI 与
  Python API 共用）会在读取时自动把旧版配置逐级迁移到当前版本，并尽可能写回
  磁盘（写入失败不影响本次读取）。你不需要手动修改配置文件。
- **无版本号的旧文件**：在引入 schema 版本之前生成的 `config.yaml` 被视为
  v0，首次读取时自动补上 `config_version`（布局不变，现有字段全部保留）。
- **版本过新**：如果配置文件由更新版本的 uniqc 写入（`config_version` 大于
  当前 uniqc 支持的版本），读取会报错并提示升级 uniqc，而不是静默误读。

## 设置配置项

```bash
# 设置平台 Token
uniqc config set originq.token YOUR_TOKEN
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

> **配置文件同时对 CLI 和 Python API 生效**：`~/.uniqc/config.yaml` 中的配置不仅支持 `uniqc config set` 写入的 CLI 命令，也被 Python API 读取。新代码优先使用顶级 `uniqc.config` 模块；旧路径 `uniqc.backend_adapter.config` 仍保留兼容。

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

## 跨机器同步配置

`uniqc sync` 可以把 `~/.uniqc/config.yaml` 中的平台凭据与配置同步到
Infisical 密钥管理平台，用于在多台机器之间共享或恢复凭据：

```bash
uniqc sync setup --project-id <INFISICAL_PROJECT_ID> --env dev
uniqc sync status   # 预览本地与远端差异
uniqc sync push     # 上传（本地优先）
uniqc sync pull     # 下载（远端优先，自动备份）
```

详见[凭据同步 (`uniqc sync`)](sync.md)。

