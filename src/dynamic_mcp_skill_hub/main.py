from argparse import ArgumentParser
import json

from dynamic_mcp_skill_hub.interceptor import QueryInterceptor
from dynamic_mcp_skill_hub.mcp import run_server
from dynamic_mcp_skill_hub.utils import configure_logging, logger


def main() -> None:
    parser = ArgumentParser(prog="dynamic-mcp-skill-hub")
    parser.add_argument("--query", help="Run a single query through the interceptor and exit.")
    args = parser.parse_args()

    configure_logging()
    if args.query:
        result = QueryInterceptor().intercept(args.query)
        logger.info("query_interceptor_result", result=result)
        print(json.dumps(result, indent=2))
        return

    logger.info("starting_dynamic_mcp_skill_hub")
    run_server()


if __name__ == "__main__":
    main()
