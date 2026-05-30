// plotting.cpp
// Plotting and plotting-specific helper functions split out from statistics.cpp.
// This file expects statistics types/functions to be available in the translation unit
// (for the current project layout, include this file after statistics.cpp in tasks1.cpp).


#include <map>
#include <string>
#include <vector>
#include <sstream>
#include <atomic>
#include "statistics.cpp"


    // rearranged type for plotting: (problem:{statistic_name: [values for each run of the method on the problem instance]})
    template <typename T=double>
    using PlottingStatistics = std::map<std::string, std::vector<std::vector<T>>>;
    // rearranged type for plotting: (statistic_name:{problem: [values for each run of the method on the problem instance]})
    template <typename T=double>
    using PlottingStatisticsByProblem = std::map<std::string, std::map<std::string, std::vector<T>>>;
    template <typename T=double>
    using MethodsPlottingStatisticsByProblem = std::map<std::string, PlottingStatisticsByProblem<T>>;


// Structure to hold configuration options for plotting functions, with default values provided for all options. This allows users to specify only the options they want to customize while using sensible defaults for the rest.
// @param title  the title of the plot
// @param sorting_criterion  the criterion used to sort the problems on the x-axis (e.g. `SortingCriterion::SIZE` (default), `SortingCriterion::OPTIMUM_PROXIMITY`)
// @param y_limits  the limits for the y-axis (by default is empty - `{}`, automatic limits will be used)
// @param guides  guides for the plot (by default is empty - `{}`, no guides will be used). For example, this can be used to add horizontal lines indicating the best known solution cost for each problem instance, or other reference values. The map is structured as: problem_name -> guide_name -> guide_value, where guide_value is the y-value at which the guide line will be drawn for the corresponding problem instance.
// @param xy_labels  the labels for the x and y axes (by default is empty - `{}`, no labels will be shown)
// @param figure_size  the size of the figure in pixels (by default is {2000, 1000})
// @param output_dir  the directory where the generated plot will be saved (by default is empty - `""`, the plot will not be saved)
// @param draw_random_solution_reference  whether to draw a reference line for a random solution (by default is false)
// @param legend_loc  the location of the legend (by default is "best")
// @param font_size  the font size for the plot (by default is 11)
// @param plot_marker  the marker style for the plot (by default is empty, different markers will be used)
// @param plot_linestyle  the linestyle for the plot (by default is empty, different linestyles will be used)
// @param scale pair of scales for `x` and `y` axis (by default is empty. Possible options for each axis are: 'linear' (default), 'log', 'asinh', 'symlog', or 'logit')
// @param connect_medians connects series of medians across different problems with a polygonal curve, `false` by default
// @param img_ext - extension in which the figure will be saved. Common values: `".svg"`, `".png"`
struct PlotConfig {
    std::string title = "Boxplot of statistics by method and problem instance";
    SortingCriterion sorting_criterion = SortingCriterion::SIZE;
    std::pair<double, double> y_limits = {};
    std::map<std::string, std::map<std::string, double>> guides = {};
    std::pair<std::string, std::string> xy_labels = {};
    std::pair<int, int> figure_size = {2000, 1000};
    std::string output_dir = "";
    bool draw_random_solution_reference = false;
    std::string legend_loc = "best";
    int font_size = 11;
    std::string plot_marker = "";// if empty, different markers will be used
    std::string plot_linestyle = "";// if empty, different linestyles will be used
    std::pair <std::string, std::string> scale ={};
    bool connect_medians = false;
    std::string img_ext = ".svg";
};


void methods_boxplot(const ExperimentResults<>& results,
                     std::vector<Problem<int>> problems, 
        const std::vector<MethodDefinition>& methods, 
        const std::string& statistic_name, 
        const PlotConfig& config =PlotConfig{}
    );










/****************************************************** Utilities ****************************************************************/


// Global variable to keep track of the next figure number for boxplots, to avoid overwriting figures when plotting multiple boxplots in the same program execution.                     
static std::atomic<long> g_next_boxplot_figure_number = 1;
// Helper function to set the size of the active figure in inches, given the desired size in pixels (assuming 100 DPI). This is used to ensure that the generated boxplots have a consistent and readable size regardless of the display settings.
static void set_active_figure_size(int width_px, int height_px)
{
    auto& interp = matplotlibcpp::detail::_interpreter::get();

    PyObject* ax = PyObject_CallObject(interp.s_python_function_gca, interp.s_python_empty_tuple);
    if (!ax) {
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: gca() failed while resizing figure; using backend default size.\n");
        return;
    }

    PyObject* fig = PyObject_GetAttrString(ax, "figure");
    if (!fig) {
        Py_DECREF(ax);
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: active figure unavailable while resizing; using backend default size.\n");
        return;
    }

    PyObject* set_size_inches = PyObject_GetAttrString(fig, "set_size_inches");
    if (!set_size_inches) {
        Py_DECREF(fig);
        Py_DECREF(ax);
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: set_size_inches unavailable; using backend default size.\n");
        return;
    }

    PyObject* args = PyTuple_New(2);
    PyTuple_SetItem(args, 0, PyFloat_FromDouble(static_cast<double>(width_px) / 100.0));
    PyTuple_SetItem(args, 1, PyFloat_FromDouble(static_cast<double>(height_px) / 100.0));

    PyObject* res = PyObject_CallObject(set_size_inches, args);

    Py_DECREF(args);
    Py_DECREF(set_size_inches);
    Py_DECREF(fig);
    Py_DECREF(ax);

    if (!res) {
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: set_size_inches() call failed; using backend default size.\n");
        return;
    }
    Py_DECREF(res);
}


// Utility: lighten or darken a hex color by a factor (0.0 = black, 1.0 = original, >1.0 = lighter)
static std::string adjust_color_brightness(const std::string& hex, double factor) {
    if (hex.empty() || hex[0] != '#' || (hex.size() != 7 && hex.size() != 9)) return hex;
    int r = std::stoi(hex.substr(1,2), nullptr, 16);
    int g = std::stoi(hex.substr(3,2), nullptr, 16);
    int b = std::stoi(hex.substr(5,2), nullptr, 16);
    r = std::min(255, std::max(0, static_cast<int>(r * factor)));
    g = std::min(255, std::max(0, static_cast<int>(g * factor)));
    b = std::min(255, std::max(0, static_cast<int>(b * factor)));
    std::ostringstream oss;
    oss << "#";
    oss << std::hex;
    if (r < 16) oss << '0'; oss << r;
    if (g < 16) oss << '0'; oss << g;
    if (b < 16) oss << '0'; oss << b;
    if (hex.size() == 9) oss << hex.substr(7,2); // preserve alpha if present
    return oss.str();
}

// Utility: adjust hex color opacity by a factor (0.0 = invisible, 1.0 = original). By default 0.5.
static std::string adjust_color_opacity(const std::string&hex_color, double factor=0.5){
    if (0.0>factor || factor >1.0)
        throw std::invalid_argument("Adjusting color requires a valid factor.");
    return (hex_color.size() < 8) ? (hex_color + std::format("{:x}", int(round(255*factor)))) : hex_color.substr(0, hex_color.size() - 2) + std::format("{:x}", int(std::stoul(hex_color.substr(hex_color.size() - 2, 2), nullptr, 16)*factor)); // add 50% opacity to the color
}
// Save the current figure using global figure counter `g_next_boxplot_figure_number`
inline void save_figure(const std::string& output_dir, std::string img_ext=".svg") {
    const long figure_number = g_next_boxplot_figure_number - 1;
    const std::string filename = "Figure_" + std::to_string(figure_number) + img_ext;
    const char sep = (output_dir.back() == '/' || output_dir.back() == '\\') ? '\0' : '/';
    const std::string full_path = sep == '\0' ? output_dir + filename : output_dir + sep + filename;
    plt::save(full_path);
}
// @brief Save the current figure using global figure conuter `g_next_boxplot_figure_number`.
// Expects `plot_config.output_dir` and `plot_config.img_ext` to be provided
inline void save_figure(const PlotConfig plot_config){save_figure(plot_config.output_dir, plot_config.img_ext);}

