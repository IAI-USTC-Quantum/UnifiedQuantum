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
[1m                                                                                [0m
[1m [0m[1;33mUsage: [0m[1mpython [0m[1;32m-m[0m[1m uniqc.cli [OPTIONS] COMMAND [ARGS]...[0m[1m                        [0m[1m [0m
[1m                                                                                [0m
 UnifiedQuantum CLI — A lightweight quantum computing framework ]8;id=16071801;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\  |       
 ]8;id=16071803;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/\[36mDocumentation[0m]8;;\                                                                  
                                                                                
 [2mPass [0m[1;2;36m-[0m[1;2;36m-ai[0m[1;2;36m-hints[0m[2m/[0m[1;2;36m-[0m[1;2;36m-ai[0m[1;2;36m-hint[0m[2m, set UNIQC_AI_HINTS=1, or run uniqc config [0m          
 [2malways-ai-hint on to show AI workflow guidance.[0m                                
 [2mAI Agent 安装建议：[0m                                                            
 [2mCodex:  npx skills add IAI-USTC-Quantum/quantum-computing.skill [0m[1;2;36m-[0m[1;2;36m-agent[0m[2m codex [0m 
 [1;2;36m-[0m[1;2;36m-skill[0m[2m '*'[0m                                                                    
 [2mClaude Code: npx skills add IAI-USTC-Quantum/quantum-computing.skill [0m[1;2;36m-[0m[1;2;36m-agent[0m[2m [0m  
 [2mclaude-code [0m[1;2;36m-[0m[1;2;36m-skill[0m[2m '*'[0m                                                        
                                                                                
 [2m默认按仓库安装本仓库全部 skill（推荐）。[0m                                       
                                                                                
[2m╭─[0m[2m Options [0m[2m───────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36m-[0m[1;36m-version[0m             [1;32m-V[0m        Show version and exit                        [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-install[0m[1;36m-completion[0m            Install completion for the current shell.    [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-show[0m[1;36m-completion[0m               Show completion for the current shell, to    [2m│[0m
[2m│[0m                                 copy it or customize the installation.       [2m│[0m
[2m│[0m [1;36m-[0m[1;36m-help[0m                          Show this message and exit.                  [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────╯[0m
[2m╭─[0m[2m Commands [0m[2m──────────────────────────────────────────────────────────────────[0m[2m─╮[0m
[2m│[0m [1;36mcircuit  [0m[1;36m [0m Circuit format conversion (OriginIR [1;33m<->[0m QASM)                     [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071808;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-circuit\[36mCLI Docs[0m]8;;\  |  ]8;id=16071810;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36msimulate [0m[1;36m [0m Local circuit simulation                                          [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071815;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-simulate\[36mCLI Docs[0m]8;;\  |  ]8;id=16071817;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36msubmit   [0m[1;36m [0m Submit circuits to quantum cloud platforms                        [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071822;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-submit\[36mCLI Docs[0m]8;;\  |  ]8;id=16071824;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mresult   [0m[1;36m [0m Query task results from quantum cloud platforms                   [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071829;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-result\[36mCLI Docs[0m]8;;\  |  ]8;id=16071831;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mdoctor   [0m[1;36m [0m Run diagnostics to verify your uniqc installation                 [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071836;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/cli/doctor.html\[36mCLI Docs[0m]8;;\  |  ]8;id=16071838;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mconfig   [0m[1;36m [0m Manage API key and configuration                                  [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071843;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-config\[36mCLI Docs[0m]8;;\  |  ]8;id=16071845;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mtask     [0m[1;36m [0m Manage submitted tasks                                            [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071850;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-task-list\[36mCLI Docs[0m]8;;\  |  ]8;id=16071852;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mbackend  [0m[1;36m [0m List, update, and inspect quantum cloud backends                  [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071857;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/cli.html#uniqc-backend\[36mCLI Docs[0m]8;;\  |  ]8;id=16071859;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mcalibrate[0m[1;36m [0m Run chip calibration experiments — XEB benchmarking               [2m│[0m
[2m│[0m [1;36m          [0m (1q/2q/parallel), readout error calibration, and parallel         [2m│[0m
[2m│[0m [1;36m          [0m execution pattern analysis. Results are cached to                 [2m│[0m
[2m│[0m [1;36m          [0m ~/.uniqc/calibration_cache/ with TTL freshness enforcement.       [2m│[0m
[2m│[0m [1;36m          [0m ]8;id=16071864;https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/4_cli/index.html\[36mCLI Docs[0m]8;;\  |  ]8;id=16071866;https://github.com/IAI-USTC-Quantum/UnifiedQuantum\[36mGitHub[0m]8;;\                                               [2m│[0m
[2m│[0m [1;36mgateway  [0m[1;36m [0m Manage the uniqc gateway web UI server.                           [2m│[0m
[2m╰──────────────────────────────────────────────────────────────────────────────╯[0m


== uniqc backend list (dummy only; cloud backends require credentials) ==
[3m                               Available Backends                               [0m
╭────────────┬──────────────────────────────┬──────────┬──────────────┬────────╮
│[1;36m [0m[1;36mPlatform  [0m[1;36m [0m│[1;36m [0m[1;36mName                        [0m[1;36m [0m│[1;36m [0m[1;36m  Qubits[0m[1;36m [0m│[1;36m [0m[1;36mStatus      [0m[1;36m [0m│[1;36m [0m[1;36mType  [0m[1;36m [0m│
├────────────┼──────────────────────────────┼──────────┼──────────────┼────────┤
│[32m [0m[32mdummy     [0m[32m [0m│[1;32m [0m[1;32mdummy:local:simulator       [0m[1;32m [0m│[32m [0m[32m       -[0m[32m [0m│[32m [0m[32mavailable   [0m[32m [0m│[32m [0m[32msim   [0m[32m [0m│
│[32m [0m[32mdummy     [0m[32m [0m│[1;32m [0m[1;32mdummy:local:virtual-line-3  [0m[1;32m [0m│[32m [0m[32m       3[0m[32m [0m│[32m [0m[32mavailable   [0m[32m [0m│[32m [0m[32msim   [0m[32m [0m│
│[32m [0m[32mdummy     [0m[32m [0m│[1;32m [0m[1;32mdummy:local:virtual-grid-2x2[0m[1;32m [0m│[32m [0m[32m       4[0m[32m [0m│[32m [0m[32mavailable   [0m[32m [0m│[32m [0m[32msim   [0m[32m [0m│
│[32m [0m[32mdummy     [0m[32m [0m│[1;32m [0m[1;32mdummy:local:mps-linear-3    [0m[1;32m [0m│[32m [0m[32m       3[0m[32m [0m│[32m [0m[32mavailable   [0m[32m [0m│[32m [0m[32msim   [0m[32m [0m│
╰────────────┴──────────────────────────────┴──────────┴──────────────┴────────╯

[2mCache:[0m
    originq: [1;36m6[0m backends, updated 6d ago [1;33m([0m[33mstale[0m[1;33m)[0m
    quafu: [1;36m16[0m backends, updated 10d ago [1;33m([0m[33mstale[0m[1;33m)[0m
    ibm: [1;36m3[0m backends, updated 10d ago [1;33m([0m[33mstale[0m[1;33m)[0m
    quark: [1;36m15[0m backends, updated 6d ago [1;33m([0m[33mstale[0m[1;33m)[0m

== uniqc simulate bell.originir --shots 256 ==
[3m      Simulation Results       [0m
┏━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┓
┃[1m [0m[1mState[0m[1m [0m┃[1m [0m[1mCount[0m[1m [0m┃[1m [0m[1mProbability[0m[1m [0m┃
┡━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━┩
│ 00    │ 127   │ 50.0%       │
│ 11    │ 127   │ 50.0%       │
└───────┴───────┴─────────────┘

== uniqc submit bell.originir --backend dummy -s 64 --wait --format json ==
[1m{[0m
  [32m"task_id"[0m: [32m"uqt_7dae8f1ba45440489cee3628a51cceb2"[0m,
  [32m"backend"[0m: [32m"dummy:local:simulator"[0m,
  [32m"shots"[0m: [1;36m64[0m
[1m}[0m
[1m{[0m
  [32m"counts"[0m: [1m{[0m
    [32m"00"[0m: [1;36m32[0m,
    [32m"11"[0m: [1;36m32[0m
  [1m}[0m,
  [32m"probabilities"[0m: [1m{[0m
    [32m"00"[0m: [1;36m0.5[0m,
    [32m"11"[0m: [1;36m0.5[0m
  [1m}[0m,
  [32m"shots"[0m: [1;36m64[0m,
  [32m"platform"[0m: [32m"dummy"[0m,
  [32m"task_id"[0m: [32m"uqt_7dae8f1ba45440489cee3628a51cceb2"[0m,
  [32m"backend_name"[0m: [32m"dummy:local:simulator"[0m,
  [32m"execution_time"[0m: null,
  [32m"error_message"[0m: null
[1m}[0m

== uniqc task list (most recent few) ==
[3m                                     Tasks                                      [0m
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃[1m [0m[1mTask ID          [0m[1m [0m┃[1m [0m[1mPlatform         [0m[1m [0m┃[1m [0m[1mStatus [0m[1m [0m┃[1m [0m[1mShots[0m[1m [0m┃[1m [0m[1mSubmit Time       [0m[1m [0m┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ uqt_7dae8f1ba454… │ dummy:local:simu… │ success │ 64    │ 2026-05-16T12:59:… │
│ uqt_05bb167b019e… │ dummy:local:simu… │ success │ 64    │ 2026-05-16T12:59:… │
│ uqt_b19692f7129b… │ dummy:local:simu… │ success │ 128   │ 2026-05-16T12:59:… │
│ uqt_57729c1ef451… │ dummy:local:mps-… │ success │ 400   │ 2026-05-16T12:58:… │
│ uqt_14cfd1790a0f… │ dummy:local:mps-… │ success │ 256   │ 2026-05-16T12:58:… │
└───────────────────┴───────────────────┴─────────┴───────┴────────────────────┘
```

