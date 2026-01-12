import unittest
import pandas as pd
from datetime import datetime, timezone
from src.datasets.total_load import TotalLoadDataset
from src.datasets.actual_generation import ActualGenerationDataset

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

if __name__ == "__main__":
    unittest.main()
