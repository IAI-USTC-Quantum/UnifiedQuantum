### 01 — CLI walkthrough: all the ``uniqc`` subcommands

*Source*: ``examples/4_cli/01_cli_walkthrough.py``  
*Status*: **pass**

把所有常用 CLI 子命令通过 ``subprocess.run`` 拉一遍，方便你看到每个命令的实际输出
形态。覆盖：

* ``uniqc --help``
* ``uniqc backend list``
* ``uniqc simulate <file>``
* ``uniqc submit <file> --backend dummy --wait``
* ``uniqc result <task_id>``
* ``uniqc task list``

需要真实 token 的子命令（``uniqc config set originq.token ...``、``uniqc submit --backend originq:...``、
``uniqc calibrate xeb``）只演示帮助文本，不会真的提交。

**Source code**

```{literalinclude} ../../../examples/4_cli/01_cli_walkthrough.py
:language: python
```

**Stdout**

```text
== uniqc --help ==
                                                                                
 Usage: python -m uniqc.cli [OPTIONS] COMMAND [ARGS]...                         
                                                                                
 UnifiedQuantum CLI — A lightweight quantum computing framework GitHub  |       
 Documentation                                                                  
                                                                                
 Pass --ai-hints/--ai-hint, set UNIQC_AI_HINTS=1, or run uniqc config           
 always-ai-hint on to show AI workflow guidance.                                
 AI Agent 安装建议：                                                            
 Codex:  npx skills add IAI-USTC-Quantum/quantum-computing.skill --agent codex  
 --skill '*'                                                                    
 Claude Code: npx skills add IAI-USTC-Quantum/quantum-computing.skill --agent   
 claude-code --skill '*'                                                        
                                                                                
 默认按仓库安装本仓库全部 skill（推荐）。                                       
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version             -V        Show version and exit                        │
│ --install-completion            Install completion for the current shell.    │
│ --show-completion               Show completion for the current shell, to    │
│                                 copy it or customize the installation.       │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ circuit    Circuit format conversion (OriginIR <-> QASM)                     │
│            CLI Docs  |  GitHub                                               │
│ simulate   Local circuit simulation                                          │
│            CLI Docs  |  GitHub                                               │
│ submit     Submit circuits to quantum cloud platforms                        │
│            CLI Docs  |  GitHub                                               │
│ result     Query task results from quantum cloud platforms                   │
│            CLI Docs  |  GitHub                                               │
│ doctor     Run diagnostics to verify your uniqc installation                 │
│            CLI Docs  |  GitHub                                               │
│ config     Manage API key and configuration                                  │
│            CLI Docs  |  GitHub                                               │
│ task       Manage submitted tasks                                            │
│            CLI Docs  |  GitHub                                               │
│ backend    List, update, and inspect quantum cloud backends                  │
│            CLI Docs  |  GitHub                                               │
│ calibrate  Run chip calibration experiments — XEB benchmarking               │
│            (1q/2q/parallel), readout error calibration, and parallel         │
│            execution pattern analysis. Results are cached to                 │
│            ~/.uniqc/calibration_cache/ with TTL freshness enforcement.       │
│            CLI Docs  |  GitHub                                               │
│ gateway    Manage the uniqc gateway web UI server.                           │
╰──────────────────────────────────────────────────────────────────────────────╯


== uniqc backend list (dummy only; cloud backends require credentials) ==
                               Available Backends                               
╭────────────┬──────────────────────────────┬──────────┬──────────────┬────────╮
│ Platform   │ Name                         │   Qubits │ Status       │ Type   │
├────────────┼──────────────────────────────┼──────────┼──────────────┼────────┤
│ dummy      │ dummy:local:simulator        │        - │ available    │ sim    │
│ dummy      │ dummy:local:virtual-line-3   │        3 │ available    │ sim    │
│ dummy      │ dummy:local:virtual-grid-2x2 │        4 │ available    │ sim    │
│ dummy      │ dummy:local:mps-linear-3     │        3 │ available    │ sim    │
│ dummy      │ virtual:release-check-r2     │        4 │ available    │ sim    │
╰────────────┴──────────────────────────────┴──────────┴──────────────┴────────╯

Cache:
    originq: 7 backends, updated 2d ago (stale)
    quafu: 16 backends, updated 83d ago (stale)
    ibm: 3 backends, updated 46d ago (stale)

== uniqc simulate bell.originir --shots 256 ==
      Simulation Results       
┏━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┓
┃ State ┃ Count ┃ Probability ┃
┡━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━┩
│ 00    │ 127   │ 50.0%       │
│ 11    │ 127   │ 50.0%       │
└───────┴───────┴─────────────┘

== uniqc submit bell.originir --backend dummy -s 64 --wait --format json ==
{
  "task_id": "uqt_900b4fb887e44eeb9a30f7213e1460c5",
  "backend": "dummy:local:simulator",
  "shots": 64
}
{
  "counts": {
    "00": 32,
    "11": 32
  },
  "probabilities": {
    "00": 0.5,
    "11": 0.5
  },
  "shots": 64,
  "platform": "dummy",
  "task_id": "uqt_900b4fb887e44eeb9a30f7213e1460c5",
  "backend_name": "dummy:local:simulator",
  "execution_time": null,
  "error_message": null
}

== uniqc task list (most recent few) ==
                                     Tasks                                      
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Task ID           ┃ Platform          ┃ Status  ┃ Shots ┃ Submit Time        ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ uqt_900b4fb887e4… │ dummy:local:simu… │ success │ 64    │ 2026-07-21T07:17:… │
│ uqt_81bb138a7a42… │ dummy:local:simu… │ success │ 64    │ 2026-07-21T07:16:… │
│ uqt_7be47e92ae6e… │ dummy:local:simu… │ success │ 128   │ 2026-07-21T07:16:… │
│ uqt_2b81cddb689e… │ dummy:local:simu… │ success │ 2000  │ 2026-07-21T07:16:… │
│ uqt_57269521d11c… │ dummy:local:mps-… │ success │ 400   │ 2026-07-21T07:16:… │
└───────────────────┴───────────────────┴─────────┴───────┴────────────────────┘
```

