#!/usr/bin/env python3
"""
Script to import Greek dictionary JSON files into Neo4j knowledge graph.
Reads JSON files from 'dictionaries' directory and imports them into Neo4j database.

Wim Otte (w.m.otte@umcutrecht.nl)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import time

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError


class DictionaryImporter:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password", database: str = "dictionarygreekdutch"):
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        self.lemma_counter = 0
        
    def connect(self) -> bool:
        """Establish connection to Neo4j database with health checks."""
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
    
    def clear_database(self) -> bool:
        """Clear existing dictionary data from the database."""
        try:
            with self.driver.session(database=self.database) as session:
                print("Clearing existing dictionary data...")
                
                # Delete all nodes and relationships
                session.run("MATCH (n) DETACH DELETE n")
                
                print("✓ Database cleared")
                return True
                
        except Exception as e:
            print(f"✗ Error clearing database: {e}")
            return False
    
    def create_constraints(self) -> bool:
        """Create database constraints and indexes for better performance."""
        try:
            with self.driver.session(database=self.database) as session:
                print("Creating database constraints and indexes...")
                
                # Create constraint for unique lemma IDs
                session.run("""
                    CREATE CONSTRAINT lemma_id_unique IF NOT EXISTS
                    FOR (l:Lemma) REQUIRE l.id IS UNIQUE
                """)
                
                # Create constraint for unique entry IDs
                session.run("""
                    CREATE CONSTRAINT entry_id_unique IF NOT EXISTS
                    FOR (e:Entry) REQUIRE e.id IS UNIQUE
                """)
                
                # Create constraint for unique dictionary names
                session.run("""
                    CREATE CONSTRAINT dict_name_unique IF NOT EXISTS
                    FOR (d:Dictionary) REQUIRE d.name IS UNIQUE
                """)
                
                # Create index for lemma text for faster searches
                session.run("""
                    CREATE INDEX lemma_text_index IF NOT EXISTS
                    FOR (l:Lemma) ON (l.text)
                """)
                
                # Create index for entry original_key for faster searches
                session.run("""
                    CREATE INDEX entry_original_key_index IF NOT EXISTS
                    FOR (e:Entry) ON (e.original_key)
                """)
                
                print("✓ Constraints and indexes created")
                return True
                
        except Exception as e:
            print(f"✗ Error creating constraints: {e}")
            return False
    
    def load_json_files(self, directory_path: str) -> Dict[str, Dict]:
        """Load and validate all JSON files from the dictionaries directory."""
        dictionaries = {}
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"✗ Directory '{directory_path}' does not exist")
            return dictionaries
        
        if not directory.is_dir():
            print(f"✗ '{directory_path}' is not a directory")
            return dictionaries
        
        json_files = list(directory.glob("*.json"))
        
        if not json_files:
            print(f"✗ No JSON files found in '{directory_path}'")
            return dictionaries
        
        print(f"Found {len(json_files)} JSON files")
        
        for file_path in json_files:
            try:
                print(f"Loading {file_path.name}...")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, dict):
                    print(f"✗ Warning: {file_path.name} does not contain a dictionary object")
                    continue
                
                # Extract dictionary name from filename (remove .json extension)
                dict_name = file_path.stem
                dictionaries[dict_name] = data
                
                print(f"✓ Loaded {len(data)} entries from {file_path.name}")
                
            except json.JSONDecodeError as e:
                print(f"✗ Error parsing JSON in {file_path.name}: {e}")
                continue
            except Exception as e:
                print(f"✗ Error loading {file_path.name}: {e}")
                continue
        
        print(f"✓ Successfully loaded {len(dictionaries)} dictionaries")
        return dictionaries
    
    def generate_unique_id(self) -> str:
        """Generate a unique ID for lemmas."""
        self.lemma_counter += 1
        return f"lemma_{self.lemma_counter:06d}"
    
    def parse_lemmas(self, key: str) -> List[str]:
        """Parse lemma variants from key string (separated by |)."""
        return [lemma.strip() for lemma in key.split('|') if lemma.strip()]
    
    def import_dictionary(self, dict_name: str, entries: Dict[str, str]) -> bool:
        """Import a single dictionary into Neo4j with improved structure."""
        try:
            with self.driver.session(database=self.database) as session:
                print(f"Importing dictionary: {dict_name}")
                
                # Create dictionary node
                session.run("""
                    MERGE (d:Dictionary {name: $dict_name})
                    SET d.entry_count = $entry_count,
                        d.imported_at = datetime()
                """, dict_name=dict_name, entry_count=len(entries))
                
                # Import entries in batches for better performance
                batch_size = 100
                entries_list = list(entries.items())
                
                for i in range(0, len(entries_list), batch_size):
                    batch = entries_list[i:i + batch_size]
                    
                    for key, value in batch:
                        lemmas = self.parse_lemmas(key)
                        
                        # Create one Entry node for this dictionary entry
                        entry_id = self.generate_unique_id()
                        
                        session.run("""
                            MATCH (d:Dictionary {name: $dict_name})
                            CREATE (e:Entry {
                                id: $entry_id,
                                text: $entry_text,
                                original_key: $original_key
                            })
                            CREATE (e)-[:BELONGS_TO]->(d)
                        """, 
                        dict_name=dict_name,
                        entry_id=entry_id,
                        entry_text=value,
                        original_key=key)
                        
                        # Create Lemma nodes that refer to this Entry
                        for lemma_text in lemmas:
                            lemma_id = self.generate_unique_id()
                            
                            session.run("""
                                MATCH (d:Dictionary {name: $dict_name}),
                                      (e:Entry {id: $entry_id})
                                CREATE (l:Lemma {
                                    id: $lemma_id,
                                    text: $lemma_text
                                })
                                CREATE (l)-[:HAS_ENTRY]->(e)
                                CREATE (l)-[:BELONGS_TO]->(d)
                            """, 
                            dict_name=dict_name,
                            entry_id=entry_id,
                            lemma_id=lemma_id,
                            lemma_text=lemma_text)
                    
                    print(f"  Processed batch {i//batch_size + 1}/{(len(entries_list)-1)//batch_size + 1}")
                
                print(f"✓ Imported {len(entries)} entries from {dict_name}")
                return True
                
        except Exception as e:
            print(f"✗ Error importing dictionary {dict_name}: {e}")
            return False
    
    def import_all_dictionaries(self, dictionaries: Dict[str, Dict]) -> bool:
        """Import all dictionaries into Neo4j."""
        success_count = 0
        
        for dict_name, entries in dictionaries.items():
            if self.import_dictionary(dict_name, entries):
                success_count += 1
        
        print(f"\n✓ Successfully imported {success_count}/{len(dictionaries)} dictionaries")
        return success_count == len(dictionaries)
    
    def get_import_stats(self) -> Dict:
        """Get statistics about the imported data."""
        try:
            with self.driver.session(database=self.database) as session:
                # Count dictionaries
                result = session.run("MATCH (d:Dictionary) RETURN count(d) as dict_count")
                dict_count = result.single()["dict_count"]
                
                # Count total lemmas
                result = session.run("MATCH (l:Lemma) RETURN count(l) as lemma_count")
                lemma_count = result.single()["lemma_count"]
                
                # Count total entries
                result = session.run("MATCH (e:Entry) RETURN count(e) as entry_count")
                entry_count = result.single()["entry_count"]
                
                # Get dictionary details
                result = session.run("""
                    MATCH (d:Dictionary)<-[:BELONGS_TO]-(l:Lemma)
                    WITH d.name as name, count(l) as lemma_count
                    MATCH (d:Dictionary {name: name})<-[:BELONGS_TO]-(e:Entry)
                    RETURN name, lemma_count, count(e) as entry_count
                    ORDER BY name
                """)
                
                dict_details = []
                for record in result:
                    dict_details.append({
                        'name': record['name'],
                        'lemma_count': record['lemma_count'],
                        'entry_count': record['entry_count']
                    })
                
                return {
                    'total_dictionaries': dict_count,
                    'total_lemmas': lemma_count,
                    'total_entries': entry_count,
                    'dictionary_details': dict_details
                }
                
        except Exception as e:
            print(f"✗ Error getting import stats: {e}")
            return {}


def main():
    """Main function to run the import process."""
    print("Greek Dictionary Importer for Neo4j")
    print("=" * 40)
    
    # Configuration
    dictionaries_dir = "dictionaries"
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"  # Change this to your Neo4j password
    neo4j_database = "dictionarygreekdutch"  # Change this to your Neo4j database name
    
    # Initialize importer
    importer = DictionaryImporter(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
    
    try:
        # Connect to Neo4j
        if not importer.connect():
            sys.exit(1)
        
        # Create constraints and indexes
        if not importer.create_constraints():
            sys.exit(1)
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        clear_data = input("Clear existing data? (y/N): ").lower().strip()
        if clear_data == 'y':
            if not importer.clear_database():
                sys.exit(1)
        
        # Load JSON files
        dictionaries = importer.load_json_files(dictionaries_dir)
        if not dictionaries:
            print("✗ No dictionaries loaded. Exiting.")
            sys.exit(1)
        
        # Import dictionaries
        start_time = time.time()
        success = importer.import_all_dictionaries(dictionaries)
        end_time = time.time()
        
        if success:
            print(f"\n✓ Import completed successfully in {end_time - start_time:.2f} seconds")
            
            # Show statistics
            stats = importer.get_import_stats()
            if stats:
                print(f"\nImport Statistics:")
                print(f"Total dictionaries: {stats['total_dictionaries']}")
                print(f"Total entries: {stats['total_entries']}")
                print(f"Total lemmas: {stats['total_lemmas']}")
                print(f"\nDictionary breakdown:")
                for detail in stats['dictionary_details']:
                    print(f"  {detail['name']}: {detail['entry_count']} entries → {detail['lemma_count']} lemmas")
        else:
            print("✗ Import failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
    finally:
        importer.close()


if __name__ == "__main__":
    main()
