// random.cpp : implementation of random number generation and shuffling algorithms for BIA course
// Main functions: `get_random_pair`, `get_random_pair0`, `reshuffle` (use `Permutation::reshuffle` instead) and `LCGrand` class (not used)

#include <iostream>
#include <numeric> 
#include <algorithm>
#include <string>

#include "stdlib.h"

#include <random>
#include <cmath>
#include <type_traits>
#include <cstdint>
#ifdef _OPENMP
    #include <omp.h>
#endif
#include "colors.h"


namespace random {

    struct RNGState {
        std::mt19937 rng;
        std::uniform_real_distribution<double> real01; // U[0;1] over doubles
        std::uniform_real_distribution<float> real01f; // U[0;1] over floats
        std::uniform_int_distribution<int> int01; // U{0,1}
        int cached_n;
        std::uniform_int_distribution<long long> pair_dist; // U{1,..., C(n,2)} 
        std::uniform_int_distribution<int> int_dist;        // U{0,..., n-1} 
        std::uniform_int_distribution<int> int_dist_minus;  // U{0,..., n-2} 
        RNGState()
            : rng(std::random_device{}()), real01(0.0, 1.0), real01f(0.0, 1.0f), int01(0,1), cached_n(0), pair_dist(1, 1), int_dist(0,1), int_dist_minus(0,1){}
    };

    static thread_local RNGState state;
    static unsigned int global_base_seed = 0;

    void seed(unsigned int seed){seed_global(seed);}
    // Seed policies
    void seed_global(unsigned int seed) {
        global_base_seed = seed;
        // seed current thread deterministically based on thread id
        #ifdef _OPENMP
            unsigned int tid = static_cast<unsigned int>(omp_get_thread_num());
        #else
            unsigned int tid = 0;
        #endif
            state.rng.seed(seed + tid);
    }

    void seed_thread(unsigned int seed) {
        #ifdef _OPENMP
            unsigned int tid = static_cast<unsigned int>(omp_get_thread_num());
        #else
            unsigned int tid = 0;
        #endif
            state.rng.seed(seed + tid);
    }

    // Update for the given new n:
    // - cached distribution for pair indices U{1,..., C(n,2)}
    // - cached distribution of ints U{0,...,n-1}
    void update_dist(int n) {
        long long max = (static_cast<long long>(n) * (n - 1)) / 2;
        if (max < 1) 
            max = 1;
        state.pair_dist = std::uniform_int_distribution<long long>(1, max);
        state.int_dist = std::uniform_int_distribution<int>(0, n-1);
        state.int_dist_minus = std::uniform_int_distribution<int>(0, n-2); 
        state.cached_n = n;
    }

    // Return a pair-index sampled from U{1,..., C(n,2)} using cached distribution
    int get_pair_index(int n) {
        if (state.cached_n != n) 
            update_dist(n);
        return static_cast<int>(state.pair_dist(state.rng));
    }
    // Fast U{0,n-1} using cached distribution
    int get_random_int(int n) {
        if (state.cached_n != n) 
            update_dist(n);
        return static_cast<int>(state.int_dist(state.rng));
    }
    // Fast U{0,n-2} using cached distribution
    int get_random_int_minus(int n) {
        if (state.cached_n != n) 
            update_dist(n);
        return static_cast<int>(state.int_dist_minus(state.rng));
    }

