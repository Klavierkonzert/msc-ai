// statistics.cpp
// Functions for gathering statistics on the performance of the algorithms
//
// sort problems by size



#include <functional>
#include <vector>
#include <tuple>
#include <map>
#include <set>
#include <string>
#include <algorithm>
#include <cstdint>
#include <ctime>
#include <numeric>
#include <functional>


#include <vector>
#include <algorithm>
#include <numeric>
#include <cmath>



#include <omp.h> // used in `get_problems_runs_statistics` for run-major parallelization across runs and problems

#include "permutation.cpp"
#include "dataloaders.cpp"
#include "algorithms.cpp"
#include "quality.cpp"

#include "matplotlibcpp.h" // Path ${env:USERPROFILE}\source\repos should be added to the include directories in the project properties
namespace plt = matplotlibcpp;






// Structure of function calls:
//
// Aggregating statistics for multiple runs of a method on multiple problem instances:
// `ExperimentResults` container <- 
//   `get_methods_problems_runs_statistics`:
//      for each method:
//          call `get_problems_runs_statistics` - aggregates statistics for multiple problems and runs of the method:
//              *if OpenMP is available and n_runs > 1, run in parallel across runs and problems, otherwise run sequentially
//                  ::in parallel:: (OpenMP)
//                      for each run:
//                          for each problem:
//                              call `get_statistics`:
//                                  costs, qualities, distances from best known solution, time taken for the run of the `method`
//              *else ::sequentially: (no OpenMP or n_runs <= 1)
//                  for each problem:
//                      call `get_runs_statistics`:
//                          for each run:
//                              call `get_statistics`:
//                                  costs, qualities, distances from best known solution, time taken for the run of the `method`
//
// Rearranging for plotting:
// `get_methods_statistics_for_plotting_by_problem`:
//      for each method:
//          call `get_statistics_for_plotting_by_problem`:
//              for each problem:
//                  rearrange statistics for plotting -> (statistic_name: [values for each run of the method on the problem instance])
//
// Plotting functions:
// `plotting::methods_boxplot` <- `get_methods_statistics_for_plotting_by_problem(...)`:
//      `sort_problems` (e.g. by size or difficulty)
//      for each problem:
//          for each method:
//              box figure <- get values for the statistic to be plotted for the method and problem instance
//
// `plotting::boxplot`         <- `get_statistics_for_plotting_by_problem(...)`



// Sorts data and problems vectors together using problem attributes as the sort key:
// - `SIZE`: sort by problem size in ascending order
// - `OPTIMUM_PROXIMITY`: sort by proximity of the best known solution to the angular optimum (in ascending order), measured by normalized angular quality (inverted)
// - `NONE`: do not sort, keep the original order
enum class SortingCriterion {
    SIZE,
    OPTIMUM_PROXIMITY,
    NONE
};
enum class AggregationType {
    MEAN,
    MEDIAN,
    MIN,
    MAX
};





/****************************************** Data Structures for Experiment Results ****************************************** */
using MethodFunction = std::function<AlgorithmRunMetrics(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)>;

// @brief Type for statistics of a single run of a method on a problem instance
// Contains the following statistics:
//
// - `cayley_distance`, `hamming_distance`: distance of the solution found by the method from the best known solution, measured in Cayley and Hamming distances, respectively. Normalized by problem size, these statistics can show how close the method's solutions are to the best known solution in terms of these distances, which can provide insights into the landscape geometry and the method's ability to navigate it.
//
// - `mean_cayley_similarity_to_other_local_optima`: mean Cayley similarity of the solution found by the method to other local optima, which can provide insights into the diversity of solutions and the method's ability to explore the solution space.
// 
// - `cost`: cost of the solution found by the method
//
// - `cost_relative_quality`, `cos_quality`, `normalized_angular_quality`, `relative_angular_quality`: quality of the solution found by the method, measured in terms of relative cost quality (lower is better), cosine quality (lower is better), normalized angular quality (higher is better), and relative angular quality (higher is better).
//
// - `time`: time taken to find the solution
//
// - `total_n_swaps`, `total_n_eval_solutions`: total number of swaps performed and total number of solutions evaluated by the method during the run, which can provide insights into the method's efficiency and search behavior.
//
// - `rel_eff`, `norm_eff`: relative efficiency and normalized efficiency of the method during the run, which can provide insights into the method's efficiency in finding good solutions relative to the search effort.
// 
//- `initial_cost_relative_quality`, `initial_cos_quality`: relative cost quality and cosine quality
template <typename T=double>
struct RunStatisticsPoint {
    double cayley_distance = 0.0;
    double hamming_distance = 0.0;
    double mean_cayley_similarity_to_other_local_optima = 0.0;
    std::int64_t cost = 0;
    double cost_relative_quality = 0.0, cos_quality = 0.0,  normalized_angular_quality = 0.0, relative_angular_quality = 0.0;
    double time = 0.0;
    int total_n_swaps = 0, total_n_eval_solutions = 0;
    double rel_eff = 0.0, norm_eff = 0.0;
    
    double initial_cost_rel_quality = 0.0, initial_cos_quality = 0.0;

    std::map<std::string, T> to_map() const
    {
        return {{"cayley_distance",            static_cast<T>(cayley_distance)},
                {"hamming_distance",           static_cast<T>(hamming_distance)},
                {"mean_cayley_similarity_to_other_local_optima", static_cast<T>(mean_cayley_similarity_to_other_local_optima)},
                {"cayley_similarity_to_best_known", 1.0 - static_cast<T>(cayley_distance)},
                {"hamming_similarity_to_best_known", 1.0 - static_cast<T>(hamming_distance)},
                {"cost",                       static_cast<T>(cost)},
                {"cost_relative_quality",      static_cast<T>(cost_relative_quality)},
                {"cos_quality",                static_cast<T>(cos_quality)},
                {"normalized_angular_quality", static_cast<T>(normalized_angular_quality)},
                {"relative_angular_quality",   static_cast<T>(relative_angular_quality)},
                {"time",                       static_cast<T>(time)},
                {"total_n_swaps",              static_cast<T>(total_n_swaps)},
                {"total_n_eval_solutions",     static_cast<T>(total_n_eval_solutions)},
                {"rel_eff",                    static_cast<T>(rel_eff)},
                {"norm_eff",                   static_cast<T>(norm_eff)}, 
                {"initial_cost_relative_quality",static_cast<T>(initial_cost_rel_quality)}, 
                {"initial_cos_quality",          static_cast<T>(initial_cos_quality)}

        };
    }
};

