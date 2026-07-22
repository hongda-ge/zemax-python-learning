from zemax_runner import connect_zemax, close_zemax


def main() -> None:
    zos = None

    try:
        zos, app, system = connect_zemax()
        print("Application object:", app is not None)
        print("System object:", system is not None)
    finally:
        close_zemax(zos)


if __name__ == "__main__":
    main()
