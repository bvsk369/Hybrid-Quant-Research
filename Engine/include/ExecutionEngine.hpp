#pragma once

#include "Bar.hpp"
#include <cmath>
#include <iostream>
#include <vector>

namespace quant {

struct Order {
  int id;
  int64_t timestamp;
  int side; // 1=Buy, -1=Sell
  double quantity;
  double price; // 0 for Market
};

struct Trade {
  int64_t entry_time;
  int64_t exit_time;
  double entry_price;
  double exit_price;
  int side;
  double pnl;
};

class ExecutionEngine {
public:
  ExecutionEngine(double initial_capital = 100000.0)
      : capital_(initial_capital), position_(0), cash_(initial_capital) {}

  void submit_order(int side, double quantity) {
    // In a real system, adds to queue. Here we just set "next order"
    pending_order_side_ = side;
    pending_order_qty_ = quantity;
  }

  void close_position() {
    if (position_ != 0) {
      submit_order(-position_side_, std::abs(position_));
    }
  }

  // Simulates filling orders at the OPEN of the current bar
  void on_bar_open(const Bar &bar) {
    if (pending_order_side_ != 0) {
      execute_trade(bar.timestamp, pending_order_side_, pending_order_qty_,
                    bar.open);
      pending_order_side_ = 0;
      pending_order_qty_ = 0;
    }
  }

  double get_equity(double current_price) const {
    return cash_ + (position_ * current_price);
  }

  double get_position() const { return position_; }
  bool is_invested() const { return position_ != 0; }

  const std::vector<Trade> &get_trades() const { return trades_; }

private:
  void execute_trade(int64_t time, int side, double qty, double price) {
    double cost = qty * price;
    // Simple fee model (0.05%) - DISABLED FOR COMPARISON
    double fee = 0.0; // cost * 0.0005;

    // Capture Entry Details
    if (position_ == 0 && side != 0) {
      last_entry_time_ = time;
      last_entry_price_ = price;
    }

    if (side == 1) { // BUY
      cash_ -= (cost + fee);
      position_ += qty;
    } else { // SELL
      cash_ += (cost - fee);
      position_ -= qty;
    }

    // Capture Exit / Trade Record
    // logic: If we just went from Invested -> Flat (0), that's a closed trade.
    // Assumptions: No partial closes, no reversing (Long -> Short) in 1 step
    // for now.
    if (std::abs(position_) < 1e-9 && position_side_ != 0) {
      // We just closed a position.
      Trade t;
      t.entry_time = last_entry_time_;
      t.exit_time = time;
      t.entry_price = last_entry_price_;
      t.exit_price = price;
      t.side = position_side_;

      // PnL calc
      if (position_side_ == 1) { // Long
        t.pnl = (t.exit_price - t.entry_price) * qty;
      } else { // Short
        t.pnl = (t.entry_price - t.exit_price) * qty;
      }
      // Subtract fees (Entry + Exit fee approx)
      double total_fee = 0.0; // (t.entry_price * qty * 0.0005) + (t.exit_price
                              // * qty * 0.0005);
      t.pnl -= total_fee;

      trades_.push_back(t);
    }

    // Update State
    if (std::abs(position_) > 1e-9)
      position_side_ = (position_ > 0) ? 1 : -1;
    else
      position_side_ = 0;

    // std::cout << ">> EXEC: " << (side == 1 ? "BUY" : "SELL") << " " << qty
    //           << " @ " << price << " | Cash: " << cash_ << std::endl;
  }

  double capital_;
  double cash_;
  double position_ = 0.0;
  int position_side_ = 0;

  // Trade Tracking
  int64_t last_entry_time_ = 0;
  double last_entry_price_ = 0.0;

  int pending_order_side_ = 0;
  double pending_order_qty_ = 0.0;

  std::vector<Trade> trades_;
};

} // namespace quant
