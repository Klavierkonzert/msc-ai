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
   - Fitness values across different `perfperiod` definitions coincide **if and only if** a creature moves along a straight line at constant speed ($\dot{\mathbf{x}}(t) \approx {\text{const}}$), such that total path arc length equals net displacement: 

   $$\int_0^T \|\dot{\mathbf{x}}(t)\|\,\mathrm{d}t \approx \|\mathbf{x}(T) - \mathbf{x}(0)\|$$

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

$$P(\text{op}_i) = \frac{w_i}{\sum_{j=0}^{8} w_j}$$


### Tested Stationary Mutation Strategies (Experiments 1 and 2)

#### Batch 1 (Tested in Experiment 1 and 2)
##### Settings and Rationale
Comparing baseline, high neural, weaker neural, and equal weights configurations:
   1. **[Baseline](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-all-crit.sim)** emphasizes neural weight modifications (`f1_nmWei = 1.0`, $67.1\%$ probability) with low morphology ($12.8\%$ total probability).  
      - Structural neuron insertions/deletions are still relatively high ($0.05$), but low compared to synaptic weight changes.
      - On the morphology side, modifier adjustments are the most common type of mutation, favoring subtle geometric scaling over drastic topology disruptions.
      - This allocation allows evolution to primarily focus on calibrating muscle activation phases, frequencies, and sensory feedback loops on viable body chassis.
   2. **[High Neural](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs01.sim)** doubles neural operator weights, further suppressing body topology perturbations to focus on controller coordination.
   3. **[Weaker Neural](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs10.sim)** doubles morphological operator weights relative to neural operators (increasing body mutation proportion to $22.6\%$), fostering broader body shape exploration.
   4. **[Equal Weights](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-equal-probs.sim)** provides equal uniform distribution ($11.1\%$ each) across morphology ($44.4\%$) and brain ($55.5\%$).

The following table summarizes the weight settings for each operator in each configuration:
   
<div align="center">
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
</div>

