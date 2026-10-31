---
name: adr
description: Create a new Architecture Decision Record and add it to the index
argument-hint: <short decision title>
---
Create an ADR for: $ARGUMENTS
1. Read docs/adr/README.md. Find the next number; confirm no existing ADR covers this.
2. Copy docs/adr/0000-template.md to docs/adr/NNNN-<kebab-title>.md.
3. Fill every section. Alternatives: at least two real options with honest pros and cons.
   Consequences: include the downsides we accept.
4. Status: Proposed. Add it to the index table.
5. Show it to the author and ask for approval. Only after approval set Status to Accepted.
If it supersedes an ADR, mark that one "Superseded by NNNN" and link both ways.
