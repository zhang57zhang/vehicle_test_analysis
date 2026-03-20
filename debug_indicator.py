import numpy as np
import pandas as pd
from src.core.indicator_engine import IndicatorEngine, IndicatorDefinition, IndicatorType

# Replicate sample_dataframe from test
sample_dataframe = pd.DataFrame({
    'time': np.linspace(0, 10, 1001),
    'VehicleSpeed': np.concatenate([
        np.linspace(0, 100, 500),
        np.linspace(100, 50, 501)
    ]),
})

print(f'VehicleSpeed max: {sample_dataframe["VehicleSpeed"].max()}')
print(f'VehicleSpeed min: {sample_dataframe["VehicleSpeed"].min()}')

engine = IndicatorEngine()
indicator = IndicatorDefinition(
    name='MaxVehicleSpeed',
    signal_name='VehicleSpeed',
    indicator_type=IndicatorType.SINGLE_VALUE,
    formula='max',
)
result = engine.calculate(indicator, sample_dataframe)
print(f'Calculated value: {result.calculated_value}')
print(f'Error: {result.error_message}')
