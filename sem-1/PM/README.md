<div align="center">

# Process Mining & Business Process Management (PM)
### Master's Coursework — Artificial Intelligence (Semester 1)
**Aliaksandr Kladneu**, Master's Student in Artificial Intelligence

</div>

---

## Overview

This repository contains the coursework, lab assignments, and term projects for the **Process Mining & Business Process Management** course. The curriculum covers the complete lifecycle of business process engineering:
1. **Design & Execution**: Modeling executable business workflows using BPMN 2.0 and executing them in modern Business Process Management Systems (jBPM / KIE Workbench).
2. **Process Discovery & Conformance**: Mining real-world event logs, discovering formal Petri nets and Process Trees, evaluating conformance metrics (Fitness, Precision, Generalization, Simplicity), and diagnosing operational bottlenecks (PM4Py, Fluxicon Disco).
3. **Operational Optimization**: Formulating and solving discrete optimization problems in business workflows using mathematical constraint programming (MiniZinc).

---

## Projects Overview

| Project | Domain / Topic | Core Technologies | Description | Direct Link |
| :--- | :--- | :--- | :--- | :---: |
| **Project 1** | **Business Process Modeling**<br>*(The Witcher 3 Quest)* | **jBPM 7**, **BPMN 2.0**, Java, HTML Forms | Executable workflow model of the "Ghosts of the Past" narrative quest from *The Witcher 3: Wild Hunt*. Features 3 embedded sub-processes, XOR/AND/OR gateways, interactive user task forms, process variable state management, and timer boundary events. | [Open Project 1](Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest/README.md) |
| **Project 2** | **Process Discovery & Event Log Mining**<br>*(Hospital Sepsis Pathways)* | **PM4Py**, **Fluxicon Disco**, Python, Scikit-Learn | Comprehensive process mining audit on a clinical sepsis event log (1,050 patient traces). Implements Inductive Miner and Heuristics Miner (C-nets), compares raw vs. macro-path and grouped diagnostic sub-processes, performs Token-Based Replay (TBR) decision mining, and explores temporal bottlenecks in Disco. | [Open Project 2](Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/README.md) |
| **Project 3** | **Mathematical Modeling & Optimization**<br>*(Battery Storage & Microgrid Dispatch)* | **MiniZinc**, Constraint Programming, Python | Discrete constraint optimization model minimizing daily operational costs for an energy consumer with solar generation, grid interaction, and battery storage. Computes optimal charging, discharging, and peak-shaving schedules under dynamic pricing. | [Open Project 3](Projects/Project%203%20-%20Mathematical%20Modeling/README.md) |

---

## Project Summaries

### [Project 1: Business Process Modeling — The Witcher Quest](Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest/README.md)
* **Goal**: Transform a complex branching video game narrative into an executable, stateful BPMN 2.0 process.
* **Key Components**:
  - **Sub-process Decomposition**: Segmented into *The Farmstead*, *Finding Louis*, and *Dealing with Bounty Hunters*.
  - **Decision Points & Concurrency**: OR-splits for concurrent looting during timed pursuit, XOR branches for combat and narrative choices, and AND joins for synchronized task completion.
  - **State & Data Objects**: Custom Java data class `Quest` managing inventory (`loot`) and cumulative rewards (`totalReward`).
  - **Interactive Forms**: Task forms for user choices, dialogue branching, and perception inputs (`triggeredTraps`).
* **Artifacts**: Standalone [`Quest.bpmn`](Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest/Quest.bpmn), packaged deployment [`WitcherQuest.zip`](Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest/WitcherQuest.zip), and detailed visual documentation.

---

### [Project 2: Event Log and Process Model Discovery](Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/README.md)
* **Goal**: Perform an end-to-end process mining audit on a real-life hospital ERP event log of patients presenting with suspected sepsis.
* **Key Components**:
  - **Three-Tier Process Discovery**:
    1. *Baseline*: Raw log discovery highlighting the "spaghetti effect" caused by repeated ambient laboratory draws.
    2. *Macro-Path Abstraction*: Filtering ambient blood tests to reveal the clean organizational spine ($F_1 > 0.92$).
    3. *Pattern Sub-Process Aggregation*: Grouping contiguous blood draws into a `Diagnostic Lab Panel` sub-process, achieving a sound, clinically complete Process Tree ($F_1 = 0.8697$).
  - **Decision Mining (TBR Classifiers)**: Token-based replay mapping clinical intake attributes (`InfectionSuspected`, `Hypotensie`, `Age`) to downstream routing splits (`Admission IC` vs. `Admission NC` vs. outpatient discharge).
  - **Disco Process Map & Bottleneck Analysis**: Directly-Follows Graph (DFG) frequency and delay analysis exposing the 2.5-hour ER boarding bottleneck and the 47.3-day outpatient relapse window.
* **Artifacts**: Executable Jupyter Notebook [`event_log_analysis.ipynb`](Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/event_log_analysis.ipynb), event log [`Sepsis.xes`](Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining/Sepsis.xes), process models, and formal report.

---

### [Project 3: Mathematical Modeling](Projects/Project%203%20-%20Mathematical%20Modeling/README.md)
* **Goal**: Formulate and solve an energy management constraint optimization problem using MiniZinc.
* **Key Components**:
  - **Objective**: Minimize total operating cost (grid purchase costs + battery degradation costs − feed-in earnings).
  - **Constraints**: Battery State of Charge (SoC) balance, charge/discharge efficiency limits, grid intake caps, and peak-shaving thresholds.
  - **Validation**: Time-series visualization of generation, consumption, battery dynamics, and economic dispatch across all optimization periods.
* **Artifacts**: MiniZinc model [`model.mzn`](Projects/Project%203%20-%20Mathematical%20Modeling/model.mzn), data instance [`data.dzn`](Projects/Project%203%20-%20Mathematical%20Modeling/data.dzn), output schedule [`solution.csv`](Projects/Project%203%20-%20Mathematical%20Modeling/solution.csv), and analytical report [`README.md`](Projects/Project%203%20-%20Mathematical%20Modeling/README.md).

---

## Laboratory Assignments (`Labs/`)

The [`Labs/`](Labs/) directory contains hands-on practical exercises exploring fundamental process mining algorithms:
- **`LW1`**: Introduction to process modeling and workflow simulation.
- **`LW5`**: Event log analysis and exploratory data statistics (`teleclaims.xes`).
- **`06_Alpha_algorithm`**: Implementation and evaluation of the classic $\alpha$-miner algorithm and footprint matrices.
- **`LW9` & `LW10`**: Mathematical programming and discrete optimization exercises in MiniZinc.
