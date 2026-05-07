API 参考
========

UnifiedQuantum 公开 API 的完整参考文档。

- 手动维护的 API 入口（推荐先读）：``api_index``
- 自动生成的 API 树（由 ``sphinx-autoapi`` 从源码生成）：``api/uniqc/index``

如果在本地构建文档时未安装 ``sphinx-autoapi`` extra，自动生成的 API 树
会缺失。建议安装 ``unified-quantum[docs]`` 后再 ``sphinx-build``。

.. toctree::
   :maxdepth: 2
   :caption: 入口

   api_index

.. toctree::
   :maxdepth: 2
   :caption: 自动生成 API 索引

   api/uniqc/index

.. note::

   ``api/uniqc/index`` 是 ``sphinx-autoapi`` 在 build 时根据 ``uniqc/`` 源码
   自动生成的产物，**不在 git 仓库中**。在本地执行 ``sphinx-build`` 之前，请
   先 ``pip install unified-quantum[docs]``（包含 ``sphinx-autoapi``）。否则
   该 toctree 节点会出现 "document isn't included in any toctree" 警告。