// @brief Type for statistics of multiple runs of a method on a problem instance: (statistic_name: [values for each run of the method on the problem instance])
template <typename T=double>
struct RunsStatistics {
    std::map<std::string, std::vector<T>> data;

    static std::vector<std::string> get_statistic_names()
    {
        std::map<std::string, T> m = RunStatisticsPoint<T>().to_map();
        std::vector<std::string> keys;

        // Extract keys using std::transform and a lambda function
        std::transform(m.begin(), m.end(), std::back_inserter(keys),
                [](const std::pair<std::string, T> &pair) { return pair.first; });
        return keys;
    }

    RunsStatistics() { for (const auto& name : get_statistic_names()) data[name] = {}; }

    size_t size() const { return data.empty() ? 0 : data.begin()->second.size(); }

    bool is_consistent() const
    {
        const size_t n = size();
        return std::all_of(data.begin(), data.end(), [n](const auto& kv) { return kv.second.size() == n; });
    }

    void reserve(size_t n) { for (auto& [_, vec] : data) vec.reserve(n); }
    void resize(size_t n)  { for (auto& [_, vec] : data) vec.resize(n); }
    void append(const RunStatisticsPoint<T>& p)
    {
        for (const auto& [name, val] : p.to_map()) data[name].push_back(val);
    }

    void set(size_t index, const RunStatisticsPoint<T>& p)
    {
        for (const auto& [name, val] : p.to_map()) data[name][index] = val;
    }

    void append_from(const RunsStatistics<T>& other)
    {
        for (auto& [name, vec] : data)
        {
            const auto& src = other.data.at(name);
            vec.insert(vec.end(), src.begin(), src.end());
        }
    }
};



    // type for (problem:{solution_distances, solution_cost, solution_qualities, time_taken}) for multiple runs of a method on multiple problem instances
    template <typename T=double>
    using ProblemsRunsStatistics = std::map<std::string, RunsStatistics<T>>;
    // type for (method: {problem:{statistic_name: [values for each run of the method on the problem instance]}})
    template <typename T=double>
    using MethodsProblemsRunsStatistics = std::map<std::string, ProblemsRunsStatistics<T>>;
    // type for (problem: [final permutations for each run])
    using ProblemsRunsSolutions = std::map<std::string, std::vector<Permutation<int>>>;
    // type for (method: {problem: [final permutations for each run]})
    using MethodsProblemsRunsSolutions = std::map<std::string, ProblemsRunsSolutions>;

    // rearranged type for plotting: (problem:{statistic_name: [values for each run of the method on the problem instance]})
    template <typename T=double>
    using PlottingStatistics = std::map<std::string, std::vector<std::vector<T>>>;
    // rearranged type for plotting: (statistic_name:{problem: [values for each run of the method on the problem instance]})
    template <typename T=double>
    using PlottingStatisticsByProblem = std::map<std::string, std::map<std::string, std::vector<T>>>;
    template <typename T=double>
    using MethodsPlottingStatisticsByProblem = std::map<std::string, PlottingStatisticsByProblem<T>>;


/************************************** Container for experiment results *******************************************/



// @brief Container for experiment results, including `methods_runs_statistics` and `methods_runs_solutions` subcontainers, with utility functions for merging results from multiple runs and converting to formats suitable for plotting.
//
// Some useful methods:
//
// - `merge(other)` - merge the results from another `ExperimentResults` object into the current one.
//
// - `aggregate` - aggregate statistics by problem for a given `statistic_name`, `aggregation_type` (possible values are `AggregationType:: MIN, MAX, MEAN, MEDIAN`), statistics are sorted as original container is.
template <typename T=double>
class ExperimentResults {
private:
    MethodsProblemsRunsStatistics<T> methods_runs_statistics_;
    MethodsProblemsRunsSolutions methods_runs_solutions_;

    static bool is_valid_runs_statistics(const RunsStatistics<T>& runs_statistics){ return runs_statistics.is_consistent(); }

public:
    ExperimentResults<T>() = default;
    explicit ExperimentResults<T>(MethodsProblemsRunsStatistics<T> methods_runs_statistics)
        : methods_runs_statistics_(std::move(methods_runs_statistics)) {}
    ExperimentResults<T>(MethodsProblemsRunsStatistics<T> methods_runs_statistics,
                         MethodsProblemsRunsSolutions methods_runs_solutions)
        : methods_runs_statistics_(std::move(methods_runs_statistics)),
          methods_runs_solutions_(std::move(methods_runs_solutions)) {}

    void clear(){methods_runs_statistics_.clear(); methods_runs_solutions_.clear();}
    bool empty() const {return methods_runs_statistics_.empty();}

