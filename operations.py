from guitarpro.models import GPException
import os
import glob
import guitarpro
import json
from utils import *


def hello():
    print("hello world")


def get_single_tracks(file, output_dir):
    song = guitarpro.parse(file)
    # tempo = song.tempo
    tracks = get_guitar_tracks(song)
    for track in tracks:
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


def get_phrases(single_track_file, output_dir, force_clean=True):
    # get 4-bar single-track phrases
    # eliminate phrases where the 4 bars are completely empty
    # eliminate tempo change? or maybe any type of mixTableChange?
    # eliminate repeats?
    # eliminate alternate-endings?
    # force clean_electric_guitar instrument channel?
    BAR_COUNT = 4
    try:
        song = guitarpro.parse(single_track_file)
    except GPException:
        print(f"GPEXCEPTION in parsing {single_track_file.split('/')[-1]}")
        return
    # tempo = song.tempo
    assert len(song.tracks) == 1
    track = song.tracks[0]
    measures = track.measures
    bar_phrases = [
        measures[i : i + BAR_COUNT] for i in range(0, len(measures), BAR_COUNT)
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


"""below is subject to change"""


def get_anno(file, output_dir):
    # for pre-processed one-track files only
    try:
        single_track_song = guitarpro.parse(file)
    except GPException:
        print(f"GPEXCEPTION in parsing {file.split('/')[-1]}")
        return

    data = dict()
    metadata = get_metadata(single_track_song)
    data["meta"] = metadata

    gt_tracks = get_guitar_tracks(single_track_song)
    assert len(single_track_song.tracks) == 1
    track = single_track_song.tracks[0]
    track_info = get_track_info(track)

    measures = []
    for measure in track.measures:
        measure_info = get_measure_info(measure)
        notes = []
        for note in get_measure_notes(measure):
            note_info = get_note_info(note)
            note_time = get_note_time(note, metadata["tempo"])
            note_info.update(note_time)
            notes.append(note_info)
            measure_info["notes"] = notes
        measures.append(measure_info)

    track_info["measures"] = measures
    data["track"] = track_info

    file_name = "{}.json".format(file.split("/")[-1].split(".")[0])

    with open(os.path.join(output_dir, file_name), "w") as file:
        json.dump(data, file, indent=2)

