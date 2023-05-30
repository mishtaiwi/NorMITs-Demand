# -*- coding: utf-8 -*-
"""
Created on: 26/05/2023
Updated on:

Original author: Ben Taylor
Last update made by:
Other updates made by:

File purpose:

"""
# Built-Ins
import dataclasses
import pickle
from pathlib import Path
# Third Party
import pandas as pd

# Local Imports
# pylint: disable=import-error,wrong-import-position
from normits_demand.models.forecasting import forecast_cnfg
from normits_demand.utils import file_ops
import ticket_splits


# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #


@dataclasses.dataclass
class GLobalVars:
    demand_segments: pd.DataFrame
    purposes: list
    norms_segments: list
    all_segments: list
    ticket_type_splits: pd.DataFrame
    station_tlcs: pd.DataFrame
    time_periods: tuple = ("AM", "IP", "PM", "OP")

    def keys(self):
        return [field.name for field in dataclasses.fields(self)]


# # # FUNCTIONS # # #
def load_globals(params: forecast_cnfg.EDGEParameters) -> GLobalVars:
    """
    Load in global variables for the process (i.e. variables which don't vary by year/time_period/segment).
    """
    demand_segments = file_ops.read_df(params.demand_segments)
    norms_segments = (
        demand_segments.loc[demand_segments["ModelSegment"] == 1][
            ["Segment"]
        ]
        .drop_duplicates()
        .values.tolist()
    )
    purposes = demand_segments["Purpose"].drop_duplicates().to_list()
    norms_segments = [
        segment for sublist in norms_segments for segment in sublist
    ]
    # all segments
    all_segments = demand_segments["Segment"].to_list()
    demand_segments.loc[:, "ToHome"] = demand_segments["ToHome"].astype(
        bool
    )
    model_stations_tlcs = file_ops.read_df(
        params.norms_to_edge_stns_path
    )
    if isinstance(params.ticket_type_splits, Path):
        with open(params.ticket_type_splits, "rb") as file:
            ticket_type_splits = pickle.load(file)
    else:
        edge_flows = file_ops.read_df(
            params.ticket_type_splits.edge_flows_path, usecols=[0, 2, 5]
        )
        flows_lookup = file_ops.read_df(params.ticket_type_splits.flow_cat_path)
        ticket_splits_df = file_ops.read_df(
            params.ticket_type_splits.splits_path
        )
        ticket_type_splits = ticket_splits.splits_loop(
            edge_flows,
            model_stations_tlcs,
            flows_lookup,
            ticket_splits_df,
            params.matrices_to_grow_dir,
        )
    vars = GLobalVars(
        demand_segments,
        purposes,
        norms_segments,
        all_segments,
        ticket_type_splits,
        model_stations_tlcs,
    )
    return vars