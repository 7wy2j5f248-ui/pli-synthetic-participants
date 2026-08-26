# Run manifest

- **Run ID:** `R001`
- **PLI interview URL:** `https://interview-ashen-five.vercel.app/`
- **Authorized by:** Project owner; synthetic testing requested on 2026-08-26
- **Transcript destination:** PLI Supabase `interview_messages` and `interview_sessions`; locate through `https://interview-ashen-five.vercel.app/researcher.html` using the generated PLI Participant ID
- **Planned start:** `2026-08-26`
- **Maximum simultaneous interviews:** `1`

## Targets

| Language code | Language | Locale or audience note | Interviews |
| --- | --- | --- | ---: |
| `en` | English | Vary naturally | 2 |
| `zh` | Simplified Chinese | Vary naturally | 2 |
| `ar` | Arabic | Vary naturally | 2 |
| `es` | Spanish | Vary naturally | 2 |
| `fr` | French | Vary naturally | 2 |
| `pt` | Portuguese | Vary naturally | 2 |
| `tr` | Turkish | Vary naturally | 2 |
| `hi` | Hindi | Vary naturally | 2 |
| `bn` | Bengali | Vary naturally | 2 |
| `vi` | Vietnamese | Vary naturally | 2 |
| `ta` | Tamil | Vary naturally | 2 |
| `sw` | Swahili | Vary naturally | 2 |
| `ur` | Urdu | Vary naturally | 2 |
| `id` | Indonesian | Vary naturally | 2 |
| `so` | Somali | Vary naturally | 2 |
| `my` | Burmese | Vary naturally | 2 |
| `fa` | Persian / Farsi | Vary naturally | 2 |
| `prs` | Dari | Vary naturally | 2 |

Total planned interviews: **36**.

## Run-specific constraints

- Adults only: `yes`
- Required participant characteristics or quotas: Broad plausible variation across life stage, work rhythm, household, sleep pattern, attitudes, and location; no fixed demographic quotas
- Characteristics to exclude: Real people, prototype persona copies, medical emergencies, and stereotyped identity-trait combinations
- PLI completion signal: A localized completion banner appears with `data-completion-signal="INTERVIEW_COMPLETE"`, the page changes to `data-interview-status="completed"`, and the answer controls become disabled
- Rate or scheduling limit: Sequential interviews only
- Transcript reference: Record the visible generated PLI Participant ID as `participant:<ID>`

## Pilot gate

Complete `R001-EN-001` first. Confirm that its transcript is retrievable from the researcher dashboard before continuing the other 35 interviews. If transcript retrieval cannot be confirmed, stop with the remaining rows `pending` and record the problem on the smoke-test row.

## Stop conditions

Stop and mark the affected interview `blocked` if the endpoint is unavailable, consent cannot be completed honestly, access controls prevent participation, the assigned language cannot be produced reliably, PLI does not conclude after the planned interview, or the transcript cannot be located by its generated Participant ID.
