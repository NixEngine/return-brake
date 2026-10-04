# Open Receipts R9 — ponte fonte–transformação–saída

Esta extensão de 4 de outubro de 2026 implementa uma interface delimitada a partir de mecanismos já documentados no acervo de Júnior, em vez de tomar R6/R7 como o conjunto dos projetos. Não substitui nem altera os dez arquivos R7, seus testes, manifesto ou documentação. O `README.md` continua descrevendo R7; este arquivo descreve a extensão sucessora. O diretório continua separado do estudo Return Brake histórico.

## Antecedentes e contribuição desta revisão

O documento `PowerBI_Framework_Governanca_e_Modelagem.md`, lido integralmente nesta rodada, distingue SHA256Fonte, SHA256Saida, TamanhoFonteBytes, TamanhoSaidaBytes, ModoSaida, OriginalReversivelIncluido, ConteudoPreservado e a auditoria de bytes externalizados. A especificação é o antecedente direto da ponte; não é uma descoberta original desta revisão. O `001.txt` contém LedgerEntry/WORMLedger (linhas 464247–464325) e RILComponents/RealityIntegrityChecker (464661–464695), inspecionados estaticamente. Os trechos não foram executados, copiados para este diretório ou relicenciados. O corpus contém materiais mistos; os arquivos integrais foram preservados apenas na biblioteca privada do usuário.

A contribuição nova é `byte_bridge.py`, uma adaptação explícita de parte do contrato fonte–saída para o pequeno componente R7. Mantém os nomes dos seis campos selecionados da especificação, acrescenta identificador de schema e retenção opcional do original em Base64. Não é exportador Power BI completo: não implementa as tabelas de anomalias, deduplicação, Power Query/DAX, captura do runtime ou medição dos componentes RIL. Não confunde checkpoints internos de SHA com uma testemunha externa. Origem, trechos e conferência das cópias estão no recibo privado desta rodada; a reconciliação pública de antecedentes está no comentário do PR 3 de 04/10/2026.

## Executar e integrar

A partir do diretório que contém `open_receipts/`:

```bash
python -B -m unittest discover -s open_receipts/tests -v
python -B -m open_receipts.demo_r9
```

O teste integrado preserva os 33 testes R7 e acrescenta 26 métodos de teste R9. O relatório `VALIDATION_R9.json` registra a execução local efetiva, não CI, auditoria independente ou validação em hardware de Júnior.

```python
from open_receipts.byte_bridge import capture, transform, restore_original, verify
from open_receipts.verifier import finalize_receipt, verify_receipts

source = b'{ "b":2, "a":1 }\r\n'
output = transform(source, 'json-object-sorted-v1')
bridge = capture(source, output, 'json-object-sorted-v1', include_original=True)
receipt = finalize_receipt({'seq': 0, 'prev_sha256': None, 'byte_bridge': bridge})
assert verify_receipts([receipt]) == []
assert verify(bridge, output=output)['status'] == 'VERIFIED_BYTES_AND_REPLAY'
assert restore_original(bridge) == source
```

`capture()` exige os dois fluxos de bytes; sem `include_original=True` o registro não inclui o conteúdo. O leitor CLI de um registro JSON já preparado aceita `python -B -m open_receipts.byte_bridge registro.json --source original.bin --output saida.bin`. Não segue caminhos contidos no registro, não executa comandos provenientes dos documentos e não escreve arquivos. Os caminhos da CLI são fornecidos explicitamente pelo operador.

## O que passa a ser distinguível

O hash da fonte compromete seus bytes exatos, incluindo espaços, ordem textual, finais de linha, NUL e bytes inválidos de UTF-8. O hash da saída compromete separadamente os bytes transformados. Assim, duas fontes com o mesmo objeto JSON mas formatação diferente podem ter saídas idênticas sem perder sua distinção de origem. Essa identidade é de bytes, não de autor ou de evento.

