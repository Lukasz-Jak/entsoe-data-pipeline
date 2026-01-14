import argparse
import logging
import sys
from datetime import datetime, timezone
from src.config import load_config
from src.logging_config import setup_logging
from src.api_client import EntsoeClient
from src.io_handler import IOHandler
from src.pipeline import Pipeline
from src.datasets.day_ahead_prices import DayAheadPricesDataset
from src.datasets.total_load import TotalLoadDataset
from src.datasets.actual_generation import ActualGenerationDataset
from src.datasets.generation_forecast_wind_solar import GenerationForecastWindSolarDataset

def main():
    parser = argparse.ArgumentParser(description="entsoe-data-pipeline MVP")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--list-datasets", action="store_true", help="List available datasets and exit")
    args = parser.parse_args()

    # In MVP we can hardcode the datasets or load them from config
    datasets = [
        DayAheadPricesDataset(),
        TotalLoadDataset(),
        ActualGenerationDataset(),
        GenerationForecastWindSolarDataset()
    ]

    if args.list_datasets:
        for dataset in datasets:
            print(dataset.__class__.__name__)
        sys.exit(0)

    if not args.start or not args.end:
        parser.error("the following arguments are required: --start, --end (unless --list-datasets is used)")

    config = load_config()
    setup_logging(config.get("logging", {}).get("level", "INFO"))
    
    logger = logging.getLogger(__name__)
    logger.info("Starting entsoe-data-pipeline")

    try:
        try:
            start_dt = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error("Invalid date format. Please use YYYY-MM-DD.")
            sys.exit(1)

        now_utc = datetime.now(timezone.utc)
        if start_dt > now_utc or end_dt > now_utc:
            logger.error("Start and end dates must not be in the future (UTC).")
            sys.exit(1)

        if end_dt <= start_dt:
            logger.error("Invalid date range: end date must be later than start date (half-open range [start, end)).")
            sys.exit(1)

        client = EntsoeClient(
            api_key=config["api"]["key"],
            retry_count=config["api"].get("retry_count", 5),
            backoff_factor=config["api"].get("backoff_factor", 1.0)
        )
        
        io_handler = IOHandler(
            base_path=config["storage"].get("base_path", "outputs"),
            formats=config["storage"].get("formats", ["csv"])
        )

        pipeline = Pipeline(client, io_handler, force=args.force)
        
        pipeline.run(datasets, start_dt, end_dt)
        
        logger.info("Download completed successfully")

    except Exception:
        logger.exception("Application failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
