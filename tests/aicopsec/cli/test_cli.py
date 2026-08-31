import re
import signal
import sys
from argparse import ArgumentParser

import pytest
import httpx
import os
import subprocess
import time

import ai4copsec.restapi.cli.main as cli_main
from ai4copsec.restapi.cli.restapi import RestapiParser
from ai4copsec.restapi.cli.aad_test import AADTestParser, _select_algorithm

from ai4copsec.restapi.app_settings import AI4COPSEC_RESTAPI_PORT

@pytest.fixture
def subparsers():
    return [
        "restapi",
        "aad-test",
    ]

def test_help(subparsers, capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['ai4copsec-restapi'])
    cli_main.run()
    captured = capsys.readouterr()

    for subparser in subparsers:
        assert re.search(subparser, captured.out), f"Help for subcommand '{subparser}' expected"


@pytest.mark.parametrize("name, klass", [
    [ "restapi", RestapiParser ],
    [ "aad-test", AADTestParser ],
])
def test_subparser(name, klass, script_runner):
    result = script_runner.run(['ai4copsec-restapi', name, "--help"])
    assert result.returncode == 0, f"Expected --help option for {name} subparser"

    test_parser = ArgumentParser()
    klass(parser=test_parser)

    for a in test_parser._actions:
        if a.help == "==SUPPRESS==":
            continue

        for option in a.option_strings:
            assert re.search(option, result.stdout) is not None, f"Should have {option=}"


@pytest.mark.parametrize("user_input, expected", [
    ["1", "default-aad"],
    ["2", "transformer-behavioral"],
    ["transformer-behavioral", "transformer-behavioral"],
    [" 1 ", "default-aad"],
])
def test_select_algorithm_valid_choice(monkeypatch, user_input, expected):
    monkeypatch.setattr("builtins.input", lambda prompt: user_input)
    assert _select_algorithm(["default-aad", "transformer-behavioral"]) == expected


def test_select_algorithm_invalid_choice(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "not-a-known-algorithm")
    with pytest.raises(ValueError, match="Invalid selection"):
        _select_algorithm(["default-aad"])


def test_select_algorithm_no_interactive_input(monkeypatch):
    def _raise_eof(prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise_eof)
    with pytest.raises(RuntimeError, match="no interactive input available"):
        _select_algorithm(["default-aad"])


def test_select_algorithm_nothing_registered():
    with pytest.raises(ValueError, match="nothing to select from"):
        _select_algorithm([])


def _write_synthetic_ais_parquet(path):
    """Write a tiny parquet file in the raw-AIS-feed schema `TestAADParser` expects
    (mmsi/msgtime/latitude/longitude/speedOverGround/courseOverGround), without depending
    on any external dataset.
    """
    import polars as pl

    rows = [
        {
            "mmsi": mmsi,
            "msgtime": f"2026-08-01T00:0{i}:00+00:00",
            "latitude": base_lat + i * 0.001,
            "longitude": base_lon + i * 0.001,
            "speedOverGround": 5.0,
            "courseOverGround": 90.0,
        }
        for mmsi, base_lat, base_lon in [(111111111, 59.0, 10.0), (222222222, 60.0, 5.0)]
        for i in range(6)
    ]
    pl.DataFrame(rows).write_parquet(path)


