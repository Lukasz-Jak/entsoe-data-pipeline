import logging
from datetime import datetime, timedelta
from typing import List
from src.api_client import EntsoeClient
from src.io_handler import IOHandler
from src.datasets.base import BaseDataset
from src.utils import to_utc, format_date_path

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, client: EntsoeClient, io_handler: IOHandler, force: bool = False):
        self.client = client
        self.io_handler = io_handler
        self.force = force

    def run(self, datasets: List[BaseDataset], start_date: datetime, end_date: datetime) -> None:
        """Execute fetch -> normalize -> write for each dataset and each day in range."""
        current_date = to_utc(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
        target_end = to_utc(end_date)
        processed_count = 0
        skipped_count = 0

        while current_date < target_end:
            day_end = current_date + timedelta(days=1)
            date_path = format_date_path(current_date)

            for dataset in datasets:
                filename = dataset.get_filename(current_date)
                
                if not self.force and self.io_handler.exists(dataset.name, date_path, filename):
                    logger.info(f"Skipped: {dataset.name} for {current_date.date()} (already exists)")
                    skipped_count += 1
                    continue

                try:
                    logger.info(f"Processing {dataset.name} for {current_date.date()}...")
                    raw_data = dataset.fetch(self.client, current_date, day_end)
                    if raw_data is None or raw_data.empty:
                        logger.warning(f"No data for {dataset.name} on {current_date.date()}")
                        continue
                    
                    normalized_data = dataset.normalize(raw_data)
                    self.io_handler.write(normalized_data, dataset.name, date_path, filename)
                    logger.info(f"Successfully processed {dataset.name} for {current_date.date()}")
                    processed_count += 1
                except Exception:
                    logger.exception(f"Failed to process {dataset.name} for {current_date.date()}")

            current_date = day_end

        logger.info(f"Pipeline finished successfully (processed={processed_count}, skipped={skipped_count})")
