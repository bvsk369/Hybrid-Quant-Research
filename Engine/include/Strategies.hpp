#pragma once

#include "Bar.hpp"
#include "Indicators.hpp"
#include <iostream>
#include <string>

namespace quant {

// ---------------------------------------------------------
// REPLICATED PYTHON STRATEGY CONSTANTS
// ---------------------------------------------------------
// Momentum
constexpr int MOMENTUM_PERIOD = 100; // ~100 mins
constexpr int RANKING_PERIOD = 100;
constexpr double MOMENTUM_ENTRY_THRESHOLD = 1.5;

// Mean Reversion
constexpr int BB_PERIOD = 100; // ~100 mins
constexpr double BB_STD_DEV = 2.0;
constexpr int RSI_PERIOD = 20; // Slightly longer RSI
constexpr double BB_LONG_THRESHOLD = -0.8;
constexpr double BB_SHORT_THRESHOLD = 0.8;
constexpr double RSI_LONG_THRESHOLD = 30.0;
constexpr double RSI_SHORT_THRESHOLD = 70.0;

// Regime
constexpr int VOL_SHORT = 50;  // ~50 mins
constexpr int VOL_LONG = 200;  // ~200 mins
constexpr int TREND_SMA = 300; // ~5 hours trend
constexpr double TREND_THRESHOLD =
    0.005; // Lower threshold slightly for 1-min noise

// ---------------------------------------------------------
// Base Strategy Interface
// ---------------------------------------------------------
class Strategy {
public:
  virtual ~Strategy() = default;

  // Called once per bar with the latest data
  virtual void on_bar(const Bar &bar) = 0;

  // Returns the current signal (-1, 0, 1)
  virtual int signal() const = 0;

  // Returns the current regime logic name (for debugging)
  virtual std::string name() const = 0;
};

// ---------------------------------------------------------
// Regime Detector Strategy (Logic from regimes.py)
// ---------------------------------------------------------
class RegimeStrategy : public Strategy {
public:
  RegimeStrategy()
      : vol_short_(VOL_SHORT), vol_long_(VOL_LONG), sma_trend_(TREND_SMA),
        last_close_(0.0), current_regime_("UNDEFINED") {}

  void on_bar(const Bar &bar) override {
    // Update Indicators
    // Volatility requires log returns.
    if (last_close_ > 0) {
      double log_ret = std::log(bar.close / last_close_);
      vol_short_.update(log_ret);
      vol_long_.update(log_ret);
    }
    last_close_ = bar.close;

    sma_trend_.update(bar.close);

    if (!vol_long_.is_ready() || !sma_trend_.is_ready()) {
      return;
    }

    // Logic Replicated from regimes.py
    // low_vol = vol_20 < vol_60
    bool low_vol = vol_short_.std_dev() < vol_long_.std_dev();

    // trend_strength = abs(close - sma_60) / sma_60
    double sma_val = sma_trend_.value();
    double trend_strength = std::abs(bar.close - sma_val) / sma_val;
    bool trending = trend_strength > TREND_THRESHOLD;

    if (low_vol && trending)
      current_regime_ = "LV_TREND";
    else if (!low_vol && trending)
      current_regime_ = "HV_TREND";
    else if (low_vol && !trending)
      current_regime_ = "LV_RANGE";
    else
      current_regime_ = "HV_RANGE";
  }

  int signal() const override {
    return 0; // Regime detector doesn't emit trade signals directly in this
              // architecture
  }

  std::string regime() const { return current_regime_; }
  std::string name() const override { return "RegimeDetector"; }

private:
  RollingStats vol_short_; // To get std_dev of returns
  RollingStats vol_long_;
  SimpleMovingAverage sma_trend_;
  double last_close_;
  std::string current_regime_;
};

// ---------------------------------------------------------
// Momentum Strategy (Logic from momentum.py)
// ---------------------------------------------------------
// ---------------------------------------------------------
// Momentum Strategy (Logic from momentum.py - Enhanced)
// ---------------------------------------------------------
class MomentumStrategy : public Strategy {
public:
  MomentumStrategy()
      : roc_(MOMENTUM_PERIOD), roc_zscore_(RANKING_PERIOD), ema_12_(12),
        ema_26_(26), vol_avg_(20), rsi_(14), current_signal_(0),
        last_zscore_(0.0) {}

