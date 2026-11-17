"""Regenera o relatório existente sem executar benchmarks."""
from __future__ import annotations
import json
from pathlib import Path
import re
from datetime import datetime
ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'resultados' / 'principal'
S = json.loads((RUN / 'resumo.json').read_text(encoding='utf-8'))
E = json.loads((RUN / 'ambiente.json').read_text(encoding='utf-8'))
CORPUS = json.loads((RUN / 'corpus.json').read_text(encoding='utf-8'))
ROWS = json.loads((RUN / 'execucoes.json').read_text(encoding='utf-8'))
P = json.loads((RUN / 'profiling' / 'resumo-profiling.json').read_text(encoding='utf-8'))
BY = {s['scenario']: s for s in S['scenarios']}
F = {e['pages']: e for e in S['effects']}
REFERENCES = [('1', 'MkDocs 1.6.1 Código do comando de build', 'https://github.com/mkdocs/mkdocs/blob/1.6.1/mkdocs/commands/build.py'), ('2', 'MkDocs 1.6.1 Conversão das páginas Markdown', 'https://github.com/mkdocs/mkdocs/blob/1.6.1/mkdocs/structure/pages.py'), ('3', 'MkDocs 1.6.1 Plugin de busca', 'https://github.com/mkdocs/mkdocs/blob/1.6.1/mkdocs/contrib/search/__init__.py'), ('4', 'MkDocs 1.6.1 Geração dos dados de busca', 'https://github.com/mkdocs/mkdocs/blob/1.6.1/mkdocs/contrib/search/search_index.py'), ('5', 'MkDocs Guia de configuração de plugins', 'https://www.mkdocs.org/user-guide/configuration/#plugins'), ('6', 'Python Contador de tempo de alta resolução', 'https://docs.python.org/3.12/library/time.html#time.perf_counter'), ('7', 'Python cProfile e limites de profiling', 'https://docs.python.org/3.12/library/profile.html')]

def num(x, d=3):
    return f'{x:.{d}f}'.replace('.', ',')

def pdata(label, function):
    return next((x for p in P if p['scenario'] == label for x in p['selected_functions'] if x['function'] == function))

