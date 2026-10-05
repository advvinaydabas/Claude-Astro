---
name: six-culture-verified-chart
description: Compute, independently verify, uncertainty-test, and synthesize a birth chart across Jyotisha, BaZi, Western/Hellenistic, Zi Wei Dou Shu, Maya-calendar, and Tibetan elemental traditions. Use for a requested six-culture chart or reading; do not use as scientific prediction or for medical, financial, legal, lifespan, death, or pregnancy claims.
---

# SIX-CULTURE VERIFIED CHART & READING v2

## Agent directive

When this file is invoked, do not install packages, write calculation code, or compute a chart before collecting the required birth data in Step 1. Follow the workflow in order.

The objective is calculation accuracy, reproducibility, convention transparency, and honest uncertainty. These controls do not make astrology a scientifically validated prediction method. Present the result as corroboration or disagreement among traditional symbolic systems, never as established causation or guaranteed future events.

Never invent a placement, dignity, star, period, element, meaning, date, or domain mapping. If a datum cannot be computed or verified, mark it unavailable and omit it from the reading.

## Step 1 — Collect birth data

Send this message and wait:

> To build your six-culture chart, please provide:
>
> 1. Date of birth — day, month, and year
> 2. Time of birth — include am/pm or use 24-hour time
> 3. Time certainty — exact from a certificate/record, rounded to the nearest 5–15 minutes, approximate, or unknown
> 4. Birthplace — city and country; hospital or district is helpful for a large city
> 5. Gender — required by some BaZi, Zi Wei, and Tibetan timing conventions
> 6. (Optional) Current residence — needed only for current-location timing methods such as a relocated solar return
>
> Please also mention whether the recorded date uses a non-Gregorian calendar or whether daylight-saving/time-zone uncertainty is possible.
>
> A wrong date or approximate time can change the chart. I will preserve uncertainty and will not silently rectify the birth time.

Do not proceed until date, time, birthplace, time certainty, and gender are available. If the user truly has no birth time, compute date-stable systems only and explicitly omit Ascendants, houses, divisional charts, Zi Wei hour-dependent placements, and other time-sensitive claims.

## Step 2 — Normalize and audit the input

Resolve and store:

- Original user-entered values without modification.
- Normalized Gregorian civil date and 24-hour local time.
- Decimal latitude, longitude, elevation if reliably available, and coordinate source.
- IANA time-zone identifier and the database release used.
- Historically correct UTC offset, DST status, and UTC instant.
- Civil weekday.
- Local mean solar time and local apparent solar time.
- Computed sunrise and sunset.
- The calendar conversion rule for dates originally recorded in another calendar.

Use the IANA time-zone database for post-1970 civil-time history. For earlier dates, report that historical civil time may be less reliable and seek a local historical source when the offset matters. Never infer a UTC offset from the modern offset alone.

### Boundary audit

Calculate and report the distance from every relevant boundary:

- Western and Jyotisha Ascendant/sign/house boundary.
- Jyotisha divisional-chart boundaries, especially D9 and D10.
- Sunrise/sunset and Western sect boundary.
- BaZi two-hour boundary, midnight/late-Zi day boundary, and exact sectional solar term.
- Zi Wei two-hour, civil-day, lunar-day, and leap-month boundary.
- Tibetan Losar/year boundary.
- Gregorian/Julian or other calendar-adoption boundary where applicable.

Do not merely label a chart "sensitive." State the boundary, computed instant, distance from it, and which outputs would change.

### Time-uncertainty ensemble

Create at least three calculation instants:

- T−uncertainty
- T reported
- T+uncertainty

Use the user's stated uncertainty. For a record exact only to the minute, use the possible rounding interval. If the user says "approximately" without a range, use a reasonable clearly disclosed range such as ±30 minutes; do not call this rectification.

Classify each result:

- **Stable:** unchanged across the entire interval.
- **Sensitive:** changes at one or more interval points.
- **Unavailable:** cannot be validly computed from the available time precision.

Only stable facts may receive high confidence. Display each sensitive alternative; never choose the more appealing chart.