// Allocate a Run N subfolder under plots_dir for this execution.
std::string prepare_plots_output_dir(const std::string& plots_dir)
{
    namespace fs = std::filesystem;
    std::string plots_output_dir;
    {
        fs::path base(plots_dir);
        int run_index = 0;
        while (fs::exists(base / ("Run " + std::to_string(run_index)))) {
            ++run_index;
        }
        fs::path run_folder = base / ("Run " + std::to_string(run_index));
        fs::create_directories(run_folder);
        plots_output_dir = run_folder.string();
        std::cout << "Plots will be saved to: " << plots_output_dir << std::endl;
    }
    return plots_output_dir;
}

// String utility: replace underscores with spaces
static std::string replace_underscores(const std::string& str) {
    std::string result = str;
    std::replace(result.begin(), result.end(), '_', ' ');
    return result;
}

// String utility: capitalize first letter
static std::string capitalize(const std::string& str) {
    if (str.empty()) return str;
    std::string result = str;
    result[0] = std::toupper(result[0]);
    return result;
}




/*************************************************************************************************************/























///////////////////////// Aggregating statistics (max, median, etc.) for plotting /////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Ordered list of best known costs for the problems, to be used for plotting reference lines on the plots of cost and quality statistics
std::map<std::string, double> get_best_costs(const std::vector<Problem<int>>& problems)
{
    std::map<std::string, double> best_costs;
    for (const auto& problem : problems)
        best_costs[problem.get_name()] = problem.get_best_cost();
    return best_costs;
}

// Ordered list of cosine qualities of the best known solutions for the problems, to be used for plotting reference lines on the plots of quality statistics
std::map<std::string, double> get_cos_qualities_of_best_known_solutions(const std::vector<Problem<int>>& problems)
{
    std::map<std::string, double> cos_qualities;
    for (const auto& problem : problems) {
        const auto& name = problem.get_name();
        const auto& matrices = problem.get_matrices();
        const auto best_cost = problem.get_best_cost();
        cos_qualities[name] = cos_quality_of_solution(best_cost, matrices.first, matrices.second);
    }
    return cos_qualities;
}

// Ordered list of normalized angular qualities of the best known solutions for the problems, to be used for plotting reference lines on the plots of quality statistics
std::map<std::string, double> get_norm_angular_qualities_of_best_known_solutions(const std::vector<Problem<int>>& problems)
{
    std::map<std::string, double> norm_ang_qualities;
    for (const auto& problem : problems) {
        const auto& name = problem.get_name();
        const auto& matrices = problem.get_matrices();
        const auto best_cost = problem.get_best_cost();
        norm_ang_qualities[name] = normalized_angle_quality_of_solution(best_cost, matrices.first, matrices.second);
    }
    return norm_ang_qualities;
}



////////////////////////// Functions Rearranging statistics for plotting /////////////////////////////////////////////////////////////////////////////////////////////////////////////

static PlottingStatistics<> get_statistics_for_plotting(const ProblemsRunsStatistics<>& problems_runs_statistics,
                                               SortingCriterion sorting_criterion)
{
    PlottingStatistics<> statistics_for_plotting;
    for (const auto& [problem, stats] : problems_runs_statistics)
        for (const auto& [name, values] : stats.data)
            statistics_for_plotting[name].push_back(values);
    return statistics_for_plotting;
}

static PlottingStatisticsByProblem<>
    get_statistics_for_plotting_by_problem(const ProblemsRunsStatistics<>& problems_runs_statistics)
{
    PlottingStatisticsByProblem<> statistics_for_plotting;
    for (const auto& [problem_name, stats] : problems_runs_statistics)
        for (const auto& [name, values] : stats.data)
            statistics_for_plotting[name][problem_name] = values;
    return statistics_for_plotting;
}

// Converts the runs statistics for multiple methods and problems into a format suitable for plotting, where the statistics are organized by method name, problem instance, and statistic type.
static MethodsPlottingStatisticsByProblem<>
    get_methods_statistics_for_plotting_by_problem(const MethodsProblemsRunsStatistics<>& methods_runs_statistics)
{
    MethodsPlottingStatisticsByProblem<> methods_statistics;

    for (const auto& [method_name, problems_runs_statistics] : methods_runs_statistics) {
        methods_statistics[method_name] = get_statistics_for_plotting_by_problem(problems_runs_statistics);
    }

    return methods_statistics;
}

template <typename T>
MethodsPlottingStatisticsByProblem<T> ExperimentResults<T>::to_plotting_statistics_by_problem() const
{
    return get_methods_statistics_for_plotting_by_problem(methods_runs_statistics_);
}



////////////////////////// Plot functions for visualizing the statistics, using matplotlib-cpp library /////////////////////////////////////////////////////////////

// performance of a method on a set of problems
void forest_plot(const std::map<std::string, std::tuple<std::vector<std::tuple<double, double>>,
                                std::vector<int>,
                                std::vector<std::tuple<double, double, double>>,
                                std::vector<double>
                                >
                >& problems_runs_statistics,
                PlotConfig config)
{
    // implementation of the forest plot using matplotlib-cpp library
}

// forest plot of an algorithm on a set of problems (forest plot) for one of statistics (e.g. cost, quality, distance from best known solution) for each problem, with error bars representing the variability of the statistics across multiple runs of the method on the same problem
// `boxplot_data` is data to be plotted along horizontal axis, on which `problems` are sorted by `sorting_criterion`.
void boxplot(std::vector<std::vector<double>>& boxplot_data,
             std::vector<Problem<int>> problems,
             PlotConfig config
             //std::string title = "Boxplot of costs relative to best known solution by problem instance",
            )
{
    if (boxplot_data.empty() || problems.empty()) {
        return;
    }

    sort_data(boxplot_data, problems, config.sorting_criterion);
    printf("Stats size per problem: %zu\n", boxplot_data.size());

    auto x_labels = std::vector<std::string>();
    x_labels.reserve(problems.size());
    for (const auto& problem : problems) {
        x_labels.push_back(problem.get_name());
    }

    std::vector<double> x_coords_jitter(boxplot_data[0].size());

    plt::figure(g_next_boxplot_figure_number++);
    set_active_figure_size(1200, 780);
    plt::boxplot(boxplot_data, x_labels);

    for (size_t i = 0; i < x_labels.size(); i++) {
        for (size_t j = 0; j < x_coords_jitter.size(); j++) {
            x_coords_jitter[j] = i + 1 +  (double)(rand() % 10) / 200.; // boxplot positions are 1-based in matplotlib
        }
        plt::scatter(x_coords_jitter, boxplot_data[i], 20); // add jitter to the x-coordinates of the points to avoid overlap, and plot the points on top of the boxplot
    }
    //plt::xticks(x_positions, x_labels);
    plt::xlabel("QAP problem instance");
    if (config.y_limits.first != config.y_limits.second) {
        plt::ylim(config.y_limits.first, config.y_limits.second);
    }
    plt::title(config.title);
    if (!config.output_dir.empty())
        save_figure(config);
    plt::show();
}









