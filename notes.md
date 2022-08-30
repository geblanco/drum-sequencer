Note Modes
===
* Default: A note-on triggers the pad, a note-off triggers it off
* Toggle: A note-on toggles the pad state from on/off and viceversa

Led Modes
===
* handled: a note-on should be sent to the controller to let it lit
* partially-handled: note-on is not sent, the controller itself gets lit, a note-off is sent
  to get light the pad off.
* unhandled: the controller knows when it should be lit and not

Track modes
===
* Select-tracks: Only one track at a time is displayed.
* All-tracks: All tracks are displayed at the same time (big controller or few tracks)

The most probable mode is:
* toggle, handled, select-tracks


ToDo
===
- Add view mode selection to wizard
- Add drumpad selection to wizard
- Add new views to wizard
- ~~load_map~~
- ~~output queue, used in leds and notes~~
- ~~input queue, add handler, remove midiin? and call from here?~~
- ~~connect led_queue~~
- ~~clock handling: depending on clock source, instantiate~~
  - ~~internal clock~~
  - ~~external clock~~
  - ~~controller clock (with passthrough: add_callback, used in inputqueue)
    instruct midiinput to not filter clock messages~~
- ~~
  moving from a central output object (be it the note output queue or the led queue)
  to a pub/sub would avoid passing lots of data, a sub-queue could receive led messages
  and prepare them for output. Only the sub-queue would have access to the midi output
  - track propagation: it doesnt need to know its output channel, led stuff...
  - track selection
  - output_queues do not need channels nor processing...
  The caveat could be speed, is it reasonable to use this mechanism for the sequencer?
  ~~
- ~~take back timestamp, is present in all callbacks~~
- ~~move modes to separate files (remove utils?)~~
- ~~wizard: setup velocity controller supports different lights? check velocity changes color~~

- ~~main: load config from controller~~
- ~~check input queues, filters not working~~
- ~~note_i/o_map: add type spec, pads can emmit cc or note, handle this situation~~
- ~~led_i/o: handle led colors by velocity~~
- ~~
  displayed tracks when TrackMode in select_tracks:
  A&H displays one track, launchpad can display more...
  check: \_select\_track and process in sequencer
  ~~
- ~~track selection by blocks, when select mode and display tracks > 1~~
- ~~clock accept time signatures from sequencer~~