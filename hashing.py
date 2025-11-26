import hashlib
def sha256_text(t): return "0x"+hashlib.sha256(t.encode()).hexdigest()
def sha256_bytes(b): return "0x"+hashlib.sha256(b).hexdigest()
def build_report(resps):
    lines=["CIS IG1 Maturity Report","",""]
    total=0
    for qid in sorted(resps):
        ans=resps[qid]['answer']
        lines.append(f"Q{qid}: {ans}")
        total+= {'Implementado':1,'Parcial':0.5,'Nao implementado':0}[ans]
    pct=round(100*total/len(resps),2)
    lines.insert(1,f"Score: {pct}%")
    return "\n".join(lines)
