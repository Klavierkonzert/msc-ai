#pragma once

#include <ctime>
#include <omp.h>

// Returns a reference to a static boolean that indicates whether to use CPU time clock (std::clock)
// or wall clock (omp_get_wtime) for measuring algorithm run times.
inline bool& use_cpu_time_clock() {
    static bool enabled = false;
    return enabled;
}

// Sets whether to use CPU time clock (std::clock) or wall clock (omp_get_wtime)
// for measuring algorithm run times.
inline void set_use_cpu_time_clock(bool enabled) {
    use_cpu_time_clock() = enabled;
}

// Returns current time in seconds, using either CPU time or wall clock
// based on `use_cpu_time_clock` setting.
inline double algorithm_time_now() {
    if (use_cpu_time_clock()) {
        return static_cast<double>(std::clock()) / static_cast<double>(CLOCKS_PER_SEC);
    }
    return omp_get_wtime();
}

// Returns timer resolution (seconds per tick) for the active timing mode.
inline double get_time_resolution() {
    if (use_cpu_time_clock()) {
        return 1.0 / static_cast<double>(CLOCKS_PER_SEC);
    }
    return omp_get_wtick();
}
