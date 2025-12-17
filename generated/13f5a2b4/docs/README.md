# Funzione radice quadrata (solo +, -, *, /)

Questo mini-progetto contiene una funzione per calcolare la radice quadrata di un numero reale **senza usare** funzioni matematiche predefinite (come `sqrt`) e utilizzando **solo** operazioni di:

- somma `+`
- sottrazione `-`
- moltiplicazione `*`
- divisione `/`

L’algoritmo utilizzato è il **metodo di Newton-Raphson** (anche noto come metodo di Erone), che converge rapidamente.

## Come funziona (Newton/Erone)

Per calcolare \(\sqrt{a}\), si risolve l’equazione:

\[ x^2 - a = 0 \]

Con Newton:

\[ x_{n+1} = x_n - \frac{x_n^2 - a}{2x_n} = \frac{1}{2}\left(x_n + \frac{a}{x_n}\right) \]

Questa formula usa solo `+`, `/`, `*`.

## Requisiti/Comportamento

- Input: numero reale `a` (double).
- Se `a < 0`: non esiste radice quadrata reale → ritorna `NaN`.
- Se `a == 0`: ritorna `0`.
- Tolleranza configurabile (`eps`).
- Numero massimo di iterazioni configurabile.

## File inclusi

- `src/sqrt_newton.c` — implementazione + documentazione in commenti.
- `assets/sqrt_illustration.svg` — immagine vettoriale che rappresenta la radice quadrata.

## Compilazione ed esecuzione (esempio)

```bash
gcc -O2 -Wall -Wextra -std=c11 src/sqrt_newton.c -o sqrt_demo
./sqrt_demo
```

## Esempio di output atteso

Il programma di demo stampa alcune radici e un controllo del quadrato.

## Licenza

Libero utilizzo a scopo didattico.
