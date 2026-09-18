# Process Mining & Business Process Management (PM)
## Master's Coursework & Term Projects &bull; Semester 1

This repository contains the coursework notes, [3 term projects](./Projects/) and laboratory exercises for the **Process Mining & Business Process Management** curriculum. The subject covers the end-to-end lifecycle of process mining - from initial business workflow specification and process discovery algorithms to conformance checking and mathematical optimization.


## Coursework & Curriculum Topics

The course combines theoretical foundations with algorithmic implementations across the following core areas:

1. Process Model Representations. Semantics & Verification
   - **Formal Representations**: Transition Systems, Petri Nets, Workflow Nets (WF-nets), BPMN 2.0, Causal Nets (C-nets), and Process Trees.
   - **Semantics & Properties**: Firing rules, reachability/coverability graphs, structural and behavioral **soundness**, liveness, boundedness, and process equivalence.
   - **Model Verification & Performance**: Model-based verification, Key Performance Indicators (KPIs), temporal/delay analysis, bottleneck identification, and statistical reasoning on process knowledge models.

2. Event Logs & Local Pattern Mining
   - **Event Data Standards - IEEE XES**
   - **Local Patterns Mining**: association rules, sequential patterns, and episodes using the _Apriori algorithm_.

3. **Process Model Discovery**
   - Problem formulation and the four quality criteria: **Fitness**, **Precision**, **Generalization**, and **Simplicity**.
   - **Classical & Regional Miners**: $\alpha$-algorithm, state-based regions, language-based regions, and evolutionary/genetic algorithms.
    - **Heuristics Miner**: Frequency-based dependency measures for robust causal net discovery under noise.
    - **Inductive Miner**: Divide-and-conquer log partitioning guaranteeing sound, block-structured process trees.

4. Conformance Checking & Model Evaluation
     - **Approximate Conformance Techniques**: Footprint comparison matrices, naïve fitness, and Token-Based Replay (TBR).
     - **Exact Conformance (Trace Alignments)**: Optimal synchronous, model, and log move alignments between event traces and process models.
     - **Alignment-based calculations for Quality Metrics:** Fitness, Precision, and Generalization.

5. Mathematical Modeling & Linear Programming (LP / MILP)
   - Foundations of constrained optimization problems using Linear Programming (LP) and Mixed-Integer Linear Programming (MILP).
   - **Algorithms & Solvers**: Simplex algorithm, Branch-and-Bound, and declarative modeling languages and solvers (MiniZinc).
   - **Modeling Techniques**: Linearization of non-linear logic, indicator variables, Big-M constraints, and scheduling design patterns.

## Projects Overview

| Project | Domain / Topic | Core Technologies | Goal | Description & Key Deliverables |
| :--- | :--- | :--- | :--- | :--- |
| **[Project 1](Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest/README.md)** | **Business Process Modeling**<br>*(The Witcher 3 Quest)* | **jBPM 7**, **BPMN 2.0**, Java, HTML Forms | Transform a complex branching video game narrative into an executable, stateful BPMN 2.0 process. | [Executable workflow model](Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest/WitcherQuest.zip) of "Ghosts of the Past" from *The Witcher 3*. Implements 3 embedded sub-processes, XOR/AND/OR gateways, custom Java objects, interactive user task forms, process variable state management. |
| **[Project 2](Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/README.md)** | **Process Discovery & Event Log Mining**<br>*(Hospital Sepsis Pathways)* | **PM4Py**, **Fluxicon Disco**, Python, Scikit-Learn | Conduct an end-to-end process mining audit on a real-life hospital ERP event log of suspected sepsis cases. | [Audit report](./Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/report.pdf) of 1,050 clinical patient traces. [Event log analysis](./Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/event_log_analysis.ipynb) features three-tier preprocessing (baseline, macro-path filtering, diagnostic panel aggregation), process model discovery using Heuristics Miner (C-nets), Inductive Miner (Process Trees) and Fuzzy Miner (in Disco), Token-Based Replay (TBR) decision mining, conformance checking, and explores temporal bottlenecks.
| **[Project 3](Projects/Project%203%20-%20Mathematical%20Modeling/README.md)** | **Mathematical Modeling & Optimization**<br>*(Battery Storage & Microgrid Dispatch)* | **MiniZinc**, MILP / Constraint Programming, Python | Formulate and solve an energy management constraint optimization problem using MiniZinc. | Discrete constraint optimization [model](Projects/Project%203%20-%20Mathematical%20Modeling/model.mzn) minimizing operating costs for an energy consumer with solar PV generation, dynamic grid pricing, and battery storage (BESS). Enforces AC bus power balance, battery degradation wear costs, peak-shaving, and non-negative sales.|

## Laboratory Exercises ([`Labs/`](./Labs/))

Hands-on exercises and practical implementations throughout the semester:
- **`LW1`**: Introduction to process modeling and workflow simulation.
- **`LW5`**: Event log exploration and data statistics (`teleclaims.xes`).
- **`06_Alpha_algorithm`**: Implementation and evaluation of the classic $\alpha$-miner algorithm and footprint matrices.
- **`LW9` & `LW10`**: Mathematical programming, linearization techniques, and discrete optimization in MiniZinc.
