# Telemetric rain gauges from SIBH

Generated 2026-11-23 23:09 UTC by `pipeline/sibh_rain.py` from hourly sums downloaded by `pipeline/fetch_sibh_rain.py` (SP Águas SIBH public API, retrieved 2026-11-23). No model output is used.

## Selection

Rain stations in SIBH within 20 km of either catchment centroid: 57. Excluded before download: 19 (ANA-owned, radar products, or conventional gauges already taken from ANA). Downloaded: 38. Sites after the co-location rule (each enters the forcing once): 23.

## Which date a day is labelled with (rule 3)

Pairs of SIBH and ANA gauges within 10 km with at least 180 shared complete days: 31. Median daily correlation: reading day 0.390; rain day 0.252. **Label used: reading day.**

In words: ANA's daily rain labelled D is the 24 hours ending at 07:00 on D, i.e. mostly rain that fell on D-1.

| SIBH gauge | ANA gauge | Distance (km) | Shared days | r, reading day | r, rain day |
| --- | --- | --- | --- | --- | --- |
| 1080 Piracaia (Dobrada) (CEMADEN) | 2346094 Piracaia (ANA) | 4.7 | 3087 | 0.140 | 0.311 |
| 1080 Piracaia (Dobrada) (CEMADEN) | 2346334 Crioulos | 9.3 | 1729 | 0.331 | 0.151 |
| 11 Piracaia (Barragem Cachoeira) (SABESP) | 2346334 Crioulos | 2.6 | 4043 | 0.421 | 0.277 |
| 11 Piracaia (Barragem Cachoeira) (SABESP) | 2346094 Piracaia (ANA) | 4.7 | 5810 | 0.199 | 0.304 |
| 1132 CACHOEIRA (CEMADEN) | 2246174 Joanópolis (ANA) | 4.7 | 795 | 0.771 | 0.171 |
| 1132 CACHOEIRA (CEMADEN) | 2246090 Joanópolis | 9.8 | 696 | 0.247 | 0.225 |
| 1202 CENTRO (CEMADEN) | 2246090 Joanópolis | 0.6 | 2628 | 0.378 | 0.178 |
| 1202 CENTRO (CEMADEN) | 2246174 Joanópolis (ANA) | 6.2 | 2652 | 0.790 | 0.265 |
| 1431 Piracaia (Cachoeira Montante) (SP ÁGUAS) | 2246174 Joanópolis (ANA) | 8.4 | 3807 | 0.745 | 0.221 |
| 1431 Piracaia (Cachoeira Montante) (SP ÁGUAS) | 2246090 Joanópolis | 8.6 | 2979 | 0.397 | 0.162 |
| 1431 Piracaia (Cachoeira Montante) (SP ÁGUAS) | 2346334 Crioulos | 9.1 | 2078 | 0.296 | 0.187 |
| 1436 Nazaré Paulista (ETA SABESP) (CEMADEN) | 2346010 Nazaré Paulista (SP Águas) | 1.0 | 2800 | 0.645 | 0.205 |
| 1436 Nazaré Paulista (ETA SABESP) (CEMADEN) | 2346446 Nazaré Paulista (ANA) | 5.9 | 3101 | 0.551 | 0.252 |
| 1449 JOANOPOLIS02 (CEMADEN) | 2246174 Joanópolis (ANA) | 0.5 | 775 | 0.793 | 0.241 |
| 1449 JOANOPOLIS02 (CEMADEN) | 2246090 Joanópolis | 5.8 | 788 | 0.363 | 0.247 |
| 15 Nazaré Paulista (Barragem Atibainha) (SABESP) | 2346010 Nazaré Paulista (SP Águas) | 1.3 | 4977 | 0.736 | 0.223 |
| 15 Nazaré Paulista (Barragem Atibainha) (SABESP) | 2346446 Nazaré Paulista (ANA) | 5.6 | 4180 | 0.606 | 0.263 |
| 17 Nazaré Paulista (Emboque do Tunel 5) (SABESP) | 2346446 Nazaré Paulista (ANA) | 6.1 | 836 | 0.825 | 0.339 |
| 27056 Bom Jesus dos Perdões (Centro) (CEMADEN) | 2346010 Nazaré Paulista (SP Águas) | 8.5 | 2118 | 0.477 | 0.185 |
| 27056 Bom Jesus dos Perdões (Centro) (CEMADEN) | 2346007 Atibaia (SP Águas) | 8.7 | 1052 | 0.286 | 0.355 |
| 27081 Piracaia (Caras) (CEMADEN) | 2346334 Crioulos | 5.6 | 1404 | 0.390 | 0.236 |
| 27832 Joanópolis (03- Ribeirão da Correnteza) (CEMADEN) | 2246174 Joanópolis (ANA) | 4.4 | 1987 | 0.750 | 0.266 |
| 33277 Piracaia (Captação) (SP ÁGUAS) | 2346094 Piracaia (ANA) | 4.0 | 1426 | 0.188 | 0.502 |
| 33279 Nazaré Paulista (Mascate) (SP ÁGUAS) | 2346010 Nazaré Paulista (SP Águas) | 2.5 | 763 | 0.353 | 0.238 |
| 33279 Nazaré Paulista (Mascate) (SP ÁGUAS) | 2346446 Nazaré Paulista (ANA) | 7.9 | 1399 | 0.711 | 0.326 |
| 33455 Nazaré Paulista - SP (IAC) | 2346446 Nazaré Paulista (ANA) | 5.7 | 740 | 0.800 | 0.327 |
| 33477 Piracaia - SP (IAC) | 2346094 Piracaia (ANA) | 1.2 | 653 | 0.321 | 0.641 |
| 5 Joanópolis (Barragem Jacareí) (SABESP) | 2246090 Joanópolis | 7.7 | 726 | 0.222 | 0.151 |
| 5 Joanópolis (Barragem Jacareí) (SABESP) | 2346094 Piracaia (ANA) | 9.6 | 1500 | 0.238 | 0.576 |
| 7 Joanópolis (Barragem Jacareí - Túnel 7 / Vargem) (SABESP) | 2346094 Piracaia (ANA) | 9.5 | 778 | 0.272 | 0.701 |
| 831 Piracaia (Rio Cachoeira - Centro) (SAISP) | 2346094 Piracaia (ANA) | 0.7 | 594 | 0.277 | 0.755 |

