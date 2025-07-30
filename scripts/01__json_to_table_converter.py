#!/usr/bin/env python3
"""
Greek Morphosyntactic Analysis JSON to Table Converter
Converts structured JSON files with Greek morphosyntactic analysis to CSV and HTML formats.

Wim Otte (w.m.otte@umcutrecht.nl)
"""

import json
import csv
import html
import argparse
from pathlib import Path
from typing import Dict, List, Any


class GreekMorphoConverter:
    """Converter for Greek morphosyntactic analysis JSON files."""
    
    def __init__(self):
        self.csv_columns = [
            'sentence_id', 'token_position', 'token', 'transliteration', 'lemma', 
            'part_of_speech', 
            'gender', 'case', 
            'person', 'number', 
            'voice', 'mood', 'tense', 
            'gloss'
        ]
        
        self.html_columns = [
            ('Pos.', 'token_position'),
            ('Form', 'token'),
            ('Translit.', 'transliteration'),
            ('Lemma', 'lemma'),
            ('POS', 'part_of_speech'),
            
            ('Gender', 'gender'),
            ('Case', 'case'),
            ('Number', 'number'),

            ('Voice', 'voice'),
            ('Mood', 'mood'),
            ('Tense', 'tense'),
            ('Person', 'person'),

            ('Gloss', 'gloss')
        ]
    
    def load_json(self, filepath: str) -> Dict[str, Any]:
        """Load and parse JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_token_data(self, sentence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract token data from a sentence."""
        tokens = []
        sentence_id = sentence['sentence_id']
        
        for i, token_data in enumerate(sentence['analysis'], 1):
            parsing = token_data.get('parsing_details', {})
            
            token_row = {
                'sentence_id': sentence_id,
                'token_position': i,
                'token': token_data.get('token', ''),
                'transliteration': token_data.get('transliteration', ''),
                'lemma': token_data.get('lemma', ''),
                'part_of_speech': token_data.get('part_of_speech', ''),
                
                'gender': parsing.get('gender', '') if parsing.get('gender') is not None else '',
                'case': parsing.get('case', '') if parsing.get('case') is not None else '',

                'person': parsing.get('person', '') if parsing.get('person') is not None else '',
                'number': parsing.get('number', '') if parsing.get('number') is not None else '',

  
                'voice': parsing.get('voice', '') if parsing.get('voice') is not None else '',
                'mood': parsing.get('mood', '') if parsing.get('mood') is not None else '',
                'tense': parsing.get('tense', '') if parsing.get('tense') is not None else '',

                'gloss': token_data.get('gloss', '')

            }
            tokens.append(token_row)
        
        return tokens
    
    def to_csv(self, data: Dict[str, Any], output_path: str = None) -> str:
        """Convert JSON data to CSV format."""
        lines = []
        
        # Add metadata section
        lines.append('# Sentence Metadata')
        lines.append('# sentence_id,sentence_text,translation_en,translation_nl,translation_fr')
        
        for sentence in data['sentences']:
            metadata_row = [
                sentence['sentence_id'],
                f'"{sentence["sentence_text"]}"',
                f'"{sentence["translation_en"]}"',
                f'"{sentence["translation_nl"]}"',
                f'"{sentence["translation_fr"]}"'
            ]
            lines.append('# ' + ','.join(metadata_row))
        
        lines.append('')
        lines.append('# Morphosyntactic Analysis')
        
        # Add header
        lines.append(','.join(self.csv_columns))
        
        # Add data rows
        for sentence in data['sentences']:
            tokens = self.extract_token_data(sentence)
            for token in tokens:
                row_values = []
                for col in self.csv_columns:
                    value = str(token[col])
                    # Escape CSV values that need it
                    if ',' in value or '"' in value or '\n' in value:
                        value = '"' + value.replace('"', '""') + '"'
                    row_values.append(value)
                lines.append(','.join(row_values))
        
        csv_content = '\n'.join(lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
        
        return csv_content
    
    def to_html(self, data: Dict[str, Any], output_path: str = None, table_number: int = 1) -> str:
        """Convert JSON data to professional HTML table format."""
        
        # Generate table caption
        if len(data['sentences']) == 1:
            sentence_text = data['sentences'][0]['sentence_text']
            caption = f'Table {table_number}. Morphosyntactic analysis of "{sentence_text}"'
        else:
            caption = f'Table {table_number}. Morphosyntactic analysis of {len(data["sentences"])} sentences'
        
        html_parts = [
            '<table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 10pt;">',
            f'  <caption style="font-weight: bold; margin-bottom: 8px; text-align: left;">',
            f'    {html.escape(caption)}',
            f'  </caption>',
            '  <thead>',
            '    <tr style="background-color: #f8f9fa; border-bottom: 2px solid #333;">'
        ]
        
        # Add headers
        for header_text, _ in self.html_columns:
            html_parts.append(f'      <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">{header_text}</th>')
        
        html_parts.append('    </tr>')
        html_parts.append('  </thead>')
        html_parts.append('  <tbody>')
        
        # Add data rows
        row_count = 0
        for sentence in data['sentences']:
            tokens = self.extract_token_data(sentence)
            
            for token in tokens:
                bg_color = '#ffffff' if row_count % 2 == 0 else '#f8f9fa'
                html_parts.append(f'    <tr style="background-color: {bg_color};">')
                
                for _, field_name in self.html_columns:
                    value = str(token[field_name]) if token[field_name] else ''
                    
                    # Special formatting for specific columns
                    if field_name in ['token', 'lemma']:
                        style = 'border: 1px solid #ddd; padding: 6px; font-family: \'Times New Roman\', serif;'
                    elif field_name in ['transliteration', 'gloss']:
                        style = 'border: 1px solid #ddd; padding: 6px; font-style: italic;'
                    else:
                        style = 'border: 1px solid #ddd; padding: 6px;'
                    
                    html_parts.append(f'      <td style="{style}">{html.escape(value)}</td>')
                
                html_parts.append('    </tr>')
                row_count += 1
        
        html_parts.extend([
            '  </tbody>',
            '</table>'
        ])
        
        html_content = '\n'.join(html_parts)
        
        if output_path:
            # Create complete HTML document
            complete_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Greek Morphosyntactic Analysis</title>
</head>
<body style="margin: 20px; font-family: Arial, sans-serif;">

{html_content}

<p style="margin-top: 20px; font-size: 12pt; color: #666;">
</p>

</body>
</html>"""
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(complete_html)
        
        return html_content
    
    def convert_file(self, input_path: str, output_dir: str = None, table_number: int = 1):
        """Convert a single JSON file to both CSV and HTML formats."""
        input_file = Path(input_path)
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
        else:
            output_path = input_file.parent
        
        # Load data
        data = self.load_json(input_path)
        
        # Generate output filenames
        base_name = input_file.stem
        csv_output = output_path / f"{base_name}_analysis.csv"
        html_output = output_path / f"{base_name}_table.html"
        
        # Convert to CSV
        self.to_csv(data, str(csv_output))
        print(f"CSV saved to: {csv_output}")
        
        # Convert to HTML
        self.to_html(data, str(html_output), table_number)
        print(f"HTML saved to: {html_output}")
        
        return str(csv_output), str(html_output)


def main():
    """Command line interface for the converter."""
    parser = argparse.ArgumentParser(
        description='Convert Greek morphosyntactic JSON files to CSV and HTML tables'
    )
    parser.add_argument('input_files', nargs='+', help='Input JSON file(s)')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: same as input file)')
    parser.add_argument('--start-table-number', type=int, default=1, 
                      help='Starting table number for HTML captions (default: 1)')
    
    args = parser.parse_args()
    
    converter = GreekMorphoConverter()
    
    for i, input_file in enumerate(args.input_files):
        print(f"\nProcessing: {input_file}")
        table_number = args.start_table_number + i
        
        try:
            converter.convert_file(input_file, args.output_dir, table_number)
        except Exception as e:
            print(f"Error processing {input_file}: {e}")


if __name__ == "__main__":
    main()


# Example usage as a module:
if __name__ == "__example__":
    # Create converter instance
    converter = GreekMorphoConverter()
    
    # Convert a single file
    csv_path, html_path = converter.convert_file("example4.json")
    
    # Or get the content as strings
    data = converter.load_json("example4.json")
    csv_content = converter.to_csv(data)
    html_content = converter.to_html(data)
    
    print("CSV content:")
    print(csv_content[:500] + "...")
    print("\nHTML content:")
    print(html_content[:500] + "...")
