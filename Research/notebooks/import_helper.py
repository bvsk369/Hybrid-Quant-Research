"""
Helper script to set up imports for notebooks.

Add this at the top of your notebook:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(os.getcwd()), 'src'))
    
Or simply run:
    exec(open('import_helper.py').read())
"""

import sys
import os

# Get the Research directory (parent of notebooks)
research_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(research_dir, 'src')

# Add src to path if not already there
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

print(f"✓ Added {src_dir} to Python path")
print(f"✓ You can now import:")
print(f"  from strategies.momentum_robust import backtest_momentum_robust, analyze_momentum_robust")
print(f"  from features_2 import add_all_features")
print(f"  from feature import add_log_returns, add_rolling_volatility")
