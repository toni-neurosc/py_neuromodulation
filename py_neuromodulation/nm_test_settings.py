import pandas as pd
from py_neuromodulation import nm_normalization

def test_settings(
    settings : dict,
    nm_channel : pd.DataFrame,
    verbose=True,) -> None:
    """Test if settings are specified correctly in nm_settings.json
    Parameters
    ----------
    settings: dict
        settings to tests
    verbose: boolean
        set to True if feedback is desired.
    Returns
    -------
    None
    """
    s = settings

    assert isinstance(s["sampling_rate_features_hz"], (float, int))
    if s["methods"]["project_cortex"] is True:
        assert isinstance(
            s["project_cortex_settings"]["max_dist_cm"], (float, int)
        )
    if s["methods"]["project_subcortex"] is True:
        assert isinstance(
            s["project_subcortex_settings"]["max_dist_cm"], (float, int)
        )
    assert (
        isinstance(value, bool) for value in s["methods"].values()
    ), "Methods must be a boolean value."
    assert any(
        value is True for value in s["methods"].values()
    ), "Set at least one method to True."
    if s["methods"]["raw_resampling"] is True:
        assert isinstance(
            s["raw_resampling_settings"]["resample_freq_hz"], (float, int)
        )
    if s["methods"]["raw_normalization"] is True:
        assert isinstance(
            s["raw_normalization_settings"]["normalization_time_s"],
            (float, int),
        )
        assert s["raw_normalization_settings"]["normalization_method"] in [
            "mean",
            "median",
            "zscore",
        ]
        assert isinstance(
            s["raw_normalization_settings"]["clip"], (float, int, bool)
        )
    if s["methods"]["feature_normalization"] is True:
        assert isinstance(
            s["feature_normalization_settings"]["normalization_time_s"],
            (float, int),
        )
        assert s["feature_normalization_settings"][
            "normalization_method"
        ] in [e.value for e in nm_normalization.NORM_METHODS]
        assert isinstance(
            s["feature_normalization_settings"]["clip"], (float, int, bool)
        )
    if s["methods"]["kalman_filter"] is True:
        assert isinstance(s["kalman_filter_settings"]["Tp"], (float, int))
        assert isinstance(
            s["kalman_filter_settings"]["sigma_w"], (float, int)
        )
        assert isinstance(
            s["kalman_filter_settings"]["sigma_v"], (float, int)
        )
        assert s["kalman_filter_settings"][
            "frequency_bands"
        ], "No frequency bands specified for Kalman filter."
        assert isinstance(
            s["kalman_filter_settings"]["frequency_bands"], list
        ), "Frequency bands for Kalman filter must be specified as a list."
        assert (
            item
            in s["bandpass_filter_settings"]["frequency_ranges_hz"].values()
            for item in s["kalman_filter_settings"]["frequency_bands"]
        ), (
            "Frequency bands for Kalman filter must also be specified in "
            "bandpass_filter_settings."
        )
    if s["methods"]["bandpass_filter"] is True:
        assert isinstance(s["frequency_ranges_hz"], dict)
        assert (
            isinstance(value, list)
            for value in s["frequency_ranges_hz"].values()
        )
        assert (
            len(value) == 2 for value in s["frequency_ranges_hz"].values()
        )
        assert (
            isinstance(value[0], list)
            for value in s["frequency_ranges_hz"].values()
        )
        assert (
            len(value[0]) == 2 for value in s["frequency_ranges_hz"].values()
        )
        assert (
            isinstance(value[1], (float, int))
            for value in s["frequency_ranges_hz"].values()
        )
        assert (
            isinstance(value, bool)
            for value in s["bandpass_filter_settings"][
                "bandpower_features"
            ].values()
        )
        assert any(
            value is True
            for value in s["bandpass_filter_settings"][
                "bandpower_features"
            ].values()
        ), "Set at least one bandpower_feature to True."
    if s["methods"]["sharpwave_analysis"] is True:
        assert isinstance(
            s["sharpwave_analysis_settings"]["filter_low_cutoff_hz"],
            (int, float),
        )
        assert isinstance(
            s["sharpwave_analysis_settings"]["filter_high_cutoff_hz"],
            (int, float),
        )
        assert (
            s["sharpwave_analysis_settings"]["filter_high_cutoff_hz"]
            > s["sharpwave_analysis_settings"]["filter_low_cutoff_hz"]
        )

    if s["methods"]["coherence"] is True:
        assert (
            ch_coh in nm_channel.name for ch_coh in s["coherence"]["channels"]
        )

        assert (
            f_band_coh in s["frequency_ranges_hz"]
            for f_band_coh in s["coherence"]["frequency_bands"]
        )

    if verbose:
        print("No Error occurred when testing the settings.")
    return
