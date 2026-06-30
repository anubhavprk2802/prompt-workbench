"""Deterministic prompt understanding, rewriting, diffing, and statistics."""

import math
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from html import escape
from itertools import zip_longest

from prompt_toolkit_app.framework_rules import FRAMEWORK_RULES


WORD_PATTERN = re.compile(r"\b[\w'-]+\b", re.UNICODE)

# Rules are ordered so detection summaries and generated prompts remain stable.
INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Summarize", (r"\bsummari[sz](?:e|ing|ation)\b", r"\bsummary\b", r"\bcondense\b", r"\brecap\b")),
    ("Explain", (r"\bexplain\b", r"\bunderstand\b", r"\bwalk me through\b", r"\bwhat does\b")),
    ("Analyze", (r"\banaly[sz]e\b", r"\banalysis\b", r"\bevaluate\b", r"\bassess\b", r"\brisks?\b")),
    ("Compare", (r"\bcompare\b", r"\bcontrast\b", r"\bdifferences?\b", r"\bversus\b", r"\bvs\.?\b")),
    (
        "Generate / write / create",
        (
            r"\bgenerat(?:e|ing|ion)\b", r"\bwrit(?:e|ing)\b", r"\bcreat(?:e|ing|ion)\b",
            r"\bdraft\b", r"\bcompose\b", r"\bbuild\b",
        ),
    ),
    ("Classify", (r"\bclassif(?:y|ication)\b", r"\bcategori[sz]e\b", r"\blabel\b")),
    (
        "Extract",
        (r"\bextract\b", r"\bpull out\b", r"\bidentify\b", r"\baction items?\b", r"\bkey points?\b"),
    ),
    ("Review", (r"\breview\b", r"\bcritique\b", r"\baudit\b", r"\bproofread\b")),
    ("Translate", (r"\btranslate\b", r"\btranslation\b", r"\bconvert .* language\b")),
    (
        "Debug / troubleshoot",
        (r"\bdebug\b", r"\btroubleshoot\b", r"\bdiagnos(?:e|is)\b", r"\bbugs?\b", r"\berrors?\b", r"\blogs?\b"),
    ),
)

CONSTRAINT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Concise / short",
        (
            r"\bconcise\b", r"\bbrief\b", r"\bshort\b", r"\bsuccinct\b",
            r"\bnot (?:too )?long\b", r"\bdon't make it too long\b", r"\bunder \d+ words?\b",
        ),
    ),
    ("Detailed", (r"\bdetailed\b", r"\bin[- ]depth\b", r"\bcomprehensive\b", r"\bthorough\b")),
    (
        "No hallucination",
        (
            r"\bno hallucinations?\b",
            r"\bdo not (?:invent|fabricate|make (?:it|things?|facts?|details?|something) up)\b",
            r"\bdon't (?:invent|fabricate|make (?:it|things?|facts?|details?|something) up)\b",
            r"\bif you don't know\b",
            r"\bonly (?:use|based on) (?:the )?(?:provided|given)\b",
        ),
    ),
    ("Markdown", (r"\bmarkdown\b",)),
    ("JSON", (r"\bjson\b",)),
    ("Table", (r"\btables?\b", r"\btabular\b")),
    ("Bullet points", (r"\bbullet points?\b", r"\bbulleted\b", r"\bbullets\b")),
    ("Include risks", (r"\brisks?\b", r"\brisk analysis\b")),
    ("Include action items", (r"\baction items?\b", r"\bnext actions?\b", r"\bfollow[- ]?ups?\b")),
)

OUTPUT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Summary", (r"\bsummari[sz]e\b", r"\bsummary\b", r"\brecap\b")),
    ("Risks", (r"\brisks?\b", r"\bpitfalls?\b", r"\bconcerns?\b")),
    ("Action items", (r"\baction items?\b", r"\bnext actions?\b", r"\bfollow[- ]?ups?\b")),
    ("Recommendations", (r"\brecommendations?\b", r"\bsuggestions?\b", r"\badvice\b")),
    ("Assumptions", (r"\bassumptions?\b",)),
    ("Test cases", (r"\btest cases?\b", r"\btest scenarios?\b", r"\btests for\b")),
    ("Acceptance criteria", (r"\bacceptance criteria\b", r"\bdefinition of done\b")),
    ("Steps", (r"\bsteps?\b", r"\bstep[- ]by[- ]step\b", r"\bprocedure\b")),
    ("Examples", (r"\bexamples?\b", r"\bdemonstrat(?:e|ion)\b")),
)


