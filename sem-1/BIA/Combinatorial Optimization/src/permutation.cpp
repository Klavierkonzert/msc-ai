#pragma once

#include <string>
#include <vector>
#include <iostream>
#include <cstdlib>

#include <algorithm>
#include <set>
#include <stdexcept>
#include <initializer_list>

#include "random.h" // for random number generation in `Permutation::reshuffle`

// Simple custom Permutation class that inherits from std::vector and provides a method to `reshuffle` the elements and `print` the permutation, and compare two permutations by calculating the number of swaps needed to transform one permutation into the other (permutation `distance`).
//
// `Permutation(n)` creates an identity permutation of size n, i.e. (0,1,...,n-1).
//
// Use `reset` method to set the current permutation to the identity permutation, and `reshuffle` method to randomly shuffle the elements of the permutation in place using the Fisher-Yates algorithm. The `print` method prints the elements of the permutation, with an optional message and delimiter between elements. 
template <typename T=int>
class Permutation: public std::vector<T> {
private:
    // Offset to allow for permutations that do not start at 0, e.g. (1,2,...,n) instead of (0,1,...,n-1). This is useful for loading permutations from files that use 1-based indexing.
    T offset =0;
    // Normalize the permutation by subtracting the offset from each element, so that the permutation starts at 0. This is useful for calculating the distance between permutations, as the distance is defined in terms of the number of swaps needed to transform one permutation into the other, and the identity permutation is defined as (0,1,...,n-1).
    void normalize() {
        if ((this->size() != 0) && (this->offset != 0)) {
            for (size_t i = 0; i < this->size(); i++) {
                (*this)[i] -= this->offset;
            }
            this->offset = 0;
        }
    }
public:
    enum class DistanceMethod {
        CAYLEY,
        HAMMING
    };

    Permutation() = default;

    // Constructor that takes a vector and initializes identity permutation - the permutation with numbers from 0 to n-1
    explicit Permutation(T n, T offset = 0) : std::vector<T>(n) {
        if (n > 0) {
            this->offset = offset;
            for (T i = 0; i < n; i++)
                (*this)[i] = i + offset;
        }
    }

    // Copy constructor
    Permutation(const Permutation& other) : std::vector<T>(other) {
        if (this->size() > 0) {
            this->offset = other.offset;
            if (this->offset != 0)
                normalize();
        }
    }
    // Initializer list constructor
    Permutation(std::initializer_list<T> init) : std::vector<T>(init) {
        if (this->size() > 0) {
            T max_elem = *std::max_element(this->begin(), this->end());
            this->offset = *std::min_element(this->begin(), this->end());
            size_t n_unique = std::set<T>(this->begin(), this->end()).size();
            if (n_unique != this->size()) {
                throw std::invalid_argument("Initializer list contains duplicate elements, which is not allowed in a valid permutation.");
            }
            if (this->offset < 0 || max_elem >= this->size()) {
                throw std::invalid_argument("Initializer list contains elements that are out of range for a valid permutation.");
            }
            if (this->offset != 0)
                normalize();
        }
    }
    // Constructor that takes a file pointer and reads the permutation from the file, given the number of elements in the permutation
    Permutation(std::FILE* file, size_t n) : std::vector<T>(n) {
        if (n > 0) {  
            for (size_t i = 0; i < n; i++)
                fscanf(file, "%d", &(*this)[i]);     
            this->offset = *std::min_element(this->begin(), this->end());      
            if (this->offset != 0)
                normalize();
        }
    }

    // Method to reshuffle the permutation using Fisher-Yates algorithm
    // O(n) time complexity, O(1) space complexity
    // reshuffle the permutation in place, done in `cycles` rounds, default is 2.
    // to further improve randomness, reshuffle every 2 orders of magnitude of the number of cycles, staring from 100 (i.e. reshuffle 1 for 1-100 cycles, 2 times for 10000 cycles, etc.)
    void reshuffle(int cycles = 2) {
        const int n = static_cast<int>(this->size());
        if (n <= 1)
            return;
        for (int c = 0; c < cycles; c++) {
            for (int i = 0; i < n; i++) {
                //U{i,..., n-1} is not used since using both U{0,...,n-1} and U{i,..., n-1} yields similar distribution (see `random.cpp` experiments) //size_t j = random::get_random_number(0, n - 1);
                int j = random::get_random_int(n - 1);
                std::swap((*this)[i], (*this)[j]);
            }
        }
    }
    // Method to reset the permutation to the identity permutation (0,1,...,n-1) or (offset, offset+1,..., offset+n-1) if offset is not 0
    // O(n) time complexity, O(1) space complexity
    void reset()
    {
        for (size_t i = 0; i < this->size(); i++)
            (*this)[i] = i + this->offset;
    }
    
