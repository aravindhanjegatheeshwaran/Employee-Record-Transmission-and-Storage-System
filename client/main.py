# client/main.py
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
    parser = argparse.ArgumentParser(description='Employee Record Transmission Client')
    
    parser.add_argument('--file', '-f', type=str, default=settings.CSV_FILE_PATH,
                        help='CSV file with employee records')
    
    parser.add_argument('--mode', '-m', type=str, choices=['http', 'kafka', 'websocket'],
                        default=settings.COMM_MODE.value,
                        help='Communication mode - note: kafka and websocket require additional packages')
    
    parser.add_argument('--batch-size', '-b', type=int, default=settings.BATCH_SIZE,
                        help='Records per batch')
    
    parser.add_argument('--workers', '-w', type=int, default=settings.MAX_WORKERS,
                        help='Concurrent worker count')
    
    parser.add_argument('--server', '-s', type=str, default=settings.SERVER_URL,
                        help='Server URL')
    
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Failed records output file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        logger.error(f"CSV file not found: {args.file}")
        return 1
    
    if args.output and os.path.dirname(args.output):
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"failed_records_{timestamp}.csv"
    
    # Create the client with the chosen communication mode
    try:
        logger.info(f"Starting transmission using {args.mode} mode")
        client = EmployeeClient(
            server_url=args.server,
            comm_mode=CommunicationMode(args.mode),
            batch_size=args.batch_size,
            max_workers=args.workers
        )
    except ImportError as e:
        # Handle missing dependency errors specifically
        logger.error(f"Dependency error: {str(e)}")
        logger.error(f"Please install the required packages in requirements.txt")
        logger.error(f"You can use HTTP mode as a fallback: --mode http")
        return 1
    
    try:
        
        # Initialize the client and process the file
        await client.initialize()
        
        start_time = time.time()
        total_records, successful_count, failed_records = await client.process_csv_file(args.file)
        elapsed_time = time.time() - start_time
        
        throughput = total_records / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(f"Processing completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total: {total_records}, Success: {successful_count}, Failed: {len(failed_records)}")
        logger.info(f"Success rate: {successful_count/total_records*100:.1f}%")
        logger.info(f"Throughput: {throughput:.1f} records/second")
        
        if failed_records:
            save_failed_records(failed_records, args.output)
            logger.info(f"Failed records saved to {args.output}")
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    finally:
        if 'client' in locals() and client:
            await client.close()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
