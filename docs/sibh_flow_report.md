# River, dam and transfer stations from SIBH

Generated 2026-11-16 11:10 UTC by `pipeline/sibh_flow.py` from hourly means downloaded by `pipeline/fetch_sibh_flow.py` (SP Águas SIBH public API, retrieved 2026-11-16). Observed records only: no model is run and no model output is used. SIBH's telemetric records are unconsolidated.

A day is the local calendar day (UTC-3) and is kept for a variable if at least 18 of its 24 hourly means are valid; the daily value is their mean. Levels more than 50 m from the station's median in the same datum, and discharges below 0 or above 1000 m3/s, are rejected; nothing else is filtered or filled. Rules: docstring of `pipeline/sibh_flow.py`.

## 1. What each station holds

`value` is a water level, in cm (in metres at the six Sabesp codes with 8-digit prefixes: 238, 349, 358, 360, 361, 362), shown here in m. A level above 100 m is a water-surface elevation; below, it is stage above the gauge zero. `read_value` is discharge in m3/s, which SIBH gives from the level with a rating curve. Where SIBH publishes a curve in force, the curve is applied to every hourly level and compared with SIBH's discharge (tolerance 2% or 0.005 m3/s). Median level is over kept days in the latest datum.

| SIBH id | Code | Operator | Name | Group | Feed | Level | Median level (m) | Days with level | Days with discharge | Rating curves published | Hours the curve reproduces | Flat days (level / discharge) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1397 | 3E-121 | SP ÁGUAS | Nazaré Paulista (Atibainha Montante) | upstream | WS-ANA | stage | 0.87 | 3155 | 3154 | 0 | not checkable | 0 / 0 |
| 1430 | 3E-122 | SP ÁGUAS | Piracaia (Cachoeira Montante) | upstream | WS-ANA | stage | 0.74 | 1760 | 1760 | 7 | 111 of 1434 | 0 / 0 |
| 30862 | 3E-116 | SP ÁGUAS | Piracaia (Captação) | below_dam | WS-SAISP | stage | 1.83 | 5871 | 3435 | 23 | 33774 of 41120 | 3 / 3 |
| 832 | 3E-145 | SP ÁGUAS | Piracaia (Rio Cachoeira - Centro) | below_dam |  | stage | 1.12 | 1642 | 1636 | 0 | not checkable | 0 / 0 |
| 10 | 1001177 | SABESP | Piracaia (Barragem Cachoeira) | dam |  | elevation | 816.00 | 4308 | 0 | 0 | not checkable | 0 / 0 |
| 362 | 62666010 | SABESP | SB-CA-BRC Barragem Cachoeira | dam |  | elevation | 815.69 | 179 | 0 | 0 | not checkable | 1 / 0 |
| 22 | 1000718 | SABESP | Piracaia (Canal Jusante Cachoeira) | dam |  | stage to 2022-10-30, then elevation | 791.90 | 1839 | 0 | 0 | not checkable | 0 / 0 |
| 14 | 1001178 | SABESP | Nazaré Paulista (Barragem Atibainha) | dam |  | elevation | 783.64 | 6141 | 0 | 0 | not checkable | 86 / 0 |
| 360 | 62653510 | SABESP | SB-CA-BRA BARRAGEM ATIBAINHA | dam |  | elevation | 783.20 | 176 | 0 | 0 | not checkable | 9 / 0 |
| 20 | 1000721 | SAISP | Nazaré Paulista (Canal Jusante Atibainha) | dam |  | stage to 2022-10-30, then elevation | 759.00 | 3218 | 0 | 0 | not checkable | 0 / 0 |
| 12 | 616 | SAISP | Piracaia (Desemboque do Túnel - 6) | transfer |  | stage | 0.88 | 3008 | 2954 | 0 | not checkable | 0 / 0 |
| 361 | 62654600 | SABESP | Piracaia (SB-CA-DBT6 Desemboque do Túnel 6) | transfer |  | stage | 1.05 | 184 | 184 | 0 | not checkable | 66 / 0 |
| 16 | 746 | SABESP | Nazaré Paulista (Emboque do Tunel 5) | transfer |  | elevation | 783.18 | 2853 | 0 | 0 | not checkable | 0 / 0 |
| 18 | 309 | SABESP | Nazaré Paulista (Desemboque do Tunel 5) | transfer |  | stage | 0.94 | 4453 | 4445 | 0 | not checkable | 1 / 0 |
| 349 | 62344010 | SABESP | SB-CA-DBT5 Desemboque Túnel 5 | transfer |  | stage | 1.06 | 184 | 184 | 0 | not checkable | 0 / 0 |
| 6 | 619 | SABESP | Joanópolis (Barragem Jacareí - Túnel 7 / Vargem) | transfer |  | elevation | 834.03 | 4346 | 0 | 0 | not checkable | 28 / 0 |
| 358 | 62596270 | SABESP | SB-CA-BJC-T7 Emboque Túnel 7 | transfer |  | elevation | 837.71 | 187 | 0 | 0 | not checkable | 1 / 0 |
| 35414 | 734 | SABESP | Transposição Jaguari (PS) - Atibainha (SC) | transfer |  | none |  | 0 | 0 | 0 | not checkable | 0 / 0 |
| 35609 | 1000734 | SABESP | Santa Isabel (Transposição Jaguari (PS) - Atibainha (SC)) | transfer |  | none |  | 0 | 0 | 0 | not checkable | 0 / 0 |
| 35354 | 637 | SABESP | Santa Isabel (EEAB Paraíba do Sul - Atibainha) | transfer |  | elevation | 617.00 | 508 | 0 | 0 | not checkable | 0 / 0 |
| 238 | 58115900 | SABESP | Santa Isabel (SB-CA-EAB-Elevatória Paraíba do Sul) | transfer |  | elevation | 620.79 | 175 | 0 | 0 | not checkable | 0 / 0 |

