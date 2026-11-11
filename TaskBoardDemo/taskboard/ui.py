"""TaskBoard's window: a greeting, three tabs, and live Bugs and Tests lists."""
import os
import pwd
from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCursor, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QProgressBar, QPushButton, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)

from .demo import RESULTS, DemoSource
from .get_started import get_started, suggestion_for
from .worker import SyncWorker

URL_ROLE = Qt.UserRole
DEVICE_COLOR = "#0a84ff"
# The app icon's turquoise (tools/make_icon.py), top to bottom.
TEAL_TOP, TEAL_BOTTOM = "#34d6c0", "#0e8f88"
# Segmented tab buttons; the selected one is filled with the app's turquoise instead of system blue.
TAB_STYLE = f"""
QPushButton {{
    border: 1px solid rgba(128, 128, 128, 110); padding: 4px 18px; background: transparent;
    border-radius: 0;
}}
QPushButton[edge="first"] {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
QPushButton[edge="last"] {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QPushButton:checked {{
    color: white; font-weight: 600; border-color: {TEAL_BOTTOM};
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {TEAL_TOP}, stop: 1 {TEAL_BOTTOM});
}}
"""
PROGRESS_STYLE = (
    "QProgressBar { border: none; border-radius: 9px; background: rgba(128, 128, 128, 50);"
    " text-align: center; min-height: 18px; max-height: 18px; }"
    "QProgressBar::chunk { border-radius: 9px; background: qlineargradient("
    f"x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 {TEAL_TOP}, stop: 1 {TEAL_BOTTOM}); }}"
)

# Badge colors for test case statuses; anything else is neutral grey.
STATUS_COLORS = {
    "Pass": "#2e9e44",
    "Pass with issues": "#b58900",
    "Fail": "#d93025",
    "Failed": "#d93025",
    "Blocked": "#e8710a",
}
NEUTRAL = "#6e6e73"


def first_name():
    full = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
    return full.split()[0] if full else ""


def greeting(now):
    phrase, emoji = (
        ("Good Morning", "☀️") if 5 <= now.hour < 12
        else ("Good Afternoon", "🌤️") if 12 <= now.hour < 17
        else ("Good Evening", "🌙")
    )
    name = first_name()
    return f"{phrase}, {name} {emoji}" if name else f"{phrase} {emoji}"


def badge(text, color=None):
    """A small rounded label tinted by `color` (defaults by status), right-aligned in its cell."""
    color = color or STATUS_COLORS.get(text, NEUTRAL)
    red, green, blue = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    label = QLabel(text)
    label.setStyleSheet(
        f"color: {color}; background: rgba({red}, {green}, {blue}, 38);"
        " border-radius: 9px; padding: 2px 8px; font-size: 11px;"
    )
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 4, 0)
    layout.addStretch()
    layout.addWidget(label)
    return holder


def secondary(text):
    label = QLabel(text)
    label.setStyleSheet("color: gray; font-size: 11px;")
    return label


def count_label(test):
    n = len(test.cases)
    return f"{n} {'test' if n == 1 else 'tests'}"


class MessagePage(QWidget):
    """Centered title and detail text, with an optional Retry button."""

    def __init__(self, title, detail="", on_retry=None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addStretch()
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        font = heading.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)
        if detail:
            text = QLabel(detail)
            text.setAlignment(Qt.AlignCenter)
            text.setWordWrap(True)
            text.setStyleSheet("color: gray;")
            layout.addWidget(text)
        if on_retry:
            self._button = QPushButton("Retry")
            self._button.clicked.connect(lambda: self._retry(on_retry))
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(self._button)
            row.addStretch()
            layout.addLayout(row)

            # A failed retry replaces this page with a fresh one, so the time shows that one happened.
            self._note = secondary(f"Last tried {datetime.now():%H:%M:%S}")
            self._note.setAlignment(Qt.AlignCenter)
            layout.addWidget(self._note)
        layout.addStretch()

    def _retry(self, on_retry):
        self._button.setEnabled(False)
        self._note.setText("Retrying…")
        on_retry()