##### Key findings in Batch 1
- **[Equal Operator Weights](./sim/f1-equal-probs.sim)** achieves roughly double the median velocity of the baseline, providing the best performance during almost the entire evolution ([Figure 3](#comparative-results-experiment-2)), outperforming the rest 3 settings.

- In $f_1$, **equal weights** translate to a 4-to-5 ratio between morphology and brain. This balanced ratio maintains structural diversity while preserving sufficient frequency of synaptic weight mutations ($11.1 \% $) to coordinate newly emerging limbs.

#### Batch 2 (Experiment 2)

To move beyond blunt global morphology-vs-brain ratios, **four tuned operator probability distributions** were developed based on the mechanical roles of the 9 operators in $f_1$:


##### Settings & Rationales
1. **[Strategy A (Continuous Neural Params Fine-Tuning)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-a.sim)** heavily suppresses catastrophic structural additions/deletions while prioritizing continuous physical and neural scaling. Protects working gaits from being ripped apart.
2. **[Strategy B (Morphology Exploration)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-b.sim)** strongly promotes structural branching alongside balanced neural operators. Encourages bilateral limbs, outriggers, and multi-legged chassis.
3. **[Strategy C (CPG Resonance & Control Dynamics)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-c.sim)** minimizes body alterations and concentrates on central pattern generator frequency/phase coordination.
4. **[Strategy D (3-Tier Evolutionary Pyramid)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-d.sim)** hierarchical architecture allocating ~15% to macro-topology jumps, ~35% to mesoscale wiring and modifiers, and ~50% to continuous parameter calibration.

The table below summarises the main differences between the 4 strategies:

<div align="center">
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
      <td align="center"><b>1.5</b></td>
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
      <td align="center"><b>1.5</b></td>
      <td style="background-color: #a2c9fd; color: #0F172A; font-weight: 600; text-align: center;">15.8%</td>
      <td align="center">0.1</td>
      <td style="background-color: #ccecfd; color: #0F172A; font-weight: 600; text-align: center;">2.0%</td>
      <td align="center">0.5</td>
      <td style="background-color: #addbfd; color: #0F172A; font-weight: 600; text-align: center;">7.8%</td>
    </tr>
    <tr>
      <td><code>f1_smModif</code></td>
      <td><b>Modifiers</b> (<code>LlRrCcQqFfMm</code>)</td>
      <td align="center"><b>1.5</b></td>
      <td style="background-color: #c3d1fe; color: #0F172A; font-weight: 600; text-align: center;">23.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center">0.7</td>
      <td style="background-color: #96c6fd; color: #0F172A; font-weight: 600; text-align: center;">13.7%</td>
      <td align="center"><b>1.0</b></td>
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
      <td align="center"><b>1.5</b></td>
      <td style="background-color: #c3d1fe; color: #0F172A; font-weight: 600; text-align: center;">23.1%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center"><b>1.5</b></td>
      <td style="background-color: #dbc1dc; color: #0F172A; font-weight: 600; text-align: center;">29.4%</td>
      <td align="center"><b>1.2</b></td>
      <td style="background-color: #b0ccfe; color: #0F172A; font-weight: 600; text-align: center;">18.8%</td>
    </tr>
    <tr>
      <td><code>f1_nmWei</code></td>
      <td><b>Synaptic Weight</b></td>
      <td align="center"><b>2.0</b></td>
      <td style="background-color: #e0bdd4; color: #0F172A; font-weight: 600; text-align: center;">30.8%</td>
      <td align="center">1.0</td>
      <td style="background-color: #9fcffd; color: #0F172A; font-weight: 600; text-align: center;">10.5%</td>
      <td align="center"><b>1.5</b></td>
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
</div>

#### [Comparative results](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/) (Experiment 2)

Each strategy was evaluated across 10 independent runs of strategies from [**Batch 1**](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/2026-09-26_172452/) and [**Batch 2**](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/2026-09-26_180136/) over 400 generations (20 CPU workers), summarised in the following figures.


<div align="center">

![Comparative Best Series (Linear)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/plots/logbooks_best_series.png)
_Figure 1: Comparative best-of-generation fitness trajectories._

![Comparative Confidence Intervals (Linear)](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/plots/logbooks_confidence_std_1.0.png)
_Figure 2: Mean fitness and shaded confidence intervals._

![Comparative Boxplots](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison/plots/boxplot_summary.png)

_Figure 3: Final Hall-of-Fame velocity and run duration distributions._

</div>


#### Findings: Stationary Mutation Strategies (Batches 1 & 2)

Comparing the varied baseline and equal weights strategies ([Batch 1](#tested-stationary-mutation-strategies-experiments-1-and-2)) and adjusted strategies ([Batch 2](#batch-2-experiment-2)) reveals how static operator allocations shape the evolutionary trajectory:
1. **[Strategy A](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-a.sim) (Continuous Fine-Tuning) a the highest peak fitness in Batch 2**:
   - Strategy A produced the <u>fastest individual</u> ($v_{max} = 0.017484$) among <u>strategies A-D</u>.
   - By heavily penalizing destructive topology changes and favoring continuous phenotypic tuning (`f1_smModif: 1.5`), evolution refines functional oscillatory gaits to high speeds without suffering recurrent structural collapses.

2. **[Strategy B](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-b.sim) (Branching & Articulation) championed static sructural exploration**:
   - Strategy B achieved the <u>highest average velocity among Strategies A–D</u> ($v_{mean} = 0.006325, v_{max} = 0.016070$), closely tracking `f1-equal-probs`.
   - *It shows a rapid increase in average fitness, observed during generations 100-150.*
   - Promoting branch forks `()` and joint separators `,` (`smJunct: 1.5`, `smComma: 1.5`) alongside balanced neural mutation rates ($1.0$) reliably provides populations with stable, multi-point ground contact early in evolution.

3. **[Strategy D](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-d.sim) (Hierarchical Joint Allocation) Provided Robust Baseline Mechanics**:
   - **Strategy D** achieved <u>high median velocity</u> ($v_{median} = 0.005484$), demonstrating that balancing joint insertion with synaptic tuning yields consistent locomotion, though without the exploratory breakthroughs of **Strategy B**.
   - Shows similar [**Weaker Neural**](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs10.sim) performance (in terms of mean, median andd performance trajectory behaviour).

4. **[Strategy C](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-c.sim)** behaves similar to [**High Neural**](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs01.sim) - both demonstrate underperformance:
   - Heavily suppressing morphological mutations ($<23\%$) caused noticeable stagnation.
   - This suggests that neural networks cannot compensate for a mechanically flawed or unarticulated body chassis: controllers require mechanical degrees of freedom to produce propulsion.

5. **[Equal Weights](./sims/f1-equal-probs.sim)**:
   - **Equal Weights** achieves the highest overall median ($0.006500$) and peak velocity ($0.019564$), benefiting from balanced structural and neural exploration. Across almost all the 400 generations this strategy retains the best average velocity.
   - *It demonstrates the highest increase in average fitness during the first 50 generations.*

6. **The Static Dilemma**:
   - <u>High structural exploration</u> (**Equal Weights, Strategy B**) discovers innovative body plans early, but repeatedly destabilizes mature, functional gaits in late generations.
   - <u>Conservative fine-tuning</u> (**Strategy A, Baseline**) protects mature gaits, but cannot construct complex articulated morphologies from scratch.

7. **[Best Evolved Creature](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/2026-09-26_180136/gens/HoF-f1-f1-strat-a-7.gen)  in Experiment 2 - found by Strategy A**:
   - Achieved $v = 0.017484$:
     ```cpp
     //genotype: 
     mf((fMm(FMX[*][|, r:0.846, r:1,1:3.431][S]LQLMmX[T][*][Gpart, rz:-1.725,ry:0](M(rFFCMmX[N, -4:4.187,-4:-0.104,-3:1][@,-5:1][|, -3:2.525, p:0.277, r:1])), rfCqX), ))
     ```
   - Highly articulated morphology featuring rotational muscle joints (`*`), bending muscles with dynamic feedback (`|`, `-3:2.525, p:0.277`), tactile contact sensor (`S`), body gyroscope sensor (`Gpart, rz:-1.725`), sinusoidal pattern generator (`N`), and friction/joint modifiers (`mf, fMm, F, LQLMm, T, M, rFFC, rfCq`).

   <div style="text-align: center; width: 70%; margin: 0 auto;">
   
      ![Experiment 2 Best Creature](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Exp2-best-creature.png)
   
      _Figure 4: Phenotype of the fastest creature evolved in Experiment 2._
    </div>


### Scheduled Mutation Schemes: Non-Stationary Developmental Exploration (Experiments 3-5)

To overcome the static exploration–exploitation dilemma, **non-stationary scheduled mutation distributions** across evolutionary time were introduced:

$$\vec{w}(t) = \vec{w}_k \quad \text{for } t_k \le t < t_{k+1}$$

_where_ $\vec{w}(t)$ _is the vector of mutation weights at generation_ $t$, $\vec{w}_k$ _is the vector of mutation weights for the $k$-th stage, and_ $t_k$ _is the start generation of the_ $k$-th _stage_.

#### Rationale for Scheduled Schemes

In biological morphogenesis, organisms undergo distinct developmental phases: embryonic body plan formation precedes neuromuscular differentiation and fine motor tuning. In evolutionary robotics, applying a uniform operator distribution throughout all 400 generations forces an artificial compromise. Scheduled schemes resolve this by decomposing the search into stages that mimics biological development:
1. **Initial Bootstrapping (Generations $0\text{--}100$)**: Unconstrained morphological exploration (**Equal Weights**, showing the best performance - *see [*Figure 2, 3*](#comparative-results-experiment-2)*) discovers viable multi-jointed body plans and limb branching. 
2. **Intermediate Articulation & Neuromuscular Scaffolding (Generations $100\text{--}200$)**: Biomechanical specialization (Strategy B for limbs, Strategy D for joints) allocates degrees of freedom and sensor-effector loops.
3. **Late-Stage Convergence & Parametric Polish (Generations $200\text{--}400$)**: Suppressing structural perturbations while prioritizing Strategy A or neural tuning allows continuous metric refinement of limb lengths, muscle angles, and synaptic weights without destructive morphological mutations.

#### Experiments 3-5: 
1. **Experiment 3: Multi-Stage Scheduled Switching (Schemes 1–7)** (run on 24 workers)
   - **Idea**: Evaluates diverse multi-stage schedules (from 2 to 6 developmental stages) combining initial global exploration, intermediate structural articulation, and late-stage neural exploitation.
   - **Rationale**: Constant mutation probabilities force an artificial compromise: early structural mutations discover body plans but later destroy mature gaits, while neural exploitation cannot construct bodies from scratch. Scheduled switching emulates biological morphogenesis (body plan formation preceding neuromuscular tuning). Schemes 1–2 test classic two- and three-stage scaffolding; Schemes 3–4 evaluate limb branching (Strategy B) with and without global bootstrap; Schemes 5–7 evaluate multi-tier pipelines (interleaving Strategy D joint growth and Strategy A continuous scaling) to test whether fine-grained transitions mitigate operator disruption shocks.

2. **Experiment 4: Biphasic Strategies (Schemes 1, 8, 9)** (run on 25 workers)
   - **Idea**: Evaluates cleaner, single-transition biphasic exploration schemes to mitigate operator disruption shocks, isolating the optimal duration of the initial morphological exploration window.
   - **Rationale**: Frequent phase transitions in Experiment 3 revealed operator shocks where abrupt shifts destabilized populations. Experiment 4 simplifies schedules into two clean phases: an unconstrained exploration phase followed by continuous parametric/neural exploitation. Schemes 8-100, 8-200, and 8-300 systematically vary the transition timing (100, 200, 300 gens) from Equal Weights to Strategy A to answer the central question: how long should morphological plasticity last before canalization? (Revealing the 100-generation sweet spot). Scheme 1 evaluates extended classic scaffolding (200 gens), and Scheme 9 pairs limb branching directly with continuous gait tuning.

3. **Experiment 5: Refined Morphogenetic Cascades (Schemes 2, 10, 11, 12)** (run on 20 workers each)
   - **Idea**: Standardizes schedules into a 100-generation developmental macro-stage cadence to resolve the "morphological freeze trap" through continuous biomechanical development.
   - **Rationale**: Completely zeroing morphological mutations (High Neural) freezes creatures in rigid mechanical configurations where even minor joint misalignments cannot be remedied. Experiment 5 replaces rigid freezes with continuous developmental progressions: Scheme 2 adds the vital 100-generation Equal Weights bootstrap to classic scaffolding; Scheme 10 tests whether a compact 50-generation final synaptic polish ($350 \to 400$) preserves the benefits of 250 uninterrupted generations of Strategy A co-adaptation without the freeze penalty; Schemes 11 and 12 eliminate freezes entirely, with Scheme 12 realizing a 4-stage biological morphogenetic cascade ($\text{Equal} \to \text{Strat B} \to \text{Strat D} \to \text{Strat A}$) from macro-anatomy to micro-parameter tuning.

#### Schemes tested in Experiments 3-5: 
The following 16 variations of 12 schemes were tested (10 runs per each):

  1. <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $ \xrightarrow{\text{150 gens }} $ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>_, in the experiment 4 this transition happens at gen 200_.

  2. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{150 gens }} $ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $\xrightarrow{\text{50 gens }} $ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span> - in experiment 5 these transitions happen at generations 100 and 150.

  3. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $ \xrightarrow{\text{100 gens }} $ <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>


  4. <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $\xrightarrow{\text{150 gens }}$ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>

  5. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $\xrightarrow{\text{150 gens }}$ <span style="color: #e8b6c7; font-weight: 600; text-align: center;">Strategy D</span> $\xrightarrow{\text{75 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span>
  
  6. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $\xrightarrow{\text{150 gens }} $ <span style="color: #e8b6c7; font-weight: 600; text-align: center;">Strategy D</span> $\xrightarrow{\text{75 gens }}$ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span>

  7. <span style="color: #f27282; font-weight: 600; text-align: center;">Equal weights</span> $\xrightarrow{\text{100 gens }}$  <span style="color: #ee5c73; font-weight: 600; text-align: center;">Strategy B</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #e8b6c7; font-weight: 600; text-align: center;">Strategy D</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #e6b7c9; font-weight: 600; text-align: center;">Strategy A</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #c0d0fe; font-weight: 600; text-align: center;">Weaker Neural</span> $\xrightarrow{\text{50 gens }}$ <span style="color: #b2dffd; font-weight: 600; text-align: center;">High-neural</span>






8. <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100/200/300 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span>  - 3 schemes 
9. <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{200 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span> 




10. <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span> $\xrightarrow{\text{250 gens }}$ <span style="color: #b2dffd; font-weight: 600;">High-neural</span> 
11. <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span>  
12. <span style="color: #f27282; font-weight: 600;">Equal weights</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #ee5c73; font-weight: 600;">Strategy B</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #92d4f8; font-weight: 600;">Strategy D</span> $\xrightarrow{\text{100 gens }}$ <span style="color: #e6b7c9; font-weight: 600;">Strategy A</span> 

> *Rationale, detailed numerical tables, fitness curves, confidence intervals, and per-run logbooks can be found in the [Task 3 Report: Experiment 3](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md#experiment-3-multi-stage-scheduled-switching-schemes-17), [Experiment 4](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md#experiment-4-two-stage-exploration-schemes) and [Experiment 5](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md#experiment-5-continuous-biomechanical-development--developmental-cascades).*

#### Implementation ([details](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md#implementation)):

Dynamic mutation scheduling is implemented through a lightweight interception pattern across two core scripts:
- [`scripts/FramsticksEvolutionScheduled.py`](../../scripts/FramsticksEvolutionScheduled.py) extends and reuses the [standard Framsticks-DEAP evolutionary runner](../../framspy-download/FramsticksEvolution.py), introducing argument `--schedule` in the format
    `"<gen_1>:<sim_path_1>;<gen_2>:<sim_path_2>;.."`
- [scripts/run_parallel.py](../../scripts/run_parallel.py) accepts `--schedules` / `--schemes` argument, with pointing `--script FramsticksEvolutionScheduled.py`.



### Summary of Scheduled Mutation Experiments

1. **The Critical 100-Generation Exploration Window**: Unconstrained morphological exploration (Equal Weights) is essential during the initial 100 generations to discover articulated, stable body plans. Curtailing or skipping this window cripples evolutionary potential, whereas extending it beyond 100 generations delays convergence.
2. **The Hazard of Rigid Morphological Freezes**: Completely zeroing morphological mutations (as in [**High Neural**](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-probs01.sim)) traps creatures in rigid mechanical configurations where even minor joint misalignments cannot be remedied.
3. **The Power of Continuous Biomechanical Tuning**: Replacing rigid freezes with continuous metric tuning ([**Strategy A**](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/sims/f1-strat-a.sim)) preserves developmental plasticity, reliably driving gaits to superior speeds while suppressing destructive topology mutations.



### Final Results across Experiments 1-5

In total, there were **24 configurations** of _mutation probabilities_ tested over **400 generations** each, with **10 independent runs** for each configuration, summarized and analyzed below.
However, since different number of workers was used in different experiments, temporal performance is not analyzed between different experiments.

#### [Comparative Analysis](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison_champions/)

<div align="center">

![Champions Confidence Intervals](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison_champions/plots/logbooks_confidence_std_1.0.png)
_Figure 5a: Mean best fitness and shaded confidence intervals over 400 generations for all experiment champions. Experiment 4 Scheme 8-100 and Experiment 5 Scheme 12 demonstrate the steepest sustained fitness ascent._

![Global Boxplot Across All 24 Configurations](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison_exp1_5/plots/boxplot_summary.png)
_Figure 5b: Comprehensive Hall-of-Fame final velocity (left) and run duration (right) distributions across all 24 configurations tested in Experiments 1–5 (240 total runs over 400 generations). Note the natural ordering by experiment [run folders](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/) and numerical [scheme indices](#schemes-tested-in-experiments-3-5)._

![Champions Boxplot Summary](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/results/hof_results_comparison_champions/plots/boxplot_summary.png)
_Figure 5c: Hall-of-Fame velocity and duration distributions for the selected top-performing strategies (Experiments 1–5)._

</div>

#### Performance of Top-4 Probabilistic Configurations

| Rank | Exp #idx | Configuration / Scheme | Mean Velocity | Median Velocity | Std Dev | Min Velocity | Max Velocity | Mean Duration (s) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | 
| 1 | **4** | **Scheme 8-100 (Early Freeze)** | **0.008272** | 0.005797 | 0.006459 | **0.001554** | **0.022688** | $970.7\text{ s}$ |
| 2 | **5** | **Scheme 12 (Morphogenetic Cascade)** | 0.007447 | 0.004367 | 0.007049 | 0.000352 | 0.019239 | $779.5\text{ s}$ |
| 3 | **3** | **Scheme 3 (Balanced Scaffolding)** | 0.007213 | 0.005296 | 0.006716 | 0.001013 | **0.023459** | $919.0\text{ s}$ |
| 4 | **1** | **Equal Weights** | 0.007167 | **0.006500** | **0.005391** | 0.000574 | 0.019564 | $758.5\text{ s}$ |

### Best Evolved Creature Genomes

#### 1. Best overall result - [Experiment 3 Scheme 3](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/2026-09-27_175220/gens/HoF-f1-scheme-3-3.gen)
- **genotype**:
  ```cpp
  qMLL(X[N, 12:12.399, 9:-1.407, 9:6.412, 12:4.867, fo:0.887,4:3.922][|, 8:1, r:0.929], (X[Gpart, ry:2.129]X[S]m((X[S][Gpart][Gpart]X[N, -4:-0.547, -1:1, -3:-1.7,3:11.708][|, -3:1, r:1][N, 0:0.987, -3:1.684, -4:-0.029, -4:1.827, fo:1, -6:12.219, -2:2.178, -6:3.295], , X[S][@, -9:1][Gpart]))))
  ```
- **Velocity**: $0.023459$
- **Morphology, Neural Architecture & Dynamics**:
  - **Redudant but stable <u>neural struture</u>** where dormant or isolated nodes surround main functional pathway being _effectively_ **one gyroscope (2 twin gyroscopes) -> amplified assembled signal -> bending muscle**. in the center (light square on _Figure 6a_), which turns the rightmost stick into a leg. 
  - <u>Movement</u> is executed by **jumping rhythmically** (sinusoidal activation plots on _Figure 6b_) on the rightmost leg and forcefully pushing heavy 3-part torso forward along the trajectory. Torso serves as a stabilisation mass and prevents turning upside-down. Gyroscopes located at the center of torso thus read reliable data regarding stability of the creature, generating a movement by bending muscle at the moment static position of the torso is achieved.

<div style="width: 70%; align-content: center; margin-left: auto; margin-right: auto;" >

![Benchmark Champion Creature](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Final-best-creature.png)

_Figure 6a: Phenotype and neural structure of the overall champion_

</div>

<div style="width: 100%; align-content: center; margin-left: auto; margin-right: auto; transform: scale(120%); transform-origin: left top;" >

![Benchmark Champion Creature Inspection](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Final-best-creature-inspection.png)

</div>

<div style="width: 100%; align-content: center; margin-left: auto; margin-right: auto; " >

_Figure 6b: Inspection of functioning of the best creature. The left side depicts the moment of jumping and lifting from the ground._

</div>


#### 2. Mean Velocity Champion - [Experiment 4 Scheme 8-100](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/2026-09-27_193443/gens/HoF-f1-scheme-8-100-2.gen)
- **Genotype**:
  ```cpp
  QMmQCX[S][S][*][G]X[T][Gpart,ry:-0.088,rz:0][S][Gpart][N, -1:-1.725, -4:2.469, -7:-3.609, -5:-0.702, 0:3.422,-2:1.862,in:0,0:0.885,-7:-0.332][S]FLLLX[T]rX[S][@, -6:1.078][|, -10:3.096, p:0.414,r:0.93]
  ```
- **Velocity**: $0.022688$

![Benchmark Exp 4 Best Creature](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Exp4-best-creature-inspection.png)
_Figure 7: Inspection of functioning of the experiment 4 champion. Compare to Figures 6._

- **Morphology, Neural Architecture & Dynamics**:
  - **Body** of this snake-like structure consists of one leg and three-part linear torso.
  - **Neural circuitry** is characterized by noticeable neural redundancy with multiple disconnected or silent neurons ("junk DNA"). 
  - **The main activation path, movement dynamics and technique** are similar to the overall champion. However, stabilization-acting torso suffers from snake-shaped form of the creature which less stable positioning. 

#### 3. Morphogenetic Cascade Champion - [Experiment 5 Scheme 12](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/runs/2026-09-27_230717/gens/HoF-f1-scheme-12-9.gen)
- **Genotype**:
  ```cpp
  MqMqqq((mrqMCMqLX[N, 13:0.523][G][G][|, 2:1.92][S][S][T, ry:1.482]m(QRmLq(, (MX[Gpart][T][G][T])))), X[S][@, -3:-0.432][N, -4:-3.21, -13:3.814, si:1.753, in:0.8, si:-4.394][|, -8:3.533])
  ```
- **Velocity**: $0.019239$

![Exp 5 Best Creature Inspection](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/images/Exp5-best-creature-inspection.png)

_Figure 8: Inspection of functioning of the experiment 5 champion. Movement dynamics and technique are similar to the overall champion and experiment 4 champion (Figures 6, 7). On the left side the moment of jumping is depicted._

- **Morphology, Neural Architecture & Dynamics**:
  - **Dynamics** demonstrates hopping and pushing technique, directly comparable to the champions of Experiments 3 and 4 (Figures 6 and 7).
  - **Neural circuitry** features significant number of disconnected neurons alongside **2 primary, largely independent activation pathways**: main for locomotion - **gyroscope -> bending muscle**, secondary (with low amplitude of work) - **touch sensor -> rotating muscle**. These pathways interact through **body mechanics and ground reaction forces**. However, this may lack some coordination, and jumping sometimes fails (the muscle bends, but creature doesnt jump because of no push-off support).

### Evolution Challenges

#### Summary of Empirical Observations: Neural Redundancy & Minimalist Reflex Loops
Inspection of champion genotypes across experiments in the Framsticks GUI neural viewer and via the Framsticks C-API (`frams.Model.newFromString`) reveals a consistent topological reality:
1. **Pervasive Neural Redundancy ("Junk DNA")**:
   - Across all top-performing creatures, the vast majority of evolved neural nodes are completely redundant, disconnected, or wired to non-effector endpoints. 
   - For instance, in the 15-node network of the Experiment 5 champion (and similarly saturated networks in Experiments 3 and 4 - see _Figures 6-8_), over half the nodes are silent: unused gyroscopes (`G`, `Gpart`), uncoupled tilt sensors (`T`), and isolated touch receptors (`S`) that exert zero torque on effectors.
2. **Minimalist Functional Reflex Arcs**:
   - Locomotion does not rely on intricate, heavily cross-wired central pattern generators (CPGs). Instead, actual forward displacement is driven by remarkably simple 1-to-2 sensor reflex loops:
     - **Champion 1 (Exp 3 Scheme 3)**: **2 gyroscopes -> adjusted weights -> central bending muscle**.
     - **Champion 2 (Exp 4 Scheme 8-100)**: **1 gyroscope -> bending muscle**.
     - **Champion 3 (Exp 5 Scheme 12)**: **2 independent gyroscope -> bending/rotating muscle reflex paths**.
3. **Coordination Through Physics Rather Than Neural Crosstalk**:
   - Even when multiple reflex arcs exist (as in Champion 3), there is virtually no direct synaptic interconnect between them. Synchronization emerges purely from **embodied physical interaction**: structural inertia, joint limits, gravity, and ground reaction forces couple the actuators dynamically.

#### Fitness Landscape Bias: Why Rectilinear Rewards Favor Simple One-Legged Evolution
A critical insight into why evolved creatures converge on such minimalist physical and neural architectures lies in the **fitness function formulation**:
- **Rectilinear Displacement as the Sole Metric**:
  - In the Framsticks velocity benchmark, used in this project, fitness rewards solely linear displacement along the primary forward axis:
    $$v = \frac{\Delta x}{\Delta t}$$
- **The Fitness Penalty on Multi-Legged Complexity**:
  - Evolving a multi-legged chassis or complex bilateral walking gaits requires coordinated multi-limb stabilization, lateral balance, and phase-shifted gait cycles.
  - Under a 1D rectilinear objective, **lateral movements, stabilization adjustments, or turning torque yield zero fitness reward**. In early evolutionary exploration, attempts to sprout additional limbs or complex multi-joint chassis invariably introduce parasitic ground friction, mechanical dragging, and coordination failures where limbs trip over one another, immediately reducing forward velocity.
- **Selective Pressure for Unilateral ("One-Legged") Pogo-Hopping**:
  - In contrast, a unilateral (single-leg) body plan concentrates 100% of available muscular torque directly along the rectilinear forward axis.
  - The remaining sticks are passively dragged or pushed along as an inert "torso," avoiding limb interference entirely.
  - Consequently, the rectilinear fitness landscape heavily rewards simple "one-legged" jumping evolution while actively suppressing the emergence of more complex chassis or multi-legged locomotion.

#### Evolutionary Mechanisms Explaining Disconnected Neurons:
1. **Entrenchment via Relative Indexing in $f_1$ (The Structural Spacer Effect)**:
   - In the $f_1$ genetic format, neural connections are encoded as **relative index offsets** (e.g., Node #13 connects to Node #0 with offset `-13` and Node #9 with offset `-4`).
   - Every intervening neuron—even if unconnected—acts as a positional spacer in the gene sequence. If a deletion mutation deletes an unused sensor (e.g. Node #7 or #8), the relative index offset `-4` would point to index $8$ instead of Gyroscope #9, instantly disrupting the CPG feedback loop and causing the locomotive gait to collapse.
   - Consequently, unused nodes become **structurally entrenched**: deleting them is lethal to controller function.
2. **Neutral Genetic Drift & Absence of Parsimony Pressure**:
   - The evolutionary fitness objective maximizes velocity ($v = \Delta x / \Delta t$), which is not influenced by parasitic neurons.
   - Because Framsticks imposes zero metabolic penalty for unused neurons ($\lambda \cdot N_{neu} = 0$), non-functional sensors (e.g. smell sensors, disconnected or neurons connected to no effector) incur zero selective disadvantage and accumulate freely during early exploratory generations.
3. **Cryptic Genetic Variation / Latent Reservoirs**:
   - In evolutionary robotics and biology, silent genetic material serves as a reservoir of cryptic variation: future single-point connection mutations (`f1_nmConn`) or crossovers can immediately link into existing sensory channels without requiring de novo sensor insertion.

#### The Evaluation Budget Penalty of Decoupled Operators
This architectural phenomenon exposes a fundamental inefficiency in the standard $f_1$ genetic representation: **the mutation budget penalty of decoupled operators**.
- In Framsticks $f_1$, neuron insertion (`f1_nmNeu`) and synaptic wiring (`f1_nmConn`) are independent, competing mutation operators on the roulette wheel.
- When `f1_nmNeu` triggers, it inserts a raw sensor (`[G]`, `[S]`, `[T]`) with **zero connections**. Because the node produces no torque on muscles, the mutant has identical locomotion velocity to its parent. The evaluation budget spent generating that offspring is wasted in the short term.
- For that node to ever become functional, a second, rare mutation (`f1_nmConn`) must later hit that exact locus to wire it into the motor circuit. If this second event never occurs, the node remains dead weight.
- **Why Strategy C Collapsed vs. Scheme 8-100 Succeeded**:
  - In **Strategy C (Neural Overdrive)**, $20\%$ of all mutations were allocated to `f1_nmNeu` and $20\%$ to `f1_nmConn`. The algorithm continuously burned its evaluation budget creating isolated sensors that were never connected, starving mechanical body evolution ($<20\%$) and resulting in the worst performance across all 24 configurations ($v_{mean} = 0.002754$).
  - In contrast, **Scheme 8-100** allowed neural exploration during generations $0\text{--}100$, then switched to **Strategy A**, slashing `f1_nmNeu` to just **$3.1\%$**. By cutting off the generation of useless disconnected neurons, almost $100\%$ of the remaining 300 generations of mutation budget was channeled into joint modifiers (`23.1\%`) and synaptic weights (`30.8\%`), yielding the #1 overall champion.



### Grand Conclusions & Key Insights

1. **The 100-Generation Window of Morphological Plasticity**:
   - Across all 24 configurations, **Equal Weights during the first 100 generations** was the single most decisive determinant of evolutionary success.
   - All top 4 strategies across the entire benchmark (Exp 4 Sch 8-100, Exp 5 Sch 12, Exp 3 Sch 3, Exp 1 Equal Weights) began with Equal Weights.
   - Delaying the transition to generation 200 or 300 caused performance to collapse by over $50\%$ (Scheme 8-200: $0.003969$, Scheme 8-300: $0.003456$), proving that morphological body plans become developmentally preferred early.

2. **The "Morphological Freeze Trap"**:
   - Setting morphological mutation weights strictly to zero (as in pure High Neural or classic scaffolding) is dangerous: if an evolved creature's limbs or actuator angles are even slightly misaligned, evolution cannot reorient them mechanically.
   - The top two strategies (Exp 4 Scheme 8-100 and Exp 5 Scheme 12) avoided complete freezes by using **Strategy A**, which allows continuous metric adjustments (`f1_smMod: 1.5`, $23.1\%$) while suppressing disruptive additions/deletions.

3. **Continuous Biological Cascades Outperform Abrupt Switching**:
   - While abrupt 50-generation switches induce disruption shocks, a structured 4-stage developmental cascade:
     $$\text{Global Exploration (Equal)} \to \text{Limb Branching (Strat B)} \to \text{Joint Allocation (Strat D)} \to \text{Biomechanical Tuning (Strat A)}$$
     guides evolution naturally from macro-anatomy to micro-parameter tuning, yielding top-tier performance without sacrificing stability.

4. **The Rectilinear Fitness Bias (Why One-Legged Pushers Dominate)**:
   - Because Framsticks fitness rewards exclusively forward displacement ($v = \Delta x / \Delta t$) without rewarding lateral balance, evolution heavily favors simple unilateral jumping/pushing mechanics. A single active leg pushing an inert multi-stick torso eliminates limb collision risks and channels all mechanical work directly into the forward axis, explaining why creatures across all experiments converge on extreme morphological and neural simplicity.

For complete per-run logbooks, statistical distributions, and individual experiment scripts, see the [Task 3 Detailed Report](./task3%20-%20Evolution%20&%20varying%20different%20mutations%20probs/README.md).
