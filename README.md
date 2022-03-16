# dukop.dk

[![Build Status](https://circleci.com/gh/dukop/django-dukop/tree/main.svg?style=shield)](https://circleci.com/gh/dukop/django-dukop/tree/main)

Collaborate calendar for local *spheres*, such as "DukOp Copenhagen" or "DukOp Århus".

## System requirements

What you are now looking at is a Python package, structured as a
[Django](https://www.djangoproject.com/) project. The various other Python
packages that it depends on will be installed while you install the package
itself.

These are the system requirements necessary for running the below Quickstart:

* Python 3.8+ (is already on your system)
* Postgres (**only** for deployment, not needed for development)

Other requirements are specified as Python packages in the *Quickstart* below
and will be installed in a *virtual environment*.

## Quickstart

Install the project and the development dependencies into a
[virtual environment](https://docs.python.org/3.7/tutorial/venv.html):

From a commandline, run:

```console
# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Upgrade to the latest Python dist tools (pip etc)
python3 -m pip install --upgrade pip setuptools wheel

# Install the package in development mode, meaning that you can keep editing
# the sources and not have to re-install.
python3 -m pip install --editable ".[dev]"

# Run the migration script to create the database
python3 manage.py migrate

# Create a superuser account so you can also log in for the first time.
python3 manage.py createsuperuser

# Generate some random event data
python3 manage.py calendar_fixtures
```

The development environment is now ready with an empty database and a single
admin user. To run the server and access it from your browser, use the
`runserver` command:

```console
./manage.py runserver
```

After running the server for the first time, consider logging in on
http://127.0.0.1:8080/admin/ to create some data for development.


## Updating from git

Once in a while, you will probably pull the latest master. In this case, you
could need to run the migration script in order to update your local development
database:

```console
./manage.py migrate
```


## Running tests

More details to come, but for now, just open a PR and wait for Travis or run
this:

```console
pytest
```

## Starting a New App

First create a new directory in the `apps` directory:

```console
mkdir src/dukop/apps/name
```

Then pass the path to the new directory to the
[startapp](https://docs.djangoproject.com/en/2.1/ref/django-admin/#django-admin-startapp)
command:

```console
mkdir src/dukop/apps/<name>
python manage.py startapp name src/dukop/apps/<name>
```
