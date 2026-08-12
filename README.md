# AI4COPSEC REST API

This package provides the RESTAPI for AI4COPSEC

Full documentation: https://ai4copsec.github.io/ai4copsec-restapi

## Installation
First, create a python virtual environment:

```
python3 -m venv .venv-ai4copsec
source .venv-ai4copsec/bin/activate
```

Then clone the repo (currently the package is not available via pypi):

Install locally with all dependencies (development and test included, refer to
pyproject.toml for the optional dependencies):

```
git clone git@github.com:ai4copsec/ai4copsec-restapi.git
cd ai4copsec-restapi

git config --global url."git@github.com:".insteadOf "https://github.com/"

pip install .
```

## Usage

All use cases are covered by subcommand of the ai4copsec-restapi command line tool.
By default, settings are read from a .env file that resides in the current working directory.
Note, that all subcommands take a '--env-file <filename>' argument to specify a specific configuration to load.

### start:

```
    $> ai4copsec-restapi start --port=12000
```

The API should now be accessible on port 12000.
You are now able to check the openapi docs via:
```
    http://127.0.0.1:12000/api/v1/docs
```

#### Running with ssl

To run with ssl, get or create a certificate and run as follows:

```
    openssl req -nodes -new -x509 -keyout key.pem -out cert.pem -days 365 -subj "/C=countrycode/ST=state/L=city/O=Organization Name/OU=Unit Name/CN=cname/emailAddress=creator@yourdomain"
    ai4copsec-restapi start --reload --port 12000 --host 0.0.0.0 --ssl-keyfile key.pem --ssl-certfile cert.pem
```


#### Enabling OAuth

By default Bearer token based authentication is disabled. To enable set the configuration according to
your identity provider. The setup has been developed/tested with keycloak.

Add the authentication configuration to the .env file, e.g.:

```
AI4COPSEC_RESTAPI_OAUTH_REQUIRED=true
AI4COPSEC_RESTAPI_OAUTH_URL="http://ai4copsec.identity-provider.org"
AI4COPSEC_RESTAPI_OAUTH_REALM="ai4copsec-realm"
```

## Development

Task shortcuts are collected in the `justfile` (requires
[`uv`](https://docs.astral.sh/uv/) and [`just`](https://just.systems/)):

```
just install   # install all dependencies (extras + dependency groups)
just lint      # format + lint with ruff
just test      # run the test suite
just docs      # build the Quarto documentation site locally (./public)
just bump PATCH|MINOR|MAJOR  # lint + test, then bump the version, tag and push
```

## Testing
For testing one can run tox.

```
    tox -e timescaledb
```

## Contributing

This project is open to contributions. For details on how to contribute please check the [Contribution Guidelines](https://github.com/ai4copsec/ai4copsec-restapi/CONTRIBUTING.md)

## License
This project is licensed under the [TO BE DEFINED](https://github.com/ai4copsec/ai4copsec-restapi/blob/main/LICENSE).

## Copyright
Copyright (c) 2026 [AI4COPSEC Consortium](https://www.ai4copsec.eu/consortium)

## Acknowledgments

The development of this library is part of the EU-project [AI4COPSEC](https://ai4copsec.eu) which receives funding
 from the Horizon Europe framework programme under Grant Agreement N. 101190021.
