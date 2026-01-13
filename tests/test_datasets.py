import unittest
import pandas as pd
from datetime import datetime, timezone
from src.datasets.total_load import TotalLoadDataset
from src.datasets.actual_generation import ActualGenerationDataset
from src.datasets.generation_forecast_wind_solar import GenerationForecastWindSolarDataset

class TestTotalLoadDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = TotalLoadDataset()

    def test_normalize_tz_naive_utc(self):
        # Create a sample DataFrame with UTC-aware index
        dr = pd.date_range(start="2024-01-01", periods=3, freq="H", tz="UTC")
        df = pd.DataFrame({"actual_load": [100, 110, 120], "forecast_load": [105, 115, 125]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        # Verify index is UTC-naive
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index.name, "timestamp_utc")
        
        # Verify values are preserved
        self.assertEqual(normalized_df["actual_load"].tolist(), [100, 110, 120])
        
        # Check if it was originally UTC
        self.assertEqual(dr[0].hour, normalized_df.index[0].hour)

    def test_normalize_from_local_tz(self):
        # Create a sample DataFrame with non-UTC aware index (e.g. Europe/Warsaw)
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="H", tz="Europe/Warsaw")
        # 2024-01-01 01:00:00+01:00 is 2024-01-01 00:00:00 UTC
        df = pd.DataFrame({"actual_load": [100]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))

class TestActualGenerationDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = ActualGenerationDataset()

    def test_normalize_multiindex_columns(self):
        # Create MultiIndex columns
        columns = pd.MultiIndex.from_tuples([
            ('Biomass', 'Actual Aggregated'),
            ('Solar', 'Actual Aggregated'),
            ('Wind Onshore', 'Actual Aggregated')
        ])
        dr = pd.date_range(start="2024-01-01", periods=1, freq="H", tz="UTC")
        df = pd.DataFrame([[10, 20, 30]], index=dr, columns=columns)
        
        normalized_df = self.dataset.normalize(df)
        
        # Verify flattened columns
        expected_cols = ['biomass_actual_aggregated', 'solar_actual_aggregated', 'wind_onshore_actual_aggregated']
        self.assertEqual(list(normalized_df.columns), expected_cols)
        
        # Verify index
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index.name, "timestamp_utc")

class TestGenerationForecastWindSolarDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = GenerationForecastWindSolarDataset()

    def test_normalize_timezone_handling(self):
        # Input: DataFrame with a UTC-aware DatetimeIndex
        dr = pd.date_range(start="2024-01-01", periods=3, freq="H", tz="UTC")
        df = pd.DataFrame({"solar": [10.0, 20.0, 30.0], "wind": [100.0, 200.0, 300.0]}, index=dr)
        
        normalized_df = self.dataset.normalize(df.copy())
        
        # Assert output index is timezone-naive
        self.assertIsNone(normalized_df.index.tz)
        # Assert index name is exactly timestamp_utc
        self.assertEqual(normalized_df.index.name, "timestamp_utc")
        # Assert timestamps are preserved in UTC
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))

    def test_normalize_multiindex_columns(self):
        # Input: DataFrame with MultiIndex columns as returned by entsoe-py
        columns = pd.MultiIndex.from_tuples([
            ('Solar', 'Generation Forecast'),
            ('Wind Onshore', 'Generation Forecast')
        ])
        dr = pd.date_range(start="2024-01-01", periods=1, freq="H", tz="UTC")
        df = pd.DataFrame([[50.0, 150.0]], index=dr, columns=columns)
        
        normalized_df = self.dataset.normalize(df.copy())
        
        # Assert columns are flattened correctly and in snake_case
        expected_cols = ['solar_generation_forecast', 'wind_onshore_generation_forecast']
        self.assertEqual(list(normalized_df.columns), expected_cols)
        # Assert wind and solar forecasts remain separate columns
        self.assertEqual(len(normalized_df.columns), 2)

    def test_normalize_deterministic(self):
        # Calling normalize() multiple times on the same input produces identical output
        dr = pd.date_range(start="2024-01-01", periods=3, freq="H", tz="UTC")
        df = pd.DataFrame({"Solar": [10.0, 20.0, 30.0], "Wind": [100.0, 200.0, 300.0]}, index=dr)
        
        df_input1 = df.copy()
        df_input2 = df.copy()
        
        normalized1 = self.dataset.normalize(df_input1)
        normalized2 = self.dataset.normalize(df_input2)
        
        pd.testing.assert_frame_equal(normalized1, normalized2)

if __name__ == "__main__":
    unittest.main()
