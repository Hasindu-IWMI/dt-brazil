# Data quality report: upper Atibaia pilot

Generated 2026-11-23 23:08 UTC by `pipeline/process.py`. Every figure is computed from the files in `data/raw`.

## 1. Reservoir records (ANA SAR, Cantareira module)

| Reservoir | First day | Last day | Days present | Days missing in span | Missing inflow | Missing release | Volume % vs hm3 mismatch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jaguari-Jacareí | 1984-01-01 | 2026-11-23 | 15668 | 0 | 0 | 0 | 6084 of 15668 days differ by more than 0.5 points |
| Cachoeira | 1984-01-01 | 2026-11-23 | 15668 | 0 | 0 | 0 | 6007 of 15668 days differ by more than 0.5 points |
| Atibainha | 1984-01-01 | 2026-11-23 | 15668 | 0 | 0 | 0 | 9587 of 15668 days differ by more than 0.5 points |
| Paiva Castro | 1984-01-01 | 2026-11-23 | 14206 | 1462 | 0 | 0 | 5843 of 14206 days differ by more than 0.5 points |

Gaps longer than 30 days: Paiva Castro, 1461 days after 1999-12-31.

The last column tests the records against themselves: reported percentage versus reported volume divided by the useful capacity ANA publishes (Jaguari-Jacareí 808.04, Cachoeira 69.65, Atibainha 96.25, Paiva Castro 7.61 hm3). A mismatch means the capacity used by the source differs from the published one for those days.

### Useful capacity in force, recovered from the records

| Reservoir | From | To | Capacity implied by the records (hm3) | Published today (hm3) |
| --- | --- | --- | --- | --- |
| Jaguari-Jacareí | 1984-01 | 1999-05 | 708.24 | 808.04 |
| Jaguari-Jacareí | 1999-06 | 1999-12 | 595.04 | 808.04 |
| Jaguari-Jacareí | 2000-01 | 2003-12 | 807.86 | 808.04 |
| Jaguari-Jacareí | 2004-01 | 2004-08 | 599.21 | 808.04 |
| Jaguari-Jacareí | 2004-09 | 2026-11 | 808.05 | 808.04 |
| Cachoeira | 1984-01 | 2003-12 | 70.34 | 69.65 |
| Cachoeira | 2004-01 | 2008-12 | 68.79 | 69.65 |
| Cachoeira | 2009-01 | 2010-03 | 70.55 | 69.65 |
| Cachoeira | 2010-04 | 2026-11 | 69.65 | 69.65 |
| Atibainha | 1984-01 | 1998-05 | 130.28 | 96.25 |
| Atibainha | 1998-06 | 1998-06 | 100.17 | 96.25 |
| Atibainha | 1998-07 | 1999-05 | 130.29 | 96.25 |
| Atibainha | 1999-06 | 2003-12 | 100.16 | 96.25 |
| Atibainha | 2004-01 | 2008-12 | 99.31 | 96.25 |
| Atibainha | 2009-01 | 2010-03 | 100.16 | 96.25 |
| Atibainha | 2010-04 | 2026-11 | 96.25 | 96.25 |
| Paiva Castro | 1984-01 | 1999-05 | 27.58 | 7.61 |
| Paiva Castro | 1999-06 | 1999-12 | 9.45 | 7.61 |
| Paiva Castro | 2004-01 | 2026-11 | 7.61 | 7.61 |

The mismatches counted in section 1 come from these capacity changes, not from bad values: using the capacity in force for each month, 0 reservoir-days remain inconsistent by more than 0.5 points. System storage is therefore expressed against the sum of the capacities in force on each day. Volumes on either side of a revision are not strictly comparable.

## 2. System storage and the implied net export

- Days with all four reservoirs reported: 14206 (1984-01-01 to 2026-11-23).
- Lowest system storage in the downloaded record: -23.3% of useful volume on 2015-02-02 (-228.7 hm3).
- Highest: 100.5% on 2010-04-08.

