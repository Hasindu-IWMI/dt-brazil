# Rain gauge audit

Generated 2026-11-23 23:09 UTC by `pipeline/audit_rain.py`. Gauges are judged only against each other; no model output is used.

Rules: at least 25 days reported, total under 25% of the regional median, median at least 50 mm (dry-record month); at least 330 days reported, ratio to the regional median under 70% or over 140% of the gauge's own median ratio (anomalous year).

## Summary by gauge, 1984 to 2026

| Code | Name | Years with 330+ days | Median ratio to region | Lowest and highest yearly ratio | Dry-record months | Anomalous years |
| --- | --- | --- | --- | --- | --- | --- |
| 2346004 | Piracaia (SP Águas) | 10 | 1.02 | 0.91 (1988) to 1.19 (1985) | 0 | none |
| 2346005 | Batatuba | 12 | 0.89 | 0.59 (1989) to 1.02 (1988) | 4 | 1989 |
| 2346094 | Piracaia (ANA) | 36 | 0.90 | 0.18 (2019) to 1.51 (2010) | 27 | 2000, 2010, 2011, 2014, 2016, 2017, 2018, 2019 |
| 2346334 | Crioulos | 29 | 1.02 | 0.59 (2018) to 1.58 (2014) | 18 | 1986, 1987, 2013, 2014, 2016, 2018, 2019 |
| 2246090 | Joanópolis | 39 | 1.02 | 0.90 (2010) to 1.29 (2005) | 0 | none |
| 2246099 | Fazenda Bonfim | 8 | 1.50 | 1.20 (1986) to 1.62 (1991) | 1 | none |
| 2246134 | Mato Mole | 0 | no complete year | | 0 | |
| 2246046 | Fazenda Retiro | 0 | no complete year | | 0 | |
| 2346403 | Água do Poço | 0 | no complete year | | 0 | |
| 2346010 | Nazaré Paulista (SP Águas) | 40 | 1.02 | 0.86 (1992) to 1.29 (2002) | 1 | none |
| 2346017 | Morro Grande | 10 | 0.90 | 0.76 (1992) to 1.07 (1989) | 1 | none |
| 2346352 | Ribeirão Acima | 15 | 0.98 | 0.69 (1997) to 1.59 (1986) | 3 | 1986, 1987 |
| 2346402 | Bairro Cuiabá | 0 | no complete year | | 0 | |
| 2346007 | Atibaia (SP Águas) | 30 | 1.05 | 0.87 (1990) to 1.35 (2020) | 0 | none |
| 2346095 | Atibaia (ANA) | 36 | 0.95 | 0.49 (2019) to 1.25 (1994) | 14 | 2019, 2021, 2022 |
| 2346019 | Santa Isabel | 30 | 0.98 | 0.78 (1992) to 1.09 (1996) | 0 | none |
| 2246174 | Joanópolis (ANA) | 12 | 1.08 | 0.80 (2016) to 1.19 (2020) | 0 | none |
| 2346446 | Nazaré Paulista (ANA) | 10 | 0.99 | 0.75 (2015) to 1.16 (2025) | 4 | none |
| SIBH-1132 | CACHOEIRA (CEMADEN, telemetric) | 1 | 1.01 | 1.01 (2015) to 1.01 (2015) | 0 | none |
| SIBH-13 | Piracaia (Desemboque do Túnel - 6) (SABESP, telemetric) | 1 | 1.14 | 1.14 (2025) to 1.14 (2025) | 2 | none |
| SIBH-27832 | Joanópolis (03- Ribeirão da Correnteza) (CEMADEN, telemetric) | 1 | 1.58 | 1.58 (2022) to 1.58 (2022) | 2 | none |
| SIBH-1449 | JOANOPOLIS02 (CEMADEN, telemetric) | 2 | 0.91 | 0.84 (2015) to 0.97 (2016) | 1 | none |
| SIBH-33857 | Rio Atibainha - Montante Atibainha (SAISP, telemetric) | 2 | 1.05 | 1.00 (2022) to 1.09 (2023) | 0 | none |
| SIBH-1398 | Nazaré Paulista (Atibainha Montante) (SP ÁGUAS, telemetric) | 2 | 1.09 | 1.00 (2022) to 1.19 (2025) | 0 | none |
| SIBH-1431 | Piracaia (Cachoeira Montante) (SP ÁGUAS, telemetric) | 8 | 0.89 | 0.78 (2016) to 1.02 (2018) | 1 | none |
| SIBH-1202 | CENTRO (CEMADEN, telemetric) | 6 | 1.06 | 0.93 (2016) to 1.38 (2022) | 0 | none |
| SIBH-11 | Piracaia (Barragem Cachoeira) (SABESP, telemetric) | 16 | 1.04 | 0.87 (2022) to 1.25 (2014) | 0 | none |
| SIBH-27081 | Piracaia (Caras) (CEMADEN, telemetric) | 2 | 0.95 | 0.89 (2017) to 1.01 (2016) | 1 | none |
| SIBH-33477 | Piracaia - SP (IAC, telemetric) | 1 | 0.87 | 0.87 (2025) to 0.87 (2025) | 3 | none |
| SIBH-15 | Nazaré Paulista (Barragem Atibainha) (SABESP, telemetric) | 16 | 1.01 | 0.84 (2013) to 1.26 (2019) | 1 | none |
| SIBH-831 | Piracaia (Rio Cachoeira - Centro) (SAISP, telemetric) | 1 | 0.89 | 0.89 (2025) to 0.89 (2025) | 0 | none |
| SIBH-33279 | Nazaré Paulista (Mascate) (SP ÁGUAS, telemetric) | 3 | 0.65 | 0.63 (2022) to 0.86 (2025) | 0 | none |
| SIBH-5 | Joanópolis (Barragem Jacareí) (SABESP, telemetric) | 2 | 1.08 | 0.85 (2022) to 1.30 (2025) | 0 | none |
| SIBH-27826 | POLICIA MILITAR (CEMADEN, telemetric) | 3 | 1.53 | 1.27 (2021) to 1.60 (2022) | 0 | none |
| SIBH-17 | Nazaré Paulista (Emboque do Tunel 5) (SABESP, telemetric) | 1 | 0.95 | 0.95 (2025) to 0.95 (2025) | 0 | none |
| SIBH-35353 | Santa Isabel (EEAB Paraíba do Sul - Atibainha) (SABESP, telemetric) | 0 | no complete year | | 1 | |
| SIBH-1080 | Piracaia (Dobrada) (CEMADEN, telemetric) | 6 | 0.69 | 0.50 (2016) to 1.19 (2021) | 24 | 2021 |
| SIBH-33364 | Bom Jesus dos Perdões - SP (IAC, telemetric) | 0 | no complete year | | 0 | |
| SIBH-35494 | Santa Isabel (Captação Represa do Jaguari) (SABESP, telemetric) | 0 | no complete year | | 0 | |
| SIBH-27056 | Bom Jesus dos Perdões (Centro) (CEMADEN, telemetric) | 5 | 1.17 | 0.94 (2021) to 1.62 (2023) | 0 | none |
| SIBH-771 | Extrema - SP (IAC, telemetric) | 0 | no complete year | | 0 | |

