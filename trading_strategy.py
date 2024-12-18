import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class TradingStrategy:
    def __init__(self):
        self.stop_loss_pct = 0.01
        self.breakeven_activation = 0.006  # 0.6%
        self.trailing_activation = 0.01    # 1.0%
        self.trailing_offset_high_vol = 0.005
        self.trailing_offset_low_vol = 0.003
        self.leverage = 10
        self.initial_capital = 1000
        self.structure_points = []

    def calculate_initial_stop(self, entry_price, direction):
        if direction == 'LONG':
            return entry_price * (1 - self.stop_loss_pct)
        return entry_price * (1 + self.stop_loss_pct)

    def calculate_volatility(self, df, current_index):
        if current_index < 2:
            return False
        last_3_candles = df.iloc[current_index-2:current_index+1]
        ranges = (last_3_candles['high'] - last_3_candles['low']) / last_3_candles['low'] * 100
        return ranges.mean() > 0.2

    def validate_structure(self, structure, current_price):
        print(f"\nValidando estructura:")
        print(f"Tipo: {structure['type']}")
        print(f"Nivel: {structure['price_start']}")
        print(f"Precio actual: {current_price}")
        print(f"Dirección: {structure['direction']}")
        return True

    def execute_backtest(self, df, structures):
        df = df.sort_values('timestamp')
        structures = structures.sort_values('time_start')
        
        trades = []
        active_trades = []
        print("\n=== Starting Forward Time Backtest ===\n")
        
        for _, structure in structures.iterrows():
            self.structure_points.append({
                'time_start': structure['time_start'],
                'time_end': structure['time_end'],
                'price_start': structure['price_start'],
                'price_end': structure['price_end'],
                'type': structure['type'],
                'direction': structure['direction']
            })
        
        for i in range(len(df)-1):
            current_candle = df.iloc[i]
            next_candle = df.iloc[i+1]
            
            print(f"\nProcessing candle: {current_candle['timestamp']}")
            
            for _, structure in structures.iterrows():
                if structure['time_start'] == current_candle['timestamp']:
                    if self.validate_structure(structure, next_candle['open']):
                        entry_price = next_candle['open']
                        
                        new_trade = {
                            'entry_time': next_candle['timestamp'],
                            'entry_price': entry_price,
                            'direction': structure['direction'],
                            'stop_loss': self.calculate_initial_stop(entry_price, structure['direction']),
                            'highest_price': entry_price,
                            'lowest_price': entry_price,
                            'breakeven_active': False,
                            'trailing_active': False,
                            'structure_type': structure['type'],
                            'structure_start_price': structure['price_start'],
                            'structure_end_price': structure['price_end']
                        }
                        
                        print(f"\n🔄 New {structure['direction']} trade:")
                        print(f"Structure type: {structure['type']}")
                        print(f"Entry price: {entry_price}")
                        active_trades.append(new_trade)
            
            trades_to_close = []
            for trade_idx, trade in enumerate(active_trades):
                current_high = next_candle['high']
                current_low = next_candle['low']
                
                if trade['direction'] == 'LONG':
                    trade['highest_price'] = max(trade['highest_price'], current_high)
                    profit_pct = (current_high - trade['entry_price']) / trade['entry_price']
                    
                    if current_low <= trade['stop_loss']:
                        trades_to_close.append((trade_idx, trade['stop_loss'], 'Stop Loss'))
                        continue
                    
                    if profit_pct >= self.breakeven_activation and not trade['breakeven_active']:
                        trade['stop_loss'] = trade['entry_price']
                        trade['breakeven_active'] = True
                        print(f"Breakeven activated at {profit_pct:.2%}")
                    
                    if profit_pct >= self.trailing_activation:
                        offset = self.trailing_offset_low_vol if not self.calculate_volatility(df, i) else self.trailing_offset_high_vol
                        new_stop = current_high * (1 - offset)
                        if new_stop > trade['stop_loss']:
                            trade['stop_loss'] = new_stop
                            if current_low <= new_stop:
                                trades_to_close.append((trade_idx, new_stop, 'Trailing Stop'))
                
                else:  # SHORT
                    trade['lowest_price'] = min(trade['lowest_price'], current_low)
                    profit_pct = (trade['entry_price'] - current_low) / trade['entry_price']
                    
                    if current_high >= trade['stop_loss']:
                        trades_to_close.append((trade_idx, trade['stop_loss'], 'Stop Loss'))
                        continue
                    
                    if profit_pct >= self.breakeven_activation and not trade['breakeven_active']:
                        trade['stop_loss'] = trade['entry_price']
                        trade['breakeven_active'] = True
                        print(f"Breakeven activated at {profit_pct:.2%}")
                    
                    if profit_pct >= self.trailing_activation:
                        offset = self.trailing_offset_low_vol if not self.calculate_volatility(df, i) else self.trailing_offset_high_vol
                        new_stop = trade['lowest_price'] * (1 + offset)
                        if new_stop < trade['stop_loss']:
                            trade['stop_loss'] = new_stop
                            if current_high >= new_stop:
                                trades_to_close.append((trade_idx, new_stop, 'Trailing Stop'))
            
            for idx, exit_price, exit_reason in sorted(trades_to_close, reverse=True):
                trade = active_trades[idx]
                
                price_diff = abs(exit_price - trade['entry_price'])
                base_pct = (price_diff / trade['entry_price']) * 100
                
                if trade['direction'] == 'LONG':
                    pnl = self.initial_capital * (base_pct/100) * self.leverage * (-1 if exit_price < trade['entry_price'] else 1)
                else:
                    pnl = self.initial_capital * (base_pct/100) * self.leverage * (-1 if exit_price > trade['entry_price'] else 1)
                
                trades.append({
                    'entry_time': trade['entry_time'],
                    'exit_time': next_candle['timestamp'],
                    'direction': trade['direction'],
                    'entry_price': trade['entry_price'],
                    'exit_price': exit_price,
                    'pnl_usd': pnl,
                    'exit_reason': exit_reason,
                    'structure_type': trade['structure_type']
                })
                
                active_trades.pop(idx)
        
        return pd.DataFrame(trades)

    def plot_results(self, df, trades_df):
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        
        # Plot candlesticks
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price Action'
        ))
        
        # Plot structures with horizontal lines
        for structure in self.structure_points:
            # Horizontal line for structure level
            fig.add_trace(go.Scatter(
                x=[structure['time_start'], structure['time_end']],
                y=[structure['price_start'], structure['price_start']],
                mode='lines',
                name=f"{structure['type']} {structure['direction']}",
                line=dict(
                    color='blue' if structure['direction'] == 'LONG' else 'red',
                    dash='dash'
                )
            ))
            
            # Add markers at start and end points
            fig.add_trace(go.Scatter(
                x=[structure['time_start'], structure['time_end']],
                y=[structure['price_start'], structure['price_end']],
                mode='markers',
                marker=dict(
                    color='blue' if structure['direction'] == 'LONG' else 'red',
                    size=8
                ),
                name=f"{structure['type']} points"
            ))
        
        # Plot trades
        for _, trade in trades_df.iterrows():
            color = 'green' if trade['pnl_usd'] > 0 else 'red'
            fig.add_trace(go.Scatter(
                x=[trade['entry_time'], trade['exit_time']],
                y=[trade['entry_price'], trade['exit_price']],
                mode='markers+lines',
                marker=dict(color=color, size=10),
                name=f"{trade['direction']} {trade['exit_reason']}"
            ))
        
        # Update layout
        fig.update_layout(
            title='Trading Strategy Results with Structure Levels',
            yaxis_title='Price',
            xaxis_title='Time',
            height=800
        )
        
        fig.show()








