# 配置管理 (`uniqc config`)

管理云平台的 API 密钥和配置。

## 初始化配置

```bash
# 创建默认配置文件
uniqc config init
```

配置文件位置：`~/.uniqc/uniqc.yml`

## 设置配置项

```bash
# 设置平台 Token
uniqc config set originq.token YOUR_TOKEN
uniqc config set quafu.token YOUR_TOKEN
uniqc config set ibm.token YOUR_TOKEN

# 在指定 profile 下设置
uniqc config set originq.token YOUR_TOKEN --profile production
```

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

> **配置文件同时对 CLI 和 Python API 生效**：`~/.uniqc/uniqc.yml` 中的 token 配置不仅支持 `uniqc config set` 写入的 CLI 命令，也被 Python 云的 `OriginQAdapter`、`QuafuAdapter` 等适配器直接读取（通过 `uniqc config` 模块 fallback）。使用 Python API 时无需额外设置环境变量。

## 配置 Profile 管理

```bash
# 列出所有 profile
uniqc config profile list

# 切换 profile
uniqc config profile use production

# 创建新 profile
uniqc config profile create testing
```
