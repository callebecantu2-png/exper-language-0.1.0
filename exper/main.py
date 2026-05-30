import sys

from . import language
from . import errors as er

# ================= MAIN =================
def main():
    if len(sys.argv) < 2:
        print("Uso: python exper.py arquivo.exper")
        return

    file_path = sys.argv[1]

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    lang = language.Exper()

    try:
        lang.run(code)

    except er.ExperError as e:
        print(e)


if __name__ == "__main__":
    main()