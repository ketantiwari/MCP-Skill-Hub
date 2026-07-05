from dynamic_mcp_skill_hub.mcp import run_server
from dynamic_mcp_skill_hub.utils import configure_logging, logger


def main() -> None:
    configure_logging()
    logger.info("starting_dynamic_mcp_skill_hub")
    run_server()


if __name__ == "__main__":
    main()