    // Fast U[0,1] using cached distribution
    double get_random_01() {
        return state.real01(state.rng);
    }
    // Fast U[0,1] using cached distribution
    float get_random_01f() {
        return state.real01f(state.rng);
    }
    // Fast U{0,1} using cached distribution
    int get_random_int01() {
        return state.int01(state.rng);
    }



// j must be greater than i, and both must be less than n
#define PAIR_INDEX(i, j, n) ( i*(2*n - i - 1)/2 + (j - i - 1))

//task 1.1;
void print_array(int* arr, int n, std::string msg="") {
    printf("%s", msg.c_str());
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}
void swap_arrays(int* arr1, int* arr2, int n, int order = 0, int offset = 0) {
    if (order == 0) {
        for (int i = 0; i < n; i++) {
            std::swap(arr1[i], arr2[i]);
        }
    } else {
    for (int i = 0; i < (n>>order); i++) {
        std::swap(arr1[(i<<order) + offset], arr2[(i <<order) +1 + offset]);
    }
    }
}

// KL divergence between two distributions P and Q, where P is the observed distribution and Q is the expected distribution. Both P and Q are arrays of probabilities that sum to 1, and length is the number of elements in the distributions.
// KL divergence D_KL(P || Q) = sum P(i) * log(P(i) / Q(i)) 
float kl_divergence(float* P, float * Q, int length) {
    float kl = 0.0f;
    for (int i = 0; i < length; i++) {
        if (P[i] > 0) { // Avoid log(0), i.e. truncate zero probabilities to a small value (e.g., 1e-10) to prevent infinite KL divergence
            kl += P[i] * log(P[i] / Q[i]);
        }
        else {
            kl += 1e-10 * log(1e-10 / Q[i]); // Add a small value to prevent infinite KL divergence
        }
    }
    return kl;
}
// D_KL(P || Q)  divergence from uniform distribution for integer counts P, where Q is the expected probability (1/length) and P is the observed count distribution (normalized by length)
float kl_divergence( float * P, int length) {
    float kl = 0.0f;
    //float Q = 1.0f / length;
    for (int i = 0; i < length; i++) {
        if (P[i] > 0) // Avoid log(0), i.e. truncate zero probabilities to a small value (e.g., 1e-10) to prevent infinite KL divergence
            kl += P[i] * log(P[i] * length ); 
        else
            kl += 1e-10 * log(1e-10 * length); // Add a small value to prevent infinite KL divergence
        //printf("Added term for index %d: %f\n", i, P[i] * log(P[i] * length ));
    }
    return kl;
}



// O(n log n) time complexity, O(n) space complexity
void reshuffle0(int* nums, int n, int begin = 0) {
    if (n <= 1) return;
    //print_array(nums, n, "Before reshuffle: ");

    reshuffle0(nums, n/2, begin);
    //print_array(nums, n, "After first half reshuffle: ");

    reshuffle0(nums + n/2, n/2 + n%2, begin);
    //print_array(nums, n, "After second half reshuffle: ");

        if (get_random_int01() == 0)
        swap_arrays(nums, nums + n/2, n/2);

    //print_array(nums, n, "After 1st swap: ");
    for (int order=1; order < int(log2(n)); order++) {
            if (get_random_int01() == 0)
            swap_arrays(nums, nums, n, order);     
        //print_array(nums, n, "After swap with order " + std::to_string(order) + ": ");

        //for (int offset = 0; offset < order; offset++)
        //    if (rand() % 2 == 0){ 
        //        swap_arrays(nums, nums, n, 1, offset);     print_array(nums, n, "After swap with order " + std::to_string(order) + " and offset " + std::to_string(offset) + ": ");}
    }
}
// O(n) time complexity, O(1) space complexity
// Fisher-Yates shuffle algorithm
void reshuffle(int* nums, int n, int begin = 0) {
    if (n <= 1) return;
        // Draw j from [i, n-1] to sample each permutation with equal probability.
        for (int i = begin; i < n; i++) {
            int j = get_random_int(n);
            std::swap(nums[i], nums[j]);
        }
}


void reshuffleP0(int* nums, int n, int cycles = 2) {
        if ( cycles == 0)
            cycles = 2;
        if (n <= 1)
            return;
        for (int c = 0; c < cycles; c++) {
            for (int i = 0; i < n; i++) {
                int j =  get_random_int(n);
                std::swap(nums[i], nums[j]);
            }
        }
    }
// void reshuffleP2(int* nums, int n, int cycles = 2) {
//         if ( cycles == 0)
//             cycles = 2;
//         if (n <= 1)
//             return;
//         for (int c = 0; c < cycles; c++) {
//             for (int i = 0; i < n; i++) {
//                 int j = random::get_random_number(i, n - 1);
//                 std::swap(nums[i], nums[j]);
//             }
//         }
//     }
void reshuffleP01(int* nums, int n, int cycles = 2) {
        if ( cycles == 0)
            cycles = 2;
        if (n <= 1)
            return;
        for (int c = 0; c < cycles; c++) {
            for (int i = 0; i < n; i++) {
                int j =  get_random_int(n);
                if (j<i)
                    j =  get_random_int_minus(n);
                std::swap(nums[i], nums[j]);
            }
        }
    }
void reshufflePi(int* nums, int n, int cycles = 2) {
        if ( cycles == 0)
            cycles = 2;
        if (n <= 1)
            return;
        for (int c = 0; c < cycles; c++) {
            for (int i = 0; i < n; i++) {
                int j = random::get_random_int(n - 1);
                std::swap(nums[i], nums[j]);
            }
        }
    }
// bad method
// void reshuffle3(int* nums, int n, int begin = 0) {
//     if (n <= 1) return;
//     for (int i = 0; i < n; i++) {
//         for (int j = i + 1; j < n; j++) {
//             if (rand() % 2 == 0) {
//                 std::swap(nums[i], nums[j]);
//             }
//         }
//     }
// }

// 2D distribution stats
// print distribution of the first, second, ..., n-th element after reshuffling an array of numbers from 1 to n for a given number of trials and reshuffling method
void print_distribution(int* nums, int n, int trials, void (*reshuffle_method)(int*, int, int), int num_reshuffle_cycles = 1) {
    float** count = new float*[n];
        float** freqs = new float*[n];
    for (int i = 0; i < n; i++) {
        count[i] = new float[n]();
            freqs[i] = new float[n]();
    }
    //place x number 
    
    int* array = new int[n];
    for (int t = 0; t < trials; t++) {
        std::copy(nums, nums + n, array);
        for (int c = 0; c < num_reshuffle_cycles; c++)
            reshuffle_method(array, n, 0);

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (array[i] == j) {
                    count[i][j]++;
                    break;
                }
            }
        }
    }
    printf("\nDistribution of each element (%%):\n", trials);
    
    printf("Els:   ");
    for (int j = 0; j < n; j++) {
        printf("%2d ", j );
    }
    
    printf("\n");

    // counts -> frequencies
    float avg_kl = 0.0f;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++)
                freqs[i][j] = count[i][j] / (float)trials;
            avg_kl += kl_divergence(freqs[i], n);
    }
    avg_kl /= n;
    for (int i = 0; i < n; i++) {
        printf("pos %d: ", i);
        for (int j = 0; j < n; j++) {
                printf("%2.0f ", 100*freqs[i][j]);
        }
            printf(" | KL=%.4f\n", kl_divergence(freqs[i], n));
        }

        // idc wise distribution
        // Count KL div between indices and uniform distr, for each element
        float avg_kl_idc = 0.0f;
        float *idc_distr = new float[n]();
        printf("KL of pos:\n");
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                idc_distr[j] = count[j][i]/ (float)trials;
            }
            printf("%.4f ", kl_divergence(idc_distr, n));
            avg_kl_idc += kl_divergence(idc_distr, n);
    }
        avg_kl_idc /= n;
        delete[] idc_distr;



        //printf("\n%sAvg KL divergence%s from uniform (per position): %f", Colors::ORANGE, Colors::RESET, avg_kl);
        //==printf("\n%sAvg KL divergence%s from uniform (per index): %f\n", Colors::ORANGE, Colors::RESET, avg_kl_idc);
        printf("\n%sAvg KL divergence%s from uniform: %f\n", Colors::ORANGE, Colors::RESET, avg_kl);

        for (int i = 0; i < n; i++){
        delete[] count[i];
            delete[] freqs[i];
        }
    delete[] count;
        delete[] freqs;
    delete[] array;
}


