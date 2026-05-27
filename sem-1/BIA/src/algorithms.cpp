// algorithms.cpp
// all the algorithms accept `Problem` (as a container for a QAP problem instance: 2x`Matrix`, size, name of the problem) and `Permutation` (as a container for a solution to the QAP problem instance) as arguments, and modify the `Permutation` in place to find a better solution to the QAP problem instance.
// The algorithms can be called with different levels of verbosity, which can be used for debugging and understanding the behavior of the algorithms. The algorithms can also be modified to accept additional parameters, such as a maximum number of iterations or a time limit, to control the stopping criteria of the algorithms.
// actual signature: void (*method)(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)
#pragma once



#include "dataloaders.cpp"
// #include "permutation.cpp"
#include "random.cpp"
#include "cost.cpp"
#include "problem.cpp"

#include <cmath>
#include <cinttypes>
#include <cstdint>
#include <omp.h>
#include <tuple>

#include "colors.h"
#include "timing.h"


// Unified run configuration used by all algorithms.
// Contains the following fields:
// - `verbose` (int): verbosity level for the algorithm run, where higher values indicate more output for debugging
// - `max_iterations` (int): maximum number of iterations for the algorithm run. If 0, there is no limit on the number of iterations. This is typical config for local search algorithms
// - `max_time_seconds` (double): maximum time in seconds for the algorithm run. If 0.0, there is no time limit. This is typical config for random search and random walk algorithms. 
// If both `max_iterations` and `max_time_seconds` are provided, the algorithm will stop when either of the limits is reached.
// - `hyperparameters` (map<string, double>) (optional): a map of hyperparameter names to their values, which can be used to pass additional parameters specific to certain algorithms (e.g. cooling schedule parameters for simulated annealing). This allows for flexibility in configuring the algorithms without changing the function signatures.
struct AlgorithmRunConfig {
    int verbose = 0;
    int max_iterations = 1000;
    double max_time_seconds = 60.0;
    std::map<std::string, double> hyperparameters = {};
    AlgorithmRunConfig() = default;
    AlgorithmRunConfig(const int verbose, const int max_iterations, const double max_time_seconds, const std::map<std::string, double> hyperparameters=std::map<std::string, double>()) : verbose(verbose), max_iterations(max_iterations), max_time_seconds(max_time_seconds), hyperparameters(hyperparameters)
    {
        if (max_iterations < 0 || max_time_seconds < 0.0 || (max_iterations == 0 && max_time_seconds == 0.0)) {
            throw std::invalid_argument("Invalid AlgorithmRunConfig: max_iterations and max_time_seconds must be non-negative, and at least one of them must be greater than 0.");
        }
    }
};
// Helper function to create `AlgorithmRunConfig` for iteration-based algorithms
inline AlgorithmRunConfig iter_cfg(const int max_iterations, const int verbose = 0, const std::map<std::string, double> hyperparameters = {}) {
    return AlgorithmRunConfig{verbose, max_iterations, 0.0, hyperparameters};
}
// Helper function to create `AlgorithmRunConfig` for time-based algorithms
inline AlgorithmRunConfig time_cfg(const double max_time_seconds, const int verbose = 0, const std::map<std::string, double> hyperparameters = {}) {
    return AlgorithmRunConfig{verbose, 0, max_time_seconds, hyperparameters};
}



// Tuple of metrics for a run of an algorithm on a problem instance:
// - best cost found, 
// - number of algorithm steps (step = changing the current solution, that is number of swaps), 
// - number of evaluated (i.e., visited – full or partial evaluation) solutions,
// - `rel_eff` (relative efficiency) - the time-weighted average cost of the incumbent solution during the run, divided by the best known cost, minus 1. This metric captures how efficiently the algorithm improves the solution over time, with lower values indicating more efficient improvement.
// - `norm_eff` (normalized efficiency) - the time-weighted average cost of the incumbent solution during the run, divided by the Frobenius product of the problem matrices, minus normalized best known cost. This metric captures how efficiently the algorithm improves the solution relative to the problem's scale, with lower values indicating more efficient improvement.
// - `total_run_time_seconds`: total run time of the algorithm in seconds.
using AlgorithmRunMetrics = std::tuple<std::int64_t, int, int, double, double, double>; 




/*************************************** Declarations ******************************************************* */

AlgorithmRunMetrics heuristic_local_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config = {});
AlgorithmRunMetrics steepest_local_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config = iter_cfg(1000));
AlgorithmRunMetrics greedy_local_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config = iter_cfg(1000));
AlgorithmRunMetrics random_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config = time_cfg(60.0));
AlgorithmRunMetrics random_walk_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config = time_cfg(60.0));

template <typename Tprecision=float
>AlgorithmRunMetrics simulated_annealing_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config);
AlgorithmRunMetrics adaptive_simulated_annealing_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config);
float GetLamTargetProbability(float progress);

AlgorithmRunMetrics tabu_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config);


namespace {
// Helper structure to the following statistiics:
// - `total_n_swaps` - total number of swaps (i.e. solution changes)/new solutions made by the algorithm during the run, which is a measure of the algorithm's search effort and can be used to compare the efficiency of different algorithms in terms of how many solution changes they make to find a good solution.
// - `rel_eff` - relative efficiency [AUC] - the time-weighted average cost of the incumbent solution during the run, divided by the best known cost, minus 1. This metric captures how efficiently the algorithm improves the solution over time, with lower values indicating more efficient improvement.
// - `norm_eff` - normalized efficiency [AUC] - the time-weighted average cost of the incumbent solution during the run, divided by the Frobenius product of the problem matrices, minus normalized best known cost. This metric captures how efficiently the algorithm improves the solution relative to the problem's scale, with lower values indicating more efficient improvement.
struct StatisticsAccumulator {
    int total_n_swaps = 0, total_n_eval_solutions = 0;

    double best_known_cost, frobenius_product;
    double start_time, last_checkpoint_time=0.0, time_weighted_cost_cum_sum=0.0, total_time=0.0;

    explicit StatisticsAccumulator(const Problem<int>& problem) :
        start_time(algorithm_time_now()),
        best_known_cost(static_cast<double>(problem.get_best_cost())),
        frobenius_product(problem.get_matrices().first.norm() * problem.get_matrices().second.norm()) {}

    // Run before best cost update
    // Sums up the time elapsed since the last checkpoint, multiplied by the current best cost BEFORE update
    // Increases number of swaps (changed solutions) by 1, as the best cost is updated after a swap is made
    inline void checkpoint(std::int64_t current_best_cost) {
        const double current_time = algorithm_time_now() - start_time;
        const double time_delta = current_time - last_checkpoint_time;
        if (time_delta > 0.0) {
            time_weighted_cost_cum_sum += time_delta * static_cast<double>(current_best_cost);
            last_checkpoint_time = current_time;
        }
        total_n_swaps++; 
    }

    // Run after the algorithm finishes to compute the total time of the run and finalize the efficiency metrics. Should be called after the last `checkpoint` call.
    inline void finish(std::int64_t current_best_cost) {
        checkpoint(current_best_cost); 
        total_n_swaps --; // since `final` must be called outside the loop
        total_time = algorithm_time_now() - start_time;
        if (total_time <= 0.0) {
            total_time = use_cpu_time_clock() ? (1.0 / static_cast<double>(CLOCKS_PER_SEC)) : 1e-9;
            time_weighted_cost_cum_sum = total_time * static_cast<double>(current_best_cost);
        }
    }

