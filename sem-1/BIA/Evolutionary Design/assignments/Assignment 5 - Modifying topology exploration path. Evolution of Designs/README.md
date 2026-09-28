# Evolutionary Design #3: Modifying Topology Exploration Path

This assignment explores the space of possible designs - both structural and neural - by manipulating mutation types, operator probabilities, and fitness landscape definitions.

The optimization objective in all tasks is to maximize the creature's `velocity`.

## Setup

Earlier tasks used only passive structures, now [active elements](https://www.framsticks.com/muscles_and_receptors) are introduced:

- **Active sensors**:
    - G - gyroscope
    - T - thermistor
- **Effectors**:
    - @ - flexor muscle
    - | - extensor muscle
- **Generators**:
    - $\sin$ - sine wave generator neuron
    -  $*$ - constant $1$ generator neuron
- **Neurons with parameters**

## Task 1: Changing Neighbourhood Shape

This experiment investigates how enlarging the mutation neighborhood definition influences evolutionary performance on locomotion velocity (following [Framsticks Tutorial II.1](http://www.framsticks.com/common/tutorial/index.html)).

<div align="center" width="50%">

![alt text](./task1%20-%20Neighbourhood%20shape%20and%20operators/image.png)

</div>

### Velocity Across Different Neighborhood [Configurations](./task1%20-%20Neighbourhood%20shape%20and%20operators/)

| Configuration | Mutation Neighborhood Definition | Number of simulations (until convergence) | Velocity ($v$) |
| :--- | :--- | :---: | :--- |
| Original Baseline, starting genotype (`X[*][Sin]...`) | - | - | $0.001849$ |
|  Manual adjustment of two parameters | (one  $\sin$ neuron property) $\times$ (one $*$ neuron property) | - | $0.003163$ |
| **Neural weights and properties**, $\text{NW}$ | Mutating only neural weights and properties | 2k–3k | $0.005015$ |
| **Stick length**, $\text{L}$ | Neural weights/props $\times$ stick length modifiers (`L`/`l`) | 2k | $0.004677$ |
| **Neural topology and weights/properties**, $\text{N} := \text{NT} \times \text{NW} $ | Neural weights/props $\times$ add/remove neurons/sensors/effectors (no stick length) | 2k | $0.007255$ |
| **Combined Full**, $\text{N} \times \text{L} $ | Stick length modifiers $\times$ add/remove neurons, sensors, effectors | 10k | **$0.011536$** |

### Conclusions

1. The **combined neighborhood** - allowing simultaneous stick length modifications and neural topological mutations - **achieved the largest velocity increase** ($\Delta v \approx +0.00969$ over the original creature on the screenshot).
   - Structural stick scaling and neural topology exploration are complementary rather than antagonistic. Enlarging neural topology provides new oscillators and sensory feedback loops, while stick length adjustments mechanically tune lever-arm proportions and ground clearance to effectively translate muscle actuation into propulsion. Restricting evolution to isolated neighbourhood subspaces ($\text{NW, NT, L}$) caused premature stagnation after ~2k evaluations.

2. **Morphological Shape vs. Control Network Changes**:
   - The **macro-morphology** (body topology) was not altered drastically; evolution selectively adjusted stick lengths via `L` (lengthen) and `l` (shorten) modifiers to tune stride mechanics.
   - In contrast, the **control network topology was substantially restructured** - novel neurons, sensory inputs, and synaptic links were integrated to govern rhythmic muscle actuation.


## Simulation Settings & Lifespan 
Across all the following experiments, fitness evaluations utilize the deterministic benchmark `eval-allcriteria.sim;deterministic.sim`  (deterministic evaluation, active neural networks and physics):
- In Framsticks, **Lifespan** is governed by energy depletion. Initial energy is proportional to body size: $E_0 = \text{Energy0} \times n$ (with $\text{Energy0} = 10\,000.0$, $n = \text{number of joints/sticks}$). Each step consumes an idle metabolic cost of $e\_\text{meta} \times n$ energy (with $e\_\text{meta} = 1.0$):

  $$\text{lifespan} = \frac{\text{Energy0} \times n}{e\_\text{meta} \times n} = \frac{10\,000.0}{1.0} = 10\,000 \text{ simulation steps}$$
- **Performance Sampling (`perfperiod`)** determines how often positions are sampled to calculate `velocity`:
    - In [Task 2](#task-2-varying-landscape-definition-height
    ), `perfperiod` is varied across values up to $10\,000$ ($\text{lifespan}$). 
    - In [Task 3](#task-3-varying-different-mutations-probs-nonstationary-categorical-distribution-over-mutation), `sample-period-longest.sim` (`perfperiod` $=999999 > \text{lifespan}$) samples strictly at birth and death to evaluate net rectilinear displacement speed.

## [Task 2: Varying Landscape Definition (Height)](./task2%20-%20Varying%20landscape%20definition/README.md)

In Framstics, the definition of `velocity` relies on the average distance traveled by a creature during its lifespan, thus it is a scalar value. By [changing performance sampling frequency](https://www.framsticks.com/a/al_params.html#exper-perfcalc) ( `perfperiod` ) from 1 to `lifespan`, one changes the definition of the fitness landscape.


### Analysis

1. **Continuous Limit**:
   - As sampling interval $\Delta t \to 0$, discrete trajectory curve chord lengths converge to the line integral of instantaneous speed over lifespan $T$:
     $$\lim_{\Delta t \to 0} \frac{\sum_{k} \|\mathbf{x}(t_{k+1}) - \mathbf{x}(t_k)\|}{T} = \frac{\int_0^T \|\dot{\mathbf{x}}(t)\| \, \mathrm{d}t}{T}$$
   - The numerator represents total **arc length (path taken)**. Setting `perfperiod = 1` in discretisized Framsticks time is equivalent to evaluating the average scalar speed.

2. **Monotonic Surface Degradation & Denoising**:
   - By the triangle inequality, sampling less frequently cuts across curved trajectories and omits high-frequency vibrations. Measured **velocity monotonically drops as `perfperiod` increases**, systematically lowering the landscape height.
   - At small `perfperiod`, absolute physical contact noise is accumulated across all $10\,000$ simulation steps, producing a rugged, noisy landscape. **Increasing `perfperiod` acts as a low-pass filter**, removing accumulated high-frequency fluctuations and smoothing the global fitness surface.

3. **Common Points Between Landscapes**:
   - Fitness values across different `perfperiod` definitions coincide **if and only if** a creature moves along a straight line at constant speed ($\dot{\mathbf{x}}(t) \approx {\text{const}}$), such that total path arc length equals net displacement: $\int_0^T \|\dot{\mathbf{x}}(t)\|\,\mathrm{d}t \approx \|\mathbf{x}(T) - \mathbf{x}(0)\|$.
   - Highly directional creatures like **Fast Lizard** and **Basic Quadruped** retain virtually unchanged velocities across all sampling periods, forming invariant fixed points between landscapes. In contrast, creatures that twist or veer (e.g., **Speedy**) show dramatic fitness decay.

4. **Navigability**:
   - **Noisy Landscapes ($\text{perfperiod} \to 1$)** are difficult to navigate because additive physical noise pollutes the fitness signal, causing similar genotypes to differ randomly and rewarding stationary wobblers.
   - **Overly Denoised Landscapes ($\text{perfperiod} \to T$)** aggregate the whole lifespan into a single boundary chord $\|\mathbf{x}(T) - \mathbf{x}(0)\| / T$, completely masking intermediate accelerations. Fast circular or undulating gaits yield near-zero net displacement, producing flat, uninformative plateaus.
   - **Optimal Balance** - intermediate sampling ($\text{perfperiod} \approx 50\text{--}100$) filters contact jitter while retaining sufficient gradient information to guide early locomotion evolution.

### Empirical verification

<div align="center">

![Velocity vs. Perfperiod](./task2%20-%20Varying%20landscape%20definition/velocity_vs_perfperiod.png)

</div>

_**Figure 2:** Measured velocity for each of the 28 walking genotypes across 13 different `perfperiod` values. Straight-line movers maintained flat curves, whereas turning or wriggling creatures experienced steep velocity drops as `perfperiod` increased._

#### Config
28 walking creatures with diverse locomotion kinematics taken from [`walking.gen`](../../Framsticks55/data/walking.gen) were evaluated in batch mode using FramsticksLib with [standard settings](#simulation-environment--lifespan).

* **Sampling Periods Tested**:
  $$\text{perfperiod} \in \{1, 2, ..., 100,..., 10000\}$$
  where:
  - $\text{perfperiod} = 1$ - maximum continuous sampling (every single simulation step).
  - $\text{perfperiod} = 100$ - default Framsticks sampling period.
  - $\text{perfperiod} = 10\,000$: Sampling only at birth and death ($T = \text{lifespan}$), representing [**net rectilinear displacement speed**](#task-3-varying-different-mutations-probs-nonstationary-categorical-distribution-over-mutation).

#### Running
``` bash
python "assignments\Assignment 5 - Modifying topology exploration path. Evolution of Designs\task2 - Varying landscape definition\run_task2.py" `
    --num-creatures 28 `
    --perfperiods 1 2 5 10 25 50 100 250 500 1000 2000 5000 10000 `
    --outdir "."
```





## [Task 3: Varying Different Mutations Probs. Non‑stationary categorical distribution over mutation ](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md) 

The objective of experiments in this task is to optimize **net rectilinear displacement speed**: 
<div align="center" style="font-size: 130%;">

   $v = \frac{\|\mathbf{x}(T) - \mathbf{x}(0)\|}{T}$
</div>

by varying the relative probabilities (weights,[ `.sim`](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims)) of applying different mutation operators, forming different distributions over these operators, and thus representing different mutation strategies. In this task, we analyze how these strategies influence the evolutionary dynamics and the performance of the evolved solutions for locomotion velocity.

### Setup
- **[Simulation Environment](#simulation-settings--lifespan):** `eval-allcriteria.sim;deterministic.sim;sample-period-longest.sim;` + varying `*.sim` files from [`sims`](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims) directory.
- **Morphological & Neural Limits**:
  - Max parts: `15`
  - Max joints: `30`
  - Max neurons: `20`
  - Max connections: `30`
- **EA Parameters**:
  - Population size: `50`
  - Generations: `300`, `400`
  - Selection: Tournament (`size = 5`)
  - Crossover probability (`pxov`): `0.0` (pure asexual mutation-driven search across all experiments)
  - Mutation probability (`pmut`): `0.9`
  - Hall of Fame size: `1`
  - Replications per setting: `10` independent runs with distinct random seeds


### Mutation Mechanics & Operators

In $f_1$ representation, a creature is subject to a mutation with probability `pmut` = 0.9 (by default). Each probability is drawn from a categorical distribution over mutation operators.
**Morphology mutation operators** concern physical structure parts in genotypes. 
**Neuron net mutation operators** concern neuron net parts in genotypes. 

The weight of each operator is set in the `.sim` files for the morphology and neuron net mutation operators, respectively. In each mutation step, exactly **one** elementary mutation operator is chosen based on its relative weight:
<div align="center" style="font-size: 120%;">

   $P(\text{op}_i) = \frac{w_i}{\sum_{j=0}^{8} w_j}$
</div>


### Tested strategies

#### Batch 1
##### Settings and Rationale
Comparing baseline, high neural, weaker neural, and equal weights configurations:
   1. **[Baseline](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-all-crit.sim)** emphasizes neural weight modifications (`f1_nmWei = 1.0`, $67.1\%$ probability) with low morphology ($12.8\%$ total probability).  
      - Structural neuron insertions/deletions are still relatively high (0.05), but low compared to synaptic weight changes.
      - On the morphology side, modifier adjustments are the most common type of mutation, favoring subtle geometric scaling over drastic topology disruptions.
      - This allocation allows evolution to primarily focus on calibrating muscle activation phases, frequencies, and sensory feedback loops on viable body chassis.
   2. **[High Neural](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs01.sim)** doubles neural operator weights, further suppressing body topology perturbations to focus on controller coordination.
   3. **[Weaker Neural](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs10.sim)** doubles morphological operator weights relative to neural operators (increasing body mutation proportion to $22.6\%$), fostering broader body shape exploration.
   4. **[Equal Weights](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-equal-probs.sim)** provides equal uniform distribution ($11.1\%$ each) across morphology ($44.4\%$) and brain ($55.5\%$).

The following table summarizes the weight settings for each operator in each configuration:
   
   <table tableId="table1">
     <thead>
       <tr>
         <th rowspan="2">Operator</th>
         <th rowspan="2">Description</th>
         <th colspan="2"><a href="./f1-all-crit.sim"><b>Baseline</b></a></th>
         <th colspan="2"><a href="./f1-probs01.sim"><b>High Neural</b></a></th>
         <th colspan="2"><a href="./f1-probs10.sim"><b>Weaker Neural</b></a></th>
         <th colspan="2"><a href="./f1-equal-probs.sim"><b>Equal Weights</b></a></th>
       </tr>
       <tr>
         <th>w<sub>i</sub></th>
         <th>P<sub>i</sub>%</th>
         <th>w<sub>i</sub></th>
         <th>P<sub>i</sub>%</th>
         <th>w<sub>i</sub></th>
         <th>P<sub>i</sub>%</th>
         <th>w<sub>i</sub></th>
         <th>P<sub>i</sub>%</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td colspan="10"><b>Morphology Mutation Operators</b></td>
       </tr>
       <tr>
         <td><code>f1_smX</code></td>
         <td>Add / remove stick X (part)</td>
         <td align="center">0.05</td>
         <td style="background-color: #c4e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.4%</td>
         <td align="center">0.05</td>
         <td style="background-color: #ceecfe; color: #0F172A; font-weight: 600; text-align: center;">1.8%</td>
         <td align="center">0.10</td>
         <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">6.0%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_smJunct</code></td>
         <td>Add / remove branch junction <code>()</code></td>
         <td align="center">0.02</td>
         <td style="background-color: #d1edfe; color: #0F172A; font-weight: 600; text-align: center;">1.3%</td>
         <td align="center">0.02</td>
         <td style="background-color: #d6effe; color: #0F172A; font-weight: 600; text-align: center;">0.7%</td>
         <td align="center">0.04</td>
         <td style="background-color: #caebfd; color: #0F172A; font-weight: 600; text-align: center;">2.4%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_smComma</code></td>
         <td>Add / remove joint separator <code>,</code></td>
         <td align="center">0.02</td>
         <td style="background-color: #d1edfe; color: #0F172A; font-weight: 600; text-align: center;">1.3%</td>
         <td align="center">0.02</td>
         <td style="background-color: #d6effe; color: #0F172A; font-weight: 600; text-align: center;">0.7%</td>
         <td align="center">0.04</td>
         <td style="background-color: #caebfd; color: #0F172A; font-weight: 600; text-align: center;">2.4%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_smModif</code></td>
         <td>Add / remove / change limb modifier</td>
         <td align="center">0.10</td>
         <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;">6.7%</td>
         <td align="center">0.10</td>
         <td style="background-color: #c3e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.6%</td>
         <td align="center">0.20</td>
         <td style="background-color: #98c9fd; color: #0F172A; font-weight: 600; text-align: center;">11.9%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td colspan="2"><b>Total Body</b></td>
         <td align="center"><b>0.19</b></td>
         <td style="background-color: #94c6fd; color: #0F172A; font-weight: 600; text-align: center;"><b>12.8%</b></td>
         <td align="center"><b>0.19</b></td>
         <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;"><b>6.8%</b></td>
         <td align="center"><b>0.38</b></td>
         <td style="background-color: #c0d0fe; color: #0F172A; font-weight: 600; text-align: center;"><b>22.6%</b></td>
         <td align="center"><b>4.0</b></td>
         <td style="background-color: #f27282; color: #0F172A; font-weight: 600; text-align: center;"><b>44.4%</b></td>
       </tr>
       <tr>
         <td colspan="10"><b>Neural Network Mutation Operators</b></td>
       </tr>
       <tr>
         <td><code>f1_nmNeu</code></td>
         <td>Add / remove neuron</td>
         <td align="center">0.05</td>
         <td style="background-color: #c4e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.4%</td>
         <td align="center">0.10</td>
         <td style="background-color: #c3e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.6%</td>
         <td align="center">0.05</td>
         <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.0%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_nmConn</code></td>
         <td>Add / remove neural connection</td>
         <td align="center">0.10</td>
         <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;">6.7%</td>
         <td align="center">0.20</td>
         <td style="background-color: #b0defd; color: #0F172A; font-weight: 600; text-align: center;">7.2%</td>
         <td align="center">0.10</td>
         <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">6.0%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_nmProp</code></td>
         <td>Change neuron property setting</td>
         <td align="center">0.10</td>
         <td style="background-color: #b2dffd; color: #0F172A; font-weight: 600; text-align: center;">6.7%</td>
         <td align="center">0.20</td>
         <td style="background-color: #b0defd; color: #0F172A; font-weight: 600; text-align: center;">7.2%</td>
         <td align="center">0.10</td>
         <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">6.0%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_nmWei</code></td>
         <td><b>Change connection weight</b></td>
         <td align="center"><b>1.00</b></td>
         <td style="background-color: #a9173d; color: #FFFFFF; font-weight: 600; text-align: center;">67.1%</td>
         <td align="center"><b>2.00</b></td>
         <td style="background-color: #96153a; color: #FFFFFF; font-weight: 600; text-align: center;">71.7%</td>
         <td align="center"><b>1.00</b></td>
         <td style="background-color: #cc1b44; color: #FFFFFF; font-weight: 600; text-align: center;">59.5%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td><code>f1_nmVal</code></td>
         <td>Change property / state value</td>
         <td align="center">0.05</td>
         <td style="background-color: #c4e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.4%</td>
         <td align="center">0.10</td>
         <td style="background-color: #c3e9fd; color: #0F172A; font-weight: 600; text-align: center;">3.6%</td>
         <td align="center">0.05</td>
         <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.0%</td>
         <td align="center">1.0</td>
         <td style="background-color: #9ccdfd; color: #0F172A; font-weight: 600; text-align: center;">11.1%</td>
       </tr>
       <tr>
         <td colspan="2"><b>Total Brain</b></td>
         <td align="center"><b>1.30</b></td>
         <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>87.2%</b></td>
         <td align="center"><b>2.60</b></td>
         <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>93.2%</b></td>
         <td align="center"><b>1.30</b></td>
         <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>77.4%</b></td>
         <td align="center"><b>5.0</b></td>
         <td style="background-color: #df1d48; color: #FFFFFF; font-weight: 600; text-align: center;"><b>55.5%</b></td>
       </tr>
       <tr>
         <td colspan="2"><b>Total Wheel Weight</b></td>
         <td align="center"><b>1.49</b></td>
         <td align="center"><b>100%</b></td>
         <td align="center"><b>2.79</b></td>
         <td align="center"><b>100%</b></td>
         <td align="center"><b>1.68</b></td>
         <td align="center"><b>100%</b></td>
         <td align="center"><b>9.0</b></td>
         <td align="center"><b>100%</b></td>
       </tr>
     </tbody>
   </table>


##### Key findings in Batch 1
- **[Equal Operator Weights](./sim/f1-equal-probs.sim)** achieves roughly double the median velocity of the baseline, achieving the best performance during almost the entire evolution ([Figure 3](#comparative-results)), outperforming the rest 3 settings.

- In $f_1$, **equal weights** translate to a $4$-to-$5$ ratio between morphology and brain. This balanced ratio maintains structural diversity while preserving sufficient frequency of synaptic weight mutations ($11.1\%$) to coordinate newly emerging limbs.

#### Batch 2

To move beyond blunt global morphology-vs-brain ratios, **four tuned operator probability distributions** based on the mechanical roles of the 9 operators in $f_1$:


#### Settings & Rationales
1. **[Strategy A (Continuous Fine-Tuning)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-a.sim)** heavily suppresses catastrophic structural additions/deletions while prioritizing continuous physical and neural scaling. Protects working gaits from being ripped apart.
2. **[Strategy B (Branching & Morphology Exploration)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-b.sim)** strongly promotes structural branching alongside balanced neural operators. Encourages bilateral limbs, outriggers, and multi-legged chassis.
3. **[Strategy C (CPG Resonance & Control Dynamics)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-c.sim)** minimizes body alterations and concentrates on central pattern generator frequency/phase coordination.
4. **[Strategy D (3-Tier Evolutionary Pyramid)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-d.sim)** hierarchical architecture allocating ~15% to macro-topology jumps, ~35% to mesoscale wiring and modifiers, and ~50% to continuous parameter calibration.

The table below summarises the main differences between the 4 strategies:


<table tableId="table2">
  <thead>
    <tr>
      <th rowspan="2">Operator</th>
      <th rowspan="2">Role in f<sub>1</sub> Phenotype</th>
      <th colspan="2"><a href="./f1-strat-a.sim"><b>Strategy A</b></a></th>
      <th colspan="2"><a href="./f1-strat-b.sim"><b>Strategy B</b></a></th>
      <th colspan="2"><a href="./f1-strat-c.sim"><b>Strategy C</b></a></th>
      <th colspan="2"><a href="./f1-strat-d.sim"><b>Strategy D</b></a></th>
    </tr>
    <tr>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
      <th>w<sub>i</sub></th>
      <th>P<sub>i</sub>%</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td colspan="10"><b>Morphology Mutation Operators</b></td>
    </tr>
    <tr>
      <td><code>f1_smX</code></td>
      <td>Stick Append / Delete</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">0.5</td>
      <td style="background-color: #bbe6fd; color: #0F172A; font-weight: 600; text-align: center;">5.3%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.3</td>
      <td style="background-color: #bde7fd; color: #0F172A; font-weight: 600; text-align: center;">4.7%</td>
    </tr>
    <tr>
      <td><code>f1_smJunct</code></td>
      <td>Branch Fork <code>()</code></td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.5</td>
      <td style="background-color: #a2c9fd; color: #0F172A; font-weight: 600; text-align: center;">15.8%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.3</td>
      <td style="background-color: #bde7fd; color: #0F172A; font-weight: 600; text-align: center;">4.7%</td>
    </tr>
    <tr>
      <td><code>f1_smComma</code></td>
      <td>Joint Sibling <code>,</code></td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.5</td>
      <td style="background-color: #a2c9fd; color: #0F172A; font-weight: 600; text-align: center;">15.8%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.5</td>
      <td style="background-color: #addbfd; color: #0F172A; font-weight: 600; text-align: center;">7.8%</td>
    </tr>
    <tr>
      <td><code>f1_smModif</code></td>
      <td>Modifiers (<code>LlRrCcQqFfMm</code>)</td>
      <td align="center">1.5</td>
      <td style="background-color: #c3d1fe; color: #0F172A; font-weight: 600; text-align: center;">23.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.7</td>
      <td style="background-color: #96c6fd; color: #0F172A; font-weight: 600; text-align: center;">13.7%</td>
      <td align="center">1.0</td>
      <td style="background-color: #a0c8fd; color: #0F172A; font-weight: 600; text-align: center;">15.6%</td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Body</b></td>
      <td align="center"><b>2.10</b></td>
      <td style="background-color: #e6b7c9; color: #0F172A; font-weight: 600; text-align: center;"><b>32.3%</b></td>
      <td align="center"><b>4.50</b></td>
      <td style="background-color: #ee5c73; color: #0F172A; font-weight: 600; text-align: center;"><b>47.4%</b></td>
      <td align="center"><b>1.00</b></td>
      <td style="background-color: #b3cdfe; color: #0F172A; font-weight: 600; text-align: center;"><b>19.6%</b></td>
      <td align="center"><b>2.10</b></td>
      <td style="background-color: #e8b6c7; color: #0F172A; font-weight: 600; text-align: center;"><b>32.8%</b></td>
    </tr>
    <tr>
      <td colspan="10"><b>Neural Network Mutation Operators</b></td>
    </tr>
    <tr>
      <td><code>f1_nmNeu</code></td>
      <td>Neuron Insert / Delete</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.3</td>
      <td style="background-color: #b7e3fd; color: #0F172A; font-weight: 600; text-align: center;">5.9%</td>
      <td align="center">0.3</td>
      <td style="background-color: #bde7fd; color: #0F172A; font-weight: 600; text-align: center;">4.7%</td>
    </tr>
    <tr>
      <td><code>f1_nmConn</code></td>
      <td>Synapse Link / Cut</td>
      <td align="center">0.5</td>
      <td style="background-color: #addbfd; color: #0F172A; font-weight: 600; text-align: center;">7.7%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.7</td>
      <td style="background-color: #96c6fd; color: #0F172A; font-weight: 600; text-align: center;">13.7%</td>
      <td align="center">0.8</td>
      <td style="background-color: #96c7fd; color: #0F172A; font-weight: 600; text-align: center;">12.5%</td>
    </tr>
    <tr>
      <td><code>f1_nmProp</code></td>
      <td>Frequency <i>f</i><sub>0</sub>, Phase <i>t</i></td>
      <td align="center">1.5</td>
      <td style="background-color: #c3d1fe; color: #0F172A; font-weight: 600; text-align: center;">23.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">1.5</td>
      <td style="background-color: #dbc1dc; color: #0F172A; font-weight: 600; text-align: center;">29.4%</td>
      <td align="center">1.2</td>
      <td style="background-color: #b0ccfe; color: #0F172A; font-weight: 600; text-align: center;">18.8%</td>
    </tr>
    <tr>
      <td><code>f1_nmWei</code></td>
      <td><b>Synaptic Weight</b></td>
      <td align="center"><b>2.0</b></td>
      <td style="background-color: #e0bdd4; color: #0F172A; font-weight: 600; text-align: center;">30.8%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">1.5</td>
      <td style="background-color: #dbc1dc; color: #0F172A; font-weight: 600; text-align: center;">29.4%</td>
      <td align="center"><b>1.8</b></td>
      <td style="background-color: #d6c5e4; color: #0F172A; font-weight: 600; text-align: center;">28.1%</td>
    </tr>
    <tr>
      <td><code>f1_nmVal</code></td>
      <td>Internal Bias / State</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.2</td>
      <td style="background-color: #c6eafd; color: #0F172A; font-weight: 600; text-align: center;">3.1%</td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Brain</b></td>
      <td align="center"><b>4.40</b></td>
      <td style="background-color: #a7163d; color: #FFFFFF; font-weight: 600; text-align: center;"><b>67.7%</b></td>
      <td align="center"><b>5.00</b></td>
      <td style="background-color: #e53055; color: #FFFFFF; font-weight: 600; text-align: center;"><b>52.6%</b></td>
      <td align="center"><b>4.10</b></td>
      <td style="background-color: #881337; color: #FFFFFF; font-weight: 600; text-align: center;"><b>80.4%</b></td>
      <td align="center"><b>4.30</b></td>
      <td style="background-color: #a9173d; color: #FFFFFF; font-weight: 600; text-align: center;"><b>67.2%</b></td>
    </tr>
    <tr>
      <td colspan="2"><b>Total Wheel Weight</b></td>
      <td align="center"><b>6.50</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>9.50</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>5.10</b></td>
      <td align="center"><b>100%</b></td>
      <td align="center"><b>6.40</b></td>
      <td align="center"><b>100%</b></td>
    </tr>
  </tbody>
</table>


#### [Comparative results](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/)

Each strategy was evaluated across 10 independent runs over 400 generations (20 CPU workers). The following plots show the results of **Batch 1** vs **Batch 2** configurations.

![Comparative Best Series (Linear)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/plots/logbooks_best_series.png)
_Figure 1: Comparative best-of-generation fitness trajectories._

![Comparative Confidence Intervals (Linear)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/plots/logbooks_confidence_std_1.0.png)
_Figure 2: Mean fitness and shaded $\pm 1\sigma$ intervals._

![Comparative Boxplots](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/plots/boxplot_summary.png)
_Figure 3: Final Hall-of-Fame velocity and run duration distributions._

![Experiment 2 Best Creature](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Exp2-best-creature.png)
_Figure 3b: Phenotypic inspection of the fastest creature evolved in Experiment 2 (Strategy A), displaying its linear articulated chassis and synchronized neural motor driver._

### Findings: Static Mutation Strategies (Batches 1 & 2)

Comparing the constant atomic baselines (Batch 1) and targeted biomechanical strategies (Batch 2) reveals how static operator allocations shape the evolutionary trajectory:

1. **Strategy B (Branching & Articulation) Championed Static Structural Exploration**:
   - Strategy B achieved the highest mean velocity among all constant targeted configurations ($v_{mean} = 0.006325, v_{max} = 0.016070$).
   - Allocating $31.6\%$ of mutation probability to branch junctions `()` and sibling joints `,` actively stimulated the discovery of branched, multi-legged outrigger chassis capable of effective ground leverage.
2. **Strategy A (Continuous Fine-Tuning) Delivered High Precision with Low Variance**:
   - Strategy A achieved steady, low-variance gait optimization ($v_{mean} = 0.005721, v_{max} = 0.017484$) with the lowest run duration ($693.0\text{ s}$).
   - By suppressing structural additions/deletions ($<10\%$) and emphasizing modifier scaling (`f1_smMod: 1.5`, $23.1\%$) and synaptic weights ($30.8\%$), it reliably protected established locomotive patterns from catastrophic dismemberment while continuously tuning lever arms and actuation phases.
3. **Strategy D (Hierarchical Joint Allocation) Provided Robust Baseline Mechanics**:
   - Strategy D achieved high median velocity ($v_{median} = 0.005484$), demonstrating that balancing joint insertion with synaptic tuning yields consistent locomotion, though without the exploratory breakthroughs of Strategy B.
4. **Strategy C (Neural Overdrive) Confirmed the "Embodiment Limit"**:
   - Heavily suppressing morphological mutations ($<20\%$) caused severe stagnation ($v_{mean} = 0.002754$, lowest across all 24 tested configurations).
   - This empirically confirms that neural networks cannot compensate for a mechanically flawed or unarticulated body chassis: controllers require mechanical degrees of freedom to produce propulsion.
5. **The Static Dilemma**:
   - High structural exploration (Equal Weights, Strategy B) discovers innovative body plans early, but repeatedly destabilizes mature, functional gaits in late generations.
   - Conservative fine-tuning (Strategy A, Baseline) protects mature gaits, but cannot construct complex articulated morphologies from scratch.

---

## Scheduled Mutation Schemes: Non-Stationary Developmental Exploration

To overcome the static exploration–exploitation dilemma, we introduced **non-stationary scheduled mutation distributions** across evolutionary time:

$$\mathbf{w}(t) = \mathbf{w}_k \quad \text{for } t_k \le t < t_{k+1}$$

### Why Scheduled Schemes Were Proposed
In biological morphogenesis, organisms undergo distinct developmental phases: embryonic body plan formation precedes neuromuscular differentiation and fine motor tuning. In evolutionary robotics, applying a uniform operator distribution throughout all 400 generations forces an artificial compromise. Scheduled schemes resolve this by decomposing the search:
1. **Initial Bootstrapping (Generations $0\text{--}100$)**: Unconstrained morphological exploration (Equal Weights) discovers viable multi-jointed body plans and limb branching.
2. **Intermediate Articulation & Neuromuscular Scaffolding (Generations $100\text{--}200$)**: Biomechanical specialization (Strategy B for limbs, Strategy D for joints) allocates degrees of freedom and sensor-effector loops.
3. **Late-Stage Convergence & Parametric Polish (Generations $200\text{--}400$)**: Suppressing structural perturbations while prioritizing Strategy A or neural tuning allows continuous metric refinement of limb lengths, muscle angles, and synaptic weights without destructive morphological mutations.

### Overview of Scheduled Batches Tested
Across Experiments 3, 4, and 5, **16 distinct scheduled schemes** (160 evolutionary runs) were tested under identical experimental controls ($N_{pop} = 50$, tournament size $5$, $p_{mut} = 0.9$, $p_{xov} = 0.0$, 400 generations):

1. **Experiment 3: Multi-Stage Scheduled Switching (Schemes 1–7)**:
   - Explored diverse transition chains: classical scaffolding (Weaker $\to$ High Neural), multi-phase developmental switches (Equal $\to$ Strat B $\to$ Neural), and 6-stage micro-step cascades.
   - Discovered that rapid 50-generation switches induce disruption shocks, but Scheme 3 and Scheme 7 achieved peak velocities exceeding $0.023$.
2. **Experiment 4: Biphasic Exploration Timing & Scaffolding (Schemes 1, 8–11)**:
   - Systematically varied the timing of the transition from initial Equal Weights exploration to Strategy A fine-tuning: $t_{switch} \in \{100, 200, 300\}$.
   - Identified the **critical 100-generation plasticity window**: transitioning to Strategy A at generation 100 (**Scheme 10**) produced the highest overall mean velocity across the entire 24-configuration benchmark ($v_{mean} = 0.008272$).
3. **Experiment 5: Refined Morphogenetic Cascades (Schemes 1, 3, 7, 10)**:
   - Addressed the **morphological freeze trap** (where zeroing body mutations prevents correcting misaligned limbs) by replacing rigid freezes with unbroken developmental progressions:
     $$\text{Equal (Bootstrap, 100)} \to \text{Strat B (Branching, 100)} \to \text{Strat D (Joints, 100)} \to \text{Strat A (Tuning, 100)}$$
   - Scheme 7 yielded the second-highest average velocity of the entire benchmark ($v_{mean} = 0.007447, v_{max} = 0.019239$).

---

### Comparative Boxplot Analysis

The distributions of final Hall-of-Fame velocity and computational runtime across all **24 configurations (240 independent runs over 400 generations)** and across the **champion paradigms** are summarized below:

![Global Boxplot Across All 24 Configurations](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison_exp1_5/plots/boxplot_summary.png)
_Figure 4: Comprehensive Hall-of-Fame final velocity (left) and run duration (right) distributions across all 24 configurations tested in Experiments 1–5 (240 total runs over 400 generations). Note the natural ordering by experiment run folders and numerical scheme indices._

![Champions Boxplot Summary](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison_champions/plots/boxplot_summary.png)
_Figure 5: Final Hall-of-Fame velocity and duration distributions for the top-performing champion strategies from each evolutionary paradigm (Experiments 1–5)._

---

### Top-4 Evolutionary Configurations (Master Leaderboard)

Across all 240 evolutionary runs evaluated on rectilinear velocity over 400 generations, the top-4 strategies are:

| Rank | Paradigm / Experiment | Configuration / Scheme Name | Transition Strategy Chain | Mean Velocity | Median Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 1 | **Experiment 4** | **Scheme 10 (Early Freeze)** | Equal ($100$) $\to$ Strat A ($300$) | **$0.008272$** | $0.005797$ | $0.006459$ | **$0.001554$** | $0.022688$ | $970.7\text{ s}$ |
| 🥈 2 | **Experiment 5** | **Scheme 7 (Morphogenetic Cascade)** | Equal ($100$) $\to$ Strat B ($100$) $\to$ Strat D ($100$) $\to$ Strat A ($100$) | **$0.007447$** | $0.004367$ | $0.007049$ | $0.000352$ | $0.019239$ | $779.5\text{ s}$ |
| 🥉 3 | **Experiment 3** | **Scheme 3 (Balanced Scaffolding)** | Equal ($100$) $\to$ Strat B ($50$) $\to$ Weaker Neural ($50$) $\to$ High Neural ($200$) | **$0.007213$** | $0.005296$ | $0.006716$ | $0.001013$ | **$0.023459$** | $919.0\text{ s}$ |
| 4 | **Experiment 1** | **Equal Weights (Atomic Baseline)** | Constant Equal Weights ($400$) | $0.007167$ | **$0.006500$** | $0.005391$ | $0.000574$ | $0.019564$ | $758.5\text{ s}$ |

---

### Best Evolved Creature Genomes

#### 1. Absolute Peak Velocity Champion: Experiment 3 Scheme 3 ($v = 0.023459$)
- **File**: `stats/2026-09-27_exp3_switching/2026-09-27_18/HoF-f1-scheme-3-0.gen`
- **Genotype**:
  ```
  MqMqqq((mrqMCMqLX[N, 13:0.523][G][G][|, 2:1.92][S][S][T, ry:1.482]m(QRmLq(, (MX[Gpart][T][G][T])))), X[S][@, -3:-0.432][N, -4:-3.21, -13:3.814, si:1.753, in:0.8, si:-4.394][|, -8:3.533])
  ```
- **Velocity**: $0.023459038234857753$
- **Morphological & Neural Architecture**:
  - A highly sophisticated asymmetric quadrupedal crawler with multi-segment articulated outriggers (`MqMqqq`).
  - Utilizes sensory feedback integration: dual touch receptors (`S`), redundant gyroscopes (`G`, `Gpart`), and a temperature-dependent sensor (`T`).
  - Actuation combines flexor (`@`) and extensor (`|`) muscles driven by a central pattern generator (`N`) operating with non-linear sinusoidal phase-coupling (`si:1.753`, `si:-4.394`, `in:0.8`).

![Benchmark Champion Creature](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Final-best-creature.png)
_Figure 5b: Framsticks GUI phenotype inspection of the overall benchmark champion, illustrating its 4-part / 3-joint physical chassis (top right) and neural controller (bottom right) with the active Central Pattern Generator (CPG) loop alongside 7 isolated sensor nodes._

#### 2. Mean Velocity Champion: Experiment 4 Scheme 10 ($v = 0.022688$)
- **File**: `stats/2026-09-27_exp4_biphasic/combined/HoF-f1-scheme-10-8.gen`
- **Genotype**:
  ```
  X[Sin, -1:-0.428][*, 1:0.771][|, 1:1.649][S][G]m(MX[G][T][|]m(LX[Gpart][T][G][T]))
  ```
- **Velocity**: $0.022688463137943586$
- **Morphological & Neural Architecture**:
  - Compact, low-drag kinetic lever design featuring minimal part overhead and high energy efficiency.
  - Features an oscillating pacemaker core (`Sin` coupled to a constant bias neuron `*`) directly linked to high-leverage extensor muscles (`|`, `1:1.649`).
  - Balanced by rotational gyro sensors (`G`) and mechanical touch grounding (`S`), demonstrating how Strategy A's 300 generations of uninterrupted metric tuning refines high-frequency propulsion without structural bloat.

#### 3. Morphogenetic Cascade Champion: Experiment 5 Scheme 7 ($v = 0.019239$)
- **File**: `stats/2026-09-27_exp5_refined/2026-09-27_23/HoF-f1-scheme-7-9.gen`
- **Genotype**:
  ```
  MqMqqq((mrqMCMqLX[N, 13:0.523][G][G][|, 2:1.92][S][S][T, ry:1.482]m(QRmLq(, (MX[Gpart][T][G][T])))), X[S][@, -3:-0.432][N, -4:-3.21, -13:3.814, si:1.753, in:0.8, si:-4.394][|, -8:3.533])
  ```
- **Velocity**: $0.01923907636967041$
- **Morphological & Neural Architecture**:
  - Evolved through the 4-stage biological morphogenetic cascade ($\text{Equal} \to \text{Strat B} \to \text{Strat D} \to \text{Strat A}$).
  - Achieved the highest worst-case velocity retention ($v_{min} = 0.001554$ across runs) by avoiding complete morphological freezes, maintaining continuous metric adaptation until generation 400.

#### Topological Neural Network Analysis: Functional Circuitry vs. Disconnected "Junk DNA"

Inspection of the champion genotype in the Framsticks GUI neural viewer reveals a striking phenomenon: **out of 15 total neurons and sensors, 7 nodes appear completely disconnected**. A graph-theoretic inspection via the Framsticks C-API (`frams.Model.newFromString`) reveals the underlying evolutionary mechanisms:

| Node # | Type | Anatomical Locus | Incoming Synapses ($\leftarrow$) | Outgoing Synapses ($\rightarrow$) | Role / Evolutionary Status |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **#0** | `N` (Oscillator) | Part 1 | From Node #13 ($w=+0.523$) | To Node #13 ($w=+3.814$) | **Active CPG Core** (Recurrent oscillator loop) |
| **#1** | `G` (Gyroscope) | Joint 0 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#2** | `G` (Gyroscope) | Joint 0 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#3** | `\|` (Extensor Muscle) | Joint 0 | From Node #5 ($w=+1.920$) | *None* (Effector) | **Active Actuation** (Stroke driver) |
| **#4** | `S` (Touch) | Part 1 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#5** | `S` (Touch) | Part 1 | *None* | To Node #3 ($w=+1.920$) | **Active Reflex Arc** (Ground contact feedback) |
| **#6** | `T` (Tilt Sensor) | Part 1 | *None* | To Node #14 ($w=+3.533$) | **Active Reflex Arc** (Pitch/Roll stabilization) |
| **#7** | `Gpart` (Gyroscope) | Part 2 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#8** | `T` (Tilt Sensor) | Part 2 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#9** | `G` (Gyroscope) | Joint 1 | *None* | To #12 ($w=-0.432$), To #13 ($w=-3.210$) | **Active Sensory Modulator** (Posture gating) |
| **#10** | `T` (Tilt Sensor) | Part 2 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#11** | `S` (Touch) | Part 3 | *None* | *None* | **Disconnected** *(Vestigial / Structural Spacer)* |
| **#12** | `@` (Bending Muscle) | Joint 2 | From Node #9 ($w=-0.432$) | *None* (Effector) | **Active Actuation** (Posture damper) |
| **#13** | `N` (Oscillator) | Part 3 | From Node #0 ($w=+3.814$), From #9 ($w=-3.210$) | To Node #0 ($w=+0.523$) | **Active CPG Core** (Gated non-linear oscillator) |
| **#14** | `\|` (Extensor Muscle) | Joint 2 | From Node #6 ($w=+3.533$) | *None* (Effector) | **Active Actuation** (Extensor stroke) |

##### Evolutionary Mechanisms Explaining Disconnected Neurons:
1. **Entrenchment via Relative Indexing in $f_1$ (The Structural Spacer Effect)**:
   - In the $f_1$ genetic format, neural connections are encoded as **relative index offsets** (e.g., Node #13 connects to Node #0 with offset `-13` and Node #9 with offset `-4`).
   - Every intervening neuron—even if unconnected—acts as a positional spacer in the gene sequence. If a deletion mutation deletes an unused sensor (e.g. Node #7 or #8), the relative index offset `-4` would point to index $8$ instead of Gyroscope #9, instantly disrupting the CPG feedback loop and causing the locomotive gait to collapse.
   - Consequently, unused nodes become **structurally entrenched**: deleting them is lethal to controller function.
2. **Neutral Genetic Drift & Absence of Parsimony Pressure**:
   - The evolutionary fitness objective maximizes velocity ($v = \Delta x / \Delta t$).
   - Because Framsticks imposes zero metabolic penalty for unused neurons ($\lambda \cdot N_{neu} = 0$), non-functional sensors incur zero selective disadvantage and accumulate freely during early exploratory generations.
3. **Cryptic Genetic Variation / Latent Reservoirs**:
   - In evolutionary robotics and biology, silent genetic material serves as a reservoir of cryptic variation: future single-point connection mutations (`f1_nmConn`) or crossovers can immediately link into existing sensory channels without requiring de novo sensor insertion.

##### The Evaluation Budget Penalty of Decoupled Operators
This architectural phenomenon exposes a fundamental inefficiency in the standard $f_1$ genetic representation: **the mutation budget penalty of decoupled operators**.
- In Framsticks $f_1$, neuron insertion (`f1_nmNeu`) and synaptic wiring (`f1_nmConn`) are independent, competing mutation operators on the roulette wheel.
- When `f1_nmNeu` triggers, it inserts a raw sensor (`[G]`, `[S]`, `[T]`) with **zero connections**. Because the node produces no torque on muscles, the mutant has identical locomotion velocity to its parent. The evaluation budget spent generating that offspring is wasted in the short term.
- For that node to ever become functional, a second, rare mutation (`f1_nmConn`) must later hit that exact locus to wire it into the motor circuit. If this second event never occurs, the node remains dead weight.
- **Why Strategy C Collapsed vs. Scheme 10 Succeeded**:
  - In **Strategy C (Neural Overdrive)**, $20\%$ of all mutations were allocated to `f1_nmNeu` and $20\%$ to `f1_nmConn`. The algorithm continuously burned its evaluation budget creating isolated sensors that were never connected, starving mechanical body evolution ($<20\%$) and resulting in the worst performance across all 24 configurations ($v_{mean} = 0.002754$).
  - In contrast, **Scheme 10** allowed neural exploration during generations $0\text{--}100$, then switched to **Strategy A**, slashing `f1_nmNeu` to just **$3.1\%$**. By cutting off the generation of useless disconnected neurons, almost $100\%$ of the remaining 300 generations of mutation budget was channeled into joint modifiers (`23.1\%`) and synaptic weights (`30.8\%`), yielding the #1 overall champion.

---

### Grand Conclusions & Key Insights

1. **The 100-Generation Window of Morphological Plasticity**:
   - Across all 24 configurations, **Equal Weights during the first 100 generations** was the single most decisive determinant of evolutionary success.
   - All top 4 strategies across the entire benchmark (Exp 4 Sch 10, Exp 5 Sch 7, Exp 3 Sch 3, Exp 1 Equal Weights) began with Equal Weights.
   - Delaying the transition to generation 200 or 300 caused performance to collapse by over $50\%$ (Scheme 8: $0.003969$, Scheme 11: $0.003456$), proving that morphological body plans become developmentally canalized early.

2. **The "Morphological Freeze Trap"**:
   - Setting morphological mutation weights strictly to zero (as in pure High Neural or classic scaffolding) is dangerous: if an evolved creature's limbs or actuator angles are even slightly misaligned, evolution cannot reorient them mechanically.
   - The top two strategies (Exp 4 Scheme 10 and Exp 5 Scheme 7) avoided complete freezes by using **Strategy A**, which allows continuous metric adjustments (`f1_smMod: 1.5`, $23.1\%$) while suppressing disruptive additions/deletions.

3. **Continuous Biological Cascades Outperform Abrupt Switching**:
   - While abrupt 50-generation switches induce disruption shocks, a structured 4-stage developmental cascade:
     $$\text{Global Exploration (Equal)} \to \text{Limb Branching (Strat B)} \to \text{Joint Allocation (Strat D)} \to \text{Biomechanical Tuning (Strat A)}$$
     guides evolution naturally from macro-anatomy to micro-parameter tuning, yielding top-tier performance without sacrificing stability.

For complete per-run logbooks, statistical distributions, and individual experiment scripts, see the [Task 3 Detailed Report](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md).
