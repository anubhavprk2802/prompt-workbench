"""Metadata for the prompt-engineering frameworks supported by the app."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FrameworkRule:
    """Human-readable framework metadata used by the engine and interface."""

    description: str
    best_for: str
    sections: tuple[str, ...]


FRAMEWORK_RULES: dict[str, FrameworkRule] = {
    "RTF": FrameworkRule(
        description=(
            "Best for straightforward prompts where role, task, and output format "
            "are the main focus."
        ),
        best_for="Fast, focused requests with an explicit response shape.",
        sections=("Role", "Task", "Format"),
    ),
    "AIM": FrameworkRule(
        description=(
            "Best for communication prompts that need a clear audience, intent, and method."
        ),
        best_for="Outcome-oriented work where source material drives a clear mission.",
        sections=("Actor", "Input", "Mission"),
    ),
    "RISEN": FrameworkRule(
        description=(
            "Best for analytical or multi-step prompts that need structured reasoning "
            "and constraints."
        ),
        best_for="Complex tasks that benefit from a workflow and strict boundaries.",
        sections=("Role", "Instructions", "Steps", "End Goal", "Narrowing"),
    ),
    "TAG": FrameworkRule(
        description="Best for quick task-oriented prompts with a clear action and goal.",
        best_for="Actionable requests with a direct path from task to result.",
        sections=("Task", "Action", "Goal"),
    ),
    "CLEAR": FrameworkRule(
        description=(
            "Best for detailed enterprise prompts that need context, length, examples, "
            "audience, and requirements."
        ),
        best_for="Detailed briefs where delivery expectations matter.",
        sections=("Context", "Length", "Examples", "Audience", "Requirements"),
    ),
}
