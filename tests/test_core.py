import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.utils import format_date_path, ensure_utc_index
from src.io_handler import IOHandler

class TestEnsureUtcIndex(unittest.TestCase):
    def test_tz_aware_to_naive_storage(self):
        # TEST 1 — tz-aware index (Europe/Warsaw) -> UTC semantics, then storage-naive
        warsaw_idx = pd.date_range(start="2024-07-01 02:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"val": [1]}, index=warsaw_idx)
        
        expected = warsaw_idx.tz_convert("UTC").tz_localize(None)[0]
        
        out = ensure_utc_index(df)
        
        self.assertIsNone(out.index.tz)
        self.assertEqual(out.index[0], expected)
        self.assertEqual(out.index.name, "timestamp_utc")

    def test_tz_naive_to_utc_naive_storage(self):
        # TEST 2 — tz-naive DatetimeIndex treated as UTC and made storage-naive
        naive_idx = pd.date_range(start="2024-01-01 00:00:00", periods=2, freq="h")
        df = pd.DataFrame({"val": [1, 2]}, index=naive_idx)
        
        out = ensure_utc_index(df)
        
        self.assertIsNone(out.index.tz)
        self.assertEqual(out.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        self.assertEqual(out.index.name, "timestamp_utc")
        self.assertEqual(list(out["val"]), [1, 2])

    def test_string_index_to_utc_naive_storage(self):
        # TEST 3 — non-datetime index (strings) converted to DatetimeIndex with UTC semantics and storage-naive
        idx = ["2024-01-01 00:00:00", "2024-01-01 01:00:00"]
        df = pd.DataFrame({"val": [1, 2]}, index=idx)
        
        out = ensure_utc_index(df)
        
        self.assertIsInstance(out.index, pd.DatetimeIndex)
        self.assertIsNone(out.index.tz)
        self.assertEqual(out.index[0], pd.Timestamp("2024-01-01 00:00:00"))
        self.assertEqual(out.index.name, "timestamp_utc")

    def test_keep_tz_aware_utc(self):
        # TEST 4 — make_naive_for_storage=False keeps tz-aware UTC index
        warsaw_idx = pd.date_range(start="2024-07-01 02:00:00", periods=1, freq="h", tz="Europe/Warsaw")
        df = pd.DataFrame({"val": [1]}, index=warsaw_idx)
        
        out = ensure_utc_index(df, make_naive_for_storage=False)
        
        self.assertIsNotNone(out.index.tz)
        self.assertEqual(str(out.index.tz), "UTC")
        self.assertEqual(out.index.name, "timestamp_utc")

class TestUtils(unittest.TestCase):
    def test_format_date_path(self):
        dt = datetime(2024, 1, 15)
        expected = "2024/2024-01"
        self.assertEqual(format_date_path(dt), expected)

class TestIOHandler(unittest.TestCase):
    def setUp(self):
        self.base_path = "outputs"
        self.formats = ["csv", "xlsx"]
        self.io_handler = IOHandler(self.base_path, self.formats)
        self.dataset_name = "test_dataset"
        self.date_path = "2024/2024-01"
        self.filename = "test_file"

    @patch("os.path.exists")
    def test_get_missing_formats_none_exist(self, mock_exists):
        # Setup: os.path.exists always returns False
        mock_exists.return_value = False
        
        missing = self.io_handler.get_missing_formats(
            self.dataset_name, self.date_path, self.filename
        )
        
        self.assertEqual(missing, ["csv", "xlsx"])
        self.assertEqual(mock_exists.call_count, 2)

    @patch("os.path.exists")
    def test_get_missing_formats_one_exists(self, mock_exists):
        # Setup: CSV exists, XLSX does not
        def side_effect(path):
            return path.endswith(".csv")
        
        mock_exists.side_effect = side_effect
        
        missing = self.io_handler.get_missing_formats(
            self.dataset_name, self.date_path, self.filename
        )
        
        self.assertEqual(missing, ["xlsx"])

    @patch("os.path.exists")
    def test_get_missing_formats_all_exist(self, mock_exists):
        # Setup: all formats exist
        mock_exists.return_value = True
        
        missing = self.io_handler.get_missing_formats(
            self.dataset_name, self.date_path, self.filename
        )
        
        self.assertEqual(missing, [])

if __name__ == "__main__":
    unittest.main()
