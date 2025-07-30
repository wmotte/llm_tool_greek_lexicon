#!/usr/bin/env python3
"""
SvBKR Greek-Dutch Dictionary Paraphraser (with Resume Capability)

Wim Otte (w.m.otte@umcutrecht.nl)

This script reads a JSON file containing Greek-Dutch dictionary entries,
paraphrases the explanations using the Google Gemini API, and saves the
results to a new JSON file.

*** NEW: This script is now robust against interruptions. ***
If the script stops, you can simply run it again. It will load the
work that was already completed from the output file and resume
where it left off, saving you time and API calls.

Instructions:
1. Make sure you have the required libraries:
   pip install google-generativeai python-dotenv tqdm
2. Create a .env file in the same directory as this script.
3. Add your Google Gemini API key to the .env file:
   GEMINI_API_KEY="YOUR_API_KEY_HERE"
4. Place your large input JSON dictionary file (e.g., 'svbkr_dictionary.json') 
   in the same directory and update the `input_filename` in the `main`
   function below.
5. Run the script: python your_script_name.py
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv
from tqdm import tqdm

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paraphrasing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Main Paraphrasing Class ---

class DictionaryParaphraser:
    """
    Handles loading, paraphrasing, and saving dictionary entries with resume support.
    """
    def __init__(self, api_key: str, model_name: str = 'gemini-2.5-flash-lite'):
        """
        Initializes the paraphraser and the Gemini model.

        Args:
            api_key: The Google Gemini API key.
            model_name: The specific Gemini model to use for generation.
        """
        if not api_key:
            raise ValueError("Gemini API key not found. Please set it in your .env file.")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"Successfully initialized Gemini model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def _create_paraphrasing_prompt(self, lemma: str, entry_text: str) -> str:
        """
        Creates a detailed prompt for the Gemini API based on user instructions.

        Args:
            lemma: The headword of the dictionary entry.
            entry_text: The full original text of the dictionary entry.

        Returns:
            A string containing the formatted prompt.
        """
        return f"""
Je bent een expert in de Griekse filologie en lexicografie, met de taak om een complex wetenschappelijk woordenboekartikel (Grieks-Nederlands) te parafraseren voor een breder publiek.

**Instructies voor Parafraseren:**

1.  **Behoud Alle Betekenissen**: Zorg ervoor dat alle genummerde definities en semantische nuanceringen uit het origineel worden meegenomen.
2.  **Vereenvoudig Etymologie**: Presenteer etymologische informatie (tussen vierkante haken `[]`) in heldere, toegankelijke taal. Zeg bijvoorbeeld "afgeleid van" in plaats van alleen het woord te tonen.
3.  **Verwijder Technische Codes**: Elimineer alle citaten en verwijzingen (zoals "Il. 19.424", "Lys. 16.15") en andere technische notaties.
4.  **Behoud Voorbeelden**: Houd relevante Griekse voorbeelden, maar presenteer ze duidelijk zonder overweldigende details. Een vertaling of korte duiding van het voorbeeld is waardevol.
5.  **Gebruik Helder Nederlands**: Schrijf in modern, vlot en toegankelijk Nederlands, maar behoud de wetenschappelijke correctheid.
6.  **Logische Structuur**: Organiseer de betekenissen logisch, meestal van de meest voorkomende naar meer gespecialiseerde gebruiken.
7.  **Behoud Gebruiksinfo**: Cruciale informatie over register (episch, poëtisch), periode of context moet behouden blijven.
8.  **Lengte**: De parafrase moet gemiddeld tussen de 10 en 50 woorden lang zijn, afhankelijk van de complexiteit van de input.
9.  **Output**: Geef ALLEEN de geparafraseerde Nederlandse tekst terug, zonder extra opmaak, titels of de originele Griekse tekst.

**Origineel Woordenboekartikel:**

**Lemma:** {lemma}
**Tekst:**
{entry_text}

