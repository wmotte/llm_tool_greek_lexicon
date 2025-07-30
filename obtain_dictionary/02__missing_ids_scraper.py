#!/usr/bin/env python3
"""
Missing IDs Greek Dictionary Scraper
Scrapes only the missing lemma IDs from missing_ids.txt and saves to remaining_batch.json

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
from typing import List, Dict
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

class MissingIDsScraper:
    def __init__(self, 
                 missing_ids_file: str = "missing_ids.txt",
                 output_file: str = "remaining_batch.json",
                 max_errors: int = 10,
                 delay: float = 0.5,
                 timeout: int = 15,
                 headless: bool = True):
        """
        Initialize the missing IDs scraper.
        
        Args:
            missing_ids_file: Path to the file containing missing IDs
            output_file: Output JSON file name
            max_errors: Maximum errors before stopping
            delay: Delay between requests
            timeout: Timeout for selenium operations
            headless: Run browser in headless mode
        """
        self.missing_ids_file = Path(missing_ids_file)
        self.output_file = Path(output_file)
        self.max_errors = max_errors
        self.delay = delay
        self.timeout = timeout
        self.headless = headless
        
        # Error tracking
        self.total_errors = 0
        self.failed_ids = []
        self.error_log = []
        
        # Progress tracking
        self.missing_ids = []
        self.completed_ids = []
        self.scraped_lemmas = []
        
        # Statistics
        self.start_time = None
        
    def load_missing_ids(self) -> List[int]:
        """Load missing IDs from the text file."""
        if not self.missing_ids_file.exists():
            logger.error(f"Missing IDs file not found: {self.missing_ids_file}")
            return []
        
        try:
            with open(self.missing_ids_file, 'r', encoding='utf-8') as f:
                ids = []
                for line in f:
                    line = line.strip()
                    if line and line.isdigit():
                        ids.append(int(line))
                
                logger.info(f"Loaded {len(ids)} missing IDs from {self.missing_ids_file}")
                return sorted(ids)  # Sort for better progress tracking
                
        except Exception as e:
            logger.error(f"Error reading missing IDs file: {e}")
            return []
    
    def scrape_single_id(self, scraper: GreekDictScraper, lemma_id: int) -> bool:
        """
        Scrape a single lemma ID.
        
        Args:
            scraper: The GreekDictScraper instance
            lemma_id: The ID to scrape
            
        Returns:
            True if successful, False if failed
        """
        try:
            lemma = scraper.scrape_lemma(lemma_id)
            
            if lemma:
                self.scraped_lemmas.append(lemma)
                self.completed_ids.append(lemma_id)
                logger.debug(f"✓ Successfully scraped ID {lemma_id}")
                return True
            else:
                raise Exception(f"No data returned for ID {lemma_id}")
                
        except (TimeoutException, WebDriverException) as e:
            error_msg = f"Selenium error for ID {lemma_id}: {str(e)[:100]}..."
            logger.warning(error_msg)
            self._handle_error(lemma_id, error_msg)
            return False
            
        except Exception as e:
            error_msg = f"General error for ID {lemma_id}: {str(e)[:100]}..."
            logger.warning(error_msg)
            self._handle_error(lemma_id, error_msg)
            return False
    
    def _handle_error(self, lemma_id: int, error_msg: str):
        """Handle individual ID errors."""
        self.total_errors += 1
        self.failed_ids.append(lemma_id)
        
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'lemma_id': lemma_id,
            'error': error_msg
        }
        self.error_log.append(error_entry)
    
    def should_stop(self) -> bool:
        """Determine if scraping should stop due to errors."""
        if self.total_errors >= self.max_errors:
            logger.error(f"Stopping: reached maximum errors ({self.max_errors})")
            return True
        return False
    
    def save_results(self):
        """Save scraped lemmas to JSON file."""
        try:
            # Create the output structure similar to batch files
            output_data = {
                "metadata": {
                    "scrape_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "missing_ids_scraper",
                    "missing_ids_file": str(self.missing_ids_file),
                    "statistics": {
                        "total_requested": len(self.missing_ids),
                        "successfully_scraped": len(self.scraped_lemmas),
                        "failed_ids": len(self.failed_ids),
                        "success_rate": len(self.scraped_lemmas) / len(self.missing_ids) * 100 if self.missing_ids else 0,
                        "total_errors": self.total_errors
                    },
                    "failed_ids": self.failed_ids,
                    "error_log": self.error_log[-20:]  # Keep last 20 errors
                },
                "lemmas": self.scraped_lemmas
            }
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Results saved to {self.output_file}")
            logger.info(f"  Successfully scraped: {len(self.scraped_lemmas)}")
            logger.info(f"  Failed IDs: {len(self.failed_ids)}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def save_failed_ids(self):
        """Save failed IDs to a separate file for potential retry."""
        if self.failed_ids:
            failed_file = self.output_file.with_suffix('.failed_ids.txt')
            try:
                with open(failed_file, 'w', encoding='utf-8') as f:
                    for failed_id in sorted(self.failed_ids):
                        f.write(f"{failed_id}\n")
                logger.info(f"Failed IDs saved to {failed_file}")
            except Exception as e:
                logger.error(f"Error saving failed IDs: {e}")
    
    def calculate_progress(self, current_index: int) -> Dict:
        """Calculate and return progress statistics."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        total_ids = len(self.missing_ids)
        progress_pct = (current_index / total_ids) * 100 if total_ids > 0 else 0
        
        # Estimate time remaining
        if current_index > 0 and elapsed_time > 0:
            rate = current_index / elapsed_time
            remaining_ids = total_ids - current_index
            eta_seconds = remaining_ids / rate
            eta_formatted = f"{eta_seconds // 60:.0f}m {eta_seconds % 60:.0f}s"
        else:
            eta_formatted = "calculating..."
        
        return {
            'current_index': current_index,
            'total_ids': total_ids,
            'progress_percent': progress_pct,
            'successful_scrapes': len(self.scraped_lemmas),
            'failed_scrapes': len(self.failed_ids),
            'elapsed_time_formatted': f"{elapsed_time // 60:.0f}m {elapsed_time % 60:.0f}s",
            'eta_formatted': eta_formatted,
            'error_count': self.total_errors
        }
    
    def run(self):
        """Run the missing IDs scraping process."""
        self.start_time = time.time()
        
        # Load missing IDs
        self.missing_ids = self.load_missing_ids()
        if not self.missing_ids:
            logger.error("No missing IDs to process")
            return
        
        logger.info(f"Starting to scrape {len(self.missing_ids)} missing IDs")
        logger.info(f"Output file: {self.output_file}")
        logger.info("=" * 60)
        
        try:
            with GreekDictScraper(delay=self.delay, headless=self.headless, timeout=self.timeout) as scraper:
                
                for i, lemma_id in enumerate(self.missing_ids):
                    if self.should_stop():
                        logger.warning("Stopping due to too many errors")
                        break
                    
                    # Show progress every 10 IDs or for the first few
                    if i % 10 == 0 or i < 5:
                        progress = self.calculate_progress(i)
                        logger.info(f"Progress: {progress['progress_percent']:.1f}% "
                                   f"({i}/{progress['total_ids']}) "
                                   f"Success: {progress['successful_scrapes']} "
                                   f"Failed: {progress['failed_scrapes']} "
                                   f"ETA: {progress['eta_formatted']}")
                    
                    # Scrape the ID
                    success = self.scrape_single_id(scraper, lemma_id)
                    
                    # Add delay between requests
                    if i < len(self.missing_ids) - 1:  # Don't delay after last ID
                        time.sleep(self.delay)
                
        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error during scraping: {e}")
        
        # Save results
        self.save_results()
        self.save_failed_ids()
        
        # Final summary
        self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final scraping summary."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        logger.info("=" * 60)
        logger.info("MISSING IDs SCRAPING COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total elapsed time: {elapsed_time // 60:.0f}m {elapsed_time % 60:.0f}s")
        logger.info(f"Requested IDs: {len(self.missing_ids)}")
        logger.info(f"Successfully scraped: {len(self.scraped_lemmas)}")
        logger.info(f"Failed to scrape: {len(self.failed_ids)}")
        
        if self.missing_ids:
            success_rate = len(self.scraped_lemmas) / len(self.missing_ids) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
        
        logger.info(f"Total errors: {self.total_errors}")
        logger.info(f"Output saved to: {self.output_file}")
        
        if self.failed_ids:
            logger.warning(f"Failed IDs ({len(self.failed_ids)}): {self.failed_ids[:10]}{'...' if len(self.failed_ids) > 10 else ''}")

def main():
    parser = argparse.ArgumentParser(description='Scraper for missing Greek dictionary IDs')
    parser.add_argument('--missing-ids-file', type=str, default='missing_ids.txt', 
                       help='File containing missing IDs (default: missing_ids.txt)')
    parser.add_argument('--output-file', type=str, default='remaining_batch.json',
                       help='Output JSON file (default: remaining_batch.json)')
    parser.add_argument('--max-errors', type=int, default=1000, 
                       help='Max errors before stopping (default: 10)')
    parser.add_argument('--delay', type=float, default=0.5, 
                       help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--timeout', type=int, default=15, 
                       help='Selenium timeout (default: 15)')
    parser.add_argument('--visible', action='store_true', 
                       help='Run browser in visible mode')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = MissingIDsScraper(
        missing_ids_file=args.missing_ids_file,
        output_file=args.output_file,
        max_errors=args.max_errors,
        delay=args.delay,
        timeout=args.timeout,
        headless=not args.visible
    )
    
    try:
        scraper.run()
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
