# Assignment 6: Fitness Landscape Exploration
## Task 1: Probing Landscape Topology across Various Genetic Encodings
### Optimizing Locomotion Velocity of Creatures with Neural Networks

### Objective and Setup

The objective of this task is to discover the topological nature of the combinatorial fitness landscape - its ruggedness, neutrality, mutational locality, and evolvability - for **net rectilinear locomotion speed** ([`velocity`](https://www.framsticks.com/a/al_params.html#exper-perfcalc)) with neural network control across four distinct genetic encodings:

- [**$f_0$**](https://www.framsticks.com/a/al_geno_f0.html) - direct low-level representation (explicit 3D parts, joints, neurons, and synaptic connections).
- [**$f_1$**](https://www.framsticks.com/a/al_geno_f1.html) - recurrent tree-developmental encoding with branching and structural repetition.
- [**$f_4$**](https://www.framsticks.com/a/al_geno_f4.html) - matrix/developmental grammar encoding.
- [**$f_H$**](https://www.framsticks.com/a/al_geno_fh.html) - handle-based indirect representation (elements assemble and fuse based on vector similarity between evolving numerical handles).

Because combinatorial solution spaces cannot be plotted directly against argument values, we study the landscape through **parent-offspring neighborhood probing**: sampling diverse solutions across the fitness spectrum and analyzing the distribution of their 1-step mutational neighbors relative to the $y = x$ reference line.



<div style="break-after: page;"></div>

### Simulation Constraints & EA Parameters

- **Optimization Criterion (Fitness)** - `velocity` with max sampling period $T$ (net rectilinear displacement speed):
  $$v = \frac{\|\mathbf{x}(T) - \mathbf{x}(0)\|}{T}$$
- **Simulation Environment ([`eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim`](..//..//..//Framsticks55/data/))**:
  - **Deterministic Physics (`deterministic.sim`)**: Eliminates sensory and mechanical noise (`randinit: 0.0`, `nnoise: 0.0`, `bnoise_vel: 0.0`) with central placement (`placement: 1`), enabling deterministic, noise-free single-trial evaluation (`evalcount: 1`).
  - **Lifespan Mechanism**: Controlled by metabolic energy consumption with starting energy $E_0 = 10\,000.0 \times n$ and idle metabolism $e_\text{meta} = 1.0 \times n$, yielding a constant lifespan of exactly $T = 10\,000$ simulation steps.
  - **Performance Sampling (`sample-period-longest.sim`)**: Configures `perfperiod: 999999`, which exceeds the lifespan, sampling coordinates strictly at birth ($t=0$) and death ($t=10\,000$) to measure rectilinear velocity without periodic sampling overhead.
- **Morphological Limits**:
  - Max parts: `30` (`-max_numparts 30`)
- **EA Parameters**:
  - **Population size**: `100` (`--popsize 100`)
  - **Generations**: `300` (`--generations 300`)
  - **Selection**: Tournament (`size = 5`)
  - **Crossover probability (`pxov`)**: `0.0` (pure asexual mutation-driven climb)
  - **Mutation probability (`pmut`)**: `0.9` (standard Framsticks rate)
  - **Hall of Fame size**: `1`
  - **Replications**: `48` independent runs per representation (2 batches on 24 CPU cores)


<div style="break-after: page;"></div>

### Experiment design

```mermaid
flowchart LR
    A["Relatively Greedy & Fast Evolutionary Climb<br>(48 runs x 300 gens per encoding)"] --> B["Climbing Solutions Pool<br>(Extracted from logbook.hof_history, serialized inside `stats/<timestamp>/<hof_base>.logbook.pkl`)"]
    A --> CurvesBoxplots["Figures 1, 2: Confidence and mean curves and boxplots of HoF"]
    B --> C["Uniform Fitness Sampling<br>(200+ parents spanning [0, F_max])"]
    C --> D["Neighborhood <br>(20 valid 1-step mutants per parent, invalid or broken genotypes rejected and retried up to 20 times)"]
    C --> ClimbersFitnessDistr["Figure 0: Distribution of Fitness values across unique fitness climbers"]
    D --> E["Figure 4: Landscape Visualizations<br>(Scatter plots with y=x, fixed scale)"]
    D --> N["Table: Neighbourhood characteristics: improvement rates, lethality / fragility rate"]
```

<a id="fig-distribution-parents-climbers"></a>

<p align="center">
  <img src="./results/landscape/climbers_distribution_2x2.png" width="95%" alt="Distribution of Unique Evolutionary Climbers and Selected Parents"/>
  <br>
  <em>Figure 0: Empirical distribution of all unique evolutionary climbers extracted from Phase 1 history (shaded histogram and continuous KDE curve) versus the distribution of the 200 selected parent solutions (red dashed step count), with marginal horizontal quartile diagrams (median and IQR) positioned directly below each panel across the four encodings on aligned shared axes.</em>
</p>


- **Infeasibility Filtering**: Invalid or broken genotypes (`fitness == FITNESS_VALUE_INFEASIBLE_SOLUTION`) are rejected and retried (up to 20 attempts per mutant), recording retry counts to quantify the **lethality / fragility rate** of each encoding.
- **Evaluation**: Each mutant $m$ is evaluated under the identical simulation settings, recording $(F(P), F(m))$, which are depicted on [Figure 4](#fig-parent-mutant-fitness-scatter-plots).



<div style="break-after: page;"></div>

### Results

48 independent evolutionary runs of 300 generations with population size 100 were executed for each representation (192 total runs across 24 CPU cores). The table and figures below summarize the optimization performance metrics across the four encodings:

| Representation | Mean Best Fitness $\pm$ Std | Median Fitness | Max Best Fitness | Mean Run Duration |
| :---: | :---: | :---: | :---: | :---: |
| **$f_0$** | **0.010111** $\pm$ 0.004524 | 0.009306 | 0.023337 | 1243.6 s |
| **$f_1$** | 0.004749 $\pm$ 0.004117 | 0.003352 | 0.016334 | 1202.9 s |
| **$f_4$** | 0.008103 $\pm$ 0.007711 | 0.006353 | **0.043587** | 1168.1 s |
| **$f_H$** | **0.012749** $\pm$ 0.004798 | **0.012263** | 0.028365 | 1369.3 s |

<a id="fig-evolution-mean-curves"></a>

<p align="center">
  <img src="./results/optimization/plots/logbooks_confidence_std_1.0.png" width="85%" alt="Optimization Convergence Curves (Mean +- 1 Std)"/>
  <br>
  <em>Figure 1: Evolutionary convergence curves showing mean best fitness and its confidence interval across 300 generations for all four encodings. Note the linear scale for generations 0–50 and logarithmic scale for generations 50–300.</em>
</p>

<a id="fig-evolution-boxplots"></a>

<p align="center">
  <img src="./results/optimization/plots/boxplot_summary.png" width="95%" alt="Hall of Fame Fitness and Run Duration Distributions"/>
  <br>
  <em>Figure 2: Distribution of final Hall of Fame fitness (left) and computational run duration per experiment in seconds (right) across 48 runs per representation.</em>
</p>

<a id="fig-best-creature-inspection"></a>

<p align="center">
  <img src="./images/best-creature-inspection.png" width="95%" alt="Best Creature Inspection"/>
  <br>

  _Figure 3a: Inspection of functioning of [the best creature](./runs/2026-10-24_185840/gens/HoF-f4-37.gen). The left side depicts the moment of jumping and lifting from the ground by extending creature's leg, two limbs on the right are used as stabilizing torso. The right side depicts creature's redundant neurons and one active neural arc: gyroscope -> bending muscle._
</p>


<p align="center">
  <img src="./images/best-second-creature-inspection.png" width="95%" alt="Best Creature Inspection"/>
  <br>

  _Figure 3b: Inspection of functioning of [the second best creature](./runs/2026-10-24_185840/gens/HoF-f4-28.gen). Mechanics and neural description coincide with the best creature._
</p>

### Fitness Landscape Probing Results

$S = 200$ diversified parent solutions per encoding were selected from the climber history pool by matching an equidistant 200-point target grid spanning $[F_{\min}, F_{\max}^{(enc)}]$ to the closest unique solution without replacement, where $F_{\max}^{(enc)}$ is the maximum fitness achieved by the given encoding across all runs.

Each selected parent was then probed by generating $N = 20$ valid 1-step mutants (rejecting infeasible configurations and generating a new mutant until a valid one is generated), producing in total $4\,000$ mutational evaluations per each format.


<a id="fig-parent-mutant-fitness-scatter-plots"></a>

<p align="center">
  <img src="./results/landscape/landscape_scatter_comparison_2x2.png" width="95%" alt="Comparative Fitness Landscape Neighborhoods (2x2 Grid)"/>
  <br>

  _Figure 4: Comparative parent-vs-mutant fitness landscape scatter plots for all four representations plotted on a globally unified fixed scale_ $[0, 0.0458]$ _with the_ $y = x$ _neutrality diagonal. Gray points indicate mutants that were obtained from parents with final fitness outliers (see [Figure 2: HoF fitness](#fig-evolution-boxplots)). For instance, [two outliers](#fig-best-creature-inspection) in_ $f4$ _representation achieve fitness above_ $0.034$ _, shading thus indicates evolutionary climbing paths resulting from the combinatorial lottery._
</p>

#### Isolating the Influence of Outliers

To assess the influence of outliers on the conclusions, producing an additional set of figures is unnecessary: the same insights can be drawn directly from the existing plots. If outlier runs are excluded from the pool from which parents are sampled, the maximum fitness for each representation contracts to the rightmost edge of the colored plume on each subplot in [Figure 4](#fig-parent-mutant-fitness-scatter-plots). Sampling 200 parents within this reduced interval would simply populate the same region more densely, mirroring the colored clusters already displayed. Similarly, the uniform parent step distribution would scale proportionally to this lower maximum while maintaining its flat profile ([Figure 0](#fig-distribution-parents-climbers)). Thus, the existing dataset and color-coded separation sufficiently isolate the effect of outliers.

_Note: motivation for isolating the effect of outliers is to prevent possible effects of "lottery winners" on the overall climbing (e.g. due to chance their trajectory could generate more beneficial mutations than average, and if we include them in the parent pool for landscape probing, we could overestimate the overall potential of a given representation)._


<div style="break-after: page;"></div>

#### Quantitative Landscape Metrics

Mutant performance relative to the parent solution is partitioned into three mutually exclusive categories based on the fitness delta $\Delta F = F(m) - F(P)$ with a numerical tolerance threshold $\epsilon = 10^{-6}$ depending on whether $\Delta F \ge \epsilon$ (better mutants), $|\Delta F| < \epsilon $ (neutral mutants) or $\Delta F \le -\epsilon$ (worse mutants).

The tolerance $\epsilon = 10^{-6}$ is chosen to prevent infinitesimal floating-point jitter or minor contact timing variations in continuous physics from being falsely classified as selective improvements or degradations, ensuring that only genuine phenotypic changes are registered.

The table below reports the complete quantitative neighborhood characteristics with and without outlying evolutionary paths.

<a id="table-neighborhood-characteristics"></a>

| Representation   |  Better ($y > x$)   | Neutral ($y \approx x$)   | Worse ($y < x$)   |   Pearson $r$ | Lethality Rate   | Max Parent Fitness   | Max Mutant Fitness   |
|:-----------------|:-----------------|----------:|:----------|:-------------------|:--------------------------|:------------------|--------------:|
| **f0**           | <span style="color: darkblue; font-weight: bold;">127 (3.17%)</span>        | 1,421 (35.52%)            | 2,457 (61.42%)    |        0.5230 | 0.50%            | 0.023337           | 0.023660           |
| No outliers          | <span style="color: darkblue; font-weight: bold;">120 (3.53%)</span>        | 1,186 (34.88%)            | 2,099 (61.74%)    |        0.4937 | 0.56%            | 0.018528           | 0.018528           |
| **f1**           | 111 (2.77%)        | 1,501 (37.52%)            | 2,390 (59.75%)    |        <span style="color: darkblue; font-weight: bold;">0.7035</span> | <span style="color: darkblue; font-weight: bold;">0.27%</span>            | <span style="color: darkred; font-weight: bold;">0.016334</span>           | <span style="color: darkred; font-weight: bold;">0.016266</span>           |
| No outliers           | 55 (2.81%)         | 708 (36.12%)              | 1,199 (61.17%)    |        <span style="color: darkblue; font-weight: bold;">0.6888</span> | <span style="color: darkblue; font-weight: bold;">0.15%</span>            | <span style="color: darkred; font-weight: bold;">0.010705</span>           | <span style="color: darkred; font-weight: bold;">0.010705</span>           |
| **f4**           | 104 (2.60%)        | 1,432 (35.80%)            | 2,470 (61.75%)    |        0.5514 | <span style="color: darkred; font-weight: bold;">2.30%</span>            | <span style="color: darkblue; font-weight: bold;">0.043587</span>           | <span style="color: darkblue; font-weight: bold;">0.043587</span>           |
| No outliers           | 64 (2.34%)         | 1,019 (37.19%)            | 1,658 (60.51%)    |        0.4678 | <span style="color: darkred; font-weight: bold;">2.49%</span>            | 0.015195           | 0.015195           |
| **fH**           | <span style="color: darkred; font-weight: bold;">56 (1.40%)</span>         | 2,331 (58.27%)            | <span style="color: darkblue; font-weight: bold;">1,614 (40.35%)</span>    |        0.5700 | 1.06%            | 0.028365           | 0.028365           |
| No outliers           | <span style="color: darkred; font-weight: bold;">54 (1.45%)</span>         | 2,242 (60.27%)            | <span style="color: darkblue; font-weight: bold;">1,425 (38.31%)</span>    |        0.5856 | 1.12%            | <span style="color: darkblue; font-weight: bold;">0.024326</span>           | <span style="color: darkblue; font-weight: bold;">0.024326</span>           |

### Comparison of Representations

- **Indirect handle-based representation** $f_H$ is the most consistent strategy with [peak average](#fig-evolution-mean-curves) and [median](#fig-evolution-boxplots) performance:
  - Mean fitness is $0.012749$ and median is $0.012263$. Its climb is steady and sustained throughout the entire 300 generations, with low variance across seeds: _60%_ of all mutations (`fH_mut_handle` + `fH_mut_property` in [`eval-allcriteria.sim`](..//..//..//Framsticks55/data/eval-allcriteria.sim)) are continuous (Gaussian centered at previous value) coordinate/parameter adjustments, designed to provide minimal numerical change, frequently leaving cluster connectivity unchanged and shielding phenotypes from catastrophic breakdown (**lowest worse rate, 40.35%**).

  - **Extreme phenotypic buffering (58.27% neutrality)** appears as an intensely saturated line along $y = x$ on [Figure 4](#fig-parent-mutant-fitness-scatter-plots), caused by elements linking via spatial proximity between abstract coordinate handles: because elements connect only when handles are within a distance threshold, coordinate shifts often don't alter the topology threshold graph, explaining _58.27%_ neutrality rate and low-variance ascent.

  - While the immediate 1-step improvement rate is the lowest ($1.40\%$), populations **drift neutrally** across high-dimensional plateaus without falling off peaks, eventually discovering portals to higher fitness levels. This sustained neutral exploration yields the highest consistency (mean $0.012749$) and reliable rank preservation ($r = 0.5700$, $0.5856$ without outliers).

- **Direct Low-Level Encoding** ($f_0$) is most mutationally beneficial, evolvable strategy:
  - **$f_0$ provides smooth and predictable ascent**. Direct representation demonstrates intermediate performance (mean $0.010111$, peak $0.023337$) with balanced variance, due to continuous/parametric adjustements (_64%_ of mutations).
  - **Highest Improvement Rate (3.17%, 3.53% without outliers)**. Direct encoding of parts, coordinates, and synaptic weights provides unconstrained parametric control, creating smooth, continuous slopes where an offspring ($0.023660$) exceeded the 300-generation parent climber maximum ($0.023337$).
  - **Decreased Locality with Exploratory Variance**. Pearson correlation ($r = 0.5230$) and median relative fitness change ($21.6\%$) reflect moderate mutational variance, visible as a tall vertical spray column at the right edge of the plume on [Figure 4](#fig-parent-mutant-fitness-scatter-plots). This step variance provides sufficient exploratory breadth to cross local irregularities.
  - Harmful mutations degrade performance progressively rather than collapsing to zero, indicating accessible upward gradients.


- **Developmental Grammar** ($f_4$) - volatile strategy with macro-mutations:
  - **$f_4$ achieves global peak with high variance**. While $f_4$ has a lower median ($0.006353$), its developmental grammar rules unlocked extraordinary locomotion velocity ($F_{\max} = 0.043587$ and the second best result $0.034267$). The high standard deviation ($\pm 0.007711$) reflects the combinatorial lottery of grammar evolution: many runs settle in mediocre local attractors, but successful runs discover coordinated modular gaits. Two lottery "winners" are depicted on [Figures 3a, b](#fig-best-creature-inspection).

  - **Bimodal Scatter Distribution**: Points in the upper fitness tier ($F(P) > 0.012$, [Figure 4](#fig-parent-mutant-fitness-scatter-plots)) either maintain velocity along $y = x$ or collapse steeply toward $y = 0$.

  - **Repetition operator** `#NUM(...)`, provided by the grammar, allows for modular repetition of genotype fragments, which helps with evolving complicated structures, this proved too volatile for continuous physics. Both champion genotypes evolved compact morphologies with no effectively repeated limbs, moved by simple one-legged pushed jumps while avoiding complex multi-segment modularity.


- **Recurrent Tree Encoding** ($f_1$) - conservative strategy with restricted structural exploration:

  - **$f_1$ struggles with premature stagnation**. Tree-developmental representation exhibited the lowest average fitness ($0.004749$) and lowest maximum ($0.016334$), flattening early in the run. In $f_1$, synaptic weight changes dominate (_67.1%_), while morphological structural disruptions are suppressed (_12.8%_).

  - **Has highest mutational locality across all encodings**: strongest parent-mutant correlation ($r = 0.7035$, $0.6888$ without outliers) and lowest lethality ($0.27\%$), with conservative perturbations (mean absolute $|\Delta F| = 0.0025$, median relative change $7.3\%$).
  - **Topological & Structural Bottlenecks** (see [Evolution Challenges and Fitness Bias](..//..//Assignment%205%20-%20Modifying%20topology%20exploration%20path.%20Evolution%20of%20Designs/README.md#evolution-challenges) in the previous work):
    - Neural connections in $f_1$ use _relative index offsets_: deleting intermediate unused nodes breaks down neural loops, entrenching the morphological search.
    - Independent neuron addition (`f1_nmNeu`) and synaptogenesis (`f1_nmConn`) cause new sensors to sprout unconnected, consuming mutation evaluations without delivering motor torque, _penalizing decoupled neural operators_.
    - High locality preserves conservative crawl movements, but escaping suboptimal basins requires coordinated restructuring across multiple subtrees, resulting in _deceptive basin trapping_.
    - Branching developmental approach is _highly disadvantageous_ due to the _rectilinear objective bias_.


<div style="break-after: page;"></div>

### Experimental Landscape Characterisation

1. **Decoupling of Mutational Locality from Evolvability**:
   - High mutational locality is conservative, not generative. In deceptive landscapes, superior locality ($f_1$, Pearson $r \approx 0.70$) confines populations to suboptimal basins of attraction. Conversely, moderate locality with parametric freedom ($f_0$, $r \approx 0.52$) or macro-mutational leaps ($f_4$, $r \approx 0.47$) is necessary to navigate past local attractors toward higher velocity ceilings.

2. **Neural Redundancy**:
   - Across all representations, over $35\%$ of all mutations are functionally neutral (see [table](#table-neighborhood-characteristics) above).
   - This baseline neutrality is driven by **universal neural redundancy**: because the current simulation settings impose zero metabolic penalty for unused neurons, champion genotypes across all encodings accumulate silent sensors, dead-end oscillators, and unconnected nodes ("junk DNA"). Forward locomotion relies on minimalist 1-to-2 reflex loops (e.g., _Gyroscope -> Bending Muscle_), meaning any mutation targeting the silent neural majority produces strictly zero fitness delta ($\Delta F = 0$). In $f_H$, this baseline is further amplified to $58.3\%$ by geometric handle clustering.
   - When beneficial mutations are scarce ($1.4\% - 3.5\%$), these extensive neutral networks allow populations to traverse genetic sequence space at constant fitness, escaping local optima and achieving higher optimization consistency across runs.

3. **Embodied Coordination & Rectilinear Objective Bias**:
   - Evolved locomotion does not rely on complex, cross-wired Central Pattern Generators; instead, multi-actuator synchronization emerges from **embodied physical coupling** (structural inertia, joint limits, gravity, and ground reaction forces dynamically driving the reflex loops).
   - Under a unidimensional rectilinear objective ($v = \Delta x / \Delta t$), lateral balance and multi-limb stabilization receive zero reward while introducing parasitic ground friction and limb collisions. Consequently, representations that readily decouple morphology to discover asymmetric, unilateral pushing gaits ($f_0, f_4$) outcompete symmetric branching encodings ($f_1$) which in its turn has to adapt to the same strategy (see [previous work](..//..//Assignment%205%20-%20Modifying%20topology%20exploration%20path.%20Evolution%20of%20Designs/README.md) for details).

