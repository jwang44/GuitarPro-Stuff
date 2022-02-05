import os, json
import librosa
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

FRAMESIZE = 2048
HOPSIZE = 512
SR = 44100

MONO_SEGMENTS_DIR = "/Volumes/MacOnly/UG_proc/all_time_top_by_hits/mono_audio_segments"
ANNO_DIR = (
    "/Volumes/MacOnly/UG_proc/all_time_top_by_hits/clean_single_track_annotations"
)
# the directory for preprocessed audio files (mono audio segments that has a reasonable length)
FILTERED_AUDIO_DIR = (
    "/Volumes/MacOnly/UG_proc/all_time_top_by_hits/mono_audio_segments_filtered"
)


def load_audio_file(file):
    """Generic function for loading an audio file into time and frequency.

    Args:
        file (str): The audio file name

    Returns:
        tuple: (times, notes), the time sequence and F0 sequence converted to MIDI notes
    """
    y, sr = librosa.load(os.path.join(FILTERED_AUDIO_DIR, file), sr=None)
    f0, _, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("G6"),
        sr=sr,
        center=False,
    )
    times = librosa.times_like(f0, sr=sr, hop_length=512, n_fft=2048)
    # convert F0 sequence to MIDI note sequence
    notes = librosa.hz_to_midi(f0)
    return times, notes


def find_anno(file, anno_dir=ANNO_DIR):
    """Given an audio file name, find the path to its corresponding annotation file. 

    Args:
        file (str): The path to the mono audio segment file.
        anno_dir (str, optional): The path to the annotation directory. Defaults to ANNO_DIR.

    Returns:
        str: The complete path to the annotation file. 
    """
    segment_name_with_onset, _ = os.path.splitext(file.split("/")[-1])
    segment_name = "_".join(segment_name_with_onset.split("_")[:-1])
    anno_file_name = segment_name + ".json"
    anno_file = os.path.join(anno_dir, anno_file_name)
    return anno_file


def plot_f0_vs_gt(file, anno_dir=ANNO_DIR):
    """Given an audio file name, plot its ground-truth pitches and estimated F0 curve

    Args:
        file (str): The filename of the mono audio segment.
        audio_dir (str, optional): The path to the audio directory. Defaults to MONO_SEGMENTS_DIR.
        anno_dir (str, optional): The path to the annotation directory. Defaults to ANNO_DIR.
    """
    times, notes = load_audio_file(file)

    anno_file = find_anno(file, anno_dir=anno_dir)
    with open(anno_file) as anno:
        note_infos = json.load(anno)

    gt = np.empty_like(notes)
    gt[:] = np.NaN

    for note in note_infos:
        onset = note["time"]["start"] * SR
        offset = (note["time"]["start"] + note["time"]["dur"]) * SR
        onset_fr = librosa.samples_to_frames(onset, hop_length=512)
        offset_fr = librosa.samples_to_frames(offset, hop_length=512)
        gt[onset_fr:offset_fr] = note["pitch"]

    plt.figure(figsize=(20, 5))
    plt.plot(times, notes, label="pYIN", color="blue")
    plt.plot(times, gt, label="GT", color="red")
    plt.legend()
    plt.show()


def get_continous_f0_segments(notes, dur_thres=80):
    """Given an estimated F0 curve, split it (on NaNs) into continuous segments

    Args:
        notes (np.Array): The estimated F0 sequence converted to MIDI note sequence
        dur_thres (int): The duration threshold for a single note event. Defaults to 80 ms. 

    Returns:
        list of F0 segment indices: A list of lists. Each list consists of the indices of a continuous F0 segment
    """
    # valid_indices are the indices of non-NaN elements
    valid_indices = [i for i in range(len(notes)) if not np.isnan(notes[i])]

    # group consecutive elements in the array
    def consecutive(data, stepsize=1):
        return np.split(data, np.where(np.diff(data) != stepsize)[0] + 1)

    # group the consecutive indices into index_segments
    f0_segments = consecutive(valid_indices)
    dur_thres_fr = librosa.time_to_frames(
        dur_thres / 1000, sr=44100, hop_length=512, n_fft=2048
    )
    valid_f0_segments = [
        f0_segment for f0_segment in f0_segments if len(f0_segment) >= dur_thres_fr
    ]
    return valid_f0_segments


