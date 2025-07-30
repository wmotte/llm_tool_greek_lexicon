Of course. Here is an updated and more detailed README.md, incorporating the rationale and technical specifics from the provided manuscript.

````markdown
# Tool-Augmented Language Models for Precision Analysis of Ancient Greek Texts

[![License: MIT](httpss://img.shields.io/badge/License-MIT-yellow.svg)](httpss://opensource.org/licenses/MIT)

[cite_start]This repository contains the code, processing scripts, and resources for the project "Tool-Augmented Language Models for Precision Analysis of Ancient/Koine Greek Texts Using a Graph-based Lexicon"[cite: 2].

The project introduces a novel methodology that enhances Large Language Models (LLMs) with a dedicated, real-time lexical tool to achieve high-precision morphosyntactic and functional grammar analysis of Ancient Greek texts.

An interactive website to explore the parsed results is available here:
**[https://wmotte.github.io/llm_tool_greek_lexicon/docs/](https://wmotte.github.io/llm_tool_greek_lexicon/docs/)**

---

## The Problem

[cite_start]Computational analysis of Ancient Greek has traditionally been hampered by the limitations of existing methods[cite: 16].
* [cite_start]**Rule-based morphological parsers** often fail to handle the language's vast dialectical complexity and the frequent occurrence of ambiguous word forms[cite: 17, 45].
* **Modern Retrieval-Augmented Generation (RAG) systems**, while powerful, retrieve information based on semantic similarity (approximate matching). [cite_start]This lacks the precision required for a morphologically rich language like Ancient Greek, where a single character can fundamentally alter a word's meaning (e.g., λόγος vs. λύγος)[cite: 17, 58, 59].

[cite_start]This project bridges this methodological gap by developing a system capable of exact lemma identification and deep linguistic analysis, moving beyond the limitations of both purely rule-based and similarity-based approaches[cite: 22, 82].

## Our Approach: Tool-Augmented AI

[cite_start]We present a tool-augmented modeling approach that integrates LLMs with real-time, dynamic access to a structured lexical database[cite: 18]. [cite_start]This architecture moves beyond simple context-stuffing (RAG) and allows the LLM to actively query a specialized tool for precise information when needed[cite: 102, 105].

The core components of our system are:
1.  **A Neo4j Knowledge Graph**: We constructed a graph database containing a complete, scholarly Greek-Dutch lexicon. [cite_start]Graph databases are exceptionally well-suited for modeling the complex, interconnected relationships inherent in linguistic data, outperforming traditional relational databases in such tasks[cite: 97, 98, 99].
2.  [cite_start]**The Model Context Protocol (MCP)**: The knowledge graph is made available to the LLM as a "tool" via an MCP server[cite: 84]. [cite_start]This protocol allows any tool-calling LLM to dynamically query the lexicon for exact lemma matching, overcoming the context window limitations of traditional methods[cite: 18, 103, 105].

[cite_start]This combination enables a more accurate and nuanced analysis of ancient texts, incorporating principles from functional linguistics frameworks like Lexical Functional Grammar (LFG) and Systemic Functional Linguistics (SFL)[cite: 20, 67, 71].

## The Lexicon: Knowledge Graph Construction

[cite_start]The foundation of our tool is a machine-readable knowledge graph built from the **Grieks-Nederlands Lexicon (SvBKR)**, a scholarly dictionary covering Greek vocabulary from Homer to the second century CE[cite: 107, 108].

The construction process involved several key steps:
* [cite_start]**Data Retrieval**: The complete lexicon, comprising 43,626 lemma entries, was retrieved by web scraping the publicly available HTML interface[cite: 108, 109].
* [cite_start]**Expansion of Forms**: Many dictionary entries were in a compressed format (e.g., providing only the nominative and genitive singular forms)[cite: 112, 113]. [cite_start]These were manually expanded into their full inflected forms using standard paradigms to facilitate precise matching[cite: 114].
* [cite_start]**Diacritic-Insensitive Indexing**: To allow for flexible matching against unaccented Greek input, each lexical form was duplicated into a variant without diacritics (e.g., ἀβάκιον → αβακιον)[cite: 116]. [cite_start]This ensures robust lookup while preserving the integrity of the original, accented forms[cite: 117].
* **Graph Modeling**: All structured data was imported into a Neo4j graph database. [cite_start]Each lemma is a `LexicalEntry` node with properties for grammar, glosses, and source info[cite: 118, 119]. [cite_start]This graph structure enables efficient querying of lemma frequency, contextual usage, and intertextual relationships[cite: 121].

[cite_start]The processing scripts used for this process are available in this repository to ensure full replication and adaptation[cite: 122].

### Example Database Queries

The LLM interacts with the knowledge graph using Cypher queries. This allows for precise, efficient retrieval of lexical data.

**1. Single Lemma Lookup (Exact Match)**
This query finds a lemma by matching its normalized, accent-free form.
```cypher
// This query locates the exact lemma λόγος by matching its normalized form ‘logos’
MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)-[:BELONGS_TO]->(d:Dictionary)
WHERE l.text_no_accents = "logos"
AND d.name = "SvBKR "
RETURN l.text, e.text
````

[cite\_start][cite: 140, 142, 143, 144, 145]

**2. Batch Processing for Multiple Lemmas**
This demonstrates the efficiency of retrieving multiple entries in a single call.

```cypher
// This batch query simultaneously retrieves lexical entries for multiple lemmas
MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)-[:BELONGS_TO]->(d:Dictionary)
WHERE l.text_no_accents IN ["eimi", "logos", "theos", "anthropos"]
AND d.name = "SvBKR"
RETURN l.text, l.text_no_accents, e.text
```

[cite\_start][cite: 146, 148, 149, 150, 151]

## Evaluation and Test Cases

[cite\_start]The system's performance was systematically evaluated using three distinct and challenging Greek texts, each chosen for a specific purpose[cite: 20, 85, 155].

1.  [cite\_start]**Hebrews 2:9 (New Testament)**: Selected for its high degree of grammatical and syntactical complexity[cite: 159, 161, 163]. [cite\_start]We also tested a minority textual variant (`χωρὶς θεοῦ` vs. `χάριτι θεοῦ`) to evaluate the model's ability to handle subtle but critical input changes, a test against the "Einstellung effect"[cite: 168, 169, 170].
2.  [cite\_start]**Job 2:9 (Septuagint)**: This passage features a long, 93-word diatribe that is a unique addition in the Greek LXX version compared to the Hebrew Masoretic Text[cite: 176, 178, 179]. [cite\_start]It serves as an excellent test case for morphosyntactic performance on a lengthy, less common text that is not well-covered by online biblical data[cite: 180, 182].
3.  [cite\_start]**The Gospel according to the Egyptians**: This fragmentary, apocryphal text is not openly available online and is restricted to licensed academic databases[cite: 189, 190]. [cite\_start]This minimizes the chance it was in the LLM's pre-training data, providing a robust benchmark for evaluating the model's parsing capabilities on genuinely "unseen" text with complex syntactic structures[cite: 199, 200, 203].

[cite\_start]The results, which can be explored on the **[interactive website](https://wmotte.github.io/llm_tool_greek_lexicon/docs/)**, demonstrate that the tool-augmented approach provides strong performance in both morphosyntactic parsing and functional grammar analysis across all test cases[cite: 209, 156].

## Installation & Usage

To replicate the knowledge graph construction or adapt the code, you can clone the repository and install the necessary Python packages.

```bash
git clone httpss://[github.com/wmotte/llm_tool_greek_lexicon.git](https://github.com/wmotte/llm_tool_greek_lexicon.git)
cd llm_tool_greek_lexicon
# It is recommended to create a virtual environment first
pip install -r requirements.txt
```

[cite\_start]The analytical workflow was executed using command-line interface (CLI) tools (Gemini CLI, Claude Code) connected to the Neo4j database via a local MCP server implementation[cite: 127, 130]. [cite\_start]The prompt instructions and JSON output schema are detailed in the manuscript's supplemental data[cite: 138, 478].

## Citation

If you use this work in your research, please cite the following manuscript:

Otte, W. M., van Wieringen, A. L. H. M., & Koet, B. J. (in preparation). *Tool-Augmented Language Models for Precision Analysis of Ancient/Koine Greek Texts Using a Graph-based Lexicon*. [cite\_start]To be submitted to *Natural Language Processing Journal*. [cite: 2, 3, 14]

## Author & Contact

  * [cite\_start]**Willem M. Otte, PhD** [cite: 3, 8]
      * [cite\_start]Tilburg University, Tilburg School of Catholic Theology, Tilburg, The Netherlands [cite: 5]
      * [cite\_start]Utrecht University, UMC Utrecht Brain Center, Utrecht, The Netherlands [cite: 6]
      * [cite\_start]Contact: `w.m.otte@umcutrecht.nl` [cite: 13]

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

```
```
