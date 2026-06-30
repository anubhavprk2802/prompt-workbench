"""Single-page local-first Prompt Workbench."""

from html import escape

import streamlit as st

from prompt_toolkit_app.core import (
    DetectionMatch,
    PromptAnalysis,
    analyze_prompt,
    calculate_stats,
    create_diff,
    render_diff_html,
    rewrite_prompt,
)
from prompt_toolkit_app.framework_rules import FRAMEWORK_RULES
from prompt_toolkit_app.sample_prompts import SAMPLE_PROMPTS


st.set_page_config(page_title="Prompt Workbench", page_icon="🛠️", layout="wide")

st.markdown(
    """
    <style>
        .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}
        h1, h2, h3 {letter-spacing: -0.02em;}
        .subtitle {color: var(--text-color); opacity: .72; font-size: 1.08rem; margin-top: -.6rem;}
        [data-testid="stMetric"], .signal-card {
            border: 1px solid rgba(128, 128, 128, .28);
            border-radius: .75rem;
            padding: .8rem; min-height: 5.7rem;
            background: rgba(128, 128, 128, .055);
        }
        .signal-title {font-size: .78rem; font-weight: 700; opacity: .72; margin-bottom: .45rem;}
        .chip {
            display: inline-block; padding: .2rem .55rem; margin: .12rem .18rem .12rem 0;
            border: 1px solid rgba(99, 102, 241, .5); border-radius: 999px;
            background: rgba(99, 102, 241, .13); font-size: .82rem;
        }
        .framework-note {
            border-left: 3px solid #6366f1; padding: .5rem .75rem; margin: .2rem 0 1rem;
            background: rgba(99, 102, 241, .08); border-radius: 0 .4rem .4rem 0;
        }
        .confidence {
            border: 1px solid rgba(128, 128, 128, .28); border-radius: .6rem;
            padding: .55rem .75rem; margin: .15rem 0 .8rem;
            background: rgba(128, 128, 128, .055); font-size: .9rem;
        }
        .diff-table {width: 100%; border-collapse: separate; border-spacing: 0 4px;}
        .diff-table th {text-align: left; padding: 6px 10px;}
        .diff-table td {
            padding: 7px 10px; font-family: monospace; white-space: pre-wrap;
            overflow-wrap: anywhere; vertical-align: top;
        }
        .line-number {width: 3rem; color: #94a3b8; text-align: right;}
        .same {background: rgba(100, 116, 139, .11);}
        .added {background: rgba(34, 197, 94, .17); border-left: 4px solid #22c55e;}
        .removed {background: rgba(239, 68, 68, .17); border-left: 4px solid #ef4444;}
        .changed {background: rgba(234, 179, 8, .18); border-left: 4px solid #eab308;}
        .empty {opacity: .42;}
        .stButton button, .stDownloadButton button {border-radius: .55rem; font-weight: 600;}
        @media (max-width: 700px) {.block-container {padding: 1rem;}}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_sample(prompt: str) -> None:
    st.session_state.original_prompt = prompt


def signal_card(title: str, values: tuple[str, ...]) -> None:
    chips = "".join(f'<span class="chip">{escape(value)}</span>' for value in values)
    card_content = chips or '<span style="opacity:.6">None detected</span>'
    st.markdown(
        f'<div class="signal-card"><div class="signal-title">{escape(title)}</div>'
        f"{card_content}</div>",
        unsafe_allow_html=True,
    )


def evidence_group(title: str, matches: tuple[DetectionMatch, ...]) -> None:
    st.markdown(f"**{title}**")
    if not matches:
        st.caption("None detected")
        return
    for match in matches:
        st.markdown(
            f"- **{escape(match.label)}** → matched “{escape(match.trigger)}”",
            unsafe_allow_html=True,
        )


st.title("Prompt Workbench")
st.markdown(
    '<p class="subtitle">Transform rough prompts into structured prompt-engineering '
    "frameworks locally.</p>",
    unsafe_allow_html=True,
)

original = st.text_area(
    "Original prompt",
    key="original_prompt",
    height=220,
    placeholder="Describe the task, desired output, and any constraints...",
)

selector_col, action_col = st.columns([3, 1])
with selector_col:
    framework = st.selectbox("Prompt framework", options=list(FRAMEWORK_RULES))
with action_col:
    st.write("")
    transform = st.button("Transform Prompt", type="primary", use_container_width=True)

selected_rule = FRAMEWORK_RULES[framework]
st.markdown(
    f'<div class="framework-note">{escape(selected_rule.description)}</div>',
    unsafe_allow_html=True,
)

with st.expander("Framework guide"):
    for name, rule in FRAMEWORK_RULES.items():
        st.markdown(
            f"**{name} — {', '.join(rule.sections)}**  \n"
            f"{rule.description}"
        )

with st.expander("Sample prompts"):
    sample_columns = st.columns(2)
    for index, (name, prompt) in enumerate(SAMPLE_PROMPTS.items()):
        with sample_columns[index % 2]:
            st.button(
                name,
                key=f"sample_{index}",
                on_click=load_sample,
                args=(prompt,),
                use_container_width=True,
            )

if transform:
    if original.strip():
        analysis = analyze_prompt(original)
        st.session_state.transformed_prompt = rewrite_prompt(original, framework, analysis)
        st.session_state.transformed_original = original
        st.session_state.transformed_framework = framework
        st.session_state.transformed_analysis = analysis
    else:
        st.warning("Enter an original prompt before transforming.")

if "transformed_prompt" in st.session_state:
    rewritten: str = st.session_state.transformed_prompt
    source: str = st.session_state.transformed_original
    used_framework: str = st.session_state.transformed_framework
    analysis: PromptAnalysis = st.session_state.transformed_analysis

    st.divider()
    st.success(f"Prompt transformed locally using the {used_framework} framework.")

    st.subheader("Detection Summary")
    confidence_messages = {
        "High": "High confidence — detections are based on explicit prompt keywords.",
        "Medium": "Medium confidence — limited prompt signals were detected.",
        "Low": "Low confidence — no clear framework signals were detected.",
    }
    st.markdown(
        f'<div class="confidence">{escape(confidence_messages[analysis.confidence])}</div>',
        unsafe_allow_html=True,
    )
    detection_columns = st.columns(3)
    with detection_columns[0]:
        signal_card("DETECTED INTENTS", analysis.intents)
    with detection_columns[1]:
        signal_card("DETECTED CONSTRAINTS", analysis.constraints)
    with detection_columns[2]:
        signal_card("OUTPUT NEEDS", analysis.output_needs)

    with st.expander("Why this was detected"):
        evidence_group("Intents", analysis.intent_matches)
        evidence_group("Constraints", analysis.constraint_matches)
        evidence_group("Output needs", analysis.output_need_matches)

    st.subheader(f"Transformed prompt - {used_framework}")
    st.code(rewritten, language="markdown", wrap_lines=True)
    st.download_button(
        "Download transformed prompt",
        data=rewritten,
        file_name=f"transformed_prompt_{used_framework.lower()}.md",
        mime="text/markdown",
    )

    st.subheader("Side-by-side comparison")
    left, right = st.columns(2)
    with left:
        st.text_area("Original", source, height=320, disabled=True)
    with right:
        st.text_area("Transformed", rewritten, height=320, disabled=True)

    with st.expander("Diff details"):
        st.caption("Green: added | Red: removed | Yellow: changed")
        st.markdown(render_diff_html(create_diff(source, rewritten)), unsafe_allow_html=True)

    st.subheader("Prompt statistics")
    original_stats = calculate_stats(source)
    rewritten_stats = calculate_stats(rewritten)
    metrics = (
        ("Characters", rewritten_stats.characters, original_stats.characters),
        ("Words", rewritten_stats.words, original_stats.words),
        ("Lines", rewritten_stats.lines, original_stats.lines),
        ("Estimated tokens", rewritten_stats.estimated_tokens, original_stats.estimated_tokens),
    )
    for column, (label, value, previous) in zip(st.columns(4), metrics):
        column.metric(label, value, delta=value - previous)
    st.caption("Transformed values are shown; deltas are relative to the original prompt.")