Feed is the station record's `data_source` in SIBH (WS-ANA: taken from ANA's web service; blank: not stated).

Hours rejected by the validity rule (level / discharge): 22: 1 / 0; 20: 1 / 0; 16: 1 / 0.

Level hours dropped because most of that day was in the other datum: 22: 7; 20: 7; 18: 1. Days dropped because their datum has fewer than 30 days at the station: none.

### Rating in use, by year

Discharge SIBH gives at two fixed stages of each station, its median and 90th-percentile stage over the whole record (median over the hours within 1 cm of that stage; blank if fewer than 5 hours). A change between years is a change of rating curve, not of flow. Nothing is fitted.

| Station | Stage (m) | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | 0.87 |  |  |  |  |  |  |  |  | 1.70 | 1.70 | 1.70 | 1.70 | 1.71 | 1.90 | 2.09 | 2.09 | 2.11 |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | 1.26 |  |  |  |  |  |  |  |  | 2.79 | 2.80 | 2.80 | 2.80 | 2.80 | 2.81 | 3.94 | 3.93 | 3.95 |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | 0.74 |  |  |  |  |  | 3.47 |  |  |  |  |  |  | 3.61 | 3.61 | 3.62 | 3.62 | 3.60 |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | 1.22 |  |  |  |  |  |  | 8.70 |  | 9.19 |  |  | 8.63 | 9.11 | 9.11 | 9.14 | 9.08 | 9.10 |
| 30862 3E-116 (Piracaia (Captação)) | 1.67 | 2.39 | 2.39 | 1.69 | 1.68 | 1.68 | 1.04 | 0.57 | 0.57 | 0.57 | 0.57 |  |  |  |  |  |  |  |
| 30862 3E-116 (Piracaia (Captação)) | 2.37 |  |  |  |  |  | 2.24 | 1.81 | 1.81 | 1.81 | 1.81 |  |  |  |  |  |  |  |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1.12 |  |  |  |  |  |  |  |  | 2.31 |  |  | 4.18 | 4.17 | 4.20 | 4.19 | 4.20 | 4.09 |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1.27 |  |  |  |  |  |  |  |  |  |  |  | 5.42 | 5.33 | 5.34 | 5.32 | 5.29 | 5.29 |
| 12 616 (Piracaia (Desemboque do Túnel - 6)) | 0.88 |  |  |  |  |  | 15.50 |  |  |  | 15.40 | 15.70 | 15.72 | 15.55 | 15.58 | 15.55 | 15.49 | 15.42 |
| 12 616 (Piracaia (Desemboque do Túnel - 6)) | 1.20 |  |  |  |  |  |  |  | 26.59 |  |  | 26.03 |  |  | 26.10 | 26.01 | 26.14 | 25.88 |
| 361 62654600 (Piracaia (SB-CA-DBT6 Desemboque do Túnel 6)) | 1.05 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 20.73 |  |  |
| 361 62654600 (Piracaia (SB-CA-DBT6 Desemboque do Túnel 6)) | 1.13 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 23.23 | 23.39 |  |
| 18 309 (Nazaré Paulista (Desemboque do Tunel 5)) | 0.94 |  |  |  |  | 20.31 |  | 20.31 | 20.11 | 20.34 | 20.31 | 20.38 | 20.29 | 20.25 | 20.33 | 20.41 | 20.31 | 20.35 |
| 18 309 (Nazaré Paulista (Desemboque do Tunel 5)) | 1.10 |  |  |  |  |  |  | 27.42 | 27.06 | 27.02 | 27.03 | 27.20 | 27.06 |  | 27.27 | 27.26 | 27.35 | 27.40 |
| 349 62344010 (SB-CA-DBT5 Desemboque Túnel 5) | 1.06 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 25.74 | 25.63 |  |
| 349 62344010 (SB-CA-DBT5 Desemboque Túnel 5) | 1.17 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 30.73 | 30.59 |  |