Implied net export, 30-day running mean, against the withdrawal limit of the band in force (the bands exist only from June 2017, so the comparison is made only from then):

| Year | Days with a 30-day mean | Median (m3/s) | 5th to 95th percentile (m3/s) | Days above the band limit | Median band limit (m3/s) |
| --- | --- | --- | --- | --- | --- |
| 1984 | 336 | 19.3 | 18.6 to 20.4 | not applicable | not applicable |
| 1985 | 365 | 20.7 | 19.3 to 23.1 | not applicable | not applicable |
| 1986 | 365 | 24.2 | 21.2 to 25.0 | not applicable | not applicable |
| 1987 | 365 | 26.4 | 24.3 to 27.3 | not applicable | not applicable |
| 1988 | 366 | 26.5 | 25.7 to 27.5 | not applicable | not applicable |
| 1989 | 365 | 27.4 | 26.0 to 28.0 | not applicable | not applicable |
| 1990 | 365 | 27.9 | 26.8 to 29.5 | not applicable | not applicable |
| 1991 | 365 | 28.7 | 28.0 to 29.2 | not applicable | not applicable |
| 1992 | 366 | 29.4 | 28.1 to 29.9 | not applicable | not applicable |
| 1993 | 364 | 30.9 | 29.9 to 31.9 | not applicable | not applicable |
| 1994 | 335 | 32.1 | 30.8 to 32.6 | not applicable | not applicable |
| 1995 | 365 | 32.1 | 31.2 to 32.8 | not applicable | not applicable |
| 1996 | 366 | 32.4 | 31.6 to 32.8 | not applicable | not applicable |
| 1997 | 365 | 32.3 | 31.7 to 32.6 | not applicable | not applicable |
| 1998 | 365 | 32.1 | 20.4 to 43.7 | not applicable | not applicable |
| 1999 | 365 | 31.8 | 30.3 to 93.8 | not applicable | not applicable |
| 2004 | 336 | 30.2 | -50.4 to 31.5 | not applicable | not applicable |
| 2005 | 365 | 31.4 | 30.0 to 32.3 | not applicable | not applicable |
| 2006 | 365 | 32.0 | 30.9 to 32.6 | not applicable | not applicable |
| 2007 | 365 | 30.4 | 29.1 to 32.0 | not applicable | not applicable |
| 2008 | 366 | 29.8 | 29.1 to 30.6 | not applicable | not applicable |
| 2009 | 365 | 30.6 | 24.5 to 31.7 | not applicable | not applicable |
| 2010 | 365 | 31.1 | 30.0 to 33.1 | not applicable | not applicable |
| 2011 | 365 | 31.5 | 30.2 to 32.6 | not applicable | not applicable |
| 2012 | 366 | 31.4 | 29.3 to 32.8 | not applicable | not applicable |
| 2013 | 365 | 31.8 | 31.1 to 32.7 | not applicable | not applicable |
| 2014 | 365 | 22.8 | 16.7 to 30.7 | not applicable | not applicable |
| 2015 | 365 | 13.3 | 12.2 to 18.1 | not applicable | not applicable |
| 2016 | 366 | 22.4 | 16.1 to 23.8 | not applicable | not applicable |
| 2017 | 365 | 24.8 | 23.9 to 25.7 | 0 of 214 | 31.0 |
| 2018 | 365 | 17.5 | 14.2 to 25.3 | 0 of 365 | 31.0 |
| 2019 | 365 | 19.0 | 16.3 to 21.0 | 0 of 365 | 31.0 |
| 2020 | 366 | 18.4 | 16.1 to 22.9 | 0 of 366 | 31.0 |
| 2021 | 365 | 13.9 | 12.1 to 21.7 | 0 of 365 | 31.0 |
| 2022 | 365 | 13.7 | 11.3 to 20.3 | 0 of 365 | 27.0 |
| 2023 | 365 | 25.0 | 20.6 to 27.7 | 0 of 365 | 33.0 |
| 2024 | 366 | 21.9 | 19.1 to 30.5 | 0 of 366 | 33.0 |
| 2025 | 365 | 24.7 | 18.6 to 29.4 | 11 of 365 | 31.0 |
| 2026 | 327 | 17.8 | 15.6 to 21.7 | 5 of 327 | 27.0 |