class LoadingPage(QWidget):
    """"Loading…" with a progress bar that fills as the first sync advances."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addStretch()
        heading = QLabel("Loading…")
        heading.setAlignment(Qt.AlignCenter)
        font = heading.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setTextVisible(False)
        self._bar.setFixedWidth(320)
        self._bar.setStyleSheet(PROGRESS_STYLE)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._bar)
        row.addStretch()
        layout.addLayout(row)

        self._text = secondary("Starting…")
        self._text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._text)
        layout.addStretch()

    def set_progress(self, fraction, text):
        self._bar.setValue(round(max(0.0, min(1.0, fraction)) * 1000))
        self._text.setText(text)


class SwitchingView(QStackedWidget):
    """A list view that can be swapped out for a message page (loading, empty, error)."""

    def show_loading(self):
        """The first-load screen. Its progress bar follows SyncWorker.progress."""
        self.loading = LoadingPage()
        self.addWidget(self.loading)
        self.setCurrentWidget(self.loading)

    def show_message(self, title, detail="", on_retry=None):
        self._clear_message()
        self._message = MessagePage(title, detail, on_retry)
        self.addWidget(self._message)
        self.setCurrentWidget(self._message)

    def _clear_message(self):
        message = getattr(self, "_message", None)
        if message is not None:
            self.removeWidget(message)
            message.deleteLater()
            self._message = None

    def show_content(self, widget):
        self._clear_message()
        self.setCurrentWidget(widget)


class BugsView(SwitchingView):
    """Bugs assigned to the user that are waiting on verification."""

    def __init__(self, on_retry, on_open):
        super().__init__()
        self._on_retry = on_retry
        self._on_open = on_open
        self._bugs = None
        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.NoSelection)
        self._list.itemClicked.connect(lambda item: self._on_open(item.data(URL_ROLE)))
        self.addWidget(self._list)
        self.show_loading()

    def set_bugs(self, bugs):
        if bugs == self._bugs:
            return
        self._bugs = bugs
        if not bugs:
            self.show_message("Nothing to Verify")
            return
        self._list.clear()
        for bug in bugs:
            row = QWidget()
            layout = QHBoxLayout(row)
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(QLabel(bug.title))
            text.addWidget(secondary(f"BUG-{bug.id}"))
            layout.addLayout(text, 1)
            layout.addWidget(badge(bug.state, NEUTRAL))
            item = QListWidgetItem()
            item.setData(URL_ROLE, f"bug:{bug.id}")
            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
        self.show_content(self._list)

    def set_error(self, message):
        self._bugs = None
        self.show_message("Couldn't Load Bugs", message, self._on_retry)


class TestsView(SwitchingView):
    """Active and Completed test runs, each expanding to the cases assigned to the user."""

    def __init__(self, on_retry, on_open):
        super().__init__()
        self._on_retry = on_retry
        self._on_open = on_open
        self._tests = None
        self._expanded = set()  # test run ids the user has opened; survives data refreshes
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(2)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.setSelectionMode(QAbstractItemView.NoSelection)
        self._tree.setIndentation(18)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(0, self._tree.header().ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, self._tree.header().ResizeMode.ResizeToContents)
        self._tree.itemClicked.connect(self._on_click)
        self._tree.itemExpanded.connect(self._on_expand)
        self._tree.itemCollapsed.connect(self._on_collapse)
        self.addWidget(self._tree)
        self.show_loading()

    def _on_click(self, item, _column):
        url = item.data(0, URL_ROLE)
        if url:
            self._on_open(url)

    def _on_expand(self, item):
        test_id = item.data(0, Qt.UserRole + 1)
        if test_id is not None:
            self._expanded.add(test_id)

    def _on_collapse(self, item):
        test_id = item.data(0, Qt.UserRole + 1)
        if test_id is not None:
            self._expanded.discard(test_id)

    def set_tests(self, tests):
        if tests == self._tests:
            return
        self._tests = tests
        if not tests:
            self.show_message("No Assigned Tests")
            return

        scroll = self._tree.verticalScrollBar().value()
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        for title, section in (
            ("Active", [t for t in tests if not t.is_completed]),
            ("Completed", [t for t in tests if t.is_completed]),
        ):
            if section:
                self._add_section(title, section)
        self._tree.setUpdatesEnabled(True)
        self._tree.verticalScrollBar().setValue(scroll)
        self.show_content(self._tree)

    def _add_section(self, title, tests):
        header = QTreeWidgetItem([title])
        font = QFont(self._tree.font())
        font.setBold(True)
        header.setFont(0, font)
        header.setFlags(Qt.ItemIsEnabled)  # a label, not something to click
        self._tree.addTopLevelItem(header)
        header.setFirstColumnSpanned(True)

        for test in tests:
            count = count_label(test) if test.is_completed else f"{test.remaining} remaining · {count_label(test)}"
            row = QTreeWidgetItem([test.title, count])
            row.setData(0, URL_ROLE, f"run:{test.id}")
            row.setData(0, Qt.UserRole + 1, test.id)
            row.setForeground(1, self._tree.palette().placeholderText())
            header.addChild(row)
            for case in test.cases:
                child = QTreeWidgetItem([case.title])
                child.setData(0, URL_ROLE, f"case:{case.id}")
                row.addChild(child)
                self._tree.setItemWidget(child, 1, badge(case.status))
            row.setExpanded(test.id in self._expanded)
        header.setExpanded(True)

    def set_error(self, message):
        self._tests = None
        self.show_message("Couldn't Load Tests", message, self._on_retry)


class HomeView(SwitchingView):
    """The landing page: a batch of five tests to run, then overall progress.

    The batch stays put while you work through it: a case you finish keeps its row and gains a
    status badge. Once every case in it has a result, Continue swaps in the next five.
    """

    def __init__(self, on_retry, on_open):
        super().__init__()
        self._on_retry = on_retry
        self._on_open = on_open
        self._tests = []
        self._batch = None      # Suggestions currently shown, in order; None until the first data arrives
        self._rendered = None   # what the list currently shows, so unchanged data doesn't redraw it

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.NoSelection)
        self._list.itemClicked.connect(lambda item: self._on_open(item.data(URL_ROLE)))

        self._empty = MessagePage("All Caught Up", "Every test assigned to you has a result.")

        self._continue = QPushButton("Continue")
        self._continue.setDefault(True)
        self._continue.setMinimumWidth(140)
        self._continue.clicked.connect(self._next_batch)
        continue_row = QHBoxLayout()
        continue_row.addStretch()
        continue_row.addWidget(self._continue)
        continue_row.addStretch()
        self._continue_holder = QWidget()
        self._continue_holder.setLayout(continue_row)
        continue_row.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Get Started")
        heading.setStyleSheet("font-size: 20px; font-weight: 700;")
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)  # the text sits below the bar, where it's easier to read
        self._progress.setStyleSheet(PROGRESS_STYLE)
        self._progress_text = secondary("")
        self._progress_text.setAlignment(Qt.AlignCenter)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(heading)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._empty, 1)
        layout.addWidget(self._continue_holder)
        layout.addWidget(self._progress)
        layout.addWidget(self._progress_text)
        self._page = page
        self.addWidget(page)
        self.show_loading()

    def set_tests(self, tests):
        self._tests = tests
        # Progress covers every case on the Tests tab: cases that have a result, out of all of them.
        total = sum(len(t.cases) for t in tests)
        done = total - sum(t.remaining for t in tests)
        self._progress.setRange(0, max(total, 1))
        self._progress.setValue(done)
        self._progress_text.setText(
            f"{done * 100 // total}% complete · {done} of {total} tests run" if total else "No tests assigned"
        )

        if self._batch is None:
            self._batch = get_started(tests)
        else:
            self._batch = self._refreshed(self._batch, tests)
        self._render()
        self.show_content(self._page)

    @staticmethod
    def _refreshed(batch, tests):
        """The same cases with their latest status. One that's no longer in the data keeps its last state."""
        latest = {c.id: (c, t) for t in tests for c in t.cases}
        return [suggestion_for(*latest[s.case.id]) if s.case.id in latest else s for s in batch]

    def _next_batch(self):
        shown = {s.case.id for s in self._batch}
        self._batch = get_started(self._tests, exclude=shown)
        self._render()

    def _render(self):
        batch = self._batch
        state = tuple((s.case.id, s.case.status) for s in batch)
        all_done = bool(batch) and all(s.case.status != "No value" for s in batch)
        self._list.setVisible(bool(batch))
        self._empty.setVisible(not batch)
        self._continue_holder.setVisible(all_done)
        if state != self._rendered:
            self._rendered = state
            self._fill_list(batch)

    def _fill_list(self, batch):
        self._list.clear()
        for suggestion in batch:
            row = QWidget()
            layout = QHBoxLayout(row)
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(QLabel(suggestion.case.title))
            text.addWidget(secondary(suggestion.test.title))
            layout.addLayout(text, 1)
            if suggestion.case.priority is not None:
                layout.addWidget(badge(f"P{suggestion.case.priority}", NEUTRAL))
            if suggestion.automatable:
                layout.addWidget(badge("Automatable", NEUTRAL))
            if suggestion.device:
                layout.addWidget(badge(suggestion.device, DEVICE_COLOR))
            # A fixed-width slot, so the device badges line up whatever the status says.
            result = badge(suggestion.case.status)
            result.setFixedWidth(130)
            layout.addWidget(result)
            item = QListWidgetItem()
            item.setData(URL_ROLE, f"case:{suggestion.case.id}")
            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)

    def set_error(self, message):
        self._batch = None
        self._rendered = None
        self.show_message("Couldn't Load Tests", message, self._on_retry)


