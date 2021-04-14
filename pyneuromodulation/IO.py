import mne_bids
import numpy as np
import os
import json


def read_BIDS_data(PATH_RUN, BIDS_PATH):
    """Given a run path and bids data path, read the respective data

    Parameters
    ----------
    PATH_RUN : string
    BIDS_PATH : string

    Returns
    -------
    raw_arr : mne.io.RawArray
    raw_arr_data : np.ndarray
    fs : int
    line_noise : int
    """
    entities = mne_bids.get_entities_from_fname(PATH_RUN)

    bids_path = mne_bids.BIDSPath(subject=entities["subject"],
                                  session=entities["session"],
                                  task=entities["task"],
                                  run=entities["run"],
                                  acquisition=entities["acquisition"],
                                  datatype="ieeg", root=BIDS_PATH)

    raw_arr = mne_bids.read_raw_bids(bids_path)

    return (raw_arr, raw_arr.get_data(), int(np.ceil(raw_arr.info["sfreq"])),
            int(raw_arr.info["line_freq"]))


def add_labels(df_, settings_wrapper, raw_arr_data):
    """Given a constructed feature data frame, resample the target labels and add to dataframe

    Parameters
    ----------
    df_ : pd.DataFrame
        computed feature dataframe
    settings_wrapper : settings.py
        initialized settings used for feature estimation
    raw_arr_data : np.ndarray
        raw data including target

    Returns
    -------
    df_ : pd.DataFrame
        computed feature dataframe including resampled features
    """
    # resample_label
    ind_label = np.where(settings_wrapper.df_M1["target"] == 1)[0]
    if ind_label.shape[0] != 0:
        offset_time = max([value[1] for value in settings_wrapper.settings[
            "bandpass_filter_settings"]["frequency_ranges"].values()])
        offset_start = np.ceil(offset_time/1000 * settings_wrapper.settings["fs"]).astype(int)
        dat_ = raw_arr_data[ind_label, offset_start:]
        if dat_.ndim == 1:
            dat_ = np.expand_dims(dat_, axis=0)
        label_downsampled = dat_[:, ::int(np.ceil(settings_wrapper.settings["fs"] /
                                 settings_wrapper.settings["sampling_rate_features"]))]

        # and add to df
        if df_.shape[0] == label_downsampled.shape[1]:
            for idx, label_ch in enumerate(settings_wrapper.df_M1["name"][ind_label]):
                df_[label_ch] = label_downsampled[idx, :]
        else:
            print("label dimensions don't match, saving downsampled label extra")
    else:
        print("no target specified")

    return df_


def save_features_and_settings(df_, folder_name, settings_wrapper):
    """save settings.json, df_M1.tsv and features.csv

    Parameters
    ----------
    df_ : pd.Dataframe
        feature dataframe
    folder_name : string
        output path
    settings_wrapper : settings.py object
    """
    # create out folder if doesn't exist
    if not os.path.exists(os.path.join(settings_wrapper.settings["out_path"], folder_name)):
        print("create output folder "+str(folder_name))
        os.makedirs(os.path.join(settings_wrapper.settings["out_path"], folder_name))

    df_.to_csv(os.path.join(settings_wrapper.settings["out_path"], folder_name,
                            folder_name+"_FEATURES.csv"))

    with open(os.path.join(settings_wrapper.settings["out_path"], folder_name,
                           folder_name+'_SETTINGS.json'), 'w') as f:
        json.dump(settings_wrapper.settings, f)

    # save df_M1 as csv
    settings_wrapper.df_M1.to_csv(os.path.join(settings_wrapper.settings["out_path"], folder_name,
                                  folder_name+"_DF_M1.csv"))