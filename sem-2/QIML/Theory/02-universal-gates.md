# Quantum Computing: Universal Gate Synthesis

> *Notes translated from my 2020 bachelor term paper, cleaned up and corrected.*

## Scope (4)
0. [Physical Foundations](./00-preliminaries.md)
1. [Principle of Computation](01-quantum-computing-fundamentals.md#1-principle-of-computation)
2. [Notes on Quantum Logic](01-quantum-computing-fundamentals.md#2-notes-on-quantum-logic)
3. [Qubit Operations & Gates](01-quantum-computing-fundamentals.md#3-operations-on-qubits)
4. **Universal Gate Synthesis**:
    1. ...  
6. [Circuits & Measurement](./03-quantum-circuits.md)
7. ...


## Universal Gate Sets

A set of gates is **universal** if any unitary transformation $U \in U(2^n)$ can be approximated to arbitrary accuracy $\epsilon > 0$ by a finite sequence of gates selected from that set.

Standard universal sets include:
* $\{H, T, \text{CNOT}\}$
* $\{\text{CNOT}\} \cup U(2)$
* $\{H, Z, CZ, CCZ\}$
* $\{D_\theta\}$ for irrational $\theta/\pi$

### Decomposition into Two-Level Unitary Operators

Any unitary matrix $U$ on a $d$-dimensional space ($d = 2^n$) can be factored into a product of at most $d(d-1)/2$ two-level unitary matrices:

$$\displaystyle U = U_1^\dagger U_2^\dagger \cdots U_k^\dagger, \quad k \le 2^{n-1}(2^n - 1) = O(4^n)$$

Using Gray code state transitions, each $n$-qubit two-level unitary decomposes into $O(n^2)$ single-qubit and CNOT operations. Thus, an arbitrary $n$-qubit unitary transformation can be synthesized using 
$$O(n^2 4^n)$$
elementary single-qubit and CNOT gates.

### Solovay–Kitaev Theorem

Because the space of unitaries forms a continuum, a finite gate set can only approximate arbitrary unitaries. The approximation error between unitaries $U$ and $V$ is defined as:

$$\displaystyle E(U, V) = \sup_{|\psi\rangle} \|(U - V)|\psi\rangle\|$$

This metric bounds variation in measurement probabilities:
$$|P_U - P_V| \le 2E(U, V)$$

**Theorem:** Let $G$ generate a dense subgroup in $\text{SU}(2)$. Any target gate $U \in \text{SU}(2)$ can be approximated to precision $\epsilon$ using a sequence of gates from $G$ of length:

$$O\left(\log^c\left(\frac{1}{\epsilon}\right)\right), \text{where } c \approx 3.97$$

For an $m$-gate circuit, synthesizing an $\epsilon$-approximation requires $O(m \log^c(m/\epsilon))$ gates.

