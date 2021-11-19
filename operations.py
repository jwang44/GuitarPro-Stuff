from guitarpro.models import GPException
import os
import glob
import guitarpro
import json
from utils import *


def hello():
    print("hello world")


def get_single_tracks(file, output_dir, unify_volume=True):
    song = guitarpro.parse(file)
    # tempo = song.tempo
    tracks = get_guitar_tracks(song)
    for track in tracks:
        # unify the volume for rendered audio
        if unify_volume:
            track.channel.volume = 100
        single_track_song = song  # this preserves the metadata in orginal song
        single_track_song.tracks = [track]
        file_name = "{}_{}.gp5".format(
            file.split("/")[-1].split(".")[0], track.name.replace("/", " ")
        )
        try:
            guitarpro.write(single_track_song, os.path.join(output_dir, file_name))
        except GPException:
            print(f"GPException, removing the corrupt file {file_name}")
            os.remove(os.path.join(output_dir, file_name))


# TODO: Do I really need to break the single-tracks into phrases?
# Why not just use the single tracks? At least it can work for the poly detector.
# This can save a lot of trouble when synthesizing into audio later.
def get_phrases(
    single_track_file,
    output_dir,
    force_clean=True,
    disable_mixTableChange=True,
    disable_repeats=True,
    bar_count=4,
):
    # get 4-bar single-track phrases
    # remove phrases where the 4 bars are completely empty
    # disable any mixTableChange, including tempo change
    # disable repeats and alternate-endings
    # force clean_electric_guitar instrument channel
    try:
        song = guitarpro.parse(single_track_file)
    except GPException:
        print(f"GPEXCEPTION in parsing {single_track_file.split('/')[-1]}")
        return
    # tempo = song.tempo
    assert len(song.tracks) == 1
    track = song.tracks[0]
    measures = track.measures

    # disable repeats in all measures
    # this includes repeats and alternative endings
    if disable_repeats:
        for measure in measures:
            # isRepeatOpen is boolean, repeatClose takes -1 or 1,
            # repeatAlternative can be whatever number, depending on which repeat group it belongs to
            # the following is the default setting in normal bars
            measure.header.isRepeatOpen = False
            measure.header.repeatClose = -1
            measure.header.repeatAlternative = 0

    # disable mixTableChange in all beats
    # this includes tempo changes, which mess up the calculation of note timings
    # and other mysterious effect/instrument changes
    if disable_mixTableChange:
        for measure in measures:
            for voice in measure.voices:
                for beat in voice.beats:
                    beat.effect.mixTableChange = None

    bar_phrases = [
        measures[i : i + bar_count] for i in range(0, len(measures), bar_count)
    ]
    for i, phrase in enumerate(bar_phrases):
        if not all(len(get_measure_notes(measure)) == 0 for measure in phrase):
            phrase_track = track
            # force the instrument to be clean electric guitar, so that synthesized audio is automatically clean guitar
            if force_clean:
                phrase_track.channel.instrument = 27
            phrase_track.measures = phrase
            phrase_song = song
            phrase_song.tracks = [phrase_track]
            # phrase_song = guitarpro.Song(tracks=[phrase_track], tempo=song.tempo)
            file_name = "{}_{}.gp5".format(
                single_track_file.split("/")[-1].split(".")[0], i
            )

            guitarpro.write(phrase_song, os.path.join(output_dir, file_name))
        # else:
        #     print(f"empty measure found in {single_track_file.split('/')[-1]} - {i}")
        # raise Exception(f"empty measure found in {single_track_file.split('/')[-1]} - {i}")


def poly_vs_mono(song):
    # return the time stamps for mono and poly segments of the song
    bpm = song.tempo
    poly_segments = []
    mono_segments = []
    previous_beat_status = 0
    beats = []
    for measure in song.tracks[0].measures:
        # for voice in measure.voices[0]:
        voice = measure.voices[0]
        beats.extend(voice.beats)
    for beat in beats:
        onset = beat.start
        onset_sec = round(((onset - 960) / 960) / (bpm / 60), 4)
        dur = beat.duration.time
        dur_sec = round((dur / 960) / (bpm / 60), 4)
        offset_sec = onset_sec + dur_sec
        # 2 for polyphonic, 1 for monophonic and silence
        beat_status = 2 if len(beat.notes) > 1 else 1
        if beat_status != previous_beat_status:
            # if current beat status is different from the previous beat, add the timing to the output list
            # the following lines can obviously be better written, I leave it like this just for clarity
            if beat_status == 2:
                poly_segments.append([onset_sec, offset_sec])
            if beat_status == 1:
                mono_segments.append([onset_sec, offset_sec])
        else:
            # if current beat status is the same as the previous one, update the offset of the entry
            if beat_status == 2:
                poly_segments[-1][1] = offset_sec
            if beat_status == 1:
                mono_segments[-1][1] = offset_sec
        previous_beat_status = beat_status
    return poly_segments, mono_segments
