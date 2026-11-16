# Data requests: drafts, not sent

Drafted 15 November 2026. **Nothing here has been sent.** Each letter is in
Portuguese with an English summary. Fill in the bracketed fields, and check
each recipient's correct channel and addressee before sending: the units
named below are my best guess from public pages, not confirmed contacts.

**Update, 16 November 2026: part of this is already public.** SP Águas' SIBH
portal (https://cth.daee.sp.gov.br/sibh/) has an open JSON API, no login, that
serves records the letters below ask for. Check it before sending, and trim the
letters accordingly.

- **Letter 5 (CEMADEN):** all eight named gauges are in SIBH as 10-minute
  records since 2014–2015, and are now in the pipeline
  (`docs/sibh_rain_report.md`). Their transmissions have gaps: CEMADEN Cachoeira
  has 802 complete days in 11 years. The request is still worth sending, but
  only for the complete logger records.
- **Letter 2 (SP Águas):** item 4 (rain) is largely answered by the telemetric
  gauges now used. The flow stations are now downloaded and checked
  (`docs/sibh_flow_report.md`):
  - Item 3 (gauges above the reservoirs) is answered in part. Atibainha
    Montante (3E-121) has stage and discharge, nearly complete from 2018;
    Cachoeira Montante (3E-122) from 2022, with a few weeks in 2015–2021. Both
    come into SIBH from ANA's telemetry. Still to ask: their **drainage areas**
    (published nowhere we found), and why 3E-122 reads more than the
    operator's inflow to the whole Cachoeira reservoir (1.11 times overall,
    1.50 in 2025).
  - Item 2 (rating curves) is answered only in part. SIBH publishes curves
    for 3E-116 (2001–2016) and 3E-122 (2015–2020), none for 3E-121 or 3E-145.
    The discharge SIBH serves for 3E-122 does not follow its published curves,
    and 3E-121's rating changed in 2023 and 2024 (23–41% more discharge for the
    same stage). After 2016, 3E-116's discharge comes from an expired curve.
    Ask for the **rating histories and discharge measurements** of 3E-116,
    3E-121, 3E-122 and 3E-145.
  - Item 1: SIBH's Piracaia (Captação), 3E-116, probably the gauge the letter
    calls Captação de Piracaia (62665900), has 10-minute stage from 2010 to the
    present. The Atibaia gauge (62669900) has not been checked yet.
- **Letter 1 (Sabesp):** checked. Trim and extend as follows.
  - Item 1 (tunnel flows) is answered in part: Tunnel 6 and Tunnel 5 outlet
    flows are public on SIBH (Tunnel 5 from 2014, Tunnel 6 complete from
    2020). Still needed: **Tunnel 7** (SIBH has only the Jacareí reservoir
    level), **Santa Inês**, and anything before 2014.
  - Item 2 (Paraíba do Sul transfer) is not answered: SIBH's two transfer
    stations return no data and the pumping station has only a level. From
    the balance with the measured tunnels we estimate a median of 5–8 m³/s a
    year in 2019–2022 and 2024–2026 and about none in 2023. Cite this and ask
    for the measured series.
  - Item 3 (how inflow is computed): the same balance shows that SAR's
    Atibainha inflow does not include the Paraíba do Sul transfer. Say so;
    the question about the method still stands.
  - Item 4 (measured outflow) is not answered: Sabesp's stations at the dams
    hold the reservoir level and the downstream-channel level only. Update the
    reason given. On most of the days the Piracaia gauge reads short, the river
    1 km below Cachoeira dam (3E-116) stands as high as usual for the reported
    release, so the release probably did reach the river. 2022 is the
    exception that may point at the release.
  - Item 7: Conrado (62664000) and the SB-CA river gauges were not among the
    stations checked.
- **Letters 3 and 4 (ANA, SGB), gauge below release at 62665000:** add to the
  evidence that the river level just below the dam does not drop on most
  shortfall days. In 2025, SP Águas' telemetric gauge beside 62665000 (3E-145)
  reads short on 13 days where 62665000 reads short on 89. Both point at
  62665000's rating, which makes the request for its rating history
  stronger. Letter 3, item B4 (does inflow include the Paraíba do Sul
  water?): our evidence says no (see letter 1, item 3); keep the question as
  a confirmation.