// random pair of not overlapping numbers from 1 to n
// O(n) time complexity, O(1) space complexity. Has better randomness properties than `get_random_pair` method, which has O(1) time complexity and O(1) space complexity, but `get_random_pair` is more efficient.
// Idea of this algorithm: generate an index from 1 to C(n, 2), and then map it to a pair of numbers (i, j) such that 0 <= i < j < n. The mapping is done by iterating through the possible values of i and calculating the number of pairs that can be formed with i as the first element. Once we find the correct value of i, we can calculate j based on the remaining index.
std::pair<int, int> get_random_pair0(int n) //generate random pair of not overlapping numbers from 1 to n
{
    int el0, el1;
    int pair_i = get_pair_index(n);
    int lower_bound, upper_bound;

    for (int k=1; k<=n; k++) 
    {
        lower_bound = (k-1)*n - k*(k-1)/2+1;
        upper_bound = k*n - k*(k+1)/2;
        //printf("Pair index: %d, k: %d, lower_bound: %d, upper_bound: %d\n", pair_i, k, lower_bound, upper_bound);
        if (lower_bound <= pair_i && pair_i <= upper_bound) {
            el0 = k - 1;
            el1 = pair_i - lower_bound + k + 1 - 1;
            break;
        }
    }
    return std::make_pair(el0, el1);
}