    // Returns the dimensions of the results as a tuple: (number of methods, max number of problems, max number of runs)
    std::tuple<size_t, size_t, size_t> get_dimensions() const
    {
        size_t n_methods = methods_runs_statistics_.size();
        size_t n_problems = 0;
        size_t n_runs = 0;
        for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics_) {
            n_problems = std::max(n_problems, problems_runs_statistics.size());
            for (const auto& [problem_name, runs_statistics] : problems_runs_statistics) {
                n_runs = std::max(n_runs, runs_statistics.size());
            }
        }
        return std::make_tuple(n_methods, n_problems, n_runs);
    }



    bool has_method(const std::string& method_name) const
    { return methods_runs_statistics_.find(method_name) != methods_runs_statistics_.end(); }

    bool has_problem(const std::string& method_name, const std::string& problem_name) const
    {
        const auto method_it = methods_runs_statistics_.find(method_name);
        if (method_it == methods_runs_statistics_.end())
            return false;
        return method_it->second.find(problem_name) != method_it->second.end();
    }

    // Get a list of method names for which results are available
    std::vector<std::string> get_method_names() const
    {
        std::vector<std::string> names;
        names.reserve(methods_runs_statistics_.size());
        for (const auto& [method_name, _] : methods_runs_statistics_)
            names.push_back(method_name);
        return names;
    }

    // Get a list of problem names for which results are available for a given method
    std::vector<std::string> get_problem_names_for_method(const std::string& method_name) const
    {
        std::vector<std::string> names;
        const auto method_it = methods_runs_statistics_.find(method_name);
        if (method_it == methods_runs_statistics_.end())
            return names;

        names.reserve(method_it->second.size());
        for (const auto& [problem_name, _] : method_it->second)
            names.push_back(problem_name);
        return names;
    }

    std::vector<std::string> get_available_statistics() const{ return RunsStatistics<T>::get_statistic_names();}

    // Get the runs statistics for a given method and problem names, or nullptr if not found
    const RunsStatistics<T>* find_runs(const std::string& method_name, const std::string& problem_name) const
    {
        const auto method_it = methods_runs_statistics_.find(method_name);
        if (method_it == methods_runs_statistics_.end()) {
            return nullptr;
        }

        const auto problem_it = method_it->second.find(problem_name);
        if (problem_it == method_it->second.end()) {
            return nullptr;
        }

        return &problem_it->second;
    }

    // Get the run solutions for a given method and problem names, or nullptr if not found
    const std::vector<Permutation<int>>* find_run_solutions(const std::string& method_name, const std::string& problem_name) const
    {
        const auto method_it = methods_runs_solutions_.find(method_name);
        if (method_it == methods_runs_solutions_.end())
            return nullptr;

        const auto problem_it = method_it->second.find(problem_name);
        if (problem_it == method_it->second.end())
            return nullptr;

        return &problem_it->second;
    }

    // Merge the results from another ExperimentResults object into this one.
    void merge(const ExperimentResults<T>& other)
    {
        for (const auto& [method_name, problems_runs_statistics] : other.methods_runs_statistics_) {
            append_method_results(method_name, problems_runs_statistics);

            const auto solutions_it = other.methods_runs_solutions_.find(method_name);
            if (solutions_it != other.methods_runs_solutions_.end()) {
                append_method_solutions(method_name, solutions_it->second);
            }
        }
    }

    MethodsPlottingStatisticsByProblem<T> to_plotting_statistics_by_problem() const;

    const MethodsProblemsRunsStatistics<T>& raw() const {return methods_runs_statistics_;}
    const MethodsProblemsRunsSolutions& raw_solutions() const {return methods_runs_solutions_;}

    // Returns a const reference to all problem-run statistics for the named method.
    // Throws std::out_of_range if the method name is not found.
    const ProblemsRunsStatistics<T>& operator[](const std::string& method_name) const
    {
        const auto it = methods_runs_statistics_.find(method_name);
        if (it == methods_runs_statistics_.end()) {
            throw std::out_of_range("ExperimentResults::operator[]: method '" + method_name + "' not found");
        }
        return it->second;
    }

    // Aggregate multiple runs statistics of a specified `statistic_name` across multiple methods for each problem instance using the specified `aggregation_type` (e.g. `MEAN`, `MEDIAN`, `MIN`, `MAX`).
    // Useful primarly to take `MAX` (default statistic) values across all the methods and runs.
    // 
    // Returns a map: problem_name -> aggregated_statistic_value for the given statistic name, aggregation type, and sorting criterion
    // The sorting criterion is used to sort the problems by their attributes (e.g. 'SIZE', 'OPTIMUM_PROXIMITY') 
    // Refer to `get_available_statistics` method for the list of available statistic names that can be aggregated.
    std::map<std::string, T> aggregate_by_problem(const std::string& statistic_name, 
                                                    AggregationType aggregation_type = AggregationType::MAX) const
    {
        std::map<std::string, T> aggregated_results;
        switch (aggregation_type){
            case AggregationType::MAX:
                for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics_)
                    for (const auto& [problem_name, runs_statistics] : problems_runs_statistics)
                        aggregated_results[problem_name] = std::max(aggregated_results[problem_name], 
                                                                    *std::max_element(runs_statistics.data.at(statistic_name).begin(), runs_statistics.data.at(statistic_name).end()));
                break;
            case AggregationType::MIN:
                for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics_)
                    for (const auto& [problem_name, runs_statistics] : problems_runs_statistics)
                        aggregated_results[problem_name] = std::min(aggregated_results[problem_name], 
                                                                    *std::min_element(runs_statistics.data.at(statistic_name).begin(), runs_statistics.data.at(statistic_name).end()));
                break;
            case AggregationType::MEAN: {
                std::map<std::string, std::vector<T>> values;
                for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics_)
                    for (const auto& [problem_name, runs_statistics] : problems_runs_statistics)
                        values[problem_name].insert(values[problem_name].end(), runs_statistics.data.at(statistic_name).begin(), runs_statistics.data.at(statistic_name).end());
                for (auto& [problem_name, vals] : values) {
                    T sum = std::accumulate(vals.begin(), vals.end(), static_cast<T>(0));
                    aggregated_results[problem_name] = sum / static_cast<T>(vals.size());
                }
                break;
            }
            case AggregationType::MEDIAN: {
                std::map<std::string, std::vector<T>> values;
                for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics_)
                    for (const auto& [problem_name, runs_statistics] : problems_runs_statistics)
                        values[problem_name].insert(values[problem_name].end(), runs_statistics.data.at(statistic_name).begin(), runs_statistics.data.at(statistic_name).end());
                for (auto& [problem_name, vals] : values) {
                    std::sort(vals.begin(), vals.end());
                    size_t mid = vals.size() / 2;
                    aggregated_results[problem_name] = (vals.size() % 2 == 0) ? (vals[mid - 1] + vals[mid]) / static_cast<T>(2) : vals[mid];
                }
                break;
            }
            default:
                throw std::invalid_argument("Unsupported aggregation type");
        }
        return aggregated_results;
    }
    // Aggregate multiple runs statistics of a specified `statistic_name` for a given `method_name` and each problem instance using the specified `aggregation_type` (e.g. `MEAN`, `MEDIAN`, `MIN`, `MAX`).
    //
    // Returns a map: problem_name -> aggregated_statistic_value for the given method name, statistic name, aggregation type, and sorting criterion
    // The sorting criterion is used to sort the problems by their attributes (e.g. 'SIZE', 'OPTIMUM_PROXIMITY') 
    // Refer to `get_available_statistics` method for the list of available statistic names that can be aggregated.
    std::map<std::string, T> aggregate_by_problem(const std::string& method_name, const std::string& statistic_name, 
                                                    AggregationType aggregation_type) const
    {
        std::map<std::string, T> aggregated_results;
        for (const auto& [problem_name, runs_statistics] : methods_runs_statistics_.at(method_name))
        {
            const auto& values = runs_statistics.data.at(statistic_name);
            T aggregated_value = 0;
            switch (aggregation_type){
                case AggregationType::MEAN:
                    aggregated_value = std::accumulate(values.begin(), values.end(), static_cast<T>(0)) / static_cast<T>(values.size());
                    break;
                case AggregationType::MEDIAN:
                {
                    std::vector<T> sorted_values = values;
                    std::sort(sorted_values.begin(), sorted_values.end());
                    size_t mid = sorted_values.size() / 2;
                    aggregated_value = (sorted_values.size() % 2 == 0) ? (sorted_values[mid - 1] + sorted_values[mid]) / static_cast<T>(2) : sorted_values[mid];
                    break;
                }
                case AggregationType::MIN:
                    aggregated_value = *std::min_element(values.begin(), values.end());
                       break;
                case AggregationType::MAX:
                    aggregated_value = *std::max_element(values.begin(), values.end());
                    break;
                }
                aggregated_results[problem_name] = aggregated_value;
               
        }
        return aggregated_results;
    }
    // @brief Aggregate multiple runs statistics of a specified `statistic_name` for each method and problem instance using the specified `aggregation_type` (e.g. `MEAN`, `MEDIAN`, `MIN`, `MAX`).
    // @return a map: method_name -> problem_name -> aggregated_statistic_value for the given statistic name, aggregation type, and sorting criterion
    // The sorting criterion is used to sort the problems by their attributes (e.g. 'SIZE', 'OPTIMUM_PROXIMITY') 
    // @note Refer to `get_available_statistics` method for the list of available statistic names that can be aggregated.
    std::map<std::string, std::map<std::string, T>> aggregate(const std::string& statistic_name, AggregationType aggregation_type) const{
        if (methods_runs_statistics_.empty()) { return {}; }
        std::map<std::string, std::map<std::string, T>> aggregated_results;
        for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics_)
            aggregated_results[method_name] = aggregate_by_problem(method_name, statistic_name, aggregation_type);
        return aggregated_results;
    }


    // For given method and problem names, returns the pair (permutation, cost) of the best solution found across all runs of the method on the problem instance, where the best solution is defined as the one with the lowest cost (best cost).
    // Theoretically possible to discover best known solution. Use Problem::get_best_cost() and Problem::get_best_solution() to get the best known solution and its cost for a given problem instance, and compare it with the best solution found across all runs of the method on the problem instance.
    std::pair<Permutation<int>, std::int64_t> get_best_solution_for_problem(const std::string& method_name, const std::string& problem_name) const
    {
        const auto* runs_statistics = find_runs(method_name, problem_name);
        const auto* runs_solutions = find_run_solutions(method_name, problem_name);
        if (!runs_statistics || !runs_solutions || runs_statistics->size() == 0 || runs_solutions->empty()) {
            throw std::runtime_error("No runs statistics found for method '" + method_name + "' and problem '" + problem_name + "'.");
        }

        size_t best_run_index = 0;
        std::int64_t best_cost = std::numeric_limits<std::int64_t>::max();
        for (size_t i = 0; i < runs_statistics->size(); ++i) {
            std::int64_t cost = static_cast<std::int64_t>((*runs_statistics).data.at("cost")[i]);
            if (cost < best_cost) {
                best_cost = cost;
                best_run_index = i;
            }
        }

        if (best_run_index >= runs_solutions->size()) {
            throw std::runtime_error("Inconsistent runs statistics and runs solutions sizes for method '" + method_name + "' and problem '" + problem_name + "'.");
        }

        return {(*runs_solutions)[best_run_index], best_cost};
    }
