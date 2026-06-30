# Prompt Workbench

Prompt Workbench is a local-first prompt engineering assistant built with
Streamlit. It transforms rough requests into structured prompts using transparent
keyword and rule matching. It does not call an AI model.

## Features

- Detects common prompt intents such as summarizing, explaining, analyzing,
  comparing, writing, classifying, extracting, reviewing, translating, and
  troubleshooting.
- Detects constraints including brevity, detail, grounding, Markdown, JSON,
  tables, bullet points, risks, and action items.
- Detects requested outputs such as summaries, recommendations, assumptions,
  test cases, acceptance criteria, steps, and examples.
- Builds task-aware RTF, AIM, RISEN, TAG, or CLEAR prompts.
- Always preserves the exact original request for traceability.
- Shows detected signals, side-by-side text, a highlighted line diff, and prompt
  statistics.
- Downloads transformed prompts as Markdown.
- Includes six ready-to-use sample prompts.

## Why local-first?

Prompt text can contain internal requirements, source material, code, or logs.
Prompt Workbench processes that text inside the local Python process. There are
no API keys, model downloads, AI services, telemetry calls, or network requests.
The same input and framework always produce the same result.

## Framework comparison

| Framework | Best Used For |
| --- | --- |
| RTF | Simple role-based prompts |
| AIM | Audience-specific communication |
| RISEN | Multi-step analytical tasks |
| TAG | Quick task-oriented prompts |
| CLEAR | Detailed enterprise prompts |

## Why deterministic?

Prompt Workbench intentionally uses rule-based detection and makes no API calls.
This keeps prompt transformation transparent, local-first, and auditable: each
detection can be traced to an explicit phrase in the original prompt.

## How deterministic detection works

Ordered regular-expression rules in `prompt_toolkit_app/core.py` scan the prompt
for explicit intent, constraint, and output signals. Those signals select a
domain-appropriate role and build steps, goals, formatting rules, and grounding
instructions. The selected framework controls where those generated elements
appear.

This is intentionally predictable rather than generative: it only acts on known
rules, displays what it detected, and preserves the original request.

## Sample prompts

- **Meeting summary:** concise decisions, risks, and action items
- **Jira story generation:** assumptions and acceptance criteria
- **Log debugging:** likely causes, troubleshooting steps, and recommendations
- **Document summary:** grounded summary with risks and actions
- **SQL explanation:** step-by-step explanation with an example
- **Test case generation:** detailed cases and expected outcomes in a table

All samples are available from the **Sample prompts** expander in the app.

## Before and after

Before:

```text
Summarize this document, include risks and action items, keep it short,
and don't make up missing details.
```

After using RISEN:

```text
Role:
You are an experienced business analyst.

Instructions:
Analyze the provided material and create a concise, grounded summary of its key information.

Original User Request:
Summarize this document, include risks and action items, keep it short,
and don't make up missing details.

Steps:
1. Read the original request and any provided source material carefully.
2. Summarize the key information.
3. Analyze the evidence, implications, and relevant risks.
4. Identify risks explicitly supported by the provided information.
5. Extract action items if available.
6. State "Not provided" when required details are missing.

End Goal:
Provide a useful response containing summary, risks, and action items.

Narrowing:
- Keep the response concise.
- Do not invent missing facts; state "Not provided" when necessary.
- Include a clearly labeled risks section.
- Include a clearly labeled action items section.
- Use clear headings and a scannable structure.
```

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

## Project structure

```text
app.py
prompt_toolkit_app/
  core.py
  framework_rules.py
  sample_prompts.py
tests/test_core.py
requirements.txt
README.md
```
