from strategies.momentum import momentum_signal, momentum_signal_enhanced
from strategies.mean_reversion import mean_reversion_signal, mean_reversion_signal_enhanced
from strategies.cash import cash_signal
import numpy as np
import pandas as pd


def allocate_signal(df, use_enhanced=False):
    """
    Allocate signals to strategies based on market regime.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with features and regime column
    use_enhanced : bool
        If True, use enhanced strategies with risk management.
        If False, use basic strategies (legacy behavior).
        
    Returns:
    --------
    pd.Series or pd.DataFrame
        If use_enhanced=False: returns signal series (backward compatible)
        If use_enhanced=True: returns DataFrame with signal, stop_loss, position_size, etc.
    """
    if not use_enhanced:
        # Legacy behavior: simple signal series
        sig = pd.Series(0, index=df.index)
        regime = df['regime']
        
        sig[regime.isin(['LV_TREND', 'HV_TREND'])] = \
            momentum_signal(df)[regime.isin(['LV_TREND', 'HV_TREND'])]
        
        sig[regime == 'LV_RANGE'] = \
            mean_reversion_signal(df)[regime == 'LV_RANGE']
        
        sig[regime == 'HV_RANGE'] = 0
        
        return sig
    
    else:
        # Enhanced behavior: full risk management
        regime = df['regime']
        
        # Initialize result DataFrame
        result = pd.DataFrame({
            'signal': 0,
            'stop_loss': np.nan,
            'take_profit': np.nan,
            'trailing_stop': np.nan,
            'position_size': 0.0,
            'entry_price': df['close']
        }, index=df.index)
        
        # TRENDING REGIMES: Use mean reversion with REDUCED position (40%)
        # Data shows momentum loses money (-130%) while mean reversion gains (+170%)
        # This is stock-specific - ICICI Bank trends don't follow momentum well
        trend_mask = regime.isin(['LV_TREND', 'HV_TREND'])
        if trend_mask.any():
            trend_mr_result = mean_reversion_signal_enhanced(df[trend_mask])
            result.loc[trend_mask, 'signal'] = trend_mr_result['signal']
            result.loc[trend_mask, 'stop_loss'] = trend_mr_result['stop_loss']
            result.loc[trend_mask, 'take_profit'] = trend_mr_result['take_profit']
            # Use 40% position in trends (more cautious since we're counter-trend)
            result.loc[trend_mask, 'position_size'] = trend_mr_result['position_size'] * 0.4
        
        # Apply mean reversion strategy to low-volatility ranging regime
        range_mask = regime == 'LV_RANGE'
        if range_mask.any():
            mr_result = mean_reversion_signal_enhanced(df[range_mask])
            result.loc[range_mask, 'signal'] = mr_result['signal']
            result.loc[range_mask, 'stop_loss'] = mr_result['stop_loss']
            result.loc[range_mask, 'take_profit'] = mr_result['take_profit']
            result.loc[range_mask, 'position_size'] = mr_result['position_size']
        
        # HV_RANGE: Use mean reversion with REDUCED position (50% of normal)
        # Instead of going fully to cash, we still participate but more cautiously
        hv_range_mask = regime == 'HV_RANGE'
        if hv_range_mask.any():
            hv_mr_result = mean_reversion_signal_enhanced(df[hv_range_mask])
            result.loc[hv_range_mask, 'signal'] = hv_mr_result['signal']
            result.loc[hv_range_mask, 'stop_loss'] = hv_mr_result['stop_loss']
            result.loc[hv_range_mask, 'take_profit'] = hv_mr_result['take_profit']
            # Reduce position size by 50% in high volatility
            result.loc[hv_range_mask, 'position_size'] = hv_mr_result['position_size'] * 0.5
        
        return result
