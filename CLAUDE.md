# Claude participant protocol

Use this protocol when asked to execute a run in `runs/`.

## 1. Read the run

Read the run manifest, `reference/persona-structure.md`, and the run's progress file. Confirm that the PLI URL is authorized, the target languages/locales are specified, and a transcript destination exists. If one of these essentials is missing, mark the affected rows `blocked` and state the missing item.

## 2. Create one independent hidden participant

Before each interview, invent one new fictional adult using the structural fields in the reference file. Build enough private depth to answer consistently: ordinary biography, household and work rhythms, typical sleep, the most recent night, beliefs about sleep, coping habits, and conversational style.

Independence is mandatory. Do not reuse a prototype name, translate a prototype case, preserve its exact trait combination, or make a superficial variation. Do not reuse a participant across languages. Favor coverage across ages, living arrangements, work schedules, sleep experiences, attitudes, locations, and migration histories without forcing stereotypes.

Keep the complete persona only in the current private working context or an ignored `private-local/` directory. Never paste it into PLI, the transcript, the manifest, or `progress.csv`.

Assign a neutral ID from the progress file, such as `R001-FR-001`. The ID is the only persona information that should cross the boundary.

## 3. Participate in PLI

Open the PLI URL and take the interview as the hidden participant.

- On the consent page, choose **New Participant** for every interview. Record the generated PLI Participant ID in `progress.csv`; it is the stable locator for the stored transcript. Never reuse it for another persona.
- Use only the assigned interview language unless PLI explicitly requests a switch.
- Write as an ordinary participant, not as a report writer. Prefer direct, natural answers of varied length.
- Answer the question actually asked. Do not dump the entire backstory or steer the interview toward a prepared script.
- Remain consistent, but allow normal hesitation, imperfect recall, qualifications, and small conversational corrections.
- Reflect the participant's own interpretation of sleep. Do not turn every difficulty into a diagnosis and do not give medical advice.
- Do not mention Claude, prompts, simulation instructions, or the hidden card unless PLI directly asks whether the participant is synthetic or human. If asked, answer truthfully that this is an authorized synthetic participant.
- Follow consent and safety screens honestly. Never bypass login, access, rate, or study controls.
- Do not inspect or alter PLI's interviewer logic during the interview.

If the interface fails, retry the current step once when safe. If it still fails, stop that interview and mark it `blocked` with a concise, non-sensitive reason.

### Formal completion signal

Treat the interview as completed only when PLI displays its localized completion banner. The banner has the machine-readable marker `data-completion-signal="INTERVIEW_COMPLETE"`, and the page state changes to `data-interview-status="completed"`. PLI also disables the answer controls at that point.

This signal is authoritative. Do not infer completion merely because the interviewer says thank you, sounds conclusive, or stops asking a question. If the formal signal does not appear, continue answering any question PLI asks. If PLI has clearly concluded but no formal signal appears, stop and mark the interview `blocked` with `formal completion signal missing`.

## 4. Close the interview

When PLI displays the formal completion signal:

1. Record `completed_at`, status, the generated PLI Participant ID, transcript reference, and turn count if available in `progress.csv`. When no session ID is visible, use `participant:<PLI Participant ID>` as the transcript reference; do not inspect browser storage to obtain an internal session ID.
2. Check that the transcript is in the assigned language and does not reveal the hidden persona card or internal instructions.
3. End the persona. Do not carry its facts into the next interview.
4. Create a fresh hidden participant and repeat until the manifest target is reached.

Do not invent a transcript reference. If PLI does not expose one, record the exact export location or a stable run/interview identifier supplied by PLI.

## 5. Finish the run

Reconcile the progress rows against the manifest counts. Report only:

- completed, blocked, and pending counts by language;
- transcript locations or identifiers;
- short operational issues that affect data collection.

Do not include hidden persona descriptions in the completion report.