def get_note_events_from_f0_segment(
    notes, f0_segment, f0_change_thres=0.5, dur_thres=80
):
    """Split a continuous F0 segment (on large freq change) into note events

    Args:
        notes (np.Array): The estimated F0 sequence converted to MIDI note sequence
        f0_segment (list): A list of indices that belong to a single continuous F0 segment, obtained from `get_continous_f0_segments(notes)`
        f0_change_threshold (float, optional): Cut the F0 segment where the difference between two adjacent frames exceeds this threshold. Defaults to 0.5 semitone.
        dur_thres (int): The duration threshold for a single note event. Defaults to 80 ms (Chen et al. 2015). 
        A 1/16 note in 200 bpm is 75ms (see DragonForce). 

    Returns:
        list of note events indices: A list of lists. Each list consists of the indices of a note event
    """
    # check that the indices in the f0 segment is indeed continuous
    assert np.all(np.diff(f0_segment, n=1) == 1)

    previous_note = notes[f0_segment[0]]
    # note_event records the indices of the elements that belongs to the current note event
    note_event = [f0_segment[0]]
    note_events = []

    # this assumes the f0 segment has at least two frames
    for i in f0_segment[1:]:
        if abs(notes[i] - previous_note) <= f0_change_thres:
            note_event.append(i)
            if i == f0_segment[-1]:
                note_events.append(note_event)
        else:
            note_events.append(note_event)
            note_event = [i]
        previous_note = notes[i]

    dur_thres_fr = librosa.time_to_frames(
        dur_thres / 1000, sr=44100, hop_length=512, n_fft=2048
    )
    valid_note_events = [
        note_event for note_event in note_events if len(note_event) >= dur_thres_fr
    ]
    return valid_note_events


# functions for picking BEND/RELEASE candidates
def count_consecutive_rise(diff):
    """Count the maximum number of consecutive frames with rising F0.

    Args:
        diff (np.Array): The 1st order diff obtained from the F0 sequence (converted to MIDI note sequence).

    Returns:
        int: How long is the longest rising trend.
    """
    cnt = 0
    max_cnt = 0
    for element in diff:
        # use >= here will count both RISE and FLAT
        # a mostly flat note (no bend/release) will also be considered as candidate
        # this should be filtered out by using the difference between the max and min freq
        if element >= 0:
            cnt += 1
        elif cnt > 0:
            max_cnt = max(max_cnt, cnt)
            cnt = 0
    if cnt > 0:
        max_cnt = max(max_cnt, cnt)
    return max_cnt


def count_consecutive_drop(diff):
    """Count the maximum number of consecutive frames with dropping F0.

    Args:
        diff (np.Array): The 1st order diff obtained from the F0 sequence (converted to MIDI note sequence).

    Returns:
        int: How long is the longest dropping trend.
    """
    cnt = 0
    max_cnt = 0
    for element in diff:
        # use >= here will count both DROP and FLAT
        # a mostly flat note (no bend/release) will also be considered as candidate
        # this should be filtered out by using the difference between the max and min freq
        if element <= 0:
            cnt += 1
        elif cnt > 0:
            max_cnt = max(max_cnt, cnt)
            cnt = 0
    if cnt > 0:
        max_cnt = max(max_cnt, cnt)
    return max_cnt