public:

    // Append runs statistics for a given method and problem. If the method and problem already have statistics, the new statistics will be appended to the existing ones. If not, a new entry will be created.
    void append_problem_runs(const std::string& method_name,
                             const std::string& problem_name,
                             const RunsStatistics<T>& runs_statistics)
    {
        if (!is_valid_runs_statistics(runs_statistics)) {
            std::cerr << Colors::YELLOW
                      << " WARNING: Ignoring malformed runs statistics for method '"
                      << method_name << "' and problem '" << problem_name << "'."
                      << Colors::RESET << std::endl;
            return;
        }

        auto& problems_runs_statistics = methods_runs_statistics_[method_name];
        auto problem_it = problems_runs_statistics.find(problem_name);
        if (problem_it == problems_runs_statistics.end()) {
            problems_runs_statistics[problem_name] = runs_statistics;
            return;
        }

        problem_it->second.append_from(runs_statistics);
    }

    // Append runs statistics for multiple problems of a given method. If the method and problem already have statistics, the new statistics will be appended to the existing ones. If not, a new entry will be created.
    void append_method_results(const std::string& method_name,
                               const ProblemsRunsStatistics<T>& problems_runs_statistics)
    {
        for (const auto& [problem_name, runs_statistics] : problems_runs_statistics) {
            append_problem_runs(method_name, problem_name, runs_statistics);
        }
    }

    void append_problem_solutions(const std::string& method_name,
                                  const std::string& problem_name,
                                  const std::vector<Permutation<int>>& runs_solutions)
    {
        auto& problems_runs_solutions = methods_runs_solutions_[method_name];
        auto& target = problems_runs_solutions[problem_name];
        target.insert(target.end(), runs_solutions.begin(), runs_solutions.end());
    }

    void append_method_solutions(const std::string& method_name,
                                 const ProblemsRunsSolutions& problems_runs_solutions)
    {
        for (const auto& [problem_name, runs_solutions] : problems_runs_solutions) {
            append_problem_solutions(method_name, problem_name, runs_solutions);
        }
    }
};

