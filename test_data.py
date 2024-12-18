from bybit_connection import get_historical_data
import pandas as pd

# Obtenemos datos
df = get_historical_data()

# Mostramos el rango de precios por día
print("\nRango de precios por día:")
df['date'] = pd.to_datetime(df['timestamp']).dt.date
daily_ranges = df.groupby('date').agg({
    'high': 'max',
    'low': 'min'
})
print(daily_ranges)

# Verificamos algunos datos
print("\nPrimeras 5 velas:")
print(df[['timestamp', 'open', 'high', 'low', 'close']].head())
