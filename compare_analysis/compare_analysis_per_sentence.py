#!/usr/bin/env python
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#######################################################################
#
import json
import argparse

def compare_json_files(file1_path, file2_path, output_path):
    """
    Vergelijkt twee JSON-bestanden met Griekse tekst-analyse en rapporteert de verschillen
    op een gebruikersvriendelijke manier.

    De volgende sleutels worden genegeerd bij de vergelijking:
    - "dictionary_entry_nl"
    - "gloss"
    - "translation_nl"
    - "translation_en"
    - "translation_fr"

    Args:
        file1_path (str): Pad naar het eerste JSON-bestand.
        file2_path (str): Pad naar het tweede JSON-bestand.
        output_path (str): Pad naar het uitvoer-tekstbestand waar de verschillen worden opgeslagen.
    """
    try:
        with open(file1_path, 'r', encoding='utf-8') as f1:
            data1 = json.load(f1)
        with open(file2_path, 'r', encoding='utf-8') as f2:
            data2 = json.load(f2)
    except FileNotFoundError as e:
        print(f"Fout: Bestand niet gevonden - {e.filename}")
        return
    except json.JSONDecodeError as e:
        print(f"Fout: Ongeldig JSON-formaat in een van de bestanden. Details: {e}")
        return

    # Definieer de sleutels die overgeslagen moeten worden
    keys_to_ignore_global = {"translation_nl", "translation_en", "translation_fr"}
    keys_to_ignore_token = {"dictionary_entry_nl", "gloss"}
    
    discrepancies = []

    # Haal zinnen op uit beide bestanden
    sentences1 = data1.get("sentences", [])
    sentences2 = data2.get("sentences", [])

    # Vergelijk de zinnen op basis van hun index
    max_sentences = max(len(sentences1), len(sentences2))
    for i in range(max_sentences):
        sentence_discrepancies = []
        
        # Controleer of de zin in beide bestanden bestaat
        if i >= len(sentences1):
            sentence_discrepancies.append(f"Zin {i+1} ontbreekt in bestand 1, maar bestaat wel in bestand 2.")
            discrepancies.extend(sentence_discrepancies)
            continue
        if i >= len(sentences2):
            sentence_discrepancies.append(f"Zin {i+1} ontbreekt in bestand 2, maar bestaat wel in bestand 1.")
            discrepancies.extend(sentence_discrepancies)
            continue

        sentence1 = sentences1[i]
        sentence2 = sentences2[i]
        
        # Vergelijk de Griekse zinstekst
        if sentence1.get("sentence_text") != sentence2.get("sentence_text"):
            sentence_discrepancies.append(f"Verschil in de Griekse brontekst (zin {i+1}):")
            sentence_discrepancies.append(f"  Bestand 1: {sentence1.get('sentence_text')}")
            sentence_discrepancies.append(f"  Bestand 2: {sentence2.get('sentence_text')}")

        # Haal de token-analyses op
        analysis1 = sentence1.get("analysis", [])
        analysis2 = sentence2.get("analysis", [])
        
        max_tokens = max(len(analysis1), len(analysis2))
        for j in range(max_tokens):
            token_discrepancies = []
            
            # Controleer of het token in beide analyses bestaat
            if j >= len(analysis1):
                token2 = analysis2[j]
                token_discrepancies.append(f"  - Token '{token2.get('token')}' (pos {j+1}) ontbreekt in bestand 1.")
                sentence_discrepancies.extend(token_discrepancies)
                continue
            if j >= len(analysis2):
                token1 = analysis1[j]
                token_discrepancies.append(f"  - Token '{token1.get('token')}' (pos {j+1}) ontbreekt in bestand 2.")
                sentence_discrepancies.extend(token_discrepancies)
                continue
            
            token1 = analysis1[j]
            token2 = analysis2[j]
            
            # Verzamel alle unieke sleutels van beide tokens, behalve de genegeerde
            all_keys = (token1.keys() | token2.keys()) - keys_to_ignore_token

            for key in sorted(list(all_keys)):
                val1 = token1.get(key)
                val2 = token2.get(key)

                if val1 != val2:
                    # Header toevoegen voor het token, alleen als er nog geen is
                    if not token_discrepancies:
                         # Gebruik het token van het eerste bestand als referentie, of het tweede als het eerste afwijkt
                        token_ref = token1.get('token') if token1.get('token') == token2.get('token') else f"{token1.get('token')}/{token2.get('token')}"
                        token_discrepancies.append(f"\nDiscrepanties voor token '{token_ref}' (positie {j+1}):")

                    # Speciale behandeling voor de geneste 'parsing_details' dictionary
                    if key == "parsing_details" and isinstance(val1, dict) and isinstance(val2, dict):
                        detail_keys = val1.keys() | val2.keys()
                        for d_key in sorted(list(detail_keys)):
                            d_val1 = val1.get(d_key)
                            d_val2 = val2.get(d_key)
                            if d_val1 != d_val2:
                                token_discrepancies.append(f"  - Verschil in '{key}.{d_key}':")
                                token_discrepancies.append(f"      Bestand 1: {d_val1}")
                                token_discrepancies.append(f"      Bestand 2: {d_val2}")
                    else:
                        token_discrepancies.append(f"  - Verschil in '{key}':")
                        token_discrepancies.append(f"      Bestand 1: {val1}")
                        token_discrepancies.append(f"      Bestand 2: {val2}")

            if token_discrepancies:
                sentence_discrepancies.extend(token_discrepancies)
        
        if sentence_discrepancies:
            discrepancies.append(f"\n{'='*20} ZIN {i+1} {'='*20}")
            discrepancies.extend(sentence_discrepancies)

    # Schrijf de resultaten naar het outputbestand
    try:
        with open(output_path, 'w', encoding='utf-8') as f_out:
            if discrepancies:
                f_out.write("Resultaten van de vergelijking tussen JSON-bestanden\n")
                f_out.write("====================================================\n")
                f_out.write("\n".join(discrepancies))
            else:
                f_out.write("Geen discrepanties gevonden tussen de opgegeven bestanden (met uitzondering van de genegeerde velden).\n")
        print(f"✅ Vergelijking voltooid. Resultaten zijn opgeslagen in '{output_path}'.")
    except IOError:
        print(f"❌ Fout: Kan niet schrijven naar het uitvoerbestand '{output_path}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Vergelijk twee JSON-bestanden met morphosyntactische en functionele analyse van Griekse tekst.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Voorbeeld:\npython %(prog)s -i1 bestand1.json -i2 bestand2.json -o output.txt"
    )
    parser.add_argument(
        "-i1", "--input1",
        required=True,
        help="Pad naar het eerste JSON-invoerbestand (bv. scholarly variant)."
    )
    parser.add_argument(
        "-i2", "--input2",
        required=True,
        help="Pad naar het tweede JSON-invoerbestand (bv. minority variant)."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Pad naar het TXT-uitvoerbestand voor de discrepanties."
    )

    args = parser.parse_args()
    compare_json_files(args.input1, args.input2, args.output)