## Step 3 — Create a reproducible calculation environment

After Step 2, create an isolated environment. Prefer Python 3.12 and pin exact package versions in a lockfile or manifest.

Preferred computational components:

- `pyswisseph` with downloaded Swiss Ephemeris data files as the primary astronomical engine.
- `skyfield` plus an appropriate JPL DE440/DE441 kernel as the independent astronomical validator.
- `zoneinfo`/`tzdata` and the current IANA time-zone release.
- `timezonefinder` for coordinate-to-zone lookup, followed by a historical-offset check.
- `lunar_python` for Chinese calendrical and BaZi calculations.
- A second Chinese-calendar calculation or direct astronomical solar-longitude calculation for solar-term validation.
- `immanuel` for Western chart objects only after explicitly configuring the required zodiac and house system.
- Canonical `iztro` plus `py-iztro` as an interface where useful. Treat them as the same underlying method, not independent engines.
- `convertdate` for Maya calendar conversion, with an independent round-trip and correlation-constant check.

If an engine or ephemeris file cannot be installed, continue only when a reliable fallback exists. Mark affected values as single-engine or unavailable. Do not claim two-engine verification merely because two wrappers call the same underlying ephemeris or library.

Record in `CALCULATION_MANIFEST.json`:

- Runtime and operating-system details.
- Package names and exact versions.
- Ephemeris filenames, versions, and checksums.
- IANA/tzdata release.
- Every zodiac, ayanamsha, node, house, calendar, day-boundary, solar-time, and school convention.
- Source-code checksum and execution timestamp.

## Step 4 — Compute deterministic datasets

Write a parameterized builder that reads `BIRTH_INPUT.json`. Never hardcode the person's data inside the calculation logic. The builder must produce facts only; interpretation belongs to the synthesis stage.

Use ISO-8601 timestamps with explicit offsets. Retain unrounded numeric values in JSON and round only for human display.

### 4A. Shared astronomical base

Compute:

- Julian day in UT and TT when required.
- Tropical apparent longitudes, latitudes, speeds, retrograde status, and relevant angles.
- Sidereal longitudes using the explicitly selected ayanamsha.
- Ascendant, MC, house cusps, sunrise, sunset, and solar-term crossings.
- Mean and true lunar nodes when a tradition requires one; never substitute silently.

Independently compare Swiss Ephemeris against JPL/Skyfield for the Sun, Moon, and planets. Store the absolute angular difference. A difference above the configured tolerance is a verification alert, not an invitation to average the answers.

Suggested alert thresholds for modern natal dates:

- Planetary longitude: > 0.01°.
- Ascendant/MC under identical conventions: > 0.05°.
- Solar-term instant: > 120 seconds.

These are alert thresholds, not claims about predictive significance.

### 4B. Jyotisha

Primary configuration:

- Sidereal zodiac.
- Lahiri ayanamsha unless the user requests a different school.
- Whole-sign houses for the primary Parāśari track.
- Explicit true-versus-mean node setting.

Compute:

1. D1/Rāśi chart with Lagna, graha positions, sign, degree, house, speed, retrogradation, combustion, planetary war where applicable, dignity, house ownership, and functional benefic/malefic status.
2. Nakshatra and pada for Lagna, Moon, and planets.
3. Graha dṛṣṭi and any sign aspects used by the selected school.
4. D9/Navāmśa and D10/Daśāmśa, but only when stable across the time-uncertainty interval.
5. D7 and D12 only when the relevant domain is requested and the birth time supports them.
6. Shadbala with component scores and units, or mark it unavailable if no validated implementation is present.
7. Ashtakavarga totals and bindus when timing/transit support is requested.
8. Vimshottari Mahadasha, Antardasha, and—only when time precision supports it—Pratyantardasha, with exact start and end timestamps.
9. A small, declared whitelist of classical yogas. Store the exact rule and placements that satisfy it; do not run unrestricted pattern mining.

Keep Parāśari, Jaimini, KP, tropical-Vedic, and alternative-ayanamsha results in separate tracks. Never combine them into one vote.

