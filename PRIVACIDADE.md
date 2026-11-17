# Registros públicos e preservação dos resultados

Os dados desta publicação derivam dos experimentos originais de 17 de novembro de 2026. Nenhum novo benchmark foi executado para preparar a publicação. Os arquivos originais permanecem arquivados separadamente e não foram sobrescritos.

Nas cópias públicas dos comandos, logs, metadados e perfis, substituímos somente os prefixos de caminhos locais que identificavam diretórios pessoais. Os marcadores mantêm a estrutura relativa necessária para entender a execução:

| Marcador | Significado |
|---|---|
| `<EXECUCAO_LOCAL>` | Diretório de trabalho e ambiente virtual utilizados na coleta |
| `<PYTHON>` | Instalação do interpretador |
| `<PROJETO>` | Diretório original do projeto acadêmico |
| `<REPOSITORIO_MKDOCS>` | Checkout local do MkDocs |
| `<DIRETORIO_USUARIO>` | Diretório pessoal do sistema |

Os comandos registrados com esses marcadores são evidências da execução, não comandos prontos para copiar. Para executar novamente, utilize as instruções e scripts do README com diretórios novos.

Preservamos os cenários, estados da busca, números de páginas, rodadas, ordens, horários, tempos, retornos, contagens e tamanhos de saída. Os perfis `.prof` preservam os contadores, tempos e relações de chamadas; somente as strings de caminhos foram mascaradas. Os gráficos, resumos numéricos e o corpus são os mesmos da coleta original.

O arquivo [proveniencia-publicacao.json](resultados/proveniencia-publicacao.json) identifica os arquivos transformados e apresenta seus hashes originais e públicos. A diferença entre esses hashes decorre da remoção de caminhos pessoais, e não de alterações nas medições. O arquivo [MANIFESTO-SHA256.txt](MANIFESTO-SHA256.txt) permite conferir os bytes da versão publicada.

O CSV [tempos-brutos.csv](resultados/principal/tempos-brutos.csv) preserva os 40 registros medidos e os quatro aquecimentos. [medicoes.csv](resultados/principal/medicoes.csv) contém somente a seleção dos 40 registros de `phase == measured`, sem mudar os valores.

O relatório público mantém os resultados e recebeu ajustes de identificação, autoria, revisão e declaração de uso de IA. Não incluímos números de registro acadêmico, ambientes virtuais ou arquivos temporários. O código oficial consultado do MkDocs e sua licença foram preservados.

As novas coletas geradas pelos scripts podem conter caminhos locais do computador que as executar. Elas são ignoradas por padrão nas pastas `execucao-*` e `reexecucao-*`; antes de publicar novos registros, repita a revisão de privacidade.
