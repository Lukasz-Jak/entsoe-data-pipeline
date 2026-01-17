import argparse
import logging
import os
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
from src.datasets.generation_forecast_day_ahead import GenerationForecastDayAheadDataset
from src.datasets.actual_generation_per_unit import ActualGenerationPerUnitDataset

def main():
    parser = argparse.ArgumentParser(description="entsoe-data-pipeline MVP")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--list-datasets", action="store_true", help="List available datasets and exit")
    parser.add_argument("--datasets", type=str, help="Comma-separated list of dataset names to execute")
    parser.add_argument("--dry-run", action="store_true", help="Preview execution plan without making changes")
    args = parser.parse_args()

    # In MVP we can hardcode the datasets or load them from config
    datasets = [
        DayAheadPricesDataset(),
        TotalLoadDataset(),
        ActualGenerationDataset(),
        GenerationForecastWindSolarDataset(),
        GenerationForecastDayAheadDataset(),
        ActualGenerationPerUnitDataset()
    ]

    if args.list_datasets:
        for dataset in datasets:
            print(dataset.__class__.__name__)
        sys.exit(0)

    if args.datasets is not None:
        selected_names = [name.strip() for name in args.datasets.split(",") if name.strip()]
        if not selected_names:
            print("Error: --datasets value cannot be empty.", file=sys.stderr)
            sys.exit(1)
        
        available_datasets = {d.__class__.__name__: d for d in datasets}
        unknown = [name for name in selected_names if name not in available_datasets]
        if unknown:
            print(f"Error: Unknown dataset(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Available datasets: {', '.join(available_datasets.keys())}", file=sys.stderr)
            sys.exit(1)
        
        # Preserve original order
        datasets = [d for d in datasets if d.__class__.__name__ in selected_names]

    if not args.start or not args.end:
        parser.error("the following arguments are required: --start, --end (unless --list-datasets is used)")

    config = load_config()
    setup_logging(config.get("logging", {}).get("level", "INFO"))
    
    logger = logging.getLogger(__name__)

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

        if not args.dry_run:
            logger.info("Starting entsoe-data-pipeline")

        client = EntsoeClient(
            api_key=config["api"]["key"],
            retry_count=config["api"].get("retry_count", 5),
            backoff_factor=config["api"].get("backoff_factor", 1.0)
        )
        
        io_handler = IOHandler(
            base_path=config["storage"].get("base_path", "outputs"),
            formats=config["storage"].get("formats", ["csv"])
        )

        if args.dry_run:
            from datetime import timedelta
            from src.utils import to_utc, format_date_path
            
            start_utc = to_utc(start_dt).replace(hour=0, minute=0, second=0, microsecond=0)
            end_utc = to_utc(end_dt)
            num_days = (end_utc.date() - start_utc.date()).days
            
            print("--- DRY RUN MODE ---")
            print(f"Date range: {start_utc.date()} to {end_utc.date()} ({num_days} days)")
            print(f"Datasets: {', '.join([d.__class__.__name__ for d in datasets])}")
            print("\nExecution Plan:")
            
            current_date = start_utc
            while current_date < end_utc:
                date_path = format_date_path(current_date)
                for dataset in datasets:
                    filename = dataset.get_filename(current_date)
                    missing = io_handler.get_missing_formats(dataset.name, date_path, filename)
                    
                    status = "WILL PROCESS"
                    if not args.force and not missing:
                        status = "SKIPPED (exists)"
                    elif args.force:
                        status = "WILL OVERWRITE"
                        
                    planned_paths = [os.path.join(io_handler.base_path, dataset.name, date_path, f"{filename}.{fmt}") for fmt in io_handler.formats]
                    
                    print(f"  - [{status}] {dataset.__class__.__name__} for {current_date.date()}")
                    for p in planned_paths:
                        exists_str = "(already exists)" if os.path.exists(p) else ""
                        print(f"    -> {p} {exists_str}")
                
                current_date += timedelta(days=1)
            
            print("\nDry run completed. Pipeline execution skipped.")
            sys.exit(0)

        pipeline = Pipeline(client, io_handler, force=args.force)
        
        pipeline.run(datasets, start_dt, end_dt)
        
        logger.info("Download completed successfully")

    except Exception:
        logger.exception("Application failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
