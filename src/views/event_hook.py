from modes import ViewMode, NoteMode


def get_drumpad_view_hook(input_queue, led_clock=None):
    prev_note_mode = input_queue.note_mode

    def on_active_view(view):
        if view == ViewMode.drumpad:
            input_queue.note_mode = NoteMode.default
            if led_clock is not None:
                led_clock.display_on_track = True

    def on_inactive_view(view):
        if view == ViewMode.drumpad:
            input_queue.note_mode = prev_note_mode
            if led_clock is not None:
                led_clock.display_on_track = None

    return on_active_view, on_inactive_view