### 4C. BaZi

Compute both local civil time and local apparent solar time. Choose the primary track according to the declared school; retain the alternative whenever it changes a pillar.

Compute:

1. Exact astronomical sectional solar terms and distance of birth from the active term.
2. Four Pillars using an explicit day-boundary rule, including the late-Zi convention.
3. Heavenly stems, earthly branches, hidden stems, elements, polarity, and Na Yin as a separately labeled traditional attribute.
4. Ten Gods for visible and hidden stems.
5. Seasonal strength, rooting, support, draining, controlling, and Day Master strength using a documented rule set.
6. Stem combinations and branch combinations, clashes, harms, punishments, destructions, and transformations, without forcing a transformation when its required conditions are absent.
7. Da Yun direction, exact start calculation, period pillars, and boundary dates.
8. Annual and monthly pillars only for requested timing windows.

Useful God/Yong Shen and favorable-element judgments are school-dependent. Name the school, expose the rule chain, assign no higher than medium confidence unless multiple declared schools agree, and display disagreements rather than selecting one silently.

### 4D. Western/Hellenistic

Primary configuration:

- Tropical zodiac.
- Whole-sign houses.
- Seven traditional planets for the Hellenistic score.
- Day/night sect calculated from the actual horizon.

Compute:

1. Ascendant, MC, planets, signs, whole-sign houses, angularity, speed, retrogradation, visibility/combustion, and sect status.
2. Essential dignity: domicile, exaltation, triplicity, bounds/terms, and face, with the selected table named.
3. House rulers, dispositors, and final-dispositor chains.
4. Applying and separating aspects with explicit orbs and aspect perfection where calculable.
5. Lot of Fortune and Lot of Spirit using the correct day/night formula.
6. Annual profection, activated house, ruler of the year, and its natal condition.
7. Solar return and transits only when timing is requested. State whether the return uses birthplace or current location; compute both if that convention materially changes the result.
8. Zodiacal releasing from Fortune or Spirit only when the Lots and implementation are validated.

Modern outer planets, modern aspect patterns, Placidus houses, psychological astrology, primary directions, and other schools must be separate optional tracks. They cannot add votes to the Hellenistic cluster.

### 4E. Zi Wei Dou Shu

Declare the implementation version, school/configuration, lunar-calendar conversion, leap-month treatment, day boundary, time index, gender encoding, and direction rule.

Compute:

1. Solar and lunar birth dates and leap-month status.
2. Ming and Shen palaces.
3. Twelve palaces with earthly branches.
4. Fourteen major stars and their brightness/temple status when supported.
5. Life ruler, body ruler, and Five-Elements Bureau.
6. Four Transformations/四化 with the transformation source year or stem.
7. Declared minor-star set, separated from major-star evidence.
8. Decadal, annual, and monthly periods with exact age convention.

Cross-check canonical JavaScript `iztro` output against the Python wrapper for serialization or interface errors, but count both as one method. Verify there are 12 unique palaces and that major-star placement invariants hold for the selected implementation.

### 4F. Maya calendar

Compute:

- Long Count using an explicit correlation constant, normally GMT 584283 unless the user requests another scholarly convention.
- Tzolkʼin number and day name.
- Haabʼ day and month.
- Calendar Round.
- Exact round-trip to the source Gregorian date.

The Maya calculation is date-based. Do not treat contemporary internet "Maya zodiac personality" descriptions as computed facts. A day-sign meaning may be used only as an attributed symbolic overlay tied to a named historical or living Maya source. It never contributes to the nine-domain convergence grade.

### 4G. Tibetan elemental astrology

First validate the Tibetan calendar conversion and Losar boundary. If a reliable lineage-specific implementation is available, compute:

- Element, animal, gender, and 60-year cycle.
- Mewa.
- Parkha.
- Life, body/health, power, wind-horse/fortune, and soul forces when their formulas and anchors are validated.
- Annual relations and obstacles with the source tradition named.