@dataclass(frozen=True)
class DetectionMatch:
    """A detected label and the exact prompt text that triggered it."""

    label: str
    trigger: str


@dataclass(frozen=True)
class PromptAnalysis:
    intents: tuple[str, ...]
    constraints: tuple[str, ...]
    output_needs: tuple[str, ...]
    intent_matches: tuple[DetectionMatch, ...] = ()
    constraint_matches: tuple[DetectionMatch, ...] = ()
    output_need_matches: tuple[DetectionMatch, ...] = ()

    @property
    def is_general(self) -> bool:
        return not (self.intents or self.constraints or self.output_needs)

    @property
    def detection_count(self) -> int:
        return len(self.intents) + len(self.constraints) + len(self.output_needs)

    @property
    def confidence(self) -> str:
        return detection_confidence(self.detection_count)


@dataclass(frozen=True)
class PromptStats:
    characters: int
    words: int
    lines: int
    estimated_tokens: int


@dataclass(frozen=True)
class DiffRow:
    original_number: int | None
    original_text: str
    original_kind: str
    rewritten_number: int | None
    rewritten_text: str
    rewritten_kind: str


def detection_confidence(detection_count: int) -> str:
    """Return the transparent confidence band for a detection count."""
    if detection_count >= 3:
        return "High"
    if detection_count >= 1:
        return "Medium"
    return "Low"


def _detect(
    text: str, rules: tuple[tuple[str, tuple[str, ...]], ...]
) -> tuple[DetectionMatch, ...]:
    matches: list[DetectionMatch] = []
    for label, patterns in rules:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                matches.append(DetectionMatch(label=label, trigger=match.group(0)))
                break
    return tuple(matches)


def analyze_prompt(prompt: str) -> PromptAnalysis:
    """Detect explicit signals using stable, auditable regular-expression rules."""
    intent_matches = _detect(prompt, INTENT_RULES)
    constraint_matches = _detect(prompt, CONSTRAINT_RULES)
    output_need_matches = _detect(prompt, OUTPUT_RULES)
    return PromptAnalysis(
        intents=tuple(match.label for match in intent_matches),
        constraints=tuple(match.label for match in constraint_matches),
        output_needs=tuple(match.label for match in output_need_matches),
        intent_matches=intent_matches,
        constraint_matches=constraint_matches,
        output_need_matches=output_need_matches,
    )


def _role_for(prompt: str, analysis: PromptAnalysis) -> str:
    text = prompt.casefold()
    if "Test cases" in analysis.output_needs or "acceptance criteria" in text:
        return "You are an experienced quality assurance engineer."
    if "sql" in text or "database" in text:
        return "You are an experienced database engineer."
    if "Debug / troubleshoot" in analysis.intents:
        return "You are an experienced software troubleshooting engineer."
    if "Translate" in analysis.intents:
        return "You are a professional translator who preserves meaning and tone."
    if any(item in text for item in ("document", "meeting", "business", "jira")):
        return "You are an experienced business analyst."
    if "Classify" in analysis.intents or "Extract" in analysis.intents:
        return "You are an experienced information analyst."
    if "Review" in analysis.intents:
        return "You are a rigorous quality reviewer."
    if "Analyze" in analysis.intents or "Compare" in analysis.intents:
        return "You are an experienced analytical specialist."
    if "Generate / write / create" in analysis.intents:
        return "You are a skilled content and planning specialist."
    return "You are a practical subject-matter expert."


def _instruction(analysis: PromptAnalysis) -> str:
    grounded = "No hallucination" in analysis.constraints
    concise = "Concise / short" in analysis.constraints
    prefix = "Create a concise, grounded" if concise and grounded else (
        "Create a concise" if concise else "Create a grounded" if grounded else "Create a clear"
    )

    if "Summarize" in analysis.intents:
        return f"Analyze the provided material and {prefix.lower()} summary of its key information."

    actions = {
        "Explain": "explain the subject in clear, accessible terms",
        "Analyze": "analyze the supplied information and its implications",
        "Compare": "compare the relevant items using consistent criteria",
        "Generate / write / create": "create the requested deliverable",
        "Classify": "classify the supplied items using explicit categories",
        "Extract": "extract the requested information from the supplied material",
        "Review": "review the supplied material and identify meaningful improvements",
        "Translate": "translate the supplied content while preserving its meaning and tone",
        "Debug / troubleshoot": "diagnose the problem and propose verifiable fixes",
    }
    detected_actions = [actions[item] for item in analysis.intents if item in actions]
    if detected_actions:
        return detected_actions[0].capitalize() + "."
    return "Complete the original request accurately and produce a useful result."


