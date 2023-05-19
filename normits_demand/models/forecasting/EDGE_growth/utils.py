# -*- coding: utf-8 -*-
"""
Utils for edge growth, such as conversions between matrix formats.
"""
# Built-Ins
import itertools
import pathlib
from typing import Tuple

# Third Party
import numpy as np
import pandas as pd

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
from normits_demand.matrices.cube_mat_converter import CUBEMatConverter

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #

# # # FUNCTIONS # # #
def long_mx_2_wide_mx(
    mx_df: pd.DataFrame,
    row: str = "no_entry",
    col: str = "no_entry",
    value: str = "no_entry",
) -> np.ndarray:
    """Convert pandas long matrix to numpy wide matrix.

    Function assumes default entry of a pandas dataframe of three columns:
        [origin/from/production, destination,to/attraction, demand]
    Can be specified if the matrix is of a different length or order.

    Parameters
    ----------
    mx_df : pd.DataFrame
        pandas long matrix dataframe to convert
    row : str, optional
        rows vector in the matrix dataframe
    col : str, optional
        columns vector in the matrix dataframe
    value : str, optional
        demand vector in the matrix dataframe

    Returns
    -------
    np.ndarray
        numpy wide matrix
    """
    # if user specified entries
    if row == "no_entry":
        row = mx_df.columns[0]
    if col == "no_entry":
        col = mx_df.columns[1]
    if value == "no_entry":
        value = mx_df.columns[2]

    # reshape to wide numpy matrix
    wide_mx = mx_df.pivot_table(
        index=row, columns=col, values=value
    ).values

    return wide_mx


def wide_mx_2_long_mx(
    mx_np: np.ndarray,
    rows: str = "from_stn_zone_id",
    cols: str = "to_stn_zone_id",
    values: str = "Demand",
) -> pd.DataFrame:
    """Convert numpy wide matrix to pandas long matrix.

    Function assumes conversion is happening to a stn2stn matrix hence the headers
    for the output dataframe are named to station level by default. Optional entries
    can be given through rows, cols and values

    Parameters
    ----------
    mx_np : np.ndarray
        numpy wide matrix dataframe to convert
    row : str, optional
        rows vector in the matrix dataframe
    col : str, optional
        columns vector in the matrix dataframe
    value : str, optional
        demand vector in the matrix dataframe

    Returns
    -------
    mx_df : pd.DataFrame
        pandas long matrix
    """
    # get omx array to pandas dataframe and reset productions
    mx_df = (
        pd.DataFrame(mx_np)
        .reset_index()
        .rename(columns={"index": rows})
    )
    # melt DF to get attractions vector
    mx_df = mx_df.melt(id_vars=[rows], var_name=cols, value_name=values)
    # adjust zone number
    mx_df[rows] = mx_df[rows] + 1
    mx_df[cols] = mx_df[cols] + 1

    return mx_df


def transpose_matrix(
    mx_df: pd.DataFrame, stations: bool = False
) -> pd.DataFrame:
    """Transpose a matrix O<>D/P<>A.

    Parameters
    ----------
    mx : pd.DataFrame
        input matrix to transpose
    stations : bool
        whether it's a stations matrix or not

    Returns
    -------
    mx : pd.DataFrame
        transposed matrix
    """
    # o/d columns
    from_col = "from_model_zone_id"
    to_col = "to_model_zone_id"
    # if stations matrix, update the od columns
    if stations:
        from_col = "from_stn_zone_id"
        to_col = "to_stn_zone_id"
    # transpose to-home PA to OD by renaming from <> to model zone id
    mx_df = mx_df.rename(
        columns={
            from_col: to_col,
            to_col: from_col,
        }
    )

    return mx_df


def expand_matrix(
    mx_df: pd.DataFrame, zones: int = 1300, stations: bool = False
) -> pd.DataFrame:
    """Expand matrix to all possible movements (zones x zones).

    Parameters
    ----------
    mx_df : pd.DataFrame
        matrix
    zones: int
        number of model zones, default = 1300
    stations : bool
        whether it's a stations matrix or not'
    Returns
    -------
    expanded_mx : pd.DataFrame
        expanded matrix
    """
    # o/d columns
    od_cols = ["from_model_zone_id", "to_model_zone_id"]
    # if stations matrix, update the od columns
    if stations:
        od_cols = ["from_stn_zone_id", "to_stn_zone_id"]
    # create empty dataframe
    expanded_mx = pd.DataFrame(
        list(
            itertools.product(range(1, zones + 1), range(1, zones + 1))
        ),
        columns=od_cols,
    )
    # get first matrix
    expanded_mx = expanded_mx.merge(
        mx_df, how="outer", on=od_cols
    ).fillna(0)
    return expanded_mx


def filter_stations(stations_lookup, df):
    """
    I think this is redundant as the df is left merged to stations lookup on
    both filtered columns.
    """
    used_stations = stations_lookup["STATIONCODE"].to_list()
    df = df.loc[
        (df["ZoneCodeFrom"].isin(used_stations))
        & (df["ZoneCodeTo"].isin(used_stations))
    ]
    return df