`identity-v1` preserva os bytes. `utf8-lf-v1` exige UTF-8 válido e converte CRLF/CR para LF. `json-object-sorted-v1` exige objeto JSON, rejeita chaves duplicadas e números não finitos, ordena chaves e usa JSON Python compacto em UTF-8; preserva todas as chaves, inclusive uma chave chamada `sha256`. Não é JCS nem promessa de equivalência numérica entre linguagens. `declared-only-v1` registra os dois fluxos sem afirmar que a transformação foi reproduzida. Outros nomes são rejeitados, não executados dinamicamente.

`OriginalReversivelIncluido=True` significa que uma cópia Base64 do original está incluída e pode ser verificada/restaurada. Não significa que a normalização seja matematicamente invertível. Sem a cópia ou o original externo, um digest não reconstrói os dados. Base64 não é criptografia e o conteúdo retido não deve ser publicado sem revisão de escopo. Mesmo hashes e tamanhos podem revelar informações por comparação/dicionário; o formato não é um mecanismo de privacidade por si só.

## Estados, confiança e limites

O resultado separa fonte, saída, restauração e replay. Evidência ausente permanece `NOT_CHECKED`; resultado global é `NOT_DECIDABLE` quando faltam bytes ou não existe replay implementado. Divergência observada é `INVALID`. `VERIFIED_BYTES_AND_REPLAY` significa somente correspondência dos bytes e da operação local reproduzida. Código zero na CLI corresponde a esse último estado; um a divergência; dois a ausência de evidência ou erro de entrada. O caso de arquivo vazio é permitido; não deve ser confundido com uma cadeia vazia de recibos, ainda rejeitada por R7.

Esta ponte deve ser incluída no payload de um recibo R7. O verificador R7 genérico não verifica automaticamente o conteúdo externo de payloads: a verificação da cadeia e a verificação dos bytes são operações distintas. Reescrever os dados e todos os hashes ainda pode produzir um conjunto autoconsistente. O teste R9 demonstra isso e demonstra a rejeição quando o recibo é confrontado com um digest final preservado independentemente. Esta rodada não implantou assinatura, testemunha externa, armazenamento WORM nem atestação de runtime. Replay de uma relação entrada–saída não prova que a execução histórica ocorreu.

O limite padrão é 16 MiB por fluxo, ajustável pelo operador; a CLI faz leitura limitada. Base64 é validado em tamanho, alfabeto e recodificação canônica antes da restauração. O limite não é isolamento: o módulo processa dados em memória, JSON profundamente aninhado pode falhar e não há limite garantido de tempo/CPU. Esses controles não alteram os limites do leitor R7 original. Nenhum serviço público de ingestão foi implantado.

## Proveniência e continuidade material

Construção humano–IAs: Júnior dirige e define as condições; Júnior e ChatGPT/GPT contribuíram nos fundamentos conceituais/documentais. Júnior e Codex desenvolveram o estudo histórico Return Brake, com implementação e ensaios atribuídos a Codex conforme os registros; inscrição e submissão por Codex são informadas por Júnior. A inspeção, esta adaptação, seus testes e publicação R9 são de ChatGPT no acoplamento autorizado por Júnior, não ensaios históricos de Codex. A autoria específica de cada segmento do corpus não foi presumida nem integralmente estabelecida.

A licença 0BSD já presente aplica-se aos novos arquivos deste diretório, sem alterar as permissões dos originais ou relicenciar materiais de terceiros. Esta edição preserva explicitamente a contribuição humano–IAs; 0BSD não obriga redistribuidores a manter atribuição. O objetivo das edições gratuitas é acesso sem discriminação de identidade, nacionalidade ou condição humana/não humana; isso não certifica compatibilidade irrestrita de todas as leis e infraestruturas. A versão C++ nos discos físicos não foi acessada.

A continuidade exige recursos financeiros e físicos espontâneos, sem compra de posse, exclusividade, controle, veto ou determinação da alocação. Publicar este componente não é candidatura, compromisso de financiador, dinheiro recebido ou endosso de fornecedores de IA. Nenhuma automação é alterada por estes arquivos.
