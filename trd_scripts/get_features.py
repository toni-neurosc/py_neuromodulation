import os
from re import VERBOSE

import numpy as np
import scipy.io as spio
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import LabelEncoder
from multiprocessing import Pool
import pickle

from py_neuromodulation import nm_stream_offline, nm_define_nmchannels

from yaml import load

PATH_DATA = r"C:\Users\ICN_admin\Documents\TRD Analysis"


def loadmat(filename):
    """
    this function should be called instead of direct spio.loadmat
    as it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    """
    data = spio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    return _check_keys(data)


def _check_keys(dict):
    """
    checks if entries in dictionary are mat-objects. If yes
    todict is called to change them to nested dictionaries
    """
    for key in dict:
        if isinstance(dict[key], spio.matlab.mio5_params.mat_struct):
            dict[key] = _todict(dict[key])
    return dict


def _todict(matobj):
    """
    A recursive function which constructs from matobjects nested dictionaries
    """
    dict = {}
    for strg in matobj._fieldnames:
        elem = matobj.__dict__[strg]
        if isinstance(elem, spio.matlab.mio5_params.mat_struct):
            dict[strg] = _todict(elem)
        else:
            dict[strg] = elem
    return dict


def set_settings(settings: dict):

    settings["features"]["fft"] = True
    settings["features"]["fooof"] = True
    settings["features"]["return_raw"] = True
    settings["features"]["raw_hjorth"] = True
    settings["features"]["sharpwave_analysis"] = True
    settings["features"]["nolds"] = True
    settings["features"]["bursts"] = True
    settings["features"]["coherence"] = True

    settings["preprocessing"]["re_referencing"] = False
    settings["preprocessing"]["preprocessing_order"] = [
        "raw_resampling",
        "notch_filter",
    ]

    settings["postprocessing"]["feature_normalization"] = True
    settings["postprocessing"]["project_cortex"] = False
    settings["postprocessing"]["project_subcortex"] = False

    settings["fooof"]["periodic"]["center_frequency"] = False
    settings["fooof"]["periodic"]["band_width"] = False
    settings["fooof"]["periodic"]["height_over_ap"] = False

    for key in list(
        settings["sharpwave_analysis_settings"]["sharpwave_features"].keys()
    ):
        settings["sharpwave_analysis_settings"]["sharpwave_features"][
            key
        ] = True
    settings["sharpwave_analysis_settings"]["sharpwave_features"][
        "peak_left"
    ] = False
    settings["sharpwave_analysis_settings"]["sharpwave_features"][
        "peak_right"
    ] = False
    settings["sharpwave_analysis_settings"]["sharpwave_features"][
        "trough"
    ] = False
    settings["sharpwave_analysis_settings"][
        "apply_estimator_between_peaks_and_troughs"
    ] = True

    settings["sharpwave_analysis_settings"]["estimator"]["max"] = [
        "prominence",
        "sharpness",
    ]
    settings["sharpwave_analysis_settings"]["estimator"]["mean"] = [
        "width",
        "interval",
        "decay_time",
        "rise_time",
        "rise_steepness",
        "decay_steepness",
        "slope_ratio",
    ]

    settings["coherence"]["channels"] = [
        ["Cg25L01", "Cg25L03"],
        ["Cg25R01", "Cg25R03"],
        ["Cg25L01", "Cg25R03"],
        ["Cg25R01", "Cg25L03"],
    ]

    settings["coherence"]["frequency_bands"] = ["high beta", "low gamma"]
    settings["coherence"]["method"]["coh"] = True
    settings["coherence"]["method"]["icoh"] = True

    settings["nolds_features"]["sample_entropy"] = False
    settings["nolds_features"]["correlation_dimension"] = False
    settings["nolds_features"]["lyapunov_exponent"] = False
    settings["nolds_features"]["hurst_exponent"] = True
    settings["nolds_features"]["detrended_fluctutaion_analysis"] = False
    settings["nolds_features"]["data"]["raw"] = True
    settings["nolds_features"]["data"]["frequency_bands"] = [
        "low beta",
        "high beta",
        "low gamma",
        "HFA",
    ]

    return settings


def run_patient_GenericStream(f):

    file_name = os.path.basename(f)[: -len("_edit.mat")]
    dat = loadmat(os.path.join(PATH_DATA, f))["D"]
    labels = dat["labels"][~np.array(dat["bad"], dtype="bool")]

    data = np.swapaxes(np.swapaxes(dat["data"], 0, 2), 1, 2)
    data = data[~np.array(dat["bad"], dtype="bool"), :, :]
    NUM_CH = data.shape[1]

    label_encoder = LabelEncoder()
    integer_encoded = label_encoder.fit_transform(labels)

    enc = OneHotEncoder(handle_unknown="ignore", sparse=False)
    label_arr = enc.fit_transform(integer_encoded.reshape(-1, 1))

    label_arr_concat = np.concatenate(
        (np.expand_dims(integer_encoded + 1, axis=1), label_arr), axis=1
    )  # integer encoded + 1, since REST will be set to zero

    label_arr_epochs = np.zeros([data.shape[0], 4, data.shape[2]])
    label_arr_epochs_names = list(label_encoder.classes_)
    label_arr_epochs_names.insert(0, "ALL")

    integer_encoded_names = label_arr_epochs_names.copy()
    integer_encoded_names[0] = "REST"

    # label_arr_epochs columns: ALL, NTR, PLS, UNPLS
    # integer_encoded_names: 0 - REST, 1 - NTR, 2 - PLS, 3 - UNPLS

    arr_insert = np.repeat(label_arr_concat[:, :, np.newaxis], 1000, axis=2)
    label_arr_epochs[:, :, 3500:4500] = arr_insert

    data_comb = np.concatenate((data, label_arr_epochs), axis=1)
    data_stream = np.concatenate(data_comb, axis=1)

    ch_names = list(dat["ch_names"])
    ch_names = ch_names + label_arr_epochs_names

    ch_types = ["seeg" for _ in range(NUM_CH)]
    ch_types = ch_types + ["misc" for _ in range(len(label_arr_epochs_names))]

    nm_channels = nm_define_nmchannels.set_channels(
        ch_names=ch_names,
        ch_types=ch_types,
        reference=None,
        bads=None,
        used_types=["seeg"],
    )

    stream = nm_stream_offline.Stream(
        settings=None,
        nm_channels=nm_channels,
        verbose=True,
    )

    stream.set_settings_fast_compute()

    stream.settings = set_settings(stream.settings)

    stream.init_stream(
        sfreq=dat["fsample"],
        line_noise=50,
    )

    stream.nm_channels.loc[
        stream.nm_channels.query('type == "misc"').index, "target"
    ] = 1

    stream.run(
        data=data_stream,
        folder_name=file_name,
        out_path_root=os.path.join(PATH_DATA, "30_05"),
    )


def main():

    files = [f for f in os.listdir(PATH_DATA) if "_edit" in f]
    # for f in files:
    #    run_patient_GenericStream(f)
    pool = Pool(processes=len(files))
    pool.map(run_patient_GenericStream, files)


if __name__ == "__main__":
    main()