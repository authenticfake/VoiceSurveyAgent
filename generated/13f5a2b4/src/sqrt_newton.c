/*
 * sqrt_newton.c
 *
 * Calcolo della radice quadrata di un numero reale usando SOLO:
 *   - somma (+)
 *   - sottrazione (-)
 *   - moltiplicazione (*)
 *   - divisione (/)
 *
 * Algoritmo: Metodo di Newton-Raphson (metodo di Erone)
 *   x_{n+1} = 0.5 * (x_n + a / x_n)
 *
 * Note importanti:
 * - Per a < 0 non esiste radice quadrata reale: ritorniamo NaN.
 * - Per a = 0, sqrt(0) = 0.
 * - La convergenza è in genere molto rapida.
 *
 * Compilazione:
 *   gcc -O2 -Wall -Wextra -std=c11 sqrt_newton.c -o sqrt_demo
 */

#include <stdio.h>
#include <float.h>

/*
 * abs_double
 *
 * Valore assoluto senza usare funzioni di libreria (solo confronti e -).
 */
static double abs_double(double x) {
    return (x < 0.0) ? (0.0 - x) : x;
}

/*
 * is_nan
 *
 * Rilevamento NaN senza usare math.h:
 * per IEEE-754, NaN != NaN.
 */
static int is_nan(double x) {
    return x != x;
}

/*
 * sqrt_newton
 *
 * Calcola sqrt(a) per a >= 0 usando Newton.
 *
 * Parametri:
 *   a            numero reale di cui calcolare la radice quadrata
 *   eps          tolleranza (es: 1e-12). Arresto quando l'errore relativo/assoluto è piccolo.
 *   max_iters    massimo numero di iterazioni
 *
 * Ritorno:
 *   - sqrt(a) (approssimata)
 *   - NaN se a < 0
 */
static double sqrt_newton(double a, double eps, int max_iters) {
    if (a < 0.0) {
        /* Genera NaN in modo portabile senza math.h */
        double z = 0.0;
        return z / z;
    }
    if (a == 0.0) {
        return 0.0;
    }

    /* Scelta di un guess iniziale semplice e stabile.
     * Per a >= 1, partire da a; per 0<a<1, partire da 1.
     */
    double x = (a >= 1.0) ? a : 1.0;

    /* Iterazione di Newton */
    for (int i = 0; i < max_iters; ++i) {
        /* x_{n+1} = 0.5 * (x + a/x) */
        double x_next = 0.5 * (x + (a / x));

        /* Criterio di arresto:
         * controlliamo la differenza tra iterazioni.
         */
        double diff = abs_double(x_next - x);

        /* Tolleranza mista (assoluta + relativa) */
        double tol = eps * (1.0 + abs_double(x_next));
        if (diff <= tol) {
            return x_next;
        }

        x = x_next;
    }

    /* Se non converge entro max_iters, ritorna l'ultima stima */
    return x;
}

int main(void) {
    double tests[] = {0.0, 2.0, 9.0, 0.25, 1e-12, 1e12, -4.0};
    int n = (int)(sizeof(tests) / sizeof(tests[0]));

    const double eps = 1e-12;
    const int max_iters = 100;

    for (int i = 0; i < n; ++i) {
        double a = tests[i];
        double r = sqrt_newton(a, eps, max_iters);

        if (is_nan(r)) {
            printf("a = %g -> sqrt(a) non reale (NaN)\n", a);
        } else {
            /* Verifica semplice: r*r dovrebbe essere ~ a */
            double check = r * r;
            printf("a = %g -> sqrt(a) ~= %.17g (r*r=%.17g)\n", a, r, check);
        }
    }

    return 0;
}
