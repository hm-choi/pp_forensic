"""Bootstrapping and Chebyshev evaluation counters.

Counts only the calls this framework makes explicitly. Bootstrapping performed
inside hn.math.approx.evaluate_chebyshev_expansion is handled by the SDK and is
not observable from Python, so the Chebyshev evaluation count is reported
alongside as the unit of depth restoration.
"""

explicit_bootstraps = 0
chebyshev_evals = 0


def reset():
    global explicit_bootstraps, chebyshev_evals
    explicit_bootstraps = 0
    chebyshev_evals = 0


def snapshot():
    return explicit_bootstraps, chebyshev_evals


def add_bootstrap(n=1):
    global explicit_bootstraps
    explicit_bootstraps += n


def add_chebyshev(n=1):
    global chebyshev_evals
    chebyshev_evals += n