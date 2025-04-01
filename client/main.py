#client/main.py
import asyncio
import logging
import argparse
import sys
import os
import time
from datetime import datetime

from config import settings, CommunicationMode
from employee_client import EmployeeClient
from utils import save_failed_records

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('client.log')
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the client application"""
    parser = argparse.ArgumentParser(description='Employee Record Transmission Client')
    
    parser.add_argument('--file', '-f', type=str, default=settings.CSV_FILE_PATH,
                        help='Path to CSV file containing employee records')
    
    parser.add_argument('--mode', '-m', type=str, choices=['http', 'kafka', 'websocket'],
                        default=settings.COMM_MODE.value,
                        help='Communication mode (http, kafka, websocket)')
    
    parser.add_argument('--batch-size', '-b', type=int, default=settings.BATCH_SIZE,
                        help='Batch size for processing')
    
    parser.add_argument('--workers', '-w', type=int, default=settings.MAX_WORKERS,
                        help='Maximum number of concurrent workers')
    
    parser.add_argument('--server', '-s', type=str, default=settings.SERVER_URL,
                        help='Server URL')
    
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file for failed records')
    
    args = parser.parse_args()
    
    # Validate args
    if not os.path.exists(args.file):
        logger.error(f"CSV file not found: {args.file}")
        sys.exit(1)
    
    # Create output directory if needed
    if args.output and os.path.dirname(args.output):
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Set default output path if not provided
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"failed_records_{timestamp}.csv"
    
    # Initialize the client
    client = EmployeeClient(
        server_url=args.server,
        comm_mode=CommunicationMode(args.mode),
        batch_size=args.batch_size,
        max_workers=args.workers
    )
    
    try:
        # Initialize client
        logger.info(f"Starting employee record transmission using {args.mode.upper()} mode")
        await client.initialize()
        
        # Process CSV file
        start_time = time.time()
        total_records, successful_count, failed_records = await client.process_csv_file(args.file)
        end_time = time.time()
        
        # Calculate statistics
        elapsed_time = end_time - start_time
        records_per_second = total_records / elapsed_time if elapsed_time > 0 else 0
        
        # Log summary
        logger.info(f"CSV processing completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total records: {total_records}")
        logger.info(f"Successful: {successful_count} ({successful_count/total_records*100:.2f}%)")
        logger.info(f"Failed: {len(failed_records)} ({len(failed_records)/total_records*100:.2f}%)")
        logger.info(f"Processing rate: {records_per_second:.2f} records/second")
        
        # Save failed records
        if failed_records:
            save_failed_records(failed_records, args.output)
            logger.info(f"Failed records saved to {args.output}")
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    finally:
        # Close the client
        try:
            await client.close()
        except Exception as e:
            logger.error(f"Error closing client: {str(e)}")


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
