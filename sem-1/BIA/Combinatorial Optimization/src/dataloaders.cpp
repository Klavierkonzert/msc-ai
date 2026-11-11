// dataloaders.cpp
// Functions for loading data from files, including the problem data (matrices) and the best known solutions (permutations and their costs)

#pragma once
#include <cinttypes>
#include <cstdint>
#include <string>
#include <vector>
#include <iostream>
#include <cstdlib>
#include <random>

#include <algorithm>
#include <set>
#include <stdexcept>
#include <initializer_list>

#include "matrix.cpp"

static std::string resolve_filename_with_default_ext(const char* filename, const char* default_ext) {
    std::string resolved = filename;
    if (!std::filesystem::path(resolved).has_extension()) {
        resolved += default_ext;
    }
    return resolved;
}

// loading data from file
// returns tuple of two matrices and the number of nodes
std::tuple<std::pair<Matrix<int>, Matrix<int>>, int> load_data_into_matrices(const char* filename, const char* default_ext=".dat");
// load the best solution from file, returns a permutation of the best solution and its cost
std::tuple<Permutation<int>, std::int64_t> load_best_solution(const char* filename, const char* default_ext=".sln");


std::tuple<std::pair<Matrix<int>, Matrix<int>>, int> load_data_into_matrices(const char* filename, const char* default_ext) {
    std::string resolved_filename = resolve_filename_with_default_ext(filename, default_ext);
    FILE* file = fopen(resolved_filename.c_str(), "r");
    if (!file) {
        perror(("Could not open file " + resolved_filename).c_str());
        return std::tuple<std::pair<Matrix<int>, Matrix<int>>, int>(std::make_pair(Matrix<int>(0), Matrix<int>(0)), 0);
    }
    int n_nodes;
    fscanf(file, "%d", &n_nodes);

    Matrix<int> matrices[2];
    for (int i = 0; i < 2; i++) {
        matrices[i] = Matrix<int>(file, n_nodes, n_nodes);
    }
    fclose(file);
    return std::tuple<std::pair<Matrix<int>, Matrix<int>>, int>(std::make_pair(matrices[0], matrices[1]), n_nodes);
}


// load (the best) solution from file, returns a permutation of the (best) solution and its cost (best cost)
std::tuple<Permutation<int>, std::int64_t> load_best_solution(const char* filename, const char* default_ext)
{
    std::string resolved_filename = resolve_filename_with_default_ext(filename, default_ext);
    FILE* file = fopen(resolved_filename.c_str(), "r");
    if (!file) {
        perror(("Could not open file " + resolved_filename).c_str());
        return std::tuple<Permutation<int>, std::int64_t>(Permutation<int>(0), 0);
    }
    int n_nodes;
    std::int64_t cost;
    fscanf(file, "%d", &n_nodes);
    fscanf(file, "%" SCNd64, &cost);

    Permutation<int> best_solution(file, n_nodes);
    fclose(file);
    return std::tuple<Permutation<int>, std::int64_t>(best_solution, cost);
}