// Boxplot comparing the performance of multiple methods on multiple problem instances, where the x-axis represents the problem instances (grouped by problem), and the y-axis represents the values of a chosen statistic (e.g. cost, quality, distance from best known solution) for each method on each problem instance.
// Each box in the boxplot represents the distribution of the chosen statistic across multiple runs of a method on a specific problem instance, allowing for a visual comparison of the methods' performance and variability on each problem. The function also allows for sorting the problems along the x-axis based on different criteria (e.g. by size or difficulty) to reveal trends in how the methods perform across different types of problems.
//
// The following statistics, defined in the `statistics.cpp` and `algorithms.cpp` modules, are available for plotting:
//
// 1. 'hamming_distance', 'cayley_distance' - distance of the solution found by the method from the best known solution, measured in Hamming and Cayley distances, respectively. Normalized by problem size, these statistics can show how close the method's solutions are to the best known solution in terms of these distances, which can provide insights into the landscape geometry and the method's ability to navigate it.
//
// 2. 'cost' - cost of the solution found by the method
//
// 3. 'cost_relative_quality', 'cos_quality', 'normalized_angular_quality', 'relative_angular_quality' - quality of the solution found by the method
//
// 4. 'time' - time taken by the method to find the solution
//
// 5. 'total_n_swaps', 'total_n_eval_solutions' - measures of the method's search effort, which can be used to analyze the efficiency of the method in exploring the solution space.
//
// 6. 'rel_eff', 'norm_eff' - measures of the method's efficiency in finding good solutions relative to the search effort, which can provide insights into the method's ability to effectively navigate the solution space and find high-quality solutions with less effort.            
//
// #### Most useful config
// @param statistic_name the name of the statistic to be plotted, which should be one of the keys in the PlottingStatisticsByProblem structure.
// @param sorting_criterion (`SIZE`, `OPTIMUM_PROXIMITY`, or `NONE`) the criterion by which the problems should be sorted along the x-axis of the plot, which can be by problem size, optimum proximity, or left unsorted (original order). Sorting by optimum proximity can help reveal trends in how the method's performance varies with landscape geometry, while sorting by size can show how performance scales with problem size. The choice of sorting criterion can affect the interpretability of the plot and should be chosen based on the specific insights one wants to gain from the visualization.
// @param y_limits a pair of doubles specifying the limits of the y-axis for the plot. If the first and second values are equal or default value (`std::pair<double, double>()`) is used, the y-axis limits will be automatically determined based on the data being plotted.
// @param aggregated_values_for_statistic contains a map <label, map <problem names,  aggregated values (e.g. max, mean, median) for the statistic being plotted>>, which can be used to add reference lines to the plot for comparison. For example, if plotting cost statistics, the aggregated values could be the best known costs for each problem instance, allowing for a visual comparison of the methods' performance against the best known solutions.
// @param xy_labels a pair of strings specifying the labels for the x and y axes of the plot. If not provided, the label "QAP problem instances" will be used for x-axis and a label corresponding to the statistic name will be used for y-axis.
void methods_boxplot(const ExperimentResults<>& results,
                     std::vector<Problem<int>> problems, 
        const std::vector<MethodDefinition>& methods, 
        const std::string& statistic_name, 
        const PlotConfig& config)
{
    if (methods.empty() || problems.empty()) {
        return;
    }

    const auto methods_statistics = results.to_plotting_statistics_by_problem();

    const bool has_guides = !config.guides.empty();

    sort_problems(problems, config.sorting_criterion);

    const std::vector<std::string> fallback_colors = { "#1f76b47e", "#d6272777", "#2ca02c75", "#ff7e0e76", "#9367bd7b", "#8c564b70", "#e377c375", "#7f7f7f6e", "#bdbd227a", "#17bdcf72" };
    const std::vector<std::string> fallback_markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };
    std::vector<std::string> colors (methods.size());
    std::vector<std::string> markers (methods.size());

    for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
        colors[method_index] = methods[method_index].color.empty() ? fallback_colors[method_index % fallback_colors.size()] : methods[method_index].color;
        markers[method_index] = methods[method_index].marker.empty() ? fallback_markers[method_index % fallback_markers.size()]: methods[method_index].marker;
    }


    std::vector<std::vector<double>> grouped_boxplot_data;
    std::vector<std::string> x_labels;//sorted by problem and method, e.g. ("Method A", "Method B") for problem 1, ("Method A", "Method B"), ... for problems 2, ...
    std::vector<double> problem_tick_positions;
    std::vector<std::string> problem_tick_labels;
    std::vector<double> group_separator_positions;
    std::vector<std::vector<double>> scatter_x(methods.size());
    std::vector<std::vector<double>> scatter_y(methods.size());
    std::vector<std::vector<double>> methods_x_positions(methods.size()); // will be a container of size |methods| x |problems|

    grouped_boxplot_data.reserve(problems.size() * methods.size());
    x_labels.reserve(problems.size() * methods.size());
    problem_tick_positions.reserve(problems.size());
    problem_tick_labels.reserve(problems.size());


    for (const auto& problem : problems) {
        const std::string problem_name = problem.get_name();
        const std::string display_name = problem_name + (problem.is_flat_problem() ? "\n (flat problem)" : "");
        const size_t group_start = grouped_boxplot_data.size() + 1;
        size_t group_boxes = 0;

        for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
            const auto& method = methods[method_index];
            auto method_it = methods_statistics.find(method.name);
            if (method_it == methods_statistics.end()) {
                continue;
            }

            auto statistic_it = method_it->second.find(statistic_name);
            if (statistic_it == method_it->second.end()) {
                continue;
            }

            auto problem_it = statistic_it->second.find(problem_name);
            if (problem_it == statistic_it->second.end()) {
                continue;
            }

            const auto& series = problem_it->second;
            grouped_boxplot_data.push_back(series);
            x_labels.push_back(method.name);
            ++group_boxes;

            const double base_x = static_cast<double>(grouped_boxplot_data.size());
            scatter_x[method_index].reserve(scatter_x[method_index].size() + series.size());
            scatter_y[method_index].reserve(scatter_y[method_index].size() + series.size());

            for (size_t i = 0; i < series.size(); ++i) {
                const double jitter = static_cast<double>(rand() % 9) / 100.0 - 0.04;
                scatter_x[method_index].push_back(base_x + jitter);
                scatter_y[method_index].push_back(series[i]);
            }
            methods_x_positions[method_index].push_back(base_x);
        }

        if (group_boxes > 0) {
            const double group_center = static_cast<double>(group_start) + (static_cast<double>(group_boxes) - 1.0) / 2.0;
            problem_tick_positions.push_back(group_center);
            problem_tick_labels.push_back(display_name);

            const double separator_x = static_cast<double>(group_start + group_boxes) - 0.5;
            group_separator_positions.push_back(separator_x);
        }
    }

    if (grouped_boxplot_data.empty()) {
        return;
    }

    // Size of the figure, font size
    matplotlibcpp::rcparams({{"font.size", std::to_string(config.font_size)}});
    plt::figure(g_next_boxplot_figure_number++);
    // instead of `plt::figure_size`, we need to set the size of the active figure after creating it, to ensure that the size is applied to the correct figure when plotting multiple boxplots in the same program execution
    set_active_figure_size(config.figure_size.first, config.figure_size.second);






    /*******************************************************************************************/ 
    /********************************** BOXPLOT ************************************************/
    plt::boxplot(grouped_boxplot_data, x_labels);

    /******************************************************************************************/



    // Secondary grouping cue: place ticks at group centers with problem labels.
    plt::xticks(problem_tick_positions, problem_tick_labels);
    // Draw subtle separators between problem groups while keeping box/scatter aligned.
    double plot_min = config.y_limits.first;
    double plot_max = config.y_limits.second;
    if (plot_min == plot_max) {
        bool initialized = false;
        for (const auto& series : grouped_boxplot_data) {
            for (double v : series) {
                if (!initialized) {
                    plot_min = v;
                    plot_max = v;
                    initialized = true;
                } else {
                    if (v < plot_min) plot_min = v;
                    if (v > plot_max) plot_max = v;
                }
            }
        }
        if (plot_min == plot_max) {
            plot_min -= 0.1;
            plot_max += 0.1;
        }
    }

    // Draw vertical separators between problem groups.
    for (size_t i = 0; i + 1 < group_separator_positions.size(); ++i) {
        const double x = group_separator_positions[i];
        plt::plot(std::vector<double>{x, x},
                  std::vector<double>{plot_min, plot_max},
                  {{"color", "#d0d0d0"}, {"linestyle", "--"}, {"linewidth", "0.8"}});
    }

    // Draw horizontal lines for best known values of the statistic for each problem, if provided, using dashed lines in a light color to indicate they are reference values.
    // If the problem is a flat problem, use a red dashed line to indicate that the best known solution is not unique and the reference value may be less meaningful.
    if (has_guides) {
        for (const auto& [aggregated_stats_label, aggregated_stats_vals] : config.guides) {
            bool regular_label_added = false;
            bool flat_label_added = false;
            bool optimal_label_added = false;

            for (size_t i = 0; i < problem_tick_positions.size(); ++i) {
                const std::string& problem_name = problems[i].get_name();
                const auto guide_value_it = aggregated_stats_vals.find(problem_name);
                if (guide_value_it == aggregated_stats_vals.end()) {
                    continue;
                }

                const bool is_flat_problem = problems[i].is_flat_problem();
                const double y_val = guide_value_it->second;
                const double left_x = (i == 0) ? 0.5 : group_separator_positions[i - 1];
                const double right_x = (i < group_separator_positions.size()) ? group_separator_positions[i] : grouped_boxplot_data.size() + 0.5;
                const std::string base_color = is_flat_problem ? "#ff00007e" : "#adadad";
                const std::string base_label = is_flat_problem ? (aggregated_stats_label + " (flat problem)"): aggregated_stats_label;

                const bool add_base_label = is_flat_problem ? !flat_label_added : !regular_label_added;
                if (add_base_label) {
                    plt::plot(std::vector<double>{left_x, right_x}, std::vector<double>{y_val, y_val},
                              {{"color", base_color}, {"linestyle", "--"}, {"linewidth", "1.2"}, {"label", base_label}});
                    if (is_flat_problem) {
                        flat_label_added = true;
                    } else {
                        regular_label_added = true;
                    }
                } else {
                    plt::plot(std::vector<double>{left_x, right_x}, std::vector<double>{y_val, y_val},
                              {{"color", base_color}, {"linestyle", "--"}, {"linewidth", "1.2"}});
                }

                // Add green offset lines for problems whose reference solution is proven optimal.
                if (problems[i].get_reference_solution_proven_optimal()) {
                    const double optimal_y = y_val + (plot_max - plot_min) * 0.004;
                    const std::string optimal_label = aggregated_stats_label + " (proven optimal)";
                    if (!optimal_label_added) {
                        plt::plot(std::vector<double>{left_x, right_x}, std::vector<double>{optimal_y, optimal_y},
                                  {{"color", "#00ff007e"}, {"linestyle", "--"}, {"linewidth", "1.2"}, {"label", optimal_label}});
                        optimal_label_added = true;
                    } else {
                        plt::plot(std::vector<double>{left_x, right_x}, std::vector<double>{optimal_y, optimal_y},
                                  {{"color", "#00ff007e"}, {"linestyle", "--"}, {"linewidth", "1.2"}});
                    }
                }
            }
        }
    }

    if (config.draw_random_solution_reference) {
        int n_iters = 100;// * std::get<2>(results.get_dimensions());
        for (size_t i = 0; i < problem_tick_positions.size(); ++i) {
            double random_solution_value = 0.0;
            bool has_reference = false;
            Permutation pp(problems[i].get_size());
            for (int iter = 0; iter < n_iters; ++iter) {
                pp.reset();
                pp.reshuffle();
                const double cost = cost_function(problems[i].get_matrices().first, problems[i].get_matrices().second, pp);
                if (iter == 0 || cost > random_solution_value) {
                    random_solution_value = cost;
                }
            }
            
            double best_known_value = problems[i].get_best_cost();
            if (statistic_name == "cost") {
                has_reference = true;
            } 
            else if (statistic_name == "cost_relative_quality") {
                random_solution_value = relative_cost_quality_of_solution(random_solution_value, best_known_value);
                best_known_value = 0.0; 
                has_reference = true;
            } 
            else if (statistic_name == "cos_quality") {
                random_solution_value = cos_quality_of_solution(random_solution_value, problems[i].get_matrices().first, problems[i].get_matrices().second);
                best_known_value = cos_quality_of_solution(best_known_value, problems[i].get_matrices().first, problems[i].get_matrices().second);
                has_reference = true;
            } 
            else if (statistic_name == "normalized_angular_quality") {
                random_solution_value = normalized_angle_quality_of_solution(random_solution_value, problems[i].get_matrices().first, problems[i].get_matrices().second);
                best_known_value = normalized_angle_quality_of_solution(best_known_value, problems[i].get_matrices().first, problems[i].get_matrices().second);
                has_reference = true;
            }
            else
                std::cerr << "Warning: random solution reference line is not implemented for statistic '" << statistic_name << "' and will not be drawn." << std::endl; 
            
            const double left_x = (i == 0) ? 0.5 : group_separator_positions[i - 1];
            const double right_x = (i < group_separator_positions.size()) ? group_separator_positions[i] : grouped_boxplot_data.size() + 0.5;
                

            if (has_reference) {
                if (i == 0) {
                    // Add the label only for the first line to avoid duplicates in the legend
                    plt::plot(std::vector<double>{left_x, right_x}, std::vector<double>{random_solution_value, random_solution_value},
                            {{"color", "#0000ff"}, {"linestyle", ":"}, {"linewidth", "1.2"}, {"label", "Random upper reference\n (worst of "+std::to_string(n_iters)+" random solutions)"}}); 
                } else {
                    plt::plot(std::vector<double>{left_x, right_x}, std::vector<double>{random_solution_value, random_solution_value},
                            {{"color", "#0000ff"}, {"linestyle", ":"}, {"linewidth", "1.2"}}); 
                }
                // Shading between random solution reference and best known solution reference (if provided) to visually indicate the area of solution space that is better than random, if the random solution reference is worse than the best known solution reference.
                if (has_guides) {
                    if (random_solution_value > best_known_value) {
                        plt::fill_between(std::vector<double>{left_x, right_x},
                                              std::vector<double>{best_known_value, best_known_value},
                                              std::vector<double>{random_solution_value, random_solution_value},
                                              {{"color", "#0000ff07"}}); // semi-transparent blue
                    }
                    
                }
            }
        }
    }

    // Scale (log, linear, etc.)
    if (!config.scale.second.empty())
        plt::set_yscale(config.scale.second);

    // Plot of medians
    if (config.connect_medians){
        // method_name: (problem name: median)
        // not sornted
        const auto medians_container = results.aggregate(statistic_name, AggregationType::MEDIAN);
        auto medians = std::vector<double> (problems.size());

        for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
            if (scatter_x[method_index].empty())
                continue;
            medians.clear();
            // problems are sorted above
            for (auto p: problems)
                medians.push_back(medians_container.at(methods[method_index].name).at(p.get_name()));
            plt::plot(methods_x_positions[method_index], medians
                        , {  {"c",adjust_color_opacity(colors[method_index], 0.25)}
                           //, {"marker", markers[method_index]}
                           , {"linestyle", "--"}
                            //    , {"label", methods[method_index].name}
                         }
                    );
        }
    }   

    // Scatterplot of points inside boxplots
    for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
        if (scatter_x[method_index].empty()) {
            continue;
        }
        plt::scatter(scatter_x[method_index],
                     scatter_y[method_index],
                     18,
                     {{"c", colors[method_index]}, {"marker", markers[method_index]}, {"label", methods[method_index].name}});
    }



    // Legend location
    try {
        plt::legend({{"loc", config.legend_loc}});
    } catch (const std::runtime_error&) {
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: legend() failed; continuing without legend for this figure.\n");
    }

    // X and Y labels
    std::string x_label, y_label;
    x_label = !config.xy_labels.first.empty() ? config.xy_labels.first : "QAP problem instances";

    if (x_label.find("sorted by") == std::string::npos) {
        switch(config.sorting_criterion) {
        case SortingCriterion::SIZE:
            x_label += ", sorted by size";
            break;
        case SortingCriterion::OPTIMUM_PROXIMITY:
            x_label += ", sorted by optimum proximity";
            break;
        default:
            x_label = "QAP problem instance" ;
        }
    }

    y_label = !config.xy_labels.second.empty() ? config.xy_labels.second : statistic_name;
    plt::xlabel(x_label);
    plt::ylabel(y_label);
    if (config.y_limits.first != config.y_limits.second) {
        plt::ylim(config.y_limits.first, config.y_limits.second);
    }



    // Title
    plt::title(config.title);
    if (!config.output_dir.empty())
        save_figure(config);
    plt::show();
}






