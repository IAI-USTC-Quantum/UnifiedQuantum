# `uniqc gateway` — Web UI 网关

`uniqc gateway` 子命令用于在后台启动一个本地 Web UI 服务，提供基于浏览器的任务、后端、配置查看入口。它读取 `~/.uniqc/uniqc.yml` 中的 `gateway` 段（如 `host`、`port`），并把进程信息写入 `~/.uniqc/gateway.pid`，方便后续 `stop`/`status` 操作。

## 子命令

| 子命令 | 说明 |
| --- | --- |
| `start`   | 在后台启动网关服务 |
| `stop`    | 停止后台运行的网关 |
| `restart` | 先 `stop` 再 `start` |
| `status`  | 查看网关是否在运行，输出 PID 和监听地址 |

## 启动

```bash
uniqc gateway start
uniqc gateway start --port 8081       # 覆盖配置中的端口
uniqc gateway start --host 0.0.0.0    # 监听所有地址（默认 127.0.0.1）
```

启动后会在控制台打印访问 URL，例如：

```
Gateway started: http://127.0.0.1:8080 (pid 12345)
```

## 状态查询

```bash
uniqc gateway status
```

输出示例：

```
Gateway is running (pid 12345) on http://127.0.0.1:8080
```

如果未在运行，会明确提示 `Gateway is not running`。

## 停止与重启

```bash
uniqc gateway stop
uniqc gateway restart
```

`stop` 会向 PID 文件中的进程发送 `SIGTERM`；如果进程已经消失，会自动清理过期的 PID 文件。

## 与配置项的关系

`uniqc.yml` 中可配置：

```yaml
gateway:
  host: 127.0.0.1
  port: 8080
```

命令行 `--host` / `--port` 会**覆盖**配置文件值，仅作用于当次启动。

## 故障排查

| 现象 | 排查方向 |
| --- | --- |
| `start` 报端口占用 | 用 `--port` 换一个端口，或检查上一次实例是否未通过 `stop` 退出 |
| `status` 显示运行中但浏览器打不开 | 确认 `host` 不是 `0.0.0.0` 时是否使用了 `127.0.0.1` 而不是公网 IP |
| `stop` 报找不到 PID | `~/.uniqc/gateway.pid` 已被清理；可直接 `start` 重新启动 |

## 参见

- [安装与初始化](installation.md)
- [配置参考](config.md)