def _steps(analysis: PromptAnalysis) -> list[str]:
    steps = ["Read the original request and any provided source material carefully."]
    intent_steps = {
        "Summarize": "Summarize the key information.",
        "Explain": "Explain the important concepts and context.",
        "Analyze": "Analyze the evidence, implications, and relevant risks.",
        "Compare": "Compare each item using the same meaningful criteria.",
        "Generate / write / create": "Create the requested deliverable.",
        "Classify": "Apply clear categories consistently.",
        "Extract": "Extract only the requested information.",
        "Review": "Review for correctness, gaps, and opportunities to improve.",
        "Translate": "Translate accurately while preserving intent and tone.",
        "Debug / troubleshoot": "Trace likely causes and propose testable fixes.",
    }
    for intent in analysis.intents:
        step = intent_steps.get(intent)
        if step and step not in steps:
            steps.append(step)

    output_steps = {
        "Risks": "Identify risks explicitly supported by the provided information.",
        "Action items": "Extract action items if available.",
        "Recommendations": "Provide practical recommendations supported by the analysis.",
        "Assumptions": "List any assumptions separately.",
        "Test cases": "Write test cases with expected outcomes.",
        "Acceptance criteria": "Define clear, testable acceptance criteria.",
        "Steps": "Present the procedure in an ordered sequence.",
        "Examples": "Include relevant examples that clarify the result.",
    }
    for output in analysis.output_needs:
        step = output_steps.get(output)
        if step and step not in steps:
            steps.append(step)

    if "No hallucination" in analysis.constraints:
        steps.append('State "Not provided" when required details are missing.')
    return steps


def _requirements(analysis: PromptAnalysis) -> list[str]:
    requirements: list[str] = []
    mapping = {
        "Concise / short": "Keep the response concise.",
        "Detailed": "Provide a detailed, thorough response.",
        "No hallucination": 'Do not invent missing facts; state "Not provided" when necessary.',
        "Markdown": "Use valid Markdown.",
        "JSON": "Return valid JSON with no surrounding commentary.",
        "Table": "Use a table for information that benefits from comparison.",
        "Bullet points": "Use bullet points for scannability.",
        "Include risks": "Include a clearly labeled risks section.",
        "Include action items": "Include a clearly labeled action items section.",
    }
    for constraint in analysis.constraints:
        requirements.append(mapping[constraint])
    if not any(item in analysis.constraints for item in ("JSON", "Table", "Bullet points")):
        requirements.append("Use clear headings and a scannable structure.")
    return requirements


def _output_labels(analysis: PromptAnalysis) -> list[str]:
    labels = list(analysis.output_needs)
    if "Summary" not in labels and "Summarize" in analysis.intents:
        labels.insert(0, "Summary")
    return labels


