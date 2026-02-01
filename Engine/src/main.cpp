#include "Engine.hpp"
#include <iostream>
#include <string>

int main(int argc, char *argv[]) {
  std::cout << "🚀 QuantEngine C++ Init..." << std::endl;

  quant::Engine engine;

  // Default Data Path (Adjust as needed)
  std::string data_path = "../../Research/Data/ICICIBANK_5minute.csv";
  if (argc > 1) {
    data_path = argv[1];
  }

  std::cout << "📂 Loading Data: " << data_path << std::endl;
  engine.load_data("ICICIBANK", data_path);

  engine.run();

  return 0;
}
