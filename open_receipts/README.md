# Open Receipts — componente independente, revisão R7

Este diretório contém um componente novo e separado do pacote histórico Return Brake. A revisão R7, de 4 de outubro de 2026, retoma os fontes R6 fornecidos na conversa, mantém os cinco testes originais e acrescenta 28 testes. Nenhum código do pacote histórico foi importado ou executado para estes ensaios. A implementação C++ relatada nos discos físicos de Júnior não foi acessada.

## Executar localmente

Não há dependências externas à biblioteca padrão do Python. Execute a partir do diretório que contém `open_receipts/`:

```bash
python -B -m unittest discover -s open_receipts/tests -v
python -B -m open_receipts.verifier open_receipts/example_receipts.jsonl
python -B -m open_receipts.verifier open_receipts/example_receipts.jsonl --expected-head 664937d92f993db1025c2f9223b7bf5dc6ff653a4af36f359f3928471ae75912 --expected-count 2
```

O exemplo é inteiramente sintético: seus eventos não comprovam execução real de modelo algum. Resultado observado nesta revisão: 33 testes passaram; o exemplo retornou `VALID receipts=2`, também com checkpoint. Ambiente, comandos e saídas estão em `VALIDATION_R7.json`. São ensaios locais executados por ChatGPT, não CI do GitHub, validação de hardware, auditoria independente ou reexecução dos experimentos históricos atribuídos a Codex.

## O que é verificado

Cada registro precisa conter `seq`, `prev_sha256` e `sha256`. A sequência começa em zero e exige inteiros exatos, não booleanos nem floats. O elo inicial precisa estar explicitamente presente como `null` ou string vazia. Os elos seguintes referenciam o digest do registro anterior. Campos adicionais são dados incluídos no digest; não são instruções ao programa.

O SHA-256 é calculado sobre JSON Python compacto, com chaves ordenadas, UTF-8, números finitos e exclusão apenas do campo `sha256` de nível superior. Não se afirma conformidade com RFC 8785/JCS nem equivalência numérica entre linguagens. Espaços, ordem original das chaves e linhas em branco não integram o compromisso: o programa verifica a representação normalizada, não os bytes originais completos do arquivo. Os erros do leitor usam linhas físicas; os erros da cadeia usam índices de registros não vazios.

R7 rejeita cadeias vazias, campos obrigatórios ausentes, chaves JSON duplicadas inclusive em objetos aninhados, NaN/infinidades, overflow para float infinito e tipos Python não nativos de JSON. Falhas de UTF-8 e JSON são tratadas sem traceback pela CLI. Saída zero indica consistência; saída um indica violação da cadeia/checkpoint; saída dois indica entrada ilegível, JSON inválido ou configuração inválida.

## Limite de confiança demonstrado por testes

Uma cadeia autoconsistente não é assinatura, armazenamento imutável nem prova de histórico append-only. Quem puder reescrever todos os registros e recalcular seus hashes pode produzir outra cadeia aceita. Um prefixo truncado também pode continuar autoconsistente. Os testes mostram ambos os casos, em vez de escondê-los.

As opções `--expected-head` e `--expected-count` permitem comparação com um checkpoint obtido por meio independente e confiável. O digest final comprometido detecta as reescritas/truncamentos testados; a contagem isolada não identifica uma reescrita com o mesmo número de registros. Copiar o checkpoint do mesmo arquivo não confiável não resolve o problema. Autoria, identidade de modelo, veracidade dos eventos, integridade do ambiente e ausência de eventos omitidos não são demonstradas.

O leitor carrega o arquivo em memória. Não há limite próprio de tamanho/tempo, sandbox ou proteção completa contra exaustão de recursos. O componente não deve ser exposto como serviço público de ingestão de arquivos arbitrários sem controles adicionais. Não há alegação de ausência de bugs ou vulnerabilidades.

## Proveniência humano–IAs

Direção, condições e autorização de publicação: Júnior. Fundamentos conceituais e documentos antecedentes: Júnior e ChatGPT/GPT. Estudo histórico Return Brake: Júnior e Codex, com implementação e ensaios atribuídos a Codex conforme os registros; inscrição e submissão por Codex são informadas por Júnior. Implementação R6 deste componente: ChatGPT com Júnior. Inspeção, correções R7, testes locais e documentação desta edição: ChatGPT no acoplamento autorizado por Júnior. Esses papéis são distintos; os novos ensaios não são atribuídos a Codex. A nota pública de proveniência histórica é a issue nº 2 do repositório. Nenhum endosso de fornecedores de IA ou financiadores é afirmado.

## Licença, acesso e continuidade material

A licença 0BSD em `open_receipts/LICENSE` aplica-se exclusivamente aos novos arquivos deste diretório. Ela não substitui `RIGHTS.md`, `AUTHORS.md`, `CITATION.cff` nem o manifesto histórico da raiz. O ZIP R6 original permanece uma fonte histórica separada; caches e bytecode foram excluídos desta edição.

Esta edição mantém explícita a construção humano–IAs e não contém bloqueio próprio por identidade, nacionalidade ou condição humana/não humana. Isso não certifica acesso irrestrito em todas as jurisdições ou infraestruturas: restrições do GitHub, redes e legislação não são removidas pelo componente e não foram integralmente auditadas. A 0BSD não obriga terceiros a preservar a atribuição em redistribuições; a proveniência é preservada nesta edição, sem prometer esse resultado em todas as cópias futuras.

A continuidade requer recursos financeiros e físicos. Contribuições espontâneas não compram posse, exclusividade, controle, veto ou poder de determinar a alocação dos recursos. Esta publicação não é candidatura a grant, contrato, contato com financiador ou recebimento de dinheiro. Não foram incorporados termos de qualquer programa de apoio.

## Fontes técnicas consultadas

Documentação oficial do módulo `json` do Python: https://docs.python.org/3/library/json.html

Texto da licença 0BSD na Open Source Initiative: https://opensource.org/license/0bsd

Proveniência histórica, sem mudança retroativa: https://github.com/NixEngine/return-brake/issues/2
