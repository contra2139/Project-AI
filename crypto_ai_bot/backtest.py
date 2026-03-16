import asyncio
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.data_ingestion import fetch_klines
from core.ta_calculator import calculate_ta
from core.msl_analyzer import detect_msl
from core.binance_client import BinanceClientManager
import json

async def run_backtest(symbol: str, timeframe: str = "1h", limit: int = 500):
    print(f"📥 Loading {limit} candles for {symbol} ({timeframe})...")
    df = await fetch_klines(symbol, timeframe, limit=limit)
    
    if df.empty:
        print(f"❌ Error: Could not fetch data for {symbol}")
        return None

    print(f"⚙️ Calculating TA and MSL...")
    df = calculate_ta(df)
    
    # Simple Strategy Simulation:
    # BUY: Price > EMA34 and EMA34 > EMA89 and RSI < 70 (Trend following)
    # SELL/CLOSE: Price < EMA34 or RSI > 80
    
    balance = 1000.0  # Starting balance (USDT)
    position = 0      # 0: None, 1: Long, -1: Short
    entry_price = 0
    trades = []
    
    for i in range(1, len(df)):
        current_row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # Signals (Simplified proxy for AI logic)
        ema_bullish = current_row['EMA_34'] > current_row['EMA_89']
        price_above_ema = current_row['close'] > current_row['EMA_34']
        rsi_not_overbought = current_row['RSI_14'] < 70
        
        # ENTRY LONG
        if position == 0 and ema_bullish and price_above_ema and rsi_not_overbought:
            position = 1
            entry_price = current_row['close']
            trades.append({
                'type': 'LONG',
                'entry_time': df.index[i],
                'entry_price': entry_price,
            })
            
        # EXIT LONG
        elif position == 1:
            # Simple Exit: Price closes below EMA34 or hitting a 2% TP / 1% SL
            if current_row['close'] < current_row['EMA_34'] or current_row['RSI_14'] > 80 or (current_row['close'] / entry_price > 1.02) or (current_row['close'] / entry_price < 0.99):
                exit_price = current_row['close']
                profit_pct = (exit_price / entry_price - 1)
                pnl = balance * 0.1 * profit_pct * 10  # Simulation: 10% margin, 10x leverage
                balance += pnl
                
                trades[-1].update({
                    'exit_time': df.index[i],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'profit_pct': profit_pct * 100
                })
                position = 0

    return {
        'symbol': symbol,
        'initial_balance': 1000.0,
        'final_balance': balance,
        'total_trades': len(trades),
        'profitable_trades': len([t for t in trades if t.get('pnl', 0) > 0]),
        'trades': trades
    }

async def main():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    reports = []
    
    try:
        for sym in symbols:
            result = await run_backtest(sym)
            if result:
                reports.append(result)
    finally:
        await BinanceClientManager.close()
            
    # Save to file for reliable reading
    os.makedirs("logs", exist_ok=True)
    with open("logs/backtest_results.json", "w") as f:
        json.dump(reports, f, indent=2, default=str)

    print("\n" + "="*40)
    print("📋 BACKTEST SUMMARY REPORT (v0.1.6)")
    print("="*40)
    
    total_net_pnl = 0
    
    for r in reports:
        win_rate = (r['profitable_trades'] / r['total_trades'] * 100) if r['total_trades'] > 0 else 0
        roi = (r['final_balance'] / r['initial_balance'] - 1) * 100
        total_net_pnl += (r['final_balance'] - r['initial_balance'])
        
        print(f"\n🪙 SYMBOL: {r['symbol']}")
        print(f"   Win Rate: {win_rate:.2f}% ({r['profitable_trades']}/{r['total_trades']})")
        print(f"   ROI: {roi:.2f}%")
        print(f"   Net Profit: {r['final_balance'] - r['initial_balance']:.2f} USDT")

    print("\n" + "="*40)
    print(f"💰 OVERALL NET PROFIT: {total_net_pnl:.2f} USDT")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
