# Biologically Inspired Algorithms (BIA)

This repository contains coursework and projects for the **Bio-Inspired Algorithms (BIA)** curriculum, split into two primary domains:
1. [`Combinatorial Optimization/`](./Combinatorial%20Optimization/): Metaheuristics (Local Search, Tabu Search, Simulated Annealing) applied to Quadratic Assignment Problems (QAP) implemented in C++ (C++20, OpenMP) with plotting powered by `matplotlib-cpp`.
2. [`Evolutionary Design/`](./Evolutionary%20Design/): Morphological evolution of 3D artificial creatures using [Framsticks](https://www.framsticks.com/) and [DEAP](https://github.com/DEAP/deap) in Python, investigating mutation intensity and genetic encodings ($f_0, f_1, f_4, f_9$).

---

## Repository Structure

```
BIA/
├── CMakeLists.txt              # Top-level CMake build configuration for C++ tasks
├── external/                   # External / third-party libraries
│   ├── deap/                   # DEAP evolutionary computation library (Python)
│   └── matplotlib-cpp/         # C++ wrapper for Python Matplotlib
├── Combinatorial Optimization/ # C++ metaheuristics for QAP
├── Evolutionary Design/        # Python Framsticks + DEAP experiments
└── README.md                   # Repository guide and setup instructions
```

---

## External Libraries Setup (`external/`)

All third-party libraries are organized in the [`external/`](./external/) directory.

### 1. DEAP (Distributed Evolutionary Algorithms in Python)

* **Source**: [https://github.com/DEAP/deap](https://github.com/DEAP/deap)
* **Location**: `external/deap`
* **Role**: Provides the evolutionary algorithm components (genetic operators, selection mechanisms, Hall of Fame, statistics logbooks) used by `FramsticksEvolution.py`.



### 2. `matplotlib-cpp` (C++ Matplotlib Wrapper)

* **Source**: [https://github.com/lava/matplotlib-cpp](https://github.com/lava/matplotlib-cpp)
* **Location**: `external/matplotlib-cpp`
* **Role**: Header-only C++ wrapper allowing C++ code to invoke Python's `matplotlib.pyplot` for generating benchmark plots.

#### CRITICAL: Required Custom Function (`set_yscale`)
The upstream `matplotlib-cpp` library lacks `set_yscale` / `set_xscale` functions. The assignments in `Combinatorial Optimization` (specifically in [`src/plotting.cpp`](./Combinatorial%20Optimization/src/plotting.cpp#L671)) require `plt::set_yscale(...)` for logarithmic and symlog plots.

If downloading a fresh clone of `matplotlib-cpp` from GitHub, you **must add the following function** inside `namespace matplotlibcpp` in `external/matplotlib-cpp/matplotlibcpp.h`:

```cpp
    // Required by Combinatorial Optimization plotting (not native to matplotlib-cpp)
    inline void set_yscale(const std::string &scale)
    {
        detail::_interpreter::get();

        PyObject* args = PyTuple_New(1);
        PyTuple_SetItem(args, 0, PyString_FromString(scale.c_str()));
        PyObject* kwargs = PyDict_New();

        PyObject *ax = PyObject_CallObject(detail::_interpreter::get().s_python_function_gca,
                                           detail::_interpreter::get().s_python_empty_tuple);
        if (!ax) throw std::runtime_error("Call to gca() failed.");
        Py_INCREF(ax);

        PyObject *set_yscale = PyObject_GetAttrString(ax, "set_yscale");
        if (!set_yscale) throw std::runtime_error("Attribute set_yscale not found.");
        Py_INCREF(set_yscale);

        PyObject *res = PyObject_Call(set_yscale, args, kwargs);
        if (!res) throw std::runtime_error("Call to set_yscale() failed.");
        Py_DECREF(set_yscale);

        Py_DECREF(ax);
        Py_DECREF(args);
        Py_DECREF(kwargs);
        Py_DECREF(res);
    }
```

---

## Automated Setup Script

Run the following commands from the `BIA/` root directory to ensure both libraries are present and configured:

### Bash / Linux / macOS:
```bash
# 1. Create external folder
mkdir -p external

# 2. Clone or update DEAP
if [ ! -d "external/deap" ]; then
    git clone https://github.com/DEAP/deap.git external/deap
fi
pip install -e external/deap

# 3. Clone matplotlib-cpp
if [ ! -d "external/matplotlib-cpp" ]; then
    git clone https://github.com/lava/matplotlib-cpp.git external/matplotlib-cpp
fi
```

### PowerShell (Windows):
```powershell
# 1. Create external folder
if (-not (Test-Path "external")) { New-Item -ItemType Directory -Path "external" | Out-Null }

# 2. Clone or update DEAP
if (-not (Test-Path "external\deap")) {
    git clone https://github.com/DEAP/deap.git external/deap
}
pip install -e external/deap

# 3. Clone matplotlib-cpp
if (-not (Test-Path "external\matplotlib-cpp")) {
    git clone https://github.com/lava/matplotlib-cpp.git external/matplotlib-cpp
}
```
