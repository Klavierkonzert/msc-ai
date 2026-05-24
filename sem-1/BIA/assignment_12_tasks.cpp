#include <vector>
#include <random>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <stdio.h>
#include <iostream>
#include <ctime>
#include <cmath>
#include <tuple>
#include <array>
#include <filesystem>
#include <omp.h>

#include "./src/timing.h"



#include "./src/algorithms.cpp"
#include "./src/quality.cpp"
#include "./src/problem.cpp"
#include "./src/plotting.cpp"


#include "matplotlibcpp.h" // Path ${env:USERPROFILE}\source\repos should be added to the include directories in the project properties


#include "./src/colors.h"


int parse_args(char *argv[], std::vector<std::string> &args, int &N_RUNS_PER_PROBLEM, bool &RUN_PARALLEL, std::string &data_dir, std::string &plots_dir, std::pair<int, int> &fig_size, bool &retFlag);

namespace plt = matplotlibcpp;

using namespace std;

// namespace {

void task2(const std::vector<Problem<int>> &problems,
           int n_runs_per_problem, int default_max_iters, float default_time_budget_seconds,
           int verbosity_level,
           const std::string &plots_output_dir, const std::pair<int, int> &fig_size);

void efficiency_plots(const std::map<std::string, double> &strict_time_budgets_by_problem, float default_time_budget_seconds, int verbosity_level, const std::vector<Problem<int>> &problems, int n_runs_per_problem, const std::string &plots_output_dir, std::map<std::string, double> &norm_best_known_costs, const std::pair<int, int> &fig_size, const std::string subtitle="");

void task345(const std::vector<Problem<int>>& problems, 
                int n_runs_per_problem, int default_max_iters, float default_time_budget_seconds, 
                int verbosity_level,
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size);
void task3(const ExperimentResults<>& results,  const std::vector<MethodDefinition>& methods,
                const std::vector<Problem<int>>& problems,            
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size);
void task4(const ExperimentResults<>& results,  const std::vector<MethodDefinition>& methods,
                const std::vector<Problem<int>>& problems,            
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size);
void task5(const ExperimentResults<>& results,  const std::vector<MethodDefinition>& methods,
                const std::vector<Problem<int>>& problems,            
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size);

std::function<AlgorithmRunConfig(const Problem<int>&)> make_time_budget_resolver(
    const std::map<std::string, double>& budgets_by_problem,
    const double default_budget_seconds,
    const int verbosity_level,
    const map<string, double> hyperparameters,
    const double min_time_budget=0.01
);

MethodDefinition make_time_constrained_method_definition(
    const std::string& display_name,
    const MethodFunction& method,
    const std::map<std::string, double>& budgets_by_problem,
    const double default_budget_seconds,
    const int verbosity_level,
    const map<string, double> hyperparameters = {},

    const std::string& color = "",
    const std::string& marker = "");

// Creates method definitions for random search and random walk methods with time budgets determined by the provided `budgets_by_problem` map, `default_budget_seconds`, and `verbosity_level`. The display names of the methods include the `budget_label` to indicate the type of time budget used (e.g., "max" or "median").
std::vector<MethodDefinition> make_time_constrained_methods(
    const vector<AlgorithmRunMetrics (*)(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)> &methods,
    const std::string& budget_label,
    const std::map<std::string, double>& budgets_by_problem,
    const double default_budget_seconds,
    const int verbosity_level,
    const map<string, double> hyperparameters = {}
    );

