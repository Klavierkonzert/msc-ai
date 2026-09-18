# Evolutionary Design

Coursework and experiments for the **Evolutionary Design** module of the Bio-Inspired Artificial Intelligence (BIA) course.

This module focuses on the evolution of 3D artificial creatures using the [Framsticks](https://www.framsticks.com/) simulator coupled with evolutionary algorithms implemented using the [DEAP](https://github.com/DEAP/deap) framework in Python.

---

## Assignments

* **[Assignment 3: Mutation Intensity in Evolutionary Algorithms](./assignments/Assignment%203%20-%20Mutation%20Intensity%20in%20Evolutionary%20Algorithms/README.md)**: Investigating the influence of mutation intensity on search performance, premature convergence, local optima, and the critical role of crossover.
* **[Assignment 4: EA with Different Genome Encodings](./assignments/Assignment%204%20-%20EA%20with%20different%20genome%20encodings/README.md)**: Comparing structural representations ($f_0, f_1, f_4, f_9$), analyzing neutral plateaus on uneven terrain, and formulating justified fitness modifications to guide evolution out of plateaus.

---

## Setup & Installation Instructions

### Automated Setup (One Command)
If you already have `Framsticks<ver>/` and `framspy-download/` in this folder, you can run the automated setup script which installs `requirements.txt`, copies `.sim` files, downloads `uneven-ground.sim`, and verifies the simulator library:

```powershell
# Windows (PowerShell):
.\setup.ps1
```
```bash
# Linux / macOS / Git Bash:
./setup.sh
```

---

### Manual Setup Step-by-Step

### 1. Download the Framsticks Simulator

* Download the most recent Framsticks build zip from [http://www.framsticks.com/apps-devel](http://www.framsticks.com/apps-devel).
* Uncompress the zip into this directory (e.g. `Framsticks55/`).
* Note the directory containing the shared library (`frams-objects.dll` on Windows, `frams-objects.so` on Linux, `frams-objects.dylib` on macOS) — the Python scripts require this path via the `-path` argument.

### 2. Download the Python Interface (`framspy`)
* Download the `framspy` repository ([https://www.framsticks.com/svn/framsticks/framspy/](https://www.framsticks.com/svn/framsticks/framspy/)) using an SVN or Git-SVN client:
  ```bash
  # Using SVN:
  svn checkout https://www.framsticks.com/svn/framsticks/framspy/ framspy-download
  ```
  *(Note: The Framsticks SVN certificate encrypts communication but may generate a domain verification warning).*

### 3. Install DEAP
Install the [DEAP](https://github.com/DEAP/deap) evolutionary computation library into your active Python / Conda environment:
```bash
# Option A: Install from local external clone:
git clone https://github.com/DEAP/deap.git ../external/deap
pip install -e ../external/deap

# Option B: Direct install via pip:
pip install deap
```

### 4. Copy Simulation (`.sim`) Settings
Copy all simulation configuration (`.sim`) files from `framspy-download/` to the `data/` directory of your Framsticks distribution:
```bash
# Bash:
cp framspy-download/*.sim $(ls -d Framsticks*/data | sort -V | tail -n 1)

# Additional uneven terrain simulation for Assignment 4:
curl -s -o $(ls -d Framsticks*/data | sort -V | tail -n 1)/uneven-ground.sim https://www.cs.put.poznan.pl/mkomosinski/uneven-ground.sim
```
*(PowerShell equivalent:)*
```powershell
$framsData = (Get-ChildItem -Directory Framsticks* | Sort-Object Name -Descending | Select-Object -First 1).FullName + "\data"
Copy-Item framspy-download\*.sim $framsData\ -Force
Invoke-WebRequest -Uri "https://www.cs.put.poznan.pl/mkomosinski/uneven-ground.sim" -OutFile "$framsData\uneven-ground.sim"
```

### 5. Verify Interoperation
Test that the Python bindings communicate properly with the native Framsticks binary library:
```bash
python framspy-download/frams-test.py Framsticks55
```
Ensure all diagnostic tests complete with `Basic tests OK`.

### 6. Run Baseline Examples
Test the baseline DEAP evolution pipeline:
```bash
# Windows CMD / PowerShell:
python framspy-download/FramsticksEvolution.py -path Framsticks55 -sim "eval-allcriteria.sim" -opt vertpos -generations 10 -popsize 20
```

---

## Running Experiments

### Sequential Execution Across Encodings ($f_0, f_1, f_4, f_9$)
```powershell
$framsPath = (Get-ChildItem -Directory Framsticks* | Sort-Object Name -Descending | Select-Object -First 1).FullName
$F_values = 0, 1, 4, 9
$N_values = 1..10

foreach ($F in $F_values) {
    foreach ($N in $N_values) {
        python framspy-download\FramsticksEvolution.py `
            -path $framsPath `
            -sim "eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim;uneven-ground.sim" `
            -opt vertpos `
            -max_numparts 30 `
            -genformat $F `
            -popsize 50 `
            -generations 50 `
            -hof_size 1 `
            -hof_savefile "HoF-f$F-$N.gen"
    }
}
```

### Parallel Execution
```bash
conda activate framsticks
python scripts/run_parallel.py \
    --script framspy-download/FramsticksEvolution.py \
    --frams-path "Framsticks55" \
    --num-experiments 10 \
    --stats-dir stats \
    --out runs \
    --workers 20 \
    --popsize 100 \
    --generations 300 \
    --tournament 10 \
    --genformats 0 1 4 9 \
    --sim "eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim;uneven-ground.sim"
```

### Analyzing Results and Building Plots
```bash
python scripts/analyze_hof.py \
    --logbook-dirs "stats/fitness = vertpos" "stats/fitness = vertpos + justified numparts"
```

---

## Directory Structure

```
Evolutionary Design/
├── assignments/
│   ├── Assignment 3 - Mutation Intensity in Evolutionary Algorithms/
│   └── Assignment 4 - EA with different genome encodings/
├── Framsticks55/               # Framsticks engine and binaries
│   ├── data/                   # Simulation files (*.sim) and scripts
│   └── frams-objects.dll       # Native simulation library
├── framspy-download/           # Python Framsticks interface & DEAP scripts
│   ├── FramsticksEvolution.py  # Main evolutionary loop
│   ├── frams-test.py           # Verification script
│   └── *.sim                   # Evaluation and physics settings
├── scripts/
│   ├── run_parallel.py         # Multi-worker parallel runner
│   └── analyze_hof.py          # Logbook analytics and visualization
├── stats/                      # Serialized DEAP logbooks (*.pkl)
└── runs/                       # Output logs and Hall-of-Fame genotypes (*.gen)
```
