# M.Sc. in AI @ PUT

This directory contains the primary codebases, term projects, and experimental studies developed during the first and the second (current) semesters of the Master's program. Projects combine algorithm development, experimental evaluation, data analysis and mathematical methods.
> Some specialized research projects are maintained in dedicated standalone repositories (forks).
> The repository is continuously updated as the programm progresses.

## [Semester 1](./sem-1/)
### Core Engineering Projects & Modules


<table>
  <thead>
    <tr>
      <th style="width: 18%;">Course Module / Link</th>
      <th style="width: 18%;">Project Domain</th>
      <th style="width: 15%;">Tech Stack</th>
      <th style="width: 37%;">Project Focus & Key Deliverables</th>
      <th style="width: 12%;">Status</th>
    </tr>
  </thead>
  <tbody>
    <!-- Process Mining (3 rows) -->
    <tr>
      <td rowspan="3">
        <a href="./sem-1/PM/"><strong>Process Mining (PM)</strong></a>
      </td>
      <td><strong><a href="./sem-1/PM/Projects/Project%201%20-%20Business%20Process%20Modeling%20-%20The%20Witcher%20Quest">Business Process Modeling/Workflow Systems</a></strong></td>
      <td><code>jBPM 7</code><br><code>BPMN 2.0</code><br><code>Java</code></td>
      <td>Executable BPMN 2.0 narrative workflow modeling the "Ghosts of the Past" quest from <em>The Witcher 3</em> with embedded sub-processes, complex gateways, and stateful task forms.</td>
      <td><code>Completed</code></td>
    </tr>
    <tr>
      <td><strong><a href="./sem-1/PM/Projects/Project%202%20-%20Event%20Log%20-%20Process%20Mining#project-2-event-log-and-process-model-discovery">Event Log, Process Discovery & Conformance</a></strong></td>
      <td><code>PM4Py</code><br><code>Python</code><br><code>Disco</code></td>
      <td>Hospital ERP audit on 1,050 suspected sepsis traces; multi-tier abstraction, Process Tree discovery, and Woflan Petri net soundness verification.</td>
      <td><code>Needs revision</code></td>
    </tr>
    <tr>
      <td><strong><a href="./sem-1/PM/Projects/Project%203%20-%20Mathematical%20Modeling">Mathematical Modeling / MILP</a></strong></td>
      <td><code>MiniZinc</code></td>
      <td>Microgrid dispatch optimization model minimizing daily operating costs under dynamic pricing and battery degradation.</td>
      <td><code>Needs revision</code></td>
    </tr>
    <!-- Bio-Inspired Algorithms (2 rows) -->
    <tr>
      <td rowspan="2">
        <a href="./sem-1/BIA/"><strong>Bio-Inspired Algorithms (BIA)</strong></a>
      </td>
      <td><strong><a href="./sem-1/BIA/Combinatorial%20Optimization/">Combinatorial Optimization</a></strong></td>
      <td><code>C++20</code><br><code>OpenMP</code><br><a href="https://github.com/lava/matplotlib-cpp"><code>matplotlib</code></a></td>
      <td>High-performance multi-start Local Search, Tabu Search, and Simulated Annealing for QAP with statistical budget scaling.  [<a href="./sem-1/BIA/Combinatorial%20Optimization/assignment_12_tasks.cpp">code</a>] [<a href="./sem-1/BIA/Combinatorial%20Optimization/src/">src</a>] [<a href="./sem-1/BIA/Combinatorial%20Optimization/assignments/Assignment%202%20-%20SA%20+TS%20in%20QAP/QAP_extended_report.pdf">report</a>]</td>
      <td><code>Completed</code></td>
    </tr>
    <tr>
      <td><strong><a href="./sem-1/BIA/Evolutionary%20Design">Evolutionary Design & Optimization</a></strong></td>
      <td><code>Python</code><br><a href="https://github.com/DEAP/deap"><code>DEAP</code></a><br><a href="https://www.framsticks.com/"><code>Framsticks</code></a></td>
      <td>Morphological evolution of 3D autonomous creatures in Framsticks; empirical investigation into how genetic representations, operator dynamics, and fitness landscape topology govern the evolvability and locomotion of embodied agents.</td>
      <td><code>Pending</code></td>
    </tr>
    <!-- Program Synthesis (1 row) -->
    <tr>
      <td>
        <strong>Program Synthesis</strong><br>
        <a href="https://github.com/Klavierkonzert/SymRegEML"><code>/SymRegEML</code></a>
      </td>
      <td><strong>Symbolic Regression</strong></td>
      <td><code>Python</code><br><code>RJMCMC</code><br><code>SymPy</code></td>
      <td><em>Bayesian Symbolic Regression on EML-Trees</em> - evaluated <em>the single-operator + const</em> functional basis in BSR; analyzed theoretical connections to Kolmogorov-Arnold representations, multi-tree MCMC proposal dynamics, and mitigated exponential numerical instability via domain restriction and simulated annealing. [<a href="https://github.com/Klavierkonzert/SymRegEML/codes/">code</a>] [<a href="https://github.com/Klavierkonzert/SymRegEML/README.md/">report</a>]</td>
      <td><code>Completed</code></td>
    </tr>
    <!-- Machine Perception (1 row) -->
    <tr>
      <td>
        <strong>Machine Perception</strong><br>
        <a href="https://github.com/Klavierkonzert/dppo"><code>/dppo</code></a>
      </td>
      <td><strong>Reinforcement Learning & Robotics</strong></td>
      <td><code>PyTorch</code><br><code>MuJoCo</code><br><code>Gym</code></td>
      <td><em>Diffusion Policy Policy Optimization (DPPO)</em> - fine-tuned continuous diffusion control policies on the Franka Kitchen robotic benchmark; surpassed the standard 5-skill baseline to successfully achieve <strong>7 sequential manipulation tasks</strong>.</td>
      <td><code>Needs revision</code></td>
    </tr>
  </tbody>
</table>

### Theoretical & Analytical Coursework
* **Multivariate Statistics**: High-dimensional hypothesis testing (MANOVA, multivariate normality), covariance structures, PCA, and discriminant analysis.
* **Machine Learning Theory**: PAC learning framework, Empirical Risk Minimization (ERM), surrogate loss functions, uniform convergence, and Vapnik–Chervonenkis (VC) dimension bounds.
* **Multiobjective Optimization (MOO)**: Pareto optimality foundations and evolutionary multi-objective algorithms (NSGA-II, NSGA-III).
  
## [Semester 2](https://github.com/Klavierkonzert/msc-ai/tree/sem-2) `[In Development]`

### Theoretical & Analytical Coursework
...
## Curriculum
For the complete 3-semester official syllabus and lecture catalog across the entire degree program, see **[curriculum.md](./curriculum.md)**