//// Plots boxplots of a given statistic (e.g. time, cost, quality) for a single method across multiple problem instances.
//// Boxplots are connected with a line to show the trend of the statistic across problem instances (e.g. dependency of running time from size of the problem instance). The x-axis represents linearly sorted characteristics of different problem instances (e.g. size, difficulty).
// void boxplot_series(const MethodsPlottingStatisticsByProblem& methods_statistics,
//                      std::vector<Problem<int>> problems,
//                      const std::vector<MethodDefinition>& methods,
//                      std::string title = "Boxplot of times by method and problem instance",
//                      std::pair<double, double> y_limits = std::pair<double, double>(),
//                      SortingCriterion sorting_criterion = SortingCriterion::SIZE)
// {
//     get_methods_statistics_for_plotting_by_problem(methods_statistics);
//     methods_boxplot(methods_statistics, problems, methods, "time", title, y_limits, std::vector<double>(), sorting_criterion);
// }

// void plot_distribution_of_costs(const std::vector<int>& costs, const std::string& problem_name) {
//     plt::figure();
//     plt::hist(costs, 20); // 20 bins
//     plt::title("Distribution of costs for " + problem_name);
//     plt::xlabel("Cost");
//     plt::ylabel("Frequency");
//     plt::show();
// }



/************************************************** Scatter plot ***************************************************************/

