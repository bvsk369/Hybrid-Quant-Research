# Import Instructions for Notebooks

## Problem
When importing from notebooks, Python can't find the `strategies` module because it's in a different directory.

## Solution

### Method 1: Use Import Helper (Recommended)

Add this at the top of your notebook:

```python
# Run this first
exec(open('import_helper.py').read())

# Now you can import normally
from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
from features_2 import add_all_features
from feature import add_log_returns, add_rolling_volatility
```

### Method 2: Manual Path Setup

Add this at the top of your notebook:

```python
import sys
import os

# Add src directory to path
src_path = os.path.join(os.path.dirname(os.getcwd()), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now import
from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
```

### Method 3: Direct Import with Full Path

```python
import sys
sys.path.append('../src')

from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
```

## Directory Structure

```
Research/
├── notebooks/          ← You are here
│   ├── import_helper.py
│   └── your_notebook.ipynb
└── src/                ← Code is here
    ├── strategies/
    │   └── momentum_robust.py
    ├── features_2.py
    └── feature.py
```

## Example Complete Notebook Cell

```python
# Setup imports
import sys
import os
import pandas as pd
import numpy as np

# Add src to path
src_path = os.path.join(os.path.dirname(os.getcwd()), 'src')
sys.path.insert(0, src_path)

# Import strategy functions
from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust
from features_2 import add_all_features
from feature import add_log_returns, add_rolling_volatility, add_moving_averages, add_zscore

# Load data
df = pd.read_csv('../Data/ICICIBANK_Features2.csv', parse_dates=True, index_col=0)

# Add features (if not already present)
if 'log_return' not in df.columns:
    df = add_log_returns(df)
    df = add_rolling_volatility(df)
    df = add_moving_averages(df)
    df = add_zscore(df)

if 'momentum_zscore_20' not in df.columns:
    df = add_all_features(df)

# Run strategy
df_results = backtest_momentum_robust(df)
metrics = analyze_momentum_robust(df_results)
```
