### 00 — 配置 Key 与后端缓存

*Source*: ``examples/3_best_practices/00_config_and_backend_cache.py``  
*Status*: **pass**

最早的用户路径：创建配置、写入平台 token（脱敏）、校验配置结构，并用本地构造的
``BackendInfo`` 演示后端缓存的写入、读取和审查。真实 token 不会写入文档输出。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/00_config_and_backend_cache.py
:language: python
```

**Stdout**

```text
profile: release-check
validation errors: []
cached backend ids: ['dummy:virtual-line-3']
cache platforms: ['dummy']
audit issues: []
```