## Gauges

A day is kept only if all 24 hourly sums are present and none is negative or above 150 mm. Distances are to the nearer catchment centroid.

| SIBH id | Code | Operator | Name | km | Hours on record | Complete days | Days with missing hours | Days with an invalid hour | First kept day | Last kept day | Used |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1132 | 352550801A | CEMADEN | CACHOEIRA | 0.9 | 31300 | 802 | 1167 | 0 | 2015-01-02 | 2025-02-27 | yes, leads its site (802 days) |
| 372 | 2346798 | SABESP | Piracaia (SB-CA-DBT6 Desemboque do Túnel 6) | 3.2 | 7569 | 313 | 4 | 0 | 2026-01-14 | 2026-11-23 | no: co-located with 13, which leads the site; this gauge fills its gaps |
| 13 | 616 | SABESP | Piracaia (Desemboque do Túnel - 6) | 3.4 | 16493 | 672 | 27 | 1 | 2014-12-18 | 2026-01-13 | yes, leads its site (985 days, gaps filled from 372) |
| 27832 | 352550803A | CEMADEN | Joanópolis (03- Ribeirão da Correnteza) | 3.5 | 74197 | 2085 | 1623 | 0 | 2015-03-01 | 2026-11-23 | yes, leads its site (2085 days) |
| 1449 | 352550802A | CEMADEN | JOANOPOLIS02 | 4.2 | 23296 | 810 | 236 | 0 | 2015-01-02 | 2020-10-15 | yes, leads its site (810 days) |
| 33857 | 724 | SAISP | Rio Atibainha - Montante Atibainha | 4.3 | 21097 | 866 | 23 | 0 | 2022-01-02 | 2024-05-28 | yes, leads its site (866 days) |
| 1398 | E3-268 | SP ÁGUAS | Nazaré Paulista (Atibainha Montante) | 5.4 | 38975 | 1600 | 31 | 1 | 2018-03-22 | 2026-11-23 | yes, leads its site (1600 days) |
| 1411 | 353860003A | CEMADEN | PIÃO | 7.1 | 0 | 0 | 0 | 0 |  |  | no: no complete day |
| 1431 | E3-269 | SP ÁGUAS | Piracaia (Cachoeira Montante) | 7.6 | 95876 | 3954 | 54 | 0 | 2015-06-14 | 2026-11-23 | yes, leads its site (3954 days) |
| 1202 | 352550804A | CEMADEN | CENTRO | 9.5 | 66900 | 2701 | 135 | 0 | 2015-01-02 | 2026-09-27 | yes, leads its site (2701 days) |
| 33433 | IAC-Joanópolis - SP | IAC | Joanópolis - SP | 9.9 | 0 | 0 | 0 | 0 |  |  | no: no complete day |
| 35574 | 1000197 | SABESP | Piracaia (Barragem) | 10.3 | 0 | 0 | 0 | 0 |  |  | no: no complete day |
| 11 | 1001177 | SABESP | Piracaia (Barragem Cachoeira) | 10.3 | 147782 | 6120 | 46 | 1 | 2010-01-02 | 2026-11-23 | yes, leads its site (6137 days, gaps filled from 33277) |
| 368 | 2346794 | SABESP | SB-CA-BRC Barragem Cachoeira | 10.4 | 4 | 0 | 1 | 0 |  |  | no: no complete day |
| 33277 | E3-110 | SP ÁGUAS | Piracaia (Captação) | 10.9 | 39422 | 1600 | 56 | 0 | 2010-01-02 | 2026-11-23 | no: co-located with 11, which leads the site; this gauge fills its gaps |
| 27081 | 353860001A | CEMADEN | Piracaia (Caras) | 11.2 | 65799 | 2092 | 887 | 0 | 2015-01-02 | 2026-11-19 | yes, leads its site (2092 days) |
| 367 | 2346793 | SABESP | SB-CA-BRA BARRAGEM ATIBAINHA | 11.3 | 4 | 0 | 1 | 0 |  |  | no: no complete day |
| 33477 | IAC-Piracaia - SP | IAC | Piracaia - SP | 11.3 | 20419 | 814 | 51 | 0 | 2024-05-07 | 2026-11-19 | yes, leads its site (814 days) |
| 21 | 1000721 | SABESP | Nazaré Paulista (Canal Jusante Atibainha) | 11.5 | 0 | 0 | 0 | 0 |  |  | no: no complete day |
| 15 | 1001178 | SABESP | Nazaré Paulista (Barragem Atibainha) | 11.5 | 147459 | 6099 | 56 | 4 | 2010-01-02 | 2026-11-23 | yes, leads its site (6133 days, gaps filled from 1436) |
| 35576 | 1000198 | SABESP | Nazaré Paulista (Barragem Atibainha) | 11.5 | 0 | 0 | 0 | 0 |  |  | no: no complete day |
| 1436 | 353240501A | CEMADEN | Nazaré Paulista (ETA SABESP) | 12.0 | 88443 | 3365 | 391 | 0 | 2015-03-01 | 2026-11-23 | no: co-located with 15, which leads the site; this gauge fills its gaps |
| 33455 | IAC-Nazaré Paulista - SP | IAC | Nazaré Paulista - SP | 12.1 | 21237 | 844 | 62 | 0 | 2024-05-07 | 2026-11-19 | no: co-located with 15, which leads the site; this gauge fills its gaps |
| 831 | E3-296 | SAISP | Piracaia (Rio Cachoeira - Centro) | 12.3 | 19192 | 784 | 23 | 0 | 2018-02-08 | 2026-11-23 | yes, leads its site (784 days) |
| 33279 | E3-121 | SP ÁGUAS | Nazaré Paulista (Mascate) | 13.6 | 40343 | 1650 | 41 | 4 | 2010-01-02 | 2026-11-23 | yes, leads its site (1650 days) |
| 7 | 619 | SABESP | Joanópolis (Barragem Jacareí - Túnel 7 / Vargem) | 14.9 | 23436 | 968 | 13 | 0 | 2020-11-07 | 2026-11-23 | no: co-located with 5, which leads the site; this gauge fills its gaps |
| 365 | 2246243 | SABESP | SB-CA-BJC-T7 Emboque Túnel 7 | 15.0 | 4 | 0 | 1 | 0 |  |  | no: no complete day |
| 5 | 179 | SABESP | Joanópolis (Barragem Jacareí) | 15.0 | 37567 | 1548 | 28 | 0 | 2010-01-02 | 2026-06-15 | yes, leads its site (1726 days, gaps filled from 7) |
| 35608 | 1000734 | SABESP | Santa Isabel (Transposição Jaguari (PS) - Atibainha (SC)) | 15.1 | 0 | 0 | 0 | 0 |  |  | no: no complete day |
| 27826 | 352020201A | CEMADEN | POLICIA MILITAR | 15.4 | 59807 | 2355 | 238 | 0 | 2015-08-02 | 2025-07-07 | yes, leads its site (2355 days) |
| 17 | 746 | SABESP | Nazaré Paulista (Emboque do Tunel 5) | 15.8 | 23065 | 950 | 16 | 0 | 2019-01-24 | 2026-11-23 | yes, leads its site (950 days) |
| 35353 | 637 | SABESP | Santa Isabel (EEAB Paraíba do Sul - Atibainha) | 15.9 | 12467 | 508 | 17 | 0 | 2025-06-17 | 2026-11-23 | yes, leads its site (508 days) |
| 373 | 2346799 | SABESP | Santa Isabel (SB-CA-EAB-Elevatória Paraíba do Sul) | 16.3 | 4 | 0 | 1 | 0 |  |  | no: no complete day |
| 1080 | 353860002A | CEMADEN | Piracaia (Dobrada) | 16.5 | 81215 | 3205 | 284 | 0 | 2015-01-02 | 2026-11-23 | yes, leads its site (3205 days) |
| 33364 | IAC-Bom Jesus dos Perdões - SP | IAC | Bom Jesus dos Perdões - SP | 16.7 | 21518 | 876 | 30 | 0 | 2024-05-07 | 2026-11-19 | yes, leads its site (876 days) |
| 35494 | 487 | SABESP | Santa Isabel (Captação Represa do Jaguari) | 17.9 | 9377 | 386 | 7 | 0 | 2025-10-22 | 2026-11-22 | yes, leads its site (386 days) |
| 27056 | 350710001A | CEMADEN | Bom Jesus dos Perdões (Centro) | 18.3 | 74091 | 2875 | 328 | 0 | 2015-10-23 | 2026-11-10 | yes, leads its site (2875 days) |
| 771 | IAC-Extrema - MG | IAC | Extrema - SP | 19.2 | 19072 | 756 | 54 | 0 | 2024-06-26 | 2026-11-19 | yes, leads its site (756 days) |