static bool linear_regression_with_pearson_r(const std::vector<double>& x,
                                             const std::vector<double>& y,
                                             double& slope,
                                             double& intercept,
                                             double& r)
{
    const size_t n = std::min(x.size(), y.size());
    if (n < 2) {
        slope = 0.0;
        intercept = 0.0;
        r = std::numeric_limits<double>::quiet_NaN();
        return false;
    }

    const double mean_x = std::accumulate(x.begin(), x.begin() + n, 0.0) / static_cast<double>(n);
    const double mean_y = std::accumulate(y.begin(), y.begin() + n, 0.0) / static_cast<double>(n);

    double sxx = 0.0;
    double syy = 0.0;
    double sxy = 0.0;
    for (size_t i = 0; i < n; ++i) {
        const double dx = x[i] - mean_x;
        const double dy = y[i] - mean_y;
        sxx += dx * dx;
        syy += dy * dy;
        sxy += dx * dy;
    }

    if (sxx <= 0.0) {
        slope = 0.0;
        intercept = mean_y;
        r = std::numeric_limits<double>::quiet_NaN();
        return false;
    }

    slope = sxy / sxx;
    intercept = mean_y - slope * mean_x;
    if (sxx > 0.0 && syy > 0.0) {
        r = sxy / std::sqrt(sxx * syy);
    } else {
        r = std::numeric_limits<double>::quiet_NaN();
    }
    return true;
}

static std::vector<double> position_match_quality_spearman(
    const std::vector<Permutation<int>>& run_permutations,
    const Permutation<int>& best_known_permutation,
    const std::vector<double>& quality_values)
{
    const size_t n_runs = std::min(run_permutations.size(), quality_values.size());
    if (n_runs < 2 || best_known_permutation.empty()) {
        return {};
    }

    size_t n_positions = best_known_permutation.size();
    for (size_t run_i = 0; run_i < n_runs; ++run_i) {
        n_positions = std::min(n_positions, run_permutations[run_i].size());
    }
    if (n_positions == 0) {
        return {};
    }

    std::vector<double> correlations(n_positions, 0.0);
    std::vector<double> matches(n_runs, 0.0);
    std::vector<double> quality(quality_values.begin(), quality_values.begin() + n_runs);

    for (size_t pos = 0; pos < n_positions; ++pos) {
        for (size_t run_i = 0; run_i < n_runs; ++run_i) {
            matches[run_i] = (run_permutations[run_i][pos] == best_known_permutation[pos]) ? 1.0 : 0.0;
        }

        const double rho = spearman_rank_correlation(matches, quality);
        correlations[pos] = std::isnan(rho) ? 0.0 : rho;
    }

    return correlations;
}

// Helper: select the most interesting x-ticks (first, last, top N, bottom N)
// @param matrix the matrix of correlations (or other values) to analyze for selecting interesting x-ticks
// @param n_top (by default 2) - the number of top values to include as x-ticks, in addition to the first and last positions. 
// @param n_bottom (by default 2) - the number of bottom values to include as x-ticks, in addition to the top values and the first and last positions. 
// @param offset (by default 1.0) a value to add to the top and bottom values to ensure index-style is relevant for the problem (some problems index from 1, some from 0)
static std::vector<size_t> select_interesting_x_ticks(
    const std::vector<std::vector<double>>& matrix,
    size_t n_top = 2,
    size_t n_bottom = 2, 
    int offset = 0)
{
    std::set<size_t> ticks_set;
    if (matrix.empty() || matrix[0].empty()) {
        return {};
    }

    const size_t n_cols = matrix[0].size();
    
    // Always include first and last
    ticks_set.insert(0 + static_cast<size_t>(offset));
    if (n_cols > 1)
        ticks_set.insert(n_cols - 1 + static_cast<size_t>(offset));

    // Collect correlations from all rows to find most interesting columns
    std::map<size_t, double> col_max_corr, col_min_corr;
    for (size_t col_i = 0; col_i < n_cols; ++col_i) {
        double max_corr = 0.0, min_corr = 0.0;
        for (const auto& row : matrix) {
            if (col_i < row.size()) {
                max_corr = std::max(max_corr, row[col_i]);
                min_corr = std::min(min_corr, row[col_i]);
            }
        }
        col_max_corr[col_i] = max_corr; col_min_corr[col_i] = min_corr;
    }

    // Find top N correlation values
    std::vector<std::pair<size_t, double>> col_max_pairs(col_max_corr.begin(), col_max_corr.end()), col_min_pairs(col_min_corr.begin(), col_min_corr.end());
    std::sort(col_max_pairs.begin(), col_max_pairs.end(),
              [](const auto& a, const auto& b) { return a.second > b.second; });
    std::sort(col_min_pairs.begin(), col_min_pairs.end(),
              [](const auto& a, const auto& b) { return a.second < b.second; });

    for (size_t i = 0; i < std::min(n_top, col_max_pairs.size()); ++i)
        ticks_set.insert(col_max_pairs[i].first + static_cast<size_t>(offset));
    for (size_t i = 0; i < std::min(n_bottom, col_min_pairs.size()); ++i)
        ticks_set.insert(col_min_pairs[i].first + static_cast<size_t>(offset));

    // // Find bottom N (smallest absolute values)
    // for (size_t i = std::max(0, static_cast<int>(col_pairs.size()) - static_cast<int>(n_bottom)); i < col_pairs.size(); ++i)
    //     ticks_set.insert(col_pairs[i].first + static_cast<size_t>(offset));

    std::vector<size_t> ticks_vec(ticks_set.begin(), ticks_set.end());
    std::sort(ticks_vec.begin(), ticks_vec.end());
    return ticks_vec;
}

static bool draw_heatmap(const std::vector<std::vector<double>>& matrix,
                         const std::vector<std::string>& x_labels,
                         const std::vector<std::string>& y_labels)
{
    if (matrix.empty() || matrix[0].empty()) {
        return false;
    }

    // Square-based heatmap rendering
    size_t n_rows = matrix.size();
    size_t n_cols = matrix[0].size();
    std::vector<double> x, y, c;
    for (size_t i = 0; i < n_rows; ++i) {
        for (size_t j = 0; j < n_cols; ++j) {
            x.push_back(j);
            y.push_back(i);
            c.push_back(matrix[i][j]);
        }
    }
    // Use squares as markers
    matplotlibcpp::scatter_colored(x, y, c, 180.0, { {"cmap", "bwr"}, {"vmin", "-1.0"}, {"vmax", "1.0"}, {"marker", "s"} });

    auto x_tick_pos = select_interesting_x_ticks(matrix, 4,4);
    auto x_tick_labels = std::vector<std::string>(x_tick_pos.size());
    printf("[plotting] Selected x-ticks at positions:");
    for (int i = 0; i < x_tick_pos.size(); ++i) {
        printf(" %zu", x_tick_pos[i]);
        x_tick_labels[i] = std::to_string(x_tick_pos[i] + 1);
    }
    try {
        //plt::xticks(x_tick_positions, x_tick_labels, { {"rotation", "45"} });
        //plt::tick_params({{"rotation", "45"} }, "x");
        plt::xticks(x_tick_pos, x_tick_labels, { {"rotation", "vertical"} });
    } catch (const std::runtime_error&) {
        PyErr_Clear();
        plt::xticks(x_tick_pos);
        //plt::xticks(x_tick_positions, x_tick_labels, { {"rotation", "vertical"} });
    }
    std::vector<double> y_pos(y_labels.size());
    std::iota(y_pos.begin(), y_pos.end(), 0.0);
    plt::yticks(y_pos, y_labels);

    // Manual colorbar legend (since plt::colorbar is not available)
    // Draw a colorbar-like patch manually
    // Draw a separated colorbar (legend) with steps matching the pixel height for a continuous look
    double legend_x = n_cols + 2.0; // more distance from plot
    double legend_y0 = 0.0;
    double legend_y1 = n_rows - 1;
    int n_steps = std::max(2, static_cast<int>(std::ceil((legend_y1 - legend_y0) * 16.0 + 1.0))); // 16 squares per row height
    for (int i = 0; i < n_steps; ++i) {
        double v0 = -1.0 + (2.0 * i) / (n_steps - 1);
        double y0 = legend_y0 + (legend_y1 - legend_y0) * i / (n_steps - 1);
        double xc = legend_x;
        matplotlibcpp::scatter_colored(std::vector<double>{xc}, std::vector<double>{y0}, std::vector<double>{v0}, 180.0, { {"cmap", "bwr"}, {"vmin", "-1.0"}, {"vmax", "1.0"}, {"marker", "s"} });
    }
    // Add text labels for min/max
    matplotlibcpp::text(legend_x - 1 , legend_y1+0.1, "Correlation");
    matplotlibcpp::text(legend_x + 0.7, legend_y0, "-1.0");
    matplotlibcpp::text(legend_x + 0.7, legend_y1, "+1.0");
    plt::show();
    return true;
}

