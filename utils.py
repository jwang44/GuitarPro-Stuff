import numpy as np


def get_metadata(song):
    metadata = {
        "title": song.title,
        # "artist": song.artist,
        # "album": song.album,
        # "tab": song.tab,
        # "tempo_name": song.tempoName,
        "tempo": song.tempo,
        # "key": song.key.name,
        # "track_count": len(song.tracks)
    }
    return metadata


def get_guitar_tracks(song):
    """
    24 Acoustic Guitar (nylon)
    25 Acoustic Guitar (steel)
    26 Electric Guitar (jazz)
    27 Electric Guitar (clean)
    28 Electric Guitar (muted)
    29 Overdriven Guitar
    30 Distortion Guitar
    """
    GUITAR_MIDI_PROGRAMS = [24, 25, 26, 27, 28, 29, 30]
    # get all non-percussive tracks (this is still necessary because some drum tracks use a guitar program number)
    m_tracks = [track for track in song.tracks if not track.isPercussionTrack]
    guitar_tracks = [
        track
        for track in m_tracks
        if track.channel.instrument in GUITAR_MIDI_PROGRAMS and len(track.strings) == 6
    ]
    return guitar_tracks


def get_track_info(track):
    track_info = {
        "track_no": track.number,
        # "string_count": len(track.strings), # total no of strings
        # "fret_count": track.fretCount, # total no of frets
        # "is_percussion": track.isPercussionTrack,
        # "is_12_string": track.is12StringedGuitarTrack,
        "name": track.name,
        # "measure_count": len(track.measures),
        "midi_channel_instrument": track.channel.instrument,  # 30 for distortion guitar
        # "midi_channel_effect": track.channel.effectChannel, # ignore for now
    }
    return track_info


def get_string_info(string):
    string_info = {
        "string_number": string.number,
        "string_value": string.value,  # EADGBE=40, 45, 50, 55, 59, 64
    }
    return string_info


def get_measure_info(measure):
    voices = [voice for voice in measure.voices if not voice.isEmpty]
    measure_info = {
        "voice_count": len(voices),
        "is_empty": measure.isEmpty,
        "measure_number": measure.number,
        # "key_sig": measure.keySignature,
        # "time_sig": measure.timeSignature,
        "start": measure.start,
        "end": measure.end,
        "length": measure.length,
    }
    return measure_info


def get_voice_info(voice):
    voice_info = {
        "beat_count": len(voice.beats),
        "is_empty": voice.isEmpty,  # empty voice means the voice has 0 beats
    }
    return voice_info


def get_beat_info(beat):
    beat_info = {
        "note_count": len(beat.notes),
        "duration_time": beat.duration.time,
        "start": beat.start,
        "vibrato": beat.effect.vibrato,  # bool
        "has_vibrato": beat.hasVibrato,  # true if any note in this beat has vibrato effect
        "has_harmonic": beat.hasHarmonic,  # true if any note in this beat has harmonic effect
        "offset": beat.startInMeasure,  # beat.start - beat.voice.measure.start
    }
    return beat_info


def get_measure_notes(measure):
    notes = []
    for voice in measure.voices:
        if not voice.isEmpty:
            for beat in voice.beats:
                notes.extend(beat.notes)
            return notes


def get_note_info(note):
    note_info = {
        "string": note.string,
        "fret": note.value,  # fret number
        # "dur_percent": note.durationPercent,
        "pitch": note.realValue,  # self.value + string.value = MIDI note number
        "type": note.type.name,  # NoteType class, rest=0, normal=1, tie=2, dead=3
        "effects": get_effect_info(note.effect),
    }
    return note_info


def get_effect_info(effect):
    effect_info = {
        "ghost_note": effect.ghostNote,  # bool
        "hammer": effect.hammer,  # bool
        "mute": effect.palmMute,  # bool
        "vibrato": effect.vibrato,  # bool
    }

    # if effect.isHarmonic:
    #   effect_info["harmonic_type"] = effect.harmonic.type.name # natural=1, artificial=2, tapped=3, pinch=4, semi=5
    effect_info["harmonic"] = True if effect.isHarmonic else False

    effect_info["bend_type"] = effect.bend.type.name if effect.isBend else None
    effect_info["bend_value"] = effect.bend.value if effect.isBend else None

    effect_info["slide_types"] = (
        [slide.name for slide in effect.slides] if effect.slides else None
    )

    if effect.isGrace:
        effect_info[
            "grace_dur"
        ] = effect.grace.durationTime  # grace note effect duration
        effect_info["grace_fret"] = effect.grace.fret
        effect_info[
            "grace_transition"
        ] = (
            effect.grace.transition.name
        )  # GraceEffectTransition class, none=0, slide=1, bend=2, hammer=3

    if effect.isTrill:  # TrillEffect, hammerOnPullOff
        effect_info["trill_fret"] = effect.trill.fret
        effect_info["trill_dur"] = effect.trill.duration.time

    return effect_info


def get_note_time(note, bpm):
    start = note.beat.start
    start_sec = round(((start - 960) / 960) / (bpm / 60), 4)
    dur = note.beat.duration.time
    dur_sec = round((dur / 960) / (bpm / 60), 4)
    time = {"start": start_sec, "dur": dur_sec}
    return time


def normalize_audio(y):
    # song-level normalization? frame-level normalization?
    y = y - np.mean(y)
    y_norm = y / max(abs(y))
    return y_norm
