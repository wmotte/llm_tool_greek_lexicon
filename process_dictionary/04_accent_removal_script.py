#!/usr/bin/env python3
"""
Postprocessing script to add accent-free versions of Greek lemmas to Neo4j database.
This script reads existing lemmas and creates accent-free versions for easier searching.

Wim Otte (w.m.otte@umcutrecht.nl)
"""

import unicodedata
import re
import sys
import time
from typing import Dict, List, Tuple, Optional

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError


class GreekAccentRemover:
    """Class to handle removal of Greek accents and diacritics."""
    
    # Greek diacritical marks to remove
    GREEK_DIACRITICS = {
        # Breathing marks
        'ἀ': 'α', 'ἁ': 'α', 'Ἀ': 'Α', 'Ἁ': 'Α',
        'ἐ': 'ε', 'ἑ': 'ε', 'Ἐ': 'Ε', 'Ἑ': 'Ε',
        'ἠ': 'η', 'ἡ': 'η', 'Ἠ': 'Η', 'Ἡ': 'Η',
        'ἰ': 'ι', 'ἱ': 'ι', 'Ἰ': 'Ι', 'Ἱ': 'Ι',
        'ὀ': 'ο', 'ὁ': 'ο', 'Ὀ': 'Ο', 'Ὁ': 'Ο',
        'ὐ': 'υ', 'ὑ': 'υ', 'Ὑ': 'Υ',
        'ὠ': 'ω', 'ὡ': 'ω', 'Ὠ': 'Ω', 'Ὡ': 'Ω',
        
        # Acute accents
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'Ά': 'Α', 'Έ': 'Ε', 'Ή': 'Η', 'Ί': 'Ι', 'Ό': 'Ο', 'Ύ': 'Υ', 'Ώ': 'Ω',
        
        # Grave accents
        'ὰ': 'α', 'ὲ': 'ε', 'ὴ': 'η', 'ὶ': 'ι', 'ὸ': 'ο', 'ὺ': 'υ', 'ὼ': 'ω',
        'Ὰ': 'Α', 'Ὲ': 'Ε', 'Ὴ': 'Η', 'Ὶ': 'Ι', 'Ὸ': 'Ο', 'Ὺ': 'Υ', 'Ὼ': 'Ω',
        
        # Circumflex accents
        'ᾶ': 'α', 'ῆ': 'η', 'ῖ': 'ι', 'ῦ': 'υ', 'ῶ': 'ω',
        'Α͂': 'Α', 'Η͂': 'Η', 'Ι͂': 'Ι', 'Υ͂': 'Υ', 'Ω͂': 'Ω',
        
        # Breathing + accent combinations
        'ἄ': 'α', 'ἅ': 'α', 'ἂ': 'α', 'ἃ': 'α', 'ἆ': 'α', 'ἇ': 'α',
        'Ἄ': 'Α', 'Ἅ': 'Α', 'Ἂ': 'Α', 'Ἃ': 'Α', 'Ἆ': 'Α', 'Ἇ': 'Α',
        'ἔ': 'ε', 'ἕ': 'ε', 'ἒ': 'ε', 'ἓ': 'ε',
        'Ἔ': 'Ε', 'Ἕ': 'Ε', 'Ἒ': 'Ε', 'Ἓ': 'Ε',
        'ἤ': 'η', 'ἥ': 'η', 'ἢ': 'η', 'ἣ': 'η', 'ἦ': 'η', 'ἧ': 'η',
        'Ἤ': 'Η', 'Ἥ': 'Η', 'Ἢ': 'Η', 'Ἣ': 'Η', 'Ἦ': 'Η', 'Ἧ': 'Η',
        'ἴ': 'ι', 'ἵ': 'ι', 'ἲ': 'ι', 'ἳ': 'ι', 'ἶ': 'ι', 'ἷ': 'ι',
        'Ἴ': 'Ι', 'Ἵ': 'Ι', 'Ἲ': 'Ι', 'Ἳ': 'Ι', 'Ἶ': 'Ι', 'Ἷ': 'Ι',
        'ὄ': 'ο', 'ὅ': 'ο', 'ὂ': 'ο', 'ὃ': 'ο',
        'Ὄ': 'Ο', 'Ὅ': 'Ο', 'Ὂ': 'Ο', 'Ὃ': 'Ο',
        'ὔ': 'υ', 'ὕ': 'υ', 'ὒ': 'υ', 'ὓ': 'υ', 'ὖ': 'υ', 'ὗ': 'υ',
        'Ὕ': 'Υ', 'Ὓ': 'Υ', 'Ὗ': 'Υ',
        'ὤ': 'ω', 'ὥ': 'ω', 'ὢ': 'ω', 'ὣ': 'ω', 'ὦ': 'ω', 'ὧ': 'ω',
        'Ὤ': 'Ω', 'Ὥ': 'Ω', 'Ὢ': 'Ω', 'Ὣ': 'Ω', 'Ὦ': 'Ω', 'Ὧ': 'Ω',
        
        # Iota subscript combinations
        'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω',
        'ΑΙ': 'Α', 'ῌ': 'Η', 'ΩΙ': 'Ω',
        'ᾴ': 'α', 'ᾲ': 'α', 'ᾷ': 'α',
        'ᾔ': 'η', 'ᾒ': 'η', 'ᾗ': 'η', 'ᾕ': 'η', 'ᾓ': 'η', 'ᾖ': 'η',
        'ᾤ': 'ω', 'ᾢ': 'ω', 'ᾧ': 'ω', 'ᾥ': 'ω', 'ᾣ': 'ω', 'ᾦ': 'ω',
        'ᾄ': 'α', 'ᾂ': 'α', 'ᾇ': 'α', 'ᾅ': 'α', 'ᾃ': 'α', 'ᾆ': 'α',
        
        # Diaeresis
        'ϊ': 'ι', 'ϋ': 'υ', 'Ϊ': 'Ι', 'Ϋ': 'Υ',
        'ΐ': 'ι', 'ΰ': 'υ',
    }
    
    @classmethod
    def remove_accents(cls, text: str) -> str:
        """
        Remove Greek accents and diacritics from text.
        
        Args:
            text: Greek text with accents
            
        Returns:
            Text with accents removed
        """
        if not text:
            return text
        
        # Method 1: Direct character mapping for Greek-specific diacritics
        result = text
        for accented, plain in cls.GREEK_DIACRITICS.items():
            result = result.replace(accented, plain)
        
        # Method 2: Unicode normalization for any remaining combining characters
        # Normalize to NFD (decomposed form) and remove combining characters
        normalized = unicodedata.normalize('NFD', result)
        without_combining = ''.join(
            char for char in normalized 
            if not unicodedata.combining(char)
        )
        
        return without_combining
    
    @classmethod
    def test_accent_removal(cls):
        """Test the accent removal with some examples."""
        test_cases = [
            'ἀββα',
            'Ἀβραάμ',
            'ἄβυσσος',
            'ἀγαθοποιέω',
            'Ἀβιαθάρ',
            'ἀβροχία',
            'ἅβρα',
        ]
        
        print("Testing accent removal:")
        for original in test_cases:
            cleaned = cls.remove_accents(original)
            print(f"  {original} → {cleaned}")