def _goal(analysis: PromptAnalysis) -> str:
    outputs = _output_labels(analysis)
    if not outputs:
        return "Provide an accurate, useful result that directly satisfies the original request."
    if len(outputs) == 1:
        result = outputs[0].lower()
    else:
        result = ", ".join(item.lower() for item in outputs[:-1]) + f", and {outputs[-1].lower()}"
    return f"Provide a useful response containing {result}."


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _bulleted(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def rewrite_prompt(
    prompt: str, framework: str, analysis: PromptAnalysis | None = None
) -> str:
    """Build a framework-specific prompt from deterministic detections."""
    cleaned = prompt.strip()
    if not cleaned:
        raise ValueError("Prompt cannot be empty.")
    if framework not in FRAMEWORK_RULES:
        raise ValueError(f"Unknown framework: {framework}")

    detected = analysis or analyze_prompt(cleaned)
    role = _role_for(cleaned, detected)
    instruction = _instruction(detected)
    steps = _steps(detected)
    requirements = _requirements(detected)
    goal = _goal(detected)
    outputs = _output_labels(detected)
    original = f"Original User Request:\n{cleaned}"

    if framework == "RTF":
        task = f"{instruction}\n\n{original}"
        format_items = ([f"Include: {', '.join(outputs)}."] if outputs else []) + requirements
        sections = (("Role", role), ("Task", task), ("Format", _bulleted(format_items)))
    elif framework == "AIM":
        interpreted = f"Interpreted objective: {instruction}\n\n{original}"
        mission = f"{goal}\n\nExecution requirements:\n{_bulleted(requirements)}"
        sections = (("Actor", role), ("Input", interpreted), ("Mission", mission))
    elif framework == "RISEN":
        sections = (
            ("Role", role),
            ("Instructions", f"{instruction}\n\n{original}"),
            ("Steps", _numbered(steps)),
            ("End Goal", goal),
            ("Narrowing", _bulleted(requirements)),
        )
    elif framework == "TAG":
        sections = (
            ("Task", f"{instruction}\n\n{original}"),
            ("Action", _numbered(steps)),
            ("Goal", f"{goal}\n\nConstraints:\n{_bulleted(requirements)}"),
        )
    else:  # CLEAR
        length = (
            "Keep the response concise and focused."
            if "Concise / short" in detected.constraints
            else "Provide enough detail to complete the task without unnecessary repetition."
        )
        examples = (
            "Include relevant examples."
            if "Examples" in detected.output_needs
            else "Use examples only when they materially improve clarity."
        )
        sections = (
            ("Context", f"{instruction}\n\n{original}"),
            ("Length", length),
            ("Examples", examples),
            ("Audience", "Write for the audience implied by the original request."),
            ("Requirements", _bulleted(requirements + ([f"Include: {', '.join(outputs)}."] if outputs else []))),
        )

    return "\n\n".join(f"{heading}:\n{content}" for heading, content in sections)


def calculate_stats(text: str) -> PromptStats:
    """Calculate lightweight prompt statistics."""
    return PromptStats(
        characters=len(text),
        words=len(WORD_PATTERN.findall(text)),
        lines=len(text.splitlines()) if text else 0,
        estimated_tokens=math.ceil(len(text) / 4),
    )


def create_diff(original: str, rewritten: str) -> tuple[DiffRow, ...]:
    """Build side-by-side line rows classified for highlighting."""
    original_lines = original.splitlines() if original else []
    rewritten_lines = rewritten.splitlines() if rewritten else []
    rows: list[DiffRow] = []

    for tag, i1, i2, j1, j2 in SequenceMatcher(
        None, original_lines, rewritten_lines
    ).get_opcodes():
        if tag == "equal":
            for offset, (old, new) in enumerate(
                zip(original_lines[i1:i2], rewritten_lines[j1:j2])
            ):
                rows.append(DiffRow(i1 + offset + 1, old, "same", j1 + offset + 1, new, "same"))
        elif tag == "delete":
            for offset, old in enumerate(original_lines[i1:i2]):
                rows.append(DiffRow(i1 + offset + 1, old, "removed", None, "", "empty"))
        elif tag == "insert":
            for offset, new in enumerate(rewritten_lines[j1:j2]):
                rows.append(DiffRow(None, "", "empty", j1 + offset + 1, new, "added"))
        else:
            for offset, (old, new) in enumerate(
                zip_longest(original_lines[i1:i2], rewritten_lines[j1:j2])
            ):
                if old is not None and new is not None:
                    rows.append(
                        DiffRow(
                            i1 + offset + 1, old, "changed",
                            j1 + offset + 1, new, "changed",
                        )
                    )
                elif old is not None:
                    rows.append(DiffRow(i1 + offset + 1, old, "removed", None, "", "empty"))
                else:
                    rows.append(DiffRow(None, "", "empty", j1 + offset + 1, new or "", "added"))
    return tuple(rows)


def render_diff_html(rows: tuple[DiffRow, ...]) -> str:
    """Render escaped diff rows as a styled HTML table."""

    def cells(number: int | None, text: str, kind: str) -> str:
        shown_number = "" if number is None else str(number)
        shown_text = escape(text) if number is not None else "-"
        return (
            f'<td class="line-number {kind}">{shown_number}</td>'
            f'<td class="{kind}">{shown_text}</td>'
        )

    body = "".join(
        f"<tr>{cells(row.original_number, row.original_text, row.original_kind)}"
        f"{cells(row.rewritten_number, row.rewritten_text, row.rewritten_kind)}</tr>"
        for row in rows
    )
    return (
        '<table class="diff-table"><thead><tr><th colspan="2">Original</th>'
        f'<th colspan="2">Transformed</th></tr></thead><tbody>{body}</tbody></table>'
    )
