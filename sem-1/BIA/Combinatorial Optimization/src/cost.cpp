#pragma once

// cost.cpp
// Functions for calculating the cost of a solution (`cost_function(...)`) to the QAP and the change in cost when swapping two elements in the permutation (`delta_cost(...)`)

#include <cstdint>

#include "dataloaders.cpp"
#include "permutation.cpp"


std::int64_t cost_function(const Matrix<int>& A, const Matrix<int>& B, const Permutation<int>& p) {
    int n = A.rows();
    if (B.rows() != n || A.cols() != n || B.cols() != n || p.size() != n)
        throw std::invalid_argument("Matrices A and B must be square and of the same size as the permutation.");
    
    std::int64_t cost = 0;
    for (int i = 0; i < n; i++) {
        const int* const a_row = A[i];
        const int* const b_row = B[p[i]];
        for (int j = 0; j < n; j++) {
            cost += a_row[j] * b_row[p[j]];
        }
    }
    return cost;
}
// p is old permutation, i and j are the indices of the two elements to be swapped in the new permutation
//https://www.cs.put.poznan.pl/mkomosinski/lectures/optimization/extras/QAP-fast-update.pdf
std::int64_t delta_cost(const Matrix<int>& A, const Matrix<int>& B, const Permutation<int>& p, int i, int j) {
    int n = A.rows();
    if (B.rows() != n || A.cols() != n || B.cols() != n || p.size() != n)
        throw std::invalid_argument("Matrices A and B must be square and of the same size as the permutation.");

    const int pi = p[i];
    const int pj = p[j];
    const int* const a_i = A[i];
    const int* const a_j = A[j];
    const int* const b_pi = B[pi];
    const int* const b_pj = B[pj];

    std::int64_t delta_cost = a_i[i] * (b_pj[pj] - b_pi[pi]) + a_j[j] * (b_pi[pi] - b_pj[pj]) +
                              a_i[j] * (b_pj[pi] - b_pi[pj]) + a_j[i] * (b_pi[pj] - b_pj[pi]);
    for (int k = 0; k < n; k++) {
        if (k != i && k != j) {
            const int pk = p[k];
            const int* const a_k = A[k];
            const int* const b_pk = B[pk];
            delta_cost += a_i[k] * (b_pj[pk] - b_pi[pk]) + a_j[k] * (b_pi[pk] - b_pj[pk]) +
                          a_k[i] * (b_pk[pj] - b_pk[pi]) + a_k[j] * (b_pk[pi] - b_pk[pj]);
        }
    }

    return delta_cost;
}
