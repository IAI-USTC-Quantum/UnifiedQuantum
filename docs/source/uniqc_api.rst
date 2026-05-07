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

