import os
from multiprocessing import Pool
import py_neuromodulation as nm
import xgboost
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import LabelEncoder

import py_neuromodulation as nm
from py_neuromodulation import (
    nm_analysis,
    nm_decode,
    nm_define_nmchannels,
    nm_IO,
)
from sklearn import linear_model, metrics, model_selection
from skopt import space as skopt_space


def set_settings(settings: dict):
    for method in list(settings["methods"].keys()):
        settings["methods"][method] = False

    settings["methods"]["fft"] = True
    settings["methods"]["fooof"] = True
    settings["methods"]["return_raw"] = True
    settings["methods"]["raw_hjorth"] = True
    settings["methods"]["re_referencing"] = False
    settings["methods"]["raw_normalization"] = False
    settings["methods"]["feature_normalization"] = True

    settings["fooof"]["periodic"]["center_frequency"] = False
    settings["fooof"]["periodic"]["band_width"] = False
    settings["fooof"]["periodic"]["height_over_ap"] = False

    settings["methods"]["sharpwave_analysis"] = True

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
    settings["sharpwave_analysis_settings"][
        "apply_estimator_between_peaks_and_troughs"
    ] = True
    settings["sharpwave_analysis_settings"]["filter_low_cutoff"] = 5
    settings["sharpwave_analysis_settings"]["filter_high_cutoff"] = 40

    settings["sharpwave_analysis_settings"]["estimator"]["max"].append("trough")
    settings["sharpwave_analysis_settings"]["estimator"]["mean"].append("width")
    settings["sharpwave_analysis_settings"]["estimator"]["max"].append(
        "decay_time"
    )
    settings["sharpwave_analysis_settings"]["estimator"]["max"].append(
        "rise_time"
    )
    settings["sharpwave_analysis_settings"]["estimator"]["max"].append(
        "rise_steepness"
    )
    settings["sharpwave_analysis_settings"]["estimator"]["max"].append(
        "decay_steepness"
    )
    settings["sharpwave_analysis_settings"]["estimator"]["mean"].append(
        "slope_ratio"
    )

    return settings


def preprocess_trd_data(dat):

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

    return data_stream, ch_names, ch_types, dat["fsample"]


def run_patient_offline_stream(f):

    file_name = os.path.basename(f)[: -len("_edit.mat")]
    dat = nm_IO.loadmat(os.path.join(PATH_DATA, f))["D"]

    data_stream, ch_names, ch_types, fs = preprocess_trd_data(dat)

    # add nm_channels

    nm_channels = nm_define_nmchannels.set_channels(
        ch_names=ch_names,
        ch_types=ch_types,
        reference=None,
        bads=[],
        new_names="default",
        used_types=("seeg",),
        target_keywords=None,
    )
    stream.nm_channels.loc[
        stream.nm_channels.query('type == "misc"').index, "target"
    ] = 1

    PATH_OUT = r"C:\Users\ICN_admin\Documents\TRD Analysis\features_epochs_OUT"
    stream = nm.Stream(
        settings=None,
        nm_channels=nm_channels,
        path_out=PATH_OUT,
        path_grids=None,
        verbose=True,
    )
    stream.settings = set_settings(stream.settings)
    stream.run(
        data=data_stream,
        sfreq=fs,
    )


PATH_DATA = r"C:\Users\ICN_admin\Documents\TRD Analysis"


def main():

    files = [f for f in os.listdir(PATH_DATA) if "_edit" in f]
    for f in files:
        run_patient_offline_stream(f)
    # pool = Pool(processes=len(files))
    # pool.map(run_patient_GenericStream, files)


if __name__ == "__main__":
    main()