class DictionaryPostprocessor:
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
    
    def get_lemma_count(self) -> int:
        """Get total count of lemmas in the database."""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("MATCH (l:Lemma) RETURN count(l) as count")
                return result.single()["count"]
        except Exception as e:
            print(f"✗ Error getting lemma count: {e}")
            return 0
    
    def create_accent_free_index(self) -> bool:
        """Create index for accent-free lemma text."""
        try:
            with self.driver.session(database=self.database) as session:
                print("Creating index for accent-free lemma text...")
                
                session.run("""
                    CREATE INDEX lemma_text_no_accents_index IF NOT EXISTS
                    FOR (l:Lemma) ON (l.text_no_accents)
                """)
                
                print("✓ Index created for accent-free text")
                return True
                
        except Exception as e:
            print(f"✗ Error creating index: {e}")
            return False
    
    def process_lemmas_batch(self, batch_size: int = 1000) -> bool:
        """Process all lemmas to add accent-free versions."""
        try:
            total_lemmas = self.get_lemma_count()
            if total_lemmas == 0:
                print("✗ No lemmas found in database")
                return False
            
            print(f"Processing {total_lemmas} lemmas...")
            processed = 0
            
            with self.driver.session(database=self.database) as session:
                # Process in batches to avoid memory issues
                skip = 0
                
                while skip < total_lemmas:
                    # Get batch of lemmas
                    result = session.run("""
                        MATCH (l:Lemma)
                        RETURN l.id as id, l.text as text
                        SKIP $skip LIMIT $limit
                    """, skip=skip, limit=batch_size)
                    
                    batch_data = []
                    for record in result:
                        lemma_id = record["id"]
                        original_text = record["text"]
                        accent_free_text = GreekAccentRemover.remove_accents(original_text)
                        
                        batch_data.append({
                            'id': lemma_id,
                            'original': original_text,
                            'accent_free': accent_free_text
                        })
                    
                    if not batch_data:
                        break
                    
                    # Update lemmas with accent-free versions
                    for item in batch_data:
                        session.run("""
                            MATCH (l:Lemma {id: $id})
                            SET l.text_no_accents = $accent_free
                        """, id=item['id'], accent_free=item['accent_free'])
                    
                    processed += len(batch_data)
                    skip += batch_size
                    
                    print(f"  Processed {processed}/{total_lemmas} lemmas ({processed/total_lemmas*100:.1f}%)")
            
            print(f"✓ Successfully processed {processed} lemmas")
            return True
            
        except Exception as e:
            print(f"✗ Error processing lemmas: {e}")
            return False
    
    def verify_processing(self) -> Dict:
        """Verify the processing results and show statistics."""
        try:
            with self.driver.session(database=self.database) as session:
                # Count lemmas with accent-free versions
                result = session.run("""
                    MATCH (l:Lemma)
                    WHERE l.text_no_accents IS NOT NULL
                    RETURN count(l) as with_accents_removed
                """)
                with_accents_removed = result.single()["with_accents_removed"]
                
                # Count total lemmas
                result = session.run("MATCH (l:Lemma) RETURN count(l) as total")
                total = result.single()["total"]
                
                # Show some examples
                result = session.run("""
                    MATCH (l:Lemma)
                    WHERE l.text <> l.text_no_accents
                    RETURN l.text as original, l.text_no_accents as accent_free
                    LIMIT 10
                """)
                
                examples = []
                for record in result:
                    examples.append({
                        'original': record['original'],
                        'accent_free': record['accent_free']
                    })
                
                # Count how many actually changed
                result = session.run("""
                    MATCH (l:Lemma)
                    WHERE l.text <> l.text_no_accents
                    RETURN count(l) as changed
                """)
                changed = result.single()["changed"]
                
                return {
                    'total_lemmas': total,
                    'processed_lemmas': with_accents_removed,
                    'changed_lemmas': changed,
                    'examples': examples
                }
                
        except Exception as e:
            print(f"✗ Error verifying processing: {e}")
            return {}
    
    def create_search_examples(self) -> None:
        """Show examples of how to search using accent-free text."""
        print("\n" + "="*50)
        print("SEARCH EXAMPLES")
        print("="*50)
        print("Now you can search for Greek lemmas without accents!")
        print()
        print("Examples of Cypher queries:")
        print()
        print("1. Find lemma by accent-free text:")
        print("   MATCH (l:Lemma) WHERE l.text_no_accents = 'αββα' RETURN l")
        print()
        print("2. Case-insensitive search:")
        print("   MATCH (l:Lemma) WHERE toLower(l.text_no_accents) = 'αβρααμ' RETURN l")
        print()
        print("3. Partial matching:")
        print("   MATCH (l:Lemma) WHERE l.text_no_accents CONTAINS 'αβρ' RETURN l")
        print()
        print("4. Get entries for accent-free search:")
        print("   MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)")
        print("   WHERE l.text_no_accents = 'αβυσσος'")
        print("   RETURN l.text as original_lemma, e.text as entry")
        print()


