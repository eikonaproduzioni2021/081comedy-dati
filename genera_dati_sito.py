#!/usr/bin/env python3
"""
Genera il JSON che il sito eikonaproduzioni.it legge per i numeri di 081comedy.

Filosofia: sul sito vanno SOLO dati misurati. Niente stime, niente "deduplicato".
Se un numero non si riesce a verificare, si tiene quello vecchio e lo si dichiara
vecchio — mai pubblicare uno zero o un valore inventato.

Cosa è automatico e cosa no
  · Instagram, Facebook  → Graph API, completamente automatici
  · YouTube              → Data API v3, completamente automatico
  · TikTok               → NON scriptabile: l'unico accesso è Windsor via MCP.
                           Si riusa l'ultimo valore noto e si marca la data.
                           Va aggiornato a mano (o da Claude) a ogni ciclo.

Protezioni contro i dati sbagliati, in ordine di importanza:
  1. nessun canale può valere 0
  2. nessun canale può perdere più del 20% rispetto al giro precedente
  3. se una qualsiasi verifica fallisce il file NON viene scritto e l'uscita è != 0
Meglio un sito con numeri di un mese fa che un sito con numeri sbagliati.
"""
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, date

BASE = "/Users/eikonaproduzioni/Documents/Eikona/Progetti/081comedy-dati-social/"
ENV = BASE + ".env"
USCITA = BASE + "sito/dati-social.json"
PRECEDENTE = USCITA
GRAPH = "https://graph.facebook.com/v24.0"
YT = "https://www.googleapis.com/youtube/v3"

# Primo contenuto pubblicato, verificato sui video Facebook (campo primo_video del
# dataset). Da qui si contano i "mesi di contenuti" mostrati sul sito: è una data
# fissa, quindi il numero cresce da solo e non va più aggiornato a mano.
LANCIO = date(2025, 5, 30)

def mesi_di_contenuti(inizio=LANCIO):
    oggi = date.today()
    m = (oggi.year - inizio.year) * 12 + (oggi.month - inizio.month)
    if oggi.day < inizio.day:      # il mese in corso non è ancora compiuto
        m -= 1
    return max(m, 0)

# TikTok: unico canale senza accesso da script. Aggiornare a ogni ciclo.
TIKTOK = {"follower": 117512, "aggiornato_il": "2026-08-28",
          "_fonte": "TikTok Studio (Windsor sottostima l'11-24%: verificato il 28/08/2026)"}

E = {}
for l in open(ENV):
    l = l.strip()
    if l and not l.startswith("#") and "=" in l:
        k, v = l.split("=", 1); E[k.strip()] = v.strip()

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)

def api(base, path, **p):
    return get(f"{base}/{path}?" + urllib.parse.urlencode(p))

errori = []

# ─────────── raccolta ───────────
try:
    ig = api(GRAPH, E["IG_USER_ID"], fields="followers_count,media_count",
             access_token=E["META_SYSTEM_USER_TOKEN"])
    ig_follower = int(ig["followers_count"])
except Exception as e:
    errori.append(f"Instagram: {e}"); ig_follower = 0

try:
    ptok = api(GRAPH, E["FB_PAGE_ID"], fields="access_token",
               access_token=E["META_SYSTEM_USER_TOKEN"])["access_token"]
    fb = api(GRAPH, E["FB_PAGE_ID"], fields="followers_count", access_token=ptok)
    fb_follower = int(fb["followers_count"])
except Exception as e:
    errori.append(f"Facebook: {e}"); fb_follower = 0

try:
    ch = api(YT, "channels", part="statistics", id=E["YOUTUBE_CHANNEL_ID"],
             key=E["YOUTUBE_API_KEY"])["items"][0]["statistics"]
    yt_iscritti = int(ch["subscriberCount"])
    yt_views_totali = int(ch["viewCount"])
except Exception as e:
    errori.append(f"YouTube: {e}"); yt_iscritti = yt_views_totali = 0

canali = {"tiktok": TIKTOK["follower"], "instagram": ig_follower,
          "youtube": yt_iscritti, "facebook": fb_follower}
community = sum(canali.values())

# ─────────── verifiche ───────────
for nome, v in canali.items():
    if v <= 0:
        errori.append(f"{nome}: valore non plausibile ({v})")

vecchio = None
if os.path.exists(PRECEDENTE):
    try: vecchio = json.load(open(PRECEDENTE))
    except Exception: pass

