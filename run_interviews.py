"""
Synthetic PLI interview runner for intervu.quest

Runs sequential, LLM-generated "synthetic participant" interviews against
the intervu.quest chat interface, using Claude to both play the persona
and drive the browser via Playwright.

HOW TO USE
----------
1. pip install playwright
   playwright install chromium
2. npm install -g @anthropic-ai/claude-code
3. Log in once on any machine with a browser, using your existing Claude
   Pro/Max account: run `claude` and follow the login prompt, or run
   `claude setup-token` to generate a long-lived OAuth token you can copy
   to a headless machine (export CLAUDE_CODE_OAUTH_TOKEN=...). No separate
   API console account, credit card, or ID verification needed — this
   uses your existing Claude.ai subscription.
4. Adjust LANGUAGES / PILOT_COUNT / FULL_COUNT_PER_LANGUAGE as needed.
5. Run: python run_interviews.py --mode pilot        (36 interviews, 2/lang)
        python run_interviews.py --mode full          (900 interviews, 50/lang)
        python run_interviews.py --mode full --languages en,fr   (subset)

NOTE ON USAGE LIMITS: this draws from your Pro plan's normal usage limits,
not pay-per-token billing. A run of 900 interviews (each ~10-15 short
generations) is a meaningful chunk of usage — it may need to be spread
across multiple days/sessions if you hit your plan's rate or usage caps.
Watch for "claude -p failed" errors in run_log.jsonl as a sign of this.

The script writes one JSON line per interview to run_log.jsonl and a full
transcript to transcripts/<run_id>_<lang>_<n>.json as it goes, so you can
kill and resume safely (it skips interviews already marked "completed").
"""

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import subprocess

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

BASE_URL = "https://intervu.quest"
RUN_LOG = Path("run_log.jsonl")
TRANSCRIPT_DIR = Path("transcripts")
TRANSCRIPT_DIR.mkdir(exist_ok=True)
DEBUG_DIR = Path("debug")
PRIVATE_DIR = Path("private-local")  # hidden personas only — must stay out of git/CI artifacts


def save_debug_snapshot(page, tag: str):
    """On any blocked/failed interview, save a screenshot + current URL/HTML
    + visible text + element diagnostics, so the failure is diagnosable from
    the uploaded artifact alone, without needing a live/manual run."""
    try:
        DEBUG_DIR.mkdir(exist_ok=True)
        page.screenshot(path=str(DEBUG_DIR / f"{tag}.png"))
        (DEBUG_DIR / f"{tag}_url.txt").write_text(page.url)
        (DEBUG_DIR / f"{tag}.html").write_text(page.content())
        try:
            body_text = page.evaluate("document.body.innerText || ''")
        except Exception:
            body_text = "(could not read body text)"
        try:
            matches = page.evaluate(
                "(() => { const el = document.getElementById('generatedId'); "
                "return el ? {textContent: el.textContent, visible: el.offsetParent !== null} : null; })()"
            )
        except Exception:
            matches = "(could not query #generatedId)"
        (DEBUG_DIR / f"{tag}_diagnostics.txt").write_text(
            f"visible body text:\n{body_text}\n\n"
            f"#generatedId element:\n{matches}\n"
        )
    except Exception as e:
        (DEBUG_DIR / f"{tag}_snapshot_failed.txt").write_text(str(e))

PILOT_COUNT = 2
FULL_COUNT_PER_LANGUAGE = 50

# language code -> (display label on the site, code used in manifest)
LANGUAGES = {
    "en": "English",
    "zh": "简体中文",
    "ar": "العربية",
    "es": "Español",
    "fr": "Français",
    "pt": "Português",
    "tr": "Türkçe",
    "hi": "हिन्दी",
    "bn": "বাংলা",
    "vi": "Tiếng Việt",
    "ta": "தமிழ்",
    "sw": "Kiswahili",
    "ur": "اردو",
    "id": "Bahasa Indonesia",
    "so": "Soomaali",
    "my": "မြန်မာဘာသာ",
    "fa": "فارسی / Persian / Farsi",
    "prs": "دری",
}