static void print_top_position_correlations(const std::string& context_label,
                                            const std::vector<double>& correlations,
                                            const std::string& metric_label,
                                            size_t top_k = 5)
{
    if (correlations.empty()) {
        std::cout << "[task5] " << context_label << " | " << metric_label << ": no correlation data" << std::endl;
        return;
    }

    std::vector<size_t> order(correlations.size());
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
        return std::abs(correlations[a]) > std::abs(correlations[b]);
    });

    const size_t n_report = std::min(top_k, order.size());
    std::cout << "[task5] " << context_label << " | " << metric_label << " top-" << n_report << " positions by |rho|:";
    for (size_t i = 0; i < n_report; ++i) {
        const size_t pos0 = order[i];
        char buf[64];
        std::snprintf(buf, sizeof(buf), "(pos %zu: rho=%.3f)", pos0 + 1, correlations[pos0]);
        std::cout << " " << buf;
    }
    std::cout << std::endl;
}


// @brief Plots heatmaps of position-wise Spearman correlations between position matches and solution quality (Relative cost) for each method and problem instance, to analyze how well the methods' solution quality correlates with correctly placing specific positions in the permutation. This can reveal if certain positions are more critical for achieving good solutions and if methods differ in their ability to correctly place those positions.
// @bug Saving before plt::show() can cause issues with some backends (ticks are not shown), so saving is not done.
// Saving is not performed!
// @param results container with experiment results, including raw solutions and statistics for each method and problem instance
// @param problems list of problem instances to include in the heatmaps
// @param methods list of method definitions to include in the heatmaps (only methods with available data in results will be plotted)
// @param config configuration for the heatmap plot (e.g. figure size, font size
void plot_position_match_quality_heatmaps(const ExperimentResults<>& results,
                                          const std::vector<Problem<int>>& problems,
                                          const std::vector<MethodDefinition>& methods,
                                          PlotConfig config = PlotConfig{})
{
    if (problems.empty() || methods.empty()) {
        std::cout << "[task5] Heatmap skipped: empty problems or methods." << std::endl;
        return;
    }

    matplotlibcpp::rcparams({{"font.size", std::to_string(config.font_size)}});

    std::cout << "[task5] Heatmap diagnostics: methods in results(stats)=";
    const auto available_methods = results.get_method_names();
    for (const auto& m : available_methods) {
        std::cout << " '" << m << "'";
    }
    std::cout << std::endl;

    const auto& solutions_raw = results.raw_solutions();
    std::cout << "[task5] Heatmap diagnostics: methods in results(solutions)=";
    for (const auto& [m, _] : solutions_raw) {
        std::cout << " '" << m << "'";
    }
    std::cout << std::endl;

    for (const auto& [m, pmap] : solutions_raw) {
        std::cout << "[task5] Heatmap diagnostics: " << m << " has " << pmap.size() << " problem solution-entries." << std::endl;
    }

    std::cout << "[task5] Heatmap diagnostics: methods requested=";
    for (const auto& method : methods) {
        std::cout << " '" << method.name << "'";
    }
    std::cout << std::endl;

    for (const auto& problem : problems) {
        const auto& problem_name = problem.get_name();
        const auto& best_known = problem.get_best_solution();
        if (best_known.empty()) {
            std::cout << "[task5] " << problem_name << ": best-known permutation is empty, skipping all heatmaps for this problem." << std::endl;
            continue;
        }

        // For each method, collect correlation vectors
        std::vector<std::vector<double>> method_corrs; // [method][position]
        std::vector<std::string> y_labels;
        std::vector<Permutation<int>> combined_permutations;
        std::vector<double> combined_rel_quality;
        std::vector<double> combined_norm_quality;
        size_t n_positions = 0;

        for (const auto& method : methods) {
            const auto* runs_stats = results.find_runs(method.name, problem_name);
            const auto* run_solutions = results.find_run_solutions(method.name, problem_name);
            if (!runs_stats || !run_solutions) continue;
            const auto rel_it = runs_stats->data.find("cost_relative_quality");
            const auto norm_it = runs_stats->data.find("cos_quality");
            if (rel_it == runs_stats->data.end() || norm_it == runs_stats->data.end()) continue;
            const size_t n_runs = std::min(run_solutions->size(), std::min(rel_it->second.size(), norm_it->second.size()));
            if (n_runs < 2) continue;

            std::vector<Permutation<int>> method_permutations(run_solutions->begin(), run_solutions->begin() + static_cast<std::ptrdiff_t>(n_runs));
            std::vector<double> method_rel_quality(rel_it->second.begin(), rel_it->second.begin() + static_cast<std::ptrdiff_t>(n_runs));
            std::vector<double> method_norm_quality(norm_it->second.begin(), norm_it->second.begin() + static_cast<std::ptrdiff_t>(n_runs));

            std::vector<double> corr_rel = position_match_quality_spearman(method_permutations, best_known, method_rel_quality);
            // Optionally, you could also add normalized cost correlations as a second row per method, but for clarity, let's do one row per method (relative cost quality)
            if (corr_rel.empty()) continue;
            if (n_positions == 0) n_positions = corr_rel.size();
            else n_positions = std::min(n_positions, corr_rel.size());
            method_corrs.push_back(std::vector<double>(corr_rel.begin(), corr_rel.begin() + static_cast<std::ptrdiff_t>(n_positions)));
            y_labels.push_back(method.name);

            // For combined
            combined_permutations.insert(combined_permutations.end(), method_permutations.begin(), method_permutations.end());
            combined_rel_quality.insert(combined_rel_quality.end(), method_rel_quality.begin(), method_rel_quality.end());
            combined_norm_quality.insert(combined_norm_quality.end(), method_norm_quality.begin(), method_norm_quality.end());
        }

        // Add combined row if enough data
        if (combined_permutations.size() >= 2) {
            std::vector<double> combined_corr_rel = position_match_quality_spearman(combined_permutations, best_known, combined_rel_quality);
            if (!combined_corr_rel.empty()) {
                n_positions = std::min(n_positions, combined_corr_rel.size());
                method_corrs.push_back(std::vector<double>(combined_corr_rel.begin(), combined_corr_rel.begin() + static_cast<std::ptrdiff_t>(n_positions)));
                y_labels.push_back("Combined");
            }
        }

        if (method_corrs.empty() || n_positions == 0) {
            std::cout << "[task5] " << problem_name << ": no valid method correlations, skipping heatmap." << std::endl;
            continue;
        }

        // Transpose to [row][col] for draw_heatmap (each row = method)
        // Already in correct shape: [method][position]
        std::vector<std::string> x_labels(n_positions);
        for (size_t pos = 0; pos < n_positions; ++pos) {
            x_labels[pos] = std::to_string(pos + 1);
        }

        plt::figure(g_next_boxplot_figure_number++);            
        plt::xlabel("Permutation position");
        plt::ylabel("Method");
        plt::title(!config.title.empty() ?  problem_name + ": " + config.title : problem_name + ": position-match correlation with quality");
            
        set_active_figure_size(config.figure_size.first, config.figure_size.second);
        draw_heatmap(method_corrs, x_labels, y_labels);
        // plt::draw();
        // if (!config.output_dir.empty()) 
        //     save_figure(config);
        // saving before plt::show() breaks ticks in the figure
    }
}

