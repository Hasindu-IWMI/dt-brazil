# Day alignment of the ANA rain gauges

Generated 2026-11-23 23:09 UTC by `pipeline/rain_alignment.py`. No model output is used; nothing here changes the forcing.

Each ANA gauge, from 2010, is compared year by year with the telemetric SIBH sites within 15 km (on ANA's own day convention, see `sibh_rain_report.md`). r(s) is the median, over sites with at least 200 shared days that year, of the daily correlation between ANA day D and the site's day D + s. A year is marked **shifted** when the best s is not 0 and beats s = 0 by at least 0.15.

## Summary by gauge

| Code | Name | Years compared | Years shifted | Shifted years | Median r(0) | Median r at best shift |
| --- | --- | --- | --- | --- | --- | --- |
| 2346094 | Piracaia (ANA) | 16 | 7 | 2018, 2020, 2021, 2022, 2023, 2024, 2025 | 0.22 | 0.30 |
| 2346334 | Crioulos | 11 | 0 | none | 0.36 | 0.38 |
| 2246090 | Joanópolis | 14 | 3 | 2015, 2017, 2020 | 0.50 | 0.55 |
| 2346010 | Nazaré Paulista (SP Águas) | 14 | 0 | none | 0.88 | 0.88 |
| 2346007 | Atibaia (SP Águas) | 3 | 1 | 2016 | 0.37 | 0.41 |
| 2346095 | Atibaia (ANA) | 8 | 1 | 2020 | 0.45 | 0.53 |
| 2246174 | Joanópolis (ANA) | 12 | 0 | none | 0.78 | 0.78 |
| 2346446 | Nazaré Paulista (ANA) | 12 | 0 | none | 0.61 | 0.61 |

## By year

| Code | Name | Year | Sites | r(-1) | r(0) | r(+1) | Best | Shifted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2346094 | Piracaia (ANA) | 2010 | 2 | 0.10 | 0.14 | 0.16 | +1 |  |
| 2346094 | Piracaia (ANA) | 2011 | 2 | 0.16 | 0.30 | 0.28 | +0 |  |
| 2346094 | Piracaia (ANA) | 2012 | 2 | 0.25 | 0.37 | 0.25 | +0 |  |
| 2346094 | Piracaia (ANA) | 2013 | 2 | 0.14 | 0.27 | 0.25 | +0 |  |
| 2346094 | Piracaia (ANA) | 2014 | 2 | 0.10 | 0.14 | 0.15 | +1 |  |
| 2346094 | Piracaia (ANA) | 2015 | 4 | 0.15 | 0.21 | 0.09 | +0 |  |
| 2346094 | Piracaia (ANA) | 2016 | 6 | 0.15 | 0.22 | 0.28 | +1 |  |
| 2346094 | Piracaia (ANA) | 2017 | 6 | 0.20 | 0.27 | 0.31 | +1 |  |
| 2346094 | Piracaia (ANA) | 2018 | 5 | 0.05 | 0.07 | 0.24 | +1 | **yes** |
| 2346094 | Piracaia (ANA) | 2019 | 3 | 0.16 | 0.21 | 0.18 | +0 |  |
| 2346094 | Piracaia (ANA) | 2020 | 4 | 0.20 | 0.33 | 0.60 | +1 | **yes** |
| 2346094 | Piracaia (ANA) | 2021 | 5 | 0.08 | 0.18 | 0.61 | +1 | **yes** |
| 2346094 | Piracaia (ANA) | 2022 | 9 | 0.10 | 0.28 | 0.64 | +1 | **yes** |
| 2346094 | Piracaia (ANA) | 2023 | 8 | 0.03 | 0.07 | 0.46 | +1 | **yes** |
| 2346094 | Piracaia (ANA) | 2024 | 12 | 0.01 | 0.36 | 0.76 | +1 | **yes** |
| 2346094 | Piracaia (ANA) | 2025 | 13 | 0.06 | 0.21 | 0.66 | +1 | **yes** |
| 2346334 | Crioulos | 2010 | 1 | 0.20 | 0.36 | 0.36 | +0 |  |
| 2346334 | Crioulos | 2011 | 1 | 0.47 | 0.60 | 0.50 | +0 |  |
| 2346334 | Crioulos | 2012 | 1 | 0.40 | 0.55 | 0.42 | +0 |  |
| 2346334 | Crioulos | 2013 | 1 | 0.26 | 0.42 | 0.31 | +0 |  |
| 2346334 | Crioulos | 2014 | 1 | 0.44 | 0.34 | 0.02 | -1 |  |
| 2346334 | Crioulos | 2015 | 3 | 0.09 | 0.65 | 0.13 | +0 |  |
| 2346334 | Crioulos | 2016 | 4 | 0.18 | 0.21 | 0.27 | +1 |  |
| 2346334 | Crioulos | 2017 | 4 | 0.12 | 0.35 | 0.22 | +0 |  |
| 2346334 | Crioulos | 2018 | 4 | 0.20 | 0.38 | 0.30 | +0 |  |
| 2346334 | Crioulos | 2019 | 2 | 0.19 | 0.34 | 0.11 | +0 |  |
| 2346334 | Crioulos | 2020 | 2 | 0.32 | 0.29 | 0.24 | -1 |  |
| 2246090 | Joanópolis | 2010 | 1 | 0.22 | 0.56 | 0.26 | +0 |  |
| 2246090 | Joanópolis | 2011 | 1 | 0.33 | 0.66 | 0.33 | +0 |  |
| 2246090 | Joanópolis | 2012 | 1 | 0.31 | 0.67 | 0.24 | +0 |  |
| 2246090 | Joanópolis | 2013 | 1 | 0.17 | 0.51 | 0.31 | +0 |  |
| 2246090 | Joanópolis | 2014 | 1 | 0.08 | 0.51 | 0.17 | +0 |  |
| 2246090 | Joanópolis | 2015 | 6 | 0.54 | 0.27 | 0.21 | -1 | **yes** |
| 2246090 | Joanópolis | 2016 | 6 | 0.60 | 0.49 | 0.31 | -1 |  |
| 2246090 | Joanópolis | 2017 | 5 | 0.54 | 0.35 | 0.21 | -1 | **yes** |
| 2246090 | Joanópolis | 2018 | 5 | 0.26 | 0.69 | 0.22 | +0 |  |
| 2246090 | Joanópolis | 2019 | 2 | 0.25 | 0.62 | 0.06 | +0 |  |
| 2246090 | Joanópolis | 2020 | 3 | 0.58 | 0.40 | 0.15 | -1 | **yes** |
| 2246090 | Joanópolis | 2021 | 5 | 0.42 | 0.27 | 0.17 | -1 |  |
| 2246090 | Joanópolis | 2022 | 6 | 0.09 | 0.06 | 0.02 | -1 |  |
| 2246090 | Joanópolis | 2023 | 5 | 0.23 | 0.40 | 0.13 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2010 | 1 | 0.23 | 0.93 | 0.20 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2011 | 1 | 0.26 | 0.87 | 0.21 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2012 | 1 | 0.26 | 0.89 | 0.32 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2013 | 1 | 0.12 | 0.88 | 0.12 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2014 | 1 | 0.10 | 0.95 | 0.09 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2015 | 1 | 0.13 | 0.94 | 0.13 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2016 | 2 | 0.33 | 0.87 | 0.36 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2017 | 2 | 0.32 | 0.89 | 0.25 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2018 | 1 | 0.28 | 0.89 | 0.26 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2019 | 1 | 0.20 | 0.91 | 0.20 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2020 | 2 | 0.25 | 0.39 | 0.10 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2021 | 2 | 0.08 | 0.49 | 0.35 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2022 | 3 | 0.21 | 0.35 | 0.22 | +0 |  |
| 2346010 | Nazaré Paulista (SP Águas) | 2023 | 3 | 0.11 | 0.19 | 0.04 | +0 |  |
| 2346007 | Atibaia (SP Águas) | 2016 | 1 | 0.29 | 0.37 | 0.55 | +1 | **yes** |
| 2346007 | Atibaia (SP Águas) | 2017 | 1 | 0.36 | 0.41 | 0.32 | +0 |  |
| 2346007 | Atibaia (SP Águas) | 2020 | 1 | 0.14 | 0.25 | 0.26 | +1 |  |
| 2346095 | Atibaia (ANA) | 2016 | 1 | 0.29 | 0.73 | 0.27 | +0 |  |
| 2346095 | Atibaia (ANA) | 2017 | 1 | 0.21 | 0.70 | 0.21 | +0 |  |
| 2346095 | Atibaia (ANA) | 2020 | 1 | 0.17 | 0.40 | 0.69 | +1 | **yes** |
| 2346095 | Atibaia (ANA) | 2021 | 1 | 0.13 | 0.16 | 0.29 | +1 |  |
| 2346095 | Atibaia (ANA) | 2022 | 1 | 0.40 | 0.43 | 0.33 | +0 |  |
| 2346095 | Atibaia (ANA) | 2023 | 1 | 0.20 | 0.23 | 0.14 | +0 |  |
| 2346095 | Atibaia (ANA) | 2024 | 2 | 0.07 | 0.46 | 0.41 | +0 |  |
| 2346095 | Atibaia (ANA) | 2025 | 2 | 0.24 | 0.60 | 0.22 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2015 | 4 | 0.14 | 0.76 | 0.12 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2016 | 4 | 0.28 | 0.79 | 0.34 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2017 | 3 | 0.20 | 0.72 | 0.31 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2018 | 3 | 0.27 | 0.69 | 0.28 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2019 | 1 | 0.08 | 0.85 | 0.10 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2020 | 2 | 0.31 | 0.77 | 0.39 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2021 | 3 | 0.10 | 0.85 | 0.14 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2022 | 4 | 0.27 | 0.80 | 0.25 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2023 | 4 | 0.15 | 0.75 | 0.33 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2024 | 4 | 0.29 | 0.79 | 0.17 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2025 | 4 | 0.25 | 0.61 | 0.17 | +0 |  |
| 2246174 | Joanópolis (ANA) | 2026 | 2 | 0.16 | 0.79 | 0.13 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2015 | 1 | 0.13 | 0.54 | 0.26 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2016 | 2 | 0.21 | 0.57 | 0.37 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2017 | 2 | 0.23 | 0.39 | 0.16 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2018 | 1 | 0.26 | 0.70 | 0.27 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2019 | 1 | 0.22 | 0.57 | 0.20 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2020 | 2 | 0.44 | 0.52 | 0.47 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2021 | 2 | 0.16 | 0.73 | 0.27 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2022 | 4 | 0.37 | 0.66 | 0.37 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2023 | 4 | 0.15 | 0.50 | 0.23 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2024 | 6 | 0.17 | 0.75 | 0.46 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2025 | 6 | 0.12 | 0.72 | 0.21 | +0 |  |
| 2346446 | Nazaré Paulista (ANA) | 2026 | 5 | 0.27 | 0.84 | 0.29 | +0 |  |
