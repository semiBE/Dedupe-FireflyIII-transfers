# Dedupe transfers

Copy `.env.example` to `.env` and set `FIREFLY_URL` and `FIREFLY_TOKEN`.
Keep `.env` private. Install dependencies with `py -m pip install -r requirements.txt`.

Run `py main.py` for one scan. Schedule recurring runs externally, for example
with cron or Windows Task Scheduler. The script-local `.env` takes precedence
over process environment variables, including when a value is blank.

The scan is a dry run by default (`DRY_RUN=true`). Set `DRY_RUN=false` in
`.env` or the environment to delete duplicates. Only `true` and `false`
(case-insensitive) are accepted. `--delete` explicitly enables deletion even
when `DRY_RUN=true`; invalid values still cause an error. Add `--days 30` to
change the scan window. Fetch errors terminate the process; individual deletion
failures are reported and cause a nonzero exit status.

## Docker Compose

Docker Compose builds the image using the Dockerfile and supplies `.env` at
runtime. The `.env` file is excluded from the build context; use plain,
unquoted values for Docker's environment file.

```powershell
docker compose up --build -d
docker compose logs --timestamps firefly-dedupe
```

This builds the image and starts one scan; the container remains stopped
afterwards. Schedule `docker compose start firefly-dedupe` externally, using
the project directory or `docker compose -f` with an absolute path to the
Compose file. Docker must be running when the scheduler starts the container.

Set `DRY_RUN=false` in `.env` to enable deletion. Recreate the container with
`docker compose up --build --force-recreate -d` to apply changes to `.env` or
the image; this also starts a scan. For non-default command-line options, add a
`command` to the service, for example `command: ["--days", "30"]`.