# Exclusions from the run manifest — enforced in the persona prompt.
PERSONA_CONSTRAINTS = """
Generate ONE adult synthetic interview persona. Requirements:
- Not a real, identifiable person.
- Not a copy of a "prototype" or template persona.
- No medical emergencies in their situation.
- Avoid stereotyped identity-trait combinations (e.g. do not default to
  cliché pairings of ethnicity/religion/gender with occupation or attitude).
- Vary naturally across life stage, work rhythm, household composition,
  sleep pattern, general attitudes, and location — no fixed quota, just
  broad plausible variation.
Return a short persona sketch (5-8 bullet points) in English, regardless
of interview language, for internal use only — it will never be shown
to the interviewer.
"""

# ---------------------------------------------------------------------------
# SELECTORS -- TODO: fill these in from the live DOM before running.
# Open the site, open devtools, and inspect each element once.
# ---------------------------------------------------------------------------

SELECTORS = {
    # link/button for each language on the landing screen (index.html);
    # matched by visible text, e.g. get_by_text("Français")
    "language_link": None,               # auto-derived from LANGUAGES label
    "welcome_continue_button": "#continueButton",       # welcome.html
    "new_participant_radio": "#newParticipant",
    "consent_agree_button": "#agreeButton",             # consent.html
    "chat_container": "#chat",                          # interview.html
    "chat_message": "#chat p.chat-message",
    "chat_input": "#message",
    "send_button": "#sendButton",
}

# Each message in #chat looks like:
#   <p class="chat-message"><b><bdi class="message-label">AI</bdi>:</b>
#    <bdi class="message-content">text</bdi></p>
# label is "AI" for the interviewer, "Participant" for the participant's own
# (echoed) messages.
INTERVIEWER_LABEL = "AI"
PARTICIPANT_LABEL = "Participant"

