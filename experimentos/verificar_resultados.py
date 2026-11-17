"""Validação documental dos dados publicados, sem executar builds do MkDocs."""
from __future__ import annotations
import ast
import csv
import hashlib
import json
import marshal
from pathlib import Path
import re
import statistics
from urllib.parse import unquote
import zipfile
from pypdf import PdfReader
from benchmark import ROOT, summarize

RUN=ROOT/'resultados'/'principal'
AI='Durante o desenvolvimento do projeto, utilizamos o Codex como ferramenta de apoio à programação, automação de experimentos, organização de informações e elaboração dos materiais técnicos. Os procedimentos, resultados e conclusões foram acompanhados, analisados e integralmente revisados por Alexandre Adler e André Macarini, responsáveis pelo trabalho acadêmico.'


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str): yield value
    elif isinstance(value,(tuple,list)):
        for x in value: yield from strings(x)
    elif isinstance(value,dict):
        for k,v in value.items():
            yield from strings(k); yield from strings(v)


def scan_text(text, label, findings):
    patterns={
        'caminho_pessoal_windows':r'[A-Za-z]:[/\\]+Users[/\\]+[^\s/\\<>]+',
        'caminho_pessoal_unix':r'/(?:Users|home)/[^\s/<>]+',
        'registro_academico':r'\bRA\s*[:=\-]?\s*\d{5,}',
        'token_github':r'\bgh[pousr]_[A-Za-z0-9]{20,}',
        'token_github_fine_grained':r'\bgithub_pat_[A-Za-z0-9_]{25,}',
        'chave_aws':r'\bAKIA[A-Z0-9]{16}\b',
        'chave_privada':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'credencial_url':r'https?://[^\s/@:]+:[^\s/@]+@',
        'credencial_atribuida':r'''(?i)\b(?:password|passwd|senha|api[_-]?key|access[_-]?token|secret[_-]?key)\s*[=:]\s*["'][^"'\r\n]{8,}["']''',
    }
    for name,pattern in patterns.items():
        if re.search(pattern,text): findings.append({'file':label,'pattern':name})


def privacy_scan():
    findings=[]
    for p in ROOT.rglob('*'):
        if not p.is_file() or any(part in p.relative_to(ROOT).parts for part in ('.git','.venv','__pycache__')): continue
        label=p.relative_to(ROOT).as_posix()
        if p.suffix=='.pdf':
            reader=PdfReader(p)
            scan_text('\n'.join(pg.extract_text() or '' for pg in reader.pages)+str(reader.metadata),label,findings)
        elif p.suffix in ('.docx','.zip'):
            with zipfile.ZipFile(p) as z:
                scan_text('\n'.join(z.namelist())+z.comment.decode('utf-8',errors='replace'),label,findings)
                for name in z.namelist():
                    scan_text(z.read(name).decode('utf-8',errors='replace'),label+'!'+name,findings)
        elif p.suffix=='.prof':
            with p.open('rb') as f: obj=marshal.load(f)
            scan_text('\n'.join(strings(obj)),label,findings)
        elif p.suffix!='.png':
            scan_text(p.read_text(encoding='utf-8',errors='replace'),label,findings)
        else:
            from PIL import Image
            with Image.open(p) as image: scan_text(str(image.info),label,findings)
    assert not findings, f'Revisar ocorrências antes da publicação: {findings}'
    return findings


def main():
    rows=json.loads((RUN/'execucoes.json').read_text(encoding='utf-8'))
    measured=[r for r in rows if r['phase']=='measured']
    warmups=[r for r in rows if r['phase']=='warmup']
    assert len(measured)==40 and len(warmups)==4
    for case in 'ABCD': assert sum(r['scenario']==case for r in measured)==10
    for n in range(1,11): assert {r['scenario'] for r in measured if r['round']==n}==set('ABCD')
    summary=json.loads((RUN/'resumo.json').read_text(encoding='utf-8'))
    assert summarize(rows)==summary
    with (RUN/'tempos-brutos.csv').open(encoding='utf-8',newline='') as f: raw=list(csv.DictReader(f))
    with (RUN/'medicoes.csv').open(encoding='utf-8',newline='') as f: selected=list(csv.DictReader(f))
    assert len(raw)==44 and selected==[r for r in raw if r['phase']=='measured'] and len(selected)==40
    for s in summary['scenarios']:
        times=[float(r['elapsed_seconds']) for r in selected if r['scenario']==s['scenario']]
        assert statistics.mean(times)==s['mean_s']
        assert statistics.median(times)==s['median_s']
        assert statistics.stdev(times)==s['stdev_s']
    corpus=json.loads((RUN/'corpus.json').read_text(encoding='utf-8'))
    with zipfile.ZipFile(ROOT/'experimentos/corpus.zip') as z:
        assert z.testzip() is None
        for n in (100,500):
            assert len([name for name in z.namelist() if name.startswith(f'corpus-{n}/docs/') and name.endswith('.md')])==n
            for r in corpus[str(n)]['files']:
                assert hashlib.sha256(z.read(f"corpus-{n}/docs/{r['file']}")).hexdigest()==r['sha256']
    sources=json.loads((RUN/'fontes.json').read_text(encoding='utf-8'))
    for r in sources:
        text=(ROOT/'experimentos/fontes-oficiais'/r['path']).read_text(encoding='utf-8').replace('\r\n','\n').rstrip()+'\n'
        assert hashlib.sha256(text.encode()).hexdigest()==r['normalized_sha256']
    for script in (ROOT/'experimentos').glob('*.py'): ast.parse(script.read_text(encoding='utf-8'))
    env=json.loads((RUN/'ambiente.json').read_text(encoding='utf-8'))
    assert sha(ROOT/'experimentos/benchmark.py')==env['benchmark_script_sha256']
    readme=(ROOT/'README.md').read_text(encoding='utf-8')
    report=PdfReader(ROOT/'relatorio/relatorio-final.pdf')
    report_text='\n'.join(p.extract_text() or '' for p in report.pages)
    assert len(report.pages)==7
    normalize=lambda text:re.sub(r'\s+',' ',text).strip()
    assert AI in readme and AI in normalize(report_text)
    for value in ('2,138','1,871','9,895','8,052','14,3%','22,9%','Alexandre Adler','André Macarini'):
        assert value in readme and value in report_text
    links_checked=0
    for md in ROOT.rglob('*.md'):
        if '.git' in md.parts or '__pycache__' in md.parts: continue
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',md.read_text(encoding='utf-8')):
            if re.match(r'^[a-z]+:',target) or target.startswith('#'): continue
            target=unquote(target.split('#',1)[0].strip('<>'))
            assert (md.parent/target).resolve().exists(), (md.relative_to(ROOT).as_posix(),target)
            links_checked+=1
    assert len(list((RUN/'logs').glob('measured-*.log')))==40
    assert len(list((RUN/'logs').glob('warmup-*.log')))==4
    manifest=ROOT/'MANIFESTO-SHA256.txt'
    if manifest.exists():
        for line in manifest.read_text(encoding='utf-8').splitlines():
            digest,name=line.split('  ',1)
            assert sha(ROOT/name)==digest,name
    privacy_scan()
    print(json.dumps({'status':'aprovado','medicoes':40,'aquecimentos':4,'corpus_conferido':600,'medias_medianas_desvios_percentuais':'conferidos','links_internos_conferidos':links_checked,'relatorio_pdf_paginas':len(report.pages),'autores':'Alexandre Adler e André Macarini','declaracao_ia':'redação aprovada pelos autores presente no README e relatório','privacidade':'nenhuma ocorrência nos padrões verificados','novos_benchmarks_executados':0},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
