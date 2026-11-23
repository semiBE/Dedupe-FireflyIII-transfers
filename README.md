# Dedupe transfers

Copy `.env.example` to `.env` and set `FIREFLY_URL` and `FIREFLY_TOKEN`.
Keep `.env` private. Install dependencies with `py -m pip install -r requirements.txt`.

Run `py main.py` for one scan. Schedule recurring runs externally, for example
with cron or Windows Task Scheduler. The script-local `.env` takes precedence
over process environment variables, including when a value is blank.

The scan is a dry run by default. Add `--delete` to delete duplicates, or
`--days 30` to change the scan window. Fetch errors terminate the process;
individual deletion failures are reported and cause a nonzero exit status.

## Container

Build the image and pass configuration at runtime (the `.env` file is excluded
from the build context):

```powershell
docker build -t firefly-dedupe .
docker create --name firefly-dedupe --env-file .env firefly-dedupe
docker start -a firefly-dedupe
```

The container runs once and remains stopped after completion. Schedule
`docker start -a firefly-dedupe` externally; do not use `--rm` or a restart
policy. Docker's `--env-file` passes values as environment variables; use
plain, unquoted values. To enable deletion or change the scan window, supply
the options when creating the container:

```powershell
docker create --name firefly-dedupe --env-file .env firefly-dedupe --delete --days 30
```

Use `docker logs --timestamps firefly-dedupe` to view output and errors from
the runs. Docker must be running when the external scheduler starts the
container. Recreate the container to apply changes to `.env` or its options.
