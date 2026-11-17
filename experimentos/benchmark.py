"""Benchmark reprodutível do plugin search do MkDocs 1.6.1.

Executar com o Python do ambiente isolado. Nenhuma função interna é instrumentada
nas medições principais. Cada observação é um novo processo do comando público.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {"A": (100, True), "B": (100, False), "C": (500, True), "D": (500, False)}
SEED = 851


def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def markdown(i):
    """Conteúdo aninhado: as primeiras 100 páginas também pertencem ao corpus 500."""
    rng = random.Random(SEED + i)
    words = "documentação software configuração desempenho projeto sistema teste página arquivo processo pesquisa conteúdo resultado geração navegação versão exemplo método execução ferramenta".split()
    parts = [f"# Página {i:04d}", "", "Documentação técnica sintética para um experimento controlado.", ""]
    for section in range(1, 7):
        parts += [f"## Seção {section}", ""]
        for _ in range(3):
            parts += [" ".join(rng.choices(words, k=48)).capitalize() + ".", ""]
        parts += ["- Validar a configuração antes da execução.", "- Registrar os resultados para reprodução.", "", "```python", f"pagina = {i}", f"secao = {section}", "print(pagina, secao)", "```", "", "[Voltar ao início](index.md)", ""]
    return "\n".join(parts)


def prepare(work):
    """Gera 100/500 arquivos exatos, com configs distintas sobre o MESMO docs_dir."""
    manifests = {}
    for n in (100, 500):
        docs = work / f"corpus-{n}" / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        expected = ["index.md"] + [f"pagina-{i:04d}.md" for i in range(1, n)]
        existing = {p.name for p in docs.glob("*.md")}
        if existing - set(expected):
            raise RuntimeError(f"Arquivos inesperados no corpus {docs}; use outro diretório de trabalho")
        for i, name in enumerate(expected):
            (docs / name).write_text(markdown(i), encoding="utf-8", newline="\n")
        records = [{"file": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(docs.glob("*.md"))]
        assert len(records) == n
        manifests[str(n)] = {"pages": n, "bytes": sum(p["bytes"] for p in records), "files": records}
    for label, (n, enabled) in SCENARIOS.items():
        base = work / f"corpus-{n}"
        search = "plugins:\n  - search:\n      lang: [pt]\n      prebuild_index: false\n      indexing: full\n" if enabled else "plugins: []\n"
        text = ("site_name: Documentação do experimento\nsite_url: https://example.org/\n"
                "docs_dir: docs\ntheme:\n  name: mkdocs\n"
                "markdown_extensions:\n  - toc\n  - tables\n  - fenced_code\n" + search)
        (base / f"{label}.yml").write_text(text, encoding="utf-8", newline="\n")
    assert manifests["100"]["files"] == manifests["500"]["files"][:100]
    return manifests


def environment():
    info = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "architecture": platform.machine(), "processor": platform.processor(), "logical_cpus": os.cpu_count(), "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}, "timer": vars(time.get_clock_info("perf_counter")), "timezone": "America/Sao_Paulo", "environment_overrides": {"PYTHONHASHSEED": "0", "PYTHONUTF8": "1", "PYTHONPATH": "removido"}}
    if os.name == "nt":
        cmd = "[pscustomobject]@{cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name); physical_cores=(Get-CimInstance Win32_Processor | Measure-Object NumberOfCores -Sum).Sum; ram_bytes=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory; power=(powercfg /getactivescheme); battery=(Get-CimInstance Win32_Battery | Select-Object BatteryStatus,EstimatedChargeRemaining)} | ConvertTo-Json -Depth 4"
        p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
        try:
            info["hardware"] = json.loads(p.stdout)
        except ValueError:
            info["hardware_collection_error"] = p.stdout + p.stderr
    return info


def validate_site(site, n, enabled):
    expected = [site / "index.html"] + [site / f"pagina-{i:04d}" / "index.html" for i in range(1, n)]
    assert all(p.is_file() and p.stat().st_size > 0 for p in expected), "Páginas HTML ausentes ou vazias"
    index = site / "search" / "search_index.json"
    assert index.is_file() == enabled, "Estado do índice de busca incorreto"
    entries, index_bytes = 0, 0
    if enabled:
        data = json.loads(index.read_text(encoding="utf-8"))
        assert "index" not in data, "Pré-construção Lunr deveria estar desabilitada"
        entries = len(data["docs"])
        assert entries == n * 8, f"Esperadas 8 entradas por página, recebido {entries}"
        roots = {r["location"].split("#")[0] for r in data["docs"]}
        assert len(roots) == n
        assert any("configuração" in r["text"] for r in data["docs"])
        index_bytes = index.stat().st_size
    return {"validated_pages": n, "search_entries": entries, "search_index_bytes": index_bytes, "site_bytes": sum(p.stat().st_size for p in site.rglob("*") if p.is_file())}


def execute(work, out, label, round_, order, phase):
    n, enabled = SCENARIOS[label]
    cfg = work / f"corpus-{n}" / f"{label}.yml"
    # Saída exclusiva e inicialmente ausente: mesmo estado inicial em TODAS as execuções.
    site = work / "sites" / f"{phase}-{round_:02d}-{label}"
    if site.exists():
        raise FileExistsError(f"Saída já existe: {site}. Use outro diretório de trabalho.")
    cmd = [sys.executable, "-m", "mkdocs", "build", "--clean", "--strict", "--config-file", str(cfg), "--site-dir", str(site)]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(PYTHONHASHSEED="0", PYTHONUTF8="1")
    start_at = datetime.now(timezone(timedelta(hours=-3))).isoformat()
    begin = time.perf_counter_ns()
    proc = subprocess.Popen(cmd, cwd=work, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = proc.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        raise RuntimeError(f"Timeout no cenário {label}")
    elapsed = (time.perf_counter_ns() - begin) / 1e9
    # O venv do Windows usa um lançador separado. Um pico desse handle não
    # representa o Python real. A métrica opcional não é divulgada.
    peak, memory_error = None, "Memória não medida: o handle do lançador do venv não representa o processo real de build"
    log = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")
    (out / "logs" / f"{phase}-{round_:02d}-{label}.log").write_text(log, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"Falha de build {label}: {log}")
    check = validate_site(site, n, enabled)
    internal = re.search(r"Documentation built in ([0-9.]+) seconds", log)
    return {"phase": phase, "round": round_, "order": order, "scenario": label, "pages": n, "search": enabled, "elapsed_seconds": elapsed, "mkdocs_logged_seconds": float(internal[1]) if internal else None, "peak_working_set_bytes": peak, "memory_error": memory_error, "started_at": start_at, "exit_code": proc.returncode, "command": cmd, **check}


def summarize(rows):
    summary = []
    for label, (n, enabled) in SCENARIOS.items():
        sample = [r for r in rows if r["phase"] == "measured" and r["scenario"] == label]
        times = [r["elapsed_seconds"] for r in sample]
        mem = [r["peak_working_set_bytes"] / 1024**2 for r in sample if r["peak_working_set_bytes"] is not None]
        summary.append({"scenario": label, "pages": n, "search": enabled, "n": len(times), "mean_s": statistics.mean(times), "median_s": statistics.median(times), "stdev_s": statistics.stdev(times), "min_s": min(times), "max_s": max(times), "cv_pct": 100 * statistics.stdev(times) / statistics.mean(times), "mean_peak_mib": statistics.mean(mem) if mem else None, "search_index_bytes": sample[0]["search_index_bytes"], "search_entries": sample[0]["search_entries"], "site_bytes": sample[0]["site_bytes"]})
    by = {r["scenario"]: r for r in summary}
    effects = []
    for on, off in (("A", "B"), ("C", "D")):
        pairs = []
        for round_ in sorted({r["round"] for r in rows if r["phase"] == "measured"}):
            pair = {r["scenario"]: r["elapsed_seconds"] for r in rows if r["phase"] == "measured" and r["round"] == round_}
            pairs.append(pair[on] - pair[off])
        effects.append({"pages": by[on]["pages"], "mean_difference_s": by[on]["mean_s"] - by[off]["mean_s"], "relative_overhead_pct": 100 * (by[on]["mean_s"] / by[off]["mean_s"] - 1), "paired_differences_s": pairs, "paired_mean_s": statistics.mean(pairs), "paired_stdev_s": statistics.stdev(pairs), "positive_pairs": sum(d > 0 for d in pairs)})
    return {"scenarios": summary, "effects": effects, "growth_on": by["C"]["mean_s"] / by["A"]["mean_s"], "growth_off": by["D"]["mean_s"] / by["B"]["mean_s"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if importlib.metadata.version("mkdocs") != "1.6.1":
        parser.error("Este estudo exige mkdocs==1.6.1")
    if args.repetitions < 5:
        parser.error("São necessárias pelo menos cinco repetições")
    work = (args.work_dir or Path(tempfile.mkdtemp(prefix="mc851a-mkdocs-"))).resolve()
    work.mkdir(parents=True, exist_ok=True)
    manifests = prepare(work)
    if args.prepare_only:
        print(f"Cenários preparados em {work}")
        return
    out = (args.output_dir or ROOT / "resultados" / datetime.now().strftime("execucao-%Y%m%d-%H%M%S")).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "logs").mkdir()
    save_json(out / "corpus.json", manifests)
    for label, (n, _) in SCENARIOS.items():
        (out / f"{label}.yml").write_bytes((work / f"corpus-{n}" / f"{label}.yml").read_bytes())
    info = environment()
    info.update({"work_dir": str(work), "repetitions": args.repetitions, "warmups_per_scenario": 1, "seed": SEED, "benchmark_script_sha256": sha(__file__), "protocol": "Um processo novo por build; saída ausente e exclusiva; caches do SO não esvaziados; aquecimento descartado; sem exclusão de outliers; blocos em ordem pseudoaleatória; memória opcional não medida"})
    save_json(out / "ambiente.json", info)
    rows = []
    rng = random.Random(SEED)
    for phase, rounds in (("warmup", [0]), ("measured", range(1, args.repetitions + 1))):
        for round_ in rounds:
            order = list(SCENARIOS)
            rng.shuffle(order)
            for position, label in enumerate(order, 1):
                row = execute(work, out, label, round_, position, phase)
                rows.append(row)
                save_json(out / "execucoes.json", rows)
                print(f"{phase:8s} rodada={round_:02d} cenário={label} {row['elapsed_seconds']:.4f} s memória={row['peak_working_set_bytes']}", flush=True)
    fields = [k for k in rows[0] if k != "command"]
    with (out / "tempos-brutos.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    save_json(out / "resumo.json", summary)
    with (out / "resumo.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary["scenarios"][0].keys())
        writer.writeheader()
        writer.writerows(summary["scenarios"])
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
