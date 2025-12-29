
# ✅ CHECKLIST “READY FOR TWILIO LIVE”

*VoiceSurveyAgent*

---

## 🔒 GATE 0 — PRECONDIZIONI (OBBLIGATORIO)

### G0.1 — Codice allineato

* [ ] Tutti i sorgenti usati sono **in `src/`**
* [ ] Nessun file `incoming_*` o KIT residuo
* [ ] Branch pulito (o commit coerente)

**Check**

```bash
git status
```

**Esito atteso**

* working tree clean

---

### G0.2 — Ambiente

* [ ] PostgreSQL attivo
* [ ] Variabili env settate
* [ ] Nessun Redis richiesto

**Check**

```bash
env | grep TWILIO
env | grep DATABASE
```

---

## 🗄️ GATE 1 — DATABASE CONSISTENCY (APP SPENTA)

👉 **APP SPENTA**

### G1.1 — DB pulito (scenario minimo)

* [ ] 1 campaign `status=running`
* [ ] ≥1 contact valido
* [ ] `call_attempts` coerenti

**Query**

```sql
SELECT id, status FROM campaigns;
SELECT id, state, attempts_count FROM contacts;
SELECT contact_id, attempt_number FROM call_attempts;
```

**Esito atteso**

* `attempts_count` = max(call_attempts.attempt_number)
* nessun doppione `(contact_id, attempt_number)`

---

### G1.2 — Vincoli critici

* [ ] UNIQUE(contact_id, attempt_number) presente

**Query**

```sql
\d call_attempts
```

---

## 🚀 GATE 2 — AVVIO APPLICAZIONE (NO TWILIO)

### G2.1 — Avvio single worker

```bash
PYTHONPATH=src uvicorn app.main:app --port 8880 --workers 1
```

**Check log**

* [ ] `Application starting`
* [ ] `Scheduler enabled`
* [ ] `Scheduler leader lock acquired`

❌ NON devono apparire:

* stacktrace
* retry loop infiniti
* deadlock

---

### G2.2 — Scheduler tick

Attendi 1 ciclo.

**Check**

```sql
SELECT * FROM call_attempts ORDER BY started_at DESC;
```

**Esito atteso**

* 1 nuovo call_attempt
* `contacts.state = in_progress`
* `attempts_count` incrementato

---

## 🧵 GATE 3 — CONCURRENCY SAFETY

### G3.1 — Avvio multi-worker

```bash
PYTHONPATH=src uvicorn app.main:app --port 8880 --workers 2
```

**Check log**

* 1 processo:

  * `Scheduler leader lock acquired`
* 1 processo:

  * `Scheduler leader lock busy; standby`

---

### G3.2 — No duplicazioni

Attendi 2–3 cicli.

**Query**

```sql
SELECT contact_id, attempt_number, COUNT(*)
FROM call_attempts
GROUP BY contact_id, attempt_number
HAVING COUNT(*) > 1;
```

**Esito atteso**

* ZERO righe

✅ Se passa → scheduler è **production-safe**

---

## 📡 GATE 4 — TELEPHONY MOCK → TWILIO DRY-RUN

### G4.1 — Provider Mock

* [ ] Telephony provider = mock
* [ ] Nessuna chiamata reale

**Check log**

* `Creating telephony provider`
* `initiate_call` chiamato **dopo commit DB**

---

### G4.2 — Callback endpoint vivo

```bash
curl -X POST http://localhost:8880/webhooks/telephony/events
```

**Esito**

* 200 / 204
* nessun errore

---

## ☎️ GATE 5 — TWILIO LIVE (DRY)

⚠️ **Solo ORA**

### G5.1 — Config Twilio

* [ ] SID
* [ ] Auth Token
* [ ] From number
* [ ] Callback HTTPS pubblico

---

### G5.2 — Prima chiamata reale (1 contatto)

* [ ] 1 contact solo
* [ ] 1 campaign

**Check DB**

```sql
SELECT * FROM call_attempts ORDER BY started_at DESC LIMIT 1;
```

**Esito**

* provider_call_id valorizzato
* answered_at / ended_at coerenti

---

## 🗣️ GATE 6 — VOICE FLOW

### G6.1 — Consenso

* [ ] Intro riprodotto
* [ ] Consenso acquisito
* [ ] Rifiuto → refused

---

### G6.2 — Q&A

* [ ] Domande sequenziali
* [ ] Repeat gestito
* [ ] Skip gestito

---

## 🧾 GATE 7 — PERSISTENZA FINALE

### G7.1 — SurveyResponse

```sql
SELECT * FROM survey_responses;
```

* [ ] 1 record
* [ ] link a call_attempt
* [ ] risposte complete

---

### G7.2 — Stato finale contatto

```sql
SELECT state FROM contacts;
```

**Esito**

* `completed` OR `refused`

---

## 🧯 GATE 8 — RECOVERY / RESTART

### G8.1 — Restart app

* [ ] App stop
* [ ] App start

**Check**

* Nessun contatto bloccato
* In-progress “stale” correttamente requeued

---

## 🎯 GATE 9 — GO / NO-GO

✅ **READY FOR TWILIO LIVE SE E SOLO SE:**

* Tutti i gate precedenti sono PASS
* Nessuna duplicazione DB
* Scheduler stabile
* Voice flow completo
* Persistenza verificata

❌ In caso contrario:

* STOP
* patch puntuale
* ripeti gate fallito

---

## 📌 OUTPUT FINALE ATTESO

Al termine devi poter dire:

> “Con N workers, PostgreSQL advisory lock, e Twilio live,
> il sistema è deterministico, idempotente e production-ready.”

