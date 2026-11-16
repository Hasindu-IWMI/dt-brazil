"""GR4J daily rainfall-runoff model (Perrin, Michel & Andréassian, 2003,
J. Hydrol. 279, 275-289). Four parameters:

  x1  production store capacity (mm)
  x2  groundwater exchange coefficient (mm/day)
  x3  routing store capacity (mm)
  x4  unit hydrograph time base (days)

Passing x5 (dimensionless exchange threshold) switches to GR5J (Le Moine,
2008): the groundwater exchange becomes x2 * (R/x3 - x5).

Inputs are daily rain and potential evapotranspiration in mm; output is
runoff in mm/day. Pure Python, no dependencies.
"""
import math


def _ordinates(x4):
    n1 = int(math.ceil(x4))
    n2 = int(math.ceil(2.0 * x4))

    def ss1(t):
        if t <= 0:
            return 0.0
        return (t / x4) ** 2.5 if t < x4 else 1.0

    def ss2(t):
        if t <= 0:
            return 0.0
        if t <= x4:
            return 0.5 * (t / x4) ** 2.5
        return 1.0 - 0.5 * (2.0 - t / x4) ** 2.5 if t < 2.0 * x4 else 1.0

    o1 = [ss1(i + 1) - ss1(i) for i in range(n1)]
    o2 = [ss2(i + 1) - ss2(i) for i in range(n2)]
    return o1, o2


def run(rain, pet, x1, x2, x3, x4, x5=None, s0=0.6, r0=0.7):
    """Return simulated runoff (mm/day) for each day. Missing inputs must be
    filled by the caller; this function does no gap handling."""
    o1, o2 = _ordinates(x4)
    n1, n2 = len(o1), len(o2)
    u1 = [0.0] * n1
    u2 = [0.0] * n2
    s = s0 * x1
    r = r0 * x3
    out = [0.0] * len(rain)
    tanh = math.tanh
    for t in range(len(rain)):
        p = rain[t]
        e = pet[t]
        if p >= e:
            pn = p - e
            ws = pn / x1
            if ws > 13.0:
                ws = 13.0
            tw = tanh(ws)
            sr = s / x1
            ps = x1 * (1.0 - sr * sr) * tw / (1.0 + sr * tw)
            s += ps
        else:
            en = e - p
            pn = 0.0
            ps = 0.0
            ws = en / x1
            if ws > 13.0:
                ws = 13.0
            tw = tanh(ws)
            sr = s / x1
            s -= s * (2.0 - sr) * tw / (1.0 + (1.0 - sr) * tw)
        sr = s / x1
        perc = s * (1.0 - (1.0 + (4.0 / 9.0 * sr) ** 4) ** -0.25)
        s -= perc
        pr = perc + (pn - ps)
        a = 0.9 * pr
        for k in range(n1 - 1):
            u1[k] = u1[k + 1] + o1[k] * a
        u1[n1 - 1] = o1[n1 - 1] * a
        b = 0.1 * pr
        for k in range(n2 - 1):
            u2[k] = u2[k + 1] + o2[k] * b
        u2[n2 - 1] = o2[n2 - 1] * b
        # GR4J: F = x2 (R/x3)^3.5.  GR5J (Le Moine 2008): F = x2 (R/x3 - x5),
        # so the exchange changes sign with the filling of the routing store.
        f = x2 * (r / x3) ** 3.5 if x5 is None else x2 * (r / x3 - x5)
        r = r + u1[0] + f
        if r < 0.0:
            r = 0.0
        qr = r * (1.0 - (1.0 + (r / x3) ** 4) ** -0.25)
        r -= qr
        qd = u2[0] + f
        if qd < 0.0:
            qd = 0.0
        out[t] = qr + qd
    return out
