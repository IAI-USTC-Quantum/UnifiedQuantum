# UnifiedQuantum 安装

本页帮助你快速完成安装，并在安装后立即验证环境是否可用。若你是第一次接触 UnifiedQuantum，建议先完成本页，再继续阅读 [快速上手](quickstart.md)。

## 推荐安装方式：通过 uv 安装

[uv](https://github.com/astral-sh/uv) 是新一代 Python 包管理工具，安装与构建速度远快于 pip。

> **中国大陆用户推荐配置清华源**，可大幅提升下载速度：
> ```bash
> # 永久生效（推荐）
> uv pip install --python-preference managed --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
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
- **Python**：>= 3.10, < 3.14
- **C++ 编译器**：支持 C++17（MSVC / gcc / clang）
- **CMake**：>= 3.26

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
pip install -e . --no-build-isolation
```

## 安装验证

安装完成后，运行以下命令确认安装成功：

```bash
python -c "import uniqc; print(uniqc.__version__)"
```

若能打印出版本号（如 `0.200.0`），说明安装成功。

## 构建 C++ 扩展常见问题

**Q：编译时报 `CMake could not find...`**
> 确保 CMake 已安装并加入 PATH。Windows 上可使用 [CMake 官方安装包](https://cmake.org/download/)。

**Q：编译时报 `fatal error: pybind11/pybind11.h: No such file`**
> 确保已执行 `git clone --recurse-submodules`，pybind11 子模块未初始化会导致此错误。运行 `git submodule update --init --recursive` 后重新安装。

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

### Quafu 平台

```bash
uv pip install unified-quantum[quafu]
# 或 pip
pip install unified-quantum[quafu]
```

### IBM 平台

```bash
uv pip install unified-quantum[qiskit]
# 或 pip
pip install unified-quantum[qiskit]
```

> **注意**：`[qiskit]` extra 包含 `qiskit`、`qiskit-aer` 和 `qiskit-ibm-runtime`。项目不在 `pyproject.toml` 中钉住第三方依赖版本，具体版本由当前包索引解析得到。

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

```bash
uv pip install unified-quantum[all]
# 或 pip
pip install unified-quantum[all]
```

## 开发者补充

维护者应使用 `uv sync --all-extras --group dev --group docs --upgrade` 建立全量环境；缺少任意可选后端依赖或文档构建依赖都应视为开发环境不完整，而不是测试阻断的正常原因。项目依赖策略是不在 `pyproject.toml` 中约束第三方依赖版本，主分支不提交 `uv.lock`，依赖解析问题应通过升级解析结果和上游兼容性审查处理。

如需本地构建文档，使用上述全量环境后进入 `docs/` 目录执行 `make html`。这一步仅在维护文档时需要，普通安装可跳过。

## 下一步

- [快速上手](quickstart.md) —— 运行安装后的第一个最小示例
- [README 中的快速示例](https://github.com/IAI-USTC-Quantum/UnifiedQuantum#quick-example) —— 先快速浏览仓库首页示例与入口说明
