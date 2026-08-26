# PLI Synthetic Participants

This repository is a small operating kit for producing multilingual synthetic sleep-interview data quickly.

Claude creates a new, hidden participant for each interview. PLI conducts the interview. The analysis system receives the resulting transcript, not the hidden persona definition.

## Roles and boundary

| Role | Owns | Must not receive |
| --- | --- | --- |
| Claude | New hidden persona and consistent participant responses | PLI's interview logic or analysis conclusions |
| PLI | Interview questions and follow-ups | Hidden persona card or generation reasoning |
| Analysis | Completed interview transcripts | Hidden persona card during primary analysis |

## Start a run

1. Copy `templates/run-manifest.md` into `runs/<run-id>/manifest.md` and fill in the PLI URL, languages, and interview count.
2. Copy `templates/progress.csv` into the same run folder.
3. Open this repository in a browser-capable Claude session and say:

   > Follow `CLAUDE.md`. Execute the run in `runs/<run-id>/manifest.md`, completing the PLI interviews and updating the progress file as you go.

4. When the progress rows say `completed`, provide the transcript references to the analysis system.

The run needs only four decisions: the authorized PLI interview URL, target languages/locales, number of interviews per language, and where PLI stores or exports transcripts.

## Files

- `CLAUDE.md` — participant-generation and interview-execution protocol.
- `reference/persona-structure.md` — the structural pattern abstracted from the prototype Persona Bank.
- `templates/run-manifest.md` — one short control file per run.
- `templates/progress.csv` — one row per attempted interview.
- `runs/` — manifests and progress records. Do not store hidden personas here.

## Non-negotiable rules

- Generate entirely new fictional adults. Do not copy, translate, rename, or lightly modify a prototype persona.
- Create a different persona for every interview; do not translate one participant's answers across languages.
- Use the assigned language naturally throughout the interview, including culturally ordinary phrasing and uncertainty.
- Never claim a synthetic participant is a real person if PLI asks directly.
- Do not expose the hidden persona card to PLI or place it in the analysis transcript.
- Run only against an authorized test or research endpoint. Do not bypass consent, access controls, safety notices, or rate limits.

## A run is complete when

Every planned row is either `completed` with a transcript reference or `blocked` with a short reason. A completed transcript should be in the assigned language, remain internally consistent, and contain no hidden persona instructions.
