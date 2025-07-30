#!/usr/bin/env python3
"""
Batch Greek Dictionary Scraper Wrapper
Scrapes the complete Greek-Dutch dictionary in batches of 200 lemmas
with error handling and automatic retry/stop functionality.

Wim Otte (w.m.otte@umutrecht.nl)

"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from selenium.common.exceptions import TimeoutException, WebDriverException

# Import the main scraper class
try:
    from greek_dict_scraper import GreekDictScraper
except ImportError:
    print("ERROR: Could not import greek_dict_scraper.py")
    print("Make sure greek_dict_scraper.py is in the same directory as this script.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchScraperManager:
    def __init__(self, 
                 batch_size: int = 200, 
                 max_errors: int = 5, 
                 max_consecutive_errors: int = 3,
                 output_dir: str = "scraped_batches",
                 delay: float = 1.0,
                 timeout: int = 15,
                 headless: bool = True):
        """
        Initialize the batch scraper manager.
        
        Args:
            batch_size: Number of lemmas per batch
            max_errors: Maximum total errors before stopping
            max_consecutive_errors: Maximum consecutive errors before stopping
            output_dir: Directory to save batch files
            delay: Delay between requests
            timeout: Timeout for selenium operations
            headless: Run browser in headless mode
        """
        self.batch_size = batch_size
        self.max_errors = max_errors
        self.max_consecutive_errors = max_consecutive_errors
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.timeout = timeout
        self.headless = headless
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Error tracking
        self.total_errors = 0
        self.consecutive_errors = 0
        self.error_log = []
        
        # Progress tracking
        self.total_lemmas = 43627  # 0 to 43626 inclusive
        self.completed_batches = []
        self.failed_batches = []
        
        # Statistics
        self.start_time = None
        self.total_scraped = 0
        
    def load_progress(self) -> Tuple[int, List[int]]:
        """Load progress from existing batch files and return next start position."""
        progress_file = self.output_dir / "progress.json"
        completed_ranges = []
        
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    completed_ranges = progress_data.get('completed_ranges', [])
                    self.failed_batches = progress_data.get('failed_batches', [])
                    logger.info(f"Loaded progress: {len(completed_ranges)} completed batches")
            except Exception as e:
                logger.warning(f"Could not load progress file: {e}")
        
        # Find existing batch files
        batch_files = list(self.output_dir.glob("batch_*.json"))
        for batch_file in batch_files:
            try:
                # Extract range from filename: batch_0000_0999.json
                parts = batch_file.stem.split('_')
                if len(parts) >= 3:
                    start_id = int(parts[1])
                    end_id = int(parts[2])
                    if [start_id, end_id] not in completed_ranges:
                        completed_ranges.append([start_id, end_id])
            except ValueError:
                continue
        
        # Sort completed ranges
        completed_ranges.sort()
        self.completed_batches = completed_ranges
        
        # Find next uncompleted batch
        next_start = 0
        for start, end in completed_ranges:
            if start == next_start:
                next_start = end + 1
            else:
                break
        
        return next_start, completed_ranges
    
    def save_progress(self):
        """Save current progress to file."""
        progress_file = self.output_dir / "progress.json"
        progress_data = {
            'last_updated': datetime.now().isoformat(),
            'completed_ranges': self.completed_batches,
            'failed_batches': self.failed_batches,
            'total_errors': self.total_errors,
            'error_log': self.error_log[-10:]  # Keep last 10 errors
        }
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save progress: {e}")
    
    def scrape_batch(self, start_id: int, end_id: int) -> bool:
        """
        Scrape a single batch of lemmas.
        
        Returns:
            True if successful, False if failed
        """
        batch_filename = self.output_dir / f"batch_{start_id:04d}_{end_id:04d}.json"
        
        logger.info(f"Starting batch: {start_id}-{end_id} ({end_id - start_id + 1} lemmas)")
        
        try:
            with GreekDictScraper(delay=self.delay, headless=self.headless, timeout=self.timeout) as scraper:
                lemmas = scraper.scrape_range(start_id, end_id)
                
                if lemmas:
                    scraper.save_to_file(lemmas, str(batch_filename))
                    self.completed_batches.append([start_id, end_id])
                    self.total_scraped += len(lemmas)
                    self.consecutive_errors = 0  # Reset consecutive error counter
                    
                    logger.info(f"✓ Batch {start_id}-{end_id} completed: {len(lemmas)} lemmas saved")
                    return True
                else:
                    raise Exception("No lemmas retrieved")
                    
        except (TimeoutException, WebDriverException) as e:
            error_msg = f"Selenium error in batch {start_id}-{end_id}: {str(e)[:100]}..."
            logger.error(error_msg)
            self._handle_error(start_id, end_id, error_msg)
            return False
            
        except Exception as e:
            error_msg = f"General error in batch {start_id}-{end_id}: {str(e)[:100]}..."
            logger.error(error_msg)
            self._handle_error(start_id, end_id, error_msg)
            return False
    
    def _handle_error(self, start_id: int, end_id: int, error_msg: str):
        """Handle batch errors and update counters."""
        self.total_errors += 1
        self.consecutive_errors += 1
        self.failed_batches.append([start_id, end_id])
        
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'batch_range': [start_id, end_id],
            'error': error_msg
        }
        self.error_log.append(error_entry)
        
        logger.warning(f"Error count: {self.consecutive_errors} consecutive, {self.total_errors} total")
    
    def should_stop(self) -> bool:
        """Determine if scraping should stop due to errors."""
        if self.total_errors >= self.max_errors:
            logger.error(f"Stopping: reached maximum total errors ({self.max_errors})")
            return True
            
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.error(f"Stopping: reached maximum consecutive errors ({self.max_consecutive_errors})")
            return True
            
        return False
    
    def calculate_progress(self, current_pos: int) -> Dict:
        """Calculate and return progress statistics."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        progress_pct = (current_pos / self.total_lemmas) * 100
        
        # Estimate time remaining
        if current_pos > 0 and elapsed_time > 0:
            rate = current_pos / elapsed_time
            remaining_lemmas = self.total_lemmas - current_pos
            eta_seconds = remaining_lemmas / rate
            eta_formatted = f"{eta_seconds // 3600:.0f}h {(eta_seconds % 3600) // 60:.0f}m"
        else:
            eta_formatted = "calculating..."
        
        return {
            'current_position': current_pos,
            'total_lemmas': self.total_lemmas,
            'progress_percent': progress_pct,
            'completed_batches': len(self.completed_batches),
            'failed_batches': len(self.failed_batches),
            'total_scraped': self.total_scraped,
            'elapsed_time_formatted': f"{elapsed_time // 3600:.0f}h {(elapsed_time % 3600) // 60:.0f}m",
            'eta_formatted': eta_formatted,
            'errors': {
                'total': self.total_errors,
                'consecutive': self.consecutive_errors
            }
        }
    
    def run(self, start_from: int = None, resume: bool = True):
        """
        Run the complete batch scraping process.
        
        Args:
            start_from: Override start position (ignore existing progress)
            resume: Whether to resume from existing progress
        """
        self.start_time = time.time()
        
        if resume and start_from is None:
            next_start, _ = self.load_progress()
            logger.info(f"Resuming from position {next_start}")
        else:
            next_start = start_from or 0
            logger.info(f"Starting fresh from position {next_start}")
        
        # Generate batch ranges
        current_pos = next_start
        
        while current_pos < self.total_lemmas:
            if self.should_stop():
                break
            
            # Calculate batch end (don't exceed total)
            batch_end = min(current_pos + self.batch_size - 1, self.total_lemmas - 1)
            
            # Skip if this batch is already completed
            if [current_pos, batch_end] in self.completed_batches:
                logger.info(f"Skipping already completed batch: {current_pos}-{batch_end}")
                current_pos = batch_end + 1
                continue
            
            # Show progress
            progress = self.calculate_progress(current_pos)
            logger.info(f"Progress: {progress['progress_percent']:.1f}% "
                       f"({progress['current_position']}/{progress['total_lemmas']}) "
                       f"ETA: {progress['eta_formatted']}")
            
            # Scrape the batch
            success = self.scrape_batch(current_pos, batch_end)
            
            # Save progress after each batch
            self.save_progress()
            
            if success:
                current_pos = batch_end + 1
            else:
                # On failure, try next batch (don't get stuck on same batch)
                current_pos = batch_end + 1
                
                # Add delay after errors
                error_delay = min(self.consecutive_errors * 30, 300)  # Max 5 minutes
                if error_delay > 0:
                    logger.info(f"Waiting {error_delay}s before next batch due to errors...")
                    time.sleep(error_delay)
        
        # Final summary
        self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final scraping summary."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        logger.info("=" * 60)
        logger.info("SCRAPING COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total elapsed time: {elapsed_time // 3600:.0f}h {(elapsed_time % 3600) // 60:.0f}m")
        logger.info(f"Completed batches: {len(self.completed_batches)}")
        logger.info(f"Failed batches: {len(self.failed_batches)}")
        logger.info(f"Total lemmas scraped: {self.total_scraped}")
        logger.info(f"Total errors: {self.total_errors}")
        
        if self.failed_batches:
            logger.warning("Failed batch ranges:")
            for start, end in self.failed_batches:
                logger.warning(f"  {start}-{end}")
        
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        logger.info("Progress saved to progress.json")