int main(int argc, char* argv[]) {
    try {
    const int VERBOSITY_LEVEL = 0; // 0 - no output, 1 - basic output, 2 - detailed output
    const int MAX_ITERS = 1000;
    const double TIME_BUDGET_SECONDS = 2*60.0;
    const char* DATA_DIR = "./QAP data/";
    string data_dir = DATA_DIR;
    string plots_dir = "./Figures";
    std::pair<int, int> fig_size{1700, 900};
    const int N_RUNS_PER_PROBLEM = 10;
    const int MAX_CORES = omp_get_max_threads();
    int n_runs_per_problem = N_RUNS_PER_PROBLEM;

    bool run_parallel = false;


    // parse command line arguments
    vector<string> args(argv + 1, argv + argc);
    if (argc > 1){
        bool retFlag;
        int retVal = parse_args(argv, args, n_runs_per_problem, run_parallel, data_dir, plots_dir, fig_size, retFlag);
        if (retFlag)
            return retVal;
    }

    string plots_output_dir = prepare_plots_output_dir(plots_dir);

    /*********************************** STEP 0: parallelization of runs of algorithms on problem instances using OpenMP ***********************************/
    const int N_CORES = min(MAX_CORES, n_runs_per_problem);

    omp_set_dynamic(0);
    if (run_parallel && N_CORES > 1 && n_runs_per_problem > 1)
        omp_set_num_threads(N_CORES);
    else
        omp_set_num_threads(1);
    cout << Colors::GREEN << "OpenMP max threads: " << omp_get_max_threads() << " (logical cores reported: " << omp_get_num_procs() << ")" << Colors::RESET << endl;

    set_use_cpu_time_clock(omp_get_max_threads() == 1);
    cout << Colors::GREEN << "Using " << (use_cpu_time_clock() ? "CPU time clock" : "wall clock") << " for measuring algorithm run times." << Colors::RESET << endl;
    cout << Colors::GREEN << "Timer resolution: " << Colors::RESET << get_time_resolution() << " seconds"  << endl;


    constexpr unsigned int GLOBAL_SEED = 234567890u;
    srand(GLOBAL_SEED);
    random::seed(GLOBAL_SEED);
    // srand(time(0));






    /*********************************** STEP 1: Loading problem names and assessing their difficulty ***********************************/
    set<string> set_problem_names_with_optimal_solutions {"esc16d","bur26h" , "esc32e",  "lipa80b","lipa40a"};
    set<string> set_problem_names_with_best_known_solutions  {"wil100"
                                                                , "tho150", "tai100b", "tai80b", "tai150b", "tai256c"
                                                                };
    vector<Problem<int>> problems_with_optimal_solutions = Problem<int>::load_problems(set_problem_names_with_optimal_solutions, data_dir, true);
    vector<Problem<int>> problems_with_best_known_solutions = Problem<int>::load_problems(set_problem_names_with_best_known_solutions, data_dir);
    vector<Problem<int>> problems = problems_with_optimal_solutions;
    problems.reserve(problems.size() + problems_with_best_known_solutions.size());
    problems.insert(problems.end(), problems_with_best_known_solutions.begin(), problems_with_best_known_solutions.end());

    map<string, Problem<int>> d_problems;
        for (const auto& problem : problems)
            d_problems[problem.get_name()] = problem;

    // sort problems by size
    std::sort(problems.begin(), problems.end(), 
                [](const Problem<int>& a, const Problem<int>& b) {return a.get_size() < b.get_size();});
    vector<int64_t> best_known_costs_sorted_by_problem_size;
    for (const auto& problem : problems)
        best_known_costs_sorted_by_problem_size.push_back(problem.get_best_cost());


    // Brief summary of each QAP instance, including the properties of the matrices and the best known solution, printed to the console and saved to a markdown report file for better readability and sharing. 
    //The markdown report file is created at `report_path`, and if a file already exists at that path, it is removed before creating the new report to ensure that the report contains only the information from the current run of the program.                                                           
    const char report_path[] = "./QAP data/Properties of the selected QAP instances.md";
    if (std::filesystem::remove(report_path)) 
        cout << Colors::GREEN << "Existing markdown report file removed successfully." << Colors::RESET << endl;
    else
        cout << Colors::YELLOW << "No existing markdown report file to remove or failed to remove. Continuing..." << Colors::RESET << endl;
        
    for (const auto& problem : problems) {
        problem.print(true,false, false);
    
        problem.print_markdown_report(report_path);
    }


    /********************************************************************************************************* */
    /********************************************Tasks**********************************************************/

    task2(problems, n_runs_per_problem, MAX_ITERS, TIME_BUDGET_SECONDS
        , 0// VERBOSITY_LEVEL
        ,plots_output_dir, fig_size);
 

    // omp_set_num_threads(30);
    // vector<Problem<int>> interesting_problems{d_problems["lipa80b"], d_problems["tai100b"]
    //         //,d_problems["tai256c"]// d_problems["tai80b"],// these 2 are less interesting
    //         //,d_problems["esc16d"]// this is very boring one
    //     };
    // sort(interesting_problems.begin(), interesting_problems.end(), [](const Problem<int>& a, const Problem<int>& b) {
    //     return a.get_size() < b.get_size();
    // });
    // task345(interesting_problems, 
    //         1000, MAX_ITERS, TIME_BUDGET_SECONDS, VERBOSITY_LEVEL, plots_output_dir, fig_size);


    return 0;
    } catch (const std::runtime_error& e) {
        std::cerr << Colors::RED << "Runtime error: " << Colors::RESET << e.what() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << Colors::RED << "Unhandled exception: " << Colors::RESET << e.what() << std::endl;
        return 1;
    }
}

/****************************************** End of main() *****************************************************************/
















const map<string, double> SA_hyperparameters  = {{"initial_acceptance_rate", 0.95},
        {"final_acceptance_rate", 0.001},
         {"max_non_improving_moves_factor", 10.0},
         {"initial_cooling_rate", 0.85},
         {"markov_chain_length_factor", 1.0}};




