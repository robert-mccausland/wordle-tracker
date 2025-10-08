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
