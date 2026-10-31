#pragma once

// ANSI color codes for terminal output
class Colors {
public:
    // Standard colors
    static constexpr const char* RED     = "\033[31m";
    static constexpr const char* GREEN   = "\033[32m";
    static constexpr const char* YELLOW  = "\033[33m";
    static constexpr const char* BLUE    = "\033[34m";
    static constexpr const char* MAGENTA = "\033[35m";
    static constexpr const char* CYAN    = "\033[36m";
    static constexpr const char* WHITE   = "\033[37m";
    static constexpr const char* ORANGE  = "\033[38;5;208m";
    
    // Bold variants
    static constexpr const char* BOLD_RED     = "\033[1;31m";
    static constexpr const char* BOLD_GREEN   = "\033[1;32m";
    static constexpr const char* BOLD_YELLOW  = "\033[1;33m";
    static constexpr const char* BOLD_BLUE    = "\033[1;34m";
    static constexpr const char* BOLD_MAGENTA = "\033[1;35m";
    static constexpr const char* BOLD_CYAN    = "\033[1;36m";
    static constexpr const char* BOLD_WHITE   = "\033[1;37m";
    
    // Background colors
    static constexpr const char* BG_RED     = "\033[41m";
    static constexpr const char* BG_GREEN   = "\033[42m";
    static constexpr const char* BG_YELLOW  = "\033[43m";
    static constexpr const char* BG_BLUE    = "\033[44m";
    static constexpr const char* BG_ORANGE  = "\033[48;5;208m";
    // Reset
    static constexpr const char* RESET   = "\033[0m";
    
    // Additional formatting
    static constexpr const char* BOLD     = "\033[1m";
    static constexpr const char* DIM      = "\033[2m";
    static constexpr const char* ITALIC   = "\033[3m";
    static constexpr const char* UNDERLINE = "\033[4m";
};

// Example usage:
// printf("%s%s%s\n", Colors::GREEN, "Success!", Colors::RESET);
// printf("%s[INFO]%s Message here\n", Colors::BLUE, Colors::RESET);
// printf("%s%sWarning%s: Something happened\n", Colors::BOLD_YELLOW, Colors::YELLOW, Colors::RESET);
