#pragma once

#include <cmath>
#include <cstddef>
#include <numeric>
#include <stdexcept>
#include <vector>


namespace quant {

/**
 * @brief Fixed-size circular buffer for efficient rolling window calculations.
 * Avoids data copying/shifting.
 */
template <typename T> class CircularBuffer {
public:
  explicit CircularBuffer(size_t capacity)
      : buffer_(capacity, T()), capacity_(capacity), head_(0), count_(0) {}

  void push(T value) {
    buffer_[head_] = value;
    head_ = (head_ + 1) % capacity_;
    if (count_ < capacity_)
      count_++;
  }

  T get(size_t index) const {
    if (index >= count_)
      throw std::out_of_range("Index out of bounds");
    // Convert logical index (0 = latest, 1 = previous) to physical index
    // physical = (head - 1 - index + capacity) % capacity
    size_t physical_idx = (head_ - 1 - index + capacity_) % capacity_;
    return buffer_[physical_idx];
  }

  // Access raw buffer for vector-like operations (ordering not guaranteed to be
  // linear in memory) For simple iteration, it's better to use get() or
  // implementing iterators.

  // Quick sum calculation
  T sum() const {
    // This is O(N). For O(1) SMA, maintain a running sum in the SMA class.
    return std::accumulate(buffer_.begin(), buffer_.begin() + count_, T(0));
  }

  size_t size() const { return count_; }
  size_t capacity() const { return capacity_; }
  bool is_full() const { return count_ == capacity_; }

private:
  std::vector<T> buffer_;
  size_t capacity_;
  size_t head_;  // Points to the *next* write position
  size_t count_; // Number of valid elements
};

} // namespace quant