Reading this table: the implied export is a residual. It should sit near the real withdrawal to Sao Paulo only if SAR's inflow is the natural inflow and evaporation is small. A persistent value far above the band limit, or negative, signals that one of those assumptions fails or that a transfer is unaccounted for (the Paraiba do Sul link feeds Atibainha since 2018).

## 3. River gauges (ANA HidroSerieHistorica, daily discharge)

| Station | Name | First day | Last day | Days present | Missing in span | Consolidated share | Min | Median | Max (m3/s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 62669900 | Atibaia (SP Águas, telemetric) | 2009-01-01 | 2014-06-05 | 1962 | 20 | 0% | 2.87 | 8.63 | 112.2 |
| 62670000 | Atibaia (ANA / SGB) | 1962-01-01 | 2026-05-31 | 22764 | 763 | 97% | 1.78 | 9.89 | 132.5 |
| 62676000 | Bairro da Ponte | 1929-10-15 | 2022-12-31 | 32736 | 1310 | 0% | 1.67 | 20.08 | 241.8 |
| 62678150 | Captação de Valinhos | 2009-01-01 | 2014-06-05 | 1936 | 46 | 0% | 3.56 | 17.75 | 159.3 |
| 62680000 | Desembargador Furtado | 1944-05-27 | 2022-12-31 | 26056 | 2652 | 0% | 0.21 | 21.73 | 316.2 |
| 62690000 | Acima de Paulínia | 1947-11-15 | 2022-12-31 | 23463 | 3978 | 0% | 1.37 | 24.60 | 347.0 |
| 62665000 | Piracaia (rio da Cachoeira, 431 km2, below Cachoeira dam) | 1972-01-01 | 2026-05-31 | 19226 | 649 | 95% | 0.19 | 3.10 | 37.3 |
| 62662000 | Nazaré Paulista (rio Atibainha, 358 km2, below Atibainha dam) | 1971-01-12 | 2022-12-31 | 15216 | 3766 | 0% | 0.11 | 1.67 | 16.6 |
| 62665100 | Cravorana (rio da Cachoeira, 407 km2) | 1971-01-13 | 1992-08-31 | 7808 | 94 | 0% | 0.21 | 4.08 | 46.2 |

Placeholder values rejected (100000.0 or negative in the raw series): 62665100: 470 days, 62676000: 1310 days, 62680000: 579 days, 62690000: 214 days.

## 4. Independent cross-checks

Reservoir releases are reported by the operator through ANA; the gauges just below each dam are run by other agencies. Agreement between them is an independent test of both.

| Pair | Days compared | Median gauge minus release (m3/s) | 5th to 95th percentile | Correlation |
| --- | --- | --- | --- | --- |
| Piracaia gauge (431 km2) vs Cachoeira release (392 km2) | 14843 | 0.95 | -0.58 to 3.08 | 0.90 |
| Nazaré Paulista gauge (358 km2) vs Atibainha release (312 km2) | 10557 | 0.41 | -0.42 to 1.65 | 0.86 |

The gauges drain slightly more area than the dams (39 and 46 km2), so a small positive difference is expected. A large or negative one is a data problem to resolve before modelling.

### Where the gauge reads below the reported release

Days on which the gauge is more than 0.5 m3/s below the release, by year (days / days compared):

| Year | Piracaia vs Cachoeira | Nazaré Paulista vs Atibainha |
| --- | --- | --- |
| 1984 | 4 / 366 | 10 / 366 |
| 1985 | 10 / 365 | 11 / 365 |
| 1986 | 0 / 365 | 89 / 365 |
| 1987 | 3 / 365 | 5 / 365 |
| 1988 | 8 / 366 | 0 / 366 |
| 1989 | 6 / 365 | 1 / 365 |
| 1990 | 5 / 365 | 11 / 365 |
| 1991 | 6 / 365 | 0 / 365 |
| 1992 | 10 / 283 | 0 / 366 |
| 1993 | 0 / 365 | 0 / 256 |
| 1994 | 2 / 365 | no data |
| 1995 | 3 / 365 | no data |
| 1996 | 3 / 366 | no data |
| 1997 | 2 / 365 | no data |
| 1998 | 2 / 365 | no data |
| 1999 | 7 / 365 | no data |
| 2000 | 6 / 366 | no data |
| 2001 | 0 / 365 | no data |
| 2002 | 3 / 365 | 0 / 311 |
| 2003 | 2 / 243 | 0 / 294 |
| 2004 | 0 / 58 | 0 / 270 |
| 2005 | 0 / 365 | 0 / 68 |
| 2006 | 13 / 365 | 1 / 342 |
| 2007 | 21 / 268 | 0 / 311 |
| 2008 | 7 / 366 | 0 / 320 |
| 2009 | 4 / 365 | 0 / 365 |
| 2010 | 53 / 365 | 2 / 365 |
| 2011 | 38 / 365 | 0 / 365 |
| 2012 | 37 / 366 | 2 / 366 |
| 2013 | 28 / 365 | 0 / 365 |
| 2014 | 4 / 365 | 8 / 365 |
| 2015 | 4 / 365 | 0 / 356 |
| 2016 | 0 / 366 | 0 / 366 |
| 2017 | 102 / 365 | 37 / 363 |
| 2018 | 101 / 365 | 14 / 363 |
| 2019 | 59 / 365 | 2 / 365 |
| 2020 | 4 / 366 | 7 / 366 |
| 2021 | 24 / 365 | 150 / 365 |
| 2022 | 98 / 365 | 97 / 362 |
| 2023 | 43 / 326 | no data |
| 2024 | 15 / 366 | no data |
| 2025 | 89 / 365 | no data |
| 2026 | 20 / 151 | no data |

What was tested: shifting the release by one or two days in either direction does not improve the agreement, so travel time is not the cause. The shortfalls cluster in particular years, which points to a rating-curve or reporting problem in those periods.

The reported releases are stepped rather than continuously varying, as valve settings would be: 36% of Cachoeira values and 39% of Atibainha values are exact multiples of 0.5 m3/s, and 64% and 81% repeat the previous day. Which record is wrong on the shortfall days cannot be decided from open data; it needs the measured outflow from the operator or the rating history of the gauge.

## 5. Control point: Rio Atibaia at Atibaia (station 62670000)

- Days with gauge flow and both releases: 14729 (1984-01-01 to 2026-05-31).
- Incremental flow from the area between the dams and the gauge: median 4.84 m3/s, 5th to 95th percentile 0.51 to 19.94.
- Days with a negative incremental flow: 459 (3.1%). Negative values mean abstractions, travel-time lag or measurement error exceed local runoff.
- Reservoir releases as a share of gauge flow: median 38%.
- Days with gauge flow under 2 m3/s: 5; under 3 m3/s: 118. The operating rules cite a 2 to 3 m3/s target range at this point (Comitês PCJ status report 2020); the exact daily target in force is not in these data.

## 6. What these data cannot tell us

- Tunnel flows between reservoirs and the withdrawal to Sao Paulo are not published in SAR; only the residual in section 2 is available.
- No sub-daily river data: ANA's public telemetry returned nothing for the Atibaia gauges. Ten-minute river data exist on the Sao Paulo state network (SIBH) and have not been downloaded; its rain gauges are used, as daily totals (`pipeline/sibh_rain.py`).
- Gauge discharge comes from rating curves; their uncertainty is not published in the open service.
- Rainfall and evaporation are in the pipeline (`pipeline/forcing.py`); the inflow models built on them did not pass validation (see the README).