def main():
    """Main function to run the postprocessing."""
    print("Greek Dictionary Accent Removal Postprocessor")
    print("=" * 50)
    
    # Test accent removal first
    GreekAccentRemover.test_accent_removal()
    print()
    
    # Configuration (should match your existing database setup)
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"  # Change this to your Neo4j password
    neo4j_database = "dictionarygreekdutch"
    
    # Initialize postprocessor
    processor = DictionaryPostprocessor(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
    
    try:
        # Connect to Neo4j
        if not processor.connect():
            sys.exit(1)
        
        # Create index for accent-free text
        if not processor.create_accent_free_index():
            print("Warning: Could not create index (may already exist)")
        
        # Ask user for confirmation
        proceed = input(f"\nProceed with adding accent-free versions to all lemmas? (y/N): ").lower().strip()
        if proceed != 'y':
            print("Operation cancelled.")
            sys.exit(0)
        
        # Process lemmas
        start_time = time.time()
        success = processor.process_lemmas_batch()
        end_time = time.time()
        
        if success:
            print(f"\n✓ Processing completed successfully in {end_time - start_time:.2f} seconds")
            
            # Show verification results
            stats = processor.verify_processing()
            if stats:
                print(f"\nProcessing Statistics:")
                print(f"Total lemmas: {stats['total_lemmas']}")
                print(f"Processed lemmas: {stats['processed_lemmas']}")
                print(f"Lemmas with accents removed: {stats['changed_lemmas']}")
                
                if stats['examples']:
                    print(f"\nExamples of accent removal:")
                    for example in stats['examples'][:5]:
                        print(f"  {example['original']} → {example['accent_free']}")
            
            # Show search examples
            processor.create_search_examples()
        else:
            print("✗ Processing failed")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)
    finally:
        processor.close()


if __name__ == "__main__":
    main()