**Geparafraseerde Nederlandse Uitleg (alleen de tekst):**
"""

    def paraphrase_entry(self, lemma: str, entry_text: str) -> str:
        """
        Paraphrases a single dictionary entry using the Gemini API.

        Args:
            lemma: The headword of the entry.
            entry_text: The original text of the entry.

        Returns:
            The paraphrased text, or the original text if an error occurs.
        """
        if "=== REFERENCE LEMMA ===" in entry_text:
            logger.debug(f"Skipping reference lemma: {lemma}")
            return entry_text

        prompt = self._create_paraphrasing_prompt(lemma, entry_text)
        
        try:
            retries = 3
            for attempt in range(retries):
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.4,
                            max_output_tokens=500 
                        )
                    )
                    paraphrased_text = response.text.strip()
                    logger.debug(f"Successfully paraphrased lemma: {lemma}")
                    return paraphrased_text
                except Exception as e:
                    logger.warning(f"API call attempt {attempt + 1} for '{lemma}' failed: {e}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        logger.error(f"Final attempt failed for lemma: {lemma}. Returning original text.")
                        return entry_text

        except Exception as e:
            logger.error(f"An unexpected error occurred while paraphrasing '{lemma}': {e}")
            return entry_text

    def process_dictionary_file(self, input_path: Path, output_path: Path):
        """
        Reads an input JSON dictionary, paraphrases all entries, and saves to a new file.
        This method is resumable and saves progress periodically.
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                original_dict = json.load(f)
            logger.info(f"Successfully loaded {len(original_dict)} total entries from {input_path}.")
        except FileNotFoundError:
            logger.error(f"Input file not found: {input_path}")
            return
        except json.JSONDecodeError:
            logger.error(f"Could not decode JSON from file: {input_path}")
            return

        paraphrased_dict: Dict[str, str] = {}
        if output_path.exists():
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    paraphrased_dict = json.load(f)
                logger.info(f"Resuming from existing output file. {len(paraphrased_dict)} entries already paraphrased.")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load existing output file at {output_path}, starting from scratch. Error: {e}")
                paraphrased_dict = {}

        save_interval = 250
        entries_processed_since_last_save = 0
        
        items_to_process = list(original_dict.items())

        with tqdm(total=len(original_dict), desc="Paraphrasing entries") as pbar:
            pbar.update(len(paraphrased_dict)) # Update progress bar with already completed items
            for lemma, entry_text in items_to_process:
                if lemma in paraphrased_dict:
                    continue

                paraphrased_text = self.paraphrase_entry(lemma, entry_text)
                paraphrased_dict[lemma] = paraphrased_text
                entries_processed_since_last_save += 1
                pbar.update(1)

                if entries_processed_since_last_save >= save_interval:
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(paraphrased_dict, f, ensure_ascii=False, indent=2)
                        entries_processed_since_last_save = 0
                        logger.info(f"Saved intermediate progress. {len(paraphrased_dict)} entries complete.")
                    except Exception as e:
                        logger.error(f"Failed to save intermediate progress to {output_path}: {e}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(paraphrased_dict, f, ensure_ascii=False, indent=2)
            logger.info(f"Final save complete. Total entries in output: {len(paraphrased_dict)}")
        except Exception as e:
            logger.error(f"Failed to save final output file: {e}")


def main():
    """
    Main function to execute the script.
    """
    logger.info("Starting the dictionary paraphrasing process...")
    
    # --- User Configuration ---
    # IMPORTANT: Update this to your actual dictionary file name
    input_filename = "svbkr_dictionary.json" 
    output_filename = "paraphrased_dictionary_output.json"
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    script_dir = Path(__file__).parent
    input_path = script_dir / input_filename
    output_path = script_dir / output_filename
    
    try:
        paraphraser = DictionaryParaphraser(api_key=gemini_api_key)
        paraphraser.process_dictionary_file(input_path, output_path)
    except ValueError as e:
        logger.error(e)
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main process: {e}")

    logger.info("Paraphrasing process finished.")


if __name__ == "__main__":
    main()