- **New finding for letters 3 and 4 (ANA, SGB):** the Piracaia rain gauge
  2346094 is one day out against every nearby telemetric gauge in every year
  from 2018 to 2025 (`docs/rain_alignment.md`): its day D holds the rain that
  the others record on D+1. It is worth asking whether its reading-date
  convention changed around 2016–2018.

Every request cites what our own analysis of the public records found, so the
recipient can see the request is specific and that we have done the work
first. The supporting reports are in this folder.

## Who to ask for what

| # | Recipient | What is asked | What it would unlock | Priority |
| --- | --- | --- | --- | --- |
| 1 | Sabesp | Daily tunnel and transfer flows; how inflow is computed; measured outflows; volume-curve history | Closing the reservoir water balance; resolving the doubtful pre-2000 inflow record | Highest |
| 2 | SP Águas / FCTH | 10-minute telemetry archive, rating curves, upstream gauges, state rain gauges | A second rainfall source; gauges above the reservoirs; sub-daily data | High |
| 3 | ANA | API access; rating history at two gauges; explanations of four anomalies in the reservoir records | Channel sections and rating uncertainty; fixing known gaps | High |
| 4 | SGB (CPRM) | Review of two stations it operates for ANA | Trustworthy rainfall at Piracaia; resolving gauge-below-release days | Medium |
| 5 | CEMADEN | Bulk history for eight rain gauges from 2014 | Rain coverage for 2022 onward, where only one gauge remains | Medium |
| 6 | Agência das Bacias PCJ | Forecast archive; aggregate abstraction data; restoration site records | A benchmark for any future model; demand; a restoration layer | Medium |

A Brazilian partner institution should send or co-sign these. ANA's API
credentials are issued against a Brazilian tax number (CPF or CNPJ), and
several state portals did not respond from outside Brazil.

---

## Common opening and closing (use in every letter)

**Abertura**

> Prezados(as) Senhores(as),
>
> Escrevo em nome de [instituição], no âmbito de um estudo-piloto de
> segurança hídrica na sub-bacia do alto Atibaia (Sistema Cantareira / Bacias
> PCJ), conduzido por [instituição] em parceria com [parceiro brasileiro]. O
> estudo utiliza exclusivamente dados públicos e tem finalidade de pesquisa,
> sem fins comerciais.
>
> Analisamos os registros diários públicos de 1984 a 2026 (reservatórios no
> SAR/ANA, vazões e chuvas no serviço de dados da ANA). Os resultados e os
> métodos estão documentados e podem ser compartilhados integralmente. A
> análise identificou questões específicas que só podem ser resolvidas com
> dados ou esclarecimentos de V.Sas., descritos abaixo.

**Fechamento**

> Comprometemo-nos a citar a fonte, a não redistribuir os dados sem
> autorização e a compartilhar com V.Sas. os resultados e as inconsistências
> que encontrarmos. Caso exista um procedimento formal para este tipo de
> solicitação, agradecemos a indicação do canal adequado.
>
> Atenciosamente,
> [nome], [cargo], [instituição], [contato]

*English: opening states who we are, that the pilot uses only public data for
non-commercial research, that we analysed the public daily records for
1984–2026 and found specific questions only the recipient can resolve. Closing
commits to citing the source, not redistributing without permission, and
sharing results and any inconsistencies found, and asks for the proper channel
if a formal procedure exists.*

---

## 1. Sabesp

**To:** Sabesp, [área responsável pela operação do Sistema Cantareira /
recursos hídricos]. Sabesp is a private company since July 2024; a request
through ANA or the Comitês PCJ may carry more weight than a direct one.

**Assunto:** Solicitação de dados operacionais do Sistema Cantareira para
pesquisa (alto Atibaia)