def is_bend_candidate(notes, dur_thres=80):
    """Given a F0 sequence, predict whether it is a bend instance.

    The conditions here are very easy to satisfy, the goal is to reach high recall. 
    It's ok to have many false positives but do not miss true positives.

    Args:
        notes (np.Array): An F0 sequence (converted to MIDI note sequence) of a valid note event
        dur_thres (int): The F0 must keep rising for at least `dur_thres` ms. Defaults to 80 ms. 

    Returns:
        bool: True for bend, False for not bend
    """
    diff = np.diff(notes, 1)
    # the freq should RISE monotonically for dur_thres ms
    dur_thres_fr = librosa.time_to_frames(
        dur_thres / 1000, sr=44100, hop_length=512, n_fft=2048
    )
    condition1 = count_consecutive_rise(diff) >= dur_thres_fr
    # the freq difference between two consectutive frames should be smaller than one semitone
    # this is probably always true. if two adjacent frames differ more than 1 semitone,
    # they would have been put into two separate note events
    condition2 = np.all(abs(diff) <= 1)
    # the difference between the max and min freq should be more than half a semitone
    condition3 = max(notes) - min(notes) >= 0.5
    if condition1 and condition2 and condition3:
        return True
    else:
        return False


def is_release_candidate(notes, dur_thres=80):
    """Given a F0 sequence, predict whether it is a release instance.

    The conditions here are very easy to satisfy, the goal is to reach high recall. 
    It's ok to have many false positives but do not miss true positives.

    Args:
        notes (np.Array): An F0 sequence (converted to MIDI note sequence) of a valid note event
        dur_thres (int): The F0 must keep dropping for at least `dur_thres` ms. Defaults to 80 ms. 

    Returns:
        bool: True for release, False for not release
    """
    diff = np.diff(notes, 1)
    # the freq should DROP monotonically for dur_thres ms
    dur_thres_fr = librosa.time_to_frames(
        dur_thres / 1000, sr=44100, hop_length=512, n_fft=2048
    )
    condition1 = count_consecutive_drop(diff) >= dur_thres_fr
    # the freq difference between two consectutive frames should be smaller than one semitone
    condition2 = np.all(abs(diff) <= 1)
    # the difference between the max and min freq should be more than half a semitone
    condition3 = max(notes) - min(notes) >= 0.5
    if condition1 and condition2 and condition3:
        return True
    else:
        return False


# functions for picking VIBRATO candidates
def is_vibrato_candidate(
    notes, peak_count=2, peak_dist_min=60, peak_dist_max=800, pitch_diff=1
):
    """Given the F0 sequence of a note event, predict whether it is a VIBRATO instance。

    Args:
        notes (np.Array): The F0 sequence (converted to MIDI notes) of a note event
        peak_count (int, optional): The note must have more than `peak_count` local maxima. Defaults to 2.
        peak_dist_min (int, optional): The distance between to adjancent peaks must be more than `peak_dist_min` ms. Defaults to 60 ms.
        peak_dist_max (int, optional): The distance between to adjancent peaks must be less than `peak_dist_max` ms. Defaults to 800 ms.
        pitch_diff (float, optional): The difference between the highest peak and the mean value must be less than `pitch_diff` semitones. Defaults to 1.

    Returns:
        bool: True for vibrato, False for not vibrato
    """
    # find local maxima in the pitch curve of the note event
    peak_indices, _ = find_peaks(notes)
    condition1 = len(peak_indices) >= peak_count
    # get the distance (in frames) between adjacent peaks
    peak_dists = np.diff(peak_indices, 1)
    # convert distance thresholds from time to frame
    peak_dist_min_fr = librosa.time_to_frames(
        peak_dist_min / 1000, sr=44100, hop_length=512, n_fft=2048
    )
    peak_dist_max_fr = librosa.time_to_frames(
        peak_dist_max / 1000, sr=44100, hop_length=512, n_fft=2048
    )
    # True if any two adjacent peaks satisfy the distance threshold
    condition2 = (
        np.logical_and(
            peak_dists >= peak_dist_min_fr, peak_dists <= peak_dist_max_fr
        ).any()
        if condition1
        else False
    )
    # True if the highest peak does not exceed the average too much
    condition3 = (
        np.max(notes[peak_indices]) - np.mean(notes) <= pitch_diff
        if condition1
        else False
    )
    if condition1 and condition2 and condition3:
        return True
    else:
        return False