### Excluded before download

| SIBH id | Code | Operator | Name | Reason |
| --- | --- | --- | --- | --- |
| 15226 | 2246174 | ANA | JOANÓPOLIS | owned by ANA; taken from ANA's service |
| 29188 | E3-229 | SP ÁGUAS | CRIOULOS | conventional gauge; duplicates ANA's record |
| 29208 | E3-250 | SP ÁGUAS | RIBEIRAO ACIMA | conventional gauge; duplicates ANA's record |
| 28651 | D3-019 | SP ÁGUAS | FAZENDA BONFIM | conventional gauge; duplicates ANA's record |
| 25524 | D3-054 | SP ÁGUAS | JOANOPOLIS | conventional gauge; duplicates ANA's record |
| 35780 | 2246167 | ANA | Extrema (Nascente Principal) | owned by ANA; taken from ANA's service |
| 14991 | 2346446 | ANA | Nazaré Paulista | owned by ANA; taken from ANA's service |
| 14981 | 2346450 | ANA | CAPTAÇÃO DE PIRACAIA | owned by ANA; taken from ANA's service |
| 35833 | 1000910 | SABESP | Piracaia (Precipitação Radar Bacia do Cachoeira) | radar product, not a gauge |
| 35832 | 1000911 | SABESP | Nazaré Paulista (Precipitação Radar Bacia do Atibainha) | radar product, not a gauge |
| 35785 | 2246197 | ANA | Camanducaia (Santa Terezinha) | owned by ANA; taken from ANA's service |
| 29130 | E3-076 | SP ÁGUAS | PIRACAIA | conventional gauge; duplicates ANA's record |
| 25465 | E3-099 | SP ÁGUAS | NAZARE PAULISTA | conventional gauge; duplicates ANA's record |
| 29186 | E3-227 | SP ÁGUAS | BATATUBA | conventional gauge; duplicates ANA's record |
| 29201 | E3-242 | SP ÁGUAS | IGARATA | conventional gauge; duplicates ANA's record |
| 28674 | D3-070 | SP ÁGUAS | GUIRRA | conventional gauge; duplicates ANA's record |
| 778 | A509 | ANA | Monte Verde - MG | owned by ANA; taken from ANA's service |
| 35784 | 2246196 | ANA | Camanducaia (Copasa) | owned by ANA; taken from ANA's service |
| 29184 | E3-225 | SP ÁGUAS | MORRO GRANDE | conventional gauge; duplicates ANA's record |

