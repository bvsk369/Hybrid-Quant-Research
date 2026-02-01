# Hybrid Quantitative Trading Engine (C++ / Python)

A high-performance algorithmic trading system demonstrating a professional **Research-to-Production** pipeline.

## 🚀 Key Highlights
- **Hybrid Architecture**: Leverages **Python** for rapid hypothesis testing/data analysis and **C++** for low-latency execution simulation.
- **Performance**: C++ Engine processes **3,000,000+ bars/sec** (Benchmarks included).
- **Strategies**: Implements Regime Detection (HMM-style logic), Momentum, and Mean Reversion strategies with dynamic switching.
- **Realistic Simulation**: Uses "Next-Open" fill logic to model real-world slippage and execution delays.

## 🛠️ Technology Stack
- **Core Engine**: C++20 (STL, Circular Buffers, OOP Polymorphism)
- **Research Layer**: Python (Pandas, Numpy, Scikit-learn for Feature Engineering)
- **Build System**: CMake & MSVC
- **Data**: 1-Minute Intraday Market Data (OHLCV) with custom CSV parsing.

## 📈 Architecture

```mermaid
graph TD
    Data[Market Data (.csv)] --> Python[Python Research Layer]
    Python -->|Analysis & Params| Strategies[Strategy Definition]
    
    Data --> CPP[C++ Execution Engine]
    Strategies --> CPP
    
    subgraph "C++ Engine (Low Latency)"
        CPP -->|Updates| Indicators[Circular Buffer Indicators]
        Indicators -->|Signals| Risk[Risk Manager]
        Risk -->|Orders| Exec[Execution Simulator]
        Exec -->|Fills| PnL[Performance Report]
    end
```

## 📊 Strategy Logic
The system uses a **Regime-Based Allocator**:
1.  **Regime Detection**: Monitors Volatility (Short vs Long term) and Trend Strength (SMA deviation).
2.  **Low Volatility + Trend** -> **Momentum Strategy** (Ride the wave).
3.  **Low Volatility + Range** -> **Mean Reversion** (Bollinger Band fades).
4.  **High Volatility** -> **Cash** (Risk off).

## ⚡ Benchmarking
The C++ Engine is optimized for speed using:
- **Circular Buffers**: O(1) indicator updates (no memory realocation).
- **Template Metaprogramming**: For efficient moving averages.
- **Buffered I/O**: Custom CSV parsing to minimize disk latency.

**Current Benchmark:**
> Processed ~76,000 bars in <25ms (**~3,000,000 bars/sec**).

## 🚀 How to Build & Run
```bash
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
.\bin\Release\QuantEngineApp.exe "..\Data\market_data.csv"
```

## 📝 Future Improvements
- [ ] Implement HFT-style Limit Order Book (LOB) support.
- [ ] Add Python Bindings (pybind11) for direct shared-memory access.
- [ ] Account for transaction cost models (impact + fixed fees).
