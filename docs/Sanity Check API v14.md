1) Crea Campaign (payload valido)

Esempio con:

Q1: free_text

Q2: scale

Q3: numeric

finestra chiamate 09:00–20:00 (orario locale)

RESP=$(curl -s -X POST "$BASE/api/campaigns" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Campaign",
    "description": "Local test",
    "language": "it",
    "intro_script": "Ciao, sono l’assistente. Vuoi dare il consenso a partecipare a un breve sondaggio?",
    "question_1_text": "Come stai oggi?",
    "question_1_type": "free_text",
    "question_2_text": "Da 1 a 5 quanto sei soddisfatto?",
    "question_2_type": "scale",
    "question_3_text": "Quanti caffè bevi al giorno?",
    "question_3_type": "numeric",
    "completion_message": "Grazie, abbiamo finito.",
    "max_attempts": 2,
    "retry_interval_minutes": 30,
    "allowed_call_start_local": "09:00",
    "allowed_call_end_local": "20:00"
  }')
echo "$RESP"


📌 Se vuoi estrarre l’id al volo e hai jq:

CAMPAIGN_ID=$(echo "$RESP" | jq -r '.id')
echo "$CAMPAIGN_ID"


Se non hai jq: copia l’id dalla risposta JSON


2) Import contatti da CSV (REQ-006) — endpoint giusto

Quello corretto è multipart su:

POST /api/campaigns/{campaign_id}/contacts/upload

curl -s -X POST "$BASE/api/campaigns/$CAMPAIGN_ID/contacts/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@contacts.csv;type=text/csv"
  
  
  ---
  Ok, qui non c’è nessun “mistero”: **la tua pipeline sta facendo esattamente quello che può fare senza eventi Twilio**.

* Lo **scheduler** crea il **call_attempt** (tu lo vedi: attempt_number=1, started_at valorizzato).
* Il **contact** passa a **in_progress** perché è stato “claimato”.
* **Senza webhook/eventi del provider** (answered/busy/no-answer/completed/failed + outcome) **nessuno lo riporta a not_reached/refused/completed**, quindi **resta in_progress**.
* La tua `_requeue_stale_in_progress(...)` è l’unica cosa che può “ripulire” dopo kill/crash; se la metti a 0 minuti lo rimette subito not_reached (come hai visto).

Quindi sì: **è coerente che con worker=2 vedi 1 attempt e l’altro worker standby** (advisory lock leader). E non vedi nuovi attempts finché non c’è:

* un altro contatto eleggibile, oppure
* lo stesso contatto torna eleggibile (es. da in_progress → not_reached via webhook o requeue).

---

## Come ricreare Campaign + Contacts e renderle “attive” (curl corretti)

Dai log e dalla VALIDATION_ERROR, **il tuo modello Campaign richiede SEMPRE**:

* `question_1_*`, `question_2_*`, `question_3_*`
* `allowed_call_start_local`, `allowed_call_end_local`
* `question_*_type` ∈ **free_text | numeric | scale** (non “scale_1_5”)

### 0) Variabili ambiente

```bash
export BASE="http://127.0.0.1:8880"
export TOKEN="...il tuo bearer..."
```

---

## 1) Crea la campaign (DRAFT)

> Nota: “scale” è il tipo giusto per 1–5.

```bash
curl -s -X POST "$BASE/api/campaigns" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Campaign",
    "description": "Local test",
    "language": "it",
    "intro_script": "Ciao, sono l’assistente. Vuoi dare il consenso a partecipare a un breve sondaggio?",
    "question_1_text": "Come stai oggi?",
    "question_1_type": "free_text",
    "question_2_text": "Da 1 a 5 quanto sei soddisfatto?",
    "question_2_type": "scale",
    "question_3_text": "Vuoi aggiungere un commento finale?",
    "question_3_type": "free_text",
    "completion_message": "Grazie, abbiamo finito.",
    "max_attempts": 2,
    "retry_interval_minutes": 30,
    "allowed_call_start_local": "09:00",
    "allowed_call_end_local": "21:00"
  }'
```

👉 Dall’output prendi l’`id` della campaign (salvalo):

```bash
export CAMPAIGN_ID="...uuid..."
```

---

## 2) Import contatti da CSV (REQ-006) — endpoint giusto

Quello corretto è **multipart** su:

**POST** `/api/campaigns/{campaign_id}/contacts/upload`

```bash
curl -s -X POST "$BASE/api/campaigns/$CAMPAIGN_ID/contacts/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@contacts.csv;type=text/csv"
```

**Se prima vedevi “Method not allowed” o “Not found”**: molto probabilmente stavi chiamando un path diverso (tipo `/api/contacts/upload` o simili). Questo è quello previsto dai docs REQ-006.

---

## 3) Metti la campaign in RUNNING (REQ-004)

Da docs: endpoint è:

**POST** `/api/campaigns/{id}/status`

Il body non è mostrato esplicitamente nei docs che mi hai caricato, quindi ti do le **2 varianti più comuni** (una delle due sarà quella giusta; l’altra ti darà validation error e capisci al volo il campo richiesto).