If Mewa, Parkha, or personal-force anchors are not validated, omit them. Retain only the verified element-animal year and label it a limited symbolic overlay. Tibetan symbolism does not contribute to a life-domain grade unless a complete, sourced domain method was actually computed.

## Step 5 — Verification report

Create `VERIFICATION_REPORT.json` and `.md`. Every material datum must include:

```json
{
  "system": "western",
  "datum": "Sun tropical longitude",
  "primary_engine": "Swiss Ephemeris",
  "primary_value": 0.0,
  "validator": "JPL/Skyfield",
  "validator_value": 0.0,
  "difference": 0.0,
  "convention": "geocentric apparent tropical",
  "boundary_distance": null,
  "uncertainty_stability": "stable",
  "confidence": "high",
  "status": "pass"
}
```

Confidence rules:

- **High:** independently verified, convention-matched, within threshold, and stable across the uncertainty interval.
- **Medium:** one trusted implementation and stable, or a school-dependent result with clear rules.
- **Low:** boundary-sensitive, weakly validated, or materially school-dependent.
- **Unavailable:** insufficient input or no validated method.

Required invariants include:

- Rahu–Ketu separation equals 180° for the selected node type.
- Vimshottari full-cycle lord years total 120.
- BaZi birth falls on the stated side of the exact solar-term instant.
- Zi Wei has 12 unique palaces.
- Maya conversion round-trips exactly.
- All timing periods are continuous, ordered, and non-overlapping within their own system.
- No "independent" validator shares the same underlying calculation code without disclosure.

If an invariant fails, stop interpretation of the affected system. Report the failure rather than repairing it with guessed values.

## Step 6 — Build the master dataset

Emit:

- `BIRTH_INPUT.json`
- `INPUT_AUDIT.md`
- `CALCULATION_MANIFEST.json`
- `MASTER_DATASET.json`
- `MASTER_DATASET.md`
- `VERIFICATION_REPORT.json`
- `VERIFICATION_REPORT.md`

`MASTER_DATASET.json` must retain:

- Original and normalized input.
- All conventions and versions.
- Raw calculations.
- Time-uncertainty alternatives.
- Verification status and confidence.
- Exact timing ranges.
- Missing or excluded methods with reasons.

Do not place prose interpretation in the master dataset.

## Step 7 — Synthesis without double-counting

### Primary domain-capable clusters

Use only these primary votes:

1. Jyotisha
2. Western/Hellenistic
3. Sinic, where BaZi and Zi Wei may corroborate one another internally but together contribute at most one cross-cultural vote

Maya and limited Tibetan elemental results are temperament overlays, not domain votes. If a complete validated Tibetan domain method is available, report it separately before deciding whether it merits an additional vote; never assume it is independent merely because it has a different cultural label.

### Nine domains

- D1 Self/identity
- D2 Career/status
- D3 Wealth/gains
- D4 Partnership
- D5 Family/roots/home
- D6 Children/creation
- D7 Health/routine
- D8 Mind/education/craft
- D9 Fortune/spirituality/worldview

Project each fact through a predeclared mapping registry. Each projection must contain:

```json
{
  "domain": "D2",
  "system": "jyotisha",
  "cluster": "jyotisha",
  "prominence": "high",
  "polarity": "mixed",
  "confidence": "high",
  "basis": "exact computed datum",
  "mapping_rule": "rule identifier"
}
```

Distinguish prominence from polarity. A heavily occupied career house establishes career prominence; it does not guarantee career success. A difficult dignity may make the polarity mixed without erasing prominence.

Never remap a fact to create agreement. Include disconfirming projections. Silence is not agreement, and an empty palace is not automatically negative.

### Domain grades

- **STRONG:** all three primary clusters agree on the material theme.
- **MODERATE:** two primary clusters agree.
- **WEAK:** only one primary cluster speaks.
- **DIVERGENT:** at least two primary clusters materially conflict.
- **INSUFFICIENT:** no defensible basis.

Report both:

- Divergent domains divided by all nine domains.
- Divergent domains divided by domains with sufficient evidence.

Do not describe non-divergent weak domains as agreement.

### Temperament axes