def main():
    parser = argparse.ArgumentParser(description='Batch scraper for Greek-Dutch dictionary')
    parser.add_argument('--batch-size', type=int, default=200, help='Lemmas per batch (default: 200)')
    parser.add_argument('--max-errors', type=int, default=5, help='Max total errors before stopping (default: 5)')
    parser.add_argument('--max-consecutive-errors', type=int, default=3, help='Max consecutive errors (default: 3)')
    parser.add_argument('--output-dir', type=str, default='scraped_batches', help='Output directory (default: scraped_batches)')
    parser.add_argument('--delay', type=float, default=0.3, help='Delay between requests (default: 1.0)')
    parser.add_argument('--timeout', type=int, default=15, help='Selenium timeout (default: 15)')
    parser.add_argument('--start-from', type=int, help='Start from specific lemma ID (ignores resume)')
    parser.add_argument('--no-resume', action='store_true', help='Don\'t resume from existing progress')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    
    args = parser.parse_args()
    
    # Create batch manager
    manager = BatchScraperManager(
        batch_size=args.batch_size,
        max_errors=args.max_errors,
        max_consecutive_errors=args.max_consecutive_errors,
        output_dir=args.output_dir,
        delay=args.delay,
        timeout=args.timeout,
        headless=not args.visible
    )
    
    try:
        # Run the batch scraping
        manager.run(
            start_from=args.start_from,
            resume=not args.no_resume
        )
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        manager.save_progress()
        logger.info("Progress saved. You can resume later with the same command.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        manager.save_progress()

if __name__ == "__main__":
    main()
