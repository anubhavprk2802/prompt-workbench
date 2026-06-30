"""Curated rough prompts for demonstrating deterministic transformations."""

SAMPLE_PROMPTS: dict[str, str] = {
    "Meeting summary": (
        "Summarize these meeting notes in concise bullet points. Include decisions, "
        "risks, and action items. Do not invent missing owners or deadlines."
    ),
    "Jira story generation": (
        "Create a Jira user story for adding passwordless login. Include assumptions, "
        "acceptance criteria, risks, and keep it in Markdown."
    ),
    "Log debugging": (
        "Debug these application logs, explain the likely cause, and give troubleshooting "
        "steps and recommendations. Do not make up details not present in the logs."
    ),
    "Document summary with risks/actions": (
        "Help me understand this document and summarize it. Identify risks and action "
        "items, keep it concise, and if something is unknown do not make it up."
    ),
    "SQL explanation": (
        "Explain this SQL query step by step with a short example. Use concise Markdown."
    ),
    "Test case generation": (
        "Generate detailed test cases for a checkout form, including assumptions, "
        "expected outcomes, and acceptance criteria. Return the test cases in a table."
    ),
}