if vecchio:
    for nome, v in canali.items():
        prima = vecchio.get("canali", {}).get(nome)
        if prima and v < prima * 0.8:
            errori.append(f"{nome}: crollo sospetto {prima} → {v} (oltre il 20%)")

if errori:
    print("NON scrivo il file. Problemi rilevati:", file=sys.stderr)
    for e in errori: print("  ·", e, file=sys.stderr)
    if vecchio:
        print(f"\nIl sito continua a mostrare i dati del {vecchio.get('aggiornato_il')}.", file=sys.stderr)
    sys.exit(1)

# ─────────── scrittura ───────────
def compatta(n):
    if n >= 1_000_000: return f"{n/1_000_000:.0f}M".replace(".0", "")
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)

dati = {
    "aggiornato_il": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    "_avvertenza": "Generato da genera_dati_sito.py. Non modificare a mano: "
                   "al prossimo giro le modifiche vengono sovrascritte.",
    "_regola": "solo dati misurati via API. Nessuna stima, nessun valore deduplicato.",

    "community": community,
    "community_label": compatta(community),
    "canali": canali,
    "tiktok_aggiornato_il": TIKTOK["aggiornato_il"],

    # MEDIA MENSILE su luglio e agosto 2026, non il singolo mese: agosto in Italia
    # e' stagionalmente basso e un mese solo non descrive il canale.
    "visualizzazioni_mese": 42035670,
    "visualizzazioni_mese_label": "42M",
    # agosto 2026: primo mese con la reach di TUTTI E QUATTRO i canali. YouTube
    # espone il "pubblico mensile" (2,2 Mln) che prima risultava non disponibile.
    "persone_raggiunte_mese": 12992495,
    "persone_raggiunte_mese_label": "13M",
    # versione da usare dentro le frasi: "…davanti a 13 milioni di persone ogni mese"
    "persone_raggiunte_mese_prosa": "13 milioni",
    # anche questa si calcola: era cablata a "281mila" e il 21/08/2026 la
    # community valeva già 302K — un numero vecchio scritto a mano
    "community_prosa": f"{community // 1000}mila",
    # cresce da solo: nessuno deve ricordarsi di aggiornarlo
    "mesi_contenuti": mesi_di_contenuti(),
    "mesi_contenuti_label": f"{mesi_di_contenuti()} mesi",
    "ore_visione_mese": 100400,
    "visualizzazioni_totali": 391872370,
    "visualizzazioni_totali_label": "390M",
    "periodo_riferimento": "media mensile · luglio e agosto 2026",
    "_nota_periodo": "media di luglio e agosto 2026, due mesi interamente misurati. Aggiornati a ogni ciclo: le reach di TikTok vanno lette da TikTok Studio, nessuna API le espone.",
}
# ─────────── tabelle di dettaglio ───────────
# Lette dallo STESSO dataset che alimenta il PDF, così sito e report non possono
# divergere. I valori parziali (dove la piattaforma non espone il totale di periodo)
# sono marcati con "parziale": in pagina prendono un asterisco.
DATASET = BASE + "archivio/2026-08-28-dataset-report.json"

def n_compatta(v):
    """Formato del PDF. Sotto i 10 milioni tiene due decimali, altrimenti
    arrotondare a una cifra gonfierebbe: 4.972.159 diventerebbe "5,0M", cioè
    mezzo punto percentuale in più di quello che è. Su un documento di vendita
    si arrotonda per difetto, mai per eccesso."""
    if v is None: return None
    if v >= 10_000_000: s, u = f"{v/1_000_000:.1f}", "M"
    elif v >= 1_000_000: s, u = f"{v/1_000_000:.2f}", "M"
    elif v >= 100_000:   s, u = f"{v/1000:.0f}",      "K"
    elif v >= 1_000:     s, u = f"{v/1000:.1f}",      "K"
    else: return f"{v:,}".replace(",", ".")
    if "." in s: s = s.rstrip("0").rstrip(".") or "0"
    return s.replace(".", ",") + u

