import datetime as dt
import logging
from argparse import ArgumentParser

import httpx
import polars as pl
from ai4copsec.tbi.ais_anomaly_detection.types import Input, Output
from ai4copsec.tbi.types import Algorithm, Vessel, Waypoint
from damast.core.dataframe import AnnotatedDataFrame

from ai4copsec.restapi.app_settings import AppSettings

from .base import BaseParser

logger = logging.getLogger(__name__)

# Columns of the raw AIS feed (e.g. data/AIS_2026_08_01.parquet in damast-examples) that
# are needed to build a trajectory - anything else in the file is ignored.
_REQUIRED_COLUMNS = ["mmsi", "msgtime", "latitude", "longitude", "speedOverGround", "courseOverGround"]


def _select_algorithm(registered: list[str]) -> str:
    """Interactively prompt the user to pick one of the registered AAD algorithms.

    Args:
        registered: Algorithm names currently registered on the queried restapi.

    Returns:
        The chosen algorithm name.

    Raises:
        ValueError: If `registered` is empty, or the user's selection is neither a valid
            list index nor an exact algorithm name.
        RuntimeError: If no interactive input is available (e.g. stdin is closed).
    """
    if not registered:
        raise ValueError("No AAD algorithms are registered on the restapi - nothing to select from")

    print("No --algorithm given - registered AAD algorithms:")
    for i, name in enumerate(registered, start=1):
        print(f"  {i}. {name}")

    try:
        choice = input(f"Select an algorithm [1-{len(registered)}] or type its name: ").strip()
    except EOFError:
        raise RuntimeError(
            "No --algorithm given and no interactive input available - "
            f"pass --algorithm explicitly, one of: {registered}"
        )

    if choice in registered:
        return choice

    if choice.isdigit() and 1 <= int(choice) <= len(registered):
        return registered[int(choice) - 1]

    raise ValueError(f"Invalid selection '{choice}' - expected 1-{len(registered)} or one of {registered}")


class AADTestParser(BaseParser):
    """Score real AIS trajectories using a registered AIS Anomaly Detection (AAD) algorithm.
    Score by using a running restapi instance (start one with `ai4copsec-restapi start`).
    """

    def __init__(self, parser: ArgumentParser):
        super().__init__(parser=parser, db_required=False)

        app_settings = AppSettings.get_instance()

        parser.description = (
            "Load AIS trajectories from one or more files against a "
            "running restapi's AAD endpoint, e.g.:\n"
            "  ai4copsec-restapi aad-test AIS_2026_08_01.parquet"
        )
        parser.add_argument(
            "data_file",
            nargs="+",
            type=str,
            help="AIS data file(s) to load, e.g. one or more .parquet files (same format required for all)",
        )
        parser.add_argument(
            "--algorithm",
            type=str,
            default=None,
            help="AAD algorithm to score with; if omitted, you will be prompted to choose from "
            "the algorithms registered on the restapi",
        )
        parser.add_argument(
            "--mmsi",
            type=int,
            nargs="+",
            default=None,
            help="MMSI(s) to score; default: the --limit vessels with the most waypoints in the data",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of vessels to score when --mmsi is not given, default: %(default)s",
        )
        parser.add_argument(
            "--min-points",
            type=int,
            default=5,
            help="Minimum number of waypoints a trajectory must have to be scored, default: %(default)s",
        )
        parser.add_argument(
            "--max-points",
            type=int,
            default=200,
            help="Cap each trajectory to its most recent N waypoints, default: %(default)s",
        )
        parser.add_argument(
            "--host", type=str, default="localhost", help="Host of the running restapi to query, default: %(default)s"
        )
        parser.add_argument(
            "--port",
            type=int,
            default=app_settings.port,
            help=f"Port of the running restapi to query, default: {app_settings.port}",
        )
        parser.add_argument(
            "--token", type=str, default=None, help="Bearer token, if the restapi requires authentication"
        )

    def execute(self, args):
        super().execute(args)

        app_settings = AppSettings.get_instance()
        scheme = "https" if app_settings.ssl.keyfile else "http"
        base_url = f"{scheme}://{args.host}:{args.port}/api/v1/technological_brick/aad"
        headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}

        with httpx.Client(base_url=base_url, headers=headers, timeout=60) as client:
            try:
                response = client.get("/algorithms")
            except httpx.ConnectError as e:
                raise RuntimeError(
                    f"Could not reach restapi at {base_url} ({e}) - is it running? "
                    "(start it with 'ai4copsec-restapi start')"
                )
            response.raise_for_status()

            registered = sorted(m["algorithm"] for m in response.json())
            if args.algorithm is None:
                algorithm = _select_algorithm(registered)
            elif args.algorithm not in registered:
                raise ValueError(
                    f"Algorithm '{args.algorithm}' is not registered for AAD on {base_url} - "
                    f"registered: {registered or '<none>'}"
                )
            else:
                algorithm = args.algorithm

            logger.info(f"Loading {args.data_file} via damast ...")
            annotated_df = AnnotatedDataFrame.from_files(args.data_file, metadata_required=False)
            trajectories = annotated_df.dataframe.collected().select(_REQUIRED_COLUMNS).drop_nulls()

            counts = trajectories.group_by("mmsi").len()
            if args.mmsi:
                mmsi_list = args.mmsi
            else:
                mmsi_list = (
                    counts.filter(pl.col("len") >= args.min_points)
                    .sort("len", descending=True)
                    .head(args.limit)["mmsi"]
                    .to_list()
                )

            if not mmsi_list:
                print(f"No vessel has >= {args.min_points} waypoints in {args.data_file}")
                return

            trajectories = (
                trajectories.filter(pl.col("mmsi").is_in(mmsi_list))
                .with_columns(pl.col("msgtime").str.to_datetime(time_zone="UTC").alias("timestamp"))
                .sort(["mmsi", "timestamp"])
            )

            for mmsi in mmsi_list:
                trajectory_df = trajectories.filter(pl.col("mmsi") == mmsi).tail(args.max_points)
                if trajectory_df.height < args.min_points:
                    print(
                        f"mmsi={mmsi}: skipped, only {trajectory_df.height} waypoints (< --min-points {args.min_points})"
                    )
                    continue

                waypoints = [
                    Waypoint(
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        sog=row["speedOverGround"],
                        cog=row["courseOverGround"],
                        timestamp=row["timestamp"],
                    )
                    for row in trajectory_df.iter_rows(named=True)
                ]

                # The model scores what comes after the historic trajectory - mirror
                # AISAnomalyDetection.create_input_sample()'s choice of a 6h window right after it.
                start_time = waypoints[-1].timestamp + dt.timedelta(seconds=1)
                input_data = Input(
                    trajectory=waypoints,
                    start_time=start_time,
                    end_time=start_time + dt.timedelta(hours=6),
                    algorithm=Algorithm(name=algorithm, parameters={}),
                    vessel=Vessel(mmsi=mmsi),
                )

                print(f"\nmmsi={mmsi}, waypoints={len(waypoints)}, algorithm={algorithm}:")
                response = client.post("/compute", json=input_data.model_dump(mode="json"))

                if response.status_code != 200:
                    print(f"  request failed ({response.status_code}): {response.text}")
                    continue

                result = Output.model_validate(response.json())
                print(result.model_dump_json(indent=2))