## 2a. Days kept per year: discharge (m3/s)

| Station | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 285 | 365 | 366 | 364 | 362 | 364 | 366 | 364 | 318 |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | 0 | 0 | 0 | 0 | 0 | 14 | 15 | 0 | 30 | 0 | 0 | 24 | 363 | 365 | 270 | 360 | 319 |
| 30862 3E-116 (Piracaia (Captação)) | 314 | 312 | 272 | 357 | 365 | 365 | 362 | 364 | 360 | 356 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 0 | 0 | 24 | 365 | 365 | 183 | 358 | 318 |
| 12 616 (Piracaia (Desemboque do Túnel - 6)) | 0 | 0 | 0 | 0 | 0 | 201 | 0 | 136 | 0 | 130 | 353 | 364 | 362 | 364 | 364 | 361 | 319 |
| 361 62654600 (Piracaia (SB-CA-DBT6 Desemboque do Túnel 6)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 172 | 12 | 0 |
| 18 309 (Nazaré Paulista (Desemboque do Tunel 5)) | 0 | 0 | 0 | 0 | 130 | 360 | 366 | 363 | 365 | 365 | 363 | 359 | 364 | 365 | 362 | 364 | 319 |
| 349 62344010 (SB-CA-DBT5 Desemboque Túnel 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 172 | 12 | 0 |

No discharge on any kept day: 10 1001177 (Piracaia (Barragem Cachoeira)); 362 62666010 (SB-CA-BRC Barragem Cachoeira); 22 1000718 (Piracaia (Canal Jusante Cachoeira)); 14 1001178 (Nazaré Paulista (Barragem Atibainha)); 360 62653510 (SB-CA-BRA BARRAGEM ATIBAINHA); 20 1000721 (Nazaré Paulista (Canal Jusante Atibainha)); 16 746 (Nazaré Paulista (Emboque do Tunel 5)); 6 619 (Joanópolis (Barragem Jacareí - Túnel 7 / Vargem)); 358 62596270 (SB-CA-BJC-T7 Emboque Túnel 7); 35414 734 (Transposição Jaguari (PS) - Atibainha (SC)); 35609 1000734 (Santa Isabel (Transposição Jaguari (PS) - Atibainha (SC))); 35354 637 (Santa Isabel (EEAB Paraíba do Sul - Atibainha)); 238 58115900 (Santa Isabel (SB-CA-EAB-Elevatória Paraíba do Sul)).

## 2b. Days kept per year: level

| Station | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 285 | 365 | 366 | 364 | 363 | 364 | 366 | 364 | 318 |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | 0 | 0 | 0 | 0 | 0 | 14 | 15 | 0 | 30 | 0 | 0 | 24 | 363 | 365 | 270 | 360 | 319 |
| 30862 3E-116 (Piracaia (Captação)) | 314 | 312 | 272 | 357 | 365 | 365 | 362 | 364 | 360 | 356 | 359 | 362 | 362 | 350 | 354 | 341 | 316 |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 0 | 0 | 24 | 365 | 365 | 183 | 358 | 319 |
| 10 1001177 (Piracaia (Barragem Cachoeira)) | 15 | 0 | 0 | 15 | 0 | 364 | 366 | 364 | 365 | 365 | 366 | 364 | 362 | 357 | 327 | 359 | 319 |
| 362 62666010 (SB-CA-BRC Barragem Cachoeira) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 168 | 11 | 0 |
| 22 1000718 (Piracaia (Canal Jusante Cachoeira)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 30 | 0 | 0 | 24 | 364 | 365 | 358 | 364 | 319 |
| 14 1001178 (Nazaré Paulista (Barragem Atibainha)) | 359 | 359 | 361 | 365 | 365 | 365 | 366 | 364 | 365 | 365 | 366 | 365 | 365 | 363 | 364 | 365 | 319 |
| 360 62653510 (SB-CA-BRA BARRAGEM ATIBAINHA) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 168 | 8 | 0 |
| 20 1000721 (Nazaré Paulista (Canal Jusante Atibainha)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 348 | 365 | 366 | 362 | 364 | 365 | 364 | 365 | 319 |
| 12 616 (Piracaia (Desemboque do Túnel - 6)) | 0 | 0 | 0 | 0 | 0 | 251 | 0 | 136 | 0 | 130 | 353 | 365 | 363 | 364 | 366 | 361 | 319 |
| 361 62654600 (Piracaia (SB-CA-DBT6 Desemboque do Túnel 6)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 172 | 12 | 0 |
| 16 746 (Nazaré Paulista (Emboque do Tunel 5)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 343 | 366 | 365 | 365 | 365 | 366 | 365 | 318 |
| 18 309 (Nazaré Paulista (Desemboque do Tunel 5)) | 0 | 0 | 0 | 0 | 131 | 362 | 366 | 363 | 365 | 365 | 365 | 359 | 365 | 365 | 364 | 364 | 319 |
| 349 62344010 (SB-CA-DBT5 Desemboque Túnel 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 172 | 12 | 0 |
| 6 619 (Joanópolis (Barragem Jacareí - Túnel 7 / Vargem)) | 0 | 0 | 0 | 0 | 14 | 363 | 366 | 365 | 364 | 365 | 366 | 363 | 365 | 365 | 366 | 365 | 319 |
| 358 62596270 (SB-CA-BJC-T7 Emboque Túnel 7) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 175 | 12 | 0 |
| 35354 637 (Santa Isabel (EEAB Paraíba do Sul - Atibainha)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 198 | 310 |
| 238 58115900 (Santa Isabel (SB-CA-EAB-Elevatória Paraíba do Sul)) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 163 | 12 | 0 |

No level on any kept day: 35414 734 (Transposição Jaguari (PS) - Atibainha (SC)); 35609 1000734 (Santa Isabel (Transposição Jaguari (PS) - Atibainha (SC))).

## 3. Gauges above the reservoirs against SAR inflow

SAR's inflow is the operator's figure, computed from the reservoir balance. The gauges measure the river above the lake and drain only part of each catchment (SIBH gives no drainage area for either), so their flow should be smaller than the inflow and move with it. Correlation is shown with SAR's day shifted by one day either way.

| Gauge | Reservoir | Days compared | Gauge mean (m3/s) | SAR inflow mean (m3/s) | Ratio | r, SAR day D-1 | r, same day | r, SAR day D+1 | r, 7-day means |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | atibainha | 3152 | 2.28 | 3.34 | 0.68 | 0.53 | 0.76 | 0.59 | 0.88 |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | cachoeira | 1758 | 4.97 | 4.49 | 1.11 | 0.68 | 0.88 | 0.84 | 0.94 |

Ratio of gauge to SAR inflow by year (sums over days both have):

| Gauge | Reservoir | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | atibainha |  |  |  | 0.83 (285) | 0.61 (365) | 0.75 (366) | 0.77 (364) | 0.56 (362) | 0.60 (364) | 0.81 (366) | 0.81 (364) | 0.61 (316) |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | cachoeira |  |  |  | 1.07 (30) |  |  |  | 0.91 (363) | 1.22 (365) | 1.39 (270) | 1.50 (360) | 0.98 (317) |

### Noise on rainless days

On days with less than 1 mm of catchment rain on the day and the 5 days before, flow should only recede. Rises on such days, and successive daily changes that cancel (negative lag-1 correlation), indicate measurement noise; the implied noise is the square root of minus the lag-1 covariance of daily changes. Same days for both records.

| Record | Rainless days compared | Median flow (m3/s) | Days on which flow rises | Lag-1 correlation of changes | Implied noise (m3/s) |
| --- | --- | --- | --- | --- | --- |
| 1397 3E-121 (Nazaré Paulista (Atibainha Montante)) | 842 | 1.54 | 26% | 0.07 | 0.00 |
| SAR inflow, atibainha (same days) | 842 | 0.93 | 52% | -0.57 | 0.79 |
| 1430 3E-122 (Piracaia (Cachoeira Montante)) | 427 | 2.69 | 18% | -0.24 | 0.06 |
| SAR inflow, cachoeira (same days) | 427 | 1.17 | 45% | -0.39 | 0.54 |

## 4. Below Cachoeira dam: the reported release against measured river flow

ANA gauge 62665000 (Piracaia, 431 km2) reads more than 0.5 m3/s below Cachoeira's reported release on 50 days or more in 2010, 2017, 2018, 2019, 2022, 2025 (`docs/data_quality_report.md`). Two SIBH stations on the same river give two more measurements: 3E-116 about 1 km below the dam, and 3E-145 in Piracaia beside ANA's gauge.

| Pair | Days compared | Mean of first (m3/s) | Mean of second (m3/s) | Median first minus second | r, same day | r, second shifted D+1 |
| --- | --- | --- | --- | --- | --- | --- |
| 30862 3E-116 (Piracaia (Captação)) vs SAR release, Cachoeira | 3435 | 1.48 | 1.54 | 0.19 | 0.80 | 0.80 |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) vs SAR release, Cachoeira | 1634 | 3.78 | 3.23 | 0.35 | 0.91 | 0.87 |
| 30862 3E-116 (Piracaia (Captação)) vs ANA 62665000 Piracaia | 3435 | 1.48 | 2.53 | -1.12 | 0.49 | 0.49 |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) vs ANA 62665000 Piracaia | 1430 | 3.79 | 3.88 | -0.05 | 0.80 | 0.73 |
| ANA 62665000 Piracaia vs SAR release, Cachoeira | 14843 | 3.86 | 2.75 | 0.95 | 0.90 | 0.89 |
| 30862 3E-116 (Piracaia (Captação)) vs 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 23 | too few days | | | | |

### Days on which a gauge reads more than 0.5 m3/s below the release

Same-day comparison. Each cell: shortfall days / days compared.

| Year | ANA 62665000 | 30862 3E-116 (Piracaia (Captação)) | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | ANA and SIBH 3E-145 both short, of days all three exist |
| --- | --- | --- | --- | --- |
| 2014 | 4 / 365 | 11 / 365 |  |  |
| 2015 | 4 / 365 | 1 / 365 |  |  |
| 2016 | 0 / 366 | 6 / 362 |  |  |
| 2017 | 102 / 365 | 72 / 364 |  |  |
| 2018 | 101 / 365 | 235 / 360 | 0 / 23 | 0 of 1 ANA-short days (23 days) |
| 2019 | 59 / 365 | 286 / 356 |  |  |
| 2020 | 4 / 366 | 6 / 8 |  |  |
| 2021 | 24 / 365 |  | 0 / 24 | 0 of 0 ANA-short days (24 days) |
| 2022 | 98 / 365 |  | 108 / 365 | 45 of 98 ANA-short days (365 days) |
| 2023 | 43 / 326 |  | 4 / 365 | 4 of 43 ANA-short days (326 days) |
| 2024 | 15 / 366 |  | 1 / 183 | 1 of 12 ANA-short days (183 days) |
| 2025 | 89 / 365 |  | 13 / 358 | 12 of 87 ANA-short days (358 days) |
| 2026 | 20 / 151 |  | 18 / 316 | 11 of 20 ANA-short days (151 days) |

### Water level below the dam on shortfall days

A water level needs no rating curve. Stations 22 and 20 read the channel just below each dam (from 2024); 3E-116 reads the river about 1 km below Cachoeira dam (from 2010); 3E-145 reads it in Piracaia beside ANA's gauge. Days are grouped by year and by reported release. Within a group, a lower level on the days the river gauge reads short means less water was in the river than on other days with the same reported release; an unchanged level means the river gauge alone is low. The scale column gives, for comparison, the median difference in level between reported releases 0.5 m3/s apart in the same year. No rating is fitted.

| Level station | Shortfall judged by | Days with level, release and gauge | Spearman: level vs release | Spearman: level vs gauge | Groups with at least 3 short and 3 other days | Short days in those groups | Median level difference, short minus other (cm) | Groups where short days are lower | Scale: level per 0.5 m3/s of release (cm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 22 1000718 (Piracaia (Canal Jusante Cachoeira)), stage | ANA 62665000 | 372 | 0.94 | 0.68 | 4 | 88 | 0.0 | 2 of 4 | 2.8 |
| 22 1000718 (Piracaia (Canal Jusante Cachoeira)), stage | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 342 | 0.93 | 0.85 | 1 | 105 | -0.2 | 1 of 1 | 2.8 |
| 22 1000718 (Piracaia (Canal Jusante Cachoeira)), elevation | ANA 62665000 | 1260 | 0.95 | 0.76 | 12 | 124 | -0.2 | 7 of 12 | 4.4 |
| 22 1000718 (Piracaia (Canal Jusante Cachoeira)), elevation | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1275 | 0.95 | 0.90 | 2 | 10 | -2.0 | 2 of 2 | 4.4 |
| 30862 3E-116 (Piracaia (Captação)), stage | ANA 62665000 | 5667 | 0.81 | 0.51 | 36 | 445 | -1.2 | 26 of 36 | 12.2 |
| 30862 3E-116 (Piracaia (Captação)), stage | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1582 | 0.92 | 0.94 | 3 | 112 | -8.1 | 3 of 3 | 9.3 |
| 832 3E-145 (Piracaia (Rio Cachoeira - Centro)), stage | ANA 62665000 | 1435 | 0.90 | 0.82 | 16 | 211 | -0.9 | 10 of 16 | 3.8 |
| 20 1000721 (Nazaré Paulista (Canal Jusante Atibainha)), stage | ANA 62662000 | 1739 | 0.95 | 0.86 | 11 | 195 | -7.4 | 9 of 11 | 5.1 |
| 20 1000721 (Nazaré Paulista (Canal Jusante Atibainha)), elevation | ANA 62662000 | 61 | 0.86 | 0.71 | 0 | 0 |  | 0 of 0 |  |

By year, for 3E-116 just below the dam (same test; blank where no group has 3 short and 3 other days):

| Year | Shortfall judged by | Groups | Short days | Median level difference, short minus other (cm) | Scale (cm per 0.5 m3/s) |
| --- | --- | --- | --- | --- | --- |
| 2010 | ANA 62665000 | 4 | 50 | -3.5 | 23.0 |
| 2011 | ANA 62665000 | 3 | 32 | -14.8 | 18.2 |
| 2012 | ANA 62665000 | 1 | 19 | 1.6 | 22.1 |
| 2013 | ANA 62665000 | 1 | 17 | -0.3 | 21.6 |
| 2014 | ANA 62665000 | 1 | 3 | -7.7 | 13.0 |
| 2015 | ANA 62665000 | 1 | 3 | 6.1 | 19.4 |
| 2017 | ANA 62665000 | 1 | 3 | -4.4 | 10.4 |
| 2018 | ANA 62665000 | 5 | 88 | -1.0 | 15.0 |
| 2019 | ANA 62665000 | 1 | 5 | -1.5 | 17.4 |
| 2021 | ANA 62665000 | 2 | 17 | 2.3 | 8.1 |
| 2022 | ANA 62665000 | 4 | 89 | -0.2 | 4.0 |
| 2022 | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1 | 102 | -8.1 | 4.0 |
| 2023 | ANA 62665000 | 4 | 35 | -4.1 | 8.8 |
| 2023 | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1 | 4 | -9.8 | 8.7 |
| 2024 | ANA 62665000 | 1 | 8 | 15.1 | 10.0 |
| 2025 | ANA 62665000 | 5 | 68 | -0.5 | 10.2 |
| 2026 | ANA 62665000 | 2 | 8 | -1.3 | 7.2 |
| 2026 | 832 3E-145 (Piracaia (Rio Cachoeira - Centro)) | 1 | 6 | -5.3 | 7.0 |

## 5. Reservoir levels against SAR

SAR gives one level per reservoir per day. Compared here with the station's mean level over the hour from 07:00 to 08:00 local time (10:00 UTC) on the same day, and with its daily mean.

| Station | Reservoir | Days compared | Median station minus SAR, 07:00 (m) | Within 5 cm, 07:00 | Median station minus SAR, daily mean (m) | Within 5 cm, daily mean |
| --- | --- | --- | --- | --- | --- | --- |
| 10 1001177 (Piracaia (Barragem Cachoeira)) | cachoeira | 4310 | 0.000 | 99% | 0.000 | 94% |
| 362 62666010 (SB-CA-BRC Barragem Cachoeira) | cachoeira | 189 | 0.000 | 99% | 0.001 | 90% |
| 14 1001178 (Nazaré Paulista (Barragem Atibainha)) | atibainha | 6146 | -0.000 | 98% | -0.000 | 98% |
| 360 62653510 (SB-CA-BRA BARRAGEM ATIBAINHA) | atibainha | 189 | 0.000 | 100% | 0.000 | 100% |
| 16 746 (Nazaré Paulista (Emboque do Tunel 5)) | atibainha | 2851 | -0.124 | 8% | -0.118 | 8% |
| 6 619 (Joanópolis (Barragem Jacareí - Túnel 7 / Vargem)) | jaguari_jacarei | 4344 | -0.009 | 54% | -0.009 | 54% |
| 358 62596270 (SB-CA-BJC-T7 Emboque Túnel 7) | jaguari_jacarei | 197 | -0.092 | 9% | -0.100 | 7% |

## 6. Tunnel flows against the reservoir balance

For each reservoir SAR's records imply a net outflow that is neither the reported release nor storage change: inflow minus release minus storage change (from the previous day's volume, as in `process.py`). For Cachoeira that should be Tunnel 6 to Atibainha, less Tunnel 7 water received from Jaguari-Jacareí; for Atibainha, Tunnel 5 to Paiva Castro less Tunnel 6 received (and any Paraíba do Sul water, if SAR does not count it as inflow). Evaporation and rain on the lake are ignored. An accounting check, not a model.

| Balance residual | Measured | SAR shift used | Days compared | Residual mean (m3/s) | Measured mean (m3/s) | Median residual minus measured | Days within 1 m3/s | r, SAR day D-1 | r, same day | r, SAR day D+1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cachoeira | 12 616 (Piracaia (Desemboque do Túnel - 6)) | +0 day | 2952 | 0.67 | 15.85 | -16.01 | 18% | 0.01 | 0.03 | 0.01 |
| Cachoeira | 361 62654600 (Piracaia (SB-CA-DBT6 Desemboque do Túnel 6)) | +0 day | 184 | -2.38 | 19.08 | -23.74 | 9% | 0.17 | 0.25 | 0.22 |
| Atibainha | 18 309 (Nazaré Paulista (Desemboque do Tunel 5)) | +1 day | 4442 | 1.08 | 19.90 | -19.87 | 2% | -0.02 | 0.14 | 0.17 |
| Atibainha | 349 62344010 (SB-CA-DBT5 Desemboque Túnel 5) | +1 day | 184 | -1.66 | 25.21 | -28.28 | 0% | -0.05 | 0.22 | 0.28 |
| Atibainha | 309 minus 616 | +1 day | 2939 | 0.41 | 4.85 | -5.26 | 21% | 0.49 | 0.72 | 0.82 |
| Atibainha | 309 minus 62654600 | +1 day | 183 | -1.65 | 6.13 | -7.68 | 1% | 0.28 | 0.71 | 0.93 |
| Atibainha | 62344010 minus 616 | +1 day | 184 | -1.66 | 6.12 | -7.70 | 1% | 0.28 | 0.71 | 0.93 |
| Atibainha | 62344010 minus 62654600 | +1 day | 183 | -1.65 | 6.13 | -7.68 | 1% | 0.28 | 0.71 | 0.93 |

Means, the median difference and the share within 1 m3/s are for the SAR shift with the highest correlation (a shift of -1 pairs the station's day D with SAR's day D-1).

### What the measured tunnels add to SAR's balance, by year

Atibainha: Tunnel 5 minus Tunnel 6 (309 minus 616), minus SAR's residual. If SAR's inflow is the natural inflow and nothing else enters, this is zero; a positive value is water entering Atibainha that SAR's inflow does not count. Cachoeira: Tunnel 6 minus SAR's residual, which is what Tunnel 7 must have delivered from Jaguari-Jacareí if SAR's inflow is natural (no Tunnel 7 flow is published). SAR shifted +1 day, the shift with the highest correlation above. Derived, not measured.

| Year | Atibainha days | Atibainha: median (m3/s) | Atibainha: mean (m3/s) | Cachoeira days | Cachoeira, implied Tunnel 7: median (m3/s) | Cachoeira, implied Tunnel 7: mean (m3/s) |
| --- | --- | --- | --- | --- | --- | --- |
| 2015 | 199 | -0.32 | -0.34 | 201 | 12.87 | 12.77 |
| 2017 | 136 | -0.01 | 0.75 | 136 | 16.76 | 14.70 |
| 2019 | 130 | 5.12 | 5.38 | 130 | 14.74 | 16.14 |
| 2020 | 350 | 6.37 | 5.17 | 353 | 17.91 | 14.80 |
| 2021 | 359 | 7.59 | 6.56 | 364 | 16.05 | 13.63 |
| 2022 | 362 | 6.89 | 5.14 | 362 | 14.86 | 10.60 |
| 2023 | 364 | -0.02 | -0.16 | 364 | 16.75 | 16.33 |
| 2024 | 362 | 6.02 | 4.76 | 364 | 26.69 | 21.79 |
| 2025 | 361 | 6.44 | 6.12 | 361 | 25.08 | 20.55 |
| 2026 | 316 | 7.69 | 7.67 | 316 | 1.43 | 8.91 |

## 7. Sites recorded under two codes

| Site | First code | Second code | Variable | Days both have | Median first minus second | r |
| --- | --- | --- | --- | --- | --- | --- |
| Cachoeira dam | 1001177 | 62666010 | level | 179 | 0.000 | 1.000 |
| Atibainha dam | 1001178 | 62653510 | level | 176 | -0.000 | 1.000 |
| Tunnel 6 outlet: Cachoeira to Atibainha | 616 | 62654600 | level | 184 | -0.000 | 1.000 |
| Tunnel 6 outlet: Cachoeira to Atibainha | 616 | 62654600 | discharge | 184 | -0.000 | 1.000 |
| Tunnel 5 outlet: Atibainha to Paiva Castro (Juqueri) | 309 | 62344010 | level | 184 | 0.000 | 1.000 |
| Tunnel 5 outlet: Atibainha to Paiva Castro (Juqueri) | 309 | 62344010 | discharge | 184 | -0.000 | 1.000 |
| Tunnel 7 at Jacareí dam: Jaguari-Jacareí to Cachoeira | 619 | 62596270 | level | 187 | 0.000 | 1.000 |
| Paraíba do Sul pumping station (EEAB) to Atibainha | 637 | 58115900 | level | 0 | | |
