# Assignment 7: Epistasis & Gene Linkage
## Empirical Estimation and 2D Matrix Visualization of Epistasis in Evolutionary Robotics

**Epistasis** - is a phenomenon of interdependence of genes, where the effect of one gene on the phenotype depends on the presence of other genes (non-linear interactions between genes).

The goal of this work is to investigate this phenomenon in evolutionary robotics, optimizing for _center-of-mass height_ (`vertpos`) in creatures evolved under directional encoding ($f_9$) with the following 6-character directional stick encoding semantics (each indicates a direction towards which the respective stick grows from the parent (last added) stick):
- `F` - forward
- `B` - backward
- `L` - left
- `R` - right
- `U` - up
- `D` - down

Firstly, [evolutionary optimization](#evolutionary-performance) is run under the following [parameters](#parameters-setup). Then 3 dissimilar individuals $s_1, s_2, s_3$ are selected from the final population $S^{G}, G=300$ of evolved creatures as follows:

$$\displaystyle s_1\mathrel{:=}\arg\max_{s \in S^{G}} \text{vertpos}$$

$$\displaystyle s_2\mathrel{:=}\arg\max_{s \in S^{G}\setminus\{s_1\}} \mathbb{d}(s, s_1)$$

$$\displaystyle s_3\mathrel{:=}\arg\max_{s \in S^{G}\setminus\{s_1, s_2\}} \min{\big(d(s, s_1), d(s, s_2)}\big)$$

where $d(g_1, g_2)$ denotes weighted Normalized Levenshtein Distance and Directional Composition Divergence (see the [script](select_dissimilar.py) for the exact implementation). 

Secondly, [pairwise epistasis](#pairwise-epistasis) was [estimated](./estimate_epistasis.py) for the selected creatures based on the formula provided below. In the end, [epistasis between triplets of genes](#triple-epistasis) was estimated.

<a id="parameters-setup"></a>

<details>
<summary><h3 style="display:inline">Parameters &amp; Setup</h3></summary>
<br>

- **Optimization Criterion (Fitness)**: `vertpos` (maximizing vertical position of the mass center).
- **Genetic Representation**: [**$f_9$ Representation**](https://www.framsticks.com/a/al_geno_f9.html).
- **Simulation Environment ([`eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim`](../../Framsticks55/data/))**:
  - **Deterministic Physics (`deterministic.sim`)**: Eliminates sensory, neural, and physical perturbation noise (`randinit: 0.0`, `nnoise: 0.0`, `bnoise_vel: 0.0`, `placement: 1`), enabling deterministic, noise-free single-trial evaluation (`evalcount: 1`).
  - **Sampling Period (`sample-period-2.sim`)**: Telemetry sampled every 2 simulation steps (`perfperiod: 2`) to ensure reliable vertical position evaluation throughout the creature lifespan.
  - **Morphological Focus (`only-body.sim`)**: Disables brain/neural mutations, ensuring evolutionary search focuses strictly on mechanical morphology.
- **Morphological & Syntactic Limits**:
  - **Max parts**: `-max_numparts 30`
- **EA Parameters**:
  - **Population size**: `--popsize 100`
  - **Generations**: `--generations 300`
  - **Selection**: `--tournament 5` (size 5)
  - **Crossover probability (`pxov`)**: `0.0` (pure asexual mutation-driven climb)
  - **Mutation probability (`pmut`)**: `0.9` (default Framsticks rate)
  - **Hall of Fame size**: `-hof_size 1`
  - **Replications**: `24` independent runs run in parallel on 24 physical cores

</details>

<a id="evolutionary-performance"></a>

<details>
<summary><h3 style="display:inline">Evolutionary Convergence &amp; Performance</h3></summary>
<br>

<p align="center">
  <img src="./results/evolution/plots/logbooks_best_series.png" width="49%" alt="Hall of Fame Trajectories Across 24 Runs"/>
  <img src="./results/evolution/plots/logbooks_confidence_std_1.0.png" width="49%" alt="Mean Fitness with Confidence Band"/>
  <br>
  <em><b>Figure 1a:</b> Hall of Fame best-fitness trajectories across 24 independent runs over 300 generations (left). <b>1b:</b> Mean best fitness across generations with confidence interval band (right).</em>
</p>

<p align="center">
  <img src="./results/evolution/plots/boxplot_summary.png" width="55%" alt="Distribution of Final Best Fitness"/>
  <br>
  <em><b>Figure 2:</b> Final Hall of Fame best fitness distribution and evaluation time across 24 replications.</em>
</p>

</details>

## Pairwise Epistasis

<a id = "pairwise-epistasis-formula"></a>

### Estimation

For an intact genotype $g$ of length $L$ with baseline fitness $F(g)$:
- $F(g \setminus \{i\})$ - fitness after disabling gene $i$.
- $F(g \setminus \{j\})$ -  fitness after disabling gene $j$.
- $F(g \setminus \{i, j\})$ - fitness after simultaneously disabling both genes $i$ and $j$.

The additive null model  $\mathcal{H}_0^1$ predicts the joint knockout effect to be the sum of independent single knockouts (this holds iff genes are independent) $ {\Delta F_{ij}}\equiv \Delta F_{i} + \Delta F_{j}$ , where:

$$\Delta F_i = F(g \setminus \{i\}) - F(g), \qquad \Delta F_j = F(g \setminus \{j\}) - F(g)$$

For two genes $i\ne j$, pairwise epistasis $\varepsilon_{i,j}$ measures the interaction deviation from additivity:

$$\varepsilon_{i,j} = \underbrace{\big[F(g \setminus \{i, j\}) - F(g)\big] }_{\Delta F_{ij}}- \big(\Delta F_i + \Delta F_j\big) \equiv F(g \setminus \{i, j\}) - F(g \setminus \{i\}) - F(g \setminus \{j\}) + F(g)$$

- $\varepsilon_{i,j} = 0 \implies$ additive / independent genes (White).
- $\varepsilon_{i,j} > 0 \implies$ positive epistasis (synergistic cooperation or functional redundancy / buffering - Green).
- $\varepsilon_{i,j} < 0 \implies$ negative epistasis (antagonistic breakdown / synthetic collapse - Red).

In the calculated matrices, the diagonal ($i = j$) stores the single-gene knockout effect $\Delta F_i (\equiv \Delta F_{ii})$.


### Pairwise Epistasis Matrices (Task 1)

Using[ `select_dissimilar.py`](./select_dissimilar.py) (based on hybrid Levenshtein edit distance and 6D directional composition divergence), $k=3$ dissimilar tall structures were [selected](./selected/) from the evolutionary pool:
1. [`/*9*/DDDDRLLRBBFUUUU`](./selected/selected_1_HoF-f9-14.gen) ($F = 1.0755$, $L = 15$) - top champion with vertical trunk ($UUUU$) on an asymmetric base.
2. [`/*9*/FLLRFBLRRUUUUL`](./selected/selected_2_HoF-f9-2.gen) ($F = 0.9854$, $L = 14$) - wide-base tripod posture transitioning into a vertical mast.
3. [`/*9*/DDDUDFRRBUUUDUF`](./selected/selected_3_HoF-f9-6.gen) ($F = 0.8776$, $L = 15$) - alternating stabilizing loops with upward segments.

<p align="center">
  <img src="./selected/3-selected-creatures.png" width="50%" alt="Selected Creatures"/>
  <br>

_**Figure 3:** Selected creatures (order preserved - left to right). All the creatures feature two main body parts: <u> a plinthed base</u> and a tall, erect <u>spine (chord)</u>. **Center of mass** of each creature (black fat dots) is located above the base. Shaded in dark regions denote <u>convex hulls formed by the support points (base sticks)</u>. **The criterion of static stability**: a projection of the center of mass onto the ground must lie strictly inside this convex hull (projections are indicated by black arrows). 6 arrows on the right indicate directions of stick growth._ 
</p>

<a id="fig-epistasis-matrices"></a>
<p align="center">
  <img src="./results/epistasis/epistasis_matrices.png" width="95%" alt="Pairwise Epistasis Matrices"/>
  <br>

_**Figure 4:** Pairwise epistasis matrices for_ $k=3$ _dissimilar tall structures arranged in a grid. Axis labels display gene letter and positional index. Off-diagonal elements show epistatic interaction_ $\varepsilon_{i,j}$, _while diagonal elements show single-gene knockout effects_ $\Delta F_i$ ._
</p>

### Interpretation of individual effects and interactions
<a id="table-epistasis-genes"></a>

|Phenotypic specialization| [Creature 1](./selected/selected_1_HoF-f9-14.gen)<br><code>/\*9\*/</code><code style="color: blue">DDDD</code><code style="color: purple">R</code><code style="color:red">LL</code><code style="color:purple">R</code><code style="color:green">BB</code><code style="color:lime">F</code><code style="color:#00bcd4">UUUU</code> | [Creature 2](./selected/selected_2_HoF-f9-2.gen)<br> <code>/\*9\*/</code><code style="color:lime">F</code><code style="color: red">LL</code><code style="color:purple">R</code><code style="color:lime">F</code><code style="color:green">B</code><code style="color:red">L</code><code style="color:purple">RR</code><code style="color:#00bcd4">UUUU</code><code style="color:red">L</code> | [Creature 3](./selected/selected_3_HoF-f9-6.gen)<br><code>/\*9\*/</code><code style="color: blue">DDD</code><code style="color:#00bcd4">U</code><code style="color:blue">D</code><code style="color:lime">F</code><code style="color:purple">R</code><code style="color:purple">R</code><code style="color:green">B</code><code style="color:#00bcd4">UUU</code><code style="color:blue">D</code><code style="color:#00bcd4">U</code><code style="color:lime">F</code> | 
|-| ---------- | ---------- | ---------- | 
|**Spine growth genes**| **0-3, 11-14**. The first 4 `D` and the last 4 `U` genes correspond to the <em><b><span style="color:blue">blue</span></b></em> and <em><b><span style="color:#00bcd4">cyan</span></b></em> _twin-chords_, directly responsible for the **height** of the creature. Having **two (redundant) copies** slightly increases the center of the mass height (`vertpos`). Deleting these letters individually only slightly decreases `vertpos` (rows and columns 0 to 3 and 11 to 14 are mainly zero value). |**9-13**. Since these genes program growth of the spine (`UUUUL`) only (increasing `vertpos`), they do not interact with each other, but their positive (in terms of `vertpos`) effect depends on _base_ genes (_0-3, 5-8_). In contrast to genes _9-12_, gene `L` serves stabilization purpose.|**0-3, 9-14**. Similar to the first (best) creature, there are 2 spines - <em><b><span style="color:blue">blue</span></b></em> and <em><b><span style="color:#00bcd4">cyan</span></b></em>, encoded by the genes at the ends of genome. In contrast to the former creature, 2 genes - `U`<sup>3</sup> and `D`<sup>12</sup> are the **key gene responsble for stability** of the creature, since both decrease long chords lengths (and hence <u>two pairs of genes <`U`<sup>3</sup>, `D`> and <`D`<sup>12</sup>, `U`> cancel out</u> - the same effect described in the second creature) - without them the creature overturns. **4**. The role of the gene `D`<sup>4</sup> is complementary to the gene `U`<sup>3</sup>, making it a **key gene responsible for morphological stability** - without this the <em><b><span style="color:blue">blue</span></b></em> chord would grow below _the base_ level, overturning the creature. 
|**Plinth genes**|**4**. Gene `R` tells the direction to place the <em><b><span style="color:blue">blue</span></b></em> spine (`DDDD`) in the center of creature's plinth, critical to the stability of the creature - removing this gene places the center of mass allows small physical perturbations to overturn the creature, coloring the 4th row and column into <em style="color:MediumSeaGreen">light green</em> (definitely positive effect). However, removal of just one `D` places the center of mass safely above the base. **5-6**. These genes are responsible for symmetry of a base, and hence are **critical for stability** of the whole creature (interaction with genes _4-10_). Genes encoding _spines_ have little mutual effect with these two genes individually, the relationship will appear on [3D map of epistasis](#3d-epistasis-heatmaps). **7**. Gene `R` here is directly responsible for the symmetry of the base, placing the center of mass directly on the median segment of the base hull, yielding the highest "collaboration rate" (central <em style="color:MediumSeaGreen">light green cross</em> on the matrix). **8-9**. Each of two genes `B` allows <em><b><span style="color:#00bcd4">cyan</span></b></em> chord to be placed - without one of these two genes the second spine disappears and `vertpos` drops noticeably. **10** Gene `F` places the <em><b><span style="color:#00bcd4">cyan</span></b></em> spine towards the center of the base, which is critical for stability (without this gene a creature overturns).| **0-2**. Gene `F` allows for one of the supporting sticks to emerge (**key for stabilization**), genes `LL` move this 'leg' towards the only place, where the position of the creature is stable. **3-4**. These genes alter the base form but in the way that does not affect the stability of the creature, thus these genes show **little epistasis** (~zero rows/colums). **5-8**. These genes influence the shape of _the base_ (`BL`) and position of _the spine_ on it (`RR`), and thus have positive epistasis with spine-genes. Gene <code>L<sup>6</sup></code> specifically has strong interaction with `RR` genes (<em style="color:green">dense green</em>), shortening the base extended by 2 _R_-direction genes, thus **making the base hull compact**. <u>Hence a pair `LR` cancels out (redundant subsequence)</u>|**5-8**. Genes `FRRB` form a U-shaped _base_, placing the center of mass strictly inside _the base hull_. Each gene here has an individual interaction with every other base gene.

#### Specialization of genes extracted from pairwise epistasis matrix
[The table](#table-epistasis-genes) above can be summarized as follows: after canceling out redundant subsequences of genes, rows and columns that form <em style="color:MediumSeaGreen">light green</em> to <em style="color:green">dense green</em> squares correspond to the _plinthed base_ phenes and the rows and columns that has near-zero interaction with each other (`white` squares) and intermediate interactions (<em style="color:#cefad0">pale green</em>) with the other genes, form _spine_ phene groups. See [Figure 4](#fig-epistasis-matrices)

#### Individual effects (red diagonals)
Individual (diagonal) effects $\Delta F_i$ take negative values since extraction of any gene from the genome leads to a decrease in the fitness depending on the role of the gene:
- gene encodes _spinal phene_ $\implies$ heigh slightly decreases
- gene encodes a part of _plinth_ $\implies$ creature immediately falls down yielding near-zero fitness.


## Triple Epistasis (Task 2)

### Estimation Formulas

#### Baseline 1
In the **first-order approach**, the null model $\mathcal{H}_0^1$ assumes independence and additive decomposability of individual fitness effects: 

$$\mathcal{H}_0^1:\quad \Delta F_{ijk} = \Delta F_i + \Delta F_j + \Delta F_k$$

The triplet epistasis measures the total interaction deviation from additivity:

$$\varepsilon_{ijk}^{(1)} \mathrel{:=} \underbrace{\big[F(g \setminus \{i, j, k\}) - F(g)\big]}_{\Delta F_{ijk}} - (\Delta F_i + \Delta F_j + \Delta F_k) \equiv F(g \setminus \{i, j, k\}) - F(g \setminus \{i\}) - F(g \setminus \{j\}) - F(g \setminus \{k\}) + 2F(g)$$

#### Baseline 2
In the **second-order approach**, the null model $\mathcal{H}_0^2$ accounts for both single-gene knockouts $\Delta F_i$ and all pairwise epistatic interactions between the three genes $\varepsilon_{ij}$: 

$$\mathcal{H}_0^2: \quad \Delta F_{ijk} = \Delta F_i + \Delta F_j + \Delta F_k + \underbrace{\varepsilon_{ij} + \varepsilon_{ik} + \varepsilon_{jk}}_{\text{2nd-order effects}} \equiv \Delta F_{ij} + \Delta F_{ik} + \Delta F_{jk} - (\Delta F_i + \Delta F_j + \Delta F_k)$$

Hence epistasis is calculated as:

$$\varepsilon^{(2)}_{i,j,k} \mathrel{:=} \Delta F_{ijk}- \big(\Delta F_i + \Delta F_j + \Delta F_k + \varepsilon_{ij} + \varepsilon_{ik} + \varepsilon_{jk}\big)$$

That is

$$\varepsilon^{(2)}_{i,j,k} \equiv \varepsilon^{(1)}_{i,j,k} - (\varepsilon_{ij} + \varepsilon_{ik} + \varepsilon_{jk})$$


In the calculated 3D tensors $(L \times L \times L)$:
- The main diagonal ($i = j = k$) stores the single-gene knockout effect $\Delta F_i (\equiv \Delta F_{iii})$.
- The 2D lateral planes/diagonals ($i = j \ne k$, etc.) store the pairwise epistases $\varepsilon_{ij}$.
- The off-diagonal entries ($i \ne j \ne k \ne i$) store the triplet epistasis ($\varepsilon_{ijk}^{(\cdot)}$).

### 3D Epistasis Heatmaps

<p align="center">
  <img src="./results/epistasis/epistasis_3d_combined.png" width="98%" alt="3D Epistasis Heatmaps across Baseline 1 and Baseline 2"/>
  <br>

_**Figure 5:** 3D epistasis heatmaps (balls arranged in a 3D grid) for_ $k=3$ _dissimilar creatures. **Top row:** Baseline 1 (relative to individual genes_ $\varepsilon_{ijk}^{(1)}$). _**Bottom row:** Baseline 2 (relative to pairwise interactions_ $\varepsilon_{ijk}^{(2)}$). _**Colormap:** Green - positive synergy / buffering; Red - negative / synthetic breakdown._
</p>

### Epistasis Matrix Sums Comparison

<a id="table-3d-epistasis-sums"></a>

| Creature | Genotype | $L$ | Triplet Count $\binom{L}{3}$ | Baseline 1<br>$\sum \varepsilon^{(1)}$ | Baseline 1<br> $\sum \lvert\varepsilon^{(1)}\rvert$ | Baseline 2<br> $\sum \varepsilon^{(2)}$ | Baseline 2 <br> $\sum \lvert\varepsilon^{(2)}\rvert$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | [`/*9*/DDDDRLLRBBFUUUU`](./selected/selected_1_HoF-f9-14.gen) | 15 | 455 | **+375.02** | 377.74 | **-171.78** | 224.35 |
| **2** | [`/*9*/FLLRFBLRRUUUUL`](./selected/selected_2_HoF-f9-2.gen) | 14 | 364 | **+344.29** | 344.55 | **-149.80** | 183.42 |
| **3** | [`/*9*/DDDUDFRRBUUUDUF`](./selected/selected_3_HoF-f9-6.gen) | 15 | 455 | **+274.31** | 276.66 | **-62.25** | 142.43 |


### Interpretation of 3D Triplet Epistasis

1. **Baseline 1 ($\sum \varepsilon^{(1)} \gg 0$, Strong Positive Buffering)**:
   - When evaluated against independent single-gene effects, all creatures exhibit overwhelming positive epistasis ($\sum \varepsilon^{(1)} > 0$, nearly all green balls).
   - This occurs because removing any single base gene (e.g. anchor `R`$^4$, symmetry genes `LL`$^{5-6}$, or stabilizer `F`$^{10}$ in Creature 1) causes the structure to topple over ($\Delta F \approx -1.0$). Summing three such single knockout penalties predicts an impossible fitness penalty of $-3.0$, whereas the simultaneous triple knockout cannot reduce fitness below ground level ($F=0$). Thus, the actual fitness is buffered against cumulative linear collapse ($\Delta F_{ijk} \gg \sum \Delta F$).

2. **Baseline 2 ($\sum \varepsilon^{(2)} < 0$, Irreducible Negative 3-Way Epistasis)**:
   - Once all pairwise interactions are accounted for, the total epistasis flips to negative ($\sum \varepsilon^{(2)} < 0$, prominent red clusters).
   - As predicted in [Task 1](#table-epistasis-genes), base-symmetry genes (e.g. `LL`$^{5-6}$ and `R`$^7$ in Creature 1, or `BL` and `RR`$^{5-8}$ in Creature 2) have strong pairwise collaborations with the spine anchors (`R`$^4$, `F`$^{10}$). When two of these genes are knocked out, the creature has already completely toppled over; knocking out a third gene (such as a spinal segment `UUUU`) produces diminishing marginal damage compared to what the pairwise sum predicts, manifesting as negative third-order interaction.
   - Creature 3 features the lowest magnitude of 3-way epistasis ($|\sum \varepsilon^{(2)}| = 62.25$ vs $171.78$ in Creature 1) because its alternating loops (`DDDUDFRRBUUUDUF`) distribute structural stabilization across several self-canceling sub-segments (`UD`, `DU`), making its higher-order genetic interactions more modular.

---

## How to Run
```powershell
#### 1. Parallel Evolutionary Run (24 Replications on 24 Cores)
python scripts\run_parallel.py `
    --script scripts\FramsticksEvolutionScheduled.py `
    --frams-path Framsticks55 `
    --sim "eval-allcriteria.sim;deterministic.sim;sample-period-2.sim;only-body.sim" `
    --opt vertpos `
    --max-numparts 30 `
    --popsize 100 `
    --generations 300 `
    --genformats 9 `
    --num-experiments 24 `
    --workers 24 `
    --out "assignments\Assignment 7 - Epistasis & Gene linkage\runs" `
    --stats-dir "assignments\Assignment 7 - Epistasis & Gene linkage\stats"

#### 2. Generate Evolutionary Plots
python scripts\analyze_hof.py `
    --headless `
    --logbook-dirs "assignments\Assignment 7 - Epistasis & Gene linkage\stats\2026-11-02_03" `
    --outdir "assignments\Assignment 7 - Epistasis & Gene linkage\results\evolution"

#### 3. Select Dissimilar Structures
python "assignments\Assignment 7 - Epistasis & Gene linkage\select_dissimilar.py" `
    --runs-dir "assignments\Assignment 7 - Epistasis & Gene linkage\runs" `
    --k 3

#### 4. Estimate and Visualize Pairwise Epistasis Matrices (Task 1)
python "assignments\Assignment 7 - Epistasis & Gene linkage\estimate_epistasis.py" `
    --frams-path Framsticks55 `
    --genotypes-folder "assignments\Assignment 7 - Epistasis & Gene linkage\selected" `
    --out "assignments\Assignment 7 - Epistasis & Gene linkage\results\epistasis\epistasis_matrices.png"

#### 5. Estimate and Visualize 3D Triplet Epistasis (Task 2)
python "assignments\Assignment 7 - Epistasis & Gene linkage\estimate_3d_epistasis.py" `
    --frams-path Framsticks55 `
    --genotypes-folder "assignments\Assignment 7 - Epistasis & Gene linkage\selected"
```