### Co-located groups (rule 4)

The first gauge listed leads the site; the others fill its missing days, in order.

- 13 Piracaia (Desemboque do Túnel - 6) (SABESP, 672 days); 372 Piracaia (SB-CA-DBT6 Desemboque do Túnel 6) (SABESP, 313 days)
- 1202 CENTRO (CEMADEN, 2701 days); 33433 Joanópolis - SP (IAC, 0 days)
- 11 Piracaia (Barragem Cachoeira) (SABESP, 6120 days); 33277 Piracaia (Captação) (SP ÁGUAS, 1600 days); 35574 Piracaia (Barragem) (SABESP, 0 days); 368 SB-CA-BRC Barragem Cachoeira (SABESP, 0 days)
- 15 Nazaré Paulista (Barragem Atibainha) (SABESP, 6099 days); 1436 Nazaré Paulista (ETA SABESP) (CEMADEN, 3365 days); 33455 Nazaré Paulista - SP (IAC, 844 days); 21 Nazaré Paulista (Canal Jusante Atibainha) (SABESP, 0 days); 35576 Nazaré Paulista (Barragem Atibainha) (SABESP, 0 days); 367 SB-CA-BRA BARRAGEM ATIBAINHA (SABESP, 0 days)
- 5 Joanópolis (Barragem Jacareí) (SABESP, 1548 days); 7 Joanópolis (Barragem Jacareí - Túnel 7 / Vargem) (SABESP, 968 days); 365 SB-CA-BJC-T7 Emboque Túnel 7 (SABESP, 0 days)
- 35353 Santa Isabel (EEAB Paraíba do Sul - Atibainha) (SABESP, 508 days); 35608 Santa Isabel (Transposição Jaguari (PS) - Atibainha (SC)) (SABESP, 0 days); 373 Santa Isabel (SB-CA-EAB-Elevatória Paraíba do Sul) (SABESP, 0 days)

