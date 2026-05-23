from secrets import token_urlsafe


def main() -> None:
    print(token_urlsafe(32))


if __name__ == "__main__":
    main()