struct MethodDefinition {
    std::string name;
    MethodFunction method;
    AlgorithmRunConfig run_config;
    std::string color;
    std::string marker;
    std::function<AlgorithmRunConfig(const Problem<int>&)> run_config_for_problem;
};

//////////////////////// Forward declarations /////////////////////////////////////////////////////////////////////////////////////////////////////////////

static RunStatisticsPoint<> get_statistics(const MethodFunction& method,
                   const Problem<int>& problem,
                   Permutation<int>& permutation,
                   const AlgorithmRunConfig& run_config,
                    int verbose =1);
static std::vector<double> get_mean_cayley_similarity_to_other_local_optima(const std::vector<Permutation<int>>& local_optima);
static RunsStatistics<> get_runs_statistics(const MethodFunction& method,
                        const Problem<int>& problem,
                        int n_runs = 10,
                        const AlgorithmRunConfig& run_config = {},
                        std::vector<Permutation<int>>* out_final_permutations = nullptr,
                        int verbose = 1);
static ProblemsRunsStatistics<> get_problems_runs_statistics(const MethodFunction& method,
                                                const std::vector<Problem<int>>& problems,
                                                int n_runs = 10,
                                                const AlgorithmRunConfig& run_config = {},
                                                const std::function<AlgorithmRunConfig(const Problem<int>&)>& run_config_for_problem = nullptr,
                                                ProblemsRunsSolutions* out_problems_runs_solutions = nullptr,
                                                int verbose = 1);
static MethodsProblemsRunsStatistics<> get_methods_problems_runs_statistics(const std::vector<MethodDefinition>& methods,
                                        const std::vector<Problem<int>>& problems,
                                        int n_runs = 10,
                                        MethodsProblemsRunsSolutions* out_methods_runs_solutions = nullptr,
                                        int verbose = 1);
ExperimentResults<>
    collect_experiment_results(const std::vector<MethodDefinition>& methods,
                               const std::vector<Problem<int>>& problems,
                               int n_runs = 10,
                               int verbose = 1);







///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////// Function definitions /////////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////



//////////////////////// Sorting functions /////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Sorts data and problems vectors together using problem attributes as the sort key
template <typename T> void sort_data(std::vector<T>& data,
                                        std::vector<Problem<int>>& problems,
                                        SortingCriterion sorting_criterion=SortingCriterion::SIZE) {
    std::vector<size_t> idx(problems.size());
    std::iota(idx.begin(), idx.end(), 0);

    switch(sorting_criterion) {
        case SortingCriterion::SIZE:
            std::sort(idx.begin(), idx.end(), [&](size_t a, size_t b) {
                return problems[a].get_size() < problems[b].get_size();
            });
            break;
        case SortingCriterion::OPTIMUM_PROXIMITY: {
            auto difficulty_measure = [](const Problem<int>& problem) {
                const auto& matrices = problem.get_matrices();
                const auto best_cost = problem.get_best_cost();
                return cos_quality_of_solution(best_cost, matrices.first, matrices.second);
                //return -normalized_angle_quality_of_solution(best_cost, matrices.first, matrices.second);
            };
            std::sort(idx.begin(), idx.end(), [&](size_t a, size_t b) {
                return difficulty_measure(problems[a]) < difficulty_measure(problems[b]);
            });
            break;
        }
        default:
            return;
    }

    // Apply the sorted index permutation to both data and problems
    std::vector<T> sorted_data(data.size());
    std::vector<Problem<int>> sorted_problems(problems.size());
    for (size_t i = 0; i < idx.size(); ++i) {
        sorted_data[i] = data[idx[i]];
        sorted_problems[i] = problems[idx[i]];
    }
    data = std::move(sorted_data);
    problems = std::move(sorted_problems);
}

void sort_problems(std::vector<Problem<int>>& problems,
                   SortingCriterion sorting_criterion = SortingCriterion::SIZE)
{
    std::vector<int> order_anchor(problems.size(), 0);
    sort_data(order_anchor, problems, sorting_criterion);
}
















///////////////////////// Statistics gathering functions /////////////////////////////////////////////////////////////////////////////////////////////////////////////

