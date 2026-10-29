"""Controlli extra: caratteri di sostituzione, doppia codifica, esempi di accenti."""
import re
from collections import Counter

text = open("index.html", "rb").read().decode("utf-8")
print("U+FFFD:", text.count("\ufffd"))
print("Ã:", text.count("Ã"), "вЂ:", text.count("вЂ"), "â€:", text.count("â€"))
acc = Counter(ch for ch in text if ch in "àèéìòùÀÈÉÌÒÙ")
print("accenti per carattere:", dict(acc))
for parola in ["città", "perché", "più", "può", "è ", "Proprietà", "già", "così", "né "]:
    print(f"{parola!r}:", text.count(parola))
