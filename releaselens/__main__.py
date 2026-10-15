import argparse
import logging
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Synthetic loopback-only sandbox")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    if args.demo:
        os.environ["RELEASELENS_DEMO"] = "true"
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import uvicorn

    from releaselens.api import create_app

    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
