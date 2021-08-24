from time import time
from numpy import concatenate, vstack, expand_dims
from numpy import round as np_round
from pandas import DataFrame, Series

from pyneuromodulation import nm_normalization


class Run:

    def __init__(self, features, settings, reference=None, projection=None,
                 resample=None, verbose=True) -> None:
        """Initialize run class

        Parameters
        ----------
        features : features.py object
            Feature_df object (needs to be initialized beforehand)
        settings : dict
            dictionary of settings such as "seglengths" or "frequencyranges"
        reference : reference.py object
            Rereference object (needs to be initialized beforehand), by default None
        projection : projection.py object
            projection object (needs to be initialized beforehand), by default None
        resample : resample.py object
            Resample object (needs to be initialized beforehand), by default None
        verbose : boolean
            if True, print out signal processed and computation time
        """

        self.features = features
        self.feature_arr = None
        self.feature_arr_raw = None
        self.raw_arr = None
        self.proj_cortex = settings["methods"]["project_cortex"]
        self.proj_subcortex = settings["methods"]["project_subcortex"]
        self.proj_cortex_array = None
        self.proj_subcortex_array = None
        self.dat_cortex = None
        self.dat_subcortex = None
        self.reference = reference
        self.resample = resample
        self.projection = projection
        self.settings = settings
        self.fs_new = int(settings["sampling_rate_features"])
        self.fs = features.fs
        self.sample_add = int(self.fs / self.fs_new)
        self.verbose = verbose
        self.offset = max([value[1] for value in settings[
            "bandpass_filter_settings"]["frequency_ranges"].values()])  # ms

        if settings["methods"]["project_cortex"] is True:
            self.idx_chs_ecog = []  # feature series indexes for dbs-lfp channels
            self.names_chs_ecog = []  # feature series name of ecog features
            self.ecog_channels = [
                settings["ch_names"][ch_idx] for ch_idx, ch in enumerate(settings["ch_types"]) if ch == "ecog"]
        if settings["methods"]["project_subcortex"] is True:
            self.idx_chs_lfp = []  # feature series indexes for ecog channels
            self.names_chs_lfp = []  # feature series name of lfp features
            #  mind here that settings["coord"]["subcortex_left/right"] is based on the "LFP" substring in the channel
            self.lfp_channels = settings["coord"]["subcortex_right"]["ch_names"] \
                if settings["sess_right"] is True \
                else settings["coord"]["subcortex_left"]["ch_names"]

        if settings["methods"]["raw_normalization"] is True:
            self.raw_normalize_samples = int(
                settings["raw_normalization_settings"][
                    "normalization_time"] * self.fs)

        if settings["methods"]["feature_normalization"] is True:
            self.feat_normalize_samples = int(
                settings["feature_normalization_settings"][
                    "normalization_time"] * self.fs_new)

        self.cnt_samples = 0

    def run(self, ieeg_batch):
        """Given a new data batch, estimate features and store in object.

        Parameters
        ----------
        ieeg_batch : np.ndarray
            Current batch of raw data

        Returns
        -------
        None
        """
        start_time = time()

        # re-reference
        if self.settings["methods"]["re_referencing"] is True:
            ieeg_batch = self.reference.rereference(ieeg_batch)

        ieeg_batch = ieeg_batch[self.settings["feature_idx"], :]

        # resample
        if self.settings["methods"]["raw_resampling"] is True:
            ieeg_batch = self.resample.raw_resampling(ieeg_batch)

        # normalize raw data
        if self.settings["methods"]["raw_normalization"] is True:
            if self.cnt_samples == 0:
                self.raw_arr = ieeg_batch
            else:
                self.raw_arr = concatenate(
                    (self.raw_arr, ieeg_batch[:, -self.sample_add:]), axis=1)
            ieeg_batch = nm_normalization.normalize_raw(
                self.raw_arr, self.raw_normalize_samples, self.fs,
                self.settings["raw_normalization_settings"]["normalization_method"],
                self.settings["raw_normalization_settings"]["clip"])

        feature_series = Series(self.features.estimate_features(ieeg_batch),
                                dtype=float)

        if self.cnt_samples == 0:
            self.cnt_samples += int(self.fs)

            if self.settings["methods"]["feature_normalization"] is True:
                self.feature_arr_raw = DataFrame([feature_series], dtype=float)
                feature_series.values[:] = 0.

            if any((self.proj_cortex, self.proj_subcortex)):
                self.init_projection_run(feature_series)

            feature_series["time"] = self.offset  # ms
            self.feature_arr = DataFrame([feature_series])

        else:
            self.cnt_samples += self.sample_add

            if self.settings["methods"]["feature_normalization"]:
                self.feature_arr_raw = self.feature_arr_raw.append(
                    feature_series, ignore_index=True)
                feature_series = nm_normalization.normalize_features(
                    feature_series, self.feature_arr_raw,
                    self.feat_normalize_samples,
                    self.settings["feature_normalization_settings"][
                        "normalization_method"],
                    self.settings["feature_normalization_settings"][
                        "clip"])

            if any((self.proj_cortex, self.proj_subcortex)):
                self.next_projection_run(feature_series)

            feature_series["time"] = self.cnt_samples * 1000 / self.fs  # ms
            self.feature_arr = self.feature_arr.append(
                feature_series, ignore_index=True)

        if self.verbose is True:
            print(str(np_round(feature_series["time"] / 1000, 2)) +
                  ' seconds of data processed')
            print("Last batch took: " + str(np_round(time() - start_time, 2)) +
                  " seconds")

    def init_projection_run(self, feature_series):
        """"""

        #  here it is assumed that only one hemisphere is recorded at a time!
        if self.proj_cortex:
            for ecog_channel in self.ecog_channels:
                self.idx_chs_ecog.append([ch_idx for ch_idx, ch in enumerate(feature_series.keys())
                                          if ch.startswith(ecog_channel + '_')])
                self.names_chs_ecog.append([ch for _, ch in enumerate(feature_series.keys())
                                            if ch.startswith(ecog_channel + '_')])
            self.dat_cortex = vstack([feature_series.iloc[idx_ch].values for idx_ch in self.idx_chs_ecog])

        if self.proj_subcortex:
            # for lfp_channels select here only the ones from the correct hemisphere!
            for lfp_channel in self.lfp_channels:
                self.idx_chs_lfp.append([ch_idx for ch_idx, ch in enumerate(feature_series.keys())
                                        if ch.startswith(lfp_channel + '_')])
                self.names_chs_lfp.append([ch for _, ch in enumerate(feature_series.keys())
                                          if ch.startswith(lfp_channel + '_')])
            self.dat_subcortex = vstack([feature_series.iloc[idx_ch].values for idx_ch in self.idx_chs_lfp])
        # now project data
        proj_cortex, proj_subcortex = self.projection.get_projected_cortex_subcortex_data(
            self.dat_cortex, self.dat_subcortex)
        self.proj_cortex_array = expand_dims(proj_cortex, axis=0)
        self.proj_subcortex_array = expand_dims(proj_subcortex, axis=0)

    def next_projection_run(self, feature_series):
        """"""

        if self.proj_cortex:
            self.dat_cortex = vstack(
                [feature_series.iloc[idx_ch].values for idx_ch in
                 self.idx_chs_ecog])
        if self.proj_subcortex:
            self.dat_subcortex = vstack(
                [feature_series.iloc[idx_ch].values for idx_ch in
                 self.idx_chs_lfp])
        proj_cortex, proj_subcortex = self.projection.get_projected_cortex_subcortex_data(
            self.dat_cortex, self.dat_subcortex)
        self.proj_cortex_array = concatenate(
            (self.proj_cortex_array, expand_dims(proj_cortex, axis=0)), axis=0)
        self.proj_subcortex_array = concatenate(
            (self.proj_subcortex_array, expand_dims(proj_subcortex, axis=0)), axis=0)