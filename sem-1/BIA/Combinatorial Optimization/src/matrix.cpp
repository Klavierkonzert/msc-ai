#pragma once

#include <type_traits>
#include <cstdint>
#include <stdexcept>

#include <limits> 
#include <string>

#include <cmath>
#include <tuple>
#include <iostream>
#include <utility>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <unordered_map>
#include <map>
#include <functional>

#include "permutation.cpp"


template <typename T=int>
class Matrix;

template <typename T>
class Matrix {
private:
    using SumType = std::conditional_t<std::is_integral_v<T>, std::int64_t, T>;
    
    T** m_data;
    int nrows, ncols;

    mutable struct Cache{
        double skewness = 0.0;  
        double variance = 0.0;  
        double mean = 0.0;
        double norm = 0.0;
        SumType trace = SumType(0);
        

        bool symmetry = false;
        bool zero_diagonality = false;

        bool is_valid = false;
    } cache;


    void allocate(int rows, int cols);
    void deallocate();

    void copy_from(const Matrix& other);

    inline bool compute_zero_diagonality() const;
    inline bool compute_symmetry() const;
    inline typename SumType compute_trace() const;
    inline double compute_norm() const;

    void recompute_cache() const;
public:
    //default constructor that initializes an empty matrix with 0 rows and 0 columns
    Matrix() : m_data(nullptr), nrows(0), ncols(0), cache() {}

    // Constructor that allocates memory for a square matrix of size n x n
    Matrix(int n) : m_data(nullptr), nrows(0), ncols(0), cache() {
        allocate(n, n);
    }
    Matrix(int rows, int cols) : m_data(nullptr), nrows(0), ncols(0), cache() {
        allocate(rows, cols);
    }
    ~Matrix() {
        deallocate();
    }

    Matrix(const Matrix& other) : m_data(nullptr), nrows(0), ncols(0), cache() {
        copy_from(other);
    }

    Matrix& operator=(const Matrix& other) {
        if (this == &other) {
            return *this;
        }
        deallocate();
        copy_from(other);
        return *this;
    }

    Matrix(Matrix&& other) noexcept : m_data(other.m_data), nrows(other.nrows), ncols(other.ncols), cache(other.cache) {
        other.m_data = nullptr;
        other.nrows = 0;
        other.ncols = 0;
        other.cache = {};
    }

    Matrix& operator=(Matrix&& other) noexcept {
        if (this == &other) {
            return *this;
        }
        deallocate();
        m_data = other.m_data;
        nrows = other.nrows;
        ncols = other.ncols;
        cache = other.cache;
        other.m_data = nullptr;
        other.nrows = 0;
        other.ncols = 0;
        other.cache = {};
        return *this;
    }
    // Constructor that takes a 2D array and its dimensions, and allocates memory and initializes the matrix with the values from the array
    Matrix(T** data, int rows, int cols) : m_data(nullptr), nrows(0), ncols(0), cache() {
        allocate(rows, cols);
        for (int i = 0; i < nrows; i++) {
            for (int j = 0; j < ncols; j++) {
                m_data[i][j] = data[i][j];
            }
        }
        recompute_cache();
    }
    // Constructor that takes a file pointer and reads the matrix from the file, given the number of rows and columns
    Matrix(std::FILE* file, int rows, int cols) : m_data(nullptr), nrows(0), ncols(0), cache() {
        allocate(rows, cols);
        for (int i = 0; i < nrows; i++) {
            for (int j = 0; j < ncols; j++) {
                fscanf(file, "%d", &m_data[i][j]);
            }
        }
        recompute_cache();
    }

    // returns the dimensions of the matrix as a pair (number of rows, number of columns)
    std::pair<int, int> size() const { return std::make_pair(nrows, ncols); }
    // returns the number of rows
    int rows() const { return nrows;}
    // returns the number of columns   
    int cols() const { return ncols;}

    T& operator()(int i, int j) {
        cache.is_valid = false;
        return m_data[i][j];
    }
    const T& operator()(int i, int j) const {
        return m_data[i][j];
    }
    T* operator[](int i) {
        cache.is_valid = false;
        return m_data[i];
    }
    const T* operator[](int i) const {
        return m_data[i];
    }

    void print(std::string msg = "", std::string delim = " ") const;

    // checks if the matrix is sparse, i.e. if the proportion of non-zero elements is less than a given threshold (default is 0.1)
    bool is_sparse(double threshold = 0.1) const;