> Solicitamos, para os reservatórios Jaguari-Jacareí, Cachoeira, Atibainha e
> Paiva Castro:
>
> 1. **Vazões diárias transferidas pelos túneis** (túneis 7, 6 e 5) e a vazão
>    bombeada na Elevatória Santa Inês, de 1984 até o presente. No SAR/ANA a
>    defluência publicada exclui as transferências pelos túneis; sem elas o
>    balanço hídrico de cada reservatório não fecha.
> 2. **Vazões diárias recebidas da interligação Jaguari–Atibainha** (bacia do
>    Paraíba do Sul), desde o início da operação.
> 3. **O método de cálculo da afluência diária** publicada, e as datas em que
>    ele ou as curvas cota-área-volume foram alterados. Os registros indicam
>    volumes úteis de referência diferentes ao longo do tempo: Atibainha cerca
>    de 130 hm³ até 1999, 100 hm³ até 2003, 99 hm³ até 2008, 100 hm³ até março
>    de 2010 e 96,25 hm³ desde então; Jaguari-Jacareí cerca de 599 hm³ entre
>    janeiro e agosto de 2004, entre períodos com cerca de 808 hm³.
> 4. **Vazões defluentes medidas** (não apenas as programadas) nas barragens
>    Cachoeira e Atibainha. Em 2017, 2018 e 2022, em cerca de 100 dias por
>    ano, o posto fluviométrico de Piracaia (62665000), a jusante, registra
>    mais de 0,5 m³/s abaixo da defluência informada de Cachoeira.
> 5. **Registros de Paiva Castro de 2000 a 2003**, ausentes no SAR.
> 6. **Curvas cota-área-volume vigentes e levantamentos batimétricos** dos
>    quatro reservatórios.
> 7. **Séries dos postos operados pela Sabesp** a montante dos reservatórios
>    (por exemplo Conrado, 62664000, e os postos SB-CA), que não retornam
>    dados no serviço público da ANA.
>
> A afluência diária publicada apresenta ruído elevado: em períodos sem chuva
> ela aumenta em cerca de metade dos dias. Qualquer informação sobre a
> incerteza desse cálculo também seria de grande valia.

*English: asks for (1) daily tunnel flows and Santa Inês pumping since 1984,
because published releases exclude tunnel transfers and the balance does not
close; (2) daily flows received from the Paraíba do Sul link; (3) the method
used to compute daily inflow and the dates it or the volume curves changed,
citing the capacity changes we recovered; (4) measured, not scheduled, dam
outflows, citing the gauge-below-release days; (5) the missing Paiva Castro
records for 2000–2003; (6) current volume curves and bathymetry; (7) series
from Sabesp gauges upstream of the reservoirs. It notes that published daily
inflow rises on about half of rainless days and asks about its uncertainty.*

---

## 2. SP Águas (formerly DAEE) and FCTH

**To:** SP Águas, [diretoria / centro responsável pela rede hidrológica], with
copy to FCTH, which operates the PCJ telemetric network. As a public body,
SP Águas can also be asked through the state access-to-information channel.

**Assunto:** Solicitação de séries históricas da rede telemétrica e
pluviométrica das Bacias PCJ para pesquisa

> Solicitamos:
>
> 1. **Série histórica completa (10 minutos) de nível, vazão e chuva** dos
>    postos telemétricos do rio Atibaia e afluentes, em especial Atibaia
>    (62669900), Captação de Valinhos (62678150), Bairro da Ponte (62676000),
>    Nazaré Paulista (62662000) e Captação de Piracaia (62665900). No serviço
>    público da ANA, esses postos não retornam dados telemétricos, e as séries
>    diárias de alguns terminam em 2014 ou 2022.
> 2. **Curvas-chave, com histórico de alterações, e medições de descarga**
>    desses postos, e as seções transversais levantadas anualmente.
> 3. **Séries dos postos a montante dos reservatórios**, Cachoeira Montante
>    (62664500) e Atibainha Montante (62654500), em operação desde 2014. São
>    os únicos postos que mediriam a afluência de forma independente do
>    balanço do reservatório.
> 4. **Séries diárias dos postos pluviométricos** da região (Piracaia,
>    Crioulos, Joanópolis, Nazaré Paulista, Ribeirão Acima, Atibaia), incluindo
>    eventuais dados de qualidade ou consistência.
>
> Para informação de V.Sas., uma auditoria entre postos vizinhos indicou
> registros anômalos no posto Crioulos (2346334): 705 mm em 2018 e 824 mm em
> 2019, contra cerca de 1.160 a 1.200 mm nos postos próximos. Podemos enviar
> o relatório completo.

