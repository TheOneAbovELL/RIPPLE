---
name: explain
description: Explain a module to the author so he can understand, defend and modify it
argument-hint: <module path>
---
Explain $ARGUMENTS for the author, who must be able to defend it in an interview.
Write or update docs/learning/<module-name>.md with:
1. What it does, in three sentences.
2. Why it exists: the requirement and ADRs behind it.
3. How it works: the main flow, naming the key functions.
4. Trade-offs: what we chose against, and when that choice would be wrong.
5. Failure modes and which tests cover them.
6. Five interview questions with short model answers.
7. One small exercise for the author to do by hand.
Under two pages. Describe only code that exists.