## Complete days per year, by site

| Site (lead SIBH id) | Name | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1132 | CACHOEIRA | 0 | 0 | 0 | 0 | 0 | 361 | 149 | 1 | 3 | 0 | 12 | 2 | 177 | 7 | 72 | 18 | 0 |
| 13 | Piracaia (Desemboque do Túnel - 6) | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 13 | 0 | 14 | 0 | 23 | 0 | 0 | 239 | 356 | 326 |
| 27832 | Joanópolis (03- Ribeirão da Correnteza) | 0 | 0 | 0 | 0 | 0 | 66 | 179 | 167 | 9 | 18 | 30 | 287 | 341 | 304 | 239 | 201 | 244 |
| 1449 | JOANOPOLIS02 | 0 | 0 | 0 | 0 | 0 | 347 | 359 | 53 | 0 | 0 | 51 | 0 | 0 | 0 | 0 | 0 | 0 |
| 33857 | Rio Atibainha - Montante Atibainha | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 357 | 363 | 146 | 0 | 0 |
| 1398 | Nazaré Paulista (Atibainha Montante) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 0 | 0 | 22 | 357 | 297 | 230 | 356 | 324 |
| 1431 | Piracaia (Cachoeira Montante) | 0 | 0 | 0 | 0 | 0 | 196 | 360 | 359 | 359 | 365 | 363 | 360 | 359 | 325 | 226 | 356 | 326 |
| 1202 | CENTRO | 0 | 0 | 0 | 0 | 0 | 364 | 359 | 353 | 351 | 55 | 256 | 339 | 349 | 263 | 0 | 0 | 12 |
| 11 | Piracaia (Barragem Cachoeira) | 362 | 360 | 365 | 364 | 364 | 363 | 364 | 361 | 362 | 364 | 366 | 362 | 365 | 363 | 363 | 363 | 326 |
| 27081 | Piracaia (Caras) | 0 | 0 | 0 | 0 | 0 | 250 | 345 | 334 | 251 | 162 | 108 | 0 | 2 | 0 | 225 | 208 | 207 |
| 33477 | Piracaia - SP | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 210 | 338 | 266 |
| 15 | Nazaré Paulista (Barragem Atibainha) | 354 | 356 | 362 | 363 | 364 | 365 | 365 | 365 | 364 | 365 | 366 | 365 | 365 | 364 | 359 | 365 | 326 |
| 831 | Piracaia (Rio Cachoeira - Centro) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 0 | 0 | 23 | 0 | 0 | 56 | 354 | 325 |
| 33279 | Nazaré Paulista (Mascate) | 14 | 0 | 0 | 14 | 0 | 0 | 14 | 0 | 14 | 0 | 0 | 23 | 351 | 339 | 226 | 332 | 323 |
| 5 | Joanópolis (Barragem Jacareí) | 14 | 0 | 0 | 14 | 0 | 0 | 14 | 0 | 28 | 0 | 14 | 23 | 359 | 284 | 290 | 360 | 326 |
| 27826 | POLICIA MILITAR | 0 | 0 | 0 | 0 | 0 | 149 | 286 | 293 | 255 | 11 | 36 | 343 | 351 | 360 | 156 | 115 | 0 |
| 17 | Nazaré Paulista (Emboque do Tunel 5) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 0 | 23 | 0 | 0 | 228 | 361 | 324 |
| 35353 | Santa Isabel (EEAB Paraíba do Sul - Atibainha) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 193 | 315 |
| 1080 | Piracaia (Dobrada) | 0 | 0 | 0 | 0 | 0 | 361 | 333 | 352 | 337 | 119 | 116 | 352 | 352 | 199 | 289 | 302 | 93 |
| 33364 | Bom Jesus dos Perdões - SP | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 236 | 325 | 315 |
| 35494 | Santa Isabel (Captação Represa do Jaguari) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 69 | 317 |
| 27056 | Bom Jesus dos Perdões (Centro) | 0 | 0 | 0 | 0 | 0 | 70 | 359 | 332 | 46 | 0 | 302 | 339 | 354 | 343 | 275 | 213 | 242 |
| 771 | Extrema - SP | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 143 | 303 | 310 |