### Variante A (più comune)

```bash
curl -s -X POST "$BASE/api/campaigns/$CAMPAIGN_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"running"}'
```

### Variante B

```bash
curl -s -X POST "$BASE/api/campaigns/$CAMPAIGN_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_status":"running"}'
```

---

# Collaudo guidato “READY FOR TWILIO LIVE” (step-by-step, DB + API)

## Prerequisiti

1. App spenta:

```bash
pkill -f uvicorn || true
```

2. DB pulito (se vuoi davvero “da zero”, fai TRUNCATE a mano, oppure ricrea campaign+contacts via API come sopra).
   Minimo indispensabile: assicurati che **non ci siano contatti in_progress** rimasti “orfani”.

---

## Test 1 — Boot + leader lock

Avvio con 2 worker:

```bash
PYTHONPATH=src uvicorn app.main:app --host 127.0.0.1 --port 8880 --log-level info --workers 2
```

Atteso nei log:

* un worker: `Scheduler leader lock acquired`
* l’altro: `Scheduler leader lock busy; standby`

✅ Questo conferma che **non farai doppie chiamate** lato scheduler.

---

## Test 2 — Scheduler crea un attempt

Dopo 1 tick, verifica DB:

### 2A Contatti eleggibili (non in_progress)

```sql
SELECT state, count(*) FROM contacts WHERE campaign_id='<CAMPAIGN_ID>' GROUP BY state;
```

### 2B Attempt creati

```sql
SELECT contact_id, attempt_number, call_id, started_at, outcome
FROM call_attempts
WHERE campaign_id='<CAMPAIGN_ID>'
ORDER BY started_at DESC
LIMIT 10;
```

Atteso:

* per almeno 1 contatto: `attempt_number=1`, `started_at` valorizzato
* `provider_call_id` vuoto (finché non integri Twilio reale)
* `outcome` vuoto (finché non arrivano webhook o un “simulatore evento”)

---

## Test 3 — Perché resta in_progress (e perché è OK)

Se non arrivano eventi provider:

```sql
SELECT id, state, attempts_count, last_attempt_at, updated_at
FROM contacts
WHERE campaign_id='<CAMPAIGN_ID>'
ORDER BY updated_at DESC
LIMIT 20;
```

Atteso:

* almeno un contatto in `in_progress`

✅ Non è bug: è “in attesa di esito chiamata”.

---

## Test 4 — Recovery after kill (il tuo Step 6)

Tu hai visto che resta `in_progress` dopo kill. È normale **se la requeue considera stale_after_minutes > 0**.

**Test definitivo recovery:**

1. kill app
2. aspetta più di `stale_after_minutes` (oppure metti temporaneamente `requeue_stale_minutes=0` come hai fatto)
3. riavvia
4. verifica che il contatto torni `not_reached`

Query:

```sql
SELECT id, state, attempts_count, last_attempt_at, updated_at
FROM contacts
WHERE campaign_id='<CAMPAIGN_ID>'
ORDER BY updated_at DESC
LIMIT 20;
```

Atteso:

* `not_reached` dopo requeue

---

# Cosa manca per “READY FOR TWILIO LIVE + consenso via voce + LLM loop”

Non è più “scheduler/DB”: lì sei a posto.

Manca la catena runtime:

1. **Twilio outbound**: `provider_call_id` valorizzato e salvato su `call_attempts`
2. **Webhook handler** che riceve gli eventi Twilio e aggiorna:

   * `call_attempts.answered_at / ended_at / outcome / provider_raw_status`
   * `contacts.state` (not_reached / refused / completed)
3. **Voice bot**:

   * TTS (o TwiML <Say>) per intro e domande
   * STT (o DTMF se fallback) per riconoscere “consenso”
   * Persistenza “conversation turns” (oggi non la stai ancora scrivendo: hai solo attempts + contact state)
4. **LLM loop** (orchestrator QA):

   * decide prossima domanda / ripetizione / fallback
   * salva transcript + risposte strutturate
5. Regole business:

   * se no-consenso ⇒ `refused` immediato (anche se max_attempts non raggiunto)
   * busy/no-answer ⇒ `not_reached` e retry quando vuoi (scheduler)

---

## Risposta secca alla tua domanda: “Consolidiamo ora o durante Twilio?”

**Consolidiamo QUI** solo ciò che è “meccanica” e ti evita rework dopo:

* Scheduler claim/idempotenza/unique constraint ✅
* Recovery post-crash (requeue stale) ✅
* Stati minimi contact/attempt coerenti ✅

Poi l’integrazione Twilio la fai sopra senza toccare più queste fondamenta.

---

Se vuoi, nel prossimo messaggio ti preparo **un README “produzione” + uno script di collaudo guidato** (solo testo + comandi, niente patch), ma dimmi prima: vuoi che il collaudo sia **solo DB+API** (senza Twilio), oppure includa già i “mock webhook calls” (sempre senza Twilio reale) per simulare gli esiti?