## Dry-record months by gauge and year

Count of flagged months per year (only years with at least one flag are listed).

| Code | Name | Flagged months by year |
| --- | --- | --- |
| 2346005 | Batatuba | 1988: 2, 1989: 2 |
| 2346094 | Piracaia (ANA) | 1989: 1, 1992: 1, 2000: 2, 2002: 1, 2011: 1, 2014: 1, 2015: 3, 2017: 2, 2018: 6, 2019: 7, 2020: 1, 2023: 1 |
| 2346334 | Crioulos | 1986: 1, 1987: 2, 2007: 4, 2008: 2, 2015: 1, 2016: 3, 2018: 1, 2019: 2, 2020: 2 |
| 2246099 | Fazenda Bonfim | 1993: 1 |
| 2346010 | Nazaré Paulista (SP Águas) | 1984: 1 |
| 2346017 | Morro Grande | 1992: 1 |
| 2346352 | Ribeirão Acima | 1990: 2, 1997: 1 |
| 2346095 | Atibaia (ANA) | 2012: 1, 2017: 1, 2018: 4, 2019: 5, 2021: 2, 2024: 1 |
| 2346446 | Nazaré Paulista (ANA) | 2014: 1, 2015: 1, 2017: 1, 2020: 1 |
| SIBH-13 | Piracaia (Desemboque do Túnel - 6) (SABESP, telemetric) | 2026: 2 |
| SIBH-27832 | Joanópolis (03- Ribeirão da Correnteza) (CEMADEN, telemetric) | 2015: 1, 2024: 1 |
| SIBH-1449 | JOANOPOLIS02 (CEMADEN, telemetric) | 2015: 1 |
| SIBH-1431 | Piracaia (Cachoeira Montante) (SP ÁGUAS, telemetric) | 2021: 1 |
| SIBH-27081 | Piracaia (Caras) (CEMADEN, telemetric) | 2018: 1 |
| SIBH-33477 | Piracaia - SP (IAC, telemetric) | 2025: 1, 2026: 2 |
| SIBH-15 | Nazaré Paulista (Barragem Atibainha) (SABESP, telemetric) | 2010: 1 |
| SIBH-35353 | Santa Isabel (EEAB Paraíba do Sul - Atibainha) (SABESP, telemetric) | 2025: 1 |
| SIBH-1080 | Piracaia (Dobrada) (CEMADEN, telemetric) | 2016: 3, 2017: 1, 2018: 4, 2019: 3, 2022: 5, 2023: 4, 2025: 3, 2026: 1 |

