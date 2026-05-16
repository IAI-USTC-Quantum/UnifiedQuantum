# Algorithm Examples

完整量子算法实现示例。

每个算法包含 Python 代码与 Markdown 文档。

## 算法列表

| Algorithm | Code | Documentation |
|-----------|------|---------------|
| Grover 搜索 | [grover.py](grover.py) | [grover.md](grover.md) |
| VQE | [vqe.py](vqe.py) | [vqe.md](vqe.md) |
| QAOA | [qaoa.py](qaoa.py) | [qaoa.md](qaoa.md) |
| QPE | [qpe.py](qpe.py) | [qpe.md](qpe.md) |
| HEA Options | [hea_options.py](hea_options.py) | [hea_options.md](hea_options.md) |
| QAOA Variants | [qaoa_variants.py](qaoa_variants.py) | [qaoa_variants.md](qaoa_variants.md) |
| HVA | [hva_example.py](hva_example.py) | [hva_example.md](hva_example.md) |
| Parameters | [parameters_demo.py](parameters_demo.py) | [parameters_demo.md](parameters_demo.md) |
| ADAPT-VQE | [adapt_vqe.py](adapt_vqe.py) | - |

## 运行方式

从仓库根目录执行：

```bash
# Grover 搜索
python examples/algorithms/grover.py --n-qubits 3 --marked-state 5

# VQE (H2 分子)
python examples/algorithms/vqe.py --molecule H2 --maxiter 100

# QAOA (MaxCut)
python examples/algorithms/qaoa.py -p 2 --maxiter 80

# QPE
python examples/algorithms/qpe.py --n-precision 4 --unitary t --shots 4096

# HEA 配置选项
python examples/2_advanced/algorithms/hea_options.py --n-qubits 4 --depth 2

# QAOA 变体 (XY mixer, warm-start, MA-QAOA)
python examples/2_advanced/algorithms/qaoa_variants.py -p 2 -n 4

# HVA (Hamiltonian Variational Ansatz)
python examples/2_advanced/algorithms/hva_example.py -p 2 -n 20

# 符号参数演示
python examples/2_advanced/algorithms/parameters_demo.py

# ADAPT-VQE
python examples/2_advanced/algorithms/adapt_vqe.py
```

## 文档说明

每个 `.md` 文件包含：

- 算法原理与数学背景
- 代码实现详解
- 运行示例与预期输出
- 扩展思路
- 参考文献