// For a single run of the method:
// returns tuple of statistics specified above
// initial solution is given from the calling function by reference to avoid multiple allocations of memory
// @param verbose 0 - supress warnings and notes, 1 - allow warnings and supress notes, 2+ - allow notes.
// @return `RunStatisticsPoint` container with the statistics of the method run on the given problem instance, including the cost and quality of the solution found, time taken, and other relevant metrics.
RunStatisticsPoint<> static get_statistics(const MethodFunction& method,
                                    const Problem<int>& problem,
                                    Permutation<int>& permutation,
                                    const AlgorithmRunConfig& run_config,
                                int verbose)
{
    const auto& matrices = problem.get_matrices();
    const auto& best_permutation = problem.get_best_solution();
    const auto best_cost = problem.get_best_cost();

    int64_t initial_cost = cost_function(matrices.first, matrices.second, permutation);
    double initial_cost_rel_quality = relative_cost_quality_of_solution(initial_cost, best_cost);
    double initial_cos_quality = cos_quality_of_solution(initial_cost, matrices.first, matrices.second);



    // MAIN measurement and statistics gathering for the method run:
    const double start = algorithm_time_now();
    auto [solution_cost, total_n_swaps, total_n_eval_solutions, rel_eff, norm_eff, total_time_run
          ] =  method(problem, permutation, run_config);
    double time_taken = algorithm_time_now() - start;




    // Check if the solution is really good:
        if (verbose>=2 && normalized_angular_distance_of_solutions(solution_cost, best_cost, matrices.first, matrices.second) < 0)
        {
            std::cerr <<'\n' << Colors::GREEN << "get_statistics:: NOTE: "<<Colors::RESET<<"Problem "<< problem.get_name()<<": Relative cost quality of the solution is negative, i.e. the solution found is superior to the best known solution. This may indicate that the method has found a new best solution, or that there is an inconsistency in the cost function implementation or in the best known solution's cost." << Colors::RESET << std::endl;
            permutation.print("New best solution found: ");
            printf("Cost of the new best solution: %lld, Cost of the previous best solution: %lld\n", solution_cost, best_cost);
        }
        else if (verbose>=2 &&
                normalized_angular_distance_of_solutions(solution_cost, best_cost, matrices.first, matrices.second) < 0.01 && 
                relative_cost_quality_of_solution(solution_cost, best_cost) < 0.01)
        {
            std::cerr <<'\n' << Colors::GREEN << "get_statistics:: NOTE: "<<Colors::RESET<<"Problem "<< problem.get_name()<<": Relative cost quality of the solution is very close to 0, i.e. the solution found is very close in cost to the best known solution. This may indicate that the method has found a solution of comparable quality to the best known solution, or that there is an inconsistency in the cost function implementation or in the best known solution's cost." << Colors::RESET << std::endl;
            permutation.print("New solution found with cost close to the best known solution: ");
            printf("Cost of the new solution: %lld, Cost of the best known solution: %lld\n", solution_cost, best_cost);
        }


    // Check whether time measurement has some inconsistencies (actual time taken by the algorithm can be lower than timer resolution (0.001s))
    if (verbose >= 1){
            if ( time_taken - total_time_run>= 2.0* get_time_resolution())
                std::cerr <<'\n' << Colors::YELLOW << "get_statistics:: WARNING: "<<Colors::RESET<<"Problem "<< problem.get_name()<<": Time taken for the method run (" << total_time_run << "s) is significantly less than the total time measured for the statistics gathering (" << time_taken << "s). This may indicate that the method is not properly measuring its execution time or that there are significant overheads in the statistics gathering process." << Colors::RESET;
            if (time_taken<get_time_resolution())
            {
                std::cerr <<'\n' <<(time_taken==0 && total_time_run==0? Colors::RED: Colors::YELLOW) << "get_statistics:: WARNING: "<<Colors::RESET<<"Problem "<< problem.get_name()
                <<": [External] time taken for the method run (" << time_taken << "s) is very close to or less than the timer resolution (" << get_time_resolution() << "s)" 
                    // << "(Internal time taken on the dedicated core, if any, is: "<<total_time_run <<")"
                <<" Setting to time resolution to avoid unreliable measurements." << Colors::RESET;
                
                time_taken = get_time_resolution();

                if (verbose>=2)
                    std::cerr <<'\n' << Colors::YELLOW << "get_statistics:: WARNING (time inconsistency) details:"<<Colors::RESET<< "Problem: "<< problem.get_name()<<". Total time run: "<<total_time_run<<". Method performed "<<total_n_swaps<<" swaps, evaluated "<< total_n_eval_solutions<<" solutions. Efficiency (relative, normalized): "<<rel_eff<<", "<< norm_eff;

            }
        }


    
    // check if the cost returned by the method matches the cost calculated from the solution using the cost function
    std::int64_t calculated_solution_cost = cost_function(matrices.first, matrices.second, permutation);
    if (solution_cost!= calculated_solution_cost)
        std::cerr <<'\n' << Colors::YELLOW << "get_statistics:: WARNING: "<<Colors::RESET<<"Problem "<< problem.get_name()<<": Calculated cost of the solution (" << calculated_solution_cost << ") does not match the cost returned by the method (" << solution_cost << "). This may indicate an inconsistency in the cost function implementation or in the method's return value." << Colors::RESET << std::endl;
    
    // Calculating some statistics
    double cost_rel_quality = relative_cost_quality_of_solution(solution_cost, best_cost);
    double cos_quality = cos_quality_of_solution(solution_cost, matrices.first, matrices.second);
    double normalized_angle_quality = normalized_angle_quality_of_solution(solution_cost, matrices.first, matrices.second);
    double relative_angular_quality = relative_angular_quality_of_solution(solution_cost, best_cost, matrices.first, matrices.second);
    return {
            permutation.normalized_distance(best_permutation, Permutation<int>::DistanceMethod::CAYLEY),
            permutation.normalized_distance(best_permutation, Permutation<int>::DistanceMethod::HAMMING),
            0.0,
            solution_cost,
            cost_rel_quality, cos_quality,
            normalized_angle_quality, relative_angular_quality,
            time_taken,
            total_n_swaps, total_n_eval_solutions,
            rel_eff, norm_eff, 
            initial_cost_rel_quality, initial_cos_quality
    };
}



