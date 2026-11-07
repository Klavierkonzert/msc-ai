# TODO: 3D Epistasis README Feedback & Corrections

- [ ] **Answer Key Question Explicitly in Section 212**:
  - Explicitly open the discussion by stating that Baseline 2 is distinctly more useful for discovering new higher-order triplet information.
  - Reiterate that Baseline 1 is dominated by trivial positive epistasis caused by the physical fitness floor ($F \ge 0$), whereas Baseline 2 isolates genuine irreducible 3-way interactions by controlling for additive and pairwise effects.

- [ ] **Revise Line 230 (Interpretation of Baseline 2 Signs)**:
  - Avoid stating that negative values provide "little information". Negative values are highly informative: they represent diminishing marginal damage / modular redundancy saturation where pairwise knockouts have already triggered the primary failure mode.
  - Distinguish both regimes clearly:
    - **Positive $\varepsilon^{(2)} > 0$ (Green)**: Genuine 3-way synergistic buffering (knocking out 3 genes retains/restores stability better than predicted from pairwise breakdowns).
    - **Negative $\varepsilon^{(2)} < 0$ (Red)**: Modularity / functional bottleneck saturation (the 3rd knockout adds diminishing structural damage compared to pairwise expectations).

[Me; the problem is that there is no diminishing damage, the damage is almost always identical once a base gene 
b is sybstracted: dF_ijb \approx dF_jb \approx dF_b. That is there is no triple effects once a base gene is knocked our]

- [ ] **Fix Mathematical Notations & Typos in Lines 221-226**:
  - Fix notation in line 222: replace mixed $F_{b,b',s} - \Delta F_b$ with consistent fitness differences $\Delta F_{b, s_1, s_2} - \Delta F_b$ (or explicit $F(g \setminus \dots)$ expressions).
  - Fix typo in line 223: `pproduces` -> `produces`.
  - Fix expression $\Delta F_{b, b', s} - (\Delta F_{b'} + \Delta F_b)$ to properly reflect the pairwise terms being subtracted in Baseline 2.

- [ ] **Clarify Baseline 1 Definition in Line 176**:
  - Clarify that $\varepsilon^{(1)}_{ijk} = 0$ strictly means exact linear additivity ($\Delta F_{ijk} = \Delta F_i + \Delta F_j + \Delta F_k$).
  - Avoid conflating $\varepsilon^{(1)} = 0$ with pairwise decomposability, as pairwise decomposability strictly corresponds to $\varepsilon^{(2)}_{ijk} = 0$.

