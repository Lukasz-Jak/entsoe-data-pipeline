import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.utils import format_date_path
from src.io_handler import IOHandler

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
