# Dati social 081comedy

Questo repository contiene **un solo file**: `dati-social.json`, con i numeri pubblici
dei canali social di [081comedy](https://www.eikonaproduzioni.it) — follower, visualizzazioni,
persone raggiunte.

Serve a una cosa sola: il sito eikonaproduzioni.it lo rilegge una volta al giorno e aggiorna
i numeri da solo, senza che nessuno debba mettere le mani nei file PHP.

**Sono tutti dati già pubblici**, gli stessi che chiunque può leggere sui profili social.
Nessuna credenziale, nessun token, nessun dato personale.

Il file è generato da `genera_dati_sito.py` (Eikona Produzioni, non incluso qui) a partire
dalle API di Meta, Google e TikTok. Non va modificato a mano: al giro successivo le modifiche
verrebbero sovrascritte.

Regola di redazione: **solo dati misurati**. Nessuna stima, nessun valore "deduplicato"
cross-platform — l'incrocio fra piattaforme non lo misura nessuna API.