def _wait_for_restapi(port, timeout=20):
    """Poll the AAD algorithms endpoint until the server (started via `ai4copsec-restapi
    start` in a subprocess) answers, or raise once `timeout` seconds have passed."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"http://localhost:{port}/api/v1/technological_brick/aad/algorithms", timeout=2)
            if response.status_code == 200:
                return
        except httpx.TransportError as e:
            last_error = e
        time.sleep(0.5)

    raise RuntimeError(f"restapi on port {port} did not become ready within {timeout}s: {last_error}")


@pytest.fixture
def running_restapi():
    """Start a real `ai4copsec-restapi start` server in a subprocess, so `aad-test` tests
    exercise it over HTTP - the same way an actual user of `aad-test` would - rather than
    calling `AISAnomalyDetection` in-process.

    `start_new_session=True` puts the CLI process (and the uvicorn child it spawns via its
    own `subprocess.Popen`) in their own process group, so killing that group on teardown
    takes the uvicorn child down too - killing just the CLI process would leave it orphaned.
    """
    port = 55556
    process = subprocess.Popen(['ai4copsec-restapi', 'start', '--port', str(port)], start_new_session=True)
    try:
        _wait_for_restapi(port)
        yield port
    finally:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def test_test_aad_unregistered_algorithm(running_restapi, tmp_path):
    """If a plugin providing an algorithm is is not installed - this should fail with a clear error, not a traceback."""

    data_file = tmp_path / "ais.parquet"
    _write_synthetic_ais_parquet(data_file)

    result = subprocess.run(
        ['ai4copsec-restapi', 'aad-test', str(data_file), '--port', str(running_restapi), '--algorithm', 'not-available'],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert re.search("not registered", result.stdout)


def test_test_aad_scores_trajectories(running_restapi, tmp_path):
    """Loading a file via damast and scoring its trajectories through a running restapi's
    `/technological_brick/aad/compute` endpoint (the in-repo 'default-aad' model) should
    succeed end-to-end."""
    data_file = tmp_path / "ais.parquet"
    _write_synthetic_ais_parquet(data_file)

    result = subprocess.run(
        [
            'ai4copsec-restapi', 'aad-test', str(data_file),
            '--algorithm', 'default-aad', '--min-points', '5', '--port', str(running_restapi),
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search("mmsi=111111111", result.stdout)
    assert re.search("mmsi=222222222", result.stdout)
    assert re.search('"anomalies"', result.stdout)


@pytest.mark.asyncio(loop_scope="function")
async def test_restapi_env_file_not_existing(script_runner, test_db_v2, db_config, timescaledb):
    result = script_runner.run(['ai4copsec-restapi', 'restapi', '--env-file', 'non-existing-envfile'])
    assert result.returncode != 0

@pytest.mark.asyncio(loop_scope="function")
async def test_restapi_env_file_via_args(script_runner, tmp_path, test_db_v2, db_config, timescaledb):
    """
    Use --env-file <filename> to point to the envfile which should be used
    """
    port = 55555
    with open(tmp_path / "existing-envfile", "w") as f:
        f.write(f"SLURM_MONITOR_DATABASE_URI={timescaledb}\n")
        f.write(f"SLURM_MONITOR_PORT={port}\n")

    p = subprocess.Popen(['ai4copsec-restapi', 'restapi', '--env-file', str(tmp_path / 'existing-envfile')])

    time.sleep(5)
    response = httpx.get(f"http://localhost:{port}/api/v2/docs")

    p.kill()
    p.wait()

    assert response.status_code == 200

@pytest.mark.asyncio(loop_scope="function")
async def test_restapi_env_file_via_env(script_runner, tmp_path, test_db_v2, db_config, timescaledb):
    """
    Set the AI4COPSEC_RESTAPI_ENV_FILE to point to the envfile which should be used
    """
    port = 55555
    with open(tmp_path / "existing-envfile", "w") as f:
        f.write(f"AI4COPSEC_RESTAPI_PORT={port}\n")

    env = os.environ.copy()
    env['AI4COPSEC_RESTAPI_ENV_FILE'] = str(tmp_path / 'existing-envfile')
    p = subprocess.Popen(['ai4copsec-restapi', 'restapi'], env=env)

    time.sleep(5)
    response = httpx.get(f"http://localhost:{port}/api/v1/docs")

    p.kill()
    p.wait()

    assert response.status_code == 200

@pytest.mark.asyncio(loop_scope="function")
async def test_restapi_env_file_with_overrides(script_runner, tmp_path, test_db_v2, db_config, timescaledb):
    """
    Using --env-file <filename> to point to the envfile which should be used, should take precedence over
    environment variables
    """
    port = 55554
    with open(tmp_path / ".a.env", "w") as f:
        f.write(f"AI4COPSEC_RESTAPI_PORT={port}\n")

    port = 55555
    with open(tmp_path / ".b.env", "w") as f:
        f.write(f"AI4COPSEC_RESTAPI_PORT={port}\n")

    env = os.environ.copy()
    env['AI4COPSEC_RESTAPI_ENV_FILE'] = str(tmp_path / '.a.env')
    p = subprocess.Popen(['ai4copsec-restapi', 'restapi', '--env-file', '.b.env'], env=env)

    time.sleep(5)
    response = httpx.get(f"http://localhost:{port}/api/v1/docs")

    p.kill()
    p.wait()

    assert response.status_code == 200

@pytest.mark.skip("DB Setup not yet implemented")
@pytest.mark.asyncio(loop_scope="function")
async def test_restapi_settings_from_env(script_runner, tmp_path, test_db, db_config, timescaledb):
    """
    AppSettings should read setting plainly from env as well
    """
    env = os.environ.copy()
    #env['AI4COPSEC_RESTAPI_DATABASE_URI'] = timescaledb

    p = subprocess.Popen(['ai4copsec-restapi', 'restapi'], env=env)

    time.sleep(5)
    response = httpx.get(f"http://localhost:{AI4COPSEC_RESTAPI_PORT}/api/v1/docs")

    p.kill()
    p.wait()

    assert response.status_code == 200