    // checks if the matrix is mostly constant, i.e. if the proportion of the most common value is greater than a given threshold (default is 0.9)
    bool is_mostly_const(double threshold = 0.9) const;

    // checks if the matrix has low variance, i.e. if the variance of the elements is less than a given threshold (default is 0.1)
    bool is_low_variance(double threshold = 0.1) const;

    // @brief Find the minimum element in the matrix and its indices, if row is specified, find the minimum element in that `row`, starting from `start_col` if specified
    // @return the value and indices of the minimal element in the matrix, optionally only in a specified row and starting from a specified column.
    // @note If `row>=0`, the the first index is guaranteed to be equal to `row`
    std::tuple<T,int,int> find_min_element(int row = -1, int start_col = -1) const;
    // @brief Find the maximum element in the matrix and its indices, if row is specified, find the maximum element in that `row`, starting from `start_col` if specified
    // @return the value and indices of the largest element in the matrix, optionally only in a specified row and starting from a specified column.
    // @note If `row>=0`, the the first index is guaranteed to be equal to `row`
    std::tuple<T,int,int> find_max_element(int row = -1, int start_col = -1) const;
    
    // returns the value and the index of the row with the lowest euclidean norm
    std::tuple<T,int> find_min_row(int start_row=-1) const;
    // returns the value and the index of the row with the highest euclidean norm
    std::tuple<T,int> find_max_row(int start_row=-1) const;
    // returns the value and the index of the column with the lowest euclidean norm
    std::tuple<T,int> find_min_col(int start_col=-1) const;
    // returns the value and the index of the column with the highest euclidean norm
    std::tuple<T,int> find_max_col(int start_col =-1) const;



    // @brief Applies a reduction function `f` to the elements of the matrix and returns the sum of the results. 
    // @param symmetrical_reduction if true and the matrix is symmetric, only the upper triangle (including diagonal if trace is non-zero, excluding otherwise) is reduced and the result is multiplied by 2. Otherwise, all elements are reduced.
    // @return `std::pair<double, int>` containing the sum of the results and the number of elements that were reduced.
    std::pair<double, int> reduce(std::function<double(double)> f, bool symmetrical_reduction=false) const;

    // @brief Computes the Frobenius norm of the matrix. Invariant to symmetric permtations (`B=PAP^T`).
    //
    // If no mutation has been made to the matrix since the last time the norm was computed, the cached value of the norm is returned. Otherwise, the norm is recomputed and the cache is updated before returning the value.
    double norm() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.norm;
    }
    

    // @brief Checks whether matrix is quadratic, i.e. both dimensions are equal.
    //
    //Invariant to symmetric permtations (`B=PAP^T`).
    inline bool is_quadratic() const {return nrows == ncols;}

    // @brief Computes symmetry of the matrix. 
    //
    //Invariant to symmetric permtations (`B=PAP^T`).
    //
    // If no mutation has been made to the matrix since the last time the norm was computed, the cached value is returned. Otherwise, the symmetry is recomputed and the cache is updated before returning the value.
    bool is_symmetric() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.symmetry;
    }
    
    // @brief Computes trace of the matrix. 
    //
    // Invariant to symmetric permtations (`B=PAP^T`).
    inline auto trace() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.trace;
    }

    // @brief Checks if the matrix has zero diagonal. Invariant to symmetric permtations (`B=PAP^T`).
    inline bool is_zero_diagonal() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.zero_diagonality;
    }

    /**************************************************************** Cached descriptive statistics**************************************************************************************/
    
    // @brief If matrix is symmetric, returns mean of the elements of the upper triangle [including or excluding diagonal - if trace is zero, diagonal elements are excluded]. Otherwise returns mean of all the elements of the matrix.
    inline double mean() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.mean;
    }

    // @brief If matrix is symmetric, returns variance (max likelihood estimate) of the elements of the upper triangle [including or excluding diagonal - if trace is zero, diagonal elements are excluded]. Otherwise returns variance of all the elements of the matrix.
    //
    // If data represents a sample, rather than the entire population, the further correction for unbiased estimation can be applied by multiplying the variance by `n/(n-1)`, where `n` is the number of elements in the sample. 
    inline double var() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.variance;
    }

    // @brief If matrix is symmetric, returns standard deviation (max likelihood estimate) of the elements of the upper triangle [including or excluding diagonal - if trace is zero, diagonal elements are excluded]. Otherwise returns standard deviation of all the elements of the matrix.
    //
    // If data represents a sample, rather than the entire population, the further correction for unbiased estimation can be applied by multiplying the variance by `sqrt(n/(n-1))`, where `n` is the number of elements in the sample. 
    inline double std() const {return sqrt(var());}

    // @brief Skewness coefficient (Fisher-Pearson).
    //
    // If matrix is symmetric, returns skewness of the elements of the upper triangle [including or excluding diagonal - if trace is zero, diagonal elements are excluded]. Otherwise returns skewness of all the elements of the matrix.
    //
    // If data represents a sample, rather than the entire population, the further correction for unbiased estimation can be applied by multiplying the skewness by `n*n/((n-1)*(n-2))`, where `n` is the number of elements in the sample.
    inline double skewness() const {
        if (!cache.is_valid)
            recompute_cache();
        return cache.skewness;
    }

    // @brief Coefficient of variation, defined as the ratio of the standard deviation to the mean. 
    //
    //Invariant to symmetric permtations (`B=PAP^T`).
    //
    // If matrix is symmetric, returns coefficient of variation of the elements of the upper triangle [including or excluding diagonal - if trace is zero, diagonal elements are excluded]. Otherwise returns coefficient of variation of all the elements of the matrix.
    inline double cv() const {
        auto mean_value = mean();
        if (mean_value != 0.0)
            return std() / mean_value;
        else
            return 0.0; // if mean is zero, all elements are zero, so coefficient of variation is zero
    }
};  

