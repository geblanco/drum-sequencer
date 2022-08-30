class TrackState(object):
    def __init__(self, nof_steps, velocity, signatures):
        self.signatures = []

    def setup_signatures(self):
        """ Valid notes:
        name                duration
        whole         note: 1
        half          note: 1/2
        quarter       note: 1/4
        eighth        note: 1/8
        sixteenth     note: 1/16
        thirty-second note: 1/32

