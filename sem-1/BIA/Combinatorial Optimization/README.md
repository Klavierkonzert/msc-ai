# BIA Lab 1 & 2 - Quadratic Assignment Problem
## Overview
This project implements and compares heuristic/metaheuristic algorithms for the Quadratic Assignment Problem (QAP). It loads QAPLIB-style `.dat` and `.sln` instances, runs multiple algorithms across selected benchmark problems, collects quality/time/efficiency statistics, and generates plots for analysis, which are used in the report.

### Main results
See the 3rd version of the report -[`final_report.pdf`](./final_report.pdf) - for results and conclusions. Two previous versions of the report can be found in the [`assignments/`](./assignments/) folder.

### Experiment tasks
 | Task | Description |
|---|---|
| [`2`](assignment_12_tasks.cpp#L299) | Compare local search, random methods, simulated annealing, adaptive SA, and tabu search across selected QAP instances |
| [`345`](assignment_12_tasks.cpp#L807) | Run tasks 3, 4, and 5 on selected interesting problems |
| [`3`](assignment_12_tasks.cpp#L843) | Initial vs final quality analysis |
| [`4`](assignment_12_tasks.cpp#L892) | Multi-run behavior and analysis |
| [`5`](assignment_12_tasks.cpp#L936) | Local optima similarity, Hamming/Cayley similarity, and position-match correlation analysis |

## Requirements

- C++20 compatible compiler
- https://github.com/lava/matplotlib-cpp
- Python
- matplotlib
- numpy

## Python dependencies

```bash
pip install matplotlib numpy
```

## Implemented algorithms for QAP
See  [`src/algorithms.cpp`](src/algorithms.cpp):
- [Heuristic local search](src/algorithms.cpp#L236)
- [Steepest local search](src/algorithms.cpp#L401)
- [Greedy local search](src/algorithms.cpp#L542)
- [Random search](src/algorithms.cpp#L664)
- [Random walk](src/algorithms.cpp#L729)
- [Simulated annealing](src/algorithms.cpp#L935)
- [Adaptive simulated annealing with Lam-like schedule](src/algorithms.cpp#L1087)
- [Tabu search with elite candidate list and tabu tenure](src/algorithms.cpp#L1376)

## Project structure
| Path | Purpose |
|---|---|
| [`assignment_12_tasks.cpp`](assignment_12_tasks.cpp) | Main entry point, CLI parsing, task orchestration |
| [`src/algorithms.cpp`](src/algorithms.cpp) | QAP optimization algorithms |
| [`src/cost.cpp`](src/cost.cpp) | QAP cost and swap-delta evaluation |
| [`src/statistics.cpp`](src/statistics.cpp) | Experiment result collection and aggregation |
| [`src/plotting.cpp`](src/plotting.cpp) | Matplotlib-based plots |
| [`src/problem.cpp`](src/problem.cpp) | QAP problem abstraction |
| [`src/matrix.cpp`](src/matrix.cpp) | Matrix container and cached matrix properties |
| [`src/permutation.cpp`](src/permutation.cpp) | Permutation representation and distance metrics |
| [`src/random.cpp`](src/random.cpp) | Contains random generators used, for example, for reshuffling a permutation. Each cpu used during experiments will run independent random generators, which will be reused until problem size changes (i.e. a new problem will be processed)|
| [`src/dataloaders.cpp`](src/dataloaders.cpp) | `.dat` / `.sln` loading |
| [`QAP data/`](./QAP%20data/) | Benchmark instances ( `.dat` and `.sln`) from QAPLIB (download instances from https://qaplib.mgi.polymtl.ca/) |
| [`Figures/`](./Figures/) | Generated experiment plots |
| [`assignments/`](./assignments/) | Reports and assignment deliverables |


## QAP Data
QAP instances are expected in [`QAP data/`](./QAP%20data/) as matching `.dat` and `.sln` files. The selected benchmark instances are documented in [`QAP data/README.md`](./QAP%20data/README.md), and their structural properties are summarized in [`QAP data/Properties of the selected QAP instances.md`](./QAP%20data/Properties%20of%20the%20selected%20QAP%20instances.md).

## The Problems Analysed
Default benchmark set:
- Proven optimum: `esc16d`, `bur26h`, `esc32e`, `lipa80b`, `lipa40a`
- Best-known solution: `wil100`, `tho150`, `tai100b`, `tai80b`, `tai150b`, `tai256c`

Some mathematical properties of these problems can be found here: [`QAP data/Properties of the selected QAP instances.md`](./QAP%20data/Properties%20of%20the%20selected%20QAP%20instances.md).

## Build With CMake

```bash
cmake -S . -B build
cmake --build build --config Release
```

The repository/folder also contains VS Code build configuration in [`.vscode/tasks.json`](../.vscode/tasks.json), [`.vscode/launch.json`](../.vscode/launch.json).

## Main entry point, run examples
[`main(...)`](assignment_12_tasks.cpp#L128) entry point: [`\assignment_12_tasks.cpp`](\assignment_12_tasks.cpp)
 User is encouraged to use the following arguments while running from console: 
 - `--parallel`, `--no-parallel` - define whether all the experiments will be run in parallel (using maximum or `--cores ...` logical cores) or sequentially (using one core).
 - `--no-windows` - all the Matplotlib windows will be discarded and plots will be saved silently.
 - `--tasks`, e.g. `tasks 2` or `tasks 345`
  
### Run examples

- Run all default tasks on default problems:
    ```bash
    ./main --no-windows
    ```

- Run only task 2 on selected problems:

    ```bash
    ./main --tasks 2 --problems wil100 tai100b --runs-per-problem 10 --no-windows
    ```
- Parallel execution
  ```bash
  ./main --parallel --cores 8 --runs-per-problem 20 --no-windows
  ```

### CLI Arguments

| Argument | Meaning |
|---|---|
| `--help` | Show usage |
| `--dir <path>` | Directory with QAP `.dat` / `.sln` files |
| `--plots-dir <path>` | Output directory for figures |
| `--fig-size <w> <h>` or `<w>x<h>` | Plot size |
| `--runs-per-problem <n>` | Number of repeated runs per method/problem |
| `--parallel` / `--no-parallel` | Enable or disable OpenMP parallel execution |
| `--cores <n>` | Number of OpenMP threads |
| `--problems` / `-p` | Problem names, space- or comma-separated |
| `--tasks` | Tasks to execute: `2`, `345`, `3`, `4`, `5` |
| `--no-windows` | Save plots without opening Matplotlib windows |

## Metrics 
Collected metrics include:
- final cost
- relative cost quality
- cosine quality
- normalized angular quality
- relative angular quality
- runtime
- number of swaps
- number of evaluated solutions
- Hamming and Cayley distance/similarity to best-known solution
- efficiency metrics based on time-weighted solution quality

## Details and issues

### Implementation Notes
- The [`Matrix`](src/matrix.cpp) class uses row-pointer based storage ([`T**`](src/matrix.cpp#32)) because QAP delta evaluation performs many irregular row accesses such as `B[p[k]][p[i]]`. A contiguous array representation was tested, but row-allocated storage performed better on the benchmark set used in this project.
- **Stopping criteria**:
  - Natural exhaustion of Local Search trajectory
  - Limit on time/number of iterations exceeded. Actual for Random Search, Tabu Search and Simulated Annealing
  - Number of restarts exceeded (as described below).
- **Task 2** performs 10 independent (can be parallelized) runs of the algorithms, meaning statistics are gathered independently. This mainly addresses efficiency calculations only, since the main research question is to measure how well metaheuristics algorithms (Tabu Search and Simulated Annealing) perform with an increased time budget provided, while the other algorithms are just restarted 10 or 100 times each run (not parallelized), as described below.
- **Multi-start implementation within algorithm definitions**:
  All local-search and random-walk algorithms support an internal multi-start (restart) loop controlled by the [`"n_restarts"`](./src/algorithms.cpp#L37) hyperparameter passed via `AlgorithmRunConfig::hyperparameters` map:
  - These restarts are **not parallelized**.
  - The **default** when the key is absent is `n_restarts = 1` (single run). Setting `n_restarts = 0` means *rerun until the time or iteration budget is exhausted*. This is safe by construction: the outer `for` condition `!n_restarts && (max_iterations > 0 || max_time_seconds > 0)` only fires when at least one budget is set, and the inner loop checks and exits via `goto finish` once that budget is hit — so an infinite loop is impossible.
  - **Restart mechanics.** At the start of every restart after the first, the permutation is re-randomised via `p.reshuffle()`, the cost is recomputed from scratch and an algorithm is restarted. Statistics (`best_cost`, `best_p`, efficiency accumulator) are aggregated across all restarts - the global best solution is always preserved.
  - **Statistics**. Global iteration counter is shared across restarts. Returned statistics are shared: current (within a restart) best cost updates the global multi-run best cost (if necessary), efficiency is recalculated with each update.
  - `max_iterations` and `max_time_seconds` can terminate the whole multi-start run early.
  - [`heuristic_local_search_qap`](./src/algorithms.cpp#L236) (100 restarts in Task 2): Each restart runs the heuristic inner loop until no improving swap is found ([`no_improving_swaps = true`](./src/algorithms.cpp#L289)), then *breaks* to the outer restart loop (not `goto finish`). 
  - [`steepest_local_search_qap`](./src/algorithms.cpp#L343) / [`greedy_local_search_qap`](./src/algorithms.cpp#L343) (10 restarts in Task 2): Restart on local-minimum (`improved = false` breaks the inner loop). 
  - [`random_walk_qap`](./src/algorithms.cpp#L761) (10 restarts in Task 2): The total time budget is split equally: each restart receives `max_time_seconds / n_restarts` seconds. Every restart gets fair share of time budget.
  - [`Random Search`](./src/algorithms.cpp#L664) and metaheuristics are explicitly excluded from multi-restart mechanics. Random Search generates a fully independent permutation every iteration, so a restart loop would be functionally identical to more iterations.
  - **Design note.** Extracting the restart loop into a shared wrapper was considered but not done: [`StatisticsAccumulator`](./src/algorithms.cpp#L91) must span the entire multi-start run (its `start_time` is set once before the restart loop, and checkpoints accumulate across restarts); [Random Walk](./src/algorithms.cpp#L761) requires custom per-restart time-slicing; and SA/Tabu do not participate at all. Keeping the ~10-line restart pattern embedded per-algorithm avoids threading the accumulator through an external wrapper and keeps budget semantics local and explicit.
- [**Task 4**](./assignment_12_tasks.cpp#L892) performs 1000 **independent** parallel runs (starts) of Local Search algorithms. Since analysis of efficiency is explicitly excluded in this task, one could run, for instance, 10 restarts within an algorithm, and perform 100 external reruns. The result will be the same. But for the sake of parallezation, in this and subsequent tasks `n_restarts` is set to default value `1`.

### Outputs

Generated plots are saved under `Figures/Run N/`. Reports and assignment write-ups are stored in `assignments/`.

### Minor issues or limitations
- Source files are included directly as `.cpp` files rather than separated into headers and translation units.
- Results involving time-budgeted algorithms depend on machine performance and parallelization settings.
- Matplotlib/Python linkage can be platform-specific. 
- `matplotlibcpp::set_yscale`, `set_xscale` are not native to the library