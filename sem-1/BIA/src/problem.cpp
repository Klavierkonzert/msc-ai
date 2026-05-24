#pragma once

#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>
#include <tuple>
#include <utility>
#include <iostream>
#include <fstream>
#include <string>

#include "dataloaders.cpp"
#include "matrix.cpp"
#include "permutation.cpp"
#include "colors.h"

template<typename T=int>
class Problem {
protected:
    static constexpr const char* data_extension = ".dat";
    static constexpr const char* solution_extension = ".sln";

    std::string name;
    std::filesystem::path dir;
    std::pair<Matrix<T>, Matrix<T>> matrices;

    Permutation<T> best_solution;
    std::int64_t best_cost;
    int size;

    bool is_flat = false; // whether the problem is flat, i.e. all solutions have the similar cost, which is checked by analysis of matrices (e.g. if one of the matrices is mostly constant, or if the variance of the elements in the matrices is low)
    bool is_reference_solution_proven_optimal = false;
public:
    Problem() : name(""), dir(), matrices{}, best_solution(), best_cost(0), size(0) {}

    Problem(const std::string& problem_name, const std::filesystem::path& problem_dir)
        : name(problem_name), dir(problem_dir), matrices{}, best_solution(), best_cost(0), size(0) {
        load(problem_name, problem_dir);
    }

    void load(const std::string& problem_name, const std::filesystem::path& problem_dir) {
        is_reference_solution_proven_optimal = false;
        name = problem_name;
        dir = std::filesystem::absolute(problem_dir);

        const std::string base = (dir / name).string();
        auto [loaded_matrices, loaded_size] = load_data_into_matrices(base.c_str(), data_extension);
        auto [loaded_best_solution, loaded_best_cost] = load_best_solution(base.c_str(), solution_extension);

        matrices = loaded_matrices;
        size = loaded_size;
        best_solution = loaded_best_solution;
        best_cost = loaded_best_cost;
        if (best_cost != cost_function(matrices.first, matrices.second, best_solution)) {
            std::cerr << Colors::YELLOW << " Problem " << name << " WARNING:" << Colors::RESET << " Loaded best cost does not match the cost calculated from the loaded best solution. This may indicate an inconsistency in the data files." << std::endl;
        }
        
        // check whether one of the matrices is sparse, mostly constant, or low variance, and print a warning if so, as these properties may affect the difficulty of the problem instance and the performance of algorithms on it
        bool is_sparse = matrices.first.is_sparse() || matrices.second.is_sparse();
        bool is_mostly_const = matrices.first.is_mostly_const() || matrices.second.is_mostly_const();
        bool is_low_variance = matrices.first.is_low_variance() || matrices.second.is_low_variance();
        this ->is_flat = is_sparse || is_mostly_const || is_low_variance;
        if (this->is_flat) {
            std::cerr << Colors::ORANGE << " WARNING: Problem " << name << " is flat. " << Colors::RESET;
            if (is_sparse) 
                std::cerr << "One of the matrices is sparse." <<  std::endl;
            if (is_mostly_const)
                std::cerr << "One of the matrices is mostly constant." <<  std::endl;
            if (is_low_variance) 
                std::cerr << "One of the matrices has low variance." << std::endl;
            printf("Norms of matrices: %f, %f\n", matrices.first.norm(), matrices.second.norm());
        }
        double norm_best_cost = static_cast<double>(best_cost) / (matrices.first.norm() * matrices.second.norm());
        if (norm_best_cost < 1e-6)
            std::cerr << Colors::ORANGE << " WARNING: Problem " << name << " has very low normalized best cost. This may indicate that the problem is very easy, as the cost of the best known solution is very close to the lower bound of the cost function, which is 0." << Colors::RESET << std::endl;
        else if (norm_best_cost >1 || norm_best_cost < 0)
            std::cerr << Colors::RED << " WARNING: Problem " << name << " has high normalized best cost: " << Colors::RESET<<norm_best_cost << " This indicates that the best cost is indicated incorrectly." << std::endl;
    }
    // Static method to load multiple problems from a set of problem names and a directory containing the problem data files. The method returns a vector of Problem objects corresponding to the loaded problems.
     static std::vector<Problem<T>> load_problems(std::set<std::string> set_problem_names, 
                                                    const std::string& data_dir, bool set_optimality_of_reference_solutions = false) {
        std::vector<std::string> problem_names(set_problem_names.begin(), set_problem_names.end());
        std::vector<Problem<T>> problems(problem_names.size());
        int i=0;
        for (const auto &name : problem_names) {
            std::cout << "Loading problem file: " << name << std::endl;
            problems[i].load(name, data_dir);
            if (set_optimality_of_reference_solutions)
                problems[i].set_reference_solution_proven_optimal(true);
            //problems[i].print();
            i++;
        }
        return problems;
    }

