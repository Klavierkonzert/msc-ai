# BIA Lab 1 & 2 - Quadratic Assignment Problem
## Overview
This project implements and compares heuristic/metaheuristic algorithms for the Quadratic Assignment Problem (QAP). It loads QAPLIB-style `.dat` and `.sln` instances, runs multiple algorithms across selected benchmark problems, collects quality/time/efficiency statistics, and generates plots for analysis, which are used in `assignments/Assignment 2 - SA + TS in QAP/....pdf` report.

### Main results
See [`assignments/Assignment 2 - SA + TS in QAP/....pdf`](./assignments/Assignment%202%20-%20SA%20+TS%20in%20QAP/QAP_extended_report.pdf) report for results and conclusions.


## Requirements

- C++20 compatible compiler
- https://github.com/lava/matplotlib-cpp
- Python
- matplotlib
- numpy

## Python dependencies

pip install matplotlib numpy

## Implemented algorithms for QAP
See  [`src/algorithms.cpp`](src/algorithms.cpp):
- Heuristic local search
- Steepest local search
- Greedy local search
- Random search
- Random walk
- Simulated annealing
- Adaptive simulated annealing with Lam-like schedule
- Tabu search with elite candidate list and tabu tenure

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
| [`QAP data/`](./QAP%20data/) | Benchmark instances from QAPLIB |
| [`Figures/`](./Figures/) | Generated experiment plots |
| [`assignments/`](./assignments/) | Reports and assignment deliverables |


## QAP Data
QAP instances are expected in `QAP data/` as matching `.dat` and `.sln` files. The selected benchmark instances are documented in `QAP data/README.md`, and their structural properties are summarized in `QAP data/Properties of the selected QAP instances.md`.

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

The repository also contains VS Code build configurations in `.vscode/tasks.json`.

## Main entry point, run examples
`main(...)` entry point: `\src\assignment_12.cpp`
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


## Experiment tasks
 | Task | Description |
|---|---|
| [`2`](assignment_12_tasks.cpp#L298) | Compare local search, random methods, simulated annealing, adaptive SA, and tabu search across selected QAP instances |
| [`345`](assignment_12_tasks.cpp#L809) | Run tasks 3, 4, and 5 on selected interesting problems |
| [`3`](assignment_12_tasks.cpp#L845) | Initial vs final quality analysis |
| [`4`](assignment_12_tasks.cpp#L893) | Multi-start behavior and restart analysis |
| [`5`](assignment_12_tasks.cpp#L937) | Local optima similarity, Hamming/Cayley similarity, and position-match correlation analysis |

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
This would be a nice place to document your matrix benchmark conclusion:

The `Matrix` class uses row-pointer based storage (`T**`) because QAP delta evaluation performs many irregular row accesses such as `B[p[k]][p[i]]`. A contiguous array representation was tested, but row-allocated storage performed better on the benchmark set used in this project.

### Outputs

Generated plots are saved under `Figures/Run N/`. Reports and assignment write-ups are stored in `assignments/`.

### Minor issues or limitations
- Source files are included directly as `.cpp` files rather than separated into headers and translation units.
- Results involving time-budgeted algorithms depend on machine performance and parallelization settings.
- Matplotlib/Python linkage can be platform-specific. 
- matplotlibcpp::set_yscale, set_xscale are not native to the library