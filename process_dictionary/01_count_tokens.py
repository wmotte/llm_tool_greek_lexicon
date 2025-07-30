#!/usr/bin/env python
#
# Wim Otte (w.m.otte@umcutrecht.nl)
#
# This script counts the number of tokens in a given text file.
########################################################################
import argparse

def count_tokens(text):
    # Simple whitespace tokenization
    tokens = text.split()
    return len(tokens)

def main():
    parser = argparse.ArgumentParser(description="Count tokens in a text file.")
    parser.add_argument('-i', '--input', required=True, help='Input text file')
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as file:
            text = file.read()
        token_count = count_tokens(text)
        print(f"Token count: {token_count}")
    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()

