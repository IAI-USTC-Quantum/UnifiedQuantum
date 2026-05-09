"""02 — RegionSelector: pick a high-fidelity sub-region of a chip

[doc-require: originq]
[doc-skip-execute]
[doc-output-include: source]

``RegionSelector`` 在芯片标定数据（拓扑 + 单/双比特保真度）上为你挑选一段
**高保真度连续子区域**（链或子区域），用于把小线路放到芯片上"最好的部分"。它接受
一个 ``ChipCharacterization``，最常用的入口是 ``RegionSelector.from_backend``。

下面的代码片段标注了 ``[doc-skip-execute]``：本地 build_docs 不会跑它，因为它需要
真实芯片标定数据（``uniqc backend update --platform originq`` 拉取）以及对应的
凭据。用法本身在所有平台上都一样。
"""

from __future__ import annotations

from uniqc import RegionSelector


def main() -> None:
    selector = RegionSelector.from_backend("originq:WK_C180")

    chain = selector.find_best_1D_chain(length=5)
    print("best 5-qubit chain:", chain.chain)
    print("estimated fidelity:", chain.estimated_fidelity)
    print("num swaps:        ", chain.num_swaps)


if __name__ == "__main__":
    main()