void task2(const std::vector<Problem<int>>& problems, 
            int n_runs_per_problem, int default_max_iters, float default_time_budget_seconds, 
            int verbosity_level,
            const std::string& plots_output_dir, const std::pair<int, int>& fig_size)
{
           
    /*********************************** STEP 2: Local search algorithms ***********************************/
    // solving the problems with different methods and collecting results for analysis and plotting
    double t = 0.0;
    clock_t start = clock();
    const std::vector<MethodDefinition> local_search_methods = {
                {"Heuristic",
                [](const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& config) {
                    return heuristic_local_search_qap(problem, p, config);
                },
                iter_cfg(default_max_iters, verbosity_level), "#11830080", "o"},
                {"Steepest LS",
                [](const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& config) {
                    return steepest_local_search_qap(problem, p, config);
                },
                iter_cfg(default_max_iters, verbosity_level), "#00438fc3", "s"},
                {"Greedy LS",
                [](const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& config) {
                    return greedy_local_search_qap(problem, p, config);
                },
                iter_cfg(default_max_iters, verbosity_level), "#68bbff80", "^"},
    };

    // Obtaining the results
    ExperimentResults results = collect_experiment_results(
        local_search_methods,
        problems,
        n_runs_per_problem
    );




    /*********************************** STEP 3: Determine time budgets and run random search ***********************************/    
    // Time budgets: MAX, MEDIAN, MEAN, defined by time taken by the local search methods on each problem instance, aggregated across the local search methods and runs by MAX, MEDIAN, MEAN, and sorted by OPTIMUM_PROXIMITY (the relative cost of the best known solution to the best solution found by the local search methods, averaged across the local search methods and runs for each problem instance) to ensure that the time budgets are more tailored to the difficulty of the problem instances and allow for better comparison of the performance of the random methods on different types of problem instances. The time budgets are determined based on the results obtained from running the local search methods on the problem instances, and are used to configure the random search and random walk methods to ensure that they have a fair amount of time to find good solutions while also allowing for meaningful comparisons between the methods.
    const std::map<std::string, double> max_time_budgets_by_problem =
        results.aggregate_by_problem("time", AggregationType::MAX);
    const std::map<std::string, double> median_time_budgets_by_problem =
        results.aggregate_by_problem("time", AggregationType::MEDIAN);
    const std::map<std::string, double> mean_time_budgets_by_problem =
        results.aggregate_by_problem("time", AggregationType::MEAN);

    // Mean budget
    // Heuristic contributes the least value
    // Mean budget should is somewhere between median and max, but closer to median
    // Should show resuts better than median, but lower than max. 
    // At the same time difference between median and max is neglectable, when plots are compared for median and max
    std::vector<MethodDefinition> random_methods = make_time_constrained_methods(vector<AlgorithmRunMetrics (*)(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)> {random_search_qap, random_walk_qap},
                                                                                    "mean",
                                                                                    mean_time_budgets_by_problem,
                                                                                    default_time_budget_seconds,
                                                                                    verbosity_level
                                                                                );
    std::vector<MethodDefinition> sa_methods =  make_time_constrained_methods(vector<AlgorithmRunMetrics (*)(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)> {simulated_annealing_qap, adaptive_simulated_annealing_qap},
                                                                                    "mean",
                                                                                    mean_time_budgets_by_problem,
                                                                                    default_time_budget_seconds,
                                                                                    0,
                                                                                    SA_hyperparameters
                                                                                );
    printf("\nTask2: Medium time budgets [s] per problem: ");
    for (auto [problem,budget]: mean_time_budgets_by_problem)
        printf("%s: %f\n", problem.c_str(), budget);

    // Obtaining results for random methods
    results.merge(collect_experiment_results(
        random_methods,
        problems,
        n_runs_per_problem
    ));
    // Obtaining results for random methods
    results.merge(collect_experiment_results(
        sa_methods,
        problems,
        n_runs_per_problem
    ));


    std::vector<MethodDefinition> all_methods = local_search_methods;
    all_methods.insert(all_methods.end(), random_methods.begin(), random_methods.end());
    all_methods.insert(all_methods.end(), sa_methods.begin(), sa_methods.end());

    clock_t end = clock();
    t += static_cast<double>(end - start) / CLOCKS_PER_SEC;
    printf("Time taken to run all methods on all problems for %d runs per problem: %.2f seconds\n", n_runs_per_problem, t);









    /*********************************** STEP 4: Plotting the results  ***********************************/
    map<string, double> norm_best_known_costs;
    for (const auto& problem : problems)
        norm_best_known_costs[problem.get_name()] = problem.get_best_norm_cost();

    
    // Part 2:
    //
    // ~dist(f(p), f(best_p))
    // Quality (primary quality metric is relative cost = (cost - best_cost) / best_cost):
    methods_boxplot(
        results, problems, all_methods,
        "cost_relative_quality",
        {
            .title = "Boxplot of relative cost quality by method and problem instance",
            .xy_labels = {"Problem instance", "Relative cost quality, lower is better"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
        }
    );
    // Quality (secondary quality metric - Normalized Cost = cost / frobenius_norms_product):
    methods_boxplot(
        results, problems, all_methods,
        "cos_quality",
        {
            .title = "Boxplot of normalized cost by method and problem instance",
            .guides = {{"Best known norm cost ", norm_best_known_costs}},
            .xy_labels = {"Problem instance", "Normalized cost, lower is better"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .draw_random_solution_reference = true,
            .legend_loc = "upper left"
        }
    );



    // Time
    methods_boxplot(
        results, problems, local_search_methods,
        "time",
        {
            .title = "Boxplot of runtime by method and problem instance",
            .sorting_criterion = SortingCriterion::OPTIMUM_PROXIMITY,
            .xy_labels = {"Problem instance", "Runtime (seconds)"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper left"
            // , .scale = {"", "log"}
        }
    );
    methods_boxplot(
        results, problems, local_search_methods,
        "time",
        {
            .title = "Boxplot of runtime by method and problem instance",
            .xy_labels = {"Problem instance", "Runtime (seconds)"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper left"
        }
    );
        methods_boxplot(
        results, problems, all_methods,
        "time",
        {
            .title = "Boxplot of runtime by method and problem instance",
            .xy_labels = {"Problem instance", "Runtime (seconds)"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper left"
            , .scale = {"", "linear"}
            , .connect_medians=true
        }
    );
    methods_boxplot(
        results, problems, all_methods,
        "time",
        {
            .title = "Boxplot of runtime by method and problem instance",
            .xy_labels = {"Problem instance", "Runtime (seconds)"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper left"
            , .scale = {"", "log"}
            , .connect_medians=true
        }
    );

    
    // Efficiency of algorithms
    //
    // Since algorithms stop at different times (the least time is taken by heuristic LS, then greedy LS, then steepest LS, and the most time is taken by random methods), it is important to compare the efficiency of algorithms in terms of the quality of solutions they find over time, rather than just the final quality of solutions they find at the end of their runs
    // This allows us to see how quickly algorithms improve their solutions and how efficiently they use their time budgets.
    // Thus time budgets must be comparable. Hence I considered several time budgets here:
    // - [default] mean time taken by local search methods as a balanced time budget, which all methods can meet. 

    // strict (minimal) time:
    // Strict budget is taken as MEDIAN running time of the heuristic local search, as it is the least time consuming method, and thus most random methods can meet this time budget, while still having some time to find better solutions than the initial solution. This allows for a more meaningful comparison of the performance of the random methods on different types of problem instances, as they are not too constrained by the time budget and can find good solutions, while still being able to show differences in performance between the methods.
    const std::map<std::string, double> strict_time_budgets_by_problem =
        results.aggregate_by_problem("Heuristic", "time", AggregationType::MEDIAN
        );
    efficiency_plots(strict_time_budgets_by_problem, default_time_budget_seconds, verbosity_level, problems, n_runs_per_problem, plots_output_dir, norm_best_known_costs, fig_size, " given minimal time budgets determined by the Heuristic local search");

    // Medium time - time budgets determined by MEDIAN time taken by GREEDY local search. Steepest local search is not given enough time in this setting 
    const std::map<std::string, double> medium_time_budgets_by_problem =
        results.aggregate_by_problem("Greedy LS", "time", AggregationType::MEDIAN);
    efficiency_plots(medium_time_budgets_by_problem, default_time_budget_seconds, verbosity_level, problems, n_runs_per_problem, plots_output_dir, norm_best_known_costs, fig_size, " given medium time budgets");

    // generous time - time budgets determined by MEDIAN time taken by STEEPEST local search. Steepest local search is not given enough time in this setting 
    const std::map<std::string, double> generous_time_budgets_by_problem =
        results.aggregate_by_problem("Steepest LS", "time", AggregationType::MEDIAN);
    efficiency_plots(generous_time_budgets_by_problem, default_time_budget_seconds, verbosity_level, problems, n_runs_per_problem, plots_output_dir, norm_best_known_costs, fig_size, " given generous time budgets");




    // Fig 8
    // G,S: average number of algorithm steps (step = changing the current solution)
    vector<MethodDefinition> GS_methods = {local_search_methods[1], local_search_methods[2]}; // Steepest LS and Greedy LS
    methods_boxplot(
        results, problems, GS_methods,
        "total_n_swaps",
        {
            .title = "Boxplot of total number of swaps by method and problem instance",
            .xy_labels = {"Problem instance", "Total number of swaps per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
        }
    );
    methods_boxplot(
        results, problems, GS_methods,
        "total_n_swaps",
        {
            .title = "Boxplot of total number of swaps by method and problem instance",
            .xy_labels = {"Problem instance", "Total number of swaps per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
            , .scale = {"", "log"}
            , .connect_medians = true
        }
    );
        vector<MethodDefinition> RWGSATS_methods (all_methods.begin()+4, all_methods.end()); // Steepest LS and Greedy LS
    methods_boxplot(
        results, problems, RWGSATS_methods,
        "total_n_swaps",
        {
            .title = "Boxplot of total number of swaps by method and problem instance",
            .xy_labels = {"Problem instance", "Total number of swaps per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
            , .scale = {"", "log"}
            , .connect_medians = true
        }
    );
    
    


    //Fig 9
    // G,S,RS,RW: average number of evaluated (i.e., visited – full or partial evaluation) solutions.
    vector<MethodDefinition> GSR_methods = {local_search_methods[1], local_search_methods[2], 
                                            random_methods[0], random_methods[1]}; // Steepest LS, Greedy LS, Random Search, Random Walk
    methods_boxplot(
        results, problems, GSR_methods,
        "total_n_eval_solutions",
        {
            .title = "Boxplot of number of evaluated solutions by method and problem instance",
            .xy_labels = {"Problem instance", "Number of evaluated solutions per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
        }
    );
    methods_boxplot(
        results, problems, GSR_methods,
        "total_n_eval_solutions",
        {
            .title = "Boxplot of number of evaluated solutions by method and problem instance",
            .xy_labels = {"Problem instance", "Number of evaluated solutions per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
            , .scale = {"", "log"}
            , .connect_medians = true
        }
    );

    vector<MethodDefinition> GSRSATS_methods (all_methods.begin()+1, all_methods.end()); // Steepest LS, Greedy LS, Random Search, Random Walk
    methods_boxplot(
        results, problems, GSRSATS_methods,
        "total_n_eval_solutions",
        {
            .title = "Boxplot of number of evaluated solutions by method and problem instance",
            .xy_labels = {"Problem instance", "Number of evaluated solutions per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
            , .scale = {"", "log"}
            , .connect_medians = true
        }
    );
    methods_boxplot(
        results, problems, GSRSATS_methods,
        "total_n_eval_solutions",
        {
            .title = "Boxplot of number of evaluated solutions by method and problem instance",
            .xy_labels = {"Problem instance", "Number of evaluated solutions per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
            , .scale = {"", "linear"}
            , .connect_medians = true
        }
    );

    //vector<MethodDefinition> GSR_methods = {local_search_methods[1], local_search_methods[2], 
    //                                        random_methods[0], random_methods[1]}; // Steepest LS, Greedy LS, Random Search, Random Walk
    methods_boxplot(
        results, problems, all_methods,
        "total_n_eval_solutions",
        {
            .title = "Boxplot of evaluated solutions by method and problem instance",
            .xy_labels = {"Problem instance", "Number of evaluated solutions per run"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
        }
    );






    // dist(p, best_p)
    //
    // G,S: average number of algorithm steps (step = changing the current solution)
    // Hamming distance (normalized): avg number of different elements between the found solution and the best known solution
    methods_boxplot(
        results, problems, all_methods,
        "hamming_distance",
        {
            .title = "Boxplot of normalized Hamming distance to the best known solution",
            .xy_labels = {"Problem instance", "Normalized Hamming distance"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "lower right"
        }
    );
    // cayley_distance (normalized): number of swaps between the found solution and the best known solution, normalized by problem size
    methods_boxplot(
        results, problems, all_methods,
        "cayley_distance",
        {
            .title = "Boxplot of normalized Cayley distance to the best known solution",
            .xy_labels = {"Problem instance", "Normalized Cayley distance"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "lower right"
        }
    );







    // Distribution of normalized angular quality of solutions found by different methods, by problem instance, sorted by optimum proximity and with guides for the normalized angular quality of the best known solutions
    methods_boxplot(
        results, problems, all_methods,
        "normalized_angular_quality",
        {
            .title = "Boxplot of normalized angular quality by method and problem instance",
            .sorting_criterion = SortingCriterion::OPTIMUM_PROXIMITY,
            // .y_limits = {0.0, 1.0},
            .guides = {{"Best solution", get_norm_angular_qualities_of_best_known_solutions(problems)}},
            .xy_labels = {"Problem instance", "Normalized angular quality, higher is better"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
        }
    );

    // Distribution of COS quality of solutions found by different methods, by problem instance, sorted by optimum proximity and with guides for the normalized angular quality of the best known solutions
    methods_boxplot(
        results, problems, all_methods,
        "cos_quality",
        {
            .title = "Boxplot of normalized cost by method and problem instance",
            .sorting_criterion = SortingCriterion::OPTIMUM_PROXIMITY,
            // .y_limits = {0.0, 1.0},
            .guides = {{"Best solution", get_cos_qualities_of_best_known_solutions(problems)}},
            .xy_labels = {"Problem instance", "Normalized cost, lower is better"},
            .figure_size = fig_size,
            .output_dir = plots_output_dir,
            .legend_loc = "upper right"
        }
    );
}

// plots efficiency graphs for the following algorithms:
// - `heuristic_local_search_qap`, `steepest_local_search_qap`, `greedy_local_search_qap`, `random_search_qap`, `random_walk_qap`
// - `simulated_annealing_qap`, `adaptive_simulated_annealing_qap` with the following hyperparameters: "initial_acceptance_rate"-> 0.95, "final_acceptance_rate"-> 0.01, "initial_cooling_rate" -> 0.9, "markov_chain_length_factor" -> 1.0, "max_non_improving_moves_factor" ->10.0
void efficiency_plots(const std::map<std::string, double> &time_budgets_by_problem, float default_time_budget_seconds, int verbosity_level, const std::vector<Problem<int>> &problems, int n_runs_per_problem, const std::string &plots_output_dir, std::map<std::string, double> &norm_best_known_costs, const std::pair<int, int> &fig_size, const std::string subtitle)
{
    vector<MethodDefinition> methods = make_time_constrained_methods(
        vector<AlgorithmRunMetrics (*)(const Problem<int> &, Permutation<int> &, const AlgorithmRunConfig &)>{heuristic_local_search_qap, steepest_local_search_qap, greedy_local_search_qap, random_search_qap, random_walk_qap},
        "", time_budgets_by_problem, default_time_budget_seconds, verbosity_level);
    ExperimentResults results = collect_experiment_results(
        methods, problems, n_runs_per_problem);
    // Simulated annealing:
    vector<MethodDefinition> sa_methods = make_time_constrained_methods(
        vector<AlgorithmRunMetrics (*)(const Problem<int> &, Permutation<int> &, const AlgorithmRunConfig &)
                >{simulated_annealing_qap
                    , adaptive_simulated_annealing_qap
                },
        "", time_budgets_by_problem, default_time_budget_seconds, 
        0,
        SA_hyperparameters
    );
    ExperimentResults sa_results = collect_experiment_results(
        sa_methods, problems, n_runs_per_problem);
    methods.insert(methods.end(), sa_methods.begin(), sa_methods.end());
    results.merge(sa_results);

    // strict time: rel_eff - relative efficiency [AUC] - the time-weighted average cost of the incumbent solution during the run, divided by the best known cost, minus 1. This metric captures how efficiently the algorithm improves the solution over time, with lower values indicating more efficient improvement.
    methods_boxplot(
        results, problems, methods,
        "rel_eff",
        {.title = "Boxplot of Relative Efficiency of solutions found by different methods"+subtitle+", by problem instance",
         .xy_labels = {"Problem instance", "Relative Efficiency [AUC], the lower the better"},
         .figure_size = fig_size,
         .output_dir = plots_output_dir,
         .legend_loc = "upper right"});
    // strict time: norm_eff - normalized efficiency [AUC] - the time-weighted average cost of the incumbent solution during the run, divided by the Frobenius product of the problem matrices, minus normalized best known cost. This metric captures how efficiently the algorithm improves the solution relative to the problem's scale, with lower values indicating more efficient improvement.
    methods_boxplot(
        results, problems, methods,
        "norm_eff",
        {.title = "Boxplot of Normalized Efficiency of solutions found by different methods"+subtitle+", by problem instance",
         .xy_labels = {"Problem instance", "Normalized Efficiency [AUC], the lower the better"},
         .figure_size = fig_size,
         .output_dir = plots_output_dir,
         .legend_loc = "upper right"});
    // Quality (primary quality metric is relative cost = (cost - best_cost) / best_cost):
    methods_boxplot(
        results, problems, methods,
        "cost_relative_quality",
        {.title = "Boxplot of Relative Cost of solutions found by different methods"+subtitle+", by problem instance",
         .xy_labels = {"Problem instance", "Relative Cost of solution, the lower the better"},
         .figure_size = fig_size,
         .output_dir = plots_output_dir,
         .legend_loc = "upper right"});
    // Quality (secondary quality metric - Normalized Cost = cost / frobenius_norms_product):
    methods_boxplot(
        results, problems, methods,
        "cos_quality",
        {.title = "Boxplot of Normalized Cost of solutions found by different methods"+subtitle+", by problem instance",
         .guides = {{"Best known norm cost ", norm_best_known_costs}},
         .xy_labels = {"Problem instance", "Normalized Cost of solution, the lower the better"},
         .figure_size = fig_size,
         .output_dir = plots_output_dir,
         .draw_random_solution_reference = true,
         .legend_loc = "upper left"});
}

void task345(const std::vector<Problem<int>>& problems, 
                int n_runs_per_problem, int default_max_iters, float default_time_budget_seconds, 
                int verbosity_level,
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size)
{
    double t = 0.0;
    clock_t start = clock();
    const std::vector<MethodDefinition> local_search_methods = {
                {"Steepest LS",
                [](const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& config) {
                    return steepest_local_search_qap(problem, p, config);
                },
                iter_cfg(default_max_iters, verbosity_level), "#00438fca", "s"},
                {"Greedy LS",
                [](const Problem<int>& problem, Permutation<int>& p, const AlgorithmRunConfig& config) {
                    return greedy_local_search_qap(problem, p, config);
                },
                iter_cfg(default_max_iters, verbosity_level), "#d664f664", "^"},
    };
    // Obtaining the results
    ExperimentResults results = collect_experiment_results(
        local_search_methods,
        problems,
        n_runs_per_problem
    );
    t = clock() - start;
    printf("Time taken to run %i iterations of %zu local search methods: %.2f seconds\n", n_runs_per_problem, local_search_methods.size(), t / CLOCKS_PER_SEC);
    
    task3(results, local_search_methods, problems, plots_output_dir, fig_size);
    task4(results, local_search_methods, problems, plots_output_dir, fig_size);
    task5(results, local_search_methods, problems, plots_output_dir, fig_size);

}


void task3(const ExperimentResults<>& results,  const std::vector<MethodDefinition>& methods,
                const std::vector<Problem<int>>& problems,            
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size)
{
    const std::vector<std::string> markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };
    int n_runs_per_problem = std::get<2>(results.get_dimensions());

    PlotConfig plot_cfg;
    plot_cfg.title = "Initial vs final normalized cost for Greedy LS and Steepest LS (" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_cfg.output_dir = plots_output_dir;
    plot_cfg.figure_size = fig_size;
    plot_cfg.xy_labels = {"Initial normalized cost", "Final normalized cost"};
    methods_scatterplot(results,
                        problems,
                        methods,
                        {"initial_cos_quality", "cos_quality"},
                        plot_cfg);

    plot_cfg.title = "Initial vs final relative cost quality for Greedy LS and Steepest LS (" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_cfg.xy_labels = {"Initial relative cost quality", "Final relative cost quality"};
    methods_scatterplot(results,
                        problems, methods,
                        {"initial_cost_relative_quality", "cost_relative_quality"},
                        plot_cfg);



    for (int i = 0; i < problems.size(); ++i) {
        plot_cfg.plot_marker = markers[i % markers.size()];
        plot_cfg.title = problems[i].get_name() + ": initial vs final relative cost quality (" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        plot_cfg.xy_labels = {"Initial relative cost quality", "Final relative cost quality"};
        methods_scatterplot(results,
                                {problems[i]}, methods,
                                {"initial_cost_relative_quality", "cost_relative_quality"},
                                plot_cfg);
        plot_cfg.title = problems[i].get_name() + ": initial vs final normalized cost (" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        plot_cfg.xy_labels = {"Initial normalized cost", "Final normalized cost"};
        methods_scatterplot(results,
                                {problems[i]},
                                methods,
                                {"initial_cos_quality", "cos_quality"},
                                plot_cfg);
    }
}

void task4(const ExperimentResults<>& results,  const std::vector<MethodDefinition>& methods,
                const std::vector<Problem<int>>& problems,            
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size)
{
    const std::vector<std::string> markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };
    int n_runs_per_problem = std::get<2>(results.get_dimensions());


    PlotConfig plot_cfg;
    plot_cfg.output_dir = plots_output_dir;
    plot_cfg.figure_size = fig_size;
    plot_cfg.xy_labels = {"Number of starts", "Relative cost quality"};
    plot_cfg.title = "Multi-start Greedy LS and Steepest LS: best and average relative cost quality vs number of starts\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_restarts_vs_quality(results, problems, methods,
                                    "cost_relative_quality", plot_cfg, 0 // using all available restarts
                         );
    plot_cfg.xy_labels = {"Number of starts", "Normalized cost"};
    plot_cfg.title = "Multi-start Greedy LS and Steepest LS: best and average normalized cost vs number of starts\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_restarts_vs_quality(results, problems, methods,
                                    "cos_quality", plot_cfg,0 // using all available restarts
                             );

    for (int i = 0; i < problems.size(); ++i) {
        plot_cfg.plot_marker = markers[i % markers.size()];
        plot_cfg.xy_labels = {"Number of starts", "Relative cost quality"};
        plot_cfg.title = problems[i].get_name() + ": best and average relative cost quality vs number of starts\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        plot_cfg.plot_linestyle = "--";
        plot_restarts_vs_quality(results, {problems[i]}, methods,
                                        "cost_relative_quality", plot_cfg, 0 // using all available restarts
                            );
        plot_cfg.plot_linestyle = ":";
        plot_cfg.xy_labels = {"Number of starts", "Normalized cost"};
        plot_cfg.title = problems[i].get_name() + ": best and average normalized cost vs number of starts\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        plot_restarts_vs_quality(results, {problems[i]}, methods,
                                        "cos_quality", plot_cfg,0 // using all available restarts
                                );
                                
    }

}


// Analysis of found local optima
void task5(const ExperimentResults<>& results,  const std::vector<MethodDefinition>& methods,
                const std::vector<Problem<int>>& problems,            
                const std::string& plots_output_dir, const std::pair<int, int>& fig_size)
{
    const std::vector<std::string> markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };
    const int n_runs_per_problem = std::get<2>(results.get_dimensions());

    PlotConfig plot_cfg;
    plot_cfg.output_dir = plots_output_dir;
    plot_cfg.figure_size = fig_size;
    
    
    
    plot_cfg.xy_labels = {"Cayley similarity", "Relative cost quality"};
    plot_cfg.title = "Local optima Cayley similarity vs relative cost quality for Greedy LS and Steepest LS\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_similarity_vs_quality(results, problems, methods, "cost_relative_quality",  plot_cfg);

        //// This plot is not very informative
        // plot_cfg.xy_labels = {"Normalized cost", "Cayley similarity"};
        // plot_cfg.title = "Local optima similarity vs normalized cost for Greedy LS and Steepest LS\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        // plot_similarity_vs_quality(results, problems, methods, "cos_quality", plot_cfg);



    plot_cfg.title = "Local optima Hamming similarity vs relative cost quality for Greedy LS and Steepest LS\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_cfg.plot_marker = "";
    plot_cfg.plot_linestyle = "";
    plot_cfg.y_limits = {};
    plot_cfg.xy_labels = {"Hamming similarity", "Relative cost quality"};
    plot_cfg.y_limits = {};
    methods_scatterplot(results, problems, methods, {"hamming_similarity_to_best_known", "cost_relative_quality"}, plot_cfg);

        //// Not very informative
        // plot_cfg.title = "Hamming distance vs normalized cost for Greedy LS and Steepest LS\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        // plot_cfg.xy_labels = {"Normalized Hamming distance", "Normalized cost"};
        // methods_scatterplot(results, problems, methods, {"hamming_distance", "cos_quality"}, plot_cfg);

    for (int i = 0; i < static_cast<int>(problems.size()); ++i) {
        plot_cfg.plot_marker = markers[i % markers.size()];
        plot_cfg.plot_linestyle = "--";
        plot_cfg.y_limits = {};

        plot_cfg.xy_labels = {"Cayley similarity", "Relative cost quality"};
        plot_cfg.title = problems[i].get_name() + ": local optima similarity vs relative cost quality\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        plot_similarity_vs_quality(results, {problems[i]}, methods, "cost_relative_quality", plot_cfg);

        // plot_cfg.plot_linestyle = ":";
        // plot_cfg.xy_labels = {"Normalized cost", "Cayley similarity"};
        // plot_cfg.title = problems[i].get_name() + ": local optima similarity vs normalized cost\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        // plot_similarity_vs_quality(results, {problems[i]}, methods, "cos_quality", plot_cfg);

        plot_cfg.plot_linestyle = "";
        plot_cfg.y_limits = {};
        plot_cfg.xy_labels = {"Hamming similarity", "Relative cost quality"};
        plot_cfg.title = problems[i].get_name() + ": local optima Hamming similarity vs relative cost quality\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        methods_scatterplot(results, {problems[i]}, methods, {"hamming_similarity_to_best_known", "cost_relative_quality"}, plot_cfg); 

        // plot_cfg.xy_labels = {"Normalized Hamming distance", "Normalized cost"};
        // plot_cfg.title = problems[i].get_name() + ": hamming distance vs normalized cost\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
        // methods_scatterplot(results, {problems[i]}, methods, {"hamming_distance", "cos_quality"}, plot_cfg);
    }
    


    // THE FOLLOWING FIGURE SHOULD BE SAVED MANUALLY
    plot_cfg.figure_size = {fig_size.first * 1.5, fig_size.second / 1.75};
    plot_cfg.plot_marker = "";
    plot_cfg.plot_linestyle = "";
    plot_cfg.title = "Heatmap of position-match Pearson's correlations with the quality of found solutions for Greedy LS and Steepest LS\n(" + std::to_string(n_runs_per_problem) + " runs per problem instance)";
    plot_position_match_quality_heatmaps(results, problems, methods, plot_cfg);
}








// @brief Makes `AlgorithmRunConfig` with time restriction for a given `Problem` instance.
// @param budgets_by_problem `map<string, double>` of max time budgets [seconds] per problem name.
// @param default_budget_seconds used when no budfet is found for the `problem`.
// @param hyperparameters are optional hyperparameters (required for Simulated Annealing and Tabu Search algorithms)
// @param min_time_budget (default 0.01) defines minimal possible time for a run. If zero is provided, this parameter is not taken into consideration.
std::function<AlgorithmRunConfig(const Problem<int>&)> make_time_budget_resolver(
    const std::map<std::string, double>& budgets_by_problem,
    const double default_budget_seconds,
    const int verbosity_level,
    const map<string, double> hyperparameters,
    const double min_time_budget)
{
    return [budgets_by_problem, default_budget_seconds, verbosity_level, hyperparameters, min_time_budget](const Problem<int>& problem) {
        const auto it = budgets_by_problem.find(problem.get_name());
        double resolved_budget = (it != budgets_by_problem.end()) ? it->second : default_budget_seconds;
        if (min_time_budget>0)
            resolved_budget = (resolved_budget<min_time_budget)? min_time_budget: resolved_budget;
        return time_cfg(resolved_budget, verbosity_level, hyperparameters);
    };
}
MethodDefinition make_time_constrained_method_definition(
    const std::string& display_name,
    const MethodFunction& method,
    const std::map<std::string, double>& budgets_by_problem,
    const double default_budget_seconds,
    const int verbosity_level,
    const map<string, double> hyperparameters,
    const std::string& color,
    const std::string& marker)
{
    return {
        display_name,
        method,
        time_cfg(default_budget_seconds, verbosity_level),
        color,
        marker,
        make_time_budget_resolver(budgets_by_problem, default_budget_seconds, verbosity_level, hyperparameters)
    };
}

// Creates method definitions for random search and random walk methods with time budgets determined by the provided `budgets_by_problem` map, `default_budget_seconds`, and `verbosity_level`. The display names of the methods include the `budget_label` to indicate the type of time budget used (e.g., "max" or "median").
std::vector<MethodDefinition> make_time_constrained_methods(
    const vector<AlgorithmRunMetrics (*)(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)> &methods,

    const std::string& budget_label,
    const std::map<std::string, double>& budgets_by_problem,

    const double default_budget_seconds,
    const int verbosity_level,
    const map<string, double> hyperparameters
)
{
    std::vector<MethodDefinition> method_definitions;
    for (const auto& method : methods) {
        std::string method_name;
        std::string method_color;
        std::string method_marker;
        if (method == &heuristic_local_search_qap) {
            method_name = "Heuristic"; method_color = "#11830080"; method_marker = "o";
        } else if (method == &steepest_local_search_qap) {
            method_name = "Steepest LS"; method_color = "#00438fbb"; method_marker = "s";
        } else if (method == &greedy_local_search_qap) {
            method_name = "Greedy LS"; method_color = "#68bbff80"; method_marker = "^";
        } else if (method == &random_search_qap) {
            method_name = "Random Search"; method_color = "#e8170080"; method_marker = "D";
        } else if (method == &random_walk_qap) {
            method_name = "Random Walk"; method_color = "#ff880080"; method_marker = "x";
        } else if (method == static_cast<AlgorithmRunMetrics (*)(const Problem<int>&, Permutation<int>&, const AlgorithmRunConfig&)>(&simulated_annealing_qap)) {
            method_name = "Simulated Annealing with geometric schedule"; method_color = "#e800cd80"; method_marker = "8";
        } else if (method == &adaptive_simulated_annealing_qap) {
            method_name = "Simulated Annealing with Lam schedule"; method_color = "#6f00ff80"; method_marker = "p";
        } else {
            method_name = "Unknown Method"; method_color = ""; method_marker = "";
        }

        method_definitions.push_back(make_time_constrained_method_definition(
            method_name + (budget_label.length()? (" (" + budget_label + " time)"): "" ),
            [method](const Problem<int>& problem, Permutation<int>& permutation, const AlgorithmRunConfig& config) {
                return method(problem, permutation, config);
            },
            budgets_by_problem,
            default_budget_seconds,
            verbosity_level,
            hyperparameters,
            method_color,
            method_marker
        ));
    }
    return method_definitions;
}







int parse_args(char *argv[], std::vector<std::string> &args, int &N_RUNS_PER_PROBLEM, bool &RUN_PARALLEL, std::string &data_dir, std::string &plots_dir, std::pair<int, int> &fig_size, bool &retFlag)
{
    retFlag = true;
    string arg1(argv[1]);
    if (arg1 == "--help")
    {
        cout << "Usage: " << argv[0] << " [--dir <data_directory>] [--plots-dir <plots_directory>] [--fig-size <width> <height>] [--runs-per-problem <n>] [--no-parallel]" << endl;
        cout << "If --dir is not provided, the program will look for data files in the default directory './QAP data/'." << endl;
        cout << "If --plots-dir is not provided, plots will be saved to './Figures/Run N/'." << endl;
        cout << "If --fig-size is not provided, the default figure size from main is used." << endl;
        return 0;
    }

    if (find(args.begin(), args.end(), "--runs-per-problem") != args.end())
    {
        auto it = find(args.begin(), args.end(), "--runs-per-problem");
        if (it != args.end() && it + 1 != args.end())
        {
            N_RUNS_PER_PROBLEM = stoi(*(it + 1));
            cout << "Number of runs per problem set to: " << N_RUNS_PER_PROBLEM << endl;
        }
        else
        {
            cerr << Colors::YELLOW << " WARNING: --runs-per-problem flag provided without a valid integer value. Using default value: " << N_RUNS_PER_PROBLEM << Colors::RESET << endl;
        }
    }
    if (find(args.begin(), args.end(), "--no-parallel") != args.end())
    {
        RUN_PARALLEL = false;
        cout << "Parallel execution disabled. Running in sequential mode." << endl;
    }

    // assigning data directory from command line argument if provided, or default
    if (find(args.begin(), args.end(), "--dir") != args.end())
    {
        auto it = find(args.begin(), args.end(), "--dir");
        if (it != args.end() && it + 1 != args.end())
        {
            data_dir = *(it + 1);
            cout << "Data directory set to: " << data_dir << endl;
        }
        else
            cerr << Colors::YELLOW << " WARNING: --dir flag provided without a valid directory path. Using default directory: './QAP data/'." << Colors::RESET << endl;
    }

    if (find(args.begin(), args.end(), "--plots-dir") != args.end())
    {
        auto it = find(args.begin(), args.end(), "--plots-dir");
        if (it != args.end() && it + 1 != args.end())
        {
            plots_dir = *(it + 1);
            cout << "Plots base directory set to: " << plots_dir << endl;
        }
        else
            cerr << Colors::YELLOW << " WARNING: --plots-dir flag provided without a valid directory path. Using default: './Figures'." << Colors::RESET << endl;
    }


    if (find(args.begin(), args.end(), "--fig-size") != args.end())
    {
        auto it = find(args.begin(), args.end(), "--fig-size");
        if (it != args.end() && it + 1 != args.end())
        {
            // Preferred style: --fig-size <width> <height>
            if (it + 2 != args.end()) {
                try {
                    const int width = std::stoi(*(it + 1));
                    const int height = std::stoi(*(it + 2));
                    if (width > 0 && height > 0) {
                        fig_size = {width, height};
                        cout << "Figure size set to: " << width << "x" << height << endl;
                    } else
                        cerr << Colors::YELLOW << " WARNING: --fig-size values must be positive. Keeping current figure size: " << fig_size.first << "x" << fig_size.second << "." << Colors::RESET << endl;
                }
                catch (...) {
                    // Backward-compatible fallback: --fig-size <width>x<height>
                    goto x_style_handling;
                }
            } else {
                x_style_handling:
                const std::string value = *(it + 1);
                const size_t sep_pos = value.find('x');
                if (sep_pos != std::string::npos && sep_pos > 0 && sep_pos + 1 < value.size()) {
                    try {
                        const int width = std::stoi(value.substr(0, sep_pos));
                        const int height = std::stoi(value.substr(sep_pos + 1));
                        if (width > 0 && height > 0) {
                            fig_size = {width, height};
                            cout << "Figure size set to: " << width << "x" << height << endl;
                        } else
                            cerr << Colors::YELLOW << " WARNING: --fig-size values must be positive. Keeping current figure size: " << fig_size.first << "x" << fig_size.second << "." << Colors::RESET << endl;
                    }
                    catch (...) {
                        cerr << Colors::YELLOW << " WARNING: Invalid --fig-size format. Use either <width> <height> or <width>x<height>. Keeping current figure size: " << fig_size.first << "x" << fig_size.second << "." << Colors::RESET << endl;
                    }
                } else
                    cerr << Colors::YELLOW << " WARNING: --fig-size expects two integers. Keeping current figure size: " << fig_size.first << "x" << fig_size.second << "." << Colors::RESET << endl;
            }
        }
        else
            cerr << Colors::YELLOW << " WARNING: --fig-size flag provided without a value. Keeping current figure size: " << fig_size.first << "x" << fig_size.second << "." << Colors::RESET << endl;
    }
    retFlag = false;
    return {};
}