    // Returns a tuple of (total number of swaps, relative efficiency, normalized efficiency, total time) based on the accumulated time-weighted cost and the best known cost. Should be called after `finish()` method to ensure that total time is computed.
    inline std::tuple<int, double, double, double> get_metrics() const {
        auto [rel_eff, norm_eff] = get_efficiency();
        return {total_n_swaps, rel_eff, norm_eff, get_total_time()};
    }
    // Returns a tuple of (relative efficiency, normalized efficiency) based on the accumulated time-weighted cost and the best known cost. 
    inline std::pair<double, double> get_efficiency() const {
        double denom1 = (total_time * best_known_cost);
        double rel_eff = denom1 > 0 ? (time_weighted_cost_cum_sum / denom1 - 1) : 0.0;
        double denom2 = (total_time * frobenius_product);
        double norm_eff = denom2 > 0 ? ((time_weighted_cost_cum_sum - total_time * best_known_cost) / denom2) : 0.0;
        return {rel_eff, norm_eff};
    }
    inline double get_total_time() const {
        return total_time;
    }
};



/******************************Helper functions for printing algorithm start and finish messages with consistent formatting and colors. 
 * These functions are used in the algorithms to print informative messages about the progress of the algorithms, including the initial permutation, initial cost, best cost found, best permutation found, number of iterations, and total number of swaps (if applicable). 
 * The messages are color-coded based on the algorithm type for better visualization in the console output. 
 ***********************************************************************************************************************************************************************************************/

void print_start_message(const char* color, const char* tag, const char* algorithm_name,
                  const std::string& problem_name, const Permutation<int>& permutation, std::int64_t initial_cost)
{
    printf("\n%s%s:%s %sProblem: %s%s\n", color, tag, Colors::RESET, Colors::BOLD, Colors::RESET,
        problem_name.c_str());
    printf("%s%s:%s %s%s starting with initial permutation:%s ", color, tag, Colors::RESET,
        Colors::BOLD, algorithm_name, Colors::RESET);
    permutation.print();
    printf("%s%s:%s %sCost of initial permutation:%s %" PRId64 "\n", color, tag, Colors::RESET,
        Colors::BOLD, Colors::RESET, initial_cost);
}
void print_new_solution_message(const char* color, const char* tag, const char* algorithm_name,
                const Permutation<int>& new_permutation, std::int64_t new_cost, std::int64_t cost_delta)
{
    printf("%s%s:%s %sNew best solution found with cost: %s%" PRId64 "%s (cost change: %s%" PRId64 "%s)\n", color, tag, Colors::RESET,
        Colors::BOLD, Colors::RESET, new_cost, Colors::BOLD, Colors::RESET, cost_delta, Colors::RESET);
    printf("%s%s:%s %sNew best permutation:%s ", color, tag, Colors::RESET,
        Colors::BOLD, Colors::RESET);
    new_permutation.print();
}
void print_finish_message(const char* color, const char* tag, const char* algorithm_name,
                const Permutation<int>& best_permutation,
                AlgorithmRunMetrics metrics, int iterations = 0)
{
    const auto [best_cost, total_n_swaps, total_n_eval_solutions, rel_eff, norm_eff, total_time] = metrics;
    printf("\n%s%s:%s %s%s finished after %d iterations.%s\n", color, tag, Colors::RESET,
        Colors::BOLD, algorithm_name, iterations, Colors::RESET);
    printf("%s%s:%s %sBest cost found:%s %" PRId64 "\n", color, tag, Colors::RESET, Colors::BOLD,
        Colors::RESET, best_cost);
    printf("%s%s:%s %sBest permutation found:%s ", color, tag, Colors::RESET, Colors::BOLD,
        Colors::RESET);
    best_permutation.print();
    if (total_n_swaps >= 0) {
     printf("%s%s:%s %sTotal number of swaps:%s %d\n", color, tag, Colors::RESET,
         Colors::BOLD, Colors::RESET, total_n_swaps);
    }
    if (total_n_eval_solutions >= 0) {
     printf("%s%s:%s %sTotal number of evaluated solutions:%s %d\n", color, tag, Colors::RESET,
         Colors::BOLD, Colors::RESET, total_n_eval_solutions);
    }
}
} // namespace






/****************************************************************************************************************************/
/************************************** Definitions of algorithms ***********************************************************/  
/***************************************Part 1: Local Search and Random algs*************************************************/
/****************************************************************************************************************************/