    void print(std::string msg="", std::string delim=" ", bool with_offset=true) const {
        if (!msg.empty()) {
            std::cout << msg << std::endl;
        }
        for (const auto& elem : *this) {
            if (with_offset) {
                std::cout << elem + offset << delim;
            } else {
                std::cout << elem << delim;
            }
        }
        std::cout << std::endl;
    }
    // swap elements at indices i and j in the permutation
    // O(1) time complexity, O(1) space complexity
    // Note: caller must ensure i and j are valid indices (no bounds checking)
    void swap(int i, int j) {
        std::swap((*this)[i], (*this)[j]);
    }

    // find the index of the first occurrence of a value in the permutation
    // O(n) time complexity, O(1) space complexity
    int index_of(const T& value, int start = 0) const {
        for (int i = start; i < this->size(); i++) {
            if (this->data()[i] == value) {
                return i;
            }
        }
        throw std::invalid_argument("Value not found in permutation.");
    }


    // Cayley distance between two permutations of the same size, defined as the number of permutations necessary to transform one permutation into the other by swapping two elements in the permutation.
    // Cannot be greater than n-1, where n is the size of the permutation, consider the worst case (1,2,...,n-1,0) and (0,1,2,...,n-1), where the distance is n-1.
    // O(n^2) time complexity, O(n) space complexity. Time complexity can be improved to O(n) 
    int cayley_distance(const Permutation& other) const {
        if (this->size() != other.size()) {
            printf("size of this permutation: %zu, size of other permutation: %zu\n", this->size(), other.size());
            throw std::invalid_argument("Permutations must be of the same size to calculate distance.");
        }
        Permutation<T> temp(*this);
        int dist = 0;

        for (int i = 0; i < temp.size(); i++) {
            if (temp[i] != other[i]) {
                dist++;
                temp.swap(i, temp.index_of(other[i], i+1));
            }
        }
        return dist;
    }
    // Hamming distance between two permutations of the same size, defined as the number of positions at which the corresponding elements are different.
    // O(n) time complexity, O(1) space complexity.
    int hamming_distance(const Permutation& other) const {
        if (this->size() != other.size()) {
            printf("size of this permutation: %zu, size of other permutation: %zu\n", this->size(), other.size());
            throw std::invalid_argument("Permutations must be of the same size to calculate distance.");
        }
        int dist = 0;
        for (int i = 0; i < this->size(); i++) {
            if ((*this)[i] != other[i]) {
                dist++;
            }
        }
        return dist;
    }
    // Distance between two permutations using the specified method (Cayley or Hamming)
    int distance(const Permutation& other, DistanceMethod method) const {
        switch (method) {
            case DistanceMethod::CAYLEY:
                return cayley_distance(other);
            case DistanceMethod::HAMMING:
                return hamming_distance(other);
            default:
                throw std::invalid_argument("Unknown distance method.");
        }
    }
    // distance normalized to [0, 1]:
    // - Cayley: max is n-1, so divide by n-1
    // - Hamming: max is n (all positions differ), so divide by n
    float normalized_distance(const Permutation& other, DistanceMethod method = DistanceMethod::CAYLEY) const {
        const size_t n = this->size();
        if (n == 0) return 0.0f;
        switch (method) {
            case DistanceMethod::CAYLEY:
                return (n <= 1) ? 0.0f : static_cast<float>(cayley_distance(other)) / static_cast<float>(n - 1);
            case DistanceMethod::HAMMING:
                return static_cast<float>(hamming_distance(other)) / static_cast<float>(n);
            default:
                throw std::invalid_argument("Unknown distance method in normalized_distance.");
        }
    }


    // Cayley distance from the identity permutation, defined as the number of permutations necessary to transform the given permutation into the identity permutation by swapping two elements in the permutation.
    // Cannot be greater than n-1, where n is the size of the permutation, consider the worst case (1,2,...,n-1,0).
    // O(n^2) time complexity, O(n) space complexity. Time complexity can be improved to O(n) 
    size_t cayley_weight() const {
        Permutation<T> temp(*this);
        size_t dist = 0;

        for (size_t i = 0; i < temp.size(); i++) {
            if (temp[i] != i) {
                dist++;
                temp.swap(i, temp.index_of(i, i+1));
            }
        }
        return dist;
    }
    size_t hamming_weight() const {
        size_t dist = 0;
        for (size_t i = 0; i < this->size(); i++) {
            if ((*this)[i] != i) {
                dist++;
            }
        }
        return dist;
    }
    size_t weight(DistanceMethod method) const {
        switch (method) {
            case DistanceMethod::CAYLEY:
                return cayley_weight();
            case DistanceMethod::HAMMING:
                return hamming_weight();
            default:
                throw std::invalid_argument("Unknown distance method.");
        }
    }
    // Permutation order normalized by the size of the permutation -1
    float normalized_weight(DistanceMethod method = DistanceMethod::CAYLEY) const {
        return static_cast<float>(weight(method)) / (this->size() - 1);
    }
};
