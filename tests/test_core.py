"""Unit tests for Prompt Workbench's deterministic engine."""

from pathlib import Path
import unittest

from prompt_toolkit_app.core import analyze_prompt, calculate_stats, create_diff, rewrite_prompt
from prompt_toolkit_app.framework_rules import FRAMEWORK_RULES


EXAMPLE_PROMPT = (
    "Help me understand this document and summarize it. If there are risks tell me, "
    "and include action items. Don't make it too long and if you don't know something "
    "don't make it up."
)


class DetectionTests(unittest.TestCase):
    def test_detects_intents(self) -> None:
        analysis = analyze_prompt("Compare and explain these logs, then debug the error.")
        self.assertIn("Compare", analysis.intents)
        self.assertIn("Explain", analysis.intents)
        self.assertIn("Debug / troubleshoot", analysis.intents)

    def test_detects_constraints(self) -> None:
        analysis = analyze_prompt("Keep it concise in JSON and do not invent facts.")
        self.assertIn("Concise / short", analysis.constraints)
        self.assertIn("JSON", analysis.constraints)
        self.assertIn("No hallucination", analysis.constraints)

    def test_detects_output_needs(self) -> None:
        analysis = analyze_prompt("Give recommendations, assumptions, test cases, and acceptance criteria.")
        self.assertEqual(
            analysis.output_needs,
            ("Recommendations", "Assumptions", "Test cases", "Acceptance criteria"),
        )

    def test_general_task_when_no_rules_match(self) -> None:
        self.assertTrue(analyze_prompt("Help with my task.").is_general)

    def test_returns_matched_trigger_phrases(self) -> None:
        analysis = analyze_prompt(EXAMPLE_PROMPT)
        intent_matches = {match.label: match.trigger.casefold() for match in analysis.intent_matches}
        constraint_matches = {
            match.label: match.trigger.casefold() for match in analysis.constraint_matches
        }
        output_matches = {
            match.label: match.trigger.casefold() for match in analysis.output_need_matches
        }

        self.assertEqual(intent_matches["Summarize"], "summarize")
        self.assertEqual(constraint_matches["Concise / short"], "don't make it too long")
        self.assertEqual(constraint_matches["No hallucination"], "don't make it up")
        self.assertEqual(output_matches["Risks"], "risks")
        self.assertEqual(output_matches["Action items"], "action items")

    def test_confidence_is_high_for_messy_summary_prompt(self) -> None:
        self.assertEqual(analyze_prompt(EXAMPLE_PROMPT).confidence, "High")

    def test_confidence_is_low_for_empty_or_generic_prompt(self) -> None:
        self.assertEqual(analyze_prompt("").confidence, "Low")
        self.assertEqual(analyze_prompt("Help with my task.").confidence, "Low")


class RewriteTests(unittest.TestCase):
    def test_smart_risen_rewrite(self) -> None:
        result = rewrite_prompt(EXAMPLE_PROMPT, "RISEN")
        self.assertIn("You are an experienced business analyst.", result)
        self.assertIn("create a concise, grounded summary", result)
        self.assertIn("Identify risks explicitly supported", result)
        self.assertIn("Extract action items if available.", result)
        self.assertIn('State "Not provided"', result)
        self.assertIn(f"Original User Request:\n{EXAMPLE_PROMPT}", result)

    def test_smart_rtf_rewrite(self) -> None:
        result = rewrite_prompt(
            "Generate concise test cases and acceptance criteria in a table.", "RTF"
        )
        self.assertIn("experienced quality assurance engineer", result)
        self.assertIn("Include: Test cases, Acceptance criteria.", result)
        self.assertIn("Use a table", result)
        self.assertIn("Original User Request:", result)

    def test_every_framework_preserves_original(self) -> None:
        for name in FRAMEWORK_RULES:
            with self.subTest(framework=name):
                self.assertIn("Original User Request:\nExplain recursion", rewrite_prompt("Explain recursion", name))

    def test_empty_prompt_handling(self) -> None:
        with self.assertRaises(ValueError):
            rewrite_prompt("  ", "TAG")


class MetadataTests(unittest.TestCase):
    def test_framework_descriptions_exist_for_all_frameworks(self) -> None:
        self.assertEqual(set(FRAMEWORK_RULES), {"RTF", "AIM", "RISEN", "TAG", "CLEAR"})
        for rule in FRAMEWORK_RULES.values():
            self.assertTrue(rule.description)
            self.assertTrue(rule.best_for)
            self.assertTrue(rule.sections)


class ExistingUtilitiesTests(unittest.TestCase):
    def test_stats_and_diff_still_work(self) -> None:
        stats = calculate_stats("Hello world\nNext line")
        self.assertEqual((stats.words, stats.lines, stats.estimated_tokens), (4, 2, 6))
        self.assertTrue(create_diff("old", "new"))


class ReadmeTests(unittest.TestCase):
    def test_readme_explains_deterministic_no_api_behavior(self) -> None:
        readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8").casefold()
        self.assertIn("why deterministic?", readme)
        self.assertIn("rule-based detection", readme)
        self.assertIn("no api calls", readme)


if __name__ == "__main__":
    unittest.main()