def merge_to_stations(stations_lookup, df, left_from, left_to):
    factors_df = df.merge(
        stations_lookup,
        how="right",
        left_on=[left_from],
        right_on=["STATIONCODE"],
    )
    # rename
    factors_df = factors_df.rename(
        columns={"stn_zone_id": "from_stn_zone_id"}
    )
    # merge on destination/attraction
    factors_df = factors_df.merge(
        stations_lookup,
        how="right",
        left_on=[left_to],
        right_on=["STATIONCODE"],
    )
    factors_df.dropna(axis=0, inplace=True)
    # rename
    factors_df = factors_df.rename(
        columns={
            "stn_zone_id": "to_stn_zone_id",
            "Demand_rate": "Demand",
        }
    )
    return factors_df


def convert_csv_2_mat(
    norms_segments: list,
    cube_exe: pathlib.Path,
    fcast_year: int,
    output_folder: pathlib.Path,
) -> None:
    """Convert CSV output matrices to Cube .MAT.
    Function converts output CSV matrices into a single Cube .MAT matrix
    in NoRMS input demand matrix format
    Parameters
    ----------
    norms_segments : list
        list of NoRMS input demand segments
    cube_exe : Path
        path to Cube Voyager executable
    fcast_year : int
        forecast year
    output_folder : Path
        path to folder where CSV matrices are saved. this is where the .MAT
        will also be saved to
    """
    # empty dictionary
    mats_dict = {}
    # create a dictionary of matrices and their paths
    for segment in norms_segments:
        mats_dict[segment] = pathlib.Path(
            output_folder, f"{fcast_year}_24Hr_{segment}.csv"
        )

    # call CUBE convertor class
    c_m = CUBEMatConverter(cube_exe)
    c_m.csv_to_mat(
        1300,
        mats_dict,
        pathlib.Path(output_folder, f"PT_24hr_Demand_{fcast_year}.MAT"),
        1,
    )


def zonal_from_to_stations_demand(
    demand_mx: pd.DataFrame,
    irsj_props: pd.DataFrame,
    stations_count: int,
    userclass: int,
    to_home: bool = False,
) -> Tuple[np.ndarray, pd.DataFrame]:
    """Create a stn2stn matrix and produce a two way conversion lookup (zonal <> stations).

    Parameters
    ----------
    demand_mx : pd.DataFrame
        demand matrix dataframe
    irsj_props : pd.DataFrame
        iRSj split probabilities dataframe
    stations_count : int
        number of stations
    userclass : int
        segments userclass
    to_home : bool
        True if the demand is a ToHome demand

    Returns
    -------
    np_mx: np.ndarray
        numpy wide matrix
    zonal_from_to_stns: pd.dataframe
        zonal <> stations conversion lookup

    """
    # expand matrix
    demand_mx = expand_matrix(demand_mx)
    # add userclass info
    demand_mx.loc[:, "userclass"] = userclass
    # if ToHome demand then transpose matrix
    if to_home:
        demand_mx = transpose_matrix(demand_mx)
    # merge demand matrix to iRSj probabilities
    mx_df = demand_mx.merge(
        irsj_props,
        how="left",
        on=["from_model_zone_id", "to_model_zone_id", "userclass"],
    )
    # find zone to zone movements with demand but no proportion
    missing_props = mx_df.loc[
        (mx_df["proportion"].isna()) & (mx_df["Demand"] > 0),
        ["from_model_zone_id", "to_model_zone_id"],
    ]
    # rename column
    mx_df = mx_df.rename(columns={"proportion": "stn_from_zone"})
    # calculate movement demand proportion
    mx_df.loc[:, "Demand"] = mx_df["Demand"] * mx_df["stn_from_zone"]

    # sum stn2stn demand
    stn2stn_mx = (
        mx_df.groupby(["from_stn_zone_id", "to_stn_zone_id"])["Demand"]
        .sum()
        .reset_index()
    )
    # rename column
    stn2stn_mx = stn2stn_mx.rename(
        columns={"Demand": "stn2stn_total_demand"}
    )

    # join the stn2stn demand total to the main matrix
    mx_df = mx_df.merge(
        stn2stn_mx,
        how="left",
        on=["from_stn_zone_id", "to_stn_zone_id"],
    )
    # calculate stn 2 zone proportions
    mx_df.loc[:, "stn_to_zone"] = (
        mx_df["Demand"] / mx_df["stn2stn_total_demand"]
    )

    # create lookup dataframe
    zonal_from_to_stns = mx_df[
        [
            "from_model_zone_id",
            "from_stn_zone_id",
            "to_stn_zone_id",
            "to_model_zone_id",
            "stn_from_zone",
            "stn_to_zone",
        ]
    ]
    # create stn2stn matrix dataframe
    mx_df = mx_df[["from_stn_zone_id", "to_stn_zone_id", "Demand"]]
    # expand matrix
    mx_df = expand_matrix(mx_df, zones=stations_count, stations=True)
    # group by stations
    mx_df = (
        mx_df.groupby(["from_stn_zone_id", "to_stn_zone_id"])["Demand"]
        .sum()
        .reset_index()
    )
    # remove no-record stations
    mx_df = mx_df.loc[
        (mx_df["from_stn_zone_id"] != 0)
        & (mx_df["to_stn_zone_id"] != 0)
    ].reset_index(drop=True)

    # fill na
    zonal_from_to_stns = zonal_from_to_stns.fillna(0)
    mx_df = mx_df.fillna(0)

    # convert to long matrix
    np_mx = long_mx_2_wide_mx(mx_df)

    return np_mx, zonal_from_to_stns