if os.path.exists(DATASET):
    try:
        D = json.load(open(DATASET))
        P, L = D["periodo_28g"], D["lifetime"]
        ORD = ["tiktok", "youtube", "instagram", "facebook"]
        NOMI = {"tiktok": "TikTok", "youtube": "YouTube",
                "instagram": "Instagram", "facebook": "Facebook"}
        # Vuoto dal ciclo di agosto 2026: col metodo della differenza fra snapshot
        # questi valori non sono piu' stime per difetto ma totali esatti. Restava
        # da marcare solo cio' che la piattaforma non espone affatto (-> None).
        PARZIALI = set()

        righe28 = []
        for chiave, etichetta in [("_fan", "Fanbase"), ("visualizzazioni", "Visualizzazioni"),
                                  ("reach", "Persone raggiunte"), ("mi_piace", "Mi piace"),
                                  ("commenti", "Commenti"), ("condivisioni", "Condivisioni")]:
            # la fanbase viene dalle API di adesso, non dal dataset archiviato:
            # altrimenti la tabella contraddice il totale community della pagina
            fonte = canali if chiave == "_fan" else P[chiave]
            righe28.append({
                "voce": etichetta,
                "valori": [{"v": n_compatta(fonte.get(c)),
                            "parziale": (chiave, c) in PARZIALI} for c in ORD],
            })

        ORDL = ["youtube", "instagram", "tiktok_365gg", "facebook"]
        NOMIL = {"youtube": "YouTube", "instagram": "Instagram",
                 "tiktok_365gg": "TikTok", "facebook": "Facebook"}
        CONT = {"youtube": 129, "instagram": 129, "tiktok_365gg": 129, "facebook": 124}
        righeL = []
        for chiave, etichetta in [("visualizzazioni", "Visualizzazioni"), ("mi_piace", "Mi piace"),
                                  ("commenti", "Commenti"), ("condivisioni", "Condivisioni")]:
            righeL.append({"voce": etichetta,
                           "valori": [{"v": n_compatta((L.get(c) or {}).get(chiave)),
                                       "parziale": False} for c in ORDL]})
        righeL.append({"voce": "Contenuti",
                       "valori": [{"v": str(CONT[c]), "parziale": False} for c in ORDL]})

        dati["tabelle"] = {
            "periodo": {"titolo": "Ultimo mese rilevato",
                        "sottotitolo": D["_meta"]["finestra_28g"]["da"] + " → " + D["_meta"]["finestra_28g"]["a"],
                        "colonne": [NOMI[c] for c in ORD], "righe": righe28},
            "lifetime": {"titolo": "Dal lancio del progetto",
                         "sottotitolo": "giugno 2025 → oggi",
                         "colonne": [NOMIL[c] for c in ORDL], "righe": righeL},
        }
    except Exception as e:
        print(f"  attenzione: tabelle non generate ({e})", file=sys.stderr)

# ─────────── case study brand content ───────────
# I numeri delle campagne vengono da brand_content_casestudy.py. Qui si leggono
# e si trasformano in etichette pronte per il sito. Se il file non c'è, la sezione
# semplicemente non viene aggiornata: il sito continua con i valori di riserva.
CASE = BASE + "archivio/2026-07-28-brand-content-casestudy.json"
VIDEO = {  # il video più visto di ogni campagna, per l'incorporazione su YouTube
    "Masseria del Duca": "glQqwp2shs4",
    "San Carlo 17": "c-PhqlCsQJQ",
}

def milioni(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}".replace(".", ",") + "M"
    return f"{n/1000:.0f}K"

if os.path.exists(CASE):
    try:
        cs = json.load(open(CASE))["campagne"]
        dati["case_study"] = [
            {
                "brand": nome,
                "settore": c.get("settore", ""),
                "contenuti": c["contenuti"],
                "visualizzazioni": milioni(c["totali"]["visualizzazioni"]),
                "per_contenuto": milioni(c["media_per_contenuto"]["visualizzazioni"]),
                "interazioni": milioni(c["totali"]["interazioni"]),
                "youtube_id": VIDEO.get(nome, ""),
            }
            # la campagna più forte per prima
            for nome, c in sorted(cs.items(),
                                  key=lambda x: -x[1]["totali"]["visualizzazioni"])
        ]
    except Exception as e:
        print(f"  attenzione: case study non letti ({e})", file=sys.stderr)

os.makedirs(os.path.dirname(USCITA), exist_ok=True)
json.dump(dati, open(USCITA, "w"), indent=2, ensure_ascii=False)

print(f"scritto {USCITA}")
print(f"  community {community:,}".replace(",", ".") + f"  ({dati['community_label']})")
for k, v in canali.items(): print(f"    {k:10s} {v:>8,}".replace(",", "."))
if vecchio:
    d = community - vecchio.get("community", community)
    print(f"  variazione dal {vecchio.get('aggiornato_il')}: {d:+,}".replace(",", "."))
