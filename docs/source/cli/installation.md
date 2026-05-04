# 安装与入口

CLI 工具随 `unified-quantum` 包一同安装。安装方式请参见[安装指南](../guide/installation.md)，推荐使用 `uv`（建议配置清华源）进行安装。

## 调用方式

```bash
# 推荐：直接命令
uniqc --help

# 备选：CLI 模块入口
python -m uniqc.cli --help
```

## AI Agent 技能安装（可选）

如果你需要给 AI Agent（Codex 或 Claude Code）补齐 UnifiedQuantum 最佳使用流程，可直接安装本仓库的 skill 集：

```bash
npx skills add IAI-USTC-Quantum/quantum-computing.skill --agent codex --skill '*'
npx skills add IAI-USTC-Quantum/quantum-computing.skill --agent claude-code --skill '*'
```
