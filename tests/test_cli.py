import unittest
import subprocess
import sys
import os

class TestCLI(unittest.TestCase):
    def run_cli(self, args):
        cmd = [sys.executable, "main.py"] + args
        # Use env to ensure we don't fail on missing API key if it's not needed for the test
        # but here we mostly test validation which happens before API key check or after it.
        # Looking at main.py, load_config() is called before date validation.
        # load_config() raises ValueError if ENTSOE_API_KEY is missing.
        # We should probably mock the environment or provide a dummy API key if needed.
        env = os.environ.copy()
        if "ENTSOE_API_KEY" not in env:
            env["ENTSOE_API_KEY"] = "dummy_key"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env
        )
        return result

    def test_future_date_validation(self):
        result = self.run_cli(["--start", "2024-01-01", "--end", "2099-01-01"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        combined_output = result.stdout + result.stderr
        self.assertIn("must not be in the future", combined_output)

    def test_invalid_date_range(self):
        result = self.run_cli(["--start", "2024-01-02", "--end", "2024-01-01"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        combined_output = result.stdout + result.stderr
        self.assertIn("Invalid date range", combined_output)

    def test_invalid_date_format(self):
        result = self.run_cli(["--start", "invalid", "--end", "2024-01-02"])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        combined_output = result.stdout + result.stderr
        self.assertIn("Invalid date format", combined_output)

    def test_list_datasets(self):
        result = self.run_cli(["--list-datasets"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("DayAheadPricesDataset", result.stdout)
        self.assertIn("TotalLoadDataset", result.stdout)
        self.assertIn("ActualGenerationDataset", result.stdout)
        self.assertIn("GenerationForecastWindSolarDataset", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("Starting entsoe-data-pipeline", result.stdout)
        self.assertNotIn("Starting entsoe-data-pipeline", result.stderr)

    def test_datasets_selection(self):
        # We need a date range where files already exist to avoid actual API calls
        # 2024-01-01 was used in previous sessions and skipped
        result = self.run_cli(["--start", "2024-01-01", "--end", "2024-01-02", "--datasets", "TotalLoadDataset"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Skipped: total_load", result.stdout + result.stderr)
        self.assertNotIn("Skipped: day_ahead_prices", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_datasets_invalid_selection(self):
        result = self.run_cli(["--start", "2024-01-01", "--end", "2024-01-02", "--datasets", "InvalidDataset"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown dataset(s): InvalidDataset", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_datasets_empty_selection(self):
        result = self.run_cli(["--start", "2024-01-01", "--end", "2024-01-02", "--datasets", ""])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot be empty", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_list_datasets_ignores_datasets(self):
        # --list-datasets should ignore --datasets and just list all
        result = self.run_cli(["--list-datasets", "--datasets", "TotalLoadDataset"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("DayAheadPricesDataset", result.stdout)
        self.assertIn("TotalLoadDataset", result.stdout)
        self.assertNotIn("Starting entsoe-data-pipeline", result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
