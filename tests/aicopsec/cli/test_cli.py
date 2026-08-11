import re
import sys
from argparse import ArgumentParser

import pytest
import httpx
import os
import subprocess
import time

import ai4copsec.restapi.cli.main as cli_main
from ai4copsec.restapi.cli.restapi import RestapiParser

from ai4copsec.restapi.db_operations import DBManager
from ai4copsec.restapi.utils.command import Command
from ai4copsec.restapi.db.v1.db_tables import SampleDisk
from ai4copsec.restapi.app_settings import AI4COPSEC_RESTAPI_PORT

@pytest.fixture
def subparsers():
    return [
        "restapi",
    ]

def test_help(subparsers, capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['ai4copsec-restapi'])
    cli_main.run()
    captured = capsys.readouterr()

    for subparser in subparsers:
        assert re.search(subparser, captured.out), f"Help for subcommand '{subparser}' expected"


@pytest.mark.parametrize("name, klass", [
    [ "restapi", RestapiParser ],
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

@pytest.mark.asyncio(loop_scope="function")
async def test_restapi_settings_from_env(script_runner, tmp_path, test_db_v2, db_config, timescaledb):
    """
    AppSettings should read setting plainly from env as well
    """
    env = os.environ.copy()
    #env['AI4COPSEC_RESTAPI_DATABASE_URI'] = timescaledb

    p = subprocess.Popen(['slurm-monitor', 'restapi'], env=env)

    time.sleep(5)
    response = httpx.get(f"http://localhost:{AI4COPSEC_RESTAPI_PORT}/api/v1/docs")

    p.kill()
    p.wait()

    assert response.status_code == 200