    // Returns: name, size, (A,B) matrices, best permutation, best cost.
    auto get_attributes() const {
        return std::tie(name, size, matrices, best_solution, best_cost);
    }

    // Getters for the problem attributes

    // Returns the name of the problem instance. For example, 'lipa90a' or 'tai100a'.
    auto get_name() const { return name; }
    // Returns the size of the problem instance, which is the size of the permutation and the dimensions of the matrices.
    auto get_size() const { return size; }
    // Returns the directory where the problem data is stored.
    auto get_dir() const { return dir; }
    const auto& get_best_solution() const { return best_solution; }
    auto get_best_cost() const { return best_cost; }
    auto get_best_norm_cost() const { return static_cast<double>(best_cost) / (matrices.first.norm() * matrices.second.norm()); }
    const auto& get_matrices() const { return matrices; }

    // checks if the problem instance is flat, i.e. if all solutions have similar cost, which may indicate that the problem is easier for local search algorithms, as there are many local optima with similar cost, and the algorithms may not get stuck in a local optimum that is much worse than the global optimum
    bool is_flat_problem() const { return is_flat; }
    // checks if the problem instance is asymmetric, which may indicate that the problem is more difficult for local search algorithms, as the landscape of the cost function may be more complex and have more local optima compared to symmetric problems
    bool is_asymmetric_problem() const { return !matrices.first.is_symmetric() || !matrices.second.is_symmetric(); }
    // @brief Maximum (by absolute value) skewness of the two matrices in the problem instance.
    //
    // This may indicate that the problem is more difficult for local search algorithms, as the landscape of the cost function may be more complex and have more local optima compared to problems with low skewness
    auto get_skewness() const {
        double s1 = matrices.first.skewness();
        double s2 = matrices.second.skewness();
        return (std::abs(s1) > std::abs(s2)) ? s1 : s2;
    }

    // this status is not provided in the data files, but provided in the library of instances
    void set_reference_solution_proven_optimal(bool is_optimal) { 
        is_reference_solution_proven_optimal = is_optimal; 
    }
    // this status is not provided in the data files, but provided in the library of instances and thus should be set after loading the problem using `set_reference_solution_proven_optimal()` method
    bool get_reference_solution_proven_optimal() const { return is_reference_solution_proven_optimal; }


    // @brief Prints the properties of the problem instance, including the properties of the matrices and the best known solution. The level of detail of the printed information can be controlled by the parameters.
    // @param print_properties (by default false) if true, prints the properties of the problem instance, including whether the problem is flat, whether the reference solution is proven optimal, and the properties of the matrices (symmetry, zero diagonality, norms, coefficient of variation, skewness).
    // @param print_matrices (by default false) if true, prints the matrices of the problem instance.
    // @param print_reference_solution (by default false) if true, prints the best known solution and its cost.
    void print(bool print_properties = false, bool print_matrices = false, bool print_reference_solution = false) const {
        #define colored(color, text) (std::string(Colors::color)  + std::string(text) + std::string(Colors::RESET)).c_str()
       
        printf("\n%sProblem: %s%s\n", Colors::GREEN, name.c_str(), Colors::RESET);
        printf("Problem size: %d\n", size);
        if (print_properties) {
            printf("Problem properties:\n");
            printf(" - Flat problem: %s\n", is_flat ? colored(ORANGE, "Yes") : "No");
            printf(" - Asymmetric problem: %s\n", is_asymmetric_problem() ?  colored(ORANGE, "Yes")  : "No");
            printf("Matrices properties:\n");
            printf(" - Symmetry of matrices:                 %s, %s\n", matrices.first.is_symmetric() ? "Symmetric" : colored(ORANGE, "Asymmetric"), matrices.second.is_symmetric() ? "Symmetric" : colored(ORANGE, "Asymmetric"));
            printf(" - Zero diagonality of matrices:         %s, %s\n", matrices.first.is_zero_diagonal() ? "Zero diag" : colored(ORANGE, "Non-zero diag"), matrices.second.is_zero_diagonal() ? "Zero diag" : colored(ORANGE, "Non-zero diag"));
            printf(" - Norms of matrices:                    %f, %f \n", matrices.first.norm(), matrices.second.norm());
            printf(" - Coefficient of variation of matrices: %f, %f \n", matrices.first.cv(), matrices.second.cv());
            printf(" - Skewness of matrices:              %s%f%s, %s%f%s \n",(get_skewness()==matrices.first.skewness())? Colors::ORANGE: Colors::RESET, 
                                                                                matrices.first.skewness(), Colors::RESET,
                                                                            (get_skewness()==matrices.second.skewness())? Colors::ORANGE: Colors::RESET, 
                                                                                matrices.second.skewness(), Colors::RESET);
            printf("Solution properties:\n");
            printf(" - Reference solution is proven optimal: %s\n", is_reference_solution_proven_optimal ? colored(GREEN, "Yes") : "No");
            printf(" - Best known cost: %" PRId64 "\n", best_cost);
        }

        if (print_matrices) {
            printf("Matrix A:\n");
            matrices.first.print();
            printf("Matrix B:\n");
            matrices.second.print();
        }
        if (print_reference_solution) {
            if (is_flat) {
                printf("%sNOTE%s: This problem is flat, meaning that many solutions have similar cost.", Colors::YELLOW, Colors::RESET);   }
            printf("Best known solution (%s):\n", is_reference_solution_proven_optimal ? "proven optimal" : "not proven optimal");
            best_solution.print();
            printf("Best known cost: %" PRId64 "\n\n", best_cost);
        }
    }

