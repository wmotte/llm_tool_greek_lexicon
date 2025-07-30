#!/usr/bin/env python3
"""
Script to merge multiple Greek dictionary JSON batch files into a single JSON file
and verify that all lemma IDs are sequential.

Wim Otte (w.m.otte@umutrecht.nl)

"""

import json
import os
import glob
from typing import List, Dict, Any
import sys

def load_batch_file(filepath: str) -> List[Dict[Any, Any]]:
    """Load a single batch JSON file and return its lemmas."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('lemmas', [])
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {filepath}: {e}")
        return []
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return []
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return []

def merge_dictionary_files(batch_directory: str = "scraped_batches", output_file: str = "merged_dictionary.json") -> bool:
    """
    Merge all batch JSON files into a single dictionary file.
    
    Args:
        batch_directory: Directory containing batch JSON files
        output_file: Output filename for merged dictionary
    
    Returns:
        True if successful, False otherwise
    """
    
    # Find all batch JSON files
    batch_pattern = os.path.join(batch_directory, "batch_*.json")
    batch_files = glob.glob(batch_pattern)
    
    if not batch_files:
        print(f"No batch files found in {batch_directory}")
        return False
    
    print(f"Found {len(batch_files)} batch files")
    
    # Sort files to process in order
    batch_files.sort()
    
    all_lemmas = []
    total_processed = 0
    
    # Process each batch file
    for batch_file in batch_files:
        print(f"Processing {os.path.basename(batch_file)}...")
        lemmas = load_batch_file(batch_file)
        
        if lemmas:
            all_lemmas.extend(lemmas)
            total_processed += len(lemmas)
            print(f"  Added {len(lemmas)} lemmas (total so far: {total_processed})")
        else:
            print(f"  No lemmas found in {batch_file}")
    
    if not all_lemmas:
        print("No lemmas found in any batch files")
        return False
    
    # Sort lemmas by lemma_id to ensure proper ordering
    print("Sorting lemmas by ID...")
    all_lemmas.sort(key=lambda x: x.get('lemma_id', 0))
    
    # Check for sequential IDs
    print("Checking for sequential IDs...")
    missing_ids = []
    duplicate_ids = []
    id_counts = {}
    
    # Count occurrences of each ID
    for lemma in all_lemmas:
        lemma_id = lemma.get('lemma_id')
        if lemma_id is not None:
            id_counts[lemma_id] = id_counts.get(lemma_id, 0) + 1
    
    # Find duplicates
    for lemma_id, count in id_counts.items():
        if count > 1:
            duplicate_ids.append(lemma_id)
    
    # Check for missing IDs in sequence
    if id_counts:
        min_id = min(id_counts.keys())
        max_id = max(id_counts.keys())
        
        print(f"ID range: {min_id} to {max_id}")
        print(f"Expected count: {max_id - min_id + 1}")
        print(f"Actual unique IDs: {len(id_counts)}")
        
        for i in range(min_id, max_id + 1):
            if i not in id_counts:
                missing_ids.append(i)
    
    # Report findings
    if duplicate_ids:
        print(f"⚠️  Found {len(duplicate_ids)} duplicate IDs: {duplicate_ids[:10]}{'...' if len(duplicate_ids) > 10 else ''}")
    
    if missing_ids:
        print(f"⚠️  Found {len(missing_ids)} missing IDs: {missing_ids[:10]}{'...' if len(missing_ids) > 10 else ''}")
        
        # Write missing IDs to a text file
        missing_ids_file = "missing_ids.txt"
        try:
            with open(missing_ids_file, 'w', encoding='utf-8') as f:
                for missing_id in sorted(missing_ids):
                    f.write(f"{missing_id}\n")
            print(f"📝 Missing IDs written to {missing_ids_file}")
        except Exception as e:
            print(f"❌ Error writing missing IDs file: {e}")
    
    if not missing_ids and not duplicate_ids:
        print("✅ All IDs are sequential with no duplicates!")
    
    # Create merged dictionary structure
    merged_data = {
        "metadata": {
            "merge_timestamp": "2025-07-03",
            "source_files": len(batch_files),
            "total_lemmas": len(all_lemmas),
            "id_range": {
                "min": min(id_counts.keys()) if id_counts else None,
                "max": max(id_counts.keys()) if id_counts else None
            },
            "validation": {
                "sequential_ids": len(missing_ids) == 0 and len(duplicate_ids) == 0,
                "missing_ids_count": len(missing_ids),
                "duplicate_ids_count": len(duplicate_ids)
            }
        },
        "lemmas": all_lemmas
    }
    
    # Write merged file
    print(f"Writing merged dictionary to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Successfully created {output_file}")
        print(f"📊 Total lemmas: {len(all_lemmas)}")
        return True
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        return False

def main():
    """Main function to run the merge process."""
    
    # Default paths - adjust as needed
    batch_directory = "scraped_batches"
    output_file = "merged_greek_dictionary.json"
    
    # Check if batch directory exists
    if not os.path.exists(batch_directory):
        print(f"Batch directory '{batch_directory}' not found!")
        print("Please ensure the directory exists or update the batch_directory variable.")
        sys.exit(1)
    
    print("🚀 Starting Greek Dictionary merge process...")
    print(f"📁 Source directory: {batch_directory}")
    print(f"📄 Output file: {output_file}")
    print("-" * 50)
    
    success = merge_dictionary_files(batch_directory, output_file)
    
    print("-" * 50)
    if success:
        print("🎉 Merge completed successfully!")
    else:
        print("❌ Merge failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
