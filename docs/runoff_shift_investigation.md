# Why the runoff share changes: investigation

Generated 2026-11-14 12:43 UTC by `pipeline/investigate_runoff.py`. Water years run October to September. Rain is the audited catchment rain; evaporation demand is Oudin PET from reanalysis temperature. No model calibration is involved.

Areas: **Cachoeira** and **Atibainha** inflows are computed by the operator from a reservoir balance. **Middle** is the 351 km2 between the two dams and the Atibaia gauge, measured only by three river gauges (rain gauges used: Batatuba, Atibaia (ANA), Nazaré Paulista (SP Águas), Atibaia (SP Águas), Piracaia (ANA), Piracaia (SP Águas), Ribeirão Acima, Nazaré Paulista (ANA), Crioulos, Morro Grande).

## T1. Runoff share by period: operator inflows against the independent area

| Period | Area | Water years | Rain (mm) | PET (mm) | Runoff (mm) | Runoff share |
| --- | --- | --- | --- | --- | --- | --- |
| 1986–2001 | cachoeira | 16 | 1685 | 1216 | 537 | 0.32 |
| 1986–2001 | atibainha | 16 | 1481 | 1215 | 616 | 0.42 |
| 1986–2001 | middle | 6 | 1544 | 1204 | 549 | 0.36 |
| 2004–2013 | cachoeira | 10 | 1548 | 1228 | 474 | 0.31 |
| 2004–2013 | atibainha | 10 | 1621 | 1226 | 516 | 0.32 |
| 2004–2013 | middle | 5 | 1596 | 1230 | 530 | 0.33 |
| 2014–2016 | cachoeira | 3 | 1407 | 1278 | 274 | 0.19 |
| 2014–2016 | atibainha | 3 | 1314 | 1277 | 264 | 0.20 |
| 2014–2016 | middle | 3 | 1338 | 1276 | 229 | 0.17 |
| 2017–2021 | cachoeira | 5 | 1351 | 1268 | 338 | 0.25 |
| 2017–2021 | atibainha | 5 | 1236 | 1265 | 295 | 0.24 |
| 2017–2021 | middle | 4 | 1346 | 1267 | 394 | 0.29 |
| 2022–2025 | cachoeira | 4 | 1436 | 1284 | 317 | 0.22 |
| 2022–2025 | atibainha | 4 | 1243 | 1283 | 364 | 0.29 |
| 2022–2025 | middle | 1 | 1178 | 1242 | 333 | 0.28 |

## T2. How much does climate alone explain?

Fu's Budyko curve, one parameter fitted to each area's 2004–2013 mean, then applied to the other periods' rain and PET. The last column is observed minus predicted runoff, as a share of observed.

| Area | Fitted w | Period | Observed share | Climate-only prediction | Observed runoff (mm) | Predicted (mm) | Unexplained |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cachoeira | 3.73 | 1986–2001 | 0.32 | 0.35 | 537 | 591 | -10% |
| cachoeira | 3.73 | 2004–2013 | 0.31 | 0.31 | 474 | 474 | -0% |
| cachoeira | 3.73 | 2014–2016 | 0.19 | 0.24 | 274 | 344 | -25% |
| cachoeira | 3.73 | 2017–2021 | 0.25 | 0.23 | 338 | 312 | +8% |
| cachoeira | 3.73 | 2022–2025 | 0.22 | 0.25 | 317 | 361 | -14% |
| atibainha | 3.95 | 1986–2001 | 0.42 | 0.28 | 616 | 414 | +33% |
| atibainha | 3.95 | 2004–2013 | 0.32 | 0.32 | 516 | 516 | +0% |
| atibainha | 3.95 | 2014–2016 | 0.20 | 0.20 | 264 | 268 | -1% |
| atibainha | 3.95 | 2017–2021 | 0.24 | 0.18 | 295 | 226 | +23% |
| atibainha | 3.95 | 2022–2025 | 0.29 | 0.18 | 364 | 223 | +39% |
| middle | 3.47 | 1986–2001 | 0.36 | 0.33 | 549 | 504 | +8% |
| middle | 3.47 | 2004–2013 | 0.33 | 0.33 | 530 | 530 | -0% |
| middle | 3.47 | 2014–2016 | 0.17 | 0.24 | 229 | 320 | -40% |
| middle | 3.47 | 2017–2021 | 0.29 | 0.24 | 394 | 330 | +16% |
| middle | 3.47 | 2022–2025 | 0.28 | 0.20 | 333 | 236 | +29% |

## T3. Catchment memory: yearly runoff share against rain

| Area | Water years | Correlation with same-year rain | With mean rain of the previous two years | With the year (trend) |
| --- | --- | --- | --- | --- |
| cachoeira | 41 | 0.56 | 0.39 | -0.51 |
| atibainha | 41 | 0.22 | 0.22 | -0.68 |
| middle | 20 | 0.45 | 0.37 | -0.44 |

## T4. Atibainha inflow relative to Cachoeira inflow

If water from the Paraíba do Sul link (operating since 2018) were counted as Atibainha inflow, this ratio would rise from 2018.

