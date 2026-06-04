# UnifiedQuantum 安装

本页帮助你快速完成安装，并在安装后立即验证环境是否可用。若你是第一次接触 UnifiedQuantum，建议先完成本页，再继续阅读 [快速上手](quickstart.md)。

## 推荐安装方式：通过 uv 安装

[uv](https://github.com/astral-sh/uv) 是新一代 Python 包管理工具，安装与构建速度远快于 pip。

> **中国大陆用户推荐配置清华源**，可大幅提升下载速度：
> ```bash
> # 永久生效（推荐）
> uv pip install --python-preference managed --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
> ```
>
> **已知问题**：清华镜像可能缺少 `quarkcircuit` 等包（返回 HTTP 404）。如果
> `uv sync --extra quark` 报依赖解析失败，请临时切换到 PyPI 官方源：
> ```bash
> UV_INDEX_URL=https://pypi.org/simple/ uv sync --extra quark
> ```

### 从 PyPI 安装

```bash
# 安装 CLI 工具（推荐，全局可用，无需虚拟环境）
uv tool install unified-quantum

# 安装 Python 包（提供 Python API，可与 CLI 安装共存）
uv pip install unified-quantum
```

### 从源码构建

当你需要安装开发版本、启用 C++ 模拟器或直接修改源码时，可使用源码安装。

#### 平台要求

- **操作系统**：跨平台，支持 Windows、Linux、macOS
- **Python**：>= 3.10, < 3.15
- **C++ 编译器**：支持 C++17（MSVC / gcc / clang）
- **CMake**：>= 3.26

> **Python 3.14 注意事项**：v0.0.15 起支持 Python 3.14（`<3.15`），但以下可选
> extra 在 Python 3.14 上**不可用**（上游尚未发布 cp314 wheel）：
>
> | Extra | Python 3.14 状态 | 替代方案 |
> |-------|-----------------|---------|
> | `[originq]` | ❌ 不可用（`pyqpanda3` 无 cp314 wheel） | 使用 Python 3.10–3.13 |
> | `[quark]` | ❌ 不可用（`srpc` / `quarkcircuit` 无 cp314 标准 wheel） | 使用 Python 3.12–3.13 |
> | `[simulation]` | ✅ 可用 | — |
> | `[visualization]` | ✅ 可用 | — |
> | `[pytorch]` | ✅ 可用 | — |
>
> 在 Python 3.14 上安装 `[originq]` 或 `[quark]` 不会报错，但相关依赖不会被安装。
> 尝试提交到 OriginQ 时会收到 `MissingDependencyError` 并附带安装提示。
> 芯片缓存（`dummy:originq:*`、`dummy:quark:*`）在 Python 3.14 上仍然可用——
> 仅实时云端连接需要对应 SDK。
>
> 等上游发布 cp314 wheel 后，将通过 patch 版本（如 `0.0.15.post1`）恢复支持。

#### 获取源码

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum
```

#### 克隆子模块（C++ 模拟器）

UnifiedQuantum 的 C++ 模拟器作为 Git 子模块存在。**首次克隆后必须初始化子模块**，否则 C++ 模拟器不会被包含：

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum
```

如果克隆时忘记加 `--recurse-submodules`，后续可以补上：

```bash
git submodule update --init --recursive
```

#### 构建并安装

```bash
# Maintainer / 全量开发环境：安装 dev、docs 和全部可选后端依赖，并按当前包索引升级解析
uv sync --all-extras --group dev --group docs --upgrade

# 验证完整测试套件
uv run pytest uniqc/test
```

> **注意：** 从源码构建时 C++ 模拟器为必需组件。如果系统 CMake 版本过低（< 3.26），请先运行 `pip install cmake --upgrade` 后再执行上述命令。

## 备选安装方式：通过 pip 安装

> pip 不支持 `uv tool install` 的 CLI 全局安装方式（无需虚拟环境即可全局调用 `uniqc` 命令）。如无特殊需求，建议优先使用上面的 uv 安装方式。

### 从 PyPI 安装

```bash
pip install unified-quantum
```

### 从源码构建

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum

# 完整安装
pip install .

# 开发模式
pip install -e .
```

## 安装验证

安装完成后，运行以下命令确认安装成功：

```bash
python -c "import uniqc; print(uniqc.__version__)"
```

若能打印出版本号（如 `0.200.0`），说明安装成功。

也可以直接运行 [`uniqc doctor`](../4_cli/doctor.md) 一键体检（依赖、配置、缓存、网络连通性）。

## 配置真机平台（推荐 OriginQ）

```bash
uniqc config init
uniqc config set originq.token <YOUR_ORIGINQ_TOKEN>
uniqc config validate
```

* OriginQ 是目前推荐的入门平台：免费试用门槛低、文档完整，`uniqc backend list -p originq`
  能看到全部芯片。
* 其它平台同理：`uniqc config set ibm.token ...` / `uniqc config set quark.token ...`。

配置文件结构与 profile 切换的完整说明见 [平台约定](../1_basic_usage/platform_conventions.md) 与
[`uniqc config`](../4_cli/config.md)。

## 构建 C++ 扩展常见问题

**Q：编译时报 `CMake could not find...`**
> 确保 CMake 已安装并加入 PATH。Windows 上可使用 [CMake 官方安装包](https://cmake.org/download/)。

**Q：编译时报 `fatal error: pybind11/pybind11.h: No such file`**
> 默认隔离构建会按 `pyproject.toml` 自动安装 PyPI 上的 `pybind11`。如果你显式使用了 `--no-build-isolation`，请先在当前环境安装 `pybind11` 后重新构建。

**Q：如何确认 C++ 模拟器已正确安装？**
> 安装后运行 `python -c "from uniqc_cpp import *; print('C++ 模拟器正常')"`。若无声出输出说明 C++ 扩展未安装成功。

## 可选依赖

核心依赖（numpy、scipy、sympy 等）在默认安装中已包含。以下为可选功能的额外依赖：

### OriginQ 平台

```bash
uv pip install unified-quantum[originq]
# 或 pip
pip install unified-quantum[originq]
```

> **Python 3.14 用户**：此 extra 在 Python 3.14 上会被 marker 门控跳过。使用
> Python 3.10–3.13 以获取 OriginQ 平台支持。

### QuarkStudio / Quark 平台

```bash
uv pip install unified-quantum[quark]
# 或 pip
pip install unified-quantum[quark]
```

> **注意**：`[quark]` extra 包含 `quarkstudio` 和 `quarkcircuit`。前者负责 `Task.status/run/result`，后者用于读取芯片拓扑、耦合器保真度、可用门和校准信息。
>
> - 可用范围：**Python 3.12–3.13、Linux / macOS**。`win32` 和 Python ≥ 3.14 上
>   该 extra 会被 marker 门控跳过（不报错，但不安装 `quarkstudio` /
>   `quarkcircuit`）。
> - 从 v0.0.15 起，`[all]` **不再包含** `[quark]`。如需 Quark 平台支持，
>   请显式安装 `[quark]`。

### IBM / Qiskit 平台

Qiskit 已是 `unified-quantum` 的**核心依赖**，随默认安装一起进来；不需要再安装 `[qiskit]` extra。如果 `import qiskit` 失败，说明当前环境损坏，请重装：

```bash
pip install --upgrade unified-quantum
```

> **注意**：核心依赖现在包含 `qiskit`、`qiskit-aer` 和 `qiskit-ibm-runtime`。项目不在 `pyproject.toml` 中钉住第三方依赖版本，具体版本由当前包索引解析得到。

### 高级模拟 (QuTiP)

```bash
uv pip install unified-quantum[simulation]
# 或 pip
pip install unified-quantum[simulation]
```

### 可视化

```bash
uv pip install unified-quantum[visualization]
# 或 pip
pip install unified-quantum[visualization]
```

### PyTorch 集成

```bash
uv pip install unified-quantum[pytorch]
# 或 pip
pip install unified-quantum[pytorch]
```

### 安装所有可选依赖

`[all]` 安装跨平台兼容的可选功能依赖（`[simulation]` + `[visualization]` +
`[pytorch]` + `[originq]` + `[quafu]` 等）。

> **v0.0.15 Breaking Change**：`[all]` **不再包含** `[quark]`。之前 `[all]`
> 因为 `quarkcircuit` 在 `win32` 和 Python 3.14 上缺少 wheel，导致跨平台
> 解析失败。如需 Quark 平台支持，请显式安装 `pip install unified-quantum[quark]`
> （仅限 Python 3.12–3.13 + Linux / macOS）。

```bash
uv pip install unified-quantum[all]
# 或 pip
pip install unified-quantum[all]
```

## 弃用政策

v0.0.15 建立了明确的弃用时间线：**所有在 `0.0.x` 中触发 `DeprecationWarning`
的公共 API 将在 `0.1.0` 中移除或不再保证兼容性**。

当前已弃用的 API 包括：

- `uniqc.simulator.get_backend()` — 改用 `get_simulator()` / `create_simulator()`
- `IBMAdapter` 类 — 改用 `QiskitAdapter`
- `quafu_adapter` 模块 — Quafu 平台已停止维护
- 所有 `*_circuit(circuit, ...)` in-place 形式 — 改用 fragment 形式

详见 [弃用政策（0.1.0 兼容性悬崖）](../7_releases/deprecation_policy.md)。
升级前请运行 `pytest -W error::DeprecationWarning` 清理所有弃用警告。

## 开发者补充

维护者应使用 `uv sync --all-extras --group dev --group docs --upgrade` 建立全量环境；缺少当前维护的可选后端依赖或文档构建依赖都应视为开发环境不完整，而不是测试阻断的正常原因。项目依赖策略是不在 `pyproject.toml` 中约束第三方依赖版本，主分支不提交 `uv.lock`，依赖解析问题应通过升级解析结果和上游兼容性审查处理。

如需本地构建文档，使用上述全量环境后进入 `docs/` 目录执行 `make html`。这一步仅在维护文档时需要，普通安装可跳过。

## 下一步

- [快速上手](quickstart.md) —— 运行安装后的第一个最小示例
- [README 中的快速示例](https://github.com/IAI-USTC-Quantum/UnifiedQuantum#quick-example) —— 先快速浏览仓库首页示例与入口说明