// Scatterplot for initial vs. final statistics for each method/problem/statistic pair
// statistics_map: key = statistic name, value = pair {initial_stat_name, final_stat_name}
void methods_scatterplot(const ExperimentResults<>& results,
                        std::vector<Problem<int>> problems,
                        const std::vector<MethodDefinition>& methods,
                        const std::pair<std::string, std::string>& statistics,
                        PlotConfig config)
{
    if (methods.empty() || problems.empty()) return;
    const auto methods_statistics = results.to_plotting_statistics_by_problem();
    sort_problems(problems, config.sorting_criterion);
    const std::vector<std::string> fallback_colors = { "#1f76b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf" };
    const std::vector<std::string> fallback_markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };

    matplotlibcpp::rcparams({{"font.size", std::to_string(config.font_size)}});
    plt::figure(g_next_boxplot_figure_number++);
    set_active_figure_size(config.figure_size.first, config.figure_size.second);

    // Plot each method/problem series separately and report its own Spearman correlation.
    for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
        const auto& method = methods[method_index];
        auto method_it = methods_statistics.find(method.name);
        if (method_it == methods_statistics.end()) continue;
        auto& stats_by_problem = method_it->second;
        std::string base_color = method.color.empty() ? fallback_colors[method_index % fallback_colors.size()] : method.color;
        std::string marker = method.marker.empty() ? fallback_markers[method_index % fallback_markers.size()] : method.marker;

        for (size_t problem_index = 0; problem_index < problems.size(); ++problem_index) {
            const auto& problem = problems[problem_index];
            const std::string& problem_name = problem.get_name();
            // Slightly adjust color for each problem
            double color_factor = 1.0 + 0.15 * (static_cast<double>(problem_index) / std::max<size_t>(1, problems.size() - 1));
            std::string color = adjust_color_brightness(base_color, color_factor);
            std::string problem_marker = fallback_markers[problem_index % fallback_markers.size()];

            // Get x (stat.first) and y (stat.second) for this method/problem
            std::vector<double> x, y;
            auto stat_first_it = stats_by_problem.find(statistics.first);
            auto stat_second_it = stats_by_problem.find(statistics.second);
            if (stat_first_it != stats_by_problem.end() && stat_second_it != stats_by_problem.end()) 
            {
                auto prob_first_it = stat_first_it->second.find(problem_name);
                auto prob_second_it = stat_second_it->second.find(problem_name);
                if (prob_first_it != stat_first_it->second.end() && prob_second_it != stat_second_it->second.end()) {
                    const auto& xvals = prob_first_it->second;
                    const auto& yvals = prob_second_it->second;
                    size_t n = std::min(xvals.size(), yvals.size());
                    x.assign(xvals.begin(), xvals.begin() + n);
                    y.assign(yvals.begin(), yvals.begin() + n);
                }
            }
            if (!x.empty() && !y.empty()) {
                double rho = spearman_rank_correlation(x, y);
                char buf[64];
                snprintf(buf, sizeof(buf), "Spearman = %.3f", rho); 

                std::string label = method.name + ", " + problem.get_name() + " (" + buf + ")";
                
                plt::scatter(x, y, 18, {{"c", color}, {"marker", config.plot_marker.empty() ? problem_marker : config.plot_marker}, {"label", label}});
            }
        }
    }

    std::string x_label = !config.xy_labels.first.empty() ? config.xy_labels.first : statistics.first;
    std::string y_label = !config.xy_labels.second.empty() ? config.xy_labels.second : statistics.second;
    plt::xlabel(replace_underscores(x_label));
    plt::ylabel(replace_underscores(y_label));

    std::string title = !config.title.empty() ? config.title : "Scatterplot: " + replace_underscores(x_label) + " vs. " + replace_underscores(y_label);
    plt::title(title);
    try {
        plt::legend({{"loc", config.legend_loc}});
    } catch (const std::runtime_error&) {
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: legend() failed; continuing without legend for this figure.\n");
    }
    if (!config.output_dir.empty()) save_figure(config);
    plt::show();
}

// Plot similarity trends vs. a selected quality metric.
// For each method/problem pair, two series are drawn:
//   1) mean_cayley_similarity_to_other_local_optima (lighter color)
//   2) cayley_similarity_to_best_known (base/original color)
void plot_similarity_vs_quality(const ExperimentResults<>& results,
                               std::vector<Problem<int>> problems,
                               const std::vector<MethodDefinition>& methods,
                               const std::string& quality_statistic_name,
                               PlotConfig config = PlotConfig{})
{
    if (methods.empty() || problems.empty()) return;

    const auto methods_statistics = results.to_plotting_statistics_by_problem();
    sort_problems(problems, config.sorting_criterion);

    const std::vector<std::string> fallback_colors = { "#1f76b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf" };
    const std::vector<std::string> line_styles = { ":", "--", "-.", "-" };
    const std::vector<std::string> markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };

    matplotlibcpp::rcparams({{"font.size", std::to_string(config.font_size)}});
    plt::figure(g_next_boxplot_figure_number++);
    set_active_figure_size(config.figure_size.first, config.figure_size.second);

    for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
        const auto& method = methods[method_index];
        auto method_it = methods_statistics.find(method.name);
        if (method_it == methods_statistics.end()) continue;
        const auto& stats_by_problem = method_it->second;

        const std::string base_color = method.color.empty() ? fallback_colors[method_index % fallback_colors.size()] : method.color;

        auto quality_it = stats_by_problem.find(quality_statistic_name);
        auto avg_sim_it = stats_by_problem.find("mean_cayley_similarity_to_other_local_optima");
        auto best_sim_it = stats_by_problem.find("cayley_similarity_to_best_known");
        if (quality_it == stats_by_problem.end() || avg_sim_it == stats_by_problem.end() || best_sim_it == stats_by_problem.end()) {
            continue;
        }

        for (size_t problem_index = 0; problem_index < problems.size(); ++problem_index) {
            const std::string& problem_name = problems[problem_index].get_name();

            auto quality_prob_it = quality_it->second.find(problem_name);
            auto avg_prob_it = avg_sim_it->second.find(problem_name);
            auto best_prob_it = best_sim_it->second.find(problem_name);
            if (quality_prob_it == quality_it->second.end() ||
                avg_prob_it == avg_sim_it->second.end() ||
                best_prob_it == best_sim_it->second.end()) {
                continue;
            }

            const auto& quality_vals = quality_prob_it->second;
            const auto& avg_sim_vals = avg_prob_it->second;
            const auto& best_sim_vals = best_prob_it->second;
            const size_t n = std::min(quality_vals.size(), std::min(avg_sim_vals.size(), best_sim_vals.size()));
            if (n == 0) continue;

            const std::string line_style = config.plot_linestyle.empty() ? line_styles[problem_index % line_styles.size()] : config.plot_linestyle;
            const std::string marker = config.plot_marker.empty() ? markers[problem_index % markers.size()] : config.plot_marker;
            const std::string avg_color = adjust_color_brightness(base_color, 2);
            const std::string colors[2] = { base_color, avg_color };

            auto labels = std::array<std::string, 2>{"to best", "avg to others"};
            auto x_series = std::array{best_sim_vals, avg_sim_vals};

            // Plotting 2 series: (similarity to best-known, y) and (average similarity to other local optima, y), with separate regression lines and correlation annotations for each.
            for (int j = 0; j < x_series.size(); ++j) {
                // reordering data
                std::vector<size_t> order(n);
                std::iota(order.begin(), order.end(), 0);
                std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
                    return x_series[j][a] < x_series[j][b];
                });

                std::vector<double> y(n), x(n);
                for (size_t i = 0; i < n; ++i) {
                    const size_t idx = order[i];
                    y[i] = quality_vals[idx];
                    x[i] = x_series[j][idx];
                }


                double slope = 0.0, intercept = 0.0, corr = std::numeric_limits<double>::quiet_NaN();
                const bool has_fit = linear_regression_with_pearson_r(x, y, slope, intercept, corr);
                char buf[64];
                if (std::isnan(corr))
                    snprintf(buf, sizeof(buf), "Pearson = n/a");
                else
                    snprintf(buf, sizeof(buf), "Pearson = %.3f", corr);

                const std::string label = method.name + ", " + problem_name + " ("+ labels[j] + ", " + buf + ")";

                try {
                    plt::scatter(x, y, 22, {{"color", colors[j]}, {"marker", marker}, {"label", ""}});
                    if (has_fit) {
                        std::vector<double> y_fit(n);
                        for (size_t i = 0; i < n; ++i) 
                            y_fit[i] = slope * x[i] + intercept;

                        plt::plot(x, y_fit, {{"color", colors[j]}, {"linestyle", line_style}, {"label", label}});
                    } else {
                        plt::plot(std::vector<double>{x.front(), x.back()}, std::vector<double>{y.front(), y.back()}, {{"color", colors[j]}, {"linestyle", line_style}, {"label", label}});
                    }
                } 
                catch (const std::runtime_error&) {
                    PyErr_Clear();
                    std::fprintf(stderr, "[plotting] Warning: similarity plot failed for method '%s' and problem '%s'; skipping this series.\n", method.name.c_str(), problem_name.c_str());
                }
            }
        }
    }
    const std::string x_label = !config.xy_labels.first.empty() ? config.xy_labels.first : "Cayley similarity";
    const std::string y_label = !config.xy_labels.second.empty() ? config.xy_labels.second : replace_underscores(quality_statistic_name);
    plt::xlabel(x_label);
    plt::ylabel(y_label);

    const std::string title = !config.title.empty() ? config.title : ("Similarity vs. " + replace_underscores(quality_statistic_name));
    plt::title(title);
    if (config.y_limits.first != config.y_limits.second) {
        plt::ylim(config.y_limits.first, config.y_limits.second);
    }

    try {
        plt::legend({{"loc", config.legend_loc}});
    } catch (const std::runtime_error&) {
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: legend() failed; continuing without legend for this figure.\n");
    }

    if (!config.output_dir.empty()) save_figure(config);
    plt::show();
}



