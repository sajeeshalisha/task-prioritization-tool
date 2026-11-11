"""Made-up data for the demo: a fictional notes app called "Nimbus Notes".

Nothing here comes from a real system. `DemoSource` stands in for a bug tracker: it hands out the
same kinds of objects the UI shows, and lets you record results so the Get Started flow works.
"""
import threading
import time
from datetime import datetime, timedelta, timezone

from .models import Bug, TestCase, TestRun

RESULTS = ("Pass", "Pass with issues", "Fail", "Blocked", "N/A")

# (title, status, days ago it was created, [(priority, title, result, instructions)])
# A 🖥️ in a case title marks it as automatable. A device is read from the title, and if neither
# the case nor its run names one, from the instructions.
_RUNS = [
    ("Nimbus Notes – Sync Regression (iOS)", "In Progress", 2, [
        (1, "Create a note and confirm it appears on a second device", "No value", ""),
        (1, "Edit the same note on two devices and resolve the conflict", "No value", ""),
        (1, "🖥️ Sync 500 notes without dropping any", "No value", ""),
        (1, "Sign out and back in; every note is still there", "Pass", ""),
        (2, "Pin a note and confirm the pin syncs", "No value", ""),
        (2, "Delete a note and restore it from Recently Deleted", "Pass", ""),
        (3, "Reorder folders and confirm the order syncs", "No value", ""),
    ]),
    ("Nimbus Notes – Sync Regression (macOS)", "In Progress", 2, [
        (1, "Open a note that was shared from an iPhone", "No value", ""),
        (1, "🖥️ Menu bar quick-note shortcut creates a note", "No value", ""),
        (2, "Drag a note into a folder", "Pass", ""),
        (2, "Export a note as a PDF", "No value", ""),
        (3, "Print a note with an attachment", "No value", ""),
    ]),
    ("Nimbus Notes – Sync Regression (watchOS)", "In Progress", 2, [
        (1, "Dictate a note on the watch and confirm it reaches the phone", "No value", ""),
        (1, "Complication shows today's pinned note", "No value", ""),
        (2, "Haptic plays when a shared note changes", "No value", ""),
    ]),
    ("Nimbus Notes – Sharing Smoke Test", "In Progress", 5, [
        (1, "Invite a collaborator to a note", "No value",
         "1. On an iPhone, open a note and tap Share.\n2. Invite a second account.\n3. Confirm the invite arrives."),
        (1, "Remove a collaborator's access", "Pass",
         "1. On an iPad, open a shared note.\n2. Remove the collaborator.\n3. Confirm they lose access."),
        (2, "Collaborator edits appear within five seconds", "No value",
         "1. Edit a shared note on an iPhone.\n2. Watch the second device for the change."),
        (3, "Shared note shows who edited it last", "No value", "Check the byline on a Mac."),
    ]),
    ("Nimbus Notes – Spatial Notes (visionOS)", "In Progress", 9, [
        (2, "Pin a note to a spot in the room", "No value", ""),
        (2, "Scroll a long note with a hand gesture", "Pass", ""),
        (3, "Resize a floating note window", "No value", ""),
    ]),
    ("Nimbus Notes – Offline Mode Regression (iOS)", "Complete", 12, [
        (1, "Edit a note in airplane mode", "Pass", ""),
        (1, "Reconnect and confirm offline edits upload", "Pass", ""),
        (1, "🖥️ Create 50 notes offline, then sync", "Pass with issues", ""),
        (2, "Offline banner appears and clears", "Pass", ""),
        (2, "Attachments queue while offline", "Fail", ""),
    ]),
    ("Nimbus Notes – Offline Mode Regression (macOS)", "Complete", 12, [
        (1, "Edit a note with Wi-Fi turned off", "Pass", ""),
        (1, "Reconnect and confirm offline edits upload", "Pass", ""),
        (2, "Offline banner appears and clears", "Pass", ""),
    ]),
    ("Nimbus Notes – Accessibility Audit", "Pass with issues", 20, [
        (1, "Every control has a VoiceOver label", "Pass with issues", ""),
        (1, "The note list is usable at the largest text size", "Pass", ""),
        (2, "Reduce Motion removes the folder animations", "Pass", ""),
        (2, "Contrast meets guidelines in dark mode", "Blocked", ""),
        (3, "Switch Control can reach the toolbar", "N/A", ""),
        (3, "Captions appear on audio attachments", "Fail", ""),
    ]),
    ("Nimbus Notes – Search Relevance", "Complete", 24, [
        (1, "Search finds text inside a note", "Pass", ""),
        (2, "Search ranks recent notes first", "Pass", ""),
        (2, "Search handles accented characters", "Pass", ""),
    ]),
]

_BUGS = [
    Bug(4182, "Pasting a table into a shared note crashes the editor", "Verify"),
    Bug(4177, "Pinned note icon is missing after restoring from a backup", "Verify"),
    Bug(4163, "Search doesn't match text inside attachments", "Verify"),
]


def _iso(days_ago):
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return when.strftime("%Y-%m-%dT%H:%M:%S+0000")


class DemoSource:
    """An in-memory stand-in for a tracker. Results you record last until the app quits."""

    def __init__(self):
        self._lock = threading.Lock()
        self._first_load = True  # the first load pretends to take a moment, so the loading screen shows
        next_id = 1000
        self._runs = []
        for run_index, (title, status, days_ago, cases) in enumerate(_RUNS, start=1):
            built = []
            for priority, case_title, result, instructions in cases:
                built.append(TestCase(next_id, case_title, result, priority, instructions))
                next_id += 1
            self._runs.append(TestRun(run_index, title, status, _iso(days_ago), tuple(built)))

    def record_result(self, case_id, result):
        with self._lock:
            self._runs = [
                TestRun(r.id, r.title, r.status, r.created_at, tuple(
                    TestCase(c.id, c.title, result, c.priority, c.instructions) if c.id == case_id else c
                    for c in r.cases))
                for r in self._runs
            ]

    def _pause(self, seconds):
        if self._first_load:
            time.sleep(seconds)

    def fetch_bugs(self, progress):
        progress(0.0, "Connecting…")
        self._pause(0.5)
        progress(1.0, "Loading bugs…")
        self._pause(0.3)
        return list(_BUGS)

    def fetch_test_runs(self, progress):
        with self._lock:
            runs = list(self._runs)
        for done in range(len(runs)):
            progress(done / len(runs), f"Loading tests ({done + 1} of {len(runs)})…")
            self._pause(0.18)
        progress(1.0, "Done")
        self._first_load = False
        return sorted(runs, key=lambda r: r.created_at, reverse=True)