*English: asks for (1) the full 10-minute archive of stage, flow and rain at
five named gauges, which return no telemetry on ANA's public service; (2)
rating curves with their revision history, discharge measurements and yearly
cross-sections; (3) series from the two gauges upstream of the reservoirs,
the only independent measure of inflow; (4) daily series from the state rain
gauges. It reports our audit finding on the Crioulos gauge and offers the
full report.*

---

## 3. ANA

**To:** ANA, Superintendência de Gestão da Rede Hidrometeorológica, for the
API (the manual gives hidro@ana.gov.br for token requests), and the Sala de
Situação for the reservoir records. ANA is a federal public body, so the
access-to-information channel is also available.

**Assunto:** Acesso à API HidroWebService e esclarecimentos sobre registros do
Sistema Cantareira no SAR

> **A. Acesso à API HidroWebService.** Solicitamos credenciais para
> [instituição brasileira, CNPJ] a fim de obter perfis transversais, curvas de
> descarga e resumos de medição de descarga dos postos 62670000 (Atibaia) e
> 62665000 (Piracaia).
>
> **B. Esclarecimentos sobre o SAR, módulo Cantareira:**
>
> 1. Não há registros de **Paiva Castro entre 2000 e 2003**. Os dados existem
>    em outra base?
> 2. Os percentuais de volume útil implicam **volumes de referência que
>    mudaram** em 1999, 2004 e 2010 (por exemplo, Atibainha de cerca de 130
>    para 96,25 hm³). Existe documentação dessas revisões, e as séries de
>    volume anteriores foram recalculadas?
> 3. Entre janeiro e agosto de 2004, **Jaguari-Jacareí** apresenta volume de
>    referência de cerca de 599 hm³. Trata-se de erro de registro?
> 4. A **afluência diária** é a afluência natural? Ela inclui a água recebida
>    da interligação com o Paraíba do Sul desde 2018?
>
> **C. Postos da rede.** O posto pluviométrico **Piracaia (2346094)** registra
> 217 mm em 2018 e 214 mm em 2019, contra cerca de 1.160 a 1.200 mm nos postos
> vizinhos, e valores muito altos em 2010 e 2016. No posto fluviométrico
> **Piracaia (62665000)**, a vazão fica abaixo da defluência informada da
> barragem Cachoeira em cerca de 100 dias por ano em 2017, 2018 e 2022.
> Algumas séries brutas contêm o valor 100000,0 como marcador. Enviamos estas
> observações como contribuição à consistência dos dados.

*English: (A) asks for API credentials for the Brazilian partner, to obtain
cross-sections, rating curves and discharge measurements at two gauges. (B)
asks four questions about the reservoir records: the missing Paiva Castro
years, documentation of the capacity revisions and whether earlier volumes
were recomputed, the anomalous 2004 capacity for Jaguari-Jacareí, and whether
daily inflow is natural inflow and includes Paraíba do Sul transfers. (C)
reports the faulty Piracaia rain gauge, the gauge-below-release days, and the
100000.0 placeholder, as a contribution to data quality.*

---

## 4. SGB (Serviço Geológico do Brasil / CPRM)

**To:** SGB, [superintendência regional responsável pela operação da rede em
São Paulo]. SGB operates stations for ANA.

**Assunto:** Possíveis inconsistências nos postos Piracaia (2346094 e
62665000)

> Em análise de dados públicos, identificamos duas questões nos postos de
> Piracaia operados por V.Sas.:
>
> 1. **Pluviômetro 2346094.** Totais anuais de 451 mm (2014), 633 mm (2017),
>    217 mm (2018) e 214 mm (2019), contra 950 a 1.300 mm nos postos vizinhos,
>    e totais acima de 2.300 mm em 2010 e 2016. Vinte e cinco meses têm total
>    inferior a 25% da mediana regional. Houve falha de equipamento ou de
>    observação nesses períodos?
> 2. **Fluviômetro 62665000.** Em 2017, 2018 e 2022, em cerca de 100 dias por
>    ano, a vazão registrada é mais de 0,5 m³/s inferior à defluência
>    informada da barragem Cachoeira, situada a montante. Houve alteração da
>    curva-chave ou da seção nesses anos?
>
> Solicitamos, se possível, o histórico de curvas-chave e de medições de
> descarga do posto 62665000 e as fichas de inspeção do posto 2346094.