// returns tuple of stats from multiple runs of the method on a given problem, including:
// 1. Tuple of normalized Hamming and Cayley distances of the solution from the best known solution,
// 2. Cost of the solution found by the method,
// 3. Tuple of quality of the solution compared to the best known solution, normalized angular quality of the solution, and relative angular quality of the solution.
// 4. Time taken to find the solution.
// 5. Tuple of counts of total number of swaps and total number of evaluated solutions.
RunsStatistics<>
    static get_runs_statistics(const MethodFunction& method,
                        const Problem<int>& problem,
                        int n_runs,
                        const AlgorithmRunConfig& run_config,
                        std::vector<Permutation<int>>* out_final_permutations,
                        int verbose)
{
    RunsStatistics<> runs_statistics;
    runs_statistics.reserve(n_runs);

    const int size = problem.get_size();
    std::vector<RunStatisticsPoint<>> run_points;
    run_points.reserve(n_runs);
    std::vector<Permutation<int>> local_optima;
    local_optima.reserve(n_runs);



    auto run_single = [&](Permutation<int>& permutation) {
        run_points.push_back(get_statistics(method, problem, permutation, run_config, verbose));
        local_optima.push_back(permutation);
    };


    // MAIN LOOP:
    // Runs are sequential here; parallelism is applied at the problem level.
    // Reuse one permutation object to avoid repeated allocations in tight loops.
    Permutation<int> permutation(size);
    for (int i = 0; i < n_runs; i++) {
        permutation.reset();
        permutation.reshuffle();
        run_single(permutation);
    }

    const std::vector<double> mean_similarity = get_mean_cayley_similarity_to_other_local_optima(local_optima);
    for (size_t i = 0; i < run_points.size(); ++i) {
        run_points[i].mean_cayley_similarity_to_other_local_optima = mean_similarity[i];
        runs_statistics.append(run_points[i]);
    }

    if (out_final_permutations) {
        *out_final_permutations = std::move(local_optima);
    }

    return runs_statistics;
}

static ProblemsRunsStatistics<> get_problems_runs_statistics(const MethodFunction& method,
                                                    const std::vector<Problem<int>>& problems,
                                                    int n_runs,
                                                    const AlgorithmRunConfig& run_config,
                                                    const std::function<AlgorithmRunConfig(const Problem<int>&)>& run_config_for_problem,
                                                    ProblemsRunsSolutions* out_problems_runs_solutions, 
                                                    int verbose)
{
    ProblemsRunsStatistics<> problems_runs_statistics;

    if (problems.empty()) {
        return problems_runs_statistics;
    }

    // Adaptive mode: run sequentially when OpenMP is effectively single-threaded.
    if (omp_get_max_threads() <= 1 || n_runs <= 1) {
        for (const auto& problem : problems) {
            const AlgorithmRunConfig resolved_run_config = run_config_for_problem ? run_config_for_problem(problem) : run_config;
            std::vector<Permutation<int>> final_permutations;
            problems_runs_statistics[problem.get_name()] = get_runs_statistics(method, problem, n_runs, resolved_run_config, &final_permutations, verbose);
            if (out_problems_runs_solutions) {
                (*out_problems_runs_solutions)[problem.get_name()] = std::move(final_permutations);
            }
        }
        return problems_runs_statistics;
    }

    std::vector<std::vector<RunStatisticsPoint<>>> run_points_by_problem(problems.size(), std::vector<RunStatisticsPoint<>>(n_runs));
    std::vector<std::vector<Permutation<int>>> solutions_by_problem(problems.size(),std::vector<Permutation<int>>(n_runs));

    // Parallelize by run index so each worker evaluates one run across all problems.
    #pragma omp parallel for default(none) shared(problems, n_runs, method, run_points_by_problem, solutions_by_problem, run_config, run_config_for_problem, verbose)
    for (int run_i = 0; run_i < n_runs; ++run_i) {
        for (int problem_i = 0; problem_i < static_cast<int>(problems.size()); ++problem_i) {
            const auto& problem = problems[problem_i];
            const AlgorithmRunConfig resolved_run_config = run_config_for_problem ? run_config_for_problem(problem) : run_config;
            
            Permutation<int> permutation(problem.get_size());
            permutation.reshuffle();

            run_points_by_problem[problem_i][run_i] = get_statistics(method, problem, permutation, resolved_run_config, verbose);

            solutions_by_problem[problem_i][run_i] = std::move(permutation);
        }
    }

    
    for (size_t problem_i = 0; problem_i < problems.size(); ++problem_i)
    {
        RunsStatistics<> runs_statistics;
        runs_statistics.reserve(n_runs);

        std::vector<double> mean_cayley_similarity = get_mean_cayley_similarity_to_other_local_optima(solutions_by_problem[problem_i]);
        for (int run_i = 0; run_i < n_runs; ++run_i) {
            run_points_by_problem[problem_i][run_i].mean_cayley_similarity_to_other_local_optima = mean_cayley_similarity[run_i];
            runs_statistics.append(run_points_by_problem[problem_i][run_i]);
        }

        problems_runs_statistics[problems[problem_i].get_name()] = std::move(runs_statistics);
        if (out_problems_runs_solutions) {
            (*out_problems_runs_solutions)[problems[problem_i].get_name()] = std::move(solutions_by_problem[problem_i]);
        }
    }
    return problems_runs_statistics;
}

