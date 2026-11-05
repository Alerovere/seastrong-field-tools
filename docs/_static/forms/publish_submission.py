"""Prepare, or explicitly publish, the static form without changing the source branch."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ASSETS = [
    "index.html", "submission.css", "submission.js", "submission-config.js",
    "submission-core.js", "submission-report.js", "submission-records.js", "drive-client.js",
    "survey-schema.js", "survey-tables.js", "pdf-lib.min.js", "pdf-lib.LICENSE.md",
    "SUBMISSION_SETUP.md",
]
MARKER = "seastrong-submission-site.json"


def git(folder, *args, check=True):
    return subprocess.run(["git", "-C", str(folder), *args], text=True, capture_output=True, check=check)


def package(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        shutil.copy2(source / name, destination / name)
    for pdf in sorted(source.glob("*_field_form_v*.pdf")):
        shutil.copy2(pdf, destination / pdf.name)
    (destination / ".nojekyll").touch()
    (destination / MARKER).write_text(json.dumps({"site": "SEASTRONG field submission", "source": "docs/_static/forms", "version": 1}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true", help="Prepare local files only; no network or publication")
    action.add_argument("--publish", action="store_true", help="Publish this folder to origin/gh-pages")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    if args.prepare:
        destination = Path(tempfile.mkdtemp(prefix="seastrong-pages-"))
        package(source, destination)
        print("Copia preparata, non pubblicata:\n" + str(destination))
        return

    repo = Path(git(source, "rev-parse", "--show-toplevel").stdout.strip())
    origin = git(repo, "remote", "get-url", "origin").stdout.strip()
    email = git(repo, "config", "user.email", check=False).stdout.strip()
    name = git(repo, "config", "user.name", check=False).stdout.strip()
    if not email or not name:
        raise SystemExit("Impostare nome ed email Git per il repository prima di pubblicare.")
    remote = git(repo, "ls-remote", "--exit-code", "origin", "refs/heads/gh-pages", check=False)
    if remote.returncode not in (0, 2):
        raise SystemExit("Non riesco a verificare il ramo remoto. Controllare l'accesso a GitHub; nessuna pubblicazione eseguita.")
    with tempfile.TemporaryDirectory(prefix="seastrong-publish-") as temporary:
        stage = Path(temporary)
        if remote.returncode == 0:
            clone = subprocess.run(["git", "clone", "--single-branch", "--branch", "gh-pages", origin, str(stage)], capture_output=True, text=True)
            if clone.returncode:
                raise SystemExit("Impossibile leggere il ramo gh-pages; nessuna modifica eseguita.")
            try:
                marker = json.loads((stage / MARKER).read_text())
                if marker.get("site") != "SEASTRONG field submission":
                    raise ValueError()
            except (OSError, ValueError):
                raise SystemExit("gh-pages contiene gia un sito non riconosciuto. Pubblicazione interrotta per conservarlo.")
        else:
            git(stage, "init", "-b", "gh-pages")
            git(stage, "remote", "add", "origin", origin)
        git(stage, "config", "user.name", name)
        git(stage, "config", "user.email", email)
        package(source, stage)
        git(stage, "add", "--all")
        if not git(stage, "status", "--porcelain").stdout.strip():
            print("Il sito pubblicato e gia aggiornato.")
            return
        git(stage, "commit", "-m", "Publish SEASTRONG field submission portal")
        pushed = git(stage, "push", "origin", "HEAD:refs/heads/gh-pages", check=False)
        if pushed.returncode:
            raise SystemExit("Push non riuscito. Nessun force push eseguito; riprovare dopo aver verificato accesso e aggiornamenti remoti.")
    print("Ramo gh-pages aggiornato. In GitHub: Settings > Pages > Deploy from a branch > gh-pages > /(root).")


if __name__ == "__main__":
    main()
