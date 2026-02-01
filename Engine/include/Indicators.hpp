#pragma once

#include "CircularBuffer.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>


namespace quant {

// Base class for all indicators
class Indicator {
public:
  virtual ~Indicator() = default;
  virtual double update(double value) = 0;
  virtual double value() const = 0;
  virtual bool is_ready() const = 0;
};

// ---------------------------------------------------------
// Simple Moving Average (SMA)
// ---------------------------------------------------------
class SimpleMovingAverage : public Indicator {
public:
  explicit SimpleMovingAverage(int period)
      : period_(period), sum_(0.0), buffer_(period) {}

  double update(double value) override {
    if (buffer_.is_full()) {
      sum_ -= buffer_.get(period_ - 1); // Remove oldest
    }
    buffer_.push(value);
    sum_ += value;

    current_value_ = sum_ / buffer_.size();
    return current_value_;
  }

  double value() const override { return current_value_; }
  bool is_ready() const override { return buffer_.is_full(); }

private:
  int period_;
  double sum_;
  CircularBuffer<double> buffer_;
  double current_value_ = 0.0;
};

// ---------------------------------------------------------
// Exponential Moving Average (EMA)
// ---------------------------------------------------------
class ExponentialMovingAverage : public Indicator {
public:
  explicit ExponentialMovingAverage(int period)
      : period_(period), alpha_(2.0 / (period + 1.0)), initialized_(false),
        current_value_(0.0) {}

  double update(double value) override {
    if (!initialized_) {
      current_value_ = value;
      initialized_ = true;
    } else {
      current_value_ = alpha_ * value + (1.0 - alpha_) * current_value_;
    }
    return current_value_;
  }

  double value() const override { return current_value_; }
  bool is_ready() const override { return initialized_; }

private:
  int period_;
  double alpha_;
  bool initialized_;
  double current_value_;
};

// ---------------------------------------------------------
// Relative Strength Index (RSI)
// ---------------------------------------------------------
class RSI : public Indicator {
public:
  explicit RSI(int period)
      : period_(period), avg_gain_(0.0), avg_loss_(0.0),
        prev_price_(std::nan("")), initialized_count_(0) {}

  double update(double value) override {
    if (std::isnan(prev_price_)) {
      prev_price_ = value;
      return 0.0;
    }

    double change = value - prev_price_;
    prev_price_ = value;

    double gain = (change > 0) ? change : 0.0;
    double loss = (change < 0) ? -change : 0.0;

    // Wilder's Smoothing
    if (initialized_count_ < period_) {
      avg_gain_ += gain;
      avg_loss_ += loss;
      initialized_count_++;

      if (initialized_count_ == period_) {
        avg_gain_ /= period_;
        avg_loss_ /= period_;
      }
    } else {
      avg_gain_ = (avg_gain_ * (period_ - 1) + gain) / period_;
      avg_loss_ = (avg_loss_ * (period_ - 1) + loss) / period_;
    }

    if (initialized_count_ < period_)
      return 0.0;

    if (avg_loss_ == 0) {
      current_value_ = 100.0;
    } else {
      double rs = avg_gain_ / avg_loss_;
      current_value_ = 100.0 - (100.0 / (1.0 + rs));
    }
    return current_value_;
  }

  double value() const override { return current_value_; }
  bool is_ready() const override { return initialized_count_ >= period_; }

private:
  int period_;
  double avg_gain_;
  double avg_loss_;
  double prev_price_;
  int initialized_count_;
  double current_value_ = 0.0;
};

// ---------------------------------------------------------
// Bollinger Bands
// ---------------------------------------------------------
struct BBResult {
  double upper;
  double middle;
  double lower;
  double pct_b;
};

class BollingerBands {
public:
  BollingerBands(int period, double std_dev_mult)
      : period_(period), mult_(std_dev_mult), sma_(period), buffer_(period) {}

  BBResult update(double value) {
    double basis = sma_.update(value);

    buffer_.push(value);

    double variance = 0.0;
    if (buffer_.is_full()) {
      double sum_sq_diff = 0.0;
      for (size_t i = 0; i < buffer_.size(); ++i) {
        double diff = buffer_.get(i) - basis;
        sum_sq_diff += diff * diff;
      }
      variance = sum_sq_diff / period_;
    }

    double std_dev = std::sqrt(variance);

    current_ = {basis + mult_ * std_dev, basis, basis - mult_ * std_dev, 0.0};

    if (current_.upper != current_.lower) {
      current_.pct_b =
          (value - current_.lower) / (current_.upper - current_.lower);
    } else {
      current_.pct_b = 0.5;
    }

    return current_;
  }

