import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
from entsoe.exceptions import NoMatchingDataError
from src.datasets.total_load import TotalLoadDataset
from src.datasets.actual_generation import ActualGenerationDataset
from src.datasets.generation_forecast_wind_solar import GenerationForecastWindSolarDataset
from src.datasets.generation_forecast_day_ahead import GenerationForecastDayAheadDataset
from src.datasets.actual_generation_per_unit import ActualGenerationPerUnitDataset
from src.datasets.scheduled_commercial_exchanges_intraday import ScheduledCommercialExchangesIntradayDataset
from src.datasets.scheduled_commercial_exchanges_day_ahead import ScheduledCommercialExchangesDayAheadDataset
from src.datasets.crossborder_physical_flows import CrossborderPhysicalFlowsDataset

class TestTotalLoadDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = TotalLoadDataset()

    def test_normalize_tz_naive_utc(self):
        # Create a sample DataFrame with UTC-aware index
        dr = pd.date_range(start="2024-01-01", periods=3, freq="h", tz="UTC")
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
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="h", tz="Europe/Warsaw")
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
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
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
        dr = pd.date_range(start="2024-01-01", periods=3, freq="h", tz="UTC")
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
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
        df = pd.DataFrame([[50.0, 150.0]], index=dr, columns=columns)
        
        normalized_df = self.dataset.normalize(df.copy())
        
        # Assert columns are flattened correctly and in snake_case
        expected_cols = ['solar_generation_forecast', 'wind_onshore_generation_forecast']
        self.assertEqual(list(normalized_df.columns), expected_cols)
        # Assert wind and solar forecasts remain separate columns
        self.assertEqual(len(normalized_df.columns), 2)

    def test_normalize_deterministic(self):
        # Calling normalize() multiple times on the same input produces identical output
        dr = pd.date_range(start="2024-01-01", periods=3, freq="h", tz="UTC")
        df = pd.DataFrame({"Solar": [10.0, 20.0, 30.0], "Wind": [100.0, 200.0, 300.0]}, index=dr)
        
        df_input1 = df.copy()
        df_input2 = df.copy()
        
        normalized1 = self.dataset.normalize(df_input1)
        normalized2 = self.dataset.normalize(df_input2)
        
        pd.testing.assert_frame_equal(normalized1, normalized2)

class TestGenerationForecastDayAheadDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = GenerationForecastDayAheadDataset()

    def test_normalize_series_input(self):
        # Input: pd.Series with a UTC-aware DatetimeIndex
        dr = pd.date_range(start="2024-01-01", periods=3, freq="h", tz="UTC")
        series = pd.Series([100.0, 200.0, 300.0], index=dr, name="some_name")
        
        normalized_df = self.dataset.normalize(series)
        
        # Assert result is a pd.DataFrame
        self.assertIsInstance(normalized_df, pd.DataFrame)
        # Assert exactly one column named generation_forecast
        self.assertEqual(list(normalized_df.columns), ["generation_forecast"])
        # Assert index is UTC-naive
        self.assertIsNone(normalized_df.index.tz)
        # Assert index name is exactly timestamp_utc
        self.assertEqual(normalized_df.index.name, "timestamp_utc")
        # Assert values are preserved
        self.assertEqual(normalized_df["generation_forecast"].tolist(), [100.0, 200.0, 300.0])

    def test_normalize_multiindex_columns(self):
        # Input: DataFrame with pd.MultiIndex columns similar to ENTSO-E output
        columns = pd.MultiIndex.from_tuples([
            ('Actual', 'Generation'),
            ('Actual', 'Consumption')
        ])
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
        df = pd.DataFrame([[500.0, 450.0]], index=dr, columns=columns)
        
        normalized_df = self.dataset.normalize(df)
        
        # Assert columns are flattened to snake_case
        expected_cols = ["actual_generation", "actual_consumption"]
        self.assertEqual(list(normalized_df.columns), expected_cols)

    def test_normalize_timezone_conversion(self):
        # Input: index in a non-UTC timezone (Europe/Warsaw)
        # 2024-01-01 01:00:00+01:00 is 2024-01-01 00:00:00 UTC
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"forecast": [1000.0]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        # Assert index converted correctly to UTC
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        # Assert index is timezone-naive
        self.assertIsNone(normalized_df.index.tz)

    def test_normalize_deterministic(self):
        # Calling normalize() on identical inputs produces identical outputs
        dr = pd.date_range(start="2024-01-01", periods=3, freq="h", tz="UTC")
        df = pd.DataFrame({"Forecast": [10.0, 20.0, 30.0]}, index=dr)
        
        df_input1 = df.copy()
        df_input2 = df.copy()
        
        normalized1 = self.dataset.normalize(df_input1)
        normalized2 = self.dataset.normalize(df_input2)
        
        pd.testing.assert_frame_equal(normalized1, normalized2)

class TestActualGenerationPerUnitDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = ActualGenerationPerUnitDataset()

    def test_normalize_multiindex_columns(self):
        # Input: DataFrame with pd.MultiIndex columns similar to ENTSO-E per-unit output
        # (Plant Name, Unit Name, Some Value)
        columns = pd.MultiIndex.from_tuples([
            ('Bełchatów', 'Unit 1', 'Actual Generation'),
            ('Kozienice', 'Unit 1', 'Actual Generation')
        ])
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
        df = pd.DataFrame([[100.0, 200.0]], index=dr, columns=columns)
        
        normalized_df = self.dataset.normalize(df)
        
        # Assert columns are flattened to snake_case
        expected_cols = ["bełchatów_unit_1_actual_generation", "kozienice_unit_1_actual_generation"]
        self.assertEqual(list(normalized_df.columns), expected_cols)

    def test_normalize_timezone_normalization(self):
        # Input: index with a non-UTC timezone (Europe/Warsaw)
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"value": [123.4]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        # Assert timestamps are converted to UTC
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        # Assert index is timezone-naive
        self.assertIsNone(normalized_df.index.tz)
        # Assert index name is exactly timestamp_utc
        self.assertEqual(normalized_df.index.name, "timestamp_utc")

    def test_normalize_non_empty_preserved(self):
        # Input: non-empty DataFrame
        dr = pd.date_range(start="2024-01-01", periods=2, freq="h", tz="UTC")
        df = pd.DataFrame({"val": [1.0, 2.0]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        # Assert DataFrame is not empty
        self.assertFalse(normalized_df.empty)
        # Assert values are preserved (no aggregation, no row loss)
        self.assertEqual(len(normalized_df), 2)
        self.assertEqual(normalized_df["val"].tolist(), [1.0, 2.0])

    def test_normalize_deterministic(self):
        # Calling normalize() on identical inputs produces identical outputs
        dr = pd.date_range(start="2024-01-01", periods=3, freq="h", tz="UTC")
        df = pd.DataFrame({"Val": [10.0, 20.0, 30.0]}, index=dr)
        
        df_input1 = df.copy()
        df_input2 = df.copy()
        
        normalized1 = self.dataset.normalize(df_input1)
        normalized2 = self.dataset.normalize(df_input2)
        
        pd.testing.assert_frame_equal(normalized1, normalized2)

    def test_fetch_no_matching_data_error(self):
        # Mock the client
        client = MagicMock()
        # Configure client.fetch_data to raise NoMatchingDataError
        client.fetch_data.side_effect = NoMatchingDataError("No data found")
        
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)
        
        # Call fetch()
        result = self.dataset.fetch(client, start, end)
        
        # Assertions
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        # Verify fetch_data was called with correct arguments
        client.fetch_data.assert_called_once_with(
            "query_generation_per_plant",
            country_code="PL",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
            psr_type=None,
            include_eic=False
        )

class TestScheduledCommercialExchangesIntradayDataset(unittest.TestCase):
    def setUp(self):
        self.counterpart_areas = ["DE", "CZ"]
        self.dataset = ScheduledCommercialExchangesIntradayDataset(counterpart_areas=self.counterpart_areas)
        self.start = datetime(2026, 1, 1)
        self.end = datetime(2026, 1, 2)

    def test_fetch_returns_empty_df_when_no_counterpart_areas(self):
        dataset = ScheduledCommercialExchangesIntradayDataset(counterpart_areas=[])
        mock_client = MagicMock()
        
        with self.assertLogs("src.datasets.scheduled_commercial_exchanges_intraday", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        mock_client.fetch_data.assert_not_called()
        self.assertEqual(len(cm.records), 1)

    def test_fetch_calls_both_directions_for_each_counterpart(self):
        dataset = ScheduledCommercialExchangesIntradayDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        # Create dummy series
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        series_pl_de = pd.Series([100.0] * len(dr), index=dr)
        series_de_pl = pd.Series([200.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [series_pl_de, series_de_pl]
        
        result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertEqual(mock_client.fetch_data.call_count, 2)
        
        # Check calls
        calls = mock_client.fetch_data.call_args_list
        # Call 1: PL -> DE
        self.assertEqual(calls[0].kwargs["country_code_from"], "PL")
        self.assertEqual(calls[0].kwargs["country_code_to"], "DE")
        self.assertFalse(calls[0].kwargs["dayahead"])
        
        # Verify start/end are UTC-aware pd.Timestamps
        self.assertIsInstance(calls[0].kwargs["start"], pd.Timestamp)
        self.assertIsInstance(calls[0].kwargs["end"], pd.Timestamp)
        self.assertEqual(str(calls[0].kwargs["start"].tz), "UTC")
        self.assertEqual(str(calls[0].kwargs["end"].tz), "UTC")
        
        # Call 2: DE -> PL
        self.assertEqual(calls[1].kwargs["country_code_from"], "DE")
        self.assertEqual(calls[1].kwargs["country_code_to"], "PL")
        self.assertFalse(calls[1].kwargs["dayahead"])

        self.assertIsInstance(calls[1].kwargs["start"], pd.Timestamp)
        self.assertIsInstance(calls[1].kwargs["end"], pd.Timestamp)
        self.assertEqual(str(calls[1].kwargs["start"].tz), "UTC")
        self.assertEqual(str(calls[1].kwargs["end"].tz), "UTC")
        
        self.assertIn("scheduled_exchange_pl_to_de", result.columns)
        self.assertIn("scheduled_exchange_de_to_pl", result.columns)
        self.assertEqual(len(result.columns), 2)

    def test_fetch_handles_NoMatchingDataError_per_direction(self):
        dataset = ScheduledCommercialExchangesIntradayDataset(counterpart_areas=["DE", "CZ"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        valid_series = pd.Series([100.0] * len(dr), index=dr)
        
        # PL -> DE: OK
        # DE -> PL: Error
        # PL -> CZ: Error
        # CZ -> PL: OK
        mock_client.fetch_data.side_effect = [
            valid_series, 
            NoMatchingDataError("No data"),
            NoMatchingDataError("No data"),
            valid_series
        ]
        
        with self.assertLogs("src.datasets.scheduled_commercial_exchanges_intraday", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertEqual(len(result.columns), 2)
        self.assertIn("scheduled_exchange_pl_to_de", result.columns)
        self.assertIn("scheduled_exchange_cz_to_pl", result.columns)
        
        # Check warnings: 2 for NoMatchingDataError + 0 for dataset-level warning (since we have data)
        # Wait, if we have SOME data, do we have a dataset-level warning? 
        # Looking at production code:
        # if not all_results:
        #     logger.warning(f"No data available for {self.name} on {start.date()} after checking all counterpart areas.")
        # So if all_results is not empty, no dataset-level warning.
        # Thus, we expect exactly 2 warnings for the 2 failed directions.
        self.assertEqual(len(cm.records), 2)

    def test_fetch_skips_unexpected_multicolumn_dataframe(self):
        dataset = ScheduledCommercialExchangesIntradayDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        multi_col_df = pd.DataFrame({"col1": [1.0], "col2": [2.0]}, index=dr[:1])
        valid_series = pd.Series([3.0] * len(dr), index=dr)
        
        # PL -> DE returns multi-column DF
        # DE -> PL returns valid Series
        mock_client.fetch_data.side_effect = [multi_col_df, valid_series]
        
        with self.assertLogs("src.datasets.scheduled_commercial_exchanges_intraday", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
            
        self.assertIn("scheduled_exchange_de_to_pl", result.columns)
        self.assertNotIn("scheduled_exchange_pl_to_de", result.columns)
        self.assertEqual(len(result.columns), 1)
        self.assertEqual(len(cm.records), 1)

    def test_normalize_timezone_and_index_name(self):
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"scheduled_exchange_pl_to_de": [100.0]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        self.assertEqual(normalized_df.index.name, "timestamp_utc")

    def test_normalize_deterministic_column_order(self):
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
        # Columns in non-alphabetical order
        df = pd.DataFrame(
            {"scheduled_exchange_pl_to_de": [100.0], "scheduled_exchange_de_to_pl": [200.0]}, 
            index=dr
        )
        
        # PL -> X comes before X -> PL
        normalized1 = self.dataset.normalize(df.copy())
        normalized2 = self.dataset.normalize(df.copy())
        
        self.assertEqual(list(normalized1.columns), ["scheduled_exchange_pl_to_de", "scheduled_exchange_de_to_pl"])
        pd.testing.assert_frame_equal(normalized1, normalized2)

    def test_dataset_does_not_load_config_in_fetch(self):
        mock_client = MagicMock()
        mock_client.fetch_data.return_value = pd.Series([100.0], index=pd.date_range(self.start, periods=1, tz="UTC"))
        
        with patch("src.config.load_config") as mock_load_config:
            self.dataset.fetch(mock_client, self.start, self.end)
            mock_load_config.assert_not_called()

    def test_fetch_propagates_unexpected_exception(self):
        dataset = ScheduledCommercialExchangesIntradayDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        mock_client.fetch_data.side_effect = RuntimeError("boom")
        
        with patch("src.datasets.scheduled_commercial_exchanges_intraday.logger.exception") as mock_log_exception:
            with self.assertRaises(RuntimeError):
                dataset.fetch(mock_client, self.start, self.end)
            mock_log_exception.assert_called_once()

class TestScheduledCommercialExchangesDayAheadDataset(unittest.TestCase):
    def setUp(self):
        self.counterpart_areas = ["DE", "CZ"]
        self.dataset = ScheduledCommercialExchangesDayAheadDataset(counterpart_areas=self.counterpart_areas)
        self.start = datetime(2026, 1, 1)
        self.end = datetime(2026, 1, 2)

    def test_fetch_returns_empty_df_when_no_counterpart_areas(self):
        dataset = ScheduledCommercialExchangesDayAheadDataset(counterpart_areas=[])
        mock_client = MagicMock()
        
        with self.assertLogs("src.datasets.scheduled_commercial_exchanges_day_ahead", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        mock_client.fetch_data.assert_not_called()
        self.assertEqual(len(cm.records), 1)

    def test_fetch_calls_both_directions_for_each_counterpart(self):
        dataset = ScheduledCommercialExchangesDayAheadDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        # Create dummy series
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        series_pl_de = pd.Series([100.0] * len(dr), index=dr)
        series_de_pl = pd.Series([200.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [series_pl_de, series_de_pl]
        
        result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertEqual(mock_client.fetch_data.call_count, 2)
        
        # Check calls
        calls = mock_client.fetch_data.call_args_list
        # Call 1: PL -> DE
        self.assertEqual(calls[0].kwargs["country_code_from"], "PL")
        self.assertEqual(calls[0].kwargs["country_code_to"], "DE")
        self.assertTrue(calls[0].kwargs["dayahead"])
        
        # Verify start/end are UTC-aware pd.Timestamps
        self.assertIsInstance(calls[0].kwargs["start"], pd.Timestamp)
        self.assertIsInstance(calls[0].kwargs["end"], pd.Timestamp)
        self.assertEqual(str(calls[0].kwargs["start"].tz), "UTC")
        self.assertEqual(str(calls[0].kwargs["end"].tz), "UTC")
        
        # Call 2: DE -> PL
        self.assertEqual(calls[1].kwargs["country_code_from"], "DE")
        self.assertEqual(calls[1].kwargs["country_code_to"], "PL")
        self.assertTrue(calls[1].kwargs["dayahead"])

        self.assertIsInstance(calls[1].kwargs["start"], pd.Timestamp)
        self.assertIsInstance(calls[1].kwargs["end"], pd.Timestamp)
        self.assertEqual(str(calls[1].kwargs["start"].tz), "UTC")
        self.assertEqual(str(calls[1].kwargs["end"].tz), "UTC")
        
        self.assertIn("scheduled_exchange_pl_to_de", result.columns)
        self.assertIn("scheduled_exchange_de_to_pl", result.columns)
        self.assertEqual(len(result.columns), 2)

    def test_fetch_handles_NoMatchingDataError_per_direction(self):
        dataset = ScheduledCommercialExchangesDayAheadDataset(counterpart_areas=["DE", "CZ"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        valid_series = pd.Series([100.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [
            valid_series, 
            NoMatchingDataError("No data"),
            NoMatchingDataError("No data"),
            valid_series
        ]
        
        with self.assertLogs("src.datasets.scheduled_commercial_exchanges_day_ahead", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertEqual(len(result.columns), 2)
        self.assertIn("scheduled_exchange_pl_to_de", result.columns)
        self.assertIn("scheduled_exchange_cz_to_pl", result.columns)
        self.assertEqual(len(cm.records), 2)

    def test_fetch_skips_unexpected_multicolumn_dataframe(self):
        dataset = ScheduledCommercialExchangesDayAheadDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        multi_col_df = pd.DataFrame({"col1": [1.0], "col2": [2.0]}, index=dr[:1])
        valid_series = pd.Series([3.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [multi_col_df, valid_series]
        
        with self.assertLogs("src.datasets.scheduled_commercial_exchanges_day_ahead", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
            
        self.assertIn("scheduled_exchange_de_to_pl", result.columns)
        self.assertNotIn("scheduled_exchange_pl_to_de", result.columns)
        self.assertEqual(len(result.columns), 1)
        self.assertEqual(len(cm.records), 1)

    def test_normalize_timezone_and_index_name(self):
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"scheduled_exchange_pl_to_de": [100.0]}, index=dr)
        
        normalized_df = self.dataset.normalize(df)
        
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        self.assertEqual(normalized_df.index.name, "timestamp_utc")

    def test_normalize_deterministic_column_order(self):
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
        df = pd.DataFrame(
            {"scheduled_exchange_pl_to_de": [100.0], "scheduled_exchange_de_to_pl": [200.0]}, 
            index=dr
        )
        
        normalized1 = self.dataset.normalize(df.copy())
        normalized2 = self.dataset.normalize(df.copy())
        
        self.assertEqual(list(normalized1.columns), ["scheduled_exchange_pl_to_de", "scheduled_exchange_de_to_pl"])
        pd.testing.assert_frame_equal(normalized1, normalized2)

    def test_dataset_does_not_load_config_in_fetch(self):
        mock_client = MagicMock()
        mock_client.fetch_data.return_value = pd.Series([100.0], index=pd.date_range(self.start, periods=1, tz="UTC"))
        
        with patch("src.config.load_config") as mock_load_config:
            self.dataset.fetch(mock_client, self.start, self.end)
            mock_load_config.assert_not_called()

    def test_fetch_propagates_unexpected_exception(self):
        dataset = ScheduledCommercialExchangesDayAheadDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        mock_client.fetch_data.side_effect = RuntimeError("boom")
        
        with patch("src.datasets.scheduled_commercial_exchanges_day_ahead.logger.exception") as mock_log_exception:
            with self.assertRaises(RuntimeError):
                dataset.fetch(mock_client, self.start, self.end)
            mock_log_exception.assert_called_once()

class TestCrossborderPhysicalFlowsDataset(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1)
        self.end = datetime(2026, 1, 2)

    def test_fetch_returns_empty_df_when_no_counterpart_areas(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=[])
        mock_client = MagicMock()
        
        with self.assertLogs("src.datasets.crossborder_physical_flows", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        mock_client.fetch_data.assert_not_called()
        self.assertEqual(len(cm.records), 1)

    def test_fetch_calls_both_directions_for_each_counterpart(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        series_pl_de = pd.Series([100.0] * len(dr), index=dr)
        series_de_pl = pd.Series([200.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [series_pl_de, series_de_pl]
        
        result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertEqual(mock_client.fetch_data.call_count, 2)
        
        # Check calls
        calls = mock_client.fetch_data.call_args_list
        # Call 1: PL -> DE
        self.assertEqual(calls[0].kwargs["country_code_from"], "PL")
        self.assertEqual(calls[0].kwargs["country_code_to"], "DE")
        
        # Verify start/end are UTC-aware pd.Timestamps
        self.assertIsInstance(calls[0].kwargs["start"], pd.Timestamp)
        self.assertIsInstance(calls[0].kwargs["end"], pd.Timestamp)
        self.assertEqual(str(calls[0].kwargs["start"].tz), "UTC")
        self.assertEqual(str(calls[0].kwargs["end"].tz), "UTC")
        
        # Call 2: DE -> PL
        self.assertEqual(calls[1].kwargs["country_code_from"], "DE")
        self.assertEqual(calls[1].kwargs["country_code_to"], "PL")

        self.assertIsInstance(calls[1].kwargs["start"], pd.Timestamp)
        self.assertIsInstance(calls[1].kwargs["end"], pd.Timestamp)
        self.assertEqual(str(calls[1].kwargs["start"].tz), "UTC")
        self.assertEqual(str(calls[1].kwargs["end"].tz), "UTC")
        
        self.assertIn("physical_flow_pl_to_de", result.columns)
        self.assertIn("physical_flow_de_to_pl", result.columns)
        self.assertEqual(len(result.columns), 2)

    def test_fetch_handles_NoMatchingDataError_per_direction(self):
        # CZ and DE -> sorted order: CZ, DE
        # Calls: PL->CZ, CZ->PL, PL->DE, DE->PL
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE", "CZ"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        valid_series = pd.Series([100.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [
            valid_series,                    # PL -> CZ: OK
            NoMatchingDataError("No data"),  # CZ -> PL: Error
            NoMatchingDataError("No data"),  # PL -> DE: Error
            valid_series                     # DE -> PL: OK
        ]
        
        with self.assertLogs("src.datasets.crossborder_physical_flows", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertEqual(len(result.columns), 2)
        self.assertIn("physical_flow_pl_to_cz", result.columns)
        self.assertIn("physical_flow_de_to_pl", result.columns)
        self.assertEqual(len(cm.records), 2)

    def test_fetch_skips_unexpected_multicolumn_dataframe(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        multi_col_df = pd.DataFrame({"col1": [1.0], "col2": [2.0]}, index=dr[:1])
        valid_series = pd.Series([3.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [multi_col_df, valid_series]
        
        with self.assertLogs("src.datasets.crossborder_physical_flows", level="WARNING") as cm:
            result = dataset.fetch(mock_client, self.start, self.end)
            
        self.assertIn("physical_flow_de_to_pl", result.columns)
        self.assertNotIn("physical_flow_pl_to_de", result.columns)
        self.assertEqual(len(result.columns), 1)
        self.assertEqual(len(cm.records), 1)

    def test_fetch_series_and_single_column_dataframe_normalization(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        
        dr = pd.date_range(start=self.start, end=self.end, freq="h", tz="UTC", inclusive="left")
        # PL -> DE: 1-column DF
        df_pl_de = pd.DataFrame({"x": [100.0] * len(dr)}, index=dr)
        # DE -> PL: Series
        series_de_pl = pd.Series([200.0] * len(dr), index=dr)
        
        mock_client.fetch_data.side_effect = [df_pl_de, series_de_pl]
        
        result = dataset.fetch(mock_client, self.start, self.end)
        
        self.assertIn("physical_flow_pl_to_de", result.columns)
        self.assertIn("physical_flow_de_to_pl", result.columns)
        self.assertEqual(len(result.columns), 2)

    def test_fetch_propagates_unexpected_exception_and_logs_context(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        mock_client = MagicMock()
        mock_client.fetch_data.side_effect = RuntimeError("boom")
        
        with patch("src.datasets.crossborder_physical_flows.logger.exception") as mock_log:
            with self.assertRaises(RuntimeError):
                dataset.fetch(mock_client, self.start, self.end)
            
            mock_log.assert_called_once()
            log_msg = mock_log.call_args[0][0]
            self.assertIn("[crossborder_physical_flows]", log_msg)
            self.assertIn("direction PL -> DE", log_msg)
            self.assertIn("start=", log_msg)
            self.assertIn("end=", log_msg)

    def test_normalize_converts_warsaw_to_utc_naive_and_sets_index_name(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        dr = pd.date_range(start="2024-01-01 01:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"physical_flow_pl_to_de": [100.0]}, index=dr)
        
        normalized_df = dataset.normalize(df)
        
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        self.assertEqual(normalized_df.index.name, "timestamp_utc")

    def test_normalize_handles_tz_naive_index_as_utc_and_makes_naive(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        dr = pd.date_range(start="2024-01-01 00:00:00", periods=1, freq="h")
        df = pd.DataFrame({"physical_flow_pl_to_de": [100.0]}, index=dr)
        
        normalized_df = dataset.normalize(df)
        
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        self.assertEqual(normalized_df.index.name, "timestamp_utc")

    def test_normalize_handles_non_datetime_index(self):
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE"])
        idx = ["2024-01-01 00:00:00", "2024-01-01 01:00:00"]
        df = pd.DataFrame({"physical_flow_pl_to_de": [100.0, 200.0]}, index=idx)
        
        normalized_df = dataset.normalize(df)
        
        self.assertIsInstance(normalized_df.index, pd.DatetimeIndex)
        self.assertIsNone(normalized_df.index.tz)
        self.assertEqual(normalized_df.index.name, "timestamp_utc")
        self.assertEqual(normalized_df.index[0], pd.Timestamp("2024-01-01 00:00:00"))

    def test_normalize_pair_group_column_order(self):
        # areas sorted CZ, DE
        dataset = CrossborderPhysicalFlowsDataset(counterpart_areas=["DE", "CZ"])
        dr = pd.date_range(start="2024-01-01", periods=1, freq="h", tz="UTC")
        df = pd.DataFrame({
            "physical_flow_de_to_pl": [1.0],
            "physical_flow_pl_to_de": [2.0],
            "physical_flow_cz_to_pl": [3.0],
            "physical_flow_pl_to_cz": [4.0]
        }, index=dr)
        
        normalized_df = dataset.normalize(df)
        
        expected_cols = [
            "physical_flow_pl_to_cz",
            "physical_flow_cz_to_pl",
            "physical_flow_pl_to_de",
            "physical_flow_de_to_pl"
        ]
        self.assertEqual(list(normalized_df.columns), expected_cols)

if __name__ == "__main__":
    unittest.main()
