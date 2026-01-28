#include "features.hpp"
#include <algorithm>
#include <numeric>
#include <cmath>

namespace quant {

std::vector<double> sma(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::nan(""));
    
    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }
    
    double sum = 0.0;
    for (int i = 0; i < period; ++i) {
        sum += prices[i];
    }
    result[period - 1] = sum / period;
    
    for (size_t i = period; i < prices.size(); ++i) {
        sum = sum - prices[i - period] + prices[i];
        result[i] = sum / period;
    }
    
    return result;
}

std::vector<double> ema(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::nan(""));
    
    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }
    
    double alpha = 2.0 / (period + 1.0);
    double ema_value = prices[0];
    
    for (size_t i = 1; i < prices.size(); ++i) {
        ema_value = alpha * prices[i] + (1 - alpha) * ema_value;
        if (i >= static_cast<size_t>(period - 1)) {
            result[i] = ema_value;
        }
    }
    
    return result;
}

std::vector<double> rsi(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::nan(""));
    
    if (prices.size() < static_cast<size_t>(period + 1)) {
        return result;
    }
    
    std::vector<double> gains, losses;
    for (size_t i = 1; i < prices.size(); ++i) {
        double change = prices[i] - prices[i - 1];
        gains.push_back(change > 0 ? change : 0.0);
        losses.push_back(change < 0 ? -change : 0.0);
    }
    
    double avg_gain = 0.0, avg_loss = 0.0;
    for (int i = 0; i < period; ++i) {
        avg_gain += gains[i];
        avg_loss += losses[i];
    }
    avg_gain /= period;
    avg_loss /= period;
    
    if (avg_loss == 0.0) {
        result[period] = 100.0;
    } else {
        double rs = avg_gain / avg_loss;
        result[period] = 100.0 - (100.0 / (1.0 + rs));
    }
    
    // Wilder's smoothing
    double alpha = 1.0 / period;
    for (size_t i = period + 1; i < prices.size(); ++i) {
        avg_gain = alpha * gains[i - 1] + (1 - alpha) * avg_gain;
        avg_loss = alpha * losses[i - 1] + (1 - alpha) * avg_loss;
        
        if (avg_loss == 0.0) {
            result[i] = 100.0;
        } else {
            double rs = avg_gain / avg_loss;
            result[i] = 100.0 - (100.0 / (1.0 + rs));
        }
    }
    
    return result;
}

std::vector<double> atr(
    const std::vector<double>& high,
    const std::vector<double>& low,
    const std::vector<double>& close,
    int period) {
    
    std::vector<double> result(close.size(), std::nan(""));
    
    if (high.size() != low.size() || high.size() != close.size() ||
        high.size() < static_cast<size_t>(period + 1)) {
        return result;
    }
    
    std::vector<double> true_ranges;
    for (size_t i = 1; i < high.size(); ++i) {
        double tr1 = high[i] - low[i];
        double tr2 = std::abs(high[i] - close[i - 1]);
        double tr3 = std::abs(low[i] - close[i - 1]);
        true_ranges.push_back(std::max({tr1, tr2, tr3}));
    }
    
    // Calculate initial ATR
    double atr_value = 0.0;
    for (int i = 0; i < period; ++i) {
        atr_value += true_ranges[i];
    }
    atr_value /= period;
    result[period] = atr_value;
    
    // Wilder's smoothing
    double alpha = 1.0 / period;
    for (size_t i = period; i < true_ranges.size(); ++i) {
        atr_value = alpha * true_ranges[i] + (1 - alpha) * atr_value;
        result[i + 1] = atr_value;
    }
    
    return result;
}

std::vector<double> momentum(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::nan(""));
    
    if (prices.size() < static_cast<size_t>(period + 1)) {
        return result;
    }
    
    for (size_t i = period; i < prices.size(); ++i) {
        if (prices[i - period] != 0.0) {
            result[i] = (prices[i] - prices[i - period]) / prices[i - period];
        }
    }
    
    return result;
}

std::vector<double> rolling_std(const std::vector<double>& values, int period) {
    std::vector<double> result(values.size(), std::nan(""));
    
    if (values.size() < static_cast<size_t>(period)) {
        return result;
    }
    
    for (size_t i = period - 1; i < values.size(); ++i) {
        double sum = 0.0;
        double sum_sq = 0.0;
        
        for (int j = 0; j < period; ++j) {
            double val = values[i - j];
            sum += val;
            sum_sq += val * val;
        }
        
        double mean = sum / period;
        double variance = (sum_sq / period) - (mean * mean);
        result[i] = std::sqrt(variance);
    }
    
    return result;
}

std::vector<double> zscore(
    const std::vector<double>& values,
    int period) {
    
    std::vector<double> result(values.size(), std::nan(""));
    
    if (values.size() < static_cast<size_t>(period)) {
        return result;
    }
    
    for (size_t i = period - 1; i < values.size(); ++i) {
        double sum = 0.0;
        double sum_sq = 0.0;
        
        for (int j = 0; j < period; ++j) {
            double val = values[i - j];
            sum += val;
            sum_sq += val * val;
        }
        
        double mean = sum / period;
        double variance = (sum_sq / period) - (mean * mean);
        double std_dev = std::sqrt(variance);
        
        if (std_dev > 0.0) {
            result[i] = (values[i] - mean) / std_dev;
        }
    }
    
    return result;
}

} // namespace quant
