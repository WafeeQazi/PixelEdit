class History:
    def __init__(self, limit=50):
        self.limit = limit
        self._current = None
        self._undo_stack = []
        self._redo_stack = []

    @property
    def current(self):
        return self._current

    @property
    def can_undo(self):
        return len(self._undo_stack) > 0

    @property
    def can_redo(self):
        return len(self._redo_stack) > 0

    def reset(self, image):
        self._current = image
        self._undo_stack = []
        self._redo_stack = []

    def push(self, new_image):
        if self._current is not None:
            self._undo_stack.append(self._current)
            if len(self._undo_stack) > self.limit:
                self._undo_stack.pop(0)
        self._redo_stack = []
        self._current = new_image

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self._current)
        self._current = self._undo_stack.pop()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self._current)
        self._current = self._redo_stack.pop()

    def clear(self):
        self._undo_stack = []
        self._redo_stack = []