template <typename T>
void Matrix<T>::allocate(int rows, int cols) {
        nrows = rows;
        ncols = cols;
        cache.norm = 0.0;
        cache.is_valid = false;
        if (nrows == 0 || ncols == 0) {
            m_data = nullptr;
            cache.is_valid = true;
            return;
        }
        m_data = new T*[nrows];
        for (int i = 0; i < nrows; i++) {
            m_data[i] = new T[ncols];
        }
    }

template <typename T>
void Matrix<T>::deallocate() {
        if (!m_data) {
            cache.norm = 0.0;
            cache.is_valid = true;
            return;
        }
        for (int i = 0; i < nrows; i++) {
            delete[] m_data[i];
        }
        delete[] m_data;
        m_data = nullptr;
        nrows = 0;
        ncols = 0;
        cache.norm = 0.0;
        cache.is_valid = true;
    }

template <typename T>
void Matrix<T>::copy_from(const Matrix& other) {
        allocate(other.nrows, other.ncols);
        for (int i = 0; i < nrows; i++) {
            for (int j = 0; j < ncols; j++) {
                m_data[i][j] = other.m_data[i][j];
            }
        }
        cache  = other.cache;
    }

/*************************************************************** Statistics functions********************************************************************************/
template <typename T>
inline std::pair<double, int> Matrix<T>::reduce(std::function<double(double)> f, 
                                                bool symmetrical_reduction) const {
    double sum = 0.0, diagonal_sum = 0.0;

    if (!cache.symmetry){
        for (int i = 0; i < nrows; i++)
            for (int j = 0; j < ncols; j++)
                sum += f(static_cast<double>(m_data[i][j]));
        return  {sum, nrows * ncols};
    }
    // matrix is symmetric: if `reduced` is true, return `f` is calculated for the triangle (including diagonal if trace is non-zero, excluding otherwise)
    else{
        if (cache.zero_diagonality)
        {
            for (int i = 0; i < nrows; i++)
                for (int j = i+1; j < ncols; j++)
                    sum += f(static_cast<double>(m_data[i][j]));
            if (symmetrical_reduction)
                return {sum, (nrows * (ncols - 1)) / 2};
            else
                sum *= 2.0; // f calculated for 2 identical yet opposite triangles of the matrix
        }
        else{
            for (int i = 0; i < nrows; i++){
                for (int j = i+1; j < ncols; j++)
                    sum += f(static_cast<double>(m_data[i][j]));
                // diagonal elements:
                diagonal_sum += f(static_cast<double>(m_data[i][i]));
            }
            if (symmetrical_reduction)
                return {(sum + diagonal_sum), (nrows * (ncols + 1)) / 2};
            else
                sum = 2.0 * sum + diagonal_sum; // sum calculated for 2 identical yet opposite triangles of the matrix, plus diagonal elements counted once
        }
        return  {sum, nrows * ncols};
    }
}

