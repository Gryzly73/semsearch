# PROGRESS

Decision and replanning log. One line per event. The agent appends; the loop reads it.
iter 1 T1: added Index.save/load (docs JSON, re-embed on load) and CLI index/--index; persistence tests pass
iter 3 T2: Cyrillic tokenize with yo-folding, Russian stopwords and suffix stemmer; ru recall@3=1.0
iter 4 T3: Index.search(lang=...) filters by doc.lang; CLI search --lang wired through