def report_blocks():
    blocks = []

    def add(kind, text=None, **kw):
        blocks.append({'kind': kind, 'text': text, **kw})
    add('title', 'Impacto da busca no desempenho do MkDocs')
    add('subtitle', 'Relatório final de estudo experimental')
    add('p', 'Alexandre Adler\nAndré Macarini\nUNICAMP - Engenharia de Computação\nMC851A - Projetos de Software\nProfessora Islene Calciolari Garcia\n17 de novembro de 2026')
    add('h', 'Resumo')
    add('p', f"Este estudo avaliou o custo de habilitar a busca no build do MkDocs 1.6.1 em documentação sintética de 100 e 500 páginas. Foram executados dez builds por cenário, além de aquecimentos, com medição externa do tempo total. A busca elevou a média em {num(F[100]['mean_difference_s'])} s ({num(F[100]['relative_overhead_pct'], 1)}%) para 100 páginas e {num(F[500]['mean_difference_s'])} s ({num(F[500]['relative_overhead_pct'], 1)}%) para 500 páginas. A dispersão foi maior nos cenários de 500 páginas. A análise do código e um profiling separado associam o custo adicional à extração de texto e à preparação dos dados de busca. Os resultados descrevem este ambiente e corpus, sem demonstrar um limite geral de escalabilidade.")
    add('h', '1 Introdução')
    add('p', 'Sites de documentação apoiam o desenvolvimento e a utilização de projetos de software livre. Sua geração é repetida durante a edição e a integração do projeto. Recursos úteis, como busca, acrescentam trabalho ao processo de construção. Medir esse custo permite discutir uma escolha de configuração com evidências, sem implementar alterações no gerador.')
    add('h', '2 Contextualização do MkDocs')
    add('p', 'O MkDocs é um gerador de sites estáticos escrito em Python. Ele combina arquivos Markdown, configuração YAML e templates de tema para produzir HTML e arquivos auxiliares. O mecanismo de plugins permite executar ações em eventos do build. A distribuição inclui o plugin search, habilitado por padrão; sua desativação exige uma lista de plugins vazia [1-5].')
    add('h', '3 Objetivos')
    add('p', 'O objetivo foi comparar o tempo de mkdocs build com e sem busca, em 100 e 500 páginas. As questões específicas foram quantificar o custo absoluto e relativo da busca, observar a mudança entre os dois tamanhos e investigar componentes que ajudam a explicar o comportamento. Identificar oportunidades de otimização foi um objetivo de análise, sem implementar ou prometer uma melhoria no código.')
    add('break')
    add('h', '4 Metodologia experimental')
    add('p', 'O desenho cruzou dois tamanhos de corpus com dois estados da busca. A e B compartilharam exatamente os mesmos 100 arquivos, enquanto C e D compartilharam os mesmos 500. A contagem inclui index.md. O gerador usou semente 851, seis seções por página, parágrafos, listas, blocos de código e links válidos para o início. As primeiras 100 páginas do corpus maior são idênticas às do menor. Os arquivos e respectivos hashes SHA-256 estão registrados no manifesto e no arquivo corpus.zip.')
    add('table', headers=['Cenário', 'Páginas', 'Busca'], rows=[[c, str(BY[c]['pages']), 'Ativada' if BY[c]['search'] else 'Desativada'] for c in 'ABCD'], widths=[2.0, 2.0, 2.6])
    bytes100 = f"{CORPUS['100']['bytes']:,}".replace(',', '.')
    bytes500 = f"{CORPUS['500']['bytes']:,}".replace(',', '.')
    add('p', f'Os corpora somaram {bytes100} e {bytes500} bytes de Markdown, respectivamente. Todos os casos utilizaram o tema mkdocs e as extensões toc, tables e fenced_code. Nos casos com busca, foram fixados lang: [pt], indexing: full e prebuild_index: false. Nos casos sem busca, foi usado plugins: []. Nenhum plugin de terceiros participou do build.')
    add('p', 'Cada execução iniciou um novo processo Python. O contador perf_counter_ns foi iniciado imediatamente antes de Popen e encerrado após communicate, cobrindo inicialização, leitura da configuração, build e término [6]. Foram utilizados --clean e --strict, uma saída exclusiva inicialmente ausente e timeout de 180 segundos. A geração do corpus, a validação de HTML e a análise ficaram fora do intervalo medido. PYTHONHASHSEED foi fixado em 0 e PYTHONPATH removido.')
    add('p', 'Após um aquecimento por cenário, foram realizadas dez rodadas. Cada rodada executou A, B, C e D em ordem pseudoaleatória reproduzível. Os 40 builds medidos foram sequenciais; nenhuma observação foi excluída. O cache do sistema operacional não foi esvaziado, portanto o estudo representa builds completos com arquivos previamente acessados, e não uma condição de disco frio.')
    add('h', '5 Ambiente de execução')
    add('table', headers=['Item', 'Configuração registrada'], rows=[['Sistema', E['platform']], ['Processador', E['hardware']['cpu'].strip()], ['CPU e memória', f"{E['hardware']['physical_cores']} núcleos físicos, {E['logical_cpus']} lógicos e {num(E['hardware']['ram_bytes'] / 1024 ** 3, 2)} GiB de RAM"], ['Python e MkDocs', 'CPython 3.12.14 de 64 bits e MkDocs 1.6.1'], ['Dependências principais', f"Markdown {E['packages']['Markdown']}, Jinja2 {E['packages']['Jinja2']} e Click {E['packages']['click']}"], ['Energia e armazenamento', f"Plano Balanced, bateria em {E['hardware']['battery']['EstimatedChargeRemaining']}% no início; trabalho em disco local fora do OneDrive"]], widths=[1.7, 4.9])
    add('p', 'A execução ocorreu em 17/11/2026, com horários em UTC-03:00 registrados por build. O pacote foi instalado em ambiente virtual exclusivo. As dependências completas foram congeladas em requirements-lock.txt. O notebook manteve o plano de energia existente; carga de fundo e variação térmica não foram controladas integralmente.')
    add('break')
    add('h', '6 Resultados dos quatro cenários')
    add('p', 'A Tabela 1 apresenta estatísticas dos dez tempos externos de cada cenário. O desvio-padrão é amostral, calculado com denominador n - 1. Os aquecimentos e os tempos instrumentados de profiling não integram essas estatísticas.')
    add('table', headers=['Caso', 'Média s', 'Mediana s', 'DP s', 'Mínimo s', 'Máximo s'], rows=[[c, num(BY[c]['mean_s']), num(BY[c]['median_s']), num(BY[c]['stdev_s']), num(BY[c]['min_s']), num(BY[c]['max_s'])] for c in 'ABCD'], widths=[0.65, 1.19, 1.19, 1.19, 1.19, 1.19])
    add('caption', 'Tabela 1 Tempos externos em segundos com dez execuções medidas por cenário')
    add('p', 'O impacto relativo foi calculado por 100 × (média com busca / média sem busca - 1). A diferença absoluta corresponde à média com busca menos a média sem busca.')
    add('table', headers=['Páginas', 'Acréscimo médio s', 'Impacto relativo', 'Pares com acréscimo'], rows=[[str(n), num(F[n]['mean_difference_s']), num(F[n]['relative_overhead_pct'], 1) + '%', f"{F[n]['positive_pairs']} de 10"] for n in (100, 500)], widths=[1.0, 1.8, 1.8, 2.0])
    add('h', '7 Gráficos comparativos')
    add('image', filename='tempos-comparativos.png', width=6.6)
    add('caption', 'Figura 1 Média do tempo total por tamanho e estado da busca com hastes de um desvio-padrão amostral')
    add('p', f"Em 100 páginas, a média passou de {num(BY['B']['mean_s'])} s para {num(BY['A']['mean_s'])} s. Em 500, passou de {num(BY['D']['mean_s'])} s para {num(BY['C']['mean_s'])} s. O custo médio absoluto da busca aumentou entre os tamanhos estudados. O percentual também aumentou nesta amostra, mas essa diferença deve ser interpretada junto da maior dispersão nos casos de 500 páginas.")
    add('break')
    add('h', '8 Discussão técnica')
    add('image', filename='diferencas-por-rodada.png', width=6.6)
    add('caption', 'Figura 2 Diferenças entre busca ativada e desativada dentro de cada rodada')
    add('p', f"O emparelhamento por rodada reduz a distância temporal entre as condições comparadas, sem eliminar interferências. As diferenças foram positivas em {F[100]['positive_pairs']} das dez rodadas de 100 páginas e em {F[500]['positive_pairs']} das dez rodadas de 500. Na rodada 4 do caso maior, a diferença foi {num(F[500]['paired_differences_s'][3])} s. Esse valor foi preservado, pois uma execução isolada mais rápida com busca é compatível com ruído do ambiente.")
    add('p', f"O coeficiente de variação do cenário C foi {num(BY['C']['cv_pct'], 1)}%, contra {num(BY['A']['cv_pct'], 1)}% em A. No caso de 500 páginas com busca, a média de {num(BY['C']['mean_s'])} s ficou acima da mediana de {num(BY['C']['median_s'])} s. Os primeiros três tempos de C foram maiores que os restantes. Esse padrão temporal impede tratar toda a dispersão como efeito do plugin e recomenda cautela com diferenças percentuais pequenas.")
    add('p', f"Passar de 100 para 500 páginas multiplicou as médias por {num(S['growth_on'], 2)} com busca e {num(S['growth_off'], 2)} sem busca. Dois tamanhos não permitem estabelecer uma lei de crescimento ou afirmar complexidade assintótica. O número de páginas e o volume de texto cresceram juntos, enquanto a navegação também passou a conter mais itens.")
    add('p', 'O build carrega a configuração, descobre arquivos e monta a navegação. Em seguida, _populate_page lê o Markdown e chama Page.render. Essa função instancia Python-Markdown, converte o texto em HTML e extrai informações como títulos e âncoras. Depois, _build_page renderiza cada página com Jinja2 e grava a saída [1-2]. O cronômetro interno do MkDocs cobre uma parte menor desse fluxo que a medição externa utilizada aqui.')
    add('p', 'Com search ativado, on_page_context chama add_entry_from_context para cada página. O plugin analisa o HTML, coleta texto e relaciona seções ao sumário. Ao final, on_post_build serializa a coleção em search/search_index.json e grava os recursos necessários [3-4]. Como prebuild_index foi false, o build gerou dados para busca no navegador, sem executar a pré-construção opcional do índice Lunr em Node.js.')
    add('p', f"A validação encontrou {BY['A']['search_entries']} entradas e {num(BY['A']['search_index_bytes'] / 1024 ** 2, 2)} MiB de JSON em A; em C, {BY['C']['search_entries']} entradas e {num(BY['C']['search_index_bytes'] / 1024 ** 2, 2)} MiB. Há oito entradas por página: a entrada geral, o título principal e seis seções. Com busca desativada, o arquivo de índice esteve ausente em todos os builds.")
    add('break')
    add('h', 'Diagnóstico por profiling')
    add('p', 'Duas execuções adicionais, uma de C e outra de D, foram instrumentadas com cProfile. Elas servem para localizar funções com custo relevante, sem substituir as 40 medições principais. Os tempos cumulativos incluem funções chamadas internamente e não devem ser somados entre linhas aninhadas [7].')
    data = []
    for label, name in (('C', '_populate_page'), ('D', '_populate_page'), ('C', '_build_page'), ('D', '_build_page'), ('C', 'add_entry_from_context'), ('C', 'generate_search_index')):
        f = pdata(label, name)
        data.append([label, name, str(f['calls']), num(f['cumulative_s'])])
    add('table', headers=['Caso', 'Função', 'Chamadas', 'Tempo cumulativo s'], rows=data, widths=[0.6, 3.0, 1.0, 2.0])
    add('caption', 'Tabela 2 Funções selecionadas das execuções instrumentadas de 500 páginas')
    search = pdata('C', 'add_entry_from_context')
    index = pdata('C', 'generate_search_index')
    add('p', f"Na execução instrumentada de C, add_entry_from_context acumulou {num(search['cumulative_s'])} s em {search['calls']} chamadas, enquanto generate_search_index acumulou {num(index['cumulative_s'])} s. A comparação indica onde o plugin realiza trabalho, mas não demonstra que esses tempos sejam iguais ao acréscimo médio do benchmark. O profiler altera o custo da execução, especialmente em trechos com muitas chamadas Python.")
    add('p', 'A geração de navegação e a renderização dos templates continuam presentes nos dois estados. Assim, desativar a busca não elimina a conversão Markdown nem a criação de links e HTML. A diferença A - B ou C - D estima o custo de habilitar o recurso completo, incluindo dados de busca, recursos estáticos e caminhos condicionais do tema. Ela não isola apenas json.dumps ou apenas a execução do plugin.')
    add('p', 'A auditoria comparou quatro arquivos do pacote instalado com cópias da tag oficial 1.6.1, normalizando somente terminações de linha e espaços finais do arquivo. Todos coincidiram. As URLs e hashes estão em resultados/principal/fontes.json; os arquivos consultados foram preservados em experimentos/fontes-oficiais. Nenhum trecho do código-fonte do MkDocs foi alterado.')
    add('h', 'Reprodutibilidade e validação')
    add('p', 'Cada build foi verificado quanto ao retorno zero, presença de todas as páginas HTML esperadas e estado correto do índice. A análise recalculou média, mediana e desvio-padrão a partir do CSV e conferiu os resultados contra o JSON. A auditoria também verificou dez blocos completos, hashes do script e dos dados e ausência de exclusões de observações. Logs individuais, ordem dos cenários e comandos completos permitem rastrear cada resultado.')
    add('break')
    add('h', '9 Dificuldades e limitações')
    add('p', 'O comando Python inicialmente disponível apontava para o ambiente de outro projeto. Foi criado um ambiente exclusivo com CPython 3.12.14. Os arquivos temporários dos builds ficaram fora do OneDrive, embora os registros e materiais finais permaneçam na pasta do projeto. Isso reduz uma fonte de interferência de disco sem produzir isolamento completo do sistema.')
    add('p', 'A tentativa de medir memória no piloto retornou o contador do lançador do ambiente virtual no Windows. Essa métrica foi rejeitada antes da série principal e os valores não foram utilizados. O consumo de memória permaneceu fora das conclusões por ser um requisito opcional. Uma futura medição precisaria acompanhar o processo Python real e possíveis descendentes.')
    add('p', 'Os testes usaram uma máquina, um sistema operacional, um tema e um corpus sintético. O notebook estava em plano Balanced e com bateria. Não houve controle integral de temperatura, frequência de CPU, antivírus ou tarefas de fundo. Os caches do sistema permaneceram ativos. Essas condições, junto da tendência temporal observada em C, limitam a precisão e a generalização dos percentuais. Nenhuma conclusão sobre latência da busca no navegador foi testada.')
    add('h', '10 Progresso e objetivos alcançados')
    add('table', headers=['Objetivo planejado', 'Resultado alcançado'], rows=[['Quatro cenários com 100 e 500 páginas', 'A, B, C e D executados e validados'], ['Pelo menos cinco repetições', 'Dez por cenário, mais um aquecimento por cenário'], ['Medição externa e estatísticas', '40 tempos, média, mediana e DP amostral'], ['Comparação e interpretação', 'Gráficos e análise por rodada com todos os dados'], ['Fundamentação no código', 'Tag 1.6.1 auditada e dois perfis de diagnóstico'], ['Memória opcional', 'Método preliminar rejeitado e métrica não divulgada'], ['Materiais das entregas', 'Relatório, textos dos formulários, slides e roteiro analisados e integralmente revisados pelos integrantes']], widths=[2.8, 3.8])
    add('p', 'O trabalho avançou da definição do recorte para a preparação do ambiente, piloto, coleta, validação, análise do código e elaboração dos materiais. Os objetivos obrigatórios do estudo foram atendidos. Alexandre Adler e André Macarini participaram do desenvolvimento, acompanharam a execução automatizada, analisaram os resultados e realizaram a revisão integral dos materiais. A gravação do vídeo e a submissão das entregas seguem o cronograma da disciplina.')
    add('h', 'Registro do uso de inteligência artificial')
    add('p', 'Durante o desenvolvimento do projeto, utilizamos o Codex como ferramenta de apoio à programação, automação de experimentos, organização de informações e elaboração dos materiais técnicos. Os procedimentos, resultados e conclusões foram acompanhados, analisados e integralmente revisados por Alexandre Adler e André Macarini, responsáveis pelo trabalho acadêmico.')
    add('break')
    add('h', '11 Possíveis melhorias')
    add('p', 'Como continuidade experimental, seria útil repetir a mesma matriz com alimentação externa e maior controle de carga do sistema. Isso poderia reduzir a dispersão sem alterar a pergunta estudada. Uma medição correta de memória exigiria acompanhar a árvore de processos do Python no Windows.')
    add('p', 'No código, oportunidades para investigação incluem reduzir o processamento repetido de HTML na extração para busca e avaliar o custo de relacionar cada seção ao sumário. Diminuir o volume indexado com indexing: sections ou titles também é uma hipótese de configuração, com perda de cobertura de pesquisa. Essas opções não foram testadas neste projeto. Qualquer otimização precisaria preservar o índice e ser validada funcionalmente antes de uma afirmação de melhoria [3-4].')
    add('h', '12 Conclusão')
    add('p', f"Neste corpus e ambiente, habilitar a busca acrescentou {num(F[100]['mean_difference_s'])} s em média em 100 páginas e {num(F[500]['mean_difference_s'])} s em 500 páginas. Os acréscimos relativos foram {num(F[100]['relative_overhead_pct'], 1)}% e {num(F[500]['relative_overhead_pct'], 1)}%. O custo absoluto cresceu com o tamanho estudado. O código e o profiling oferecem uma explicação plausível pela extração de conteúdo e preparação dos dados de busca, sem atribuir toda a diferença a uma função específica. A maior variabilidade em 500 páginas exige cautela na comparação dos percentuais. O estudo produziu um protocolo reproduzível e não requereu alterações no MkDocs.")
    add('h', '13 Referências')
    for number, title, url in REFERENCES:
        add('ref', f'[{number}] {title}. Disponível em {url}. Acesso em 17 nov. 2026.')
    add('p', 'Dados primários do estudo: resultados/principal/tempos-brutos.csv, execucoes.json, ambiente.json e resumo.json. Código reprodutível: experimentos/benchmark.py, analisar.py e diagnostico.py.')
    return blocks

