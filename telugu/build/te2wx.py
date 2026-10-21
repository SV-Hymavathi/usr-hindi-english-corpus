"""Telugu script -> WX (case-sensitive; the inverse of wx2te.py).
Short e/o are eV/oV, long e/o are e/o; ళ = lY, ఱ = rY; anusvara M, visarga H, ardhanusvara z."""
V = {'అ': 'a', 'ఆ': 'A', 'ఇ': 'i', 'ఈ': 'I', 'ఉ': 'u', 'ఊ': 'U', 'ఋ': 'q', 'ౠ': 'Q', 'ఎ': 'eV', 'ఏ': 'e', 'ఐ': 'E',
     'ఒ': 'oV', 'ఓ': 'o', 'ఔ': 'O'}
M = {'ా': 'A', 'ి': 'i', 'ీ': 'I', 'ు': 'u', 'ూ': 'U', 'ృ': 'q', 'ౄ': 'Q', 'ె': 'eV', 'ే': 'e', 'ై': 'E', 'ొ': 'oV',
     'ో': 'o', 'ౌ': 'O'}
C = {'క': 'k', 'ఖ': 'K', 'గ': 'g', 'ఘ': 'G', 'ఙ': 'f', 'చ': 'c', 'ఛ': 'C', 'జ': 'j', 'ఝ': 'J', 'ఞ': 'F', 'ట': 't', 'ఠ': 'T',
     'డ': 'd', 'ఢ': 'D', 'ణ': 'N', 'త': 'w', 'థ': 'W', 'ద': 'x', 'ధ': 'X', 'న': 'n', 'ప': 'p', 'ఫ': 'P', 'బ': 'b', 'భ': 'B',
     'మ': 'm', 'య': 'y', 'ర': 'r', 'ల': 'l', 'వ': 'v', 'శ': 'S', 'ష': 'R', 'స': 's', 'హ': 'h', 'ళ': 'lY', 'ఱ': 'rY'}
S = {'ం': 'M', 'ః': 'H', 'ఁ': 'z'}
VIRAMA = '్'


def te2wx(text):
    out = []; chars = list(text); i = 0
    while i < len(chars):
        ch = chars[i]
        if ch in C:
            nxt = chars[i + 1] if i + 1 < len(chars) else ''
            if nxt == VIRAMA: out.append(C[ch]); i += 2; continue
            if nxt in M: out.append(C[ch] + M[nxt]); i += 2; continue
            out.append(C[ch] + 'a'); i += 1; continue
        if ch in V: out.append(V[ch])
        elif ch in S: out.append(S[ch])
        elif ch in (' ', '‌', '‍', '-'): pass          # multiword roots are written as one WX word
        else: out.append(ch)
        i += 1
    return ''.join(out)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    from wx2te import wx2te
    for w in ['దర్శనం', 'వెళ్ళు', 'పోటెత్తు', 'భగవంతుడు', 'దీపాల వరుస', 'చెయ్యి', 'గంగమ్మ', 'అమ్మవారు', 'ఒడ్డు']:
        x = te2wx(w); print(w, x, wx2te(x), 'OK' if wx2te(x) == w.replace(' ', '') else 'MISMATCH')
