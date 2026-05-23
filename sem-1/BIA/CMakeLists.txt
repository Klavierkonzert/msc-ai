cmake_minimum_required(VERSION 3.16)

project(BIA)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(external)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

add_executable(main assignment_12_tasks.cpp)

target_include_directories(main PRIVATE ${Python3_INCLUDE_DIRS})

target_link_libraries(main PRIVATE ${Python3_LIBRARIES})