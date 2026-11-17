"""Verifica os dados brutos e produz gráficos a partir de uma execução real."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark import summarize, save_json, sha


def analyze(run_dir, figures):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    rows = json.loads((run_dir / "execucoes.json").read_text(encoding="utf-8"))
    env = json.loads((run_dir / "ambiente.json").read_text(encoding="utf-8"))
    summary = summarize(rows)
    saved = json.loads((run_dir / "resumo.json").read_text(encoding="utf-8"))
    assert summary == saved, "Resumo não confere com os dados brutos"
    n = env["repetitions"]
    assert n >= 5
    assert len(rows) == 4 * (n + 1)
    assert len([r for r in rows if r["phase"] == "warmup"]) == 4
    for round_ in range(1, n + 1):
        block = [r for r in rows if r["phase"] == "measured" and r["round"] == round_]
        assert {r["scenario"] for r in block} == set("ABCD")
        assert {r["order"] for r in block} == set(range(1, 5))
    for r in rows:
        assert r["exit_code"] == 0 and r["validated_pages"] == r["pages"]
        assert r["elapsed_seconds"] > 0
        assert r["search_entries"] == (r["pages"] * 8 if r["search"] else 0)
        assert r["search_index_bytes"] > 0 if r["search"] else r["search_index_bytes"] == 0
    # Segunda leitura independente pelo CSV, com estatísticas de biblioteca padrão.
    with (run_dir / "tempos-brutos.csv").open(encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    for case in summary["scenarios"]:
        data = [float(r["elapsed_seconds"]) for r in csv_rows if r["phase"] == "measured" and r["scenario"] == case["scenario"]]
        assert statistics.mean(data) == case["mean_s"]
        assert statistics.median(data) == case["median_s"]
        assert statistics.stdev(data) == case["stdev_s"]
    checks = {"status": "aprovado", "measured_builds": 4 * n, "warmups": 4, "failed_builds": 0, "outliers_removed": 0, "rounds_complete": n, "statistics_recomputed_from_csv": True, "html_and_index_checked_every_build": True, "benchmark_script_sha256_matches": sha(Path(__file__).with_name("benchmark.py")) == env["benchmark_script_sha256"], "raw_json_sha256": sha(run_dir / "execucoes.json"), "raw_csv_sha256": sha(run_dir / "tempos-brutos.csv"), "memory": "Não medida; valor do lançador rejeitado no piloto"}
    assert checks["benchmark_script_sha256_matches"]
    save_json(run_dir / "validacao.json", checks)
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 16, "axes.labelsize": 12, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 260})
    colors = {True: "#B52B3B", False: "#213A52"}
    by = {r["scenario"]: r for r in summary["scenarios"]}
    fig, ax = plt.subplots(figsize=(9, 4.7), layout="constrained")
    x = np.array([0, 1]); width = .31
    for labels, offset, name, enabled in ((["B", "D"], -width/2, "Busca desativada", False), (["A", "C"], width/2, "Busca ativada", True)):
        values = [by[c]["mean_s"] for c in labels]
        bars = ax.bar(x + offset, values, width, yerr=[by[c]["stdev_s"] for c in labels], capsize=5, color=colors[enabled], label=name)
        ax.bar_label(bars, labels=[f"{v:.3f}".replace(".", ",") for v in values], padding=9, fontsize=11)
    ax.set_xticks(x, ["100 páginas", "500 páginas"])
    ax.set_ylabel("Tempo total externo (s)")
    ax.set_ylim(0, max(r["mean_s"] + r["stdev_s"] for r in by.values()) * 1.25)
    ax.set_title("Tempo de geração do site", loc="left", pad=14, fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    ax.yaxis.grid(True, color="#E5E7EB"); ax.set_axisbelow(True)
    fig.supxlabel(f"Média de {n} execuções por cenário. Hastes: ±1 desvio-padrão amostral, não intervalo de confiança.", fontsize=9)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(figures / f"tempos-comparativos.{ext}")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.3), layout="constrained", sharey=True)
    for ax, e in zip(axes, summary["effects"]):
        differences = e["paired_differences_s"]
        ax.axhline(0, color="#6B7280", linewidth=1)
        ax.plot(range(1, n + 1), differences, "o-", color=colors[True], linewidth=1.4)
        ax.axhline(e["paired_mean_s"], color=colors[False], linestyle="--", label="Diferença média")
        ax.set_title(f"{e['pages']} páginas", fontweight="bold", loc="left")
        ax.set_xlabel("Rodada"); ax.set_xticks(range(1, n + 1)); ax.yaxis.grid(True, color="#E5E7EB")
    axes[0].set_ylabel("Tempo com busca menos sem busca (s)")
    axes[1].legend(frameon=False)
    fig.supxlabel("Cada ponto compara os dois estados da busca dentro da mesma rodada. Todos os pares foram mantidos.", fontsize=9)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(figures / f"diferencas-por-rodada.{ext}")
    plt.close(fig)
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", type=Path, default=ROOT / "resultados" / "principal")
    p.add_argument("--figures-dir", type=Path, default=ROOT / "graficos")
    args = p.parse_args()
    analyze(args.run_dir, args.figures_dir)
