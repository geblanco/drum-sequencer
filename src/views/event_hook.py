from modes import ViewMode, NoteMode


# Both drumpad and clockset must process note_off events, tell the input queue
def get_view_hook(input_queue, led_clock=None):
    prev_note_mode = input_queue.note_mode
    active_views = [ViewMode.drumpad, ViewMode.clock_set]

    def on_active_view(view):
        if view in active_views:
            input_queue.note_mode = NoteMode.default
            if led_clock is not None:
                led_clock.display_on_track = True

    def on_inactive_view(view):
        if view in active_views:
            input_queue.note_mode = prev_note_mode
            if led_clock is not None:
                led_clock.display_on_track = None

    return on_active_view, on_inactive_view
