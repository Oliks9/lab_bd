import sys

from quiz_client.database import OracleGateway
from quiz_client.ui import run_application


def verify_connection(arguments):
    if len(arguments) != 6:
        return 2
    gateway = OracleGateway()
    try:
        gateway.connect(arguments[1], arguments[2], arguments[3])
        gateway.authenticate(arguments[4], arguments[5])
        return 0
    except Exception:
        return 1
    finally:
        gateway.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--connection-check":
        sys.exit(verify_connection(sys.argv[1:]))
    run_application()
