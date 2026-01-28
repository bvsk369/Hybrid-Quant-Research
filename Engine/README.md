# Quant Engine - C++ Implementation

High-performance C++ engine for quantitative trading strategies.

## Building

### Prerequisites
- CMake 3.15+
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- Python 3.7+ with development headers
- pybind11 (will be downloaded automatically)

### Build Steps

```bash
# Create build directory
mkdir build
cd build

# Configure
cmake ..

# Build
cmake --build .

# Install Python module
pip install .
```

### Windows (Visual Studio)

```powershell
mkdir build
cd build
cmake .. -G "Visual Studio 16 2019" -A x64
cmake --build . --config Release
```

## Usage

### Python Interface

```python
import quant_engine

# Calculate indicators
prices = [100, 101, 102, 103, 104, 105]
sma_5 = quant_engine.features.sma(prices, 5)
rsi = quant_engine.features.rsi(prices, 14)

print(f"SMA(5): {sma_5}")
print(f"RSI: {rsi}")
```

### Performance Comparison

Expected speedup vs pandas:
- SMA: 10-20x faster
- RSI: 15-30x faster
- Rolling calculations: 20-50x faster

## Project Structure

```
Engine/
├── src/              # C++ source files
├── include/          # Header files
├── python_bindings/ # Python interface
├── tests/            # Unit tests
└── CMakeLists.txt    # Build configuration
```

## Next Steps

1. Add backtesting engine
2. Add data handler
3. Add risk management module
4. Comprehensive unit tests
5. Performance benchmarks

## Notes

- This is a starting template
- Add more features as needed
- Focus on correctness before optimization
- Profile before optimizing
