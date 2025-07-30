#!/usr/bin/env python3
"""
Greek-Dutch Dictionary Scraper (JavaScript-enabled)
Scrapes lemma entries from https://woordenboekgrieks.nl using Selenium for JavaScript rendering

Wim Otte (w.m.otte@umutrecht.nl)

"""

import json
import time
import argparse
from typing import Dict, List, Optional
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GreekDictScraper:
    def __init__(self, delay: float = 1.0, headless: bool = True, timeout: int = 10):
        """
        Initialize the scraper with Selenium WebDriver.
        
        Args:
            delay: Delay between requests in seconds
            headless: Run browser in headless mode
            timeout: Timeout for waiting for elements (seconds)
        """
        self.base_url = "https://woordenboekgrieks.nl/browse"
        self.delay = delay
        self.timeout = timeout
        self.driver = None
        self.wait = None
        
        # Setup Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
    def __enter__(self):
        """Context manager entry."""
        self.start_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_driver()
        
    def start_driver(self):
        """Initialize the WebDriver."""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.wait = WebDriverWait(self.driver, self.timeout)
            logger.info("WebDriver started successfully")
        except Exception as e:
            logger.error(f"Failed to start WebDriver: {e}")
            logger.error("Make sure ChromeDriver is installed and in PATH")
            logger.error("Install with: pip install chromedriver-autoinstaller")
            raise
            
    def close_driver(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
            
    def extract_lemma_data(self, page_source: str) -> Optional[Dict]:
        """
        Extract lemma data from the selected lemma element.
        
        Args:
            page_source: HTML source of the page
            
        Returns:
            Dictionary containing lemma data or None if not found
        """
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find the selected lemma (contains 'x--selected' in class)
        selected_lemma = soup.find('div', class_=lambda x: x and 'x--selected' in x)
        
        if not selected_lemma:
            logger.warning("No selected lemma found on page")
            return None
            
        lemma_data = {"type": "selected"}
        
        # Add raw HTML-to-text conversion
        lemma_data["raw_text"] = self._create_raw_text_summary(selected_lemma)
        
        # Check if this is a full lemma (has 'lem' or 'xlLem' class) or reference (has 'verwLem' class)
        lem_div = selected_lemma.find('div', class_='lem')
        xl_lem_div = selected_lemma.find('div', class_='xlLem')
        verw_lem_div = selected_lemma.find('div', class_='verwLem')
        
        if lem_div:
            # Regular full lemma entry
            lemma_data["entry_type"] = "full"
            lemma_data["lemma_format"] = "regular"
            lemma_data.update(self._extract_full_lemma(lem_div))
            logger.debug(f"Extracted regular full lemma with {len(lemma_data.get('betekenissen', []))} meanings")
        elif xl_lem_div:
            # XL full lemma entry (similar structure but different classes)
            lemma_data["entry_type"] = "full"
            lemma_data["lemma_format"] = "xl"
            lemma_data.update(self._extract_full_lemma(xl_lem_div, is_xl=True))
            logger.debug(f"Extracted XL full lemma with {len(lemma_data.get('betekenissen', []))} meanings")
        elif verw_lem_div:
            # Reference lemma entry
            lemma_data["entry_type"] = "reference"
            lemma_data["lemma_format"] = "reference"
            lemma_data.update(self._extract_reference_lemma(verw_lem_div))
            logger.debug("Extracted reference lemma")
        else:
            logger.warning("Unknown lemma structure")
            return None
            
        return lemma_data
    
    def _extract_full_lemma(self, lem_div, is_xl: bool = False) -> Dict:
        """Extract data from full lemma entry (regular or XL)."""
        data = {}
        
        # Extract vorm (form) section
        vorm_div = lem_div.find('div', class_='vorm')
        if vorm_div:
            # Main word
            hoofd_w = vorm_div.find('div', class_='hoofdW')
            if hoofd_w:
                data['hoofdwoord'] = hoofd_w.get_text(strip=True)
                
            # Etymology
            etym_div = vorm_div.find('div', class_='etym')
            if etym_div:
                data['etymologie'] = self._extract_etymology(etym_div)
                
            # Morphological info
            morf_i = vorm_div.find('div', class_='morfI')
            if morf_i:
                data['morfologie'] = self._extract_morphology(morf_i)
        
        # Extract bet (meaning/definitions) section
        # Handle both regular 'bet' and XL 'xlBet' classes
        if is_xl:
            bet_div = lem_div.find('div', class_='xlBet')
        else:
            bet_div = lem_div.find('div', class_='bet')
        
        if bet_div:
            # Check for ordered list of meanings (complex structure)
            # Handle both regular and XL lemma class patterns
            ol_niv = None
            if is_xl:
                ol_niv = bet_div.find('ol', class_=lambda x: x and 'xlNiv' in ' '.join(x) if isinstance(x, list) else 'xlNiv' in x)
            else:
                ol_niv = bet_div.find('ol', class_=lambda x: x and 'niv' in ' '.join(x) and 'xl' not in ' '.join(x) if isinstance(x, list) else 'niv' in x and 'xl' not in x)
            
            if ol_niv:
                data['betekenissen'] = self._extract_numbered_meanings(ol_niv)
            else:
                # Simple structure (single meaning)
                simple_meaning = {}
                
                # Usage/etymology info
                gebr_w = bet_div.find('div', class_='gebrW')
                if gebr_w:
                    simple_meaning['gebruik_info'] = [self._extract_text_with_abbr(gebr_w)]
                    
                # Translation/meaning - check for multiple vertM elements
                vert_elements = bet_div.find_all('div', class_='vertM')
                if vert_elements:
                    simple_meaning['vertalingen'] = []
                    for vert in vert_elements:
                        simple_meaning['vertalingen'].append(vert.get_text(separator=' ', strip=True))
                
                if simple_meaning:
                    data['betekenissen'] = [simple_meaning]
        
        return data
    
    def _extract_reference_lemma(self, verw_lem_div) -> Dict:
        """Extract data from reference lemma entry."""
        data = {}
        
        # Main word
        hoofd_w = verw_lem_div.find('div', class_='hoofdW')
        if hoofd_w:
            data['hoofdwoord'] = hoofd_w.get_text(strip=True)
            
        # Etymology (if present in reference lemma)
        etym_div = verw_lem_div.find('div', class_='etym')
        if etym_div:
            data['etymologie'] = self._extract_etymology(etym_div)
            
        # Morphological info
        morf_i = verw_lem_div.find('div', class_='morfI')
        if morf_i:
            data['morfologie'] = self._extract_morphology(morf_i)
            
        # Cross reference
        kruis_verw = verw_lem_div.find('div', class_='kruisVerw')
        if kruis_verw:
            data['kruisverwijzing'] = self._extract_cross_reference(kruis_verw)
        
        return data
    
    def _extract_morphology(self, morf_div) -> Dict:
        """Extract morphological information."""
        morph_data = {}
        
        # Extract abbreviations and their meanings
        abbrs = morf_div.find_all('span', class_='abbr')
        if abbrs:
            morph_data['afkortingen'] = []
            for abbr in abbrs:
                abbr_info = {
                    'tekst': abbr.get_text(strip=True),
                    'betekenis': abbr.get('data-abbr', '')
                }
                morph_data['afkortingen'].append(abbr_info)
        
        # Extract any links in morphology
        links = morf_div.find_all('span', class_='link')
        if links:
            morph_data['verwijzingen'] = []
            for link in links:
                link_info = {
                    'tekst': link.get_text(strip=True),
                    'target_id': link.get('data-targetid', '')
                }
                morph_data['verwijzingen'].append(link_info)
        
        # Extract any special elements (like 'r' class)
        special_elements = morf_div.find_all('div', class_='r')
        if special_elements:
            morph_data['speciale_elementen'] = []
            for elem in special_elements:
                morph_data['speciale_elementen'].append(elem.get_text(strip=True))
        
        # Get full text with proper spacing
        morph_data['volledige_tekst'] = morf_div.get_text(separator=' ', strip=True)
        
        return morph_data
    
    def _extract_text_with_abbr(self, div) -> Dict:
        """Extract text that may contain abbreviations and formatting."""
        result = {'volledige_tekst': div.get_text(separator=' ', strip=True)}
        
        # Extract abbreviations and their meanings
        abbrs = div.find_all('span', class_='abbr')
        if abbrs:
            result['afkortingen'] = []
            for abbr in abbrs:
                abbr_info = {
                    'tekst': abbr.get_text(strip=True),
                    'betekenis': abbr.get('data-abbr', '')
                }
                result['afkortingen'].append(abbr_info)
        
        # Extract any links
        links = div.find_all('span', class_='link')
        if links:
            result['verwijzingen'] = []
            for link in links:
                link_info = {
                    'tekst': link.get_text(strip=True),
                    'target_id': link.get('data-targetid', '')
                }
                result['verwijzingen'].append(link_info)
        
        # Extract punctuation elements if present
        punct_elements = div.find_all('span', class_=['punc-stan', 'punc-bekn'])
        if punct_elements:
            result['interpunctie'] = []
            for punct in punct_elements:
                punct_info = {
                    'tekst': punct.get_text(strip=True),
                    'type': punct.get('class', [])[-1] if punct.get('class') else 'onbekend'
                }
                result['interpunctie'].append(punct_info)
        
        return result
    
    def _extract_cross_reference(self, kruis_div) -> Dict:
        """Extract cross-reference information."""
        ref_data = {'volledige_tekst': kruis_div.get_text(separator=' ', strip=True)}
        
        # Find links
        links = kruis_div.find_all('span', class_='link')
        if links:
            ref_data['verwijzingen'] = []
            for link in links:
                link_info = {
                    'tekst': link.get_text(strip=True),
                    'target_id': link.get('data-targetid', '')
                }
                ref_data['verwijzingen'].append(link_info)
        
        return ref_data
    
    def _extract_etymology(self, etym_div) -> Dict:
        """Extract etymology information."""
        etym_data = {
            'volledige_tekst': etym_div.get_text(separator=' ', strip=True)
        }
        
        # Find links in etymology
        links = etym_div.find_all('span', class_='link')
        if links:
            etym_data['verwijzingen'] = []
            for link in links:
                link_info = {
                    'tekst': link.get_text(strip=True),
                    'target_id': link.get('data-targetid', '')
                }
                etym_data['verwijzingen'].append(link_info)
        
        return etym_data
    
    def _extract_numbered_meanings(self, ol_div) -> List[Dict]:
        """Extract numbered meanings from ordered list."""
        meanings = []
        
        for i, li in enumerate(ol_div.find_all('li'), 1):
            meaning = {'nummer': i}
            
            # Extract all usage info blocks (gebrW)
            gebr_blocks = li.find_all('div', class_='gebrW')
            if gebr_blocks:
                meaning['gebruik_info'] = []
                for gebr in gebr_blocks:
                    meaning['gebruik_info'].append(self._extract_text_with_abbr(gebr))
            
            # Extract ALL translations/meanings (vertM) - there can be multiple
            vert_elements = li.find_all('div', class_='vertM')
            if vert_elements:
                meaning['vertalingen'] = []
                for vert in vert_elements:
                    meaning['vertalingen'].append(vert.get_text(separator=' ', strip=True))
            
            # Extract citations
            citations = li.find_all('div', class_='cit')
            if citations:
                meaning['citaten'] = []
                for cit in citations:
                    citation_data = self._extract_citation(cit)
                    if citation_data:
                        meaning['citaten'].append(citation_data)
            
            meanings.append(meaning)
        
        return meanings
    
    def _extract_citation(self, cit_div) -> Dict:
        """Extract citation information."""
        citation = {}
        
        # Greek citation text
        cit_g = cit_div.find('div', class_='citG')
        if cit_g:
            # Extract individual Greek words
            greek_words = cit_g.find_all('span', class_='citg-word')
            if greek_words:
                citation['griekse_tekst'] = {
                    'woorden': [word.get_text(strip=True) for word in greek_words],
                    'volledige_tekst': cit_g.get_text(separator=' ', strip=True)
                }
            else:
                citation['griekse_tekst'] = {'volledige_tekst': cit_g.get_text(separator=' ', strip=True)}
        
        # Dutch translation of citation
        cit_nv = cit_div.find('div', class_='citNV')
        if cit_nv:
            citation['nederlandse_vertaling'] = cit_nv.get_text(strip=True)
        
        # Reference information
        verw_div = cit_div.find('div', class_='verw')
        if verw_div:
            citation['referentie'] = self._extract_reference_info(verw_div)
        
        return citation
    
    def _extract_reference_info(self, verw_div) -> Dict:
        """Extract detailed reference information."""
        ref_info = {
            'volledige_referentie': verw_div.get_text(separator=' ', strip=True),
            'data_abbr_verw': verw_div.get('data-abbr-verw', '')
        }
        
        # Author
        aut_div = verw_div.find('div', class_='aut')
        if aut_div:
            ref_info['auteur'] = aut_div.get_text(strip=True)
        
        # Work/title
        werk_div = verw_div.find('div', class_='werk')
        if werk_div:
            ref_info['werk'] = werk_div.get_text(strip=True)
        
        # Location/reference
        plaats_div = verw_div.find('div', class_='plaats')
        if plaats_div:
            ref_info['plaats'] = plaats_div.get_text(strip=True)
        
        return ref_info
    
    def _create_complete_text_summary(self, lemma_data: Dict) -> str:
        """Create a smart, structured complete text summary of the lemma."""
        if lemma_data.get('entry_type') == 'reference':
            return self._create_reference_summary(lemma_data)
        
        parts = []
        
        # 1. Headword
        if 'hoofdwoord' in lemma_data:
            parts.append(f"**{lemma_data['hoofdwoord'].strip()}**")
        
        # 2. Etymology
        if 'etymologie' in lemma_data:
            etym_text = lemma_data['etymologie'].get('volledige_tekst', '').strip()
            if etym_text:
                parts.append(f"Etymology: {etym_text}")
        
        # 3. Morphological information
        if 'morfologie' in lemma_data:
            morf_text = lemma_data['morfologie'].get('volledige_tekst', '').strip()
            if morf_text:
                parts.append(f"Forms: {morf_text}")
        
        # 4. Meanings with translations and examples
        if 'betekenissen' in lemma_data:
            for i, meaning in enumerate(lemma_data['betekenissen'], 1):
                meaning_parts = []
                
                # Number for multiple meanings
                if len(lemma_data['betekenissen']) > 1:
                    meaning_parts.append(f"{i}.")
                
                # Translations
                if 'vertalingen' in meaning:
                    translations = [t.strip() for t in meaning['vertalingen'] if t.strip()]
                    if translations:
                        meaning_parts.append(" ".join(translations))
                elif 'vertaling' in meaning:  # Fallback for old structure
                    if meaning['vertaling'].strip():
                        meaning_parts.append(meaning['vertaling'].strip())
                
                # Usage information (grammatical details)
                if 'gebruik_info' in meaning:
                    usage_texts = []
                    for gebruik in meaning['gebruik_info']:
                        if isinstance(gebruik, dict) and 'volledige_tekst' in gebruik:
                            usage_text = gebruik['volledige_tekst'].strip()
                            if usage_text and not any(usage_text.startswith(prefix) for prefix in ['abs.:', 'met ', 'soms ', 'ook']):
                                usage_texts.append(f"({usage_text})")
                    if usage_texts:
                        meaning_parts.append(" ".join(usage_texts))
                
                # Key citations (limit to most important ones)
                if 'citaten' in meaning and meaning['citaten']:
                    citation_examples = []
                    for citation in meaning['citaten'][:2]:  # Limit to first 2 citations per meaning
                        if 'griekse_tekst' in citation and 'nederlandse_vertaling' in citation:
                            greek = citation['griekse_tekst'].get('volledige_tekst', '').strip()
                            dutch = citation['nederlandse_vertaling'].strip()
                            if greek and dutch:
                                # Add author if available
                                author = ""
                                if 'referentie' in citation and 'auteur' in citation['referentie']:
                                    author = f" ({citation['referentie']['auteur'].strip()})"
                                citation_examples.append(f'"{greek}" = "{dutch}"{author}')
                    
                    if citation_examples:
                        meaning_parts.append("Examples: " + "; ".join(citation_examples))
                
                if meaning_parts:
                    parts.append(" ".join(meaning_parts))
        
        # 5. Cross-references for reference entries
        if 'kruisverwijzing' in lemma_data:
            kruis_text = lemma_data['kruisverwijzing'].get('volledige_tekst', '').strip()
            if kruis_text:
                parts.append(f"See: {kruis_text}")
        
        return " | ".join(parts) if parts else "No content available"
    
    def _create_reference_summary(self, lemma_data: Dict) -> str:
        """Create summary for reference entries."""
        parts = []
        
        # Headword
        if 'hoofdwoord' in lemma_data:
            parts.append(f"**{lemma_data['hoofdwoord'].strip()}**")
        
        # Morphological info
        if 'morfologie' in lemma_data:
            morf_text = lemma_data['morfologie'].get('volledige_tekst', '').strip()
            if morf_text:
                parts.append(morf_text)
        
        # Cross-reference
        if 'kruisverwijzing' in lemma_data:
            kruis_text = lemma_data['kruisverwijzing'].get('volledige_tekst', '').strip()
            if kruis_text:
                parts.append(f"→ {kruis_text}")
        
        return " | ".join(parts) if parts else "Reference entry"
    
    def _create_raw_text_summary(self, selected_lemma_element) -> str:
        """Create a clean text version of the entire HTML element."""
        if not selected_lemma_element:
            return ""
        
        # Create a copy to avoid modifying the original
        from copy import copy
        element_copy = copy(selected_lemma_element)
        
        # Remove XML comments and unwanted attributes
        for comment in element_copy.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()
        
        # Convert specific HTML structures to readable text
        text_parts = []
        
        # Find the main content (lem, xlLem, or verwLem)
        lem_div = element_copy.find('div', class_='lem')
        xl_lem_div = element_copy.find('div', class_='xlLem')
        verw_lem_div = element_copy.find('div', class_='verwLem')
        
        if lem_div:
            text_parts.append("=== FULL LEMMA ===")
            text_parts.append(self._convert_html_section_to_text(lem_div))
        elif xl_lem_div:
            text_parts.append("=== XL LEMMA ===")
            text_parts.append(self._convert_html_section_to_text(xl_lem_div))
        elif verw_lem_div:
            text_parts.append("=== REFERENCE LEMMA ===")
            text_parts.append(self._convert_html_section_to_text(verw_lem_div))
        
        return "\n".join(text_parts).strip()
    
    def _convert_html_section_to_text(self, section) -> str:
        """Convert an HTML section to structured text."""
        lines = []
        
        # Handle vorm section
        vorm_div = section.find('div', class_='vorm')
        if vorm_div:
            lines.append("\n--- FORM ---")
            
            # Headword
            hoofd_w = vorm_div.find('div', class_='hoofdW')
            if hoofd_w:
                lines.append(f"Headword: {hoofd_w.get_text(separator=' ', strip=True)}")
            
            # Etymology
            etym_div = vorm_div.find('div', class_='etym')
            if etym_div:
                lines.append(f"Etymology: {etym_div.get_text(separator=' ', strip=True)}")
            
            # Morphology
            morf_i = vorm_div.find('div', class_='morfI')
            if morf_i:
                lines.append(f"Morphology: {morf_i.get_text(separator=' ', strip=True)}")
        
        # Handle bet section (meanings) - support both regular 'bet' and XL 'xlBet'
        bet_div = section.find('div', class_='bet') or section.find('div', class_='xlBet')
        if bet_div:
            lines.append("\n--- MEANINGS ---")
            
            # Check for numbered list (both regular and XL patterns)
            ol_niv = bet_div.find('ol', class_=lambda x: x and (
                ('niv' in ' '.join(x) if isinstance(x, list) else 'niv' in x) or 
                ('xlNiv' in ' '.join(x) if isinstance(x, list) else 'xlNiv' in x)
            ))
            if ol_niv:
                for i, li in enumerate(ol_niv.find_all('li'), 1):
                    lines.append(f"\n{i}. {self._convert_meaning_item_to_text(li)}")
            else:
                # Simple meaning
                lines.append(self._convert_simple_meaning_to_text(bet_div))
        
        # Handle cross-reference (for verwLem)
        kruis_verw = section.find('div', class_='kruisVerw')
        if kruis_verw:
            lines.append(f"\nCross-reference: {kruis_verw.get_text(separator=' ', strip=True)}")
        
        return "\n".join(lines)
    
    def _convert_meaning_item_to_text(self, li_element) -> str:
        """Convert a meaning list item to text."""
        parts = []
        
        # Get all direct children in order
        for child in li_element.children:
            if hasattr(child, 'get') and child.get('class'):
                class_name = ' '.join(child.get('class', []))
                
                if 'gebrW' in class_name:
                    usage_text = child.get_text(separator=' ', strip=True)
                    if usage_text:
                        parts.append(f"Usage: {usage_text}")
                
                elif 'vertM' in class_name:
                    translation_text = child.get_text(separator=' ', strip=True)
                    if translation_text:
                        parts.append(f"Translation: {translation_text}")
                
                elif 'cit' in class_name:
                    citation_text = self._convert_citation_to_text(child)
                    if citation_text:
                        parts.append(f"Citation: {citation_text}")
        
        return " | ".join(parts)
    
    def _convert_citation_to_text(self, cit_element) -> str:
        """Convert a citation element to text."""
        parts = []
        
        # Greek text
        cit_g = cit_element.find('div', class_='citG')
        if cit_g:
            greek_text = cit_g.get_text(separator=' ', strip=True)
            if greek_text:
                parts.append(f"Greek: {greek_text}")
        
        # Dutch translation
        cit_nv = cit_element.find('div', class_='citNV')
        if cit_nv:
            dutch_text = cit_nv.get_text(separator=' ', strip=True)
            if dutch_text:
                parts.append(f"Dutch: {dutch_text}")
        
        # Reference
        verw_div = cit_element.find('div', class_='verw')
        if verw_div:
            ref_text = verw_div.get_text(separator=' ', strip=True)
            if ref_text:
                parts.append(f"Ref: {ref_text}")
        
        return " - ".join(parts)
    
    def _convert_simple_meaning_to_text(self, bet_div) -> str:
        """Convert simple meaning structure to text."""
        parts = []
        
        # Usage info
        gebr_w = bet_div.find('div', class_='gebrW')
        if gebr_w:
            usage_text = gebr_w.get_text(separator=' ', strip=True)
            if usage_text:
                parts.append(f"Usage: {usage_text}")
        
        # Translation
        vert_m = bet_div.find('div', class_='vertM')
        if vert_m:
            translation_text = vert_m.get_text(separator=' ', strip=True)
            if translation_text:
                parts.append(f"Translation: {translation_text}")
        
        return " | ".join(parts)
    
    def scrape_lemma(self, lemma_id: int) -> Optional[Dict]:
        """
        Scrape a single lemma by ID using Selenium.
        
        Args:
            lemma_id: The lemma ID to scrape
            
        Returns:
            Dictionary containing lemma data or None if failed
        """
        url = f"{self.base_url}/{lemma_id}"
        
        try:
            logger.info(f"Scraping lemma {lemma_id}")
            
            # Navigate to the page
            self.driver.get(url)
            
            # Wait for the selected lemma to appear
            try:
                # Wait for any element with x--selected class to be present
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='x--selected']"))
                )
                
                # Give a bit more time for full content loading
                time.sleep(0.5)
                
            except TimeoutException:
                logger.warning(f"Timeout waiting for selected lemma on page {lemma_id}")
                return None
            
            # Get page source and extract data
            page_source = self.driver.page_source
            lemma_data = self.extract_lemma_data(page_source)
            
            if lemma_data:
                lemma_data['lemma_id'] = lemma_id
                lemma_data['url'] = url
                
                # Add complete text summary for MCP/LLM consumption
                lemma_data['complete_text'] = self._create_complete_text_summary(lemma_data)
                
            return lemma_data
            
        except Exception as e:
            logger.error(f"Error scraping lemma {lemma_id}: {e}")
            return None
    
    def scrape_range(self, start_id: int, end_id: int) -> List[Dict]:
        """
        Scrape a range of lemmas.
        
        Args:
            start_id: Starting lemma ID (inclusive)
            end_id: Ending lemma ID (inclusive)
            
        Returns:
            List of lemma dictionaries
        """
        lemmas = []
        total = end_id - start_id + 1
        successful = 0
        
        for i, lemma_id in enumerate(range(start_id, end_id + 1)):
            lemma_data = self.scrape_lemma(lemma_id)
            
            if lemma_data:
                lemmas.append(lemma_data)
                successful += 1
            
            # Progress tracking
            progress = ((i + 1) / total) * 100
            logger.info(f"Progress: {progress:.1f}% ({i + 1}/{total}) - Successful: {successful}")
            
            # Rate limiting
            if i < total - 1:  # Don't delay after last request
                time.sleep(self.delay)
        
        return lemmas
    
    def save_to_file(self, lemmas: List[Dict], filename: str) -> None:
        """
        Save lemmas to JSON file.
        
        Args:
            lemmas: List of lemma dictionaries
            filename: Output filename
        """
        try:
            # Add some statistics
            stats = {
                'total_lemmas': len(lemmas),
                'full_lemmas': len([l for l in lemmas if l.get('entry_type') == 'full']),
                'regular_lemmas': len([l for l in lemmas if l.get('lemma_format') == 'regular']),
                'xl_lemmas': len([l for l in lemmas if l.get('lemma_format') == 'xl']),
                'reference_lemmas': len([l for l in lemmas if l.get('entry_type') == 'reference']),
                'lemmas_with_citations': len([l for l in lemmas if any('citaten' in m for m in l.get('betekenissen', []))]),
                'lemmas_with_etymology': len([l for l in lemmas if 'etymologie' in l]),
                'lemmas_with_complete_text': len([l for l in lemmas if 'complete_text' in l and l['complete_text']]),
                'lemmas_with_raw_text': len([l for l in lemmas if 'raw_text' in l and l['raw_text']]),
                'average_text_length': sum(len(l.get('complete_text', '')) for l in lemmas) // max(len(lemmas), 1),
                'average_raw_text_length': sum(len(l.get('raw_text', '')) for l in lemmas) // max(len(lemmas), 1)
            }
            
            # Create output structure
            output_data = {
                'metadata': {
                    'scrape_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'statistics': stats
                },
                'lemmas': lemmas
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(lemmas)} lemmas to {filename}")
            logger.info(f"Statistics: {stats['full_lemmas']} full ({stats['regular_lemmas']} regular, {stats['xl_lemmas']} XL), "
                       f"{stats['reference_lemmas']} reference, {stats['lemmas_with_citations']} with citations, "
                       f"{stats['lemmas_with_etymology']} with etymology")
            logger.info(f"Complete text summaries: {stats['lemmas_with_complete_text']} entries, "
                       f"avg length: {stats['average_text_length']} chars")
            logger.info(f"Raw text summaries: {stats['lemmas_with_raw_text']} entries, "
                       f"avg length: {stats['average_raw_text_length']} chars")
        except Exception as e:
            logger.error(f"Error saving to file: {e}")

def main():
    parser = argparse.ArgumentParser(description='Scrape Greek-Dutch dictionary (JavaScript-enabled)')
    parser.add_argument('--start', type=int, default=0, help='Start lemma ID (default: 0)')
    parser.add_argument('--end', type=int, default=49, help='End lemma ID (default: 49)')
    parser.add_argument('--output', type=str, default='greek_lemmas.json', help='Output filename')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout for waiting for elements')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode (not headless)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.start < 0 or args.end < args.start:
        logger.error("Invalid range specified")
        return
    
    if args.end > 43626:
        logger.warning(f"End ID {args.end} exceeds maximum (43626), setting to 43626")
        args.end = 43626
    
    # Initialize scraper with context manager
    headless = not args.visible
    
    try:
        with GreekDictScraper(delay=args.delay, headless=headless, timeout=args.timeout) as scraper:
            # Scrape lemmas
            logger.info(f"Starting scrape: lemmas {args.start} to {args.end}")
            lemmas = scraper.scrape_range(args.start, args.end)
            
            # Save results
            if lemmas:
                scraper.save_to_file(lemmas, args.output)
                logger.info(f"Scraping complete! Retrieved {len(lemmas)} lemmas")
            else:
                logger.error("No lemmas retrieved")
                
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()