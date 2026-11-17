"""Profiling separado e auditoria do pacote instalado contra a tag oficial 1.6.1."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pstats
import subprocess
import sys
import zipfile
from benchmark import ROOT, save_json, validate_site


def main(work, run):
    import mkdocs
    assert mkdocs.__version__ == "1.6.1"
    audit = []
    for p in ("commands/build.py", "structure/pages.py", "contrib/search/__init__.py", "contrib/search/search_index.py"):
        installed = Path(mkdocs.__file__).parent / p
        official = ROOT / "experimentos" / "fontes-oficiais" / "mkdocs" / p
        clean = lambda file: file.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip() + "\n"
        same = clean(installed) == clean(official)
        assert same, f"Fonte instalada diferente da tag oficial: {p}"
        audit.append({"path": "mkdocs/" + p, "official_url": "https://github.com/mkdocs/mkdocs/blob/1.6.1/mkdocs/" + p, "normalized_sha256": hashlib.sha256(clean(installed).encode()).hexdigest(), "installed_matches_official_tag": same})
    save_json(run / "fontes.json", audit)
    pip = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True)
    (ROOT / "experimentos" / "requirements-lock.txt").write_text(pip.stdout.replace("\r\n", "\n"), encoding="utf-8")
    with zipfile.ZipFile(ROOT / "experimentos" / "corpus.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for n in (100, 500):
            base = work / f"corpus-{n}"
            for file in sorted(base.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(work))
    profile_dir = run / "profiling"
    profile_dir.mkdir(exist_ok=False)
    result = []
    for label in ("C", "D"):
        site = work / "sites" / f"profile-{label}"
        if site.exists():
            raise FileExistsError(site)
        profile = profile_dir / f"{label}.prof"
        cmd = [sys.executable, "-m", "cProfile", "-o", str(profile), "-m", "mkdocs", "build", "--clean", "--strict", "-f", str(work / "corpus-500" / f"{label}.yml"), "-d", str(site)]
        env = os.environ.copy(); env.pop("PYTHONPATH", None); env.update(PYTHONHASHSEED="0", PYTHONUTF8="1")
        p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", timeout=300)
        (profile_dir / f"{label}.log").write_text(p.stdout + p.stderr, encoding="utf-8")
        assert p.returncode == 0, p.stderr
        validate_site(site, 500, label == "C")
        stats = pstats.Stats(str(profile))
        functions = []
        for (file, line, name), (pcalls, calls, self_s, cumulative_s, callers) in stats.stats.items():
            functions.append({"file": file, "line": line, "function": name, "primitive_calls": pcalls, "calls": calls, "self_s": self_s, "cumulative_s": cumulative_s})
        functions.sort(key=lambda f: f["cumulative_s"], reverse=True)
        selected = [f for f in functions if any(s in f["file"].replace("\\", "/") for s in ("mkdocs/commands/build.py", "mkdocs/contrib/search/", "mkdocs/structure/pages.py"))]
        result.append({"scenario": label, "pages": 500, "search": label == "C", "instrumented_total_s": stats.total_tt, "top_functions": functions[:35], "selected_functions": selected, "command": cmd, "warning": "Tempos instrumentados de diagnóstico; não comparar diretamente com o benchmark e não somar tempos cumulativos de funções aninhadas"})
        print(f"Profiling {label} concluído", flush=True)
    save_json(profile_dir / "resumo-profiling.json", result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work-dir", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, default=ROOT / "resultados" / "principal")
    args = p.parse_args()
    main(args.work_dir.resolve(), args.run_dir.resolve())
