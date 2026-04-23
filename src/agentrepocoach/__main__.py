"""Enable ``python -m agentrepocoach``."""
from .cli import main

raise SystemExit(main())  # See cli.py:main() for argument parsing
