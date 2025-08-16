# app/src/main/cpp/CMakeLists.txt
cmake_minimum_required(VERSION 3.18.1)
project("pqc_native")

add_library(
        pqc_native
        SHARED
        dilithium_signer.c
)

find_library(log-lib log)

target_include_directories(pqc_native PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(pqc_native ${log-lib})