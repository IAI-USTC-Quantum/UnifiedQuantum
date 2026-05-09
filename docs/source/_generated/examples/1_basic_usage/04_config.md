### 04 — Configuration: ``uniqc config`` + ``~/.uniqc/config.yaml``

*Source*: ``examples/1_basic_usage/04_config.py``  
*Status*: **pass**

只演示**只读**的配置 API：本例不会去碰真实的 ``~/.uniqc/config.yaml``，而是写到一个
临时文件再读回来。

实际使用时推荐三种方式之一：

1. ``uniqc config init`` + ``uniqc config set originq.token <YOUR_TOKEN>``
2. 手动编辑 ``~/.uniqc/config.yaml``
3. 用 ``UNIQC_PROFILE`` 环境变量切换 profile

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/04_config.py
:language: python
```

**Stdout**

```text
written to: /tmp/uniqc-config-demo-g7srbl75/config.yaml
active profile: demo
originq token (redacted): originq-token-redacted
validation errors: []

CLI equivalents:
  uniqc config init
  uniqc config set originq.token YOUR_TOKEN
  uniqc config set ibm.proxy.http http://proxy.example.com:8080
  uniqc config validate
```

