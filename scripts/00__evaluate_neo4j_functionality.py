#!/usr/bin/env python3
"""
Neo4j MCP Connection Test Script
Mimics the MCP Neo4j functionality for troubleshooting

Wim Otte (w.m.otte@umcutrecht.nl)
"""

from neo4j import GraphDatabase
import json
from typing import Dict, List, Any, Optional
import sys


class Neo4jMCPTester:
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """Initialize Neo4j connection with same parameters as MCP config"""
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                print(f"✅ Connected to Neo4j successfully (test value: {test_value})")
                return True
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            print("🔒 Neo4j connection closed")
    
    def get_neo4j_schema(self) -> Dict:
        """
        Get database schema - mimics dictionaries-get_neo4j_schema
        Requires APOC plugin to be installed
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Get schema using APOC
                result = session.run("CALL apoc.meta.schema() YIELD value RETURN value")
                schema_data = result.single()["value"]
                
                print("✅ Schema retrieved successfully")
                return schema_data
                
        except Exception as e:
            print(f"❌ Failed to get schema: {e}")
            # Fallback: try manual schema detection
            return self._get_manual_schema()
    
    def _get_manual_schema(self) -> Dict:
        """Manual schema detection without APOC"""
        try:
            with self.driver.session(database=self.database) as session:
                # Get node labels and counts
                labels_result = session.run("""
                    CALL db.labels() YIELD label
                    CALL apoc.cypher.run('MATCH (n:' + label + ') RETURN count(n) as count', {}) 
                    YIELD value
                    RETURN label, value.count as count
                """)
                
                schema = {}
                for record in labels_result:
                    label = record["label"]
                    count = record["count"]
                    schema[label] = {
                        "type": "node",
                        "count": count,
                        "properties": {},
                        "relationships": {}
                    }
                
                print("✅ Manual schema detection completed")
                return schema
                
        except Exception as e:
            print(f"❌ Manual schema detection failed: {e}")
            return {}
    
    def read_neo4j_cypher(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute read Cypher query - mimics dictionaries-read_neo4j_cypher
        """
        if params is None:
            params = {}
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params)
                records = []
                
                for record in result:
                    # Convert record to dictionary
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        # Handle Neo4j node/relationship objects
                        if hasattr(value, '_properties'):
                            record_dict[key] = dict(value._properties)
                            if hasattr(value, '_labels'):
                                record_dict[key]['_labels'] = list(value._labels)
                        else:
                            record_dict[key] = value
                    records.append(record_dict)
                
                print(f"✅ Query executed successfully, returned {len(records)} records")
                return records
                
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            return []
    
    def write_neo4j_cypher(self, query: str, params: Optional[Dict] = None) -> Dict:
        """
        Execute write Cypher query - mimics dictionaries-write_neo4j_cypher
        """
        if params is None:
            params = {}
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params)
                summary = result.consume()
                
                write_info = {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added,
                    "labels_removed": summary.counters.labels_removed,
                    "indexes_added": summary.counters.indexes_added,
                    "indexes_removed": summary.counters.indexes_removed,
                    "constraints_added": summary.counters.constraints_added,
                    "constraints_removed": summary.counters.constraints_removed
                }
                
                print(f"✅ Write query executed successfully")
                print(f"   Changes: {write_info}")
                return write_info
                
        except Exception as e:
            print(f"❌ Write query execution failed: {e}")
            return {}


def main():
    """Main function to test Neo4j connectivity"""
    
    # Your MCP configuration parameters
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "password"
    NEO4J_DATABASE = "dictionaries"
    
    print("🚀 Starting Neo4j MCP Connection Test")
    print(f"   URI: {NEO4J_URI}")
    print(f"   Database: {NEO4J_DATABASE}")
    print(f"   Username: {NEO4J_USERNAME}")
    print("-" * 50)
    
    # Initialize tester
    tester = Neo4jMCPTester(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE)
    
    try:
        # Test connection
        if not tester.connect():
            print("Cannot proceed without valid connection")
            return
        
        print("\n📊 Testing Schema Retrieval...")
        schema = tester.get_neo4j_schema()
        if schema:
            print(f"   Found {len(schema)} node types")
            for node_type, info in schema.items():
                if isinstance(info, dict) and 'count' in info:
                    print(f"   - {node_type}: {info['count']} nodes")
        
        print("\n🔍 Testing Basic Queries...")
        
        # Test 1: Simple return
        print("   Test 1: Simple return query")
        result = tester.read_neo4j_cypher("RETURN 1 as test, 'hello' as message")
        if result:
            print(f"   Result: {result[0]}")
        
        # Test 2: Count all nodes
        print("   Test 2: Count all nodes")
        result = tester.read_neo4j_cypher("MATCH (n) RETURN count(n) as total_nodes")
        if result:
            print(f"   Total nodes: {result[0]['total_nodes']}")
        
        # Test 3: Get dictionaries (if they exist)
        print("   Test 3: Get dictionaries")
        result = tester.read_neo4j_cypher("MATCH (d:Dictionary) RETURN d.name as name, d.entry_count as entries LIMIT 5")
        if result:
            print(f"   Found {len(result)} dictionaries:")
            for dict_info in result:
                print(f"   - {dict_info}")
        else:
            print("   No Dictionary nodes found or query failed")
        
        # Test 4: Get sample lemmas
        print("   Test 4: Get sample lemmas")
        result = tester.read_neo4j_cypher("MATCH (l:Lemma) RETURN l.text as text LIMIT 3")
        if result:
            print(f"   Sample lemmas: {[r['text'] for r in result]}")
        
        print("\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        tester.close()


if __name__ == "__main__":
    # Check if neo4j package is installed
    try:
        import neo4j
        print(f"Using neo4j driver version: {neo4j.__version__}")
    except ImportError:
        print("❌ neo4j package not found. Install with: pip install neo4j")
        sys.exit(1)
    
    main()