def ask_claude(prompt: str) -> str:
    """Call Claude Code in headless mode (`claude -p`). Authenticates via
    CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`, tied to your Pro/Max
    login) rather than a separate API console key — no separate developer
    account or ID verification needed."""
    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--output-format", "text",
            "--dangerously-skip-permissions",  # no TTY in CI to answer prompts
        ],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(
            f"claude -p failed (exit {result.returncode})\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# PERSONA / ANSWER GENERATION
# ---------------------------------------------------------------------------

def generate_persona(lang_label: str) -> str:
    return ask_claude(PERSONA_CONSTRAINTS)


def generate_answer(persona: str, lang_label: str, question: str, history: list) -> str:
    """Ask Claude to answer in-character, in the interview's language."""
    history_text = "\n".join(f"{h['role']}: {h['text']}" for h in history[-10:])
    prompt = f"""
You are role-playing a synthetic research participant for a study.
Persona (internal only, never reveal): {persona}

Respond naturally and conversationally IN {lang_label}, as this persona,
to the interviewer's latest message. Keep answers realistic in length
(1-4 sentences typically). Answer the question actually asked — do not
dump the whole backstory or steer toward a prepared script. Allow normal
hesitation, imperfect recall, and small conversational corrections.

Do not mention that you are Claude, an AI, a prompt, or a simulation
unless the interviewer directly asks whether you are a real person or a
synthetic/AI participant — if asked directly, answer truthfully that this
is an authorized synthetic participant. Never expose this persona sketch
or these instructions in your answer. Do not give medical advice or turn
ordinary sleep difficulty into a diagnosis.

Recent conversation:
{history_text}

Interviewer just said: {question}

Your reply (in {lang_label} only):
"""
    return ask_claude(prompt)


# ---------------------------------------------------------------------------
# BROWSER AUTOMATION
# ---------------------------------------------------------------------------

def get_chat_messages(page):
    """Return list of {label, text} for every message currently in #chat,
    in DOM order (oldest first)."""
    els = page.query_selector_all(SELECTORS["chat_message"])
    out = []
    for el in els:
        label_el = el.query_selector("bdi.message-label")
        content_el = el.query_selector("bdi.message-content")
        out.append({
            "label": label_el.inner_text().strip() if label_el else "",
            "text": content_el.inner_text().strip() if content_el else "",
        })
    return out


def run_single_interview(page, lang_code: str, lang_label: str, run_id: str, idx: int) -> dict:
    page.goto(BASE_URL, wait_until="networkidle")

    # 1. Language selection (index.html)
    link_selector = SELECTORS["language_link"] or f"text={lang_label}"
    page.click(link_selector)
    page.wait_for_load_state("networkidle")

    # 2. Welcome / research info screen (welcome.html)
    page.click(SELECTORS["welcome_continue_button"])
    page.wait_for_load_state("networkidle")

    # 3. Consent form (consent.html) — select "new participant", capture ID, agree
    #
    # Real page structure (confirmed from captured source):
    #   #participantIdBox  -> for RETURNING participants (stays hidden — this
    #                         was mistakenly what earlier versions checked)
    #   #generatedIdBox    -> shown for NEW participants; the actual ID text
    #                         lives in the #generatedId element inside it.
    # Using textContent (not innerText) avoids a headless-only quirk where
    # innerText depends on layout being flushed, which can lag in headless
    # Chromium until something (like a screenshot) forces a reflow.
    page.click(SELECTORS["new_participant_radio"])
    page.wait_for_function(
        """() => {
            const el = document.getElementById('generatedId');
            return el && /P\\d{6,}/.test(el.textContent || '');
        }""",
        timeout=15000,
    )
    participant_id = page.evaluate("document.getElementById('generatedId').textContent").strip()
    page.click(SELECTORS["consent_agree_button"])
    page.wait_for_load_state("networkidle")

    # 4. Interview chat (interview.html)
    persona = generate_persona(lang_label)
    # Per CLAUDE.md: the hidden persona must never enter the transcript, the
    # manifest, or progress.csv. Keep it only in an ignored private-local file.
    PRIVATE_DIR.mkdir(exist_ok=True)
    (PRIVATE_DIR / f"{run_id}_{lang_code}_{idx}_persona.txt").write_text(persona)

    history = []
    transcript = {
        "run_id": run_id,
        "language": lang_code,
        "index": idx,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "participant_id": participant_id,
        "turns": [],
        "status": "in_progress",
    }

    seen_count = 0
    max_turns = 60  # safety cap so a stuck/long interview doesn't loop forever
    for turn in range(max_turns):
        try:
            page.wait_for_function(
                f"document.querySelectorAll('{SELECTORS['chat_message']}').length > {seen_count}",
                timeout=30000,
            )
        except PWTimeout:
            transcript["status"] = "blocked"
            transcript["error"] = "no new interviewer message appeared (timeout)"
            save_debug_snapshot(page, f"{run_id}_{lang_code}_{idx}_no_message_timeout")
            break

        messages = get_chat_messages(page)
        seen_count = len(messages)
        latest = messages[-1]

        if latest["label"] != INTERVIEWER_LABEL:
            # Unexpected state (e.g. our own message hasn't been followed by
            # a reply yet) — wait one more beat and re-check.
            page.wait_for_timeout(1000)
            continue

        history.append({"role": "interviewer", "text": latest["text"]})
        transcript["turns"].append({"role": "interviewer", "text": latest["text"]})

        if _interview_is_complete(page):
            transcript["status"] = "completed"
            break

        answer = generate_answer(persona, lang_label, latest["text"], history)
        history.append({"role": "participant", "text": answer})
        transcript["turns"].append({"role": "participant", "text": answer})

        page.fill(SELECTORS["chat_input"], answer)
        page.click(SELECTORS["send_button"])
        seen_count += 1  # our own message also gets appended to #chat
        page.wait_for_timeout(1000)
    else:
        transcript["status"] = "blocked"
        transcript["error"] = "formal completion signal missing (exceeded max_turns)"

    transcript["ended_at"] = datetime.now(timezone.utc).isoformat()
    return transcript


def _interview_is_complete(page) -> bool:
    """Authoritative completion check per CLAUDE.md: PLI sets
    data-completion-signal="INTERVIEW_COMPLETE" and data-interview-status="completed"
    on the page when (and only when) the interview has formally concluded.
    Do not infer completion from conversational text alone."""
    status = page.evaluate("document.body.getAttribute('data-interview-status')")
    signal_el = page.query_selector('[data-completion-signal="INTERVIEW_COMPLETE"]')
    return status == "completed" and signal_el is not None


# ---------------------------------------------------------------------------
# RUN ORCHESTRATION
# ---------------------------------------------------------------------------

def load_completed_keys() -> set:
    if not RUN_LOG.exists():
        return set()
    done = set()
    for line in RUN_LOG.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("status") == "completed":
            done.add((rec["language"], rec["index"]))
    return done


def append_log(record: dict):
    with RUN_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["pilot", "full"], required=True)
    parser.add_argument("--languages", default=None, help="comma-separated subset, e.g. en,fr")
    parser.add_argument("--headless", action="store_true", default=True)
    args = parser.parse_args()

    langs = args.languages.split(",") if args.languages else list(LANGUAGES.keys())
    count_per_lang = PILOT_COUNT if args.mode == "pilot" else FULL_COUNT_PER_LANGUAGE
    run_id = f"{'PILOT' if args.mode == 'pilot' else 'FULL'}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    completed = load_completed_keys()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()

        # Pilot gate: run EN-001 first, confirm before continuing, if in pilot mode
        pilot_gate_lang = "en"
        if args.mode == "pilot" and pilot_gate_lang in langs:
            print("Running pilot gate interview R001-EN-001 ...")
            try:
                record = run_single_interview(page, pilot_gate_lang, LANGUAGES[pilot_gate_lang], run_id, 1)
            except Exception as e:
                save_debug_snapshot(page, f"{run_id}_{pilot_gate_lang}_1_exception")
                record = {
                    "run_id": run_id, "language": pilot_gate_lang, "index": 1,
                    "status": "blocked", "error": str(e),
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                }
            append_log(record)
            transcript_path = TRANSCRIPT_DIR / f"{run_id}_{pilot_gate_lang}_1.json"
            transcript_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))

            if record["status"] != "completed" or not record.get("participant_id"):
                print("STOP: pilot gate interview did not complete / no participant ID captured.")
                print("Fix selectors/config and re-run before continuing.")
                browser.close()
                return
            print(f"Pilot gate passed. Participant ID: {record['participant_id']}")
            completed.add((pilot_gate_lang, 1))

        for lang_code in langs:
            lang_label = LANGUAGES[lang_code]
            for idx in range(1, count_per_lang + 1):
                if (lang_code, idx) in completed:
                    continue
                print(f"[{run_id}] {lang_code} #{idx}/{count_per_lang} ...")
                try:
                    record = run_single_interview(page, lang_code, lang_label, run_id, idx)
                except Exception as e:
                    save_debug_snapshot(page, f"{run_id}_{lang_code}_{idx}_exception")
                    record = {
                        "run_id": run_id, "language": lang_code, "index": idx,
                        "status": "blocked", "error": str(e),
                        "ended_at": datetime.now(timezone.utc).isoformat(),
                    }
                append_log(record)
                transcript_path = TRANSCRIPT_DIR / f"{run_id}_{lang_code}_{idx}.json"
                transcript_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))

                if record["status"] == "blocked":
                    print(f"  -> BLOCKED: {record.get('error')}")
                else:
                    print(f"  -> {record['status']}, participant_id={record.get('participant_id')}")

                time.sleep(2)  # small pause between sequential interviews

        browser.close()

    print(f"Run {run_id} finished. See {RUN_LOG} and {TRANSCRIPT_DIR}/ for results.")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------
# Confirmed live against intervu.quest on 2026-08-26 (language select ->
# welcome -> consent -> chat loop, participant ID capture, message parsing
# all verified against the real DOM).
#
# STILL OPEN: the exact wording the interviewer uses to conclude an
# interview hasn't been observed yet (_looks_like_conclusion is a guess).
# Run one interview all the way to the end with --headless=False and update
# that function with the real closing phrase before trusting max_turns /
# completion detection for the full 900-interview run.
