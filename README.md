# Tool-Augmented Language Models for Precision Analysis of Ancient Greek Texts

This repository contains the code, processing scripts, and resources for the project "Tool-Augmented Language Models for Precision Analysis of Ancient/Koine Greek Texts Using a Graph-based Lexicon".

The project introduces a novel methodology that enhances Large Language Models (LLMs) with a dedicated, real-time lexical tool to achieve high-precision morphosyntactic and functional grammar analysis of Ancient Greek texts.

An interactive website to explore the parsed results is available here:
** [https://wmotte.github.io/llm_tool_greek_lexicon/docs/](https://wmotte.github.io/llm_tool_greek_lexicon/docs/)**

---

## The Problem

Computational analysis of Ancient Greek has traditionally been hampered by the limitations of existing methods.
* **Rule-based morphological parsers** often fail to handle the language's vast dialectical complexity and the frequent occurrence of ambiguous word forms.
* **Modern Retrieval-Augmented Generation (RAG) systems**, while powerful, retrieve information based on semantic similarity (approximate matching). This lacks the precision required for a morphologically rich language like Ancient Greek, where a single character can fundamentally alter a word's meaning (e.g., λόγος vs. λύγος).

This project bridges this methodological gap by developing a system capable of exact lemma identification and deep linguistic analysis, moving beyond the limitations of both purely rule-based and similarity-based approaches.

## Our Approach: Tool-Augmented AI

We present a tool-augmented modeling approach that integrates LLMs with real-time, dynamic access to a structured lexical database. This architecture moves beyond simple context-stuffing (RAG) and allows the LLM to actively query a specialized tool for precise information when needed.

The core components of our system are:
1.  **A Neo4j Knowledge Graph**: We constructed a graph database containing a complete, scholarly Greek-Dutch lexicon. Graph databases are exceptionally well-suited for modeling the complex, interconnected relationships inherent in linguistic data, outperforming traditional relational databases in such tasks.
2.  **The Model Context Protocol (MCP)**: The knowledge graph is made available to the LLM as a "tool" via an MCP server. This protocol allows any tool-calling LLM to dynamically query the lexicon for exact lemma matching, overcoming the context window limitations of traditional methods.

This combination enables a more accurate and nuanced analysis of ancient texts, incorporating principles from functional linguistics frameworks like Lexical Functional Grammar (LFG) and Systemic Functional Linguistics (SFL).

## The Lexicon: Knowledge Graph Construction

The foundation of our tool is a machine-readable knowledge graph built from the **Grieks-Nederlands Lexicon (SvBKR)**, a scholarly dictionary covering Greek vocabulary from Homer to the second century CE.

The construction process involved several key steps:
* **Data Retrieval**: The complete lexicon, comprising 43,626 lemma entries, was retrieved by web scraping the publicly available HTML interface.
* **Expansion of Forms**: Many dictionary entries were in a compressed format (e.g., providing only the nominative and genitive singular forms). These were manually expanded into their full inflected forms using standard paradigms to facilitate precise matching.
* **Diacritic-Insensitive Indexing**: To allow for flexible matching against unaccented Greek input, each lexical form was duplicated into a variant without diacritics (e.g., ἀβάκιον → αβακιον). This ensures robust lookup while preserving the integrity of the original, accented forms.
* **Graph Modeling**: All structured data was imported into a Neo4j graph database. Each lemma is a `LexicalEntry` node with properties for grammar, glosses, and source info. This graph structure enables efficient querying of lemma frequency, contextual usage, and intertextual relationships.

The processing scripts used for this process are available in this repository to ensure full replication and adaptation.

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


**2. Batch Processing for Multiple Lemmas**
This demonstrates the efficiency of retrieving multiple entries in a single call.

```cypher
// This batch query simultaneously retrieves lexical entries for multiple lemmas
MATCH (l:Lemma)-[:HAS_ENTRY]->(e:Entry)-[:BELONGS_TO]->(d:Dictionary)
WHERE l.text_no_accents IN ["eimi", "logos", "theos", "anthropos"]
AND d.name = "SvBKR"
RETURN l.text, l.text_no_accents, e.text
```


## Evaluation and Test Cases

The system's performance was systematically evaluated using three distinct and challenging Greek texts, each chosen for a specific purpose.

1.  **Hebrews 2:9 (New Testament)**: Selected for its high degree of grammatical and syntactical complexity. We also tested a minority textual variant (`χωρὶς θεοῦ` vs. `χάριτι θεοῦ`) to evaluate the model's ability to handle subtle but critical input changes, a test against the "Einstellung effect".
2.  **Job 2:9 (Septuagint)**: This passage features a long, 93-word diatribe that is a unique addition in the Greek LXX version compared to the Hebrew Masoretic Text. It serves as an excellent test case for morphosyntactic performance on a lengthy, less common text that is not well-covered by online biblical data.
3.  **The Gospel according to the Egyptians**: This fragmentary, apocryphal text is not openly available online and is restricted to licensed academic databases. This minimizes the chance it was in the LLM's pre-training data, providing a robust benchmark for evaluating the model's parsing capabilities on genuinely "unseen" text with complex syntactic structures.

The results, which can be explored on the **[interactive website](https://wmotte.github.io/llm_tool_greek_lexicon/docs/)**, demonstrate that the tool-augmented approach provides strong performance in both morphosyntactic parsing and functional grammar analysis across all test cases.

## Usage

To replicate the knowledge graph construction or adapt the code, you can clone the repository and install the necessary Python packages.

The analytical workflow was executed using command-line interface (CLI) tools (Gemini CLI, Claude Code) connected to the Neo4j database via a local MCP server implementation. The prompt instructions and JSON output schema are detailed in the manuscript's supplemental data.

## Citation

If you use this work in your research, please cite the following manuscript:

Otte, W. M., van Wieringen, A. L. H. M., & Koet, B. J. (in preparation). *Tool-Augmented Language Models for Precision Analysis of Ancient/Koine Greek Texts Using a Graph-based Lexicon*.


## License

This project is licensed under the CC0 1.0 Universal License. See the `LICENSE` file for details.


