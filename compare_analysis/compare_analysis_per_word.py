#!/usr/bin/env python
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#
# Comparison in case sentences do not match.
###########################################################
import json
import argparse

def flatten_tokens(data):
    """
    Voegt alle token-analyses van alle zinnen samen tot één platte lijst.

    Args:
        data (dict): De geladen JSON-data.

    Returns:
        list: Een lijst van alle token-dictionaries.
    """
    all_tokens = []
    for sentence in data.get("sentences", []):
        all_tokens.extend(sentence.get("analysis", []))
    return all_tokens

def compare_analyses(file1_path, file2_path, output_path):
    """
    Vergelijkt twee JSON-bestanden met Griekse tekst-analyse token voor token,
    ongeacht de zinsopdeling, en rapporteert de verschillen.

    De volgende sleutels worden genegeerd bij de vergelijking:
    - "dictionary_entry_nl", "gloss"
    - "translation_nl", "translation_en", "translation_fr"

    Args:
        file1_path (str): Pad naar het eerste JSON-bestand.
        file2_path (str): Pad naar het tweede JSON-bestand.
        output_path (str): Pad naar het uitvoer-tekstbestand voor de verschillen.
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
    keys_to_ignore_token = {"dictionary_entry_nl", "gloss"}
    
    # Maak platte lijsten van alle tokens, onafhankelijk van de zinsstructuur
    tokens1 = flatten_tokens(data1)
    tokens2 = flatten_tokens(data2)

    discrepancies = []
    max_tokens = max(len(tokens1), len(tokens2))

    for i in range(max_tokens):
        token_discrepancies = []
        
        token1 = tokens1[i] if i < len(tokens1) else None
        token2 = tokens2[i] if i < len(tokens2) else None

        # Controleer op extra tokens in een van de bestanden
        if token1 is None:
            discrepancies.append(f"\n--- Extra token in Bestand 2 op algehele positie {i+1} ---")
            discrepancies.append(f"  Token: '{token2.get('token')}'")
            continue
        if token2 is None:
            discrepancies.append(f"\n--- Extra token in Bestand 1 op algehele positie {i+1} ---")
            discrepancies.append(f"  Token: '{token1.get('token')}'")
            continue
        
        # Verzamel alle unieke sleutels van beide tokens, behalve de genegeerde
        all_keys = (token1.keys() | token2.keys()) - keys_to_ignore_token

        for key in sorted(list(all_keys)):
            val1 = token1.get(key)
            val2 = token2.get(key)

            if val1 != val2:
                # Voeg een header toe voor het token, alleen bij de eerste discrepantie
                if not token_discrepancies:
                    token_ref = token1.get('token') if token1.get('token') == token2.get('token') else f"{token1.get('token')}/{token2.get('token')}"
                    token_discrepancies.append(f"\n--- Discrepantie voor token '{token_ref}' op algehele positie {i+1} ---")

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
            discrepancies.extend(token_discrepancies)

    # Schrijf de resultaten naar het outputbestand
    try:
        with open(output_path, 'w', encoding='utf-8') as f_out:
            f_out.write(f"Resultaten van de vergelijking tussen:\n1: {file1_path}\n2: {file2_path}\n")
            f_out.write("====================================================\n")
            if discrepancies:
                f_out.write("\n".join(discrepancies))
            else:
                f_out.write("\nGeen inhoudelijke discrepanties gevonden in de token-analyses.")
        print(f"✅ Vergelijking voltooid. Resultaten zijn opgeslagen in '{output_path}'.")
    except IOError:
        print(f"❌ Fout: Kan niet schrijven naar het uitvoerbestand '{output_path}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Vergelijkt twee JSON-bestanden met Griekse tekst-analyse token voor token, ongeacht de zinsopdeling.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Voorbeeld:\npython %(prog)s -i1 bestand1.json -i2 bestand2.json -o output.txt"
    )
    parser.add_argument(
        "-i1", "--input1",
        required=True,
        help="Pad naar het eerste JSON-invoerbestand."
    )
    parser.add_argument(
        "-i2", "--input2",
        required=True,
        help="Pad naar het tweede JSON-invoerbestand."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Pad naar het TXT-uitvoerbestand voor de discrepanties."
    )

    args = parser.parse_args()
    compare_analyses(args.input1, args.input2, args.output)
