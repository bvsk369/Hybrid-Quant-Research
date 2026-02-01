#pragma once

#include "Bar.hpp"
#include <map>
#include <string>
#include <vector>


namespace quant {

/**
 * @brief Manages market data (loading, storage, and access).
 * Optimized for sequential access during backtesting.
 */
class MarketDataManager {
public:
  MarketDataManager();
  ~MarketDataManager();

  /**
   * @brief Load CSV data for a specific symbol.
   * Expected format: timestamp(or datetime),open,high,low,close,volume
   *
   * @param symbol The ticker symbol (e.g., "ICICIBANK")
   * @param filepath Absolute path to the CSV file
   * @return true if loaded successfully, false otherwise
   */
  bool load_csv(const std::string &symbol, const std::string &filepath);

  /**
   * @brief Get all loaded bars for a symbol.
   */
  const std::vector<Bar> &get_bars(const std::string &symbol) const;

private:
  std::map<std::string, std::vector<Bar>> data_store_;
};

} // namespace quant
