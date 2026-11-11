#pragma once

// Quality measures for solutions to QAP
#include <cstdint>
#include "colors.h"
#include "dataloaders.cpp"
#include "matrix.cpp"

constexpr double PI = 3.14159265358979323846f;




// relative to the best cost quality
double relative_cost_quality_of_solution(std::int64_t cost, std::int64_t best_cost) {
    if (best_cost == 0) {
        throw std::invalid_argument("Best cost cannot be zero when calculating quality of solution.");
    }
    return static_cast<double>(cost - best_cost) / static_cast<double>(best_cost);
}

// QAP objective function normalized by the product of the Frobenious norms of the two matrices, which gives a measure of the quality of the solution that is independent of the scale of the cost function:
// $ cos(\pi) = \frac{cost}{||A|| \cdot ||B||} $
// Takes values between between 0 and 1 for most of the QAP instances (for >=0 matrices).
// The smaller the value, the better the solution (0 means that the solution is as good as the utopia solution), and 1 means that the solution is as bad as possible, i.e. orthogonal to the best solution)
double cos_quality_of_solution(std::int64_t cost, const Matrix<int>& A, const Matrix<int>& B) {
    double cos = (static_cast<double>(cost)) / (static_cast<double>(A.norm() * B.norm())); 
    return cos;
}
// angle of the solution (between -pi/2 and pi/2, but for most of the QAP instances it should be between 0 and pi/2)
// The closer to pi/2, the better the solution
double angle_quality_of_solution(std::int64_t cost, const Matrix<int>& A, const Matrix<int>& B) {
    double cos = (static_cast<double>(cost)) / (static_cast<double>(A.norm() * B.norm())); 
    return acos(cos);
}
// normalised angle of the solution (between -1 and 1, but for most of the QAP instances it should be between 0 and 1).
// The closer to 1, the better the solution
double normalized_angle_quality_of_solution(std::int64_t cost, const Matrix<int>& A, const Matrix<int>& B) {
    double cos = (static_cast<double>(cost)) / (static_cast<double>(A.norm() * B.norm())); 
    return 2.0f * acos(cos) / PI;
}

// difference of angles of two solutions
// the closer to 0, the more similar the solutions (0 means that the solutions are as good as each other), and the closer to +-pi/2, the worse the solutions (orthogonal to each other)
double angular_distance_of_solutions(std::int64_t cost1, std::int64_t cost2, const Matrix<int>& A, const Matrix<int>& B) {
    double cos1 = (static_cast<double>(cost1)) / (static_cast<double>(A.norm() * B.norm())),
          cos2 = (static_cast<double>(cost2)) / (static_cast<double>(A.norm() * B.norm()));
    return acos(cos2) - acos(cos1);
}
// difference of angles of two solutions normalized to [0, 1] (for most QAPs), where 0 means that the 1st solution (`cost1`) is as good as the 2nd solution (`cost2`) and 1 means that 2 solutions are orthogonal to each other (one is the best and the other is the worst possible solution)
// Normalized to [0, 1] (angular distance divided by pi/2)
double normalized_angular_distance_of_solutions(std::int64_t cost1, std::int64_t cost2, const Matrix<int>& A, const Matrix<int>& B) {
    double cos1 = (static_cast<double>(cost1)) / (static_cast<double>(A.norm() * B.norm())),
          cos2 = (static_cast<double>(cost2)) / (static_cast<double>(A.norm() * B.norm()));
    return 2.0f * (acos(cos2) - acos(cos1)) / PI;
}
// gives ratio of the angle of the solution compared to the angle of the best solution, so that it is normalized to [0, 1], where 0 means that the solution is as good as the best solution and 1 means that the solution is as "bad" as possible (orthogonal to the best solution)
double relative_angular_quality_of_solution(std::int64_t cost, std::int64_t best_cost, const Matrix<int>& A, const Matrix<int>& B) {
    double cos_best = (static_cast<double>(best_cost)) / (static_cast<double>(A.norm() * B.norm())),
          cos_current = (static_cast<double>(cost)) / (static_cast<double>(A.norm() * B.norm()));

    return acos(cos_current)/ acos(cos_best); 
}

// Normalised distance of the cost values
double normalized_cost_distance_of_solutions(std::int64_t cost1, std::int64_t cost2, const Matrix<int>& A, const Matrix<int>& B) {
    double norm_dist = (static_cast<double>(cost1) - static_cast<double>(cost2)) / (static_cast<double>(A.norm() * B.norm()));
    return norm_dist;
}