  BBResult value() const { return current_; }
  bool is_ready() const { return sma_.is_ready(); }

private:
  int period_;
  double mult_;
  SimpleMovingAverage sma_;
  CircularBuffer<double> buffer_;
  BBResult current_;
};

// ---------------------------------------------------------
// Average True Range (ATR)
// ---------------------------------------------------------
class ATR : public Indicator {
public:
  explicit ATR(int period)
      : period_(period), prev_close_(std::nan("")), initialized_count_(0),
        current_value_(0.0) {}

  double update(double high, double low, double close) {
    double tr = 0.0;
    if (std::isnan(prev_close_)) {
      tr = high - low;
    } else {
      double tr1 = high - low;
      double tr2 = std::abs(high - prev_close_);
      double tr3 = std::abs(low - prev_close_);
      tr = std::max({tr1, tr2, tr3});
    }
    prev_close_ = close;

    if (initialized_count_ < period_) {
      current_value_ += tr;
      initialized_count_++;
      if (initialized_count_ == period_) {
        current_value_ /= period_;
      }
    } else {
      // Wilder's Smoothing: (Prior ATR * (n-1) + Current TR) / n
      current_value_ = (current_value_ * (period_ - 1) + tr) / period_;
    }

    return current_value_;
  }

  // Override standard update
  double update(double value) override { return 0.0; }

  double value() const override { return current_value_; }
  bool is_ready() const override { return initialized_count_ >= period_; }

private:
  int period_;
  double prev_close_;
  int initialized_count_;
  double current_value_;
};

// ---------------------------------------------------------
// Rate of Change (ROC) / Momentum
// (Price_t - Price_t-n) / Price_t-n
// ---------------------------------------------------------
class RateOfChange : public Indicator {
public:
  explicit RateOfChange(int period)
      : period_(period), buffer_(period + 1), current_value_(0.0) {}

  double update(double value) override {
    // We push current value
    buffer_.push(value);

    // We need period+1 items to calculate change over 'period' intervals
    // e.g. ROC(1): need t(new) and t-1(old). Count=2.
    if (buffer_.size() <= (size_t)period_) {
      return 0.0; // Not ready
    }

    // Old price is at index 'period' in logical terms?
    // simple test: period=1. push 10, push 11. size=2.
    // get(0) = 11. get(1) = 10.
    // ROC = (11-10)/10.
    double old_price = buffer_.get(period_);

    if (old_price != 0.0) {
      current_value_ = (value - old_price) / old_price;
    } else {
      current_value_ = 0.0;
    }
    return current_value_;
  }

  double value() const override { return current_value_; }
  bool is_ready() const override { return buffer_.size() > (size_t)period_; }

private:
  int period_;
  CircularBuffer<double> buffer_;
  double current_value_;
};

// ---------------------------------------------------------
// Rolling Statistics (Mean, StdDev, ZScore)
// ---------------------------------------------------------
class RollingStats : public Indicator {
public:
  explicit RollingStats(int period)
      : period_(period), buffer_(period), count_(0), sum_(0.0), sum_sq_(0.0) {}

  double update(double value) override {
    double old_val = 0.0;
    if (buffer_.is_full()) {
      old_val = buffer_.get(period_ - 1);
      sum_ -= old_val;
      sum_sq_ -= old_val * old_val;
    }

    buffer_.push(value);
    sum_ += value;
    sum_sq_ += value * value;

    // Calculate stats
    double n = (double)buffer_.size();
    mean_ = sum_ / n;

    double variance = (sum_sq_ / n) - (mean_ * mean_);
    if (variance < 0)
      variance = 0;
    std_dev_ = std::sqrt(variance);

    if (std_dev_ > 1e-9) {
      zscore_ = (value - mean_) / std_dev_;
    } else {
      zscore_ = 0.0;
    }

    return mean_;
  }

  double value() const override { return mean_; } // Default value is mean
  double std_dev() const { return std_dev_; }
  double zscore() const { return zscore_; }

  bool is_ready() const override { return buffer_.is_full(); }

private:
  int period_;
  CircularBuffer<double> buffer_;
  size_t count_;
  double sum_;
  double sum_sq_;

  double mean_ = 0.0;
  double std_dev_ = 0.0;
  double zscore_ = 0.0;
};

} // namespace quant