// Generate random pair of not overlapping numbers from 0 to n-1
// O(1) time complexity, O(1) space complexity
// Simple, but has slightly worse randomness properties than `get_random_pair0`, as it generates pairs with different probabilities. For example, the pair (0, 1) has a higher probability of being generated than the pair (0, n-1), which can lead to biased results in algorithms that rely on random pairs.
std::pair<int, int> get_random_pair(int n) {
    // Draw two distinct values uniformly from [0, n-1], then sort.
    // This makes each unordered pair (i, j), i < j, equally likely.
    int a = get_random_int(n);
    int b = get_random_int_minus(n);
    if (b >= a) {
        b++;
    }

    if (a < b)
        return std::make_pair(a, b);
    return std::make_pair(b, a);
}





} // namespace random

// 1D distribution stats
void print_pair_distribution(int n, std::pair<int, int> (*pair_method)(int), int trials=1000) {
    int n_possible_pairs = n * (n - 1) / 2;
    float *counts = new float[n_possible_pairs]();
    for (int t = 0; t < trials; t++) {
        auto pair = pair_method(n);
        int index = PAIR_INDEX(pair.first, pair.second, n);
        counts[index]++;
    }
    // obtaining probabilities from counts
    for (int i = 0; i < n_possible_pairs; i++) {
        counts[i] /= (double)(trials ); // Normalize counts to probabilities
    }
    printf("Sum of probabilities: %f\n", std::accumulate(counts, counts + n_possible_pairs, 0.0f));

    float expected_prob = 1.0f / n_possible_pairs;
    // Print the distribution
    printf("\nPair distribution (%%):\n");
    printf("Expected percentage for each pair: %.2f%%\n", 100.0 / n_possible_pairs);
    printf("KL divergence from uniform distribution: %.6f\n", random::kl_divergence(counts, n_possible_pairs));
    for (int i = 0; i < n-1; i++) {
        for (int j = i + 1; j < n; j++) {
            int index = PAIR_INDEX(i, j, n);
            printf("%4.2f ", 100 * counts[index] );
        }
        printf("\n");
    }

    delete[] counts;
}




////////////////////////////// tests /////////////////////////////////////////

// // Test for reshuffling methods and their distribution properties. The `print_distribution` function generates a specified number of random permutations using the provided reshuffling method and counts how many times each element appears in each position. It then calculates the KL divergence from a uniform distribution for each position and prints the distribution and KL divergence values. The `main` function initializes an array of numbers from 0 to n-1, calls the `print_distribution` function for different reshuffling methods, and prints the results. This allows us to compare the randomness properties of different reshuffling algorithms by analyzing their distributions and KL divergence values.
// int main() {
//     srand(time(0));

//     // LCGrand<int> rng(26); // Create a random number generator for numbers 0 to 26
//     // for (int i = 0; i <= 27; i++) {
//     //     std::cout << rng.next() << std::endl; // Print the next random number
//     // }
//     // return 0;

//     // test `reshuffle` methods
//     int n = 20;
//     int *init_permutation = new int[n];
//     for (int i = 0; i < n; i++)
//         init_permutation[i] = i;
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle0, 1);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle, 1);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle0, 2);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle, 2);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle0, 3);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle, 3);
//     random::print_distribution(init_permutation, n, 100, random::reshuffle0, 3);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffle, 3);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffleP0, 3);
//     // random::print_distribution(init_permutation, n, 100, random::reshuffleP01, 3);
//     random::print_distribution(init_permutation, n, 100, random::reshuffleP2, 3);
//     random::print_distribution(init_permutation, n, 100, random::reshufflePi, 3);
//     // print_distribution(init_permutation, n, 1000000, reshuffle3);
//     delete[] init_permutation;
//     return 0;
// }




// //// comparison of two random pair generation methods
// // int main() {
// //     srand(time(0));

// //     int n = 10;
// //     print_pair_distribution(n, get_random_pair, 100);
// //     print_pair_distribution(n, get_random_pair0, 100);
// //     // print_pair_distribution(n, reshuffle3, 1000000);
// //     return 0;
// // }