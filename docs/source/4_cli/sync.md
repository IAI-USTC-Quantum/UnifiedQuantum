# 凭据同步 (`uniqc sync`)

在多台机器之间同步 `~/.uniqc/config.yaml` 中的量子真机凭据与平台配置，后端为 [Infisical](https://infisical.com) 密钥管理平台（通过本机 `infisical` CLI 访问）。

## 概述

`uniqc sync` 把配置文件中的平台凭据（以及随之保存的非敏感平台设置，如 `task_group_size`、`available_qubits`、IBM 代理等）扁平化为一组 `UNIQC_` 前缀的 Infisical secrets，从而实现：

- 在一台机器上 `push` 上传凭据，在其他机器上 `pull` 一键恢复；
- 服务器端轮换 token 后，各机器 `pull` 即可拿到新值；
- 项目里其他非 `UNIQC_` 前缀的 secrets 完全不受影响。

| 子命令 | 说明 |
|--------|------|
| `setup` | 保存 Infisical 项目 ID 与默认环境到 `~/.uniqc/config.yaml` 的 `sync` 节 |
| `status` | 对比本地与远端差异（不写入任何内容） |
| `push` | 上传本地配置到 Infisical（**本地优先**，远端同名值被覆盖） |
| `pull` | 下载远端配置覆盖本地（**远端优先**，自动生成时间戳备份） |

## 前置条件

```bash
# 1. 安装 Infisical CLI（https://infisical.com/docs/cli/overview）
# macOS / Linux:
brew install infisical/get-cli/infisical
# 2. 登录
infisical login
```

在 Infisical 中创建一个项目（例如 `uniqc`），记下 Project ID（项目设置页可以看到），建议为凭据使用独立项目或独立环境（`dev` / `staging` / `prod`）。

## 初始设置 (`uniqc sync setup`)

```bash
uniqc sync setup --project-id 8501c316-2ab9-4d44-959d-73fd119b5736 --env dev
```

该命令把同步设置写入配置文件的 `sync` 节（该节属于本机设置，不会被同步）：

```yaml
sync:
  project_id: 8501c316-2ab9-4d44-959d-73fd119b5736
  env: dev
```

也可以不用 `setup`，改用环境变量或命令行参数：

| 优先级 | project_id | env |
|--------|-----------|-----|
| 1（最高） | `--project-id` | `--env` / `-e` |
| 2 | `UNIQC_INFISICAL_PROJECT_ID` | `UNIQC_INFISICAL_ENV` |
| 3 | 配置文件 `sync` 节 | 配置文件 `sync` 节 |
| 默认 | —（缺失时报错） | `dev` |

## 查看差异 (`uniqc sync status`)

```bash
uniqc sync status                # 表格形式
uniqc sync status --format json  # JSON 输出，适合脚本
```

输出分三个视图：

- **Would push**：仅本地存在（`add`）或与远端不同（`update`）的键；
- **Would pull**：仅远端存在或与本地不同的键；
- **Stale on remote**：远端有、本地没有的键——只有 `push --prune` 才会删除它们。

输出只包含配置键名（如 `default.originq.token`），**永远不会打印任何密钥值**。

## 上传凭据 (`uniqc sync push`)

```bash
uniqc sync push                 # 上传新增/变更的键
uniqc sync push --prune         # 同时删除远端已不在本地的 UNIQC_ 键
uniqc sync push --dry-run       # 只预览，不写入
```

- `push` 是**本地优先**：远端同名键会被本地值覆盖；不询问。
- `--prune` 只删除 `UNIQC_` 前缀且符合 uniqc 布局的远端键，项目中的其他 secrets 永远不会被 push 触碰。
- 首次在新项目上使用时，建议先 `status` 再 `push`。

## 下载凭据 (`uniqc sync pull`)

```bash
uniqc sync pull                 # 覆盖本地配置（自动备份）
uniqc sync pull --no-backup     # 跳过备份
uniqc sync pull --dry-run       # 只预览
```

- `pull` 是**远端优先**：本地 profile 段被远端状态整体替换（镜像语义），本地有而远端没有的键会被丢弃。
- 本机专属键不会被动：`active_profile`、`always_ai_hints`、`sync`、以及不含平台子键的节（如 `gateway`）。
- 写入前会把旧配置备份为 `~/.uniqc/config.yaml.bak-<时间戳>`。
- 若远端环境为空（一个 `UNIQC_` 键都没有），`pull` 会拒绝执行，避免误清空本地配置。
- 若本地 `active_profile` 指向的 profile 不在远端，pull 会自动切回 `default`（或第一个可用 profile）并给出警告。

新机器上恢复凭据的完整流程：

```bash
infisical login
uniqc sync setup --project-id <ID> --env dev
uniqc sync pull
uniqc config validate   # 确认配置有效
```

## Secret 布局与值编码

每个配置值对应一个 secret，命名规则：

```text
<profile>.<platform>.<field>  ->  UNIQC_<PROFILE>_<PLATFORM>_<FIELD>
```

例如：

| 配置键 | Secret 名 |
|--------|-----------|
| `default.originq.token` | `UNIQC_DEFAULT_ORIGINQ_TOKEN` |
| `default.quark.QUARK_API_KEY` | `UNIQC_DEFAULT_QUARK_QUARK_API_KEY` |
| `default.ibm.proxy.http` | `UNIQC_DEFAULT_IBM_PROXY_HTTP` |

值编码规则（保证 push/pull 往返后类型不变）：

- 字符串**原样存储**——token 可以直接被其他工具消费（`infisical run -- env`、`infisical secrets get UNIQC_DEFAULT_ORIGINQ_TOKEN`）；
- 数字、布尔、列表、字典等非字符串值存储为 `json:` 前缀 + JSON 文本（如 `json:200`、`json:[3, 7, 11]`）；
- 以 `json:` 或 `@` 开头、或含换行的字符串同样走 JSON 编码，避免歧义。

空值（空字符串、空列表等）代表"未设置"，不会被同步。

## CI / 无人值守场景

`infisical` CLI 登录态之外，还可以使用机器身份 / 服务令牌（Machine Identity Access Token 或 Service Token）：

```bash
export UNIQC_INFISICAL_TOKEN=<machine-identity-access-token>
export UNIQC_INFISICAL_PROJECT_ID=<project-id>
uniqc sync pull --env prod
```

自建 Infisical 实例时，域名沿用 CLI 自带的环境变量 `INFISICAL_DOMAIN`。

## 安全说明

- `~/.uniqc/config.yaml` 由 `uniqc config` 统一以 `0600` 权限原子写入；
- CLI 输出（status / push / pull / dry-run）只显示键名，绝不回显密钥值；
- pull 前自动备份；任何一次 pull 的旧配置都可以从 `~/.uniqc/config.yaml.bak-*` 找回；
- 请确认 Infisical 项目的访问权限配置（最小权限原则），凭据的可见范围等于项目成员范围。

## 常见问题

**`Error: infisical CLI failed (exit 1): ... couldn't find your logged in details`**
先运行 `infisical login`；CI 中改用 `UNIQC_INFISICAL_TOKEN`。

**`Error: No Infisical project configured`**
运行 `uniqc sync setup --project-id <ID>`，或设置 `UNIQC_INFISICAL_PROJECT_ID`。

**换了一台机器 pull 后，为什么 `task_group_size` 这类设置也变了？**
sync 镜像的是整个平台配置段（凭据 + 平台设置）。只同步 token 的做法会让两台机器的配置悄悄分叉，更难排查。

**`Ignored unparsable secret 'UNIQC_...'` 警告**
项目里存在 `UNIQC_` 前缀但不符合 uniqc 布局的 secret。它会被忽略且不会被修改/删除；确认它不是本工具创建的即可。