def write_docx(blocks, target, title='Relatório final'):
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.2677)
    sec.page_height = Inches(11.6929)
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.83)
    sec.right_margin = Inches(0.83)
    for name in ('Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Caption'):
        style = doc.styles[name]
        style.font.name = 'Arial'
        style.font.color.rgb = RGBColor(0, 0, 0)
    normal = doc.styles['Normal']
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1
    doc.styles['Title'].font.size = Pt(25)
    doc.styles['Title'].font.bold = True
    doc.styles['Subtitle'].font.size = Pt(12)
    doc.styles['Heading 1'].font.size = Pt(13)
    doc.styles['Heading 1'].font.bold = True
    doc.styles['Heading 1'].paragraph_format.space_before = Pt(10)
    doc.styles['Heading 1'].paragraph_format.space_after = Pt(6)
    doc.styles['Caption'].font.size = Pt(9)
    doc.styles['Caption'].font.italic = True
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run('MC851A   ')
    run.font.name = 'Arial'
    run.font.size = Pt(8)
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.core_properties.title = 'Impacto da busca no desempenho do MkDocs'
    doc.core_properties.author = 'Alexandre Adler e André Macarini'
    doc.core_properties.subject = 'MC851A - estudo experimental com MkDocs 1.6.1'
    for block in blocks:
        kind = block['kind']
        if kind == 'break':
            doc.add_page_break()
        elif kind == 'table':
            table = doc.add_table(rows=1, cols=len(block['headers']))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            for i, h in enumerate(block['headers']):
                table.rows[0].cells[i].text = h
            for row in block['rows']:
                for cell, value in zip(table.add_row().cells, row):
                    cell.text = str(value)
            for j, row in enumerate(table.rows):
                trPr = row._tr.get_or_add_trPr()
                no_split = OxmlElement('w:cantSplit')
                trPr.append(no_split)
                if j == 0:
                    repeat = OxmlElement('w:tblHeader')
                    trPr.append(repeat)
                for i, cell in enumerate(row.cells):
                    cell.width = Inches(block['widths'][i])
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    tcPr = cell._tc.get_or_add_tcPr()
                    sh = OxmlElement('w:shd')
                    sh.set(qn('w:fill'), '213A52' if j == 0 else 'F2F5F7' if j % 2 else 'FFFFFF')
                    tcPr.append(sh)
                    borders = OxmlElement('w:tcBorders')
                    for side in ('top', 'left', 'bottom', 'right'):
                        edge = OxmlElement('w:' + side)
                        edge.set(qn('w:val'), 'single')
                        edge.set(qn('w:sz'), '4')
                        edge.set(qn('w:color'), 'D9D9D9')
                        borders.append(edge)
                    tcPr.append(borders)
                    margins = OxmlElement('w:tcMar')
                    for side, v in (('top', 75), ('bottom', 75), ('left', 90), ('right', 90)):
                        mar = OxmlElement('w:' + side)
                        mar.set(qn('w:w'), str(v))
                        mar.set(qn('w:type'), 'dxa')
                        margins.append(mar)
                    tcPr.append(margins)
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(0)
                        p.paragraph_format.line_spacing = 1.04
                        if len(block['headers']) >= 4:
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        for run in p.runs:
                            run.font.size = Pt(9.3)
                            run.font.bold = j == 0
                            run.font.color.rgb = RGBColor.from_string('FFFFFF' if j == 0 else '000000')
            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_after = Pt(2)
            spacer.paragraph_format.space_before = Pt(0)
        elif kind == 'image':
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.add_run().add_picture(str(ROOT / 'graficos' / block['filename']), width=Inches(block['width']))
            p.paragraph_format.keep_with_next = True
        else:
            style = {'title': 'Title', 'subtitle': 'Subtitle', 'h': 'Heading 1', 'caption': 'Caption'}.get(kind, 'Normal')
            p = doc.add_paragraph(block['text'], style)
            if block.get('keep'):
                p.paragraph_format.keep_together = True
            if block.get('keep_with_next'):
                p.paragraph_format.keep_with_next = True
            if kind == 'ref':
                p.paragraph_format.space_after = Pt(7)
                for run in p.runs:
                    run.font.size = Pt(9)
    doc.save(target)

def write_markdown(blocks, target):
    text = []
    for b in blocks:
        k = b['kind']
        if k in ('title', 'h'):
            text.append(('# ' if k == 'title' else '## ') + b['text'])
        elif k == 'table':
            text.append('| ' + ' | '.join(b['headers']) + ' |\n| ' + ' | '.join(('---' for _ in b['headers'])) + ' |\n' + '\n'.join(('| ' + ' | '.join(map(str, row)) + ' |' for row in b['rows'])))
        elif k == 'image':
            text.append(f"![Gráfico](../graficos/{b['filename']})")
        elif k == 'break':
            text.append('<!-- Quebra de página no DOCX -->')
        else:
            text.append(b['text'])
    target.write_text('\n\n'.join(text) + '\n', encoding='utf-8')

if __name__ == "__main__":
    blocks = report_blocks()
    write_markdown(blocks, ROOT / "relatorio" / "relatorio-final.md")
    write_docx(blocks, ROOT / "relatorio" / "relatorio-final.docx")