    // @brief Prints a markdown report with the properties of the problem instance, including the properties of the matrices and the best known solution. The report is appended to the specified file path.
    // 
    // Call `std::filesystem::remove(report_path)` before calling this method for the first time to remove any existing report file, if you want to start with a clean report.
    void print_markdown_report(const char* report_path) const {
        #define md_colored(color, text) "<span style=\"color:" + std::string(color) + "\">" + std::string(text) + "</span>"
        #define md_colored_nums(color, text) "<span style=\"color:" + std::string(color) + "\">" + std::to_string(text) + "</span>"
        std::ofstream outFile(report_path, std::ios_base::app);

        if (!outFile) {
            std::cerr << Colors::RED << " ERROR: Could not open file " << report_path << " for writing the markdown report." << Colors::RESET << std::endl;
            return;
        }
        else {
            outFile << "\n### Problem: " << name.c_str() << "\n"
                        << "Problem size: " << size << "\n"

                        << "#### Problem properties:\n"
                            << " * Flat problem: " << (is_flat ? md_colored("ORANGE", "Yes") : "No") << "\n"
                            << " * Asymmetric problem: " << (is_asymmetric_problem() ? md_colored("ORANGE", "Yes") : "No") << "\n"

                        << "#### Matrices properties:\n|Property|Matrix A| Matrix B<br />|\n|---|---|---|\n"
                            << "|Symmetry        |" << (matrices.first.is_symmetric() ? "Symmetric" : md_colored("ORANGE", "Asymmetric")) << "|" << (matrices.second.is_symmetric() ? "Symmetric" : md_colored("ORANGE", "Asymmetric")) << "|\n"
                            << "|Zero diagonality|" << (matrices.first.is_zero_diagonal() ? "Zero diag" : md_colored("ORANGE", "Non-zero diag")) << "|" << (matrices.second.is_zero_diagonal() ? "Zero diag" : md_colored("ORANGE", "Non-zero diag")) << "|\n"
                            << "|Frobenius norm|" << matrices.first.norm() << "|" << matrices.second.norm() << "|\n"
                            << "|Coefficient of variation <br> of the elements|" << matrices.first.cv() << "|" << matrices.second.cv() << "|\n"
                            << "|Skewness|" << ((get_skewness()==matrices.first.skewness() )? md_colored_nums("ORANGE", matrices.first.skewness() ) : std::to_string(matrices.first.skewness()))
                                            << "|" << ((get_skewness()==matrices.second.skewness())? md_colored_nums("ORANGE", matrices.second.skewness()) : std::to_string(matrices.second.skewness()))
                                    << "| \n"
                        << "#### Solution properties:\n"
                            << "* Reference solution is proven optimal: " << (is_reference_solution_proven_optimal ? md_colored("GREEN", "Yes") : "No") << "\n"
                            << "* Best known cost: " << best_cost << "\n";
            
            outFile.close();
        }
    }
};