// @brief Heuristics algorithm for QAP.
//
// Idea: match the largest and the smallest elements in the matrices, and then make a swap and recalculate cost
// An alternative idea could be to match the largest and the lowest (in terms of euclidean norm) rows or columns 
// 
// Permutation will be modified in place, so it is passed by reference. The initial permutation should be randomized or given as is before calling this function.
// Searches for the largest element in the first matrix and the smallest element in the second matrix, and if they are not matched in the current permutation, it modifies the permutation by swapping the elements at the indices of the largest element in the first matrix and the smallest element in the second matrix. The algorithm stops when no improving swaps are found in an iteration or when a maximum number of iterations is reached.
//
// Sources of randomness: 
//
// -initial permutation `p` is randomized
//
// @param problem       the QAP problem instance
// @param p             initial permutation. Will be modified in place, so it is passed by reference. Should be randomized or given as is before calling this function.
// @param run_config    configuration for the algorithm run, including `max_iterations`, optional `max_time_seconds`, and `verbosity`.
AlgorithmRunMetrics heuristic_local_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config){
    const auto& [verbose, max_iterations, max_time_seconds,    _] = run_config;
    const auto& [name, n, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto& A = matrices.first;
    const auto& B = matrices.second;

    std::int64_t delta, best_cost = cost_function(A, B, p);
    int total_n_eval_solutions = 0;
    StatisticsAccumulator efficiency_stats_acc(problem);

    if (verbose) print_start_message(Colors::BLUE, "H", "Heuristic", name, p, best_cost);

    bool no_improving_swaps = false;
    int it = 0;

    // it is possible that after the first iteration of matching the largest and the smallest elements in the matrices, the new permutation still has the same largest element in A and the same smallest element in B unmatched, thus we can have multiple improving swaps in a row, so we continue iterating until no improving swaps are found, or until we reach the maximum number of iterations, or until the optional time limit is reached
    while (true) {
        if ((max_iterations > 0 && it >= max_iterations) || no_improving_swaps)
            break;
        else if ((max_time_seconds > 0 && algorithm_time_now() - efficiency_stats_acc.start_time >= max_time_seconds)) {
            if (verbose) printf("%sH: iteration %d:%s Time limit %f reached, stopping early.\n", Colors::BLUE, it, Colors::RESET, max_time_seconds);
            break;
        }

        if (verbose) printf("%sH: iteration %d:%s\n", Colors::BLUE, it, Colors::RESET);
        no_improving_swaps = true;

        for (int i = 0; i < n-1; i++) {
            // Matrix A is fixed, permutation affects matrix B
            // find max element in the i-th row of A and min el in the i-th row of B:
            auto [maxA_val, maxA_i, maxA_j] = A.find_max_element(i, i); // O(n-i)
            auto [minB_val, minB_i, minB_j] = B.find_min_element(i, i); // O(n-i)

            // If ||row or col||_F is used as a min/max search crit:
            // auto [maxA_val, maxA_i] = A.find_max_row(i);
            // auto [minB_val,minB_j ]= B.find_min_col(i);

            // it was a partial evaluation of the solution, thus
            total_n_eval_solutions ++;

           if (verbose>2) 
            printf("H: Iteration %d: row %d: maxA_val: %d at (%d, %d), minB_val: %d at (%d, %d)\n", it, i, maxA_val, maxA_i, maxA_j, minB_val, minB_i, minB_j);

           //if (maxA_i==minB_j){
            if (maxA_i == minB_i && maxA_j == minB_j) {
                if (verbose > 2) printf("H: The largest element in A and the lowest element in B are already matched in the permutation.\n");
            }
            else //else modify the permutation by swapping the elements at the indices of the largest element in A and the lowest element in B
            {
                // delta calculation for single elements matching:
                delta = delta_cost(A, B, p, maxA_j, minB_j);
                ////std::swap(p[maxA_j], p[minB_j]);
                //// delta += delta_cost(A, B, p, maxA_i, minB_i);
                //// if (delta>=0) // if no effect or it's worse, then redo swap // if single elements are matched
                ////     std::swap(p[maxA_j], p[minB_j]);

                // if rows/cols are matched:
                //delta = delta_cost(A, B, p, maxA_j, minB_j); 
                //// delta = delta_cost(A, B, p, maxA_i, minB_j);

                if (verbose > 2) {
                    printf("H: Swapping elements at indices %d and %d in the permutation.\n", maxA_j, minB_j);
                    printf("H: Cost change: %" PRId64 "\n", delta);
                }

                if (delta < 0) {
                    efficiency_stats_acc.checkpoint(best_cost);
                    // swaps if single elements are matched
                    std::swap(p[maxA_j], p[minB_j]); // already done
                    ////std::swap(p[maxA_i], p[minB_i]); 

                    // swaps if rows/cols are matched instead of single elements:
                    // std::swap(p[maxA_i], p[minB_j]); 

                    best_cost += delta;
                    no_improving_swaps = false;

                    if (verbose > 1) {
                        printf("%sH: iteration %d: row %d:%s Permutation after swap: ", Colors::BLUE, it, i, Colors::RESET);
                        p.print();
                        printf("%sH: iteration %d: row %d:%s Cost after swap: %" PRId64 "\n", Colors::BLUE, it, i, Colors::RESET, best_cost);
                    }
                }
            }
        }
        if (verbose && no_improving_swaps) printf("%sH: iteration %d:%s No improving swaps found, stopping early.\n", Colors::BLUE, it+1, Colors::RESET);
        it++;
    }
    efficiency_stats_acc.finish(best_cost);
    auto [total_n_swaps, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    AlgorithmRunMetrics metrics = {best_cost, total_n_swaps, total_n_eval_solutions, rel_eff, norm_eff, total_time};
    if (verbose) print_finish_message(Colors::BLUE, "H", "Heuristic", p, metrics, it);
    return metrics;
}


// @brief Steepest local search algorithm for QAP.
//
// Explores the whole neighborhood of the current solution and moves to the best solution in the neighborhood, if it is better than the current solution. The neighborhood is defined as all permutations that can be obtained by swapping two elements in the current permutation. The algorithm stops when no improvement is found in the neighborhood or when a maximum number of iterations is reached.
//
// Sources of randomness:
// 
// - initial permutation `p` is randomized, 
//
// - the order of the neighborhood exploration is NOT randomized, since the algorithm explores the whole neighborhood to select the best solution.
//
// @param problem       the QAP problem instance
// @param p             initial permutation. Will be modified in place, so it is passed by reference. Should be randomized or given as is before calling this function.
// @param run_config    configuration for the algorithm run, including `max_iterations` and `verbosity`. Max time `max_time_seconds` can be provided. If `max_time_seconds` is provided, the algorithm will stop when the time limit is reached, in addition to the other stopping criteria.
AlgorithmRunMetrics steepest_local_search_qap(const Problem<int>& problem, Permutation<int> &p, const AlgorithmRunConfig& run_config) 
{
    const auto& [verbose, max_iterations, max_time_seconds, _] = run_config;
    const auto& [name, problem_size, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t delta, best_delta_in_neighborhood, best_cost = cost_function(A, B, p);
    int best_i, best_j;
    int total_n_eval_solutions = 0;
    bool improved = true;
    StatisticsAccumulator efficiency_stats_acc(problem);

    if (verbose) print_start_message(Colors::MAGENTA, "S", "Steepest LS", name, p, best_cost);

    int iter = 0;

    // terminated when no improvements are found (local minimum is reached), or when the maximum number of iterations is reached, or when the time limit is reached IF PROVIDED, whichever comes first
    while (true) 
    {
        if ((max_iterations > 0 && iter >= max_iterations) || !improved )
            break;
        else if (max_time_seconds > 0 && (algorithm_time_now() - efficiency_stats_acc.start_time >= max_time_seconds))
        {
            if (verbose) printf("%sS: iteration %d:%s Time limit %f reached, stopping early.\n", Colors::MAGENTA, iter+1, Colors::RESET, max_time_seconds);
            break;
        }
        
        // Exploring the neighborhood of the current solution by swapping each pair of elements in the permutation and calculating the cost change (delta) for each swap. If a swap results in a better solution (delta < 0), we perform the swap and update the best cost. We continue exploring the neighborhood until we have explored all pairs of elements or until we find an improvement. If we find an improvement, we set improved to true and continue to the next iteration of the local search. If we do not find any improvement after exploring the entire neighborhood, we set improved to false and exit the loop.
        best_delta_in_neighborhood = 0;
        best_i = -1; best_j = -1; // indices of the best swap in the neighborhood
        improved = false;
        
        for (int i = 0; i < problem_size - 1 ; i++) {
            for (int j = i+1; j < problem_size ; j++) {
                delta = delta_cost(A, B, p, i, j);
                total_n_eval_solutions++; // partial evaluation of the solution
                if (verbose > 2) {
                    printf("S: Evaluating swap of elements at indices %d and %d in the permutation.\n", i, j);
                    printf("S: Cost change for this swap: %" PRId64 "\n", delta);
                }
                if (delta < 0 && delta < best_delta_in_neighborhood) {
                    best_delta_in_neighborhood = delta;
                    best_i = i ;
                    best_j = j ;
                }
            }
        }

        if (best_i != -1 && best_j != -1) {
            efficiency_stats_acc.checkpoint(best_cost);
            p.swap(best_i, best_j);
            best_cost += best_delta_in_neighborhood;
            improved = true;
        }

        iter++;
    }
    efficiency_stats_acc.finish(best_cost);
    auto[total_n_swaps, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    AlgorithmRunMetrics metrics = {best_cost, total_n_swaps, total_n_eval_solutions, rel_eff, norm_eff, total_time};
    if (verbose) print_finish_message(Colors::MAGENTA, "S", "Steepest LS", p, metrics, iter);
    return metrics;
}

// @brief Greedy local search algorithm for QAP.
//
// Explores the neighborhood of the current solution and moves to the first solution in the neighborhood that is better than the current solution. The neighborhood is defined as all permutations that can be obtained by swapping two elements in the current permutation. The algorithm stops when no improvement is found in the neighborhood or when a maximum number of iterations is reached.
//
//
// Sources of randomness: 
//
// 1) initial permutation `p` is randomized, 
//
// 2) the order of the neighborhood exploration is randomized by randomly selecting the first element to be swapped and then randomly selecting the second element to be swapped from the remaining elements. 
//     Then the first improving solution in the generated random neighborhood is selected as the new solution.
//
//
//
//
// @param problem       the QAP problem instance
// @param p             initial permutation. Will be modified in place, so it is passed by reference. Should be randomized or given as is before calling this function.
// @param run_config    configuration for the algorithm run, including `max_time_seconds` and `verbosity`.
AlgorithmRunMetrics greedy_local_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config) 
{ 
    const auto& [verbose, max_iterations, max_time_seconds, _] = run_config;
    const auto& [name, problem_size, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t delta, best_cost = cost_function(A, B, p);
    int improved_i, improved_j;
    int total_n_eval_solutions = 0;
    bool improved = true;
    StatisticsAccumulator efficiency_stats_acc(problem);

    int first_i, first_j;
    if (verbose) print_start_message(Colors::CYAN, "G", "Greedy LS", name, p, best_cost);

    int iter = 0;
    while (true) {
        if ((max_iterations > 0 && iter >= max_iterations) || !improved ||
            (max_time_seconds > 0 && algorithm_time_now() - efficiency_stats_acc.start_time >= max_time_seconds)) {
            break;
        }
        // exploring the neighborhood of the current solution by swapping each pair of elements in the permutation and calculating the cost change (delta) for each swap. If a swap results in a better solution (delta < 0), we perform the swap and update the best cost. We continue exploring the neighborhood until we have explored all pairs of elements or until we find an improvement. If we find an improvement, we set improved to true and continue to the next iteration of the local search. If we do not find any improvement after exploring the entire neighborhood, we set improved to false and exit the loop.
        improved = false;
        improved_i = -1; improved_j = -1;
        auto [first_i, first_j] = random::get_random_pair(problem_size); // get a random pair of indices to start the neighborhood exploration from, to ensure that the order of the neighborhood exploration is randomized in each iteration of the local search, which can help to escape local minima.
        for (int i = first_i; i < problem_size - 1 + first_i; i++) {
            for (int j = first_j; j < problem_size + first_j; j++) {
                delta = delta_cost(A, B, p, i % problem_size, j % problem_size);
                total_n_eval_solutions++; // partial evaluation of the solution
                if (verbose > 2) {
                    printf("G: Evaluating swap of elements at indices %d and %d in the permutation.\n", i % problem_size, j % problem_size);
                    printf("G: Cost change for this swap: %" PRId64 "\n", delta);
                }
                if (delta < 0) {
                    efficiency_stats_acc.checkpoint(best_cost);
                    p.swap(i % problem_size, j % problem_size);
                    best_cost += delta;
                    improved = true;
                    
                    goto next_iteration; // break out of both loops and accept the first improving solution found
                }
            }
        }
        next_iteration:;
        iter++;
    }
    efficiency_stats_acc.finish(best_cost);
    auto[total_n_swaps, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    AlgorithmRunMetrics metrics = {best_cost, total_n_swaps, total_n_eval_solutions, rel_eff, norm_eff, total_time};
    if (verbose) print_finish_message(Colors::CYAN, "G", "Greedy LS", p, metrics, iter);
    return metrics;
}


// Generates a series of random solutions and picks the best one among them. 
// Random solutions are generated by performing a number of random shuffling using the `reshuffle()` method of the `Permutation` class. Experiments show that setting `NUM_RESHUFFLE_CYCLES` (internal function constant) to 2 is beneficial for random properties of a newly generated solution.
// 
//Sources of randomness: 
//
// 1. initial permutation `p` is randomized
//
// 2. this permutation is reshuffled each iteration (Fisher-Yates algorithm, see `Permutation::reshuffle()` method), which generates a new random solution far from the current solution in the solution space.
//
// @param problem       the QAP problem instance
// @param p             initial permutation. Will be modified in place, so it is passed by reference. Should be randomized or given as is before calling this function.
// @param run_config    configuration for the algorithm run, including `max_time_seconds` and `verbosity`.
AlgorithmRunMetrics random_search_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config)
{
    const auto& [verbose, max_iterations, max_time_seconds, _] = run_config;
    const auto& [name, n, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t cost, best_cost = cost_function(A, B, p);

    Permutation<int> best_p = p;
    StatisticsAccumulator efficiency_stats_acc(problem);

    if (verbose) print_start_message(Colors::YELLOW, "RS", "Random Search", name, p, best_cost);
    
    int iter = 0;
    while (true) {
        if ((max_time_seconds > 0 && algorithm_time_now() - efficiency_stats_acc.start_time >= max_time_seconds) ||
            (max_iterations > 0 && iter >= max_iterations)) {
            break;
        }
        p.reshuffle(); // reshuffle the permutation by performing a series of random swaps to generate a new, seemingly absolutely random solution from `p`.
        cost = cost_function(A, B, p);
        if (cost<best_cost) {
            efficiency_stats_acc.checkpoint(best_cost);
            if (verbose > 2) {
                printf("RS: Iteration %d: Generated random permutation lower higher cost than current cost.\n", iter+1);
                p.print("New best solution: ");
                printf("Cost of new best solution: %" PRId64 "\n", cost_function(A, B, p));
            }
            best_p = p;
            best_cost = cost;
        }

        iter++;
    }
    efficiency_stats_acc.finish(best_cost);
    auto[ignored, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    p = best_p;
    // Number of evaluated solutions is number of iterations here; number of swaps is irrelevant
    AlgorithmRunMetrics metrics = {best_cost, -1, iter, rel_eff, norm_eff, total_time};
    if (verbose) print_finish_message(Colors::YELLOW, "RS", "Random Search", best_p, metrics, iter);
    return metrics;
}

// @brief Random walk algorithm for QAP.
//
// In each iteration, a random pair of indices is selected, and the elements at these indices in the permutation are swapped, which generates the next solution in the neighborhood of the current solution. If the new solution is better than the current solution, it becomes the new best solution. The algorithm stops when a maximum number of iterations is reached or when an optional time limit is reached.
//
//Sources of randomness: 
//
// 1. initial permutation `p` is to be randomized.
//
// 2. in each iteration, a random pair of indices is selected [from uniform distribution], and the elements at these indices in the permutation are swapped, which generates the next solution in the neighborhood of the current solution. 
//
// @param problem   the QAP problem instance
// @param p         initial permutation; should be randomized or given as is before calling this function.
// @param run_config      configuration for the algorithm run, including `max_time_seconds` and `verbosity`.
AlgorithmRunMetrics random_walk_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config)
{
    const auto& [verbose, max_iterations, max_time_seconds, _] = run_config;
    const auto& [name, n, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t delta, cost, best_cost = cost_function(A, B, p);
    cost = best_cost;
    
    Permutation<int> best_p = p;
    StatisticsAccumulator efficiency_stats_acc(problem);

    if (verbose) print_start_message(Colors::ORANGE, "RW", "Random Walk", name, p, best_cost);

    int iter = 0;
    while (!((max_time_seconds > 0 && algorithm_time_now() - efficiency_stats_acc.start_time >= max_time_seconds) ||
            (max_iterations > 0 && iter >= max_iterations))) 
    {

        auto [i, j] = random::get_random_pair(n); // get a random pair of indices to swap in the permutation
        delta = delta_cost(A, B, p, i, j); // calculate the cost change (delta) for swapping the elements at the randomly selected indices in the permutation
        cost += delta; // update the cost
        p.swap(i, j); // perform the swap in the permutation to generate a new solution in the neighborhood of the current solution
        // total number of swaps is the same as num of evaluated solutions here which is the same as number of iterations
        
        if (cost < best_cost) { // if the new solution is better than the current solution, update the best cost and continue to the next iteration of the random walk
            efficiency_stats_acc.checkpoint(best_cost);
            best_cost = cost;
            best_p = p;
        }
        if (verbose > 2) {
            printf("RW: Iteration %d: Swapped elements at indices %d and %d in the permutation.\n", iter+1, i, j);
            printf("RW: Cost change for this swap: %" PRId64 "\n", delta);
            printf("RW: Cost after this swap: %" PRId64 "\n", best_cost);
        }

        iter++;
    }


    efficiency_stats_acc.finish(best_cost);
    auto[ignored, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    p = best_p;
    AlgorithmRunMetrics metrics = {best_cost, iter, iter, rel_eff, norm_eff, total_time};
    if (verbose) print_finish_message(Colors::ORANGE, "RW", "Random Walk", best_p, metrics, iter);
    return metrics;
}

































/****************************************************************************************************************************/
/********************************* Part 2: Simulated Annealing and Tabu Search **********************************************/
/****************************************************************************************************************************/


// @brief Markov chain length `L` - number of iterations per temperature schedule step, calculated as |N(p)|*factor, where factor is given by from the `run_config.hyperparameters["markov_chain_length_factor"]` if any. Default value is not provided.
int eval_markov_chain_length(const Problem<int>& problem, const AlgorithmRunConfig& run_config)
{
    float     L_factor = static_cast<float>(run_config.hyperparameters.at("markov_chain_length_factor"));
    if (L_factor<=0)
        throw std::invalid_argument("Markov chain length factor must be greater than 0");
    auto n = problem.get_size();
    return int(round(L_factor* (n * (n - 1) / 2 ) ));
}


// @brief Maximum number of non-improving moves `f = run_cong.hyperparameters["max_non_improving_moves_factor"]` if any. Default is `0`, i.e. this stopping criteria will not be used.
//
// Set heuristically to `L * f`, where `L` is the length of Markow chain in Simulated Annealing, calculated by `eval_markov_chain_length(...)`.
int eval_max_non_improving_moves(const Problem<int>& problem, const AlgorithmRunConfig& run_config)
{
    if (run_config.hyperparameters.find("max_non_improving_moves_factor")!= run_config.hyperparameters.end() ){
        int M = run_config.hyperparameters.at("max_non_improving_moves_factor");
        if (M<0)
            throw std::invalid_argument("Simulated annealing requires valid for the corresponding stopping criterion to be used.");
        else if (M>0)
            return M*eval_markov_chain_length(problem, run_config);
        else if(M==0)
            std::printf("SA WARNINNG: Setting 'max_non_improving_moves_factor' to zero. This stopping criterion will not be used.");
    }
    return 0;
}

// @brief Estimates an average delta cost for deteriorating moves within a neighbourhood of the given initial solution. Number of evaluations is defined as sqrt(|N(init_solution)|)
template <typename T=double> T eval_avg_worse_delta (const Problem<int> &problem, Permutation<int> &init_solution)
{
    const auto&[A,B] = problem.get_matrices();
    int64_t cum_delta=0, delta = 0;
    auto n= problem.get_size();
    int num_evaluations = int(sqrt(n));

    for (int it =0; it<num_evaluations; it++){
        while (delta<=0){
            auto [i, j] = random::get_random_pair(n); // get a random pair of indices to swap in the permutation
            delta = delta_cost(A, B, init_solution, i, j);
        }
        cum_delta+=delta;
    }
    return static_cast<T>(cum_delta)/num_evaluations;
}

//@brief Evaluates [initial or final] temperature for the given `target_acceptance_rate` (set above 0.8) and estimated delta (of deteriorating moves)
// @param target_acceptance_rate defines the target probability of accepting a worsening move
template <typename T=double> inline T eval_temperature(T delta, T target_acceptance_rate=(T)0.95){
    return -delta/std::log(target_acceptance_rate);
}


// @brief Simulated annealing algorithm for QAP with geometric cooling schedule. 
//
// Uses geometric cooling schedule, where the temperature is updated geometrically as follows: T_{k+1} = `alpha` * T_k, where `0 < alpha < 1` is the cooling rate. 
// The algorithm accepts worse solutions with a probability that decreases as the temperature decreases, allowing it to escape local minima and explore the solution space more effectively. 
//
// The algorithm stops when running time exceeds the specified number of iterations (`max_iterations`), maximum amount of time (`max_time_seconds`) or recent rate of improvements falls below a threshold.
//
//
//Sources of randomness: 
//
// 1. initial permutation `p` is randomized
//
// 2. Hyperparameters such as `run_config.hyperparameters["initial_acceptance_rate"]` and `run_config.hyperparameters["final_acceptance_rate"]` define the target probabilities of accepting worsening moves at the beginning and cooling rate`alpha` used to modify the temperature at each schedule step, which affect the randomness of the search process.
//
// 3. Average delta cost for deteriorating moves is estimated at the beginning of the algorithm by sampling random swaps in the neighborhood of the initial solution, and this estimation is used to calculate the initial temperature based on the `run_config.hyperparameters["initial_acceptance_rate"]` hyperparameter, and temperature during the course of the algorithm. 
//
// 4. In each iteration, a random pair of indices is selected [from uniform distribution], and the elements at these indices in the permutation are swapped, if it improves the cost, or if it does not improve the cost but is accepted according to the Metropolis criterion.
//
// 5. Probability of accepting a worsening move (if one is obtained in step 3), which follows Boltzmann distribution
//
// 6. Running time (not number of iterations), which is used to determine number of cooling steps, and influences number of iterations of the algorithm. So, if the time budget is used as a stopping criterion, small fluctuations in running time can lead to slightly different number of iterations and schedule steps, which can affect the randomness of the search process and the results of the algorithm.
//
// The algorithm stops if one of these criteria is met: 
//
// - when running time exceeds the specified limit (`run_config.max_time_seconds`) (some fluctuation in actual number of iterations is possible)
//
// - number of iterations (`run_config.max_iterations`) is reached (some fluctuation in actual running time is possible)
//
// - recent rate of improvements falls below a threshold defined by `run_config.hyperparameters["final_acceptance_rate"]` hyperparameter AND no improvements condition was met (`run_config.hyperparameters["max_non_improving_moves_factor"]`).
//
// @param problem   the QAP problem instance
// @param p         initial permutation; should be randomized or given as is before calling this function.
// @param run_config      configuration for the algorithm run. Must include non-empty`hyperparameters` map with entries `"initial_acceptance_rate"`, `"final_acceptance_rate"` (typically 0.01), `"initial_cooling_rate"` and `"markov_chain_length_factor"` (1.0 by default) for the simulated annealing algorithm. 
// Also `max_time_seconds` or `max_iterations`, and, optionally, `verbosity` are to be provided.
template <typename Tprecision> 
    AlgorithmRunMetrics simulated_annealing_qap(
        const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config
)
{
    if (run_config.hyperparameters.find("initial_acceptance_rate")      == run_config.hyperparameters.end() ||
        run_config.hyperparameters.find("final_acceptance_rate")      == run_config.hyperparameters.end() ||
        run_config.hyperparameters.find("max_non_improving_moves_factor") == run_config.hyperparameters.end()||
        run_config.hyperparameters.find("initial_cooling_rate")                 == run_config.hyperparameters.end()  ||
        run_config.hyperparameters.find("markov_chain_length_factor")   == run_config.hyperparameters.end()) {
        throw std::invalid_argument("Simulated annealing requires 'initial_temperature_factor', 'cooling_rate', and 'markov_chain_length_factor' hyperparameters in the run configuration.");
    }

    const auto& [verbose, max_iterations, max_time_seconds, hyperparameters] = run_config;
    const auto& [name, n, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t delta, cost, best_cost = cost_function(A, B, p);
    cost = best_cost;
    
    Permutation<int> best_p = p;
    StatisticsAccumulator efficiency_stats_acc(problem);

    
    int iter=0, total_n_eval_solutions=0;

    auto avg_init_bad_delta =eval_avg_worse_delta<Tprecision>(problem, p);

    Tprecision  alpha = static_cast<Tprecision> (hyperparameters.at("initial_cooling_rate"));
    const Tprecision T0 = eval_temperature<Tprecision>(avg_init_bad_delta, hyperparameters.at("initial_acceptance_rate"));
    Tprecision temperature = T0;
    
    int L = eval_markov_chain_length(problem, run_config);

    // One of the stopping criteria: 
    int num_non_improving_moves=0, max_non_improving_moves= eval_max_non_improving_moves(problem, run_config);
    bool no_improvements=false;
    Tprecision prob_accept_deteriorating_move = std::exp(-avg_init_bad_delta/temperature);

    if (verbose) 
    {
        print_start_message(Colors::ORANGE, "SA", "Simulated Annealing", name, p, best_cost);
        printf("SA: Init temperature=%lf, L=%d\n", T0, L);
        printf("SA %s: Step %d it %d: Init acceptance rate of deteriorating moves: %f, with avg delta %lf and temperature %lf, L==%d.\n", problem.get_name().c_str(), iter/L, iter, prob_accept_deteriorating_move, avg_init_bad_delta, temperature, L);
    }    
    //if time budget is provided, number of steps will be determined based on the overall time budget `max_time_seconds` and recalculated average time per step `avg_time_per_step`
    long num_steps = static_cast<long>(std::max(2, max_iterations / L)); // "max_iterations" must be sufficiently high to have sufficiently many steps (num_steps)! 
    double avg_time_per_step=0; // recalculated every schedule step and is used to determine `num_steps` on the go
    const Tprecision  acceptance_rate_target_decrease = static_cast<Tprecision> (hyperparameters.at("initial_acceptance_rate")/hyperparameters.at("final_acceptance_rate"));

    // Main loop
    while (!((max_time_seconds > 0 && algorithm_time_now() - efficiency_stats_acc.start_time >= max_time_seconds) ||
            (max_iterations > 0 && iter >= max_iterations) ||
            (max_non_improving_moves>0 && no_improvements && prob_accept_deteriorating_move<hyperparameters.at("final_acceptance_rate") )
        )) 
    {
        auto pr = random::get_random_pair(n); // get a random pair of indices to swap in the permutation
        int i = pr.first;
        int j = pr.second;
        delta = delta_cost(A, B, p, i, j); // calculate the cost change (delta) for swapping the elements at the randomly selected indices in the permutation
        total_n_eval_solutions++;

        //              Metropolis criterion
        if (delta <= 0 || random::get_random_01f() < std::exp(- static_cast<Tprecision>(delta) / temperature)) {
            p.swap(i, j); // perform the swap in the permutation to generate a new solution in the neighborhood of the current solution
            cost += delta; // update the cost
            efficiency_stats_acc.checkpoint(best_cost); // increase number of swaps

            if (delta<=0)
                num_non_improving_moves =0;
                // moving_avg_bad_delta=0;
            else
                num_non_improving_moves ++;
                //if num_non_improving_moves==1: first_moving_bad_delta=delta
                //if num_non_improving_moves>max_non_improving_moves: moving_avg_bad_delta = (max_non_improving_moves*moving_avg_bad_delta-first_moving_bad_delta+delta)/moving_avg_bad_delta;
                
            if (cost < best_cost) { // if the new solution is better than the current solution, update the best cost and continue to the next iteration of the random walk
                best_cost = cost;
                best_p = p;
            }

            if (verbose > 2) {
                printf("SA: Step %d it %d: Swapped elements at indices %d and %d in the permutation.\n", iter/L, iter+1, i, j);
                printf("SA: Cost change for this swap: %" PRId64 "\n", delta);
                printf("SA: Cost after this swap: %" PRId64 "\n", best_cost);
            }
        }

        iter++;
        if (iter % L == 0){
            // Recalculating number of steps 
            if (max_iterations==0)
            {    
                avg_time_per_step = algorithm_time_now() - efficiency_stats_acc.start_time;
                if (iter/L>0) 
                    avg_time_per_step/=(iter/L+1); // recalc average
                num_steps = std::max(2l, lround(max_time_seconds/avg_time_per_step)); 
            }

            alpha = pow(avg_init_bad_delta/(T0*log(acceptance_rate_target_decrease) + avg_init_bad_delta ), (Tprecision) 1.0/  ( num_steps-1)); //num_steps - 1 since one step is spent with alpha=hyperparameters.at('initial_cooling_rate')
            temperature *= alpha; // update the temperature according to the geometric cooling schedule
        }

        no_improvements =(num_non_improving_moves>max_non_improving_moves);
        prob_accept_deteriorating_move = exp(-avg_init_bad_delta/temperature);
        if (no_improvements&&verbose || verbose>2)
            printf("SA %s: Step %d it %d: Acceptance rate of deteriorating moves: %f.\n Number of non-improving moves: %d", problem.get_name().c_str(), iter/L, iter, prob_accept_deteriorating_move,num_non_improving_moves);
    }


    efficiency_stats_acc.finish(best_cost);
    auto[_, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    p = best_p;
    AlgorithmRunMetrics metrics = {best_cost, iter, iter, rel_eff, norm_eff, total_time};
    if (verbose)  print_finish_message(Colors::ORANGE, "SA", "Simulated Annealing", best_p, metrics, iter);
    if (verbose)  printf("SA %s: Step %d it %d: Final acceptance rate of deteriorating moves: %f, with avg delta %lf and temperature %lf, L==%d, last alpha ==%f.\n", problem.get_name().c_str(), iter/L, iter, prob_accept_deteriorating_move, avg_init_bad_delta, temperature, L, alpha);

    return metrics;
}








// @brief Simulated annealing algorithm for QAP with adaptive cooling schedule based on Lam schedule.
//
// Uses adaptive cooling schedule, where the temperature is updated based on the rate of improvements in the recent history of the search. 
// The algorithm accepts worse solutions with a probability that decreases as the temperature decreases, allowing it to escape local minima and explore the solution space more effectively. 
//
//Sources of randomness: 
//
// 1. initial permutation `p` is randomized
//
// 2. Hyperparameter `run_config.hyperparameters["initial_acceptance_rate"]` define initial probability of accepting worsening moves at the beginning.
//
// 3. Average delta cost for deteriorating moves is estimated at the beginning of the algorithm by sampling random swaps in the neighborhood of the initial solution, and this estimation is used to calculate the temperature used to define probability of accepting worsening moves during the course of the algorithm.
//
// 4. In each iteration, a random pair of indices is selected [from uniform distribution], and the elements at these indices in the permutation are swapped, if it improves the cost, or if it does not improve the cost but is accepted according to the Metropolis criterion.
//
// 5. Probability of accepting a worsening move (if one is obtained in step 4), which follows Boltzmann distribution
//
// 6. Running time (not number of iterations), which is used to determine number of cooling steps in Lam schedule (see `GetLamTargetProbability`), and influences number of iterations of the algorithm. So, if the time budget is used as a stopping criterion, small fluctuations in running time can lead to slightly different number of iterations and schedule steps (likely will be absorbed by integer rounding in this case), which can affect the randomness of the search process and the results of the algorithm. 
//
// The algorithm stops if one of these criteria is met: 
//
// - when running time exceeds the specified limit (`run_config.max_time_seconds`) (and no limit for number of iterations) (some fluctuation in actual running is possible)
//
// - number of iterations (`run_config.max_iterations`) is reached  (if provided) (some fluctuation in actual number of iterations is possible)
// @param problem   the QAP problem instance
// @param p         initial permutation; should be randomized or given as is before calling this function.
// @param run_config      configuration for the algorithm run. Must include non-empty`hyperparameters` map with entries `"initial_temperature_factor"` and `"cooling_rate"` for the simulated annealing algorithm, in addition to `max_time_seconds` and `verbosity`.
AlgorithmRunMetrics adaptive_simulated_annealing_qap(const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config) 
{
    if (run_config.hyperparameters.find("initial_acceptance_rate")      == run_config.hyperparameters.end() ||
        run_config.hyperparameters.find("markov_chain_length_factor") == run_config.hyperparameters.end()) {
        throw std::invalid_argument("Simulated annealing requires 'initial_temperature_factor' and 'markov_chain_length_factor' hyperparameters in the run configuration.");
    }

    const auto& [verbose, max_iterations, max_time_seconds, hyperparameters] = run_config;
    const auto& [name, n, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t delta, cost, best_cost = cost_function(A, B, p);
    cost = best_cost;
    
    Permutation<int> best_p = p;
    StatisticsAccumulator efficiency_stats_acc(problem);

    if (verbose) print_start_message(Colors::YELLOW, "LAMSA", "Simulated Annealing", name, p, best_cost);

    int iter=0, total_n_eval_solutions=0;

    // arbitrary initial temperature, will be adjusted (down or up) in the loop below. 
    //If you have already implemented any method that adjusts initial T based on the ruggedness of the landscape (like we discussed during the lecture and labs), use it here instead of 1.0!
    double temperature = eval_temperature(eval_avg_worse_delta(problem, p), 
                                            hyperparameters.at("initial_acceptance_rate"));

    // Num of iterations per schedule step.
    // During a step, T remains constant, and we measure the ratio of accepted deteriorating moves. If you set ITERATIONS_PER_STEP too low, you will get too much noise in the measured ratio. ITERATIONS_PER_STEP too high will result in reliable ratio, but slow responsiveness in adjusting T. 100 is typically a good tradeoff; you can try 50 for a more responsive temperature adjustment.
    int L = eval_markov_chain_length(problem, run_config);
    if (verbose) printf("LAMSA: Init temperature=%lf, L=%d", temperature, L);

    // how it works: we keep temperature constant during a "step" which lasts ITERATIONS_PER_STEP iterations.
    // after a "step" competes, we adjust temperature (down or up) based on the acceptance rate of deteriorating moves we have calculated during last "step". 
    
    //if time budget is provided, number of steps will be determined based on the overall time budget `max_time_seconds` and recalculated average time per step `avg_time_per_step`
    int num_steps = std::max(2, int(max_iterations / L)); // "max_iterations" must be sufficiently high to have sufficiently many steps (num_steps)! usually we need 1000 steps, or 10000, or more... max_iterations = ITERATIONS_PER_STEP * num_steps;
    double avg_time_per_step=0; // recalculated every schedule step and is used to determine `num_steps` on the go

    int accepted_bad_moves, total_bad_moves;
    float progress, P_target, P_current, error;

    for (int step=0; step<num_steps; step++) // T is constant during a single step
    {
        accepted_bad_moves = 0;
        total_bad_moves = 0;
        progress = step / (num_steps-1); // from 0.0 to 1.0
        P_target = GetLamTargetProbability(progress);
        if (P_target <= 0.001) // last phase of SA: become strictly greedy
            temperature = 0.0;

        for (int it=0; it<L; it++, iter ++) // one step (constant temperature level) of standard SA
        { 			
            //neighbor = GenerateNeighbor(current_solution);
            //delta_f = Objective(neighbor) - Objective(current_solution);
            auto [i, j] = random::get_random_pair(n); // get a random pair of indices to swap in the permutation
            delta = delta_cost(A, B, p, i, j); // calculate the cost change (delta) for swapping the elements at the randomly selected indices in the permutation
            total_n_eval_solutions++;
            if (delta <= 0){ // improving move, always accept [why not accept improvements probabilistically? an improvement can be absolutely insignificant, while the remaining neighbours could give better improvements]
                //current_solution = neighbor;
                p.swap(i, j); 
                cost += delta; // update the cost
                efficiency_stats_acc.checkpoint(best_cost); // increase number of swaps

                if (cost < best_cost) { // if the new solution is better than the current solution, update the best cost and continue to the next iteration of the random walk
                    best_cost = cost;
                    best_p = p;
                }
            }
            else{ // deteriorating move
                total_bad_moves++;
                if (random::get_random_01f() < exp(-delta/temperature)){
                    p.swap(i, j); 
                    cost += delta; 
                    efficiency_stats_acc.checkpoint(best_cost); // increase number of swaps
                    accepted_bad_moves++;
                }
            }
        }


        if (temperature > 0) // only adjust T (for the next step) if we are not in the final, strictly greedy phase (T=0)
        {
            if (total_bad_moves == 0) // wow, accepted all moves during the recent step: free-falling down a steep gradient?
                temperature*= 1.5; // bump up temperature to escape (we want thermal equilibrium!), the multiplier can be e.g. 1.2 .. 2.0
            else{
                P_current = accepted_bad_moves / total_bad_moves; // the actual acceptance rate of deteriorating moves during the recent ste
                error = P_target - P_current;
                // use a dynamic multiplier based on how big the error is (a proportional controller).
                // if error is large positive (we are rejecting too much and need more acceptances), T goes up - and vice versa.
                //adjustment_factor: 0.5 can be adjusted: 0.1 -> slower changes of T, 1.0 -> may cause more violent oscillations
                temperature *= 1.0 + (error * 0.5); // adjust T (down or up!) to make P_current approach P_target
            }
        }


        // Recalculating number of steps 
        if (max_iterations==0)
        {    
            avg_time_per_step = algorithm_time_now() - efficiency_stats_acc.start_time;
            if (step>0) 
                avg_time_per_step/=(step+1); // recalc average
            num_steps = std::max(2.0, round(max_time_seconds/avg_time_per_step)); 
        }
    }

    efficiency_stats_acc.finish(best_cost);
    auto[_, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    p = best_p; // this is a permutation, not a probability, as in the code of all the other algorithms above
    AlgorithmRunMetrics metrics = {best_cost, iter, iter, rel_eff, norm_eff, total_time};
    if (verbose) 
    {
        print_finish_message(Colors::YELLOW, "LAMSA", "Simulated Annealing", best_p, metrics, iter);
        printf("LAMSA: Step %d it %d: Final acceptance rate of deteriorating moves: %lf and temperature %lf\n", iter/L, iter, P_current, temperature);
    }
    return metrics;
}

// use the magical "Lam Curve" for target acceptance probability; "progress" is from 0.0 (start) to 1.0 (end)
// @return probability of acceptance of a bad solution
float GetLamTargetProbability(float progress)
{
    if (progress < 0.15) // first 15% of iterations: fast drop from 1.0 to 0.44
        return 1.0 - (progress / 0.15) * (1.0 - 0.44);
    else if (progress < 0.65) // next 50% of time: the "plateau"
        return 0.44; // stay at probability of 0.44, for efficient optimization
    else{ // progress in range from 0.65 to 1.0
        //remaining_progress = (progress - 0.65) / 0.35; // normalize remaining iterations
        return 0.44 * (1.0 - (progress - 0.65) / 0.35); // final 35%: quick cooling down to 0.0 
    }
}



/********************************************************* Tabu search ************************************************************************/


// @brief Evaluates the lifespan of the elite candidate list, i.e. number of iterations for which the list is kept unchanged before being rebuilt.
//
// Calculated heuristically as `f * min(ceil(problem.get_skewness()), pow(problem.size(), 2.0/3.0))`, where factor `f` is given by from the `run_config.hyperparameters["elite_candidate_list_lenghth_factor"]` if any, or assumed to be 1. Default value is 1.
// @note The rationale behind this heuristic is as follows: the lifespan of the elite candidate list can be long enough if one of the matrices demonstrates high skewness, meaning that remaining good moves in the list don't deteriorate fast, as it is in the case of low skewness in the matrices with almost uniform distribution of values - in such cases it's recommended to reevaluate elite candidates frequently. 
//
// @note Lifespan of the elite candidate list is the hyperparameter that is specific to the tabu search algorithm, and it defines how many iterations we keep the elite candidate list unchanged before rebuilding it. If the list is rebuilt too often, we will spend too much time on rebuilding and not enough time on exploring the solution space. If the list is rebuilt too rarely, we may miss out on good candidate moves that could be added to the list. So, it is important to find a good balance between these two extremes.
int eval_elite_candidate_list_lifespan(const Problem<int>& problem, const AlgorithmRunConfig& run_config)
{
    double f = 1.0;
    if (run_config.hyperparameters.find("elite_candidate_list_lifespan_factor")!= run_config.hyperparameters.end() ){
        f = run_config.hyperparameters.at("elite_candidate_list_lifespan_factor");
        if (f<=0) throw std::invalid_argument("Elite candidate list lifespan factor must be positive.");
    }
    else 
        std::printf("Tabu Search Warning: 'elite_candidate_list_lifespan_factor' hyperparameter not found. Setting it to default value of %f.\n", f);
    
    double upper_limit = std::pow(problem.get_size(), 2.0/3.0);
    int lower_limit = 1;
    return std::max(lower_limit, int(f* std::min(upper_limit, std::ceil(std::abs(problem.get_skewness())))));
}

// @brief Evaluates the elite candidate list size, i.e. number of candidate moves in the elite candidate list.
//
// Heuristically set to `f * elite_candidate_list_lifespan`, where `f=2` and `elite_candidate_list_lifespan` is a number of steps elite candidate list is considered to be valid, and the factor of 2 is used to have a sufficiently large pool of candidates to choose from.
//
//
// If `run_config.hyperparameters["elite_candidate_list_size_factor"]` is provided, then `f` is set to this value.
// @note Size of the list is the hyperparameter that is specific to the tabu search algorithm, and it defines how many candidate moves we keep in the elite candidate list. If the list is too long, we will spend too much time on evaluating and maintaining it, and if it is too short, we may miss out on good candidate moves that could be added to the list. So, it is important to find a good balance between these two extremes.
int eval_elite_candidate_list_size(int elite_candidate_list_lifespan, const Problem<int>& problem, const AlgorithmRunConfig& run_config)
{
    double f = 2.0;
    if (run_config.hyperparameters.find("elite_candidate_list_size_factor")!= run_config.hyperparameters.end() ){
        f = run_config.hyperparameters.at("elite_candidate_list_size_factor");
        if (f<=1) throw std::invalid_argument("Elite candidate list size factor must begreater than 1.");
    }
    else 
        std::printf("Tabu Search Warning: 'elite_candidate_list_size_factor' hyperparameter not found. Setting it to default value of %f.\n", f);
    return int(f* elite_candidate_list_lifespan);
}

// @brief Evaluates the tabu tenure, i.e. number of iterations for which a move is considered tabu after being added to the tabu list.
//
// Heuristically set to `sqrt(problem.get_size())*f`, where factor `f` is given by from the `run_config.hyperparameters["tabu_tenure_factor"]`. By default `f=
// @note Tabu tenure is the hyperparameter that is specific to the tabu search algorithm, and it defines how many iterations we consider a move to be tabu after it has been added to the tabu list. If the tenure is too short, we may allow moves that lead to cycling back to recently visited solutions, and if it is too long, we may miss out on good candidate moves that could be added to the list. So, it is important to find a good balance between these two extremes.
int eval_tabu_tenure(const Problem<int>& problem, const AlgorithmRunConfig& run_config)
{   
    double f = 1.0;
    if (run_config.hyperparameters.find("tabu_tenure_factor")== run_config.hyperparameters.end() ){
        throw std::invalid_argument("Tabu Search Warning: 'tabu_tenure_factor' hyperparameter not found.");
    }
    else{    
        f = run_config.hyperparameters.at("tabu_tenure_factor");
        if (f<=0) throw std::invalid_argument("Tabu tenure factor must be positive.");
        return int(sqrt(problem.get_size())*f);
    }
}

//Wrapper for a std::multimap objects which keeps fixed amount of entries with the lowest keys (delta costs)
template<typename Key, typename Value>
class FixedSizeMinMap {
private:
    std::multimap<Key, Value> map;
    size_t max_size;

public:
    FixedSizeMinMap(size_t max_size) : max_size(max_size) {}

    // @return iterators to the beginning of the map (the entry with the lowest key, i.e. the best candidate move)
    auto begin() { return map.begin(); }
    // @return iterator to the end of the map (one past the entry with the highest key, i.e. the worst candidate move)
    auto end() { return map.end(); }

    auto begin() const { return map.begin(); }
    auto end() const  { return map.end(); }

    // Inserts a new key-value pair into the map. If the map exceeds the maximum size, the entry with the highest key (worst delta cost) is removed.
    // @note Complexity: O(1) for finding the worst entry, O(1) for removing the worst entry, and O(log(max_size)) for inserting the new entry, where max_size is the maximum size of the map. So, overall complexity is O(log(max_size)).
    void insert(const Key& key, const Value& value) {
        if (map.size() < max_size) 
            map.insert({key, value});
        else {
            auto worst_it = map.rbegin(); // Get the iterator to the entry with the highest key (worst delta cost)
            auto worst_key = worst_it->first;
            if (key<worst_key){
                map.erase(std::prev(map.end())); // Remove the entry with the highest key (used prev(end) since `map::erase` accepts only forward iters)
                map.insert({key, value});
            }
        }
    }

    void clear() {
        map.clear();
    }

    // Removes the entry with the lowest key (best delta cost) from the map.
    auto pop_front() {
        return map.erase(map.begin());
    }

    // Removes the entry at the specified index from the map. If the index is out of bounds, no action is taken.
    auto erase(typename std::multimap<Key, Value>::iterator it) {
        return map.erase(it);
    }

    const std::multimap<Key, Value>& get_map() const {
        return map;
    }

    bool empty() const { return map.empty();}
};


#define HASH(nbits, i, j) (((i) <= (j)) ? (((i) << (nbits)) | (j)) : (((j) << (nbits)) | (i)))

// @brief Tabu search algorithm for QAP with adaptive elite candidate tracking.
//
// This implementation employs two distinct memory layers: short-term memory modeled by an adaptive elite candidate list, and mid-term memory modeled by a tabu list. 
//
// The algorithm operates via two nested loops.  At each "step" of the outer loop, a fresh elite candidate list is generated based on the current solution (permutation `p`) and stored in a automatically sorted container (wrapping `std::multimap`).
//
// The inner loop sequentially evaluates these candidates. If the top candidate is non-tabu, tabu-expired, or satisfies the aspiration criterion (i.e., strictly improves upon the best cost achieved so far), 
//      it is executed, placed to the tabu list and dropped from the elite candidate list.
// Otherwise, the next elite candidate move is evaluated in the same fashion.
//
// [OPTIONAL mechanics]: If the actual delta of an elite move drifts too far from the stale delta calculated  when the list was formed (e.g., exceeding a configured relative threshold), the elite list will immediately  be invalidated and reconstructed.
//
// Although this algorithm is fully deterministic, there are a few sources of randomness:
//
// - The initial permutation `p` is randomized prior to invocation.
//
// - Running time (not the number of iterations) is used to determine the total number of "steps" when operating on a time budget, though small micro-fluctuations in running time are heavily absorbed by integer rounding.
//
// The algorithm terminates gracefully if any of the following criteria are met:
//
// - The total elapsed execution time exceeds the specified limit (`run_config.max_time_seconds`).
//
// - The total number of algorithm iterations reaches the specified limit (`run_config.max_iterations`).
//
// - Stagnation is detected: The global best solution fails to improve for a consecutive number of iterations, defined heuristically as `N * run_config.hyperparameters["max_non_improving_moves_factor"]`, where `N = problem.get_size()`.
//
// @param problem      The QAP problem instance.
// @param p            Initial permutation; should be randomized or given as-is before calling this function.
// @param run_config   Configuration for the algorithm run. Must include a non-empty `hyperparameters` map with entries:
//
//   - `"elite_candidate_list_lifespan_factor"`: Defines the factor `fl` used in the heuristic calculation of the elite list lifespan `L` (how many iterations the list is assumed valid). `L` scales proportionally with the problem skewness and is hard-capped by N^(2/3). Default value is 1.0.
//
//   - `"elite_candidate_list_size_factor"`: Defines the factor `fs` used to determine the total size of the elite list, scaled proportionally to the lifespan: `fs * L`. Default value is 2.0.
// 
//   - `"tabu_tenure_factor"`: Defines the factor `ft` used in the heuristic calculation of the tabu tenure (the number of iterations an accepted move's inverse is banned), set as: `ft * sqrt(problem.get_size())`. Default value is 1.0.
//
//   - `"delta_drift_relative_threshold"`: [Optional] Defines how far an actual delta cost can drift from its stale estimate (computed when the elite list was formed) before forcing an early list rebuild. Set to 0.0 (default) to disable this check.
// 
//   - `"max_non_improving_moves_factor"`: Used in the stopping criteria to define the multiplier for the maximum consecutive swaps allowed without a global cost improvement. Recommended value is 2.0.
//
// - Additionally, the configuration must explicitly specify `max_time_seconds` or `max_iterations`, and optionally, `verbosity`.
AlgorithmRunMetrics tabu_search_qap(
        const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& run_config
)
{
    const auto TS_COLOR =Colors::YELLOW;

    if (run_config.hyperparameters.find("elite_candidate_list_size_factor")      == run_config.hyperparameters.end() ||
        run_config.hyperparameters.find("elite_candidate_list_lifespan_factor") == run_config.hyperparameters.end() ||
        run_config.hyperparameters.find("tabu_tenure_factor")                   == run_config.hyperparameters.end() ||
        run_config.hyperparameters.find("max_non_improving_moves_factor")       == run_config.hyperparameters.end()

    ) {
        throw std::invalid_argument("Tabu search requires 'elite_candidate_list_lifespan_factor', 'elite_candidate_list_size_factor', 'tabu_tenure_factor' and 'max_non_improving_moves_factor' hyperparameters in the run configuration.");
    }

    const auto& [verbose, max_iterations, max_time_seconds, hyperparameters] = run_config;
    const auto& [name, problem_size, matrices, best_permutation, known_best_cost] = problem.get_attributes();
    const auto&[A, B] = matrices;

    std::int64_t delta, cost, best_cost = cost_function(A, B, p);
    cost = best_cost;
    
    Permutation<int> best_p = p;
    StatisticsAccumulator efficiency_stats_acc(problem);

    if (verbose>=1) print_start_message(TS_COLOR, "TS", "Tabu Search", name, p, best_cost);

    int iter=0, total_n_eval_solutions=0;

    // Hyperparameters:
    // Number of iterations per elite candidate list                                        
    int L = eval_elite_candidate_list_lifespan(problem, run_config);
    int elite_candidate_list_size = eval_elite_candidate_list_size(L, problem, run_config);
    int tabu_tenure = eval_tabu_tenure(problem, run_config); // number of iterations for which a move is considered tabu after being made. 
    //float tabu_tenure_factor = hyperparameters.at("tabu_tenure_factor");
    auto delta_drift_relative_threshold = (run_config.hyperparameters.find("delta_drift_relative_threshold")!= run_config.hyperparameters.end()? 
                                            static_cast<float> (run_config.hyperparameters.at("delta_drift_relative_threshold")) : 0.0);

    if (verbose>=0.5) printf("%sTS%s::NOTE: the following hyperparameters are set for problem %s: elite candidates list lifespan=%d and size=%d, tabu tenure=%d, delta_drift_relative_threshold=%f", 
        TS_COLOR, Colors::RESET, name.c_str(), L, elite_candidate_list_size, tabu_tenure, delta_drift_relative_threshold);

    //if time budget is provided, number of steps will be determined based on the overall time budget `max_time_seconds` and recalculated average time per step `avg_time_per_step`
    int num_steps = std::max(2, int(max_iterations / L)); // "max_iterations" must be sufficiently high to have sufficiently many steps (num_steps)
    double avg_time_per_step=0; // recalculated every L steps and is used to determine `num_steps` on the go

    // std::map automatically sorts entries by their keys (delta cost), whlie multimap also allows duplicate keys
    // internal structure of map is binary tree
    FixedSizeMinMap<int64_t, std::pair<int, int>> 
        elite_candidate_moves(elite_candidate_list_size); // list of candidate moves (swaps) with the lowest total delta cost, which we will be using during the next L iterations (steps) of the tabu search. We keep track of these candidates and their deltas for the next L iterations, and we update this list every L iterations. 
    std::unordered_map<int, int> 
        tabu_list; // tabu list to keep track of recently made moves (swaps) and their tabu tenure (number of iterations for which they are considered tabu).
    // tabu list should map Hash(i,j) -> tabu tenure (i, j)
    int nbits = (problem_size > 1) ? static_cast<int>(std::ceil(std::log2(problem_size))) : 1; // number of bits needed to represent the indices of the permutation, used for hashing moves in the tabu list

    // One of the stopping criteria: 
    int num_globally_non_improving_moves=0, max_non_improving_moves= problem_size* run_config.hyperparameters.at("max_non_improving_moves_factor") ;
    

    // each step is a sequence of L iterations over elite candidate moves, where we keep track of the best move in the neighborhood (the one with the lowest delta cost) and accept it if it is not tabu, or if it is tabu but leads to a solution better than the best known solution (aspiration criterion), or if its tabu tenure has expired. After each step, we update the elite candidate list and tabu list for the next step. We also recalculate number of steps based on the time budget and average time per step.
    for (int step=0; step<num_steps; step++) // T is constant during a single step
    {
        // Scanning the neighbourhood of the current solution and forming the elite candidate list for the next L iterations.
        for (int i = 0; i < problem_size - 1 ; i++){
            for (int j = i+1; j < problem_size; j++) {
                delta = delta_cost(A, B, p, i, j); 
                // add the candidate move (swap) and its delta cost to the list of elite candidates
                elite_candidate_moves.insert(delta, {i, j}); // if 2 moves has the same delta, their order in this container is  determined, not random.
            }
        }
        total_n_eval_solutions+=problem_size*(problem_size-1)/2;

        auto it = elite_candidate_moves.begin();
        int local_iter=0;
        while (local_iter < L && !elite_candidate_moves.empty() && it != elite_candidate_moves.end()) 
        {
            // best_move_in_neighborhood = *elite_candidate_moves.begin(); 
            // the best move in the neighborhood is the one with the lowest delta cost, which is the first entry in the map
            // if this move (`it-> second`) cannot be executed (tabu or no aspiration), then it ++
            auto [stale_delta, move] = *it;
            auto [i, j] = move;
            int move_key = HASH(nbits, i, j);
            //if (verbose) std::cout <<TS_COLOR<<"\nTS:"<<Colors::RESET<<" NOTE: hash of the move ("<<i<<", "<<j<<") =="<<move_key;
            auto tabu_it = tabu_list.find(move_key);
            auto updated_delta = delta_cost(A, B, p, i, j); 


            // This section was actually not triggered,
            // OPTIONAL: QUALITY THRESHOLD FILTER: Reject if intermediate swaps corrupted this elite move
            if (delta_drift_relative_threshold >0 && updated_delta - stale_delta>delta_drift_relative_threshold* abs(stale_delta) ) {
                if (verbose>=2) printf("%sTS%s:: NOTE: Quality of the elite candidate degraded more than %f. The elite candidate list will be recreated.", TS_COLOR, Colors::RESET, delta_drift_relative_threshold);
                elite_candidate_moves.erase(it);
                it = elite_candidate_moves.begin();
                continue;
            }

            // if the move (the best currently available in the elite list):
            // is EITHER not tabu, 
            //OR if it is tabu but leads to a solution better than the best known solution (aspiration criterion), 
            //OR tabu tenure has expired, we can consider this move for execution
            if (tabu_it == tabu_list.end() || cost + updated_delta < best_cost || iter >= tabu_it->second) {
                cost += updated_delta;// update the cost
                p.swap(i, j); 
                efficiency_stats_acc.checkpoint(best_cost); // increase number of swaps

                // Aspiration criterion: if the new solution is better than the current best solution found so far, we accept it even if the move is tabu, and update the best cost and best solution accordingly.
                if (cost < best_cost) { 
                    best_cost = cost;
                    best_p = p;
                    num_globally_non_improving_moves = 0;
                }
                else num_globally_non_improving_moves++;

                // add the move to the tabu list with its [clock stamp +] tabu tenure/update tabu status
                // tabu satus will expire once `iter>=tabu_tenure`
                tabu_list[move_key] = iter + tabu_tenure; 

                /*Thus we don't have to manually delete a move from tabu list as in the lines below:*/
                // // If tabu tenure has expired, we need to remove this move
                // // if it was not performed
                // auto cur_it = tabu_list.find(move_key);
                // if (cur_it != tabu_list.end() && iter >= cur_it->second) 
                //     tabu_list.erase(cur_it);// remove the move from the tabu list if its tenure has expired

                //// if (updated_delta > 0) 
                ////     accepted_bad_moves++;

                // Safely erase the executed move
                elite_candidate_moves.erase(it);

                // Increment both clock and lifespan ONLY when a move physically occurs
                local_iter++;
                iter++;



                // EARLY TERMINATION TRIGGER: Stagnation limit reached
                if (num_globally_non_improving_moves >= max_non_improving_moves) {
                    if (verbose>1.5) {
                        std::printf("%sTS%s:: NOTE: Stagnation limit hit. No improvements for %d iterations. Exiting early.\n", TS_COLOR, Colors::RESET, num_globally_non_improving_moves);
                    }
                    // Force the loops to break out elegantly
                    step = num_steps; // Forces outer loop termination on next iteration sequence
                    break;            // Breaks current while loop immediately
                }

                // Reset back to the fresh absolute best option at the front
                it = elite_candidate_moves.begin();
            }
            else
            {
                if (elite_candidate_moves.empty() && local_iter < L)
                    if (verbose>=2) std::printf("%sTS%s:: NOTE: Neighborhood exhausted early at step %d. Consider diversifying...\n", TS_COLOR, Colors::RESET, step);
                it ++;
            }
        }


        // if (accepted_bad_moves > 5) 
        //    tabu_tenure *= run_config.hyperparameters["tabu_tenure_factor"];
        
        // Clear the elite candidate list and tabu list for the next step
        elite_candidate_moves.clear();

        // tabu list is not cleared, as it operates independently from the elite candidates list, as both represent different aspects of the memory

        // Recalculating number of steps 
        if (max_iterations==0)
        {    
            avg_time_per_step = algorithm_time_now() - efficiency_stats_acc.start_time;
            if (step>0) 
                avg_time_per_step/=(step+1); // recalc average
            num_steps = std::max(2.0, round(max_time_seconds/avg_time_per_step)); 
        }
    }

    efficiency_stats_acc.finish(best_cost);
    auto[_, rel_eff, norm_eff, total_time] = efficiency_stats_acc.get_metrics();
    p = best_p; // this is a permutation, not a probability, as in the code of all the other algorithms above
    AlgorithmRunMetrics metrics = {best_cost, iter, total_n_eval_solutions, rel_eff, norm_eff, total_time};
    if (verbose>=1) 
    {
        print_finish_message(Colors::YELLOW, "TS", "Tabu Search", best_p, metrics, iter);
    }
    return metrics;
}






