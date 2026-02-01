#pragma once

#include "ExecutionEngine.hpp"
#include "MarketDataManager.hpp"
#include "RiskManager.hpp"
#include "Strategies.hpp"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <memory>
#include <vector>


namespace quant {

class Engine {
public:
  Engine()
      : risk_manager_(
            {2.0, 0.10, 20, 5}),    // Limit: 20 Trades/Day (for 1-min data)
        execution_engine_(100000.0) // 100k Capital
  {}

  void load_data(const std::string &symbol, const std::string &filepath) {
    if (market_data_.load_csv(symbol, filepath)) {
      symbol_ = symbol;
    }
  }

  void run() {
    if (symbol_.empty()) {
      std::cerr << "No data loaded!" << std::endl;
      return;
    }

    const auto &bars = market_data_.get_bars(symbol_);
    std::cout << "Starting Backtest on " << symbol_ << " (" << bars.size()
              << " bars)..." << std::endl;

    // Reset Components
    regime_strategy_ = std::make_unique<RegimeStrategy>();
    momentum_strategy_ = std::make_unique<MomentumStrategy>();
    mean_reversion_strategy_ = std::make_unique<MeanReversionStrategy>();

    // Start Timer
    auto start_time = std::chrono::high_resolution_clock::now();

    // Main Event Loop
    for (const auto &bar : bars) {

      // 1. Process Fills (Orders from previous bar execute at Open)
      execution_engine_.on_bar_open(bar);

      // 2. Intra-bar Risk Check (Stops/Targets hit during High/Low?)
      if (execution_engine_.is_invested()) {
        if (risk_manager_.check_exit(bar)) {
          execution_engine_.close_position();
          risk_manager_.on_exit(false); // Stop hit = Loss (mostly)
          // std::cout << "STOP HIT at " << bar.timestamp << std::endl;
        }
      }

      // 3. Update Strategies (End of Bar)
      regime_strategy_->on_bar(bar);
      momentum_strategy_->on_bar(bar);
      mean_reversion_strategy_->on_bar(bar);

      std::string regime = regime_strategy_->regime();

      // 4. Generate Signals & Position Sizing
      int signal = 0;

      // Allocation Logic (from allocator.py)
      if (regime == "LV_TREND" || regime == "HV_TREND") {
        signal = momentum_strategy_->signal();
      } else if (regime == "LV_RANGE") {
        signal = mean_reversion_strategy_->signal();
      } else {
        // HV_RANGE -> Cash
        signal = 0;
      }

      // 5. Execution Logic (if not already in position)
      if (signal != 0 && !execution_engine_.is_invested()) {
        if (risk_manager_.can_enter(bar.timestamp)) {
          // Calculate Allocation (e.g., fixed fractional or fixed size)
          double alloc_amt = 100000.0 * 0.20; // Reduced to 20%
          double qty = alloc_amt / bar.close;

          execution_engine_.submit_order(signal, qty);

          risk_manager_.on_entry(bar.close, bar.close * 0.01,
                                 signal); // Dummy ATR
        }
      } else if (signal == 0 && execution_engine_.is_invested()) {
        execution_engine_.close_position();
        risk_manager_.on_exit(true); // Normal exit
      }

      // Update Churn Cooldown
      risk_manager_.update_cooldown();
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration_us = std::chrono::duration_cast<std::chrono::microseconds>(
                           end_time - start_time)
                           .count();
    double duration_ms = duration_us / 1000.0;
    double bars_per_sec = (bars.size() / duration_ms) * 1000.0;

    std::cout << "\n[BENCHMARK] Processed " << bars.size() << " bars in "
              << duration_ms << " ms (" << std::fixed << std::setprecision(0)
              << bars_per_sec << " bars/sec)\n";

    // Final Reporting
    print_performance_report(bars.back().close);
  }

  void print_performance_report(double current_price) {
    double final_equity = execution_engine_.get_equity(current_price);
    double total_return = (final_equity - 100000.0) / 100000.0 * 100.0;

    const auto &trades = execution_engine_.get_trades();
    int total_trades = trades.size();
    int winning_trades = 0;
    double gross_profit = 0.0;
    double gross_loss = 0.0;

    for (const auto &t : trades) {
      if (t.pnl > 0) {
        winning_trades++;
        gross_profit += t.pnl;
      } else {
        gross_loss += std::abs(t.pnl);
      }
    }

    double win_rate =
        total_trades > 0 ? (double)winning_trades / total_trades * 100.0 : 0.0;
    double profit_factor = gross_loss > 0 ? gross_profit / gross_loss : 99.9;

    std::cout << "\n==========================================\n";
    std::cout << "          PERFORMANCE REPORT              \n";
    std::cout << "==========================================\n";
    std::cout << "Final Equity:   " << std::fixed << std::setprecision(2)
              << final_equity << "\n";
    std::cout << "Total Return:   " << total_return << "%\n";
    std::cout << "------------------------------------------\n";
    std::cout << "Total Trades:   " << total_trades << "\n";
    std::cout << "Win Rate:       " << win_rate << "%\n";
    std::cout << "Profit Factor:  " << profit_factor << "\n";
    std::cout << "Gross Profit:   " << gross_profit << "\n";
    std::cout << "Gross Loss:     " << -gross_loss << "\n";
    std::cout << "==========================================\n";
  }

private:
  MarketDataManager market_data_;
  std::string symbol_;

  // Components
  RiskManager risk_manager_;
  ExecutionEngine execution_engine_;

  // Strategies
  std::unique_ptr<RegimeStrategy> regime_strategy_;
  std::unique_ptr<MomentumStrategy> momentum_strategy_;
  std::unique_ptr<MeanReversionStrategy> mean_reversion_strategy_;
};

} // namespace quant