| Period | Days | Mean Cachoeira inflow (m3/s) | Mean Atibainha inflow (m3/s) | Ratio |
| --- | --- | --- | --- | --- |
| 1986–2001 | 5844 | 6.69 | 6.12 | 0.91 |
| 2004–2013 | 3653 | 5.89 | 5.08 | 0.86 |
| 2014–2017 | 1461 | 3.60 | 2.79 | 0.78 |
| 2018–2021 | 1461 | 4.12 | 2.78 | 0.68 |
| 2022–2026 | 1778 | 4.30 | 3.89 | 0.90 |

## Water-year table

| Water year | Cachoeira rain | runoff | share | Atibainha rain | runoff | share | Middle rain | runoff | share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1985 | 1682 | 545 | 0.32 | 1447 | 531 | 0.37 | 1271 | 490 | 0.39 |
| 1986 | 1438 | 368 | 0.26 | 1247 | 502 | 0.40 | 1255 | 374 | 0.30 |
| 1987 | 2111 | 701 | 0.33 | 1792 | 725 | 0.40 | 1780 | 648 | 0.36 |
| 1988 | 1848 | 711 | 0.38 | 1652 | 744 | 0.45 | 1674 | 678 | 0.40 |
| 1989 | 1931 | 638 | 0.33 | 1895 | 714 | 0.38 | 1776 | 569 | 0.32 |
| 1990 | 1645 | 468 | 0.28 | 1315 | 578 | 0.44 | 1333 | 428 | 0.32 |
| 1991 | 2104 | 662 | 0.31 | 1469 | 708 | 0.48 | 1443 | 597 | 0.41 |
| 1992 | 1435 | 356 | 0.25 | 1527 | 507 | 0.33 |  |  |  |
| 1993 | 1656 | 544 | 0.33 | 1608 | 606 | 0.38 |  |  |  |
| 1994 | 1235 | 387 | 0.31 | 1203 | 457 | 0.38 |  |  |  |
| 1995 | 1990 | 706 | 0.35 | 1646 | 727 | 0.44 |  |  |  |
| 1996 | 1873 | 725 | 0.39 | 1565 | 993 | 0.63 |  |  |  |
| 1997 | 1520 | 515 | 0.34 | 1403 | 640 | 0.46 |  |  |  |
| 1998 | 1544 | 461 | 0.30 | 1290 | 637 | 0.49 |  |  |  |
| 1999 | 1783 | 684 | 0.38 | 1431 | 533 | 0.37 |  |  |  |
| 2000 | 1336 | 355 | 0.27 | 1202 | 371 | 0.31 |  |  |  |
| 2001 | 1507 | 311 | 0.21 | 1444 | 407 | 0.28 |  |  |  |
| 2002 | 1398 | 362 | 0.26 | 1576 | 498 | 0.32 |  |  |  |
| 2003 | 1092 | 274 | 0.25 | 1187 | 373 | 0.31 |  |  |  |
| 2004 | 1540 | 392 | 0.25 | 1504 | 395 | 0.26 |  |  |  |
| 2005 | 1612 | 431 | 0.27 | 1397 | 484 | 0.35 |  |  |  |
| 2006 | 1496 | 424 | 0.28 | 1424 | 478 | 0.34 |  |  |  |
| 2007 | 1155 | 310 | 0.27 | 1184 | 439 | 0.37 |  |  |  |
| 2008 | 1518 | 461 | 0.30 | 1574 | 509 | 0.32 |  |  |  |
| 2009 | 1746 | 589 | 0.34 | 1913 | 544 | 0.28 | 1688 | 415 | 0.25 |
| 2010 | 1746 | 712 | 0.41 | 1896 | 772 | 0.41 | 1782 | 897 | 0.50 |
| 2011 | 1680 | 659 | 0.39 | 1819 | 637 | 0.35 | 1506 | 665 | 0.44 |
| 2012 | 1606 | 374 | 0.23 | 1823 | 477 | 0.26 | 1538 | 397 | 0.26 |
| 2013 | 1383 | 385 | 0.28 | 1674 | 430 | 0.26 | 1467 | 277 | 0.19 |
| 2014 | 1047 | 216 | 0.21 | 977 | 192 | 0.20 | 938 | 95 | 0.10 |
| 2015 | 1532 | 202 | 0.13 | 1204 | 208 | 0.17 | 1219 | 168 | 0.14 |
| 2016 | 1641 | 404 | 0.25 | 1762 | 392 | 0.22 | 1857 | 425 | 0.23 |
| 2017 | 1511 | 358 | 0.24 | 1504 | 340 | 0.23 | 1467 | 424 | 0.29 |
| 2018 | 1203 | 289 | 0.24 | 993 | 255 | 0.26 |  |  |  |
| 2019 | 1585 | 388 | 0.25 | 1521 | 361 | 0.24 | 1525 | 477 | 0.31 |
| 2020 | 1126 | 360 | 0.32 | 1169 | 255 | 0.22 | 1177 | 307 | 0.26 |
| 2021 | 1332 | 296 | 0.22 | 994 | 265 | 0.27 | 1217 | 367 | 0.30 |
| 2022 | 1447 | 364 | 0.25 | 1149 | 341 | 0.30 | 1178 | 333 | 0.28 |
| 2023 | 1650 | 413 | 0.25 | 1492 | 453 | 0.30 |  |  |  |
| 2024 | 1378 | 276 | 0.20 | 1061 | 344 | 0.32 |  |  |  |
| 2025 | 1269 | 214 | 0.17 | 1272 | 318 | 0.25 |  |  |  |
