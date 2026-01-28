#pragma once

#include <vector>
#include <cmath>

namespace quant {

/**
 * Calculate Simple Moving Average
 */
std::vector<double> sma(const std::vector<double>& prices, int period);

/**
 * Calculate Exponential Moving Average
 */
std::vector<double> ema(const std::vector<double>& prices, int period);

/**
 * Calculate RSI (Relative Strength Index)
 */
std::vector<double> rsi(const std::vector<double>& prices, int period = 14);

/**
 * Calculate ATR (Average True Range)
 */
std::vector<double> atr(
    const std::vector<double>& high,
    const std::vector<double>& low,
    const std::vector<double>& close,
    int period = 14
);

/**
 * Calculate momentum (rate of change)
 */
std::vector<double> momentum(const std::vector<double>& prices, int period);

/**
 * Calculate rolling standard deviation
 */
std::vector<double> rolling_std(const std::vector<double>& values, int period);

/**
 * Calculate z-score
 */
std::vector<double> zscore(
    const std::vector<double>& values,
    int period
);

} // namespace quant