/******************************* Recomputing cached characteristics: norm, symmetry, etc. ********************************/
template <typename T>
inline bool Matrix<T>::compute_symmetry() const {
    if (nrows != ncols)
        return false;
    for (int i = 0; i < nrows; i++) 
        for (int j = i+1; j < ncols; j++) 
            if (m_data[i][j]!=m_data[j][i])
                return false;
    return true;
}

template <typename T>
inline bool Matrix<T>::compute_zero_diagonality() const {
    int n  =nrows>ncols? ncols : nrows; // if not square, check zero diagonality for the largest possible square submatrix
    for (int i = 0; i < n; i++) 
        if (m_data[i][i] != 0)
            return false;
    return true;
}

template <typename T>
inline typename Matrix<T>::SumType Matrix<T>::compute_trace() const {
    if (nrows != ncols)
        throw std::logic_error("Trace is defined only for square matrices");

    SumType sum = SumType{};
    for (int i = 0; i < nrows; ++i)
        sum += m_data[i][i];
    return sum;
}

template <typename T>
inline double Matrix<T>::compute_norm() const {
    double sum = 0.0;
    if (!cache.symmetry)
        for (int i = 0; i < nrows; i++)
            for (int j = 0; j < ncols; j++) {
                const double value = static_cast<double>(m_data[i][j]);
                sum += value * value;
            }
    else
        for (int i = 0; i < nrows; i++){
            const double value = static_cast<double>(m_data[i][i]);
            sum += value * value;
            for (int j = i+1; j < ncols; j++) {
                const double value = static_cast<double>(m_data[i][j]);
                sum += 2.0 *value * value;
            }
        }
    return std::sqrt(sum);
}


template <typename T>
void Matrix<T>::recompute_cache() const {
    cache.zero_diagonality = compute_zero_diagonality();
    cache.symmetry = compute_symmetry();
    cache.trace = compute_trace(); 
    cache.norm = compute_norm();
    auto [m, sample_size] = reduce([](double x){ return x; }, true);
        cache.mean = m/ static_cast<double>(sample_size);
    auto [v, sample_size_] = reduce([mean = this->cache.mean](double x)
                                                            { 
                                                                const double d = x - mean;
                                                                return d * d; }, 
                                                        true);
        cache.variance = v/static_cast<double>(sample_size_);
    auto [sk, sample_size__] = reduce([mean = this->cache.mean](double x)
                                                                    { 
                                                                        const double d = x - mean;
                                                                        return d * d * d; }, 
                                                                    true);
        if (cache.variance > 0.0)
            cache.skewness = sk/ (static_cast<double>(sample_size__) * cache.variance * std::sqrt(cache.variance));
        else
            cache.skewness = 0.0; // if variance is zero, all elements are identical, so skewness is zero

    cache.is_valid = true;
}




/***************************************************************************************************/ 

template <typename T>
void Matrix<T>::print(std::string msg, std::string delim) const {
        if (!msg.empty()) {
            std::cout << msg << std::endl;
        }
        for (int i = 0; i < nrows; i++) {
            for (int j = 0; j < ncols; j++) {
                std::cout << m_data[i][j] << delim;
            }
            std::cout << std::endl;
        }
    }
template <typename T>
bool Matrix<T>::is_sparse(double threshold) const {
        int non_zero_count = 0;
        for (int i = 0; i < nrows; i++) {
            for (int j = 0; j < ncols; j++) {
                if (m_data[i][j] != 0) {
                    non_zero_count++;
                }
            }
        }
        double sparsity = static_cast<double>(non_zero_count) / (nrows * ncols);
        return sparsity < threshold;
    }

template <typename T>
bool Matrix<T>::is_mostly_const(double threshold) const {
        int most_common_value_count = 0;
        std::map<T, int> value_counts;
        for (int i = 0; i < nrows; i++) {
            for (int j = 0; j < ncols; j++) {
                value_counts[m_data[i][j]]++;
                if (value_counts[m_data[i][j]] > most_common_value_count) {
                    most_common_value_count = value_counts[m_data[i][j]];
                }
            }
        }
        double most_common_value_proportion = static_cast<double>(most_common_value_count) / (nrows * ncols);
        return most_common_value_proportion > threshold;
    }

template <typename T>
bool Matrix<T>::is_low_variance(double threshold) const {
    if (nrows == 0 || ncols == 0 || m_data == nullptr)
        return true;
    if (!cache.is_valid)
        recompute_cache();
    return var() *(nrows==ncols? nrows : sqrt(nrows*ncols)) /norm() < threshold;
}

