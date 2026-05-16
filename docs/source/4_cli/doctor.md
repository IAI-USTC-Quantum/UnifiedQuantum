# 环境诊断 (`uniqc doctor`)

一键检查 UnifiedQuantum 安装环境的健康状态，覆盖依赖、配置、缓存、网络连通性和平台标定数据。

## 使用方式

```bash
uniqc doctor
```

命令按顺序执行以下 6 项检查，每项使用 ✓（通过）、✗（失败）、⚠（警告）标记状态。

## 检查项说明

### 1. 环境与版本

显示 `uniqc` 版本、Python 版本、操作系统和配置文件路径。

### 2. 依赖

检查核心依赖（`numpy`、`typer`、`rich`、`scipy`、`pyyaml`）和可选依赖（`pyqpanda3`、`qiskit` 等）的安装状态和版本。

### 3. 配置文件

- 验证 `~/.uniqc/config.yaml` 存在性
- 调用 `validate_config()` 报告所有错误/警告
- 显示当前活跃 profile
- 对每个平台展示脱敏后的 API Key（前 6 位 + `****`）

### 4. 任务数据库

检查 `~/.uniqc/cache/tasks.sqlite`：
- 验证 `application_id` 是否为 `0x554E4943`（UNIC）
- 报告 schema 版本和任务数量

### 5. 后端缓存

检查 `~/.uniqc/cache/backends.json`：
- 显示每个平台的缓存后端数量
- 报告缓存年龄和是否过期（TTL 24 小时）

### 6. 平台连通性与标定数据

对每个已配置凭据的平台：
- 强制刷新后端列表以测试凭据和网络连通性
- 对每个硬件后端获取标定数据，检查 `available_qubits`、`connectivity`、`single_qubit_data`、`two_qubit_data` 是否为空
- 报告标定时间戳

## 示例输出

以下是全平台配置、全依赖安装的健康系统输出示例：

```
─────────────── 1. Environment & Version ───────────────

 uniqc     0.0.11
 Python    3.12.3  (CPython)
 OS        Linux-5.15.167.4-microsoft-standard-WSL2-x86_64-with-glibc2.39
 Config    /home/user/.uniqc/config.yaml

─────────────────── 2. Dependencies ────────────────────

         Core Dependencies
┌──────────────────────────────────────┐
│ Package  Version                     │
│ numpy    1.26.4                      │
│ typer    0.12.3                      │
│ rich     13.7.1                      │
│ scipy    1.13.1                      │
│ yaml     6.0.1                       │
└──────────────────────────────────────┘

         Optional Dependencies
┌──────────────────────────────────────────────┐
│ Group          Package              Version   │
│ originq        pyqpanda3            3.x.x     │
│ quark          quarkstudio          x.x.x     │
│                quarkcircuit          x.x.x     │
│ qiskit         qiskit               1.x.x     │
│                qiskit_ibm_runtime   0.30.x    │
│ simulation     qutip                5.x.x     │
│ visualization  matplotlib           3.9.x     │
│ pytorch        torch                2.x.x     │
└──────────────────────────────────────────────┘

─────────────────── 3. Config File ────────────────────

 ✓ Config file: /home/user/.uniqc/config.yaml
 ✓ Configuration is valid
   Active profile: default

         Platform Credentials
┌──────────────────────────────────────────┐
│ Platform  Token/Key          Status      │
│ originq   abc123****         configured  │
│ quark     qrk456****         configured  │
│ ibm       ibm012****         configured  │
└──────────────────────────────────────────┘

─────────────────── 4. Task Database ──────────────────

 ✓ Task database: /home/user/.uniqc/cache/tasks.sqlite
 ✓ application_id: 0x554E4943 (UNIC)
   Schema version: 5
   Task count: 42

─────────────────── 5. Backend Cache ──────────────────

 ✓ Backend cache exists

         Backend Cache
┌──────────────────────────────────────────┐
│ Platform  Backends  Age    Stale?        │
│ originq   5         0.5h   no            │
│ ibm       8         25.3h  yes           │
└──────────────────────────────────────────┘

───────── 6. Platform Connectivity & Calibration ──────

 Platform: originq
 ✓ Connectivity OK — 5 backend(s) fetched
 ✓ wuyuan:d5: calibration OK (calibrated_at=2026-05-10T08:00:00Z)
 ✓ WK_C180: calibration OK (calibrated_at=2026-05-10T06:30:00Z)

 Platform: quark
 ✓ Connectivity OK — 2 backend(s) fetched
 ✓ QC24-04: calibration OK (calibrated_at=2026-05-10T04:00:00Z)

 Platform: ibm
 ✓ Connectivity OK — 8 backend(s) fetched
 ✓ ibm-sherbrooke: calibration OK (calibrated_at=2026-05-09T20:00:00Z)
 ✓ ibm-kyoto: calibration OK (calibrated_at=2026-05-09T20:00:00Z)

──────────────────── Done ────────────────────
```
