# Wordle Tracker

Short description of your project goes here XD

## Setup

### Prerequisites

Make sure you have the following prerequisites installed:

-   Python 3.11+
-   Git
-   Make

### Clone the repository:

```bash
git clone https://github.com/robert-mccausland/wordle-tracker.git
cd wordle-tracker
```

### Create a virtual environment:

```bash
python -m venv .venv
```

### Activate the virtual environment:

#### Linux / macOS:

```bash
source .venv/bin/activate
```

#### Windows (cmder):

```bash
source .venv/Scripts/activate
```

**Make sure your virtual environment is activated when running any subsequent commands**

### Run project setup:

```bash
make setup
```

### IDE setup:

You should now be ready to develop, but you may find it useful to configure your IDE with support for the following tools:

-   Mypy
-   Flake8
-   Black

## Development Workflow

### Linting and Type Checking

```bash
make check
```

### Formatting

```bash
make format
```

### Pre-commit

-   Pre-commit hooks automatically run formatting, linting and type checking.

### Run the project

```bash
python manage.py runserver
```

### Run the bot

To run the bot you will need to configure it with a token to access discord's servers.

```bash
cp .env.example .env
```

Fill the `TOKEN` variable with your secret discord token, which you can get from the [discord developer portal](https://discord.com/developers/applications)

Once you have the `.env` file setup you can run the bot:

```bash
make run-bot
```

### Deployment

Code committed to the `main` branch will be automatically deployed.

On the VM the container has a memory limit (default `256m`, swap capped to match) and `restart: unless-stopped`, so a memory leak gets it OOM-killed and restarted rather than starving the other bots on the VM (ZOO-49). To change the limit, set a `MEM_LIMIT` variable (e.g. `384m`) on the GitHub environment and redeploy; see `deploy/docker-compose.yml`. The release rejects a value that isn't a whole number with a `b`/`k`/`m`/`g` suffix, or is below `32m`, before touching the VM. If the bot gets stuck in a restart loop at the limit, stop it (`docker-compose stop` on the VM) or redeploy with a higher limit rather than leaving it looping: each restart logs in to Discord again, and too many logins in a day can get the token reset. Any extra copy on the same VM (e.g. a staging deployment) has its own limit, which counts towards the VM's ~1 GB.
