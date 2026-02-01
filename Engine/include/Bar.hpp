#pragma once

#include <cstdint>
#include <limits>
#include <string>

namespace quant {

/**
 * @brief Represents a single OHLCV bar.
 * Aligned to 64 bytes (cache line) if we add padding, but for now kept compact.
 * 8 bytes * 6 fields = 48 bytes.
 */
struct Bar {
  int64_t timestamp; // Unix timestamp in seconds
  double open;
  double high;
  double low;
  double close;
  double volume;

  // Default constructor
  Bar()
      : timestamp(0), open(0.0), high(0.0), low(0.0), close(0.0), volume(0.0) {}

  // Constructor
  Bar(int64_t ts, double o, double h, double l, double c, double v)
      : timestamp(ts), open(o), high(h), low(l), close(c), volume(v) {}

  // Check if the bar is valid
  bool is_valid() const { return timestamp > 0 && high >= low && open > 0; }
};

} // namespace quant
