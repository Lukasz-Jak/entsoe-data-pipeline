import argparse
import logging
from datetime import datetime
from src.config import load_config
from src.logging_config import setup_logging
from src.api_client import EntsoeClient
from src.io_handler import IOHandler
from src.pipeline import Pipeline
from src.datasets.day_ahead_prices import DayAheadPricesDataset
from src.datasets.total_load import TotalLoadDataset

def main():
    parser = argparse.ArgumentParser(description="entsoe-data-pipeline MVP")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.get("logging", {}).get("level", "INFO"))
    
    logger = logging.getLogger(__name__)
    logger.info("Starting entsoe-data-pipeline")

    start_dt = datetime.strptime(args.start, "%Y-%m-%d")
    end_dt = datetime.strptime(args.end, "%Y-%m-%d")

    if end_dt <= start_dt:
        msg = "Invalid date range: end date must be later than start date (half-open range [start, end))."
        logger.error(msg)
        raise ValueError(msg)

    try:
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
        
        # In MVP we can hardcode the datasets or load them from config
        datasets = [
            DayAheadPricesDataset(),
            TotalLoadDataset()
        ]
        
        pipeline.run(datasets, start_dt, end_dt)
        
        logger.info("Download completed successfully")

    except Exception:
        logger.exception("Application failed")

if __name__ == "__main__":
    main()