## Yearly totals from 2010, mm (blank = fewer than 330 days reported; * = flagged biased year)

| Year | 2346094 Piracaia (ANA) | 2346334 Crioulos | 2246090 Joanópolis | 2346010 Nazaré Paulista (SP Águas) | 2346007 Atibaia (SP Águas) | 2346095 Atibaia (ANA) | 2346019 Santa Isabel | 2246174 Joanópolis (ANA) | 2346446 Nazaré Paulista (ANA) | SIBH-1132 CACHOEIRA (CEMADEN, telemetric) | SIBH-13 Piracaia (Desemboque do Túnel - 6) (SABESP, telemetric) | SIBH-27832 Joanópolis (03- Ribeirão da Correnteza) (CEMADEN, telemetric) | SIBH-1449 JOANOPOLIS02 (CEMADEN, telemetric) | SIBH-33857 Rio Atibainha - Montante Atibainha (SAISP, telemetric) | SIBH-1398 Nazaré Paulista (Atibainha Montante) (SP ÁGUAS, telemetric) | SIBH-1431 Piracaia (Cachoeira Montante) (SP ÁGUAS, telemetric) | SIBH-1202 CENTRO (CEMADEN, telemetric) | SIBH-11 Piracaia (Barragem Cachoeira) (SABESP, telemetric) | SIBH-27081 Piracaia (Caras) (CEMADEN, telemetric) | SIBH-33477 Piracaia - SP (IAC, telemetric) | SIBH-15 Nazaré Paulista (Barragem Atibainha) (SABESP, telemetric) | SIBH-831 Piracaia (Rio Cachoeira - Centro) (SAISP, telemetric) | SIBH-33279 Nazaré Paulista (Mascate) (SP ÁGUAS, telemetric) | SIBH-5 Joanópolis (Barragem Jacareí) (SABESP, telemetric) | SIBH-27826 POLICIA MILITAR (CEMADEN, telemetric) | SIBH-17 Nazaré Paulista (Emboque do Tunel 5) (SABESP, telemetric) | SIBH-35353 Santa Isabel (EEAB Paraíba do Sul - Atibainha) (SABESP, telemetric) | SIBH-1080 Piracaia (Dobrada) (CEMADEN, telemetric) | SIBH-33364 Bom Jesus dos Perdões - SP (IAC, telemetric) | SIBH-35494 Santa Isabel (Captação Represa do Jaguari) (SABESP, telemetric) | SIBH-27056 Bom Jesus dos Perdões (Centro) (CEMADEN, telemetric) | SIBH-771 Extrema - SP (IAC, telemetric) | Regional median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | 2351* | 2056 | 1403 | 1494 | 1649 | 1103 | 1563 |  |  |  |  |  |  |  |  |  |  | 1554 |  |  | 1528 |  | (14 days) | (14 days) |  |  |  |  |  |  |  |  | 1554 |
| 2011 | 2146* | 1547 | 1601 | 1596 | 1650 | 1328 | 1425 |  |  |  |  |  |  |  |  |  |  | 1631 |  |  | 1703 |  |  |  |  |  |  |  |  |  |  |  | 1601 |
| 2012 | 1183 | 2142 | 1392 | 1671 | 1881 | 1304 | 1531 |  |  |  |  |  |  |  |  |  |  | 1624 |  |  | 1521 |  |  |  |  |  |  |  |  |  |  |  | 1531 |
| 2013 | 1121 | 1752* | 1297 | 1307 | 1431 | 972 | 1217 | (214 days) |  |  |  |  |  |  |  |  |  | 1143 |  |  | 1028 |  | (14 days) | (14 days) |  |  |  |  |  |  |  |  | 1217 |
| 2014 | 451* | 1502* | 927 | 951 | 1029 | 879 | (304 days) | 954 | (160 days) |  | (14 days) |  |  |  |  |  |  | 1184 |  |  | 943 |  |  |  |  |  |  |  |  |  |  |  | 951 |
| 2015 | 1280 | 1481 | 1978 | 1748 | 1610 | 1198 |  | 1844 | 1217 | 1631 |  | (66 days) | 1368 |  |  | (196 days) | 1900 | 1830 | (250 days) |  | 1632 |  |  |  | (149 days) |  |  | 1507 |  |  | (70 days) |  | 1620 |
| 2016 | 2359* | 1111* | 1538 | 1795 | (316 days) | 1680 |  | 1275 | 1596 | (149 days) |  | (179 days) | 1555 |  |  | 1245 | 1485 | 1615 | 1615 |  | 1616 |  | (14 days) | (14 days) | (286 days) |  |  | 795 |  |  | 1873 |  | 1596 |
| 2017 | 633* | 942 | 1373 | 1255 | (286 days) | (225 days) |  | 1340 | 1332 | (1 days) | (13 days) | (167 days) | (53 days) |  |  | 1201 | 1270 | 1186 | 1081 |  | 1262 |  |  |  | (293 days) |  |  | 906 |  |  | 1221 |  | 1221 |
| 2018 | 217* | 705* | 1300 | 1159 | 1136 | (179 days) | (318 days) | 1270 | 1313 | (3 days) |  | (9 days) |  |  | (14 days) | 1213 | 1291 | 1458 | (251 days) |  | 1121 | (26 days) | (14 days) | (28 days) | (255 days) |  |  | 627 |  |  | (46 days) |  | 1186 |
| 2019 | 214* | 824* | 1425 | 1194 | 1365 | 592* | (210 days) | 1370 | 1207 |  | (14 days) | (18 days) |  |  |  | 1106 | (55 days) | 1474 | (162 days) |  | 1525 |  |  |  | (11 days) | (14 days) |  | (119 days) |  |  |  |  | 1207 |
| 2020 | 835 | (297 days) | 1405 | 1135 | 1592 | 1228 | (91 days) | 1405 | 1039 | (12 days) |  | (30 days) | (51 days) |  |  | 1026 | (256 days) | 1343 | (108 days) |  | 1058 |  |  | (14 days) | (36 days) |  |  | (116 days) |  |  | (302 days) |  | 1182 |
| 2021 | 1046 | (181 days) | 1272 | 1189 | (85 days) | 615* |  | 1222 | 1021 | (2 days) | (23 days) | (287 days) |  |  | (22 days) | 865 | 1009 | 1242 |  |  | 1016 | (23 days) | (23 days) | (23 days) | 1327 | (23 days) |  | 1247* |  |  | 982 |  | 1046 |
| 2022 | 1145 |  | 1528 | 1696 |  | 942* |  | 1608 | 1317 | (177 days) |  | 2400 |  | 1521 | 1521 | 1252 | 2102 | 1319 | (2 days) |  | 1653 |  | 959 | 1295 | 2437 |  |  | 958 |  |  | 2235 |  | 1521 |
| 2023 | 1196 |  | (327 days) | 1453 |  | (321 days) |  | 1527 | (253 days) | (7 days) |  | (304 days) |  | 1667 | (297 days) | (325 days) | (263 days) | 1493 |  |  | 1595 |  | 999 | (284 days) | 2342 |  |  | (199 days) |  |  | 2479 |  | 1527 |
| 2024 | 897 |  |  |  |  | 1031 |  | 1333 | 1184 | (72 days) | (239 days) | (239 days) |  | (146 days) | (230 days) | (226 days) |  | 1463 | (225 days) | (210 days) | 1403 | (56 days) | (226 days) | (290 days) | (156 days) | (228 days) |  | (289 days) | (236 days) |  | (275 days) | (135 days) | 1258 |
| 2025 | 886 |  |  |  |  | 1063 |  | 1181 | 1228 | (18 days) | 1201 | (201 days) |  |  | 1256 | 1024 |  | 1052 | (208 days) | 917 | 1203 | 942 | 913 | 1378 | (115 days) | 1002 | (193 days) | (302 days) | (325 days) | (69 days) | (213 days) | (303 days) | 1058 |
| 2026 | (150 days) |  |  |  |  | (76 days) |  | (212 days) | (212 days) |  | (326 days) | (244 days) |  |  | (324 days) | (326 days) | (12 days) | (326 days) | (207 days) | (266 days) | (326 days) | (325 days) | (323 days) | (326 days) |  | (324 days) | (315 days) | (93 days) | (315 days) | (317 days) | (242 days) | (310 days) | too few gauges |

## Coverage: gauges reporting at least 330 days, by year

| Year | Gauges |
| --- | --- |
| 1984 | 10 |
| 1985 | 12 |
| 1986 | 12 |
| 1987 | 12 |
| 1988 | 10 |
| 1989 | 12 |
| 1990 | 12 |
| 1991 | 11 |
| 1992 | 10 |
| 1993 | 11 |
| 1994 | 9 |
| 1995 | 7 |
| 1996 | 9 |
| 1997 | 8 |
| 1998 | 8 |
| 1999 | 7 |
| 2000 | 7 |
| 2001 | 7 |
| 2002 | 7 |
| 2003 | 5 |
| 2004 | 4 |
| 2005 | 6 |
| 2006 | 6 |
| 2007 | 5 |
| 2008 | 5 |
| 2009 | 4 |
| 2010 | 9 |
| 2011 | 9 |
| 2012 | 9 |
| 2013 | 9 |
| 2014 | 9 |
| 2015 | 14 |
| 2016 | 15 |
| 2017 | 13 |
| 2018 | 12 |
| 2019 | 11 |
| 2020 | 10 |
| 2021 | 13 |
| 2022 | 18 |
| 2023 | 9 |
| 2024 | 6 |
| 2025 | 14 |
| 2026 | 0 |