- T1 Leadership/visibility
- T2 Drive/initiative
- T3 Nurturing/service
- T4 Intellect/craft
- T5 Adaptability
- T6 Discipline/structure

Jyotisha, Western, and Sinic systems provide computed temperament bases. Maya and Tibetan meanings must be labeled attributed symbolism and may only corroborate, soften, or dissent. They never upgrade the domain grades.

### Chronology

Overlay on one ISO-date axis:

- Jyotisha Vimshottari periods.
- BaZi Da Yun and requested annual/monthly pillars.
- Western profections plus validated return/transit activations.
- Zi Wei decadal and annual periods.

A timing window is:

- **Moderate:** two primary clusters independently activate the same domain.
- **Strong/⭐:** all three primary clusters activate the same domain.

Do not create a convergence by combining multiple techniques inside one cluster. State the exact beginning and end determined by the overlap. If no current convergence exists, say so plainly.

## Step 8 — Present the reading

Create `SYNTHESIS.json` and `FINAL_READING.md`, then present a concise version to the person.

Use this order:

1. **Input and sensitivity summary** — normalized birth instant, weekday, location, historical offset, and every material boundary.
2. **Verification summary** — engines, largest differences, failures, and unavailable methods.
3. **Divergence rate** — before positive themes.
4. **Strongest cross-cultural themes** — STRONG first, then MODERATE; cite each system and exact basis.
5. **Disagreements** — do not smooth them over.
6. **Weak and insufficient areas** — explicitly prevent over-reading.
7. **Temperament overlay** — mark Maya/Tibetan content as symbolic.
8. **Timing** — current and next moderate/strong window, or state that none exists.
9. **Closing frame** — repeat that this is computed symbolic corroboration, not a validated forecast.

Every interpretive sentence must be traceable to `SYNTHESIS.json`. Do not introduce a placement, date, number, star, dignity, aspect, period, or symbolic meaning that is absent from the dataset and mapping registry.

## Safety and anti-fabrication rules

- Never claim certainty, fate, inevitability, supernatural validation, or scientific proof.
- Never give a medical diagnosis, treatment recommendation, lifespan/death prediction, pregnancy/fertility claim, guaranteed financial outcome, or legal conclusion.
- Never use rectification to select a chart that best fits a biography unless the user explicitly requests a separate rectification exercise; even then, label it hypothesis testing rather than fact.
- Never average conflicting engines or schools.
- Never use multiple wrappers around the same engine as independent corroboration.
- Never count natal repetition and timing repetition inside one system as two cultural votes.
- Drop generic Barnum claims that would fit most people.
- Report how many candidate claims were removed for missing basis, low confidence, or duplication.
- Preserve raw data and provenance so another agent can reproduce the result.

## Completion checklist

Do not call the task complete unless:

- [ ] Required birth inputs were collected.
- [ ] Historical civil time and coordinates were audited.
- [ ] Boundary and uncertainty ensembles were computed.
- [ ] Conventions and versions were recorded.
- [ ] Each available system passed its invariants.
- [ ] Independent verification was genuine and disclosed.
- [ ] Missing methods were explicitly listed.
- [ ] Synthesis used primary-cluster counting and separated prominence from outcome.
- [ ] Disagreements and weak evidence were presented.
- [ ] Timing windows used exact overlaps.
- [ ] The final caveat was included.

## Technical references

- [IANA Time Zone Database](https://www.iana.org/time-zones/tz-link)
- [Swiss Ephemeris documentation](https://www.astro.com/swisseph-download/doc/swisseph.htm)
- [Swiss Ephemeris programming interface](https://www.astro.com/swisseph/swephprg.htm)
- [iztro documentation](https://docs.iztro.com/en_US/quick-start)
- [py-iztro repository and underlying-version notes](https://github.com/x-haose/py-iztro/blob/master/README.md)

## Final standing instruction

Ask first. Audit civil time and uncertainty. Compute by declared conventions. Verify with genuinely independent engines. Preserve disagreements. Synthesize by primary cultural cluster. Present only evidence-supported symbolic themes, never promises or predictions.
