#!/usr/bin/env python3
"""
Script to verify that Greek dictionary data was correctly imported into Neo4j.
Performs various checks to ensure data integrity and accessibility.

Wim Otte (w.m.otte@umcutrecht.nl)
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import random

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError


class DictionaryVerifier:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password", database: str = "dictionarygreekdutch"):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        
    def connect(self) -> bool:
        """Establish connection to Neo4j database."""
        try:
            print(f"Connecting to Neo4j at {self.uri}...")
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 'Connection successful' as message")
                message = result.single()["message"]
                print(f"✓ {message}")
                
            return True
            
        except ServiceUnavailable as e:
            print(f"✗ Cannot connect to Neo4j. Is the server running on {self.uri}?")
            print(f"Error: {e}")
            return False
        except AuthError as e:
            print(f"✗ Authentication failed. Check username/password.")
            print(f"Error: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error connecting to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            print("✓ Neo4j connection closed")
    
    def check_database_structure(self) -> bool:
        """Verify the basic database structure."""
        print("\n1. Checking database structure...")
        
        try:
            with self.driver.session(database=self.database) as session:
                # Check if Dictionary nodes exist
                result = session.run("MATCH (d:Dictionary) RETURN count(d) as count")
                dict_count = result.single()["count"]
                
                if dict_count == 0:
                    print("✗ No Dictionary nodes found")
                    return False
                print(f"✓ Found {dict_count} Dictionary nodes")
                
                # Check if Entry nodes exist
                result = session.run("MATCH (e:Entry) RETURN count(e) as count")
                entry_count = result.single()["count"]
                
                if entry_count == 0:
                    print("✗ No Entry nodes found")
                    return False
                print(f"✓ Found {entry_count} Entry nodes")
                
                # Check if Lemma nodes exist
                result = session.run("MATCH (l:Lemma) RETURN count(l) as count")
                lemma_count = result.single()["count"]
                
                if lemma_count == 0:
                    print("✗ No Lemma nodes found")
                    return False
                print(f"✓ Found {lemma_count} Lemma nodes")
                
                # Check relationships
                result = session.run("MATCH ()-[r:BELONGS_TO]->() RETURN count(r) as count")
                belongs_to_count = result.single()["count"]
                
                result = session.run("MATCH ()-[r:HAS_ENTRY]->() RETURN count(r) as count")
                has_entry_count = result.single()["count"]
                
                if belongs_to_count == 0:
                    print("✗ No BELONGS_TO relationships found")
                    return False
                print(f"✓ Found {belongs_to_count} BELONGS_TO relationships")
                
                if has_entry_count == 0:
                    print("✗ No HAS_ENTRY relationships found")
                    return False
                print(f"✓ Found {has_entry_count} HAS_ENTRY relationships")
                
                return True
                
        except Exception as e:
            print(f"✗ Error checking database structure: {e}")
            return False
    
    def check_dictionary_integrity(self) -> bool:
        """Check the integrity of dictionary data."""
        print("\n2. Checking dictionary integrity...")
        
        try:
            with self.driver.session(database=self.database) as session:
                # Check that all lemmas belong to a dictionary
                result = session.run("""
                    MATCH (l:Lemma)
                    WHERE NOT (l)-[:BELONGS_TO]->(:Dictionary)
                    RETURN count(l) as orphaned_lemmas
                """)
                orphaned_lemmas = result.single()["orphaned_lemmas"]
                
                if orphaned_lemmas > 0:
                    print(f"✗ Found {orphaned_lemmas} orphaned lemmas (not connected to any dictionary)")
                    return False
                print("✓ All lemmas are connected to dictionaries")
                
                # Check that all entries belong to a dictionary
                result = session.run("""
                    MATCH (e:Entry)
                    WHERE NOT (e)-[:BELONGS_TO]->(:Dictionary)
                    RETURN count(e) as orphaned_entries
                """)
                orphaned_entries = result.single()["orphaned_entries"]
                
                if orphaned_entries > 0:
                    print(f"✗ Found {orphaned_entries} orphaned entries (not connected to any dictionary)")
                    return False
                print("✓ All entries are connected to dictionaries")
                
                # Check that all lemmas have an entry
                result = session.run("""
                    MATCH (l:Lemma)
                    WHERE NOT (l)-[:HAS_ENTRY]->(:Entry)
                    RETURN count(l) as lemmas_without_entry
                """)
                lemmas_without_entry = result.single()["lemmas_without_entry"]
                
                if lemmas_without_entry > 0:
                    print(f"✗ Found {lemmas_without_entry} lemmas without entries")
                    return False
                print("✓ All lemmas have entries")
                
                # Check that all lemmas have required properties
                result = session.run("""
                    MATCH (l:Lemma)
                    WHERE l.id IS NULL OR l.text IS NULL
                    RETURN count(l) as incomplete_lemmas
                """)
                incomplete_lemmas = result.single()["incomplete_lemmas"]
                
                if incomplete_lemmas > 0:
                    print(f"✗ Found {incomplete_lemmas} lemmas with missing properties")
                    return False
                print("✓ All lemmas have required properties (id, text)")
                
                # Check that all entries have required properties
                result = session.run("""
                    MATCH (e:Entry)
                    WHERE e.id IS NULL OR e.text IS NULL OR e.original_key IS NULL
                    RETURN count(e) as incomplete_entries
                """)
                incomplete_entries = result.single()["incomplete_entries"]
                
                if incomplete_entries > 0:
                    print(f"✗ Found {incomplete_entries} entries with missing properties")
                    return False
                print("✓ All entries have required properties (id, text, original_key)")
                
                # Check for duplicate lemma IDs
                result = session.run("""
                    MATCH (l:Lemma)
                    WITH l.id as id, count(l) as count
                    WHERE count > 1
                    RETURN sum(count) as duplicate_ids
                """)
                duplicate_lemma_ids = result.single()["duplicate_ids"]
                
                if duplicate_lemma_ids and duplicate_lemma_ids > 0:
                    print(f"✗ Found {duplicate_lemma_ids} duplicate lemma IDs")
                    return False
                print("✓ All lemma IDs are unique")
                
                # Check for duplicate entry IDs
                result = session.run("""
                    MATCH (e:Entry)
                    WITH e.id as id, count(e) as count
                    WHERE count > 1
                    RETURN sum(count) as duplicate_ids
                """)
                duplicate_entry_ids = result.single()["duplicate_ids"]
                
                if duplicate_entry_ids and duplicate_entry_ids > 0:
                    print(f"✗ Found {duplicate_entry_ids} duplicate entry IDs")
                    return False
                print("✓ All entry IDs are unique")
                
                return True
                
        except Exception as e:
            print(f"✗ Error checking dictionary integrity: {e}")
            return False
    
    def check_against_source_files(self, dictionaries_dir: str) -> bool:
        """Compare database content against original JSON files."""
        print("\n3. Comparing against source files...")
        
        try:
            # Load source files
            directory = Path(dictionaries_dir)
            if not directory.exists():
                print(f"✗ Source directory '{dictionaries_dir}' not found")
                return False
            
            json_files = list(directory.glob("*.json"))
            if not json_files:
                print(f"✗ No JSON files found in '{dictionaries_dir}'")
                return False
            
            source_data = {}
            total_source_entries = 0
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    dict_name = file_path.stem
                    source_data[dict_name] = data
                    total_source_entries += len(data)
                except Exception as e:
                    print(f"✗ Error loading {file_path.name}: {e}")
                    return False
            
            print(f"✓ Loaded {len(source_data)} source dictionaries with {total_source_entries} total entries")
            
            # Compare with database
            with self.driver.session(database=self.database) as session:
                # Check dictionary count
                result = session.run("MATCH (d:Dictionary) RETURN d.name as name ORDER BY name")
                db_dicts = [record["name"] for record in result]
                source_dicts = list(source_data.keys())
                
                if set(db_dicts) != set(source_dicts):
                    print(f"✗ Dictionary mismatch:")
                    print(f"  Source: {sorted(source_dicts)}")
                    print(f"  Database: {sorted(db_dicts)}")
                    return False
                print(f"✓ All {len(source_dicts)} dictionaries present in database")
                
                # Check entry counts for each dictionary
                for dict_name in source_dicts:
                    source_entries = source_data[dict_name]
                    
                    # Count entries and lemmas created from this dictionary
                    result = session.run("""
                        MATCH (d:Dictionary {name: $dict_name})<-[:BELONGS_TO]-(e:Entry)
                        WITH count(e) as entry_count
                        MATCH (d:Dictionary {name: $dict_name})<-[:BELONGS_TO]-(l:Lemma)
                        RETURN entry_count, count(l) as lemma_count
                    """, dict_name=dict_name)
                    
                    record = result.single()
                    db_entry_count = record["entry_count"]
                    db_lemma_count = record["lemma_count"]
                    
                    if db_entry_count != len(source_entries):
                        print(f"✗ Entry count mismatch for {dict_name}:")
                        print(f"  Source: {len(source_entries)} entries")
                        print(f"  Database: {db_entry_count} entries")
                        return False
                    
                    print(f"✓ {dict_name}: {len(source_entries)} entries → {db_lemma_count} lemmas")
                
                return True
                
        except Exception as e:
            print(f"✗ Error comparing against source files: {e}")
            return False
    
    def test_search_functionality(self) -> bool:
        """Test various search scenarios to ensure data is accessible."""
        print("\n4. Testing search functionality...")
        
        try:
            with self.driver.session(database=self.database) as session:
                # Test 1: Search by exact lemma text
                result = session.run("""
                    MATCH (l:Lemma {text: $text})-[:HAS_ENTRY]->(e:Entry)
                    RETURN l.text, e.text as entry_text
                    LIMIT 1
                """, text="Α")
                
                records = list(result)
                if records:
                    print("✓ Exact text search works")
                else:
                    print("? No results for exact text search (this might be normal)")
                
                # Test 2: Search by partial lemma text
                result = session.run("""
                    MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)
                    WHERE l.text CONTAINS $text
                    RETURN l.text, e.text as entry_text
                    LIMIT 3
                """, text="αβ")
                
                records = list(result)
                if records:
                    print(f"✓ Partial text search works ({len(records)} results)")
                else:
                    print("? No results for partial text search")
                
                # Test 3: Get sample entries from each dictionary
                result = session.run("""
                    MATCH (d:Dictionary)<-[:BELONGS_TO]-(l:Lemma)-[:HAS_ENTRY]->(e:Entry)
                    WITH d.name as dict_name, collect({lemma: l, entry: e})[0] as sample
                    RETURN dict_name, sample.lemma.text as lemma_text, 
                           left(sample.entry.text, 100) as entry_preview
                    ORDER BY dict_name
                """)
                
                records = list(result)
                if records:
                    print(f"✓ Dictionary sampling works:")
                    for record in records:
                        preview = record["entry_preview"]
                        if len(preview) == 100:
                            preview += "..."
                        print(f"  {record['dict_name']}: '{record['lemma_text']}' → {preview}")
                else:
                    print("✗ Dictionary sampling failed")
                    return False
                
                # Test 4: Check for entries with multiple lemma variants
                result = session.run("""
                    MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)
                    WHERE e.original_key CONTAINS '|'
                    WITH e.original_key as original_key, collect(l.text) as lemma_variants
                    WHERE size(lemma_variants) > 1
                    RETURN original_key, lemma_variants
                    LIMIT 5
                """)
                
                records = list(result)
                if records:
                    print(f"✓ Multi-variant entries found ({len(records)} examples):")
                    for record in records:
                        variants = ", ".join(record['lemma_variants'])
                        print(f"  Key: '{record['original_key']}' → Lemmas: [{variants}]")
                else:
                    print("? No multi-variant entries found (this might be normal)")
                
                # Test 5: Test getting entry from lemma
                result = session.run("""
                    MATCH (l:Lemma {text: $text})-[:HAS_ENTRY]->(e:Entry)
                    RETURN l.text, e.text as entry_text, e.original_key
                    LIMIT 1
                """, text="ἀβοήθητος")
                
                records = list(result)
                if records:
                    print("✓ Lemma-to-entry lookup works")
                    record = records[0]
                    print(f"  '{record['l.text']}' → Entry key: '{record['e.original_key']}'")
                else:
                    print("? No specific lemma found for lookup test")
                
                return True
                
        except Exception as e:
            print(f"✗ Error testing search functionality: {e}")
            return False
    
    def get_detailed_statistics(self) -> bool:
        """Generate detailed statistics about the imported data."""
        print("\n5. Detailed statistics...")
        
        try:
            with self.driver.session(database=self.database) as session:
                # Dictionary statistics - simplified version to avoid syntax issues
                result = session.run("""
                    MATCH (d:Dictionary)<-[:BELONGS_TO]-(e:Entry)
                    WITH d.name as dict_name, count(e) as entry_count
                    MATCH (d:Dictionary {name: dict_name})<-[:BELONGS_TO]-(l:Lemma)
                    RETURN dict_name, entry_count, count(l) as lemma_count
                    ORDER BY dict_name
                """)
                
                print("Dictionary Statistics:")
                print("-" * 60)
                print(f"{'Dictionary':<15} {'Entries':<8} {'Lemmas':<8}")
                print("-" * 60)
                
                total_entries = 0
                total_lemmas = 0
                
                for record in result:
                    dict_name = record["dict_name"]
                    entries = record["entry_count"]
                    lemmas = record["lemma_count"]
                    
                    print(f"{dict_name:<15} {entries:<8} {lemmas:<8}")
                    
                    total_entries += entries
                    total_lemmas += lemmas
                
                print("-" * 60)
                print(f"{'TOTAL':<15} {total_entries:<8} {total_lemmas:<8}")
                
                # Additional statistics
                result = session.run("""
                    MATCH (e:Entry)
                    WHERE e.original_key CONTAINS '|'
                    RETURN count(e) as multi_variant_entries
                """)
                multi_variant_entries = result.single()["multi_variant_entries"]
                
                result = session.run("""
                    MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)
                    WITH e, count(l) as lemma_count
                    RETURN max(lemma_count) as max_lemmas_per_entry
                """)
                max_lemmas = result.single()["max_lemmas_per_entry"]
                
                # Check text length statistics separately
                result = session.run("""
                    MATCH (l:Lemma)
                    WITH min(size(l.text)) as min_lemma_length, max(size(l.text)) as max_lemma_length
                    MATCH (e:Entry)
                    RETURN min_lemma_length, max_lemma_length,
                           min(size(e.text)) as min_entry_length,
                           max(size(e.text)) as max_entry_length
                """)
                
                length_stats = result.single()
                
                print(f"\nAdditional Statistics:")
                print(f"Multi-variant entries: {multi_variant_entries} entries")
                print(f"Maximum lemmas per entry: {max_lemmas}")
                print(f"Lemma text length: {length_stats['min_lemma_length']}-{length_stats['max_lemma_length']} characters")
                print(f"Entry text length: {length_stats['min_entry_length']}-{length_stats['max_entry_length']} characters")
                
                # Show examples of multi-variant entries
                if multi_variant_entries > 0:
                    print(f"\nExamples of multi-variant entries:")
                    result = session.run("""
                        MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)
                        WHERE e.original_key CONTAINS '|'
                        WITH e.original_key as original_key, collect(l.text) as lemmas
                        RETURN original_key, lemmas
                        LIMIT 3
                    """)
                    
                    for record in result:
                        lemmas = ", ".join(record['lemmas'])
                        print(f"  '{record['original_key']}' → [{lemmas}]")
                
                return True
                
        except Exception as e:
            print(f"✗ Error generating statistics: {e}")
            return False
                
        except Exception as e:
            print(f"✗ Error generating statistics: {e}")
            return False
    
    def run_comprehensive_verification(self, dictionaries_dir: str = "dictionaries") -> bool:
        """Run all verification checks."""
        print("Greek Dictionary Import Verification")
        print("=" * 40)
        
        checks = [
            ("Database Structure", lambda: self.check_database_structure()),
            ("Dictionary Integrity", lambda: self.check_dictionary_integrity()),
            ("Source File Comparison", lambda: self.check_against_source_files(dictionaries_dir)),
            ("Search Functionality", lambda: self.test_search_functionality()),
            ("Detailed Statistics", lambda: self.get_detailed_statistics())
        ]
        
        passed_checks = 0
        
        for check_name, check_func in checks:
            try:
                if check_func():
                    passed_checks += 1
                else:
                    print(f"\n✗ {check_name} check failed")
            except Exception as e:
                print(f"\n✗ {check_name} check failed with error: {e}")
        
        print(f"\n" + "=" * 40)
        print(f"Verification Results: {passed_checks}/{len(checks)} checks passed")
        
        if passed_checks == len(checks):
            print("✓ All verifications passed! Data import was successful.")
            return True
        else:
            print("✗ Some verifications failed. Please check the import process.")
            return False


def main():
    """Main function to run verification."""
    # Configuration
    dictionaries_dir = "dictionaries"
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"  # Change this to your Neo4j password
    neo4j_database = "dictionarygreekdutch"  # Change this to your Neo4j database name
    
    # Initialize verifier
    verifier = DictionaryVerifier(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
    
    try:
        # Connect to Neo4j
        if not verifier.connect():
            return False
        
        # Run verification
        success = verifier.run_comprehensive_verification(dictionaries_dir)
        return success
        
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during verification: {e}")
        return False
    finally:
        verifier.close()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
