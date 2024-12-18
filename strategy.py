import pandas as pd

class TradingStrategy:
    def __init__(self):
        self.stop_loss_pct = 0.01  # 1%
        self.breakeven_pct = 0.006  # 0.6%
        self.trailing_activation_pct = 0.01  # 1%
        self.trailing_offset_pct = 0.003  # 0.3%
        self.leverage = 10
        self.initial_capital = 1000

    def execute_backtest(self, df, structures):
        trades = []
        active_trades = []
        
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            current_time = df['timestamp'].iloc[i]
            
            # Revisar señales de entrada
            for _, structure in structures.iterrows():
                if structure['time_end'] == current_time and i + 1 < len(df):
                    entry_price = df['close'].iloc[i + 1]
                    print(f"\n🎯 Nueva señal detectada - {structure['direction']}")
                    print(f"Precio de entrada: {entry_price}")
                    
                    if structure['direction'] == 'LONG':
                        stop_loss = entry_price * (1 - self.stop_loss_pct)
                        take_profit = entry_price * (1 + self.stop_loss_pct)
                        print(f"Stop Loss inicial: {stop_loss}")
                        print(f"Take Profit: {take_profit}")
                        active_trades.append({
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'direction': 'LONG',
                            'entry_time': df['timestamp'].iloc[i + 1],
                            'trailing_active': False
                        })
                    
                    elif structure['direction'] == 'SHORT':
                        stop_loss = entry_price * (1 + self.stop_loss_pct)
                        take_profit = entry_price * (1 - self.stop_loss_pct)
                        print(f"Stop Loss inicial: {stop_loss}")
                        print(f"Take Profit: {take_profit}")
                        active_trades.append({
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'direction': 'SHORT',
                            'entry_time': df['timestamp'].iloc[i + 1],
                            'trailing_active': False
                        })
            
            # Gestionar trades activos
            trades_to_remove = []
            for trade_idx, active_trade in enumerate(active_trades):
                # Calcular profit actual
                if active_trade['direction'] == 'LONG':
                    current_profit_pct = (current_price - active_trade['entry_price']) / active_trade['entry_price'] * 100
                else:
                    current_profit_pct = (active_trade['entry_price'] - current_price) / active_trade['entry_price'] * 100
                
                print(f"\n📊 Analizando trade {active_trade['direction']}:")
                print(f"Precio actual: {current_price}")
                print(f"Profit actual: {current_profit_pct:.2f}%")
                print(f"Stop loss actual: {active_trade['stop_loss']}")
                
                # Gestionar trailing stop
                if active_trade['direction'] == 'LONG':
                    # Activar breakeven
                    if current_profit_pct >= self.breakeven_pct and not active_trade['trailing_active']:
                        print(f"🎯 ¡Activando breakeven! Stop loss -> {active_trade['entry_price']}")
                        active_trade['stop_loss'] = active_trade['entry_price']
                        active_trade['trailing_active'] = True
                    
                    # Activar trailing offset
                    if current_profit_pct >= self.trailing_activation_pct:
                        new_stop = current_price * (1 - self.trailing_offset_pct)
                        if new_stop > active_trade['stop_loss']:
                            print(f"📈 ¡Actualizando trailing stop! {active_trade['stop_loss']} -> {new_stop}")
                            active_trade['stop_loss'] = new_stop
                
                else:  # SHORT
                    # Activar breakeven
                    if current_profit_pct >= self.breakeven_pct and not active_trade['trailing_active']:
                        print(f"🎯 ¡Activando breakeven! Stop loss -> {active_trade['entry_price']}")
                        active_trade['stop_loss'] = active_trade['entry_price']
                        active_trade['trailing_active'] = True
                    
                    # Activar trailing offset
                    if current_profit_pct >= self.trailing_activation_pct:
                        new_stop = current_price * (1 + self.trailing_offset_pct)
                        if new_stop < active_trade['stop_loss']:
                            print(f"📉 ¡Actualizando trailing stop! {active_trade['stop_loss']} -> {new_stop}")
                            active_trade['stop_loss'] = new_stop

                # Verificar cierre de trade
                if active_trade['direction'] == 'LONG':
                    if df['low'].iloc[i] <= active_trade['stop_loss']:
                        exit_price = max(df['low'].iloc[i], active_trade['stop_loss'])
                        print(f"❌ Stop Loss tocado en LONG: {exit_price}")
                        trades_to_remove.append(trade_idx)
                    elif df['high'].iloc[i] >= active_trade['take_profit']:
                        exit_price = active_trade['take_profit']
                        print(f"✅ Take Profit alcanzado en LONG: {exit_price}")
                        trades_to_remove.append(trade_idx)
                    else:
                        continue
                else:  # SHORT
                    if df['high'].iloc[i] >= active_trade['stop_loss']:
                        exit_price = min(df['high'].iloc[i], active_trade['stop_loss'])
                        print(f"❌ Stop Loss tocado en SHORT: {exit_price}")
                        trades_to_remove.append(trade_idx)
                    elif df['low'].iloc[i] <= active_trade['take_profit']:
                        exit_price = active_trade['take_profit']
                        print(f"✅ Take Profit alcanzado en SHORT: {exit_price}")
                        trades_to_remove.append(trade_idx)
                    else:
                        continue
                
                # Calcular PnL para trades cerrados
                price_diff = abs(exit_price - active_trade['entry_price'])
                base_pct = (price_diff / active_trade['entry_price']) * 100
                leveraged_pct = base_pct * self.leverage
                
                if active_trade['direction'] == 'LONG':
                    pnl_usd = self.initial_capital * (base_pct/100) * self.leverage if exit_price > active_trade['entry_price'] else -self.initial_capital * (base_pct/100) * self.leverage
                else:
                    pnl_usd = self.initial_capital * (base_pct/100) * self.leverage if exit_price < active_trade['entry_price'] else -self.initial_capital * (base_pct/100) * self.leverage
                
                print(f"💰 PnL del trade: ${pnl_usd:.2f}")
                
                trades.append({
                    'entry_price': active_trade['entry_price'],
                    'exit_price': exit_price,
                    'entry_time': active_trade['entry_time'],
                    'exit_time': current_time,
                    'direction': active_trade['direction'],
                    'price_diff': price_diff,
                    'base_pct': base_pct,
                    'leveraged_pct': leveraged_pct,
                    'pnl_usd': pnl_usd
                })
            
            # Remover trades cerrados
            for idx in sorted(trades_to_remove, reverse=True):
                active_trades.pop(idx)
        
        return pd.DataFrame(trades)