/****************************************Plot for n_runs ~ best_quality ****************************/

// Plots best-so-far and average-so-far solution quality vs. number of independent starts for each method/problem.
// Each method uses a dedicated color, each problem uses a different line style/marker
// statistic_name: e.g. "cost", "cost_relative_quality", etc.
void plot_restarts_vs_quality(const ExperimentResults<>& results,
                             const std::vector<Problem<int>>& problems,
                             const std::vector<MethodDefinition>& methods,
                             const std::string& statistic_name,
                             PlotConfig config = PlotConfig{},
                             int max_restarts = 0)
{
    if (methods.empty() || problems.empty()) return;
    const auto methods_statistics = results.to_plotting_statistics_by_problem();

    // Color and line/marker styles
    const std::vector<std::string> fallback_colors = { "#1f76b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf" };
    const std::vector<std::string> line_styles = {":" ,"--" ,"-.","-" };
    const std::vector<std::string> markers = { "o", "s", "^", "D", "x", "P", "v", "*", "h", "H", "X" };

    matplotlibcpp::rcparams({{"font.size", std::to_string(config.font_size)}});
    plt::figure(g_next_boxplot_figure_number++);
    set_active_figure_size(config.figure_size.first, config.figure_size.second);

    for (size_t method_index = 0; method_index < methods.size(); ++method_index) {
        const auto& method = methods[method_index];
        auto method_it = methods_statistics.find(method.name);
        if (method_it == methods_statistics.end()) continue;
        auto& stats_by_problem = method_it->second;
        std::string color = method.color.empty() ? fallback_colors[method_index % fallback_colors.size()] : method.color;

        for (size_t problem_index = 0; problem_index < problems.size(); ++problem_index) {
            const auto& problem = problems[problem_index];
            const std::string& pname = problem.get_name();
            std::string line_style = config.plot_linestyle.empty() ? line_styles[problem_index % line_styles.size()] : config.plot_linestyle;
            std::string marker = config.plot_marker.empty() ? markers[problem_index % markers.size()] : config.plot_marker;

            // Get the statistic values for this method/problem
            std::vector<double> values;
            auto stat_it = stats_by_problem.find(statistic_name);
            if (stat_it != stats_by_problem.end()) {
                auto prob_it = stat_it->second.find(pname);
                if (prob_it != stat_it->second.end()) {
                    values = prob_it->second;
                }
            }
            if (values.empty()) continue;

            size_t n = (max_restarts == 0) ? values.size() : std::min(values.size(), static_cast<size_t>(max_restarts));
            std::vector<double> best_so_far(n), avg_so_far(n);
            double best = values[0];
            double sum = values[0];
            best_so_far[0] = best;
            avg_so_far[0] = values[0];
            std::vector<double> x_change_points = {1}; // to mark where the best solution changes
            std::vector<double> y_change_points = {values[0]};
            for (size_t i = 1; i < n; ++i) {
                if (values[i] < best) {
                    x_change_points.push_back(i + 1);
                    y_change_points.push_back(values[i]);
                    best = values[i];
                }
                sum += values[i];
                best_so_far[i] = best;
                avg_so_far[i] = sum / (i + 1);
            }
            // X axis: 1..n
            std::vector<double> x(n);
            std::iota(x.begin(), x.end(), 1);
            try {
                // Plot best-so-far
                std::string label_best = method.name + ", " + problem.get_name() + " (best)";
                plt::plot(x, best_so_far, { {"color", color}, {"linestyle", line_style}, 
                                            //{"marker", marker}, 
                                            {"label", label_best} });
                plt::scatter(x_change_points, y_change_points, 50, {{"color", color}, {"marker", marker}, {"label", ""}}); // mark points where best solution changes with 'X' marker

                // Plot avg-so-far
                std::string label_avg = method.name + ", " + problem.get_name() + " (avg)";
                // alpha is not supported, so manually added transparency
                std::string avg_color;
                try {
                    avg_color = (color.size() < 8) ? (color + "80") : color.substr(0, color.size() - 2) + std::format("{:x}", std::stoul(color.substr(color.size() - 2, 2), nullptr, 16)/2); // add 50% opacity to the color
                } catch (const std::runtime_error&) {
                    PyErr_Clear();
                    std::fprintf(stderr, "[plotting] Warning: failed to adjust color opacity for average line; using original color without transparency.\n");
                    avg_color = color;
                }
                plt::plot(x, avg_so_far, { {"color", avg_color}, {"linestyle", line_style}, {"marker", ""}, {"label", label_avg}});//, {"alpha", "0.6"} });
            }
            catch (const std::runtime_error&) {
                PyErr_Clear();
                std::fprintf(stderr, "[plotting] Warning: plot() failed for method '%s' and problem '%s'; skipping this line.\n", method.name.c_str(), problem.get_name().c_str());
            }
        }
    }

    std::string xlabel = !config.xy_labels.first.empty() ? config.xy_labels.first : "Number of starts";
    std::string ylabel = !config.xy_labels.second.empty() ? config.xy_labels.second : statistic_name;
    plt::xlabel(xlabel);
    plt::ylabel(replace_underscores(ylabel));
    std::string title = !config.title.empty() ? config.title : "Best/average quality vs. number of starts";
    plt::title(title);
    try {
        plt::legend({{"loc", config.legend_loc}});
    } catch (const std::runtime_error&) {
        PyErr_Clear();
        std::fprintf(stderr, "[plotting] Warning: legend() failed; continuing without legend for this figure.\n");
    }
    if (!config.output_dir.empty()) save_figure(config);
    plt::show();
}