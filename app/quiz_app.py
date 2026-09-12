import sys

def verify_connection(arguments):
    if len(arguments) != 6:
        return 2
    from quiz_client.database import OracleGateway

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
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        if len(sys.argv) != 3:
            sys.exit(2)
        from quiz_client.diagnostics import run_self_check

        sys.exit(run_self_check(sys.argv[2]))
    if len(sys.argv) > 1 and sys.argv[1] == "--connection-check":
        sys.exit(verify_connection(sys.argv[1:]))
    from quiz_client.ui import run_application

    run_application()
