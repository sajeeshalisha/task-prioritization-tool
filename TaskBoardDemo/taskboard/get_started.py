"""Picks the "Get Started" tests: the highest-priority unrun cases, most important device first."""
from dataclasses import dataclass

from .devices import DEVICE_ORDER, device_in
from .models import TestCase, TestRun

LIMIT = 5


@dataclass(frozen=True)
class Suggestion:
    case: TestCase
    test: TestRun
    device: str  # one of DEVICE_ORDER, or "" if unknown
    automatable: bool  # tests that can be automated matter less than ones that can't


def device_of(case, test):
    """The device a case runs on, from the most specific text available.

    The case title beats its test run's title, and both beat the instructions, which are only
    a last resort because they describe every device a test touches.
    """
    for text in (case.title, test.title, case.instructions):
        device = device_in(text)
        if device:
            return device
    return ""


def is_automatable(case):
    """A 🖥️ in the title marks a test that can be automated."""
    return "\U0001F5A5" in case.title


def _rank(device):
    return DEVICE_ORDER.index(device) if device else len(DEVICE_ORDER)


def suggestion_for(case, test):
    return Suggestion(case, test, device_of(case, test), is_automatable(case))


def _priority_rank(case):
    """1 is highest. Cases with no priority go last."""
    return case.priority if case.priority is not None else float("inf")


def get_started(tests, limit=LIMIT, exclude=()):
    """Up to `limit` unrun cases: priority 1 first, then 2, and so on until nothing is left.

    Within a priority, manual tests come before automatable ones, and each of those groups is
    ordered watchOS, iOS, macOS, visionOS, then unknown. Within a device, cases from newer test runs
    come first, then by position in the test run: `tests` is already newest first and sorting is
    stable, so only the three keys below need sorting. Cases whose ids are in `exclude` are skipped.
    """
    candidates = [
        suggestion_for(case, test)
        for test in tests
        for case in test.cases
        if case.status == "No value" and case.id not in exclude
    ]
    candidates.sort(key=lambda s: (_priority_rank(s.case), s.automatable, _rank(s.device)))
    return candidates[:limit]
