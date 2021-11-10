from modes import ViewMode, NoteMode


def get_drumpad_view_hook(input_queue):
    prev_note_mode = input_queue.note_mode

    def on_active_view(view):
        if view == ViewMode.drumpad:
            input_queue.note_mode = NoteMode.default

    def on_inactive_view(view):
        if view == ViewMode.drumpad:
            input_queue.note_mode = prev_note_mode

    return on_active_view, on_inactive_view
