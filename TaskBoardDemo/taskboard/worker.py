"""Background thread that keeps TaskBoard's data up to date."""
import threading

from PySide6.QtCore import QThread, Signal


class SyncWorker(QThread):
    """Polls a data source repeatedly and hands results to the UI thread through signals.

    The source provides `fetch_bugs(progress)` and `fetch_test_runs(progress)`; `progress(fraction,
    text)` reports how far along it is. Bugs arrive first because they're quick; test runs take
    longer. A failure in one doesn't block the other.
    """

    bugs_loaded = Signal(list)
    tests_loaded = Signal(list)
    failed = Signal(str, str)  # which ("bugs" or "tests"), message
    synced = Signal()          # a full pass finished
    progress = Signal(float, str)  # how far along the current pass is (0 to 1) and what it's doing

    def __init__(self, source, interval=2, parent=None):
        super().__init__(parent)
        self._source = source
        self._interval = interval  # seconds to rest between passes
        self._wake = threading.Event()
        self._stop = False

    def refresh_now(self):
        """Skips the rest of the current wait and syncs immediately."""
        self._wake.set()

    def stop(self):
        self._stop = True
        self._wake.set()
        self.wait()

    def run(self):
        while not self._stop:
            # Bugs take the first 15% of the progress bar; the test runs take the rest.
            try:
                self.bugs_loaded.emit(self._source.fetch_bugs(lambda f, t: self.progress.emit(0.15 * f, t)))
            except Exception as error:
                self.failed.emit("bugs", str(error))
            try:
                self.tests_loaded.emit(
                    self._source.fetch_test_runs(lambda f, t: self.progress.emit(0.15 + 0.85 * f, t)))
            except Exception as error:
                self.failed.emit("tests", str(error))
            self.synced.emit()

            self._wake.wait(self._interval)
            self._wake.clear()