template <typename T>
std::tuple<T,int,int> Matrix<T>::find_min_element(int row, int start_col) const {
    if (nrows == 0 || ncols == 0 || m_data == nullptr) {
        throw std::runtime_error("Matrix is empty; cannot find minimum element.");
    }
        T min_val = m_data[0][0];
        int min_i = 0, min_j = 0;
        if (row != -1) {
            for (int j = start_col > 0 ? start_col : 0; j < ncols; j++) {
                if (m_data[row][j] < min_val) {
                    min_val = m_data[row][j];
                    min_i = row;
                    min_j = j;
                }
            }
        } else {
            for (int i = 0; i < nrows; i++) {
                for (int j = 0; j < ncols; j++) {
                    if (m_data[i][j] < min_val) {
                        min_val = m_data[i][j];
                        min_i = i;
                        min_j = j;
                    }
                }
            }
        }
        return std::make_tuple(min_val, min_i, min_j);
    }
template <typename T>
std::tuple<T,int,int> Matrix<T>::find_max_element(int row, int start_col) const {
    if (nrows == 0 || ncols == 0 || m_data == nullptr) {
        throw std::runtime_error("Matrix is empty; cannot find maximum element.");
    }
        T max_val = m_data[0][0];
        int max_i = 0, max_j = 0;
        if (row != -1) {
            for (int j = start_col > 0 ? start_col : 0; j < ncols; j++) {
                if (m_data[row][j] > max_val) {
                    max_val = m_data[row][j];
                    max_i = row;
                    max_j = j;
                }
            }
        } else {
            for (int i = 0; i < nrows; i++) {
                for (int j = 0; j < ncols; j++) {
                    if (m_data[i][j] > max_val) {
                        max_val = m_data[i][j];
                        max_i = i;
                        max_j = j;
                    }
                }
            }
        }
        return std::make_tuple(max_val, max_i, max_j);
    }

template <typename T>
std::tuple<T,int> Matrix<T>::find_min_row(int start_row) const {
    if (nrows == 0 || ncols == 0 || m_data == nullptr) {
        throw std::runtime_error("Matrix is empty; cannot find minimum row.");
    }
        T min_row_norm_squared = std::numeric_limits<T>::max();
        int min_row_i = 0;
        for (int i = (start_row==-1? 0: start_row); i < nrows; i++) {
            double row_norm_squared = 0.0;
            for (int j = 0; j < ncols; j++) {
                row_norm_squared += static_cast<double>(m_data[i][j]) * m_data[i][j];
            }
            if (row_norm_squared < min_row_norm_squared) {
                min_row_norm_squared = row_norm_squared;
                min_row_i = i;
            }
        }
        return std::make_tuple(std::sqrt(min_row_norm_squared), min_row_i);
    }
template <typename T>
std::tuple<T,int> Matrix<T>::find_max_row(int start_row) const {
    if (nrows == 0 || ncols == 0 || m_data == nullptr) {
        throw std::runtime_error("Matrix is empty; cannot find maximum row.");
    }
        T max_row_norm_squared = std::numeric_limits<T>::lowest();
        int max_row_i = 0;
        for (int i = (start_row==-1? 0: start_row); i < nrows; i++) {
            double row_norm_squared = 0.0;
            for (int j = 0; j < ncols; j++) {
                row_norm_squared += static_cast<double>(m_data[i][j]) * m_data[i][j];
            }
            if (row_norm_squared > max_row_norm_squared) {
                max_row_norm_squared = row_norm_squared;
                max_row_i = i;
            }
        }
        return std::make_tuple(std::sqrt(max_row_norm_squared), max_row_i);
    }
template <typename T>
std::tuple<T,int> Matrix<T>::find_min_col(int start_col) const {
    if (nrows == 0 || ncols == 0 || m_data == nullptr) {
        throw std::runtime_error("Matrix is empty; cannot find minimum column.");
    }
        T min_col_norm_squared = std::numeric_limits<T>::max();
        int min_col_j = 0;
        for (int j = (start_col==-1? 0: start_col); j < ncols; j++) {
            double col_norm_squared = 0.0;
            for (int i = 0; i < nrows; i++) {
                col_norm_squared += static_cast<double>(m_data[i][j]) * m_data[i][j];
            }
            if (col_norm_squared < min_col_norm_squared) {
                min_col_norm_squared = col_norm_squared;
                min_col_j = j;
            }
        }
        return std::make_tuple(std::sqrt(min_col_norm_squared), min_col_j);
    }