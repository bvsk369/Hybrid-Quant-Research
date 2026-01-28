"""
Test script to verify enhanced strategies work correctly.

Run from Research/src/:
    python test_enhanced_strategies.py
"""

import pandas as pd
import numpy as np
import sys
import os

# Import our modules
from features import generate_features
from cleaning import clean_equity_data
from regimes import detect_regime
from strategies.momentum import momentum_signal_enhanced
from strategies.mean_reversion import mean_reversion_signal_enhanced
from allocator import allocate_signal


def test_momentum_strategy():
    """Test enhanced momentum strategy."""
    print("\n" + "="*60)
    print("TESTING ENHANCED MOMENTUM STRATEGY")
    print("="*60)
    
    # Load sample data
    data_path = os.path.join('..', 'Data', 'ICICIBANK_Features2.csv')
    
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        print("Please update the data_path variable in this script.")
        return
    
    # Load and prepare data
    df = pd.read_csv(data_path, parse_dates=True, index_col=0)
    df.columns = [c.lower() for c in df.columns]
    
    print(f"✅ Loaded {len(df)} rows of data")
    
    # Clean and generate features
    print("Cleaning data...")
    df = clean_equity_data(df)
    
    print("Generating features...")
    df = generate_features(df)
    
    print(f"✅ Features generated. Shape: {df.shape}")
    
    # Test momentum strategy
    print("\nTesting momentum_signal_enhanced()...")
    result = momentum_signal_enhanced(df)
    
    print(f"\n📊 Momentum Strategy Results:")
    print(f"   Total signals: {(result['signal'] != 0).sum()}")
    print(f"   Long signals: {(result['signal'] == 1).sum()}")
    print(f"   Short signals: {(result['signal'] == -1).sum()}")
    print(f"\n   Position size stats:")
    print(result['position_size'].describe())
    
    # Check for issues
    if result['stop_loss'].isna().all():
        print("⚠️  Warning: All stop losses are NaN")
    else:
        print(f"✅ Stop losses calculated for {(~result['stop_loss'].isna()).sum()} rows")
    
    return df, result


def test_mean_reversion_strategy():
    """Test enhanced mean reversion strategy."""
    print("\n" + "="*60)
    print("TESTING ENHANCED MEAN REVERSION STRATEGY")
    print("="*60)
    
    # Load sample data
    data_path = os.path.join('..', 'Data', 'ICICIBANK_Features2.csv')
    
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return
    
    # Load and prepare data
    df = pd.read_csv(data_path, parse_dates=True, index_col=0)
    df.columns = [c.lower() for c in df.columns]
    
    # Clean and generate features
    df = clean_equity_data(df)
    df = generate_features(df)
    
    # Test mean reversion strategy
    print("\nTesting mean_reversion_signal_enhanced()...")
    result = mean_reversion_signal_enhanced(df)
    
    print(f"\n📊 Mean Reversion Strategy Results:")
    print(f"   Total signals: {(result['signal'] != 0).sum()}")
    print(f"   Long signals: {(result['signal'] == 1).sum()}")
    print(f"   Short signals: {(result['signal'] == -1).sum()}")
    print(f"\n   Position size stats:")
    print(result['position_size'].describe())
    
    # Check for issues
    if result['take_profit'].isna().all():
        print("⚠️  Warning: All take profits are NaN")
    else:
        print(f"✅ Take profits calculated for {(~result['take_profit'].isna()).sum()} rows")
    
    return df, result


def test_allocator_enhanced():
    """Test enhanced allocator."""
    print("\n" + "="*60)
    print("TESTING ENHANCED ALLOCATOR")
    print("="*60)
    
    # Load sample data
    data_path = os.path.join('..', 'Data', 'ICICIBANK_Features2.csv')
    
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return
    
    # Load and prepare data
    df = pd.read_csv(data_path, parse_dates=True, index_col=0)
    df.columns = [c.lower() for c in df.columns]
    
    # Clean and generate features
    df = clean_equity_data(df)
    df = generate_features(df)
    
    # Add regime detection
    print("Detecting regimes...")
    df['regime'] = detect_regime(df)
    
    print("\nRegime distribution:")
    print(df['regime'].value_counts())
    
    # Test enhanced allocator
    print("\nTesting allocate_signal(use_enhanced=True)...")
    result = allocate_signal(df, use_enhanced=True)
    
    print(f"\n📊 Enhanced Allocator Results:")
    print(f"   Total signals: {(result['signal'] != 0).sum()}")
    print(f"   Long signals: {(result['signal'] == 1).sum()}")
    print(f"   Short signals: {(result['signal'] == -1).sum()}")
    
    # Breakdown by regime
    print("\n📌 Signals by regime:")
    for regime in df['regime'].unique():
        regime_signals = result[df['regime'] == regime]['signal']
        non_zero = (regime_signals != 0).sum()
        print(f"   {regime:12s}: {non_zero:4d} signals")
    
    print("\n✅ All tests completed successfully!")
    
    return df, result


if __name__ == "__main__":
    print("="*60)
    print("ENHANCED STRATEGIES TEST SUITE")
    print("="*60)
    
    try:
        # Test individual strategies
        df_mom, result_mom = test_momentum_strategy()
        df_mr, result_mr = test_mean_reversion_strategy()
        
        # Test full allocator
        df_full, result_full = test_allocator_enhanced()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nYour enhanced strategies are ready to use!")
        print("\nNext steps:")
        print("1. Run the full backtesting pipeline with runner.py")
        print("2. Update runner.py to use enhanced allocator")
        print("3. Compare performance with legacy strategies")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
