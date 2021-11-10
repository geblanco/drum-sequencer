from utils import ButtonToggler
from modes import ViewMode, SelectMode


class Router(object):
    def __init__(self, config, display, flush_view_hook):
        super(Router, self).__init__()
        self.config = config

        self.display = display
        self.flush_view_hook = flush_view_hook
        self.mode_toggler = ButtonToggler(
            sel_mode=config.get("view_select_mode", SelectMode.arrows),
            sel_map=self.config.get("view_select_map", []),
            nof_displayed_opts=1,
            max_opts=len(ViewMode),
            update_hook=self.update_view,
        )

        self.view = ViewMode(ViewMode.sequencer)
        self.views = {}

    def add_view(self, view_name, view):
        self.views[view_name] = view

    def update_view(self, view_index):
        if view_index < len(self.views):
            self.view = ViewMode.from_index(view_index)
            self.display.set_view(self.view)
            view = self.get_current_view()
            self.flush_view_hook()
            view.propagate()

    def get_current_view(self):
        view = [
            view for name, view in self.views.items()
            if name == self.view
        ]
        return view[0]

    def process(self, message):
        if message.type in ["note_on", "note_off"]:
            note = message.note
            value = message.velocity
        elif message.type in ["control_change"]:
            note = message.control
            value = message.value

        if self.mode_toggler.should_toggle(note):
            self.mode_toggler.toggle(note)
        else:
            self.get_current_view()(note, value)
