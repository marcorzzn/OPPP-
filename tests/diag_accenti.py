"""Conteggio completo delle lettere accentate e delle parole italiane tipiche."""
import re
import unicodedata
from collections import Counter

text = open("index.html", "rb").read().decode("utf-8")
lettere = Counter()
for ch in text:
    if ch.isalpha() and ord(ch) > 127:
        lettere[ch] += 1
print("occorrenze accentate totali:", sum(lettere.values()))
print("per carattere:", dict(sorted(lettere.items(), key=lambda kv: -kv[1])))
for w in ["qualità", "attività", "densità", "proprietà", "perché", "può", "più", "città", "è", "sarà", "verrà"]:
    print(f"{w}:", len(re.findall(r"(?<!\w)" + re.escape(w) + r"(?!\w)", text, re.I)))
