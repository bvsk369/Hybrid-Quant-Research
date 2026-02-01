#include "MarketDataManager.hpp"
#include <algorithm>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>


namespace quant {

MarketDataManager::MarketDataManager() {}

MarketDataManager::~MarketDataManager() {}

// Helper to parse timestamp strings like "2024-01-01 09:15:00" or simple Unix
// ints
int64_t parse_time(const std::string &time_str) {
  // Try to parse as integer first (Unix timestamp)
  try {
    if (std::all_of(time_str.begin(), time_str.end(), ::isdigit)) {
      return std::stoll(time_str);
    }
  } catch (...) {
  }

  // Fallback: Parse "YYYY-MM-DD HH:MM:SS"
  // Note: This is a basic implementation. For high speed, use strptime or
  // custom parser.
  std::tm tm = {};
  std::istringstream ss(time_str);
  ss >> std::get_time(&tm, "%Y-%m-%d %H:%M:%S");
  if (ss.fail()) {
    // Try just date
    ss.clear();
    ss.str(time_str);
    ss >> std::get_time(&tm, "%Y-%m-%d");
  }

  // std::mktime assumes local time, strictly speaking we want UTC, but for
  // relative backtests it's fine. Ideally use _mkgmtime (Windows) or timegm
  // (Linux)
  return std::mktime(&tm);
}

const std::vector<Bar> &
MarketDataManager::get_bars(const std::string &symbol) const {
  static const std::vector<Bar> empty;
  auto it = data_store_.find(symbol);
  if (it != data_store_.end()) {
    return it->second;
  }
  return empty;
}

bool MarketDataManager::load_csv(const std::string &symbol,
                                 const std::string &filepath) {
  std::ifstream file(filepath);
  if (!file.is_open()) {
    std::cerr << "❌ Error: Could not open file " << filepath << std::endl;
    return false;
  }

  std::vector<Bar> bars;
  bars.reserve(100000); // Reserve generic size to minimize realloc

  std::string line;
  // Skip header
  if (std::getline(file, line)) {
    // Simple check if it's a header
    if (line.find("timestamp") == std::string::npos &&
        line.find("Date") == std::string::npos && !std::isalpha(line[0])) {
      // No header? Reset to beginning
      file.clear();
      file.seekg(0);
    }
  }

  while (std::getline(file, line)) {
    if (line.empty())
      continue;

    std::stringstream ss(line);
    std::string segment;
    std::vector<std::string> row;

    while (std::getline(ss, segment, ',')) {
      row.push_back(segment);
    }

    if (row.size() < 6)
      continue;

    try {
      Bar bar;
      // Assumption: Columns are Date, Open, High, Low, Close, Volume
      // Adjust based on your specific CSV format if needed
      bar.timestamp = parse_time(row[0]);
      bar.open = std::stod(row[1]);
      bar.high = std::stod(row[2]);
      bar.low = std::stod(row[3]);
      bar.close = std::stod(row[4]);
      bar.volume = std::stod(row[5]);

      bars.push_back(bar);
    } catch (const std::exception &e) {
      // std::cerr << "Data parse error: " << e.what() << " on line: " << line
      // << std::endl;
      continue;
    }
  }

  if (bars.empty()) {
    std::cerr << " Warning: No bars loaded for " << symbol << std::endl;
    return false;
  }

  data_store_[symbol] = std::move(bars);
  std::cout << " Loaded " << data_store_[symbol].size() << " bars for "
            << symbol << std::endl;
  return true;
}

} // namespace quant