  void on_bar(const Bar &bar) override {
    // 1. Update Core Indicators
    double mom = roc_.update(bar.close);
    roc_zscore_.update(mom);

    // 2. Update Enhanced Filters
    ema_12_.update(bar.close);
    ema_26_.update(bar.close);
    vol_avg_.update(bar.volume);
    rsi_.update(bar.close);

    if (!roc_zscore_.is_ready() || !ema_26_.is_ready() ||
        !vol_avg_.is_ready() || !rsi_.is_ready())
      return;

    // 3. Logic (Replicating momentum_signal_enhanced from python)
    double z = roc_zscore_.zscore();
    double rsi_val = rsi_.value();

    bool trend_up = ema_12_.value() > ema_26_.value();
    bool trend_down = ema_12_.value() < ema_26_.value();

    bool high_volume = bar.volume > vol_avg_.value();

    bool rsi_not_extreme_high = rsi_val < 75.0;
    bool rsi_not_extreme_low = rsi_val > 25.0;

    // Momentum Acceleration (zscore increasing/decreasing)
    bool momentum_accel = (z > last_zscore_); // Long case
    bool momentum_decel = (z < last_zscore_); // Short case
    last_zscore_ = z;

    // Entry Logic
    bool long_entry = (z > MOMENTUM_ENTRY_THRESHOLD) && trend_up &&
                      high_volume && rsi_not_extreme_high && momentum_accel;
    bool short_entry = (z < -MOMENTUM_ENTRY_THRESHOLD) && trend_down &&
                       high_volume && rsi_not_extreme_low && momentum_decel;

    // Exit Condition (Momentum Weakening - exit_zscore default 0.3)
    double exit_zscore = 0.3;
    bool momentum_weak = std::abs(z) < exit_zscore;

    if (long_entry) {
      current_signal_ = 1;
    } else if (short_entry) {
      current_signal_ = -1;
    } else if (momentum_weak) {
      current_signal_ = 0;
    }
    // Else hold previous signal (no change) implied
  }

  int signal() const override { return current_signal_; }
  std::string name() const override { return "MomentumEnhanced"; }

private:
  RateOfChange roc_;
  RollingStats roc_zscore_;

  // Enhanced Filters
  ExponentialMovingAverage ema_12_;
  ExponentialMovingAverage ema_26_;
  SimpleMovingAverage vol_avg_;
  RSI rsi_;

  int current_signal_;
  double last_zscore_;
};

// ---------------------------------------------------------
// Mean Reversion Strategy (Logic from mean_reversion.py)
// ---------------------------------------------------------
// ---------------------------------------------------------
// Mean Reversion Strategy (Logic from mean_reversion.py - Enhanced)
// ---------------------------------------------------------
class MeanReversionStrategy : public Strategy {
public:
  MeanReversionStrategy()
      : bb_(BB_PERIOD, BB_STD_DEV), rsi_(RSI_PERIOD), vol_20_(20), vol_60_(60),
        current_signal_(0) {}

  void on_bar(const Bar &bar) override {
    // 1. Update Indicators
    BBResult bb_res = bb_.update(bar.close);
    double rsi_val = rsi_.update(bar.close);

    // Update Volatility (needs log returns)
    // Assuming simple return approx or tracking last close
    if (last_close_ > 0) {
      double log_ret = std::log(bar.close / last_close_);
      vol_20_.update(log_ret);
      vol_60_.update(log_ret);
    }
    last_close_ = bar.close;

    if (!bb_.is_ready() || !rsi_.is_ready() || !vol_60_.is_ready())
      return;

    // 2. Calculate Derived Values
    double std_dev = (bb_res.upper - bb_res.middle) / BB_STD_DEV;
    double bb_pos = 0.0;
    if (std_dev > 0) {
      bb_pos = (bar.close - bb_res.middle) / (BB_STD_DEV * std_dev);
    }

    // 3. Logic Matching mean_reversion_signal_enhanced
    // Parameters from Python Enhanced:
    // bb_threshold = 0.6
    // rsi_oversold = 35, rsi_overbought = 65
    // use_volatility_filter = True (vol_20 < vol_60)

    const double FILTER_BB_THRESH = 0.8; // Stricter (was 0.6)
    const double FILTER_RSI_LOW = 30.0;  // Stricter (was 35.0)
    const double FILTER_RSI_HIGH = 70.0; // Stricter (was 65.0)

    bool low_vol_regime = vol_20_.std_dev() < vol_60_.std_dev();

    // Entry Conditions
    bool long_entry = (bb_pos < -FILTER_BB_THRESH) &&
                      (rsi_val < FILTER_RSI_LOW) && low_vol_regime;
    bool short_entry = (bb_pos > FILTER_BB_THRESH) &&
                       (rsi_val > FILTER_RSI_HIGH) && low_vol_regime;

    // Exit Conditions (Mean Reversion complete)
    // Exit near middle band (bb_pos < 0.1 approx or cross 0)
    // Python: bb_pos > take_profit_target (0.1) for Long Exit
    const double EXIT_THRESH = 0.1;
    bool exit_long = bb_pos > EXIT_THRESH;
    bool exit_short = bb_pos < -EXIT_THRESH;

    if (long_entry) {
      current_signal_ = 1;
    } else if (short_entry) {
      current_signal_ = -1;
    } else {
      // Evaluate Exits
      if (current_signal_ == 1 && exit_long) {
        current_signal_ = 0;
      } else if (current_signal_ == -1 && exit_short) {
        current_signal_ = 0;
      }
      // Else hold (signal remains 1 or -1)
    }
  }

  int signal() const override { return current_signal_; }
  std::string name() const override { return "MeanReversionEnhanced"; }

private:
  BollingerBands bb_;
  RSI rsi_;

  // Enhanced Volatility Filters
  RollingStats vol_20_;
  RollingStats vol_60_;
  double last_close_ = 0.0;

  int current_signal_;
};

} // namespace quant
