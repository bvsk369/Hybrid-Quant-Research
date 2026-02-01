#pragma once

#include "Bar.hpp"
#include <algorithm>
#include <ctime>
#include <iostream>
#include <optional>

namespace quant {

// ---------------------------------------------------------
// Risk Manager Configuration
// ---------------------------------------------------------
struct RiskConfig {
  double atr_stop_multiplier = 2.0; // 2x ATR Stop
  double max_drawdown_limit = 0.10; // 10% Max Drawdown
  int max_trades_per_day = 10;      // Prevent 183 trades/day issue
  int cooldown_bars = 5;            // Cooldown after loss
};

// ---------------------------------------------------------
// Risk Manager Logic
// ---------------------------------------------------------
class RiskManager {
public:
  explicit RiskManager(RiskConfig config) : config_(config) {}

  // Check if we can enter a new trade
  bool can_enter(int64_t current_time) {
    // Reset daily trades if day changes
    if (is_new_day(current_time)) {
      trades_today_ = 0;
      last_trade_day_ = current_time;
      // Note: strictly we should store 'current day', but tracking change is
      // enough
    }

    if (trades_today_ >= config_.max_trades_per_day)
      return false;
    if (cooldown_counter_ > 0)
      return false;

    return true;
  }

  // Initialize risk parameters for a new position
  void on_entry(double price, double atr_value, int side) {
    entry_price_ = price;
    highest_price_ = price;
    lowest_price_ = price;
    atr_at_entry_ = atr_value;
    side_ = side;

    // Initial Stop Loss
    if (side == 1) { // Long
      stop_loss_ = price - (atr_at_entry_ * config_.atr_stop_multiplier);
    } else { // Short
      stop_loss_ = price + (atr_at_entry_ * config_.atr_stop_multiplier);
    }

    trades_today_++;
  }

  // Update risk state with new bar (Trailing Stop Logic)
  // Returns TRUE if stop hit
  bool check_exit(const Bar &bar) {
    if (side_ == 0)
      return false;

    // 1. Check Stop Loss
    if (side_ == 1 && bar.low < stop_loss_)
      return true;
    if (side_ == -1 && bar.high > stop_loss_)
      return true;

    // 2. Trailing Stop Logic (Update Stop if price moves in favor)
    if (side_ == 1) {
      if (bar.high > highest_price_) {
        highest_price_ = bar.high;
        // Move stop up
        double new_stop =
            highest_price_ - (atr_at_entry_ * config_.atr_stop_multiplier);
        stop_loss_ = std::max(stop_loss_, new_stop);
      }
    } else {
      if (bar.low < lowest_price_) {
        lowest_price_ = bar.low;
        // Move stop down
        double new_stop =
            lowest_price_ + (atr_at_entry_ * config_.atr_stop_multiplier);
        stop_loss_ = std::min(stop_loss_, new_stop);
      }
    }

    return false;
  }

  void on_exit(bool is_win) {
    side_ = 0;
    if (!is_win) {
      cooldown_counter_ = config_.cooldown_bars;
    }
  }

  void update_cooldown() {
    if (cooldown_counter_ > 0)
      cooldown_counter_--;
  }

private:
  bool is_new_day(int64_t current_time) {
    // Helper to check if current_time day != last_trade_day_ day
    std::time_t t1 = static_cast<std::time_t>(current_time);
    std::time_t t2 = static_cast<std::time_t>(last_trade_day_);

    std::tm *tm1 = std::localtime(&t1);
    int day1 = tm1->tm_mday;
    int year1 = tm1->tm_year;
    int mon1 = tm1->tm_mon;

    std::tm *tm2 = std::localtime(&t2);
    int day2 = tm2->tm_mday;
    int year2 = tm2->tm_year;
    int mon2 = tm2->tm_mon;

    if (year1 != year2 || mon1 != mon2 || day1 != day2) {
      return true;
    }
    return false;
  }

  RiskConfig config_;

  // Position State
  int side_ = 0; // 0=Flat, 1=Long, -1=Short
  double entry_price_ = 0.0;
  double stop_loss_ = 0.0;
  double highest_price_ = 0.0;
  double lowest_price_ = 0.0;
  double atr_at_entry_ = 0.0;

  // Globals
  int trades_today_ = 0;
  int64_t last_trade_day_ = 0;
  int cooldown_counter_ = 0;
};

} // namespace quant