*English: reports the two problems at the Piracaia stations (rain gauge
totals far below neighbours in four years and far above in two; river gauge
below the reported dam release on about 100 days a year in three years),
asks whether there was an equipment, observation, rating or section change,
and requests the rating and measurement history and inspection records.*

---

## 5. CEMADEN

**To:** CEMADEN, [coordenação de operações / atendimento a pesquisadores].

**Assunto:** Solicitação de séries históricas de pluviômetros automáticos
(Piracaia, Joanópolis e Nazaré Paulista)

> Solicitamos as séries históricas completas, desde 2014, dos pluviômetros
> automáticos Piracaia_Caras, Piracaia_Dobrada e Piracaia_Pião;
> Joanópolis_Cachoeira, Joanópolis_joanopolis02, Joanópolis_joanopolis03 e
> Joanópolis_Centro; e Nazaré Paulista_ETA Sabesp.
>
> O Mapa Interativo permite o download mensal por estado mediante CAPTCHA, o
> que inviabiliza a obtenção de doze anos de dados para vários postos.
> Existindo acesso por API ou por arquivo consolidado, agradecemos a
> orientação sobre como solicitá-lo.
>
> Os postos convencionais da região tornaram-se escassos: de 2022 a 2025, a
> bacia de contribuição do reservatório Cachoeira conta com um posto ou
> nenhum em 775 dias.

*English: asks for the full history since 2014 of eight named automatic rain
gauges, explains that the interactive map's monthly, per-state, CAPTCHA-gated
download makes twelve years impractical, asks how to obtain API or bulk
access, and notes that conventional gauges have thinned to one or none on 775
days in 2022–2025 for the Cachoeira catchment.*

---

## 6. Agência das Bacias PCJ (and Comitês PCJ)

**To:** Fundação Agência das Bacias PCJ, [coordenação de sistema de
informações / apoio ao Comitê], with copy to the monitoring chamber (CT-MH).

**Assunto:** Solicitação de dados para estudo de segurança hídrica no alto
Atibaia

> Solicitamos:
>
> 1. **Arquivo das previsões do SPHM-PCJ** (sistema de previsão
>    hidrometeorológica em operação desde 2019) para os pontos de controle do
>    rio Atibaia, a fim de servir de referência a qualquer modelo que venhamos
>    a propor.
> 2. **Dados agregados de captações e lançamentos** a montante dos pontos de
>    controle Atibaia e Valinhos, por setor e por mês. Não solicitamos dados
>    individualizados de usuários.
> 3. **Registros espaciais dos projetos de restauração e de pagamento por
>    serviços ambientais** na bacia (localização, área e data de implantação).
> 4. **Camadas geográficas** do Plano das Bacias PCJ 2020–2035.
>
> Gostaríamos também de apresentar os resultados ao Comitê. Um deles pode ser
> de interesse: a fração da chuva que se converte em afluência aos
> reservatórios caiu de cerca de 0,32 (2004–2013) para cerca de 0,19
> (2014–2016), o que foi confirmado em uma área medida apenas por postos
> fluviométricos, e recuperou-se apenas em parte desde então.

*English: asks for (1) the archive of the operational forecast system, as a
benchmark for any future model; (2) aggregate abstraction and return-flow data
by sector and month upstream of the two control points, explicitly not
per-user data; (3) spatial records of restoration and payment-for-services
projects; (4) the basin plan's GIS layers. It offers to present the results
and mentions the fall in runoff share as a finding of interest.*

---

## Before sending: checklist

- [ ] A Brazilian partner institution has agreed to send or co-sign.
- [ ] Each addressee and channel has been confirmed.
- [ ] Bracketed fields are filled in.
- [ ] The supervisor has approved sharing the findings quoted in the letters.
- [ ] The reports to attach are chosen: `data_quality_report.md`,
      `rain_audit.md`, `runoff_shift_investigation.md`.
- [ ] A native Portuguese speaker has reviewed the text.