// maps methods runs statistics (on multiple problems) to method names
static MethodsProblemsRunsStatistics<> get_methods_problems_runs_statistics(const std::vector<MethodDefinition>& methods,
                                                                   const std::vector<Problem<int>>& problems,
                                                                   int n_runs,
                                                                   MethodsProblemsRunsSolutions* out_methods_runs_solutions,
                                                                int verbose)
{
    // Check duplicates:
    std::set<std::string> unique_problem_names;
    for (const auto& problem : problems) {
        unique_problem_names.insert(problem.get_name());
    }
    if (unique_problem_names.size() != problems.size()) {
        std::cerr << Colors::YELLOW << "get_methods_problems_runs_statistics:: WARNING: "<<Colors::RESET<<"Duplicate problem instances detected in the input. This may lead to redundant computations and skewed statistics." << Colors::RESET << std::endl;
    }

    MethodsProblemsRunsStatistics<> methods_runs_statistics;

    for (const auto& method_definition : methods) {
        ProblemsRunsSolutions problems_runs_solutions;
        methods_runs_statistics[method_definition.name] = get_problems_runs_statistics(method_definition.method,
                                                                                       std::vector< Problem<int>>(problems.begin(), problems.end()),
                                                                                       n_runs,
                                                                                       method_definition.run_config,
                                                                                       method_definition.run_config_for_problem,
                                                                                       &problems_runs_solutions,
                                                                                    verbose);
        if (out_methods_runs_solutions) {
            (*out_methods_runs_solutions)[method_definition.name] = std::move(problems_runs_solutions);
        }
    }

    return methods_runs_statistics;
}

ExperimentResults<> collect_experiment_results(const std::vector<MethodDefinition>& methods,
                                             const std::vector<Problem<int>>& problems,
                                             int n_runs, 
                                             int verbose)
{
    MethodsProblemsRunsSolutions methods_runs_solutions;
    MethodsProblemsRunsStatistics<> methods_runs_statistics =
        get_methods_problems_runs_statistics(methods, problems, n_runs, &methods_runs_solutions, verbose);

    if (verbose > 0) {
        std::cout << "\n[debug] collect_experiment_results: stats methods=" << methods_runs_statistics.size()  << ", solutions methods=" << methods_runs_solutions.size() << std::endl;
        for (const auto& [method_name, problem_solutions] : methods_runs_solutions) 
            std::cout << "[debug] collect_experiment_results: " << method_name << " solution-problem entries=" << problem_solutions.size() << std::endl;
    }

    return ExperimentResults<>(std::move(methods_runs_statistics), std::move(methods_runs_solutions));
}

























/********************************************************************************************************************/
/***********************************Statistics functions: Spearman, Mean Cayley Similarity **********************************************/
/****************************************************************************************************************/

// @brief The Spearman rank correlation coefficient for two vectors.
// @return NaN if vectors are not the same size or have less than 2 elements.
double spearman_rank_correlation(const std::vector<double>& x, const std::vector<double>& y) {
    if (x.size() != y.size() || x.size() < 2) return std::numeric_limits<double>::quiet_NaN();
    size_t n = x.size();

    // Helper: compute ranks (average for ties)
    auto compute_ranks = [](const std::vector<double>& v) {
        std::vector<size_t> idx(v.size());
        std::iota(idx.begin(), idx.end(), 0);
        std::sort(idx.begin(), idx.end(), [&](size_t i, size_t j) { return v[i] < v[j]; });
        std::vector<double> ranks(v.size());
        for (size_t i = 0; i < v.size(); ) {
            size_t j = i + 1;
            while (j < v.size() && v[idx[j]] == v[idx[i]]) ++j;
            double rank = (i + j - 1) / 2.0 + 1;
            for (size_t k = i; k < j; ++k) ranks[idx[k]] = rank;
            i = j;
        }
        return ranks;
    };

    std::vector<double> rx = compute_ranks(x);
    std::vector<double> ry = compute_ranks(y);

    double mean_rx = std::accumulate(rx.begin(), rx.end(), 0.0) / n;
    double mean_ry = std::accumulate(ry.begin(), ry.end(), 0.0) / n;
    double num = 0.0, denom_x = 0.0, denom_y = 0.0;
    for (size_t i = 0; i < n; ++i) {
        double dx = rx[i] - mean_rx;
        double dy = ry[i] - mean_ry;
        num += dx * dy;
        denom_x += dx * dx;
        denom_y += dy * dy;
    }
    if (denom_x == 0.0 || denom_y == 0.0) return std::numeric_limits<double>::quiet_NaN();
    return num / std::sqrt(denom_x * denom_y);
}

// @brief Computes the mean Cayley similarity of each local optimum to all other local optima in the given vector.
// @details The Cayley similarity between two permutations is defined as 1 - (Cayley distance / problem size), where the Cayley distance is the minimum number of swaps needed to transform one permutation into the other. The mean Cayley similarity for a local optimum is computed by averaging its Cayley similarity to all other local optima in the vector. If there is only one local optimum, its mean Cayley similarity is defined as 1.0.
// @param local_optima A vector of permutations representing the local optima found across multiple runs of a method on a problem instance. 
static std::vector<double> get_mean_cayley_similarity_to_other_local_optima(const std::vector<Permutation<int>>& local_optima)
{
    const size_t n_runs = local_optima.size();
    if (n_runs == 0)
        return {};

    std::vector<double> mean_similarity(n_runs, 0.0);
    if (n_runs == 1) {
        mean_similarity[0] = 1.0;
        return mean_similarity;
    }

    for (size_t i = 0; i < n_runs; ++i) {
        for (size_t j = i + 1; j < n_runs; ++j) {
            const double similarity = 1.0 - local_optima[i].normalized_distance(local_optima[j], Permutation<int>::DistanceMethod::CAYLEY);
            mean_similarity[i] += similarity;
            mean_similarity[j] += similarity;
        }
    }

    for (double& similarity_sum : mean_similarity)
        similarity_sum /= static_cast<double>(n_runs - 1);
        
    return mean_similarity;
}