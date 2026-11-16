# Rain gauge audit

Generated 2026-11-14 12:06 UTC by `pipeline/audit_rain.py`. Gauges are judged only against each other; no model output is used.

Rules: at least 25 days reported, total under 25% of the regional median, median at least 50 mm (dry-record month); at least 330 days reported, ratio to the regional median under 70% or over 140% of the gauge's own median ratio (anomalous year).

## Summary by gauge, 1984 to 2026

| Code | Name | Years with 330+ days | Median ratio to region | Lowest and highest yearly ratio | Dry-record months | Anomalous years |
| --- | --- | --- | --- | --- | --- | --- |
| 2346004 | Piracaia (SP Águas) | 10 | 1.02 | 0.91 (1988) to 1.19 (1985) | 0 | none |
| 2346005 | Batatuba | 12 | 0.89 | 0.59 (1989) to 1.02 (1988) | 4 | 1989 |
| 2346094 | Piracaia (ANA) | 36 | 0.87 | 0.18 (2019) to 1.50 (2010) | 25 | 2000, 2010, 2011, 2014, 2016, 2017, 2018, 2019 |
| 2346334 | Crioulos | 29 | 1.02 | 0.60 (1986) to 1.58 (2014) | 16 | 1986, 1987, 2014, 2016, 2018, 2019 |
| 2246090 | Joanópolis | 39 | 1.02 | 0.90 (2010) to 1.29 (2005) | 0 | none |
| 2246099 | Fazenda Bonfim | 8 | 1.50 | 1.20 (1986) to 1.62 (1991) | 1 | none |
| 2246134 | Mato Mole | 0 | no complete year | | 0 | |
| 2246046 | Fazenda Retiro | 0 | no complete year | | 0 | |
| 2346403 | Água do Poço | 0 | no complete year | | 0 | |
| 2346010 | Nazaré Paulista (SP Águas) | 40 | 1.00 | 0.86 (1992) to 1.29 (2002) | 1 | none |
| 2346017 | Morro Grande | 10 | 0.90 | 0.76 (1992) to 1.07 (1989) | 1 | none |
| 2346352 | Ribeirão Acima | 15 | 0.98 | 0.69 (1997) to 1.59 (1986) | 3 | 1986, 1987 |
| 2346402 | Bairro Cuiabá | 0 | no complete year | | 0 | |
| 2346007 | Atibaia (SP Águas) | 30 | 1.05 | 0.87 (1990) to 1.33 (1994) | 0 | none |
| 2346095 | Atibaia (ANA) | 36 | 0.95 | 0.49 (2019) to 1.25 (1994) | 10 | 2019, 2021, 2022 |
| 2346019 | Santa Isabel | 30 | 0.98 | 0.78 (1992) to 1.09 (1996) | 0 | none |
| 2246174 | Joanópolis (ANA) | 12 | 1.09 | 0.80 (2016) to 1.20 (2024) | 0 | none |
| 2346446 | Nazaré Paulista (ANA) | 10 | 1.00 | 0.79 (2015) to 1.13 (2018) | 4 | none |

## Dry-record months by gauge and year

Count of flagged months per year (only years with at least one flag are listed).

| Code | Name | Flagged months by year |
| --- | --- | --- |
| 2346005 | Batatuba | 1988: 2, 1989: 2 |
| 2346094 | Piracaia (ANA) | 1989: 1, 1992: 1, 2000: 2, 2002: 1, 2011: 1, 2014: 1, 2015: 3, 2017: 3, 2018: 5, 2019: 5, 2020: 1, 2023: 1 |
| 2346334 | Crioulos | 1986: 1, 1987: 2, 2007: 4, 2008: 2, 2015: 1, 2016: 3, 2019: 1, 2020: 2 |
| 2246099 | Fazenda Bonfim | 1993: 1 |
| 2346010 | Nazaré Paulista (SP Águas) | 1984: 1 |
| 2346017 | Morro Grande | 1992: 1 |
| 2346352 | Ribeirão Acima | 1990: 2, 1997: 1 |
| 2346095 | Atibaia (ANA) | 2012: 1, 2018: 3, 2019: 4, 2021: 1, 2024: 1 |
| 2346446 | Nazaré Paulista (ANA) | 2014: 1, 2015: 1, 2017: 1, 2020: 1 |

## Yearly totals from 2010, mm (blank = fewer than 330 days reported; * = flagged biased year)

| Year | 2346094 Piracaia (ANA) | 2346334 Crioulos | 2246090 Joanópolis | 2346010 Nazaré Paulista (SP Águas) | 2346007 Atibaia (SP Águas) | 2346095 Atibaia (ANA) | 2346019 Santa Isabel | 2246174 Joanópolis (ANA) | 2346446 Nazaré Paulista (ANA) | Regional median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | 2351* | 2056 | 1403 | 1494 | 1649 | 1103 | 1563 |  |  | 1563 |
| 2011 | 2146* | 1547 | 1601 | 1596 | 1650 | 1328 | 1425 |  |  | 1596 |
| 2012 | 1183 | 2142 | 1392 | 1671 | 1881 | 1304 | 1531 |  |  | 1531 |
| 2013 | 1121 | 1752 | 1297 | 1307 | 1431 | 972 | 1217 | (214 days) |  | 1297 |
| 2014 | 451* | 1502* | 927 | 951 | 1029 | 879 | (304 days) | 954 | (160 days) | 951 |
| 2015 | 1280 | 1481 | 1978 | 1748 | 1610 | 1198 |  | 1844 | 1217 | 1545 |
| 2016 | 2359* | 1111* | 1538 | 1795 | (316 days) | 1680 |  | 1275 | 1596 | 1596 |
| 2017 | 633* | 942 | 1373 | 1255 | (286 days) | (225 days) |  | 1340 | 1332 | 1293 |
| 2018 | 217* | 705* | 1300 | 1159 | 1136 | (179 days) | (318 days) | 1270 | 1313 | 1159 |
| 2019 | 214* | 824* | 1425 | 1194 | 1365 | 592* | (210 days) | 1370 | 1207 | 1200 |
| 2020 | 835 | (297 days) | 1405 | 1135 | 1592 | 1228 | (91 days) | 1405 | 1039 | 1228 |
| 2021 | 1046 | (181 days) | 1272 | 1189 | (85 days) | 615* |  | 1222 | 1021 | 1118 |
| 2022 | 1145 |  | 1528 | 1696 |  | 942* |  | 1608 | 1317 | 1423 |
| 2023 | 1196 |  | (327 days) | 1453 |  | (321 days) |  | 1527 | (253 days) | 1453 |
| 2024 | 897 |  |  |  |  | 1031 |  | 1333 | 1184 | 1107 |
| 2025 | 886 |  |  |  |  | 1063 |  | 1181 | 1228 | 1122 |
| 2026 | (150 days) |  |  |  |  | (76 days) |  | (212 days) | (212 days) | too few gauges |

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
| 2010 | 7 |
| 2011 | 7 |
| 2012 | 7 |
| 2013 | 7 |
| 2014 | 7 |
| 2015 | 8 |
| 2016 | 7 |
| 2017 | 6 |
| 2018 | 7 |
| 2019 | 8 |
| 2020 | 7 |
| 2021 | 6 |
| 2022 | 6 |
| 2023 | 3 |
| 2024 | 4 |
| 2025 | 4 |
| 2026 | 0 |
