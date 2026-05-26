from pathlib import Path


def main():
    p = Path("C:/app")
    p.mkdir(parents=True, exist_ok=True)
    out = p / "output.txt"
    out.write_text("harbor-hell: task completed")
    print("Wrote", out)


if __name__ == "__main__":
    main()