class MainWindow(QMainWindow):
    TABS = ("Home", "Tests", "Bugs")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TaskBoard")
        self.resize(900, 640)

        self.source = DemoSource()
        self.worker = SyncWorker(self.source, interval=2)
        self.home = HomeView(self.worker.refresh_now, self.open_item)
        self.tests = TestsView(self.worker.refresh_now, self.open_item)
        self.bugs = BugsView(self.worker.refresh_now, self.open_item)

        self.stack = QStackedWidget()
        for page in (self.home, self.tests, self.bugs):
            self.stack.addWidget(page)

        self.greeting = QLabel()
        self.greeting.setStyleSheet("font-weight: 600;")
        self._update_greeting()
        timer = QTimer(self)
        timer.timeout.connect(self._update_greeting)
        timer.start(60_000)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)
        self.tab_group = QButtonGroup(self)
        for index, name in enumerate(self.TABS):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setChecked(index == 0)
            button.setProperty("edge", "first" if index == 0 else "last" if index == len(self.TABS) - 1 else "middle")
            button.setStyleSheet(TAB_STYLE)
            self.tab_group.addButton(button, index)
            tab_row.addWidget(button)
        self.tab_group.idClicked.connect(self.stack.setCurrentIndex)

        new_bug = QPushButton("＋ New Bug")
        new_bug.clicked.connect(lambda: self.open_item("new-bug:"))
        refresh = QPushButton("↻")
        refresh.setToolTip("Reload data now")
        refresh.setFixedWidth(34)
        refresh.clicked.connect(self._refresh)

        header = QHBoxLayout()
        header.addWidget(self.greeting, 1)
        header.addLayout(tab_row)
        # The greeting and the buttons share the free space equally so the tabs stay centered.
        right = QHBoxLayout()
        right.addStretch()
        right.addWidget(new_bug)
        right.addWidget(refresh)
        header.addLayout(right, 1)

        self.status = secondary("Syncing…")

        root = QVBoxLayout()
        root.addLayout(header)
        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(128, 128, 128, 80);")
        root.addWidget(divider)
        root.addWidget(self.stack, 1)
        root.addWidget(self.status)
        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

        self.worker.bugs_loaded.connect(self.bugs.set_bugs)
        self.worker.tests_loaded.connect(self.tests.set_tests)
        self.worker.tests_loaded.connect(self.home.set_tests)
        self.worker.failed.connect(self._on_failed)
        self.worker.synced.connect(self._on_synced)
        for view in (self.home, self.tests, self.bugs):
            self.worker.progress.connect(view.loading.set_progress)
        QGuiApplication.instance().applicationStateChanged.connect(self._on_app_state)
        self.worker.start()

    def open_item(self, ref):
        """What clicking a bug, test run or test case does.

        In a real tracker this would open the item. In the demo, clicking a test case lets you
        record a result for it, which is what drives the Get Started flow.
        """
        kind, _, item_id = ref.partition(":")
        if kind == "case":
            menu = QMenu(self)
            for result in RESULTS:
                menu.addAction(result, lambda r=result: self._record_result(int(item_id), r))
            menu.exec(QCursor.pos())
        elif kind == "new-bug":
            self.status.setText("In a real tracker this would open a new bug form.")
        else:
            self.status.setText(f"In a real tracker this would open {kind} {item_id}.")

    def _record_result(self, case_id, result):
        self.source.record_result(case_id, result)
        self.status.setText("Syncing…")
        self.worker.refresh_now()

    def _on_app_state(self, state):
        if state == Qt.ApplicationActive:
            self.worker.refresh_now()

    def _update_greeting(self):
        self.greeting.setText(greeting(datetime.now()))

    def _refresh(self):
        self.status.setText("Syncing…")
        self.worker.refresh_now()

    def _on_failed(self, source, message):
        if source == "bugs":
            self.bugs.set_error(message)
        else:
            self.tests.set_error(message)
            self.home.set_error(message)

    def _on_synced(self):
        self.status.setText(f"Updated {datetime.now():%H:%M:%S}")

    def closeEvent(self, event):
        self.worker.stop()
        super().closeEvent(event)
