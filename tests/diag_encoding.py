"""Verifica encoding del file HTML: accenti, mojibake, meta charset, campioni UI."""
import re

raw = open("index.html", "rb").read()
text = raw.decode("utf-8")
accenti = len(re.findall(r"[àèéìòùÀÈÉÌÒÙ]", text))
mojibake = len(re.findall(r"вЂ|Ã[\x80-\xbf]|â€|Ð[°-¿]", text))
campioni = ["Seleziona", "Proprietà", "Modifiche non salvate", "Salva con nome", "Ridimensiona"]
print("bytes:", len(raw))
print("chars:", len(text))
print("accenti:", accenti)
print("mojibake:", mojibake)
print("meta charset UTF-8:", bool(re.search(r'<meta[^>]+charset=["\']?utf-8', text, re.I)))
print("campioni presenti:", {c: c in text for c in campioni})
# mostra un paio di righe con accenti per ispezione
for m in re.finditer(r"^.*[àèéìòù].*$", text, re.M):
    print("ESEMPIO:", m.group(0)[:110])
    break
