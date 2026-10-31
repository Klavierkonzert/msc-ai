#pragma once

#include <utility>

namespace random {

void seed(unsigned int value);
int get_random_int(int n);
int get_random_int_minus(int n) ;
double get_random_01();
float get_random_01f() ;
int get_random_int01() ;
std::pair<int, int> get_random_pair0(int n);
std::pair<int, int> get_random_pair(int n);

// New API additions
void seed_global(unsigned int value);
void seed_thread(unsigned int value);
int get_pair_index(int n);

} // namespace random
