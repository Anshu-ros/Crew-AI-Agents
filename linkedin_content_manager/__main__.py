"""Command-line entry point."""

import argparse
import json
import logging
import sys

from linkedin_content_manager.config import ConfigurationError, load_settings
from linkedin_content_manager.logging_config import configure_logging
from linkedin_content_manager.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research, draft, critique, optimize, and schedule a LinkedIn post."
    )
    parser.add_argument("topic", help="Topic for the LinkedIn post")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the dotenv file (default: .env)",
    )
    args = parser.parse_args()

    try:
        settings = load_settings(args.env_file)
    except ConfigurationError as error:
        parser.error(str(error))

    configure_logging()
    try:
        record = run_pipeline(args.topic, settings)
    except Exception as error:
        logging.getLogger(__name__).exception("Pipeline failed")
        print(f"Pipeline failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(record, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
