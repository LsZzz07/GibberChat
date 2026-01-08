cmake_minimum_required(VERSION 3.22.1)

project("gibberlink")

# Define the library name
add_library(
        gibberlink
        SHARED
        native-lib.cpp
        ggwave.cpp
        # Note: 'fft.h' is required by ggwave.cpp but could not be auto-downloaded.
        # Please ensure 'fft.h' is present in this directory.
        # reed-solomon.cpp # Likely header-only (rs.hpp) used now

)

# If the files are missing, compilation will fail.
# We are assuming the user will provide the ggwave source code in the same directory.
# For now, we only link if they exist, or user has to add them.
# To make this robust for the "scaffold" phase:
# We will comment them out and instruct user to uncomment after adding files,
# OR we assume they will add them. 
# Best approach: Add them to sources but acknowledge in walkthrough they need to be present.

target_include_directories(gibberlink PRIVATE .)

find_library(
        log-lib
        log)

target_link_libraries(
        gibberlink
        ${log-lib})
