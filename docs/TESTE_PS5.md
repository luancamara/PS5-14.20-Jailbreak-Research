# Teste em um PS5 real a partir de outra máquina

Este fork prepara uma sessão de pesquisa reproduzível. O diagnóstico inicial
confirma acesso ao host e coleta de resultados. Os probes seguintes exercitam
falhas de memória e podem encerrar o navegador. Não há jailbreak completo de
14.20 validado neste fork.

## 1. Preparar a máquina

Use um PS5 próprio e uma máquina na mesma rede local, sem isolamento entre
clientes. O caminho principal usa macOS ou Linux, Python 3.10+, Git e OpenSSL.
Nenhuma dependência Python precisa ser instalada. Node 24, Make e um compilador
C são usados pelos testes locais, não pelo host em execução.

```sh
git clone https://github.com/luancamara/PS5-14.20-Jailbreak-Research.git
cd PS5-14.20-Jailbreak-Research
git rev-parse HEAD
python3 --version
openssl version
```

Guarde a revisão mostrada pelo Git. Anote a versão completa do software em
**Configurações → Sistema → Software do sistema → Informações do console**.
O firmware extraído do User-Agent é um dado separado; se houver divergência,
registre ambos. O fork não substitui a versão por 10.40.

## 2. Conferir primeiro no computador

Na raiz do clone, execute:

```sh
python3 tools/host.py --no-dns --no-https --http-port 8080 --no-watch --no-heartbeat
```

Abra `http://127.0.0.1:8080/`. A tela deve mostrar **PS5 baseline**, informações
do navegador e **Beacon HTTP 204**. O terminal e `host-beacons.log` devem conter
`/beacon/BASELINE` com o mesmo `run_id` mostrado na tela.

Esse resultado no computador confirma apenas a infraestrutura local. Encerre
com `Ctrl+C` antes de iniciar a sessão do console.

Se quiser executar a suíte de regressão:

```sh
make test
```

Ela cobre host HTTP, beacons GET/POST, erro de gravação, caminhos do Guia do
usuário, firmware, empacotamento, loader/sender simulados, FTP e autorização das
rotas nativas com serviços simulados. `make test-native` exige Linux e verifica
os helpers nativos com serviços PS5 simulados. Nenhum deles prova exploração
no console. O workflow `checks.yml` executa essas verificações em clones limpos.

## 3. Iniciar DNS e HTTPS para o PS5

Descubra o IPv4 da interface da máquina conectada à mesma rede do console.
Substitua `IP_DA_MAQUINA` pelo endereço real, não pelo IP do PS5 ou de uma VPN.

```sh
RUN_DIR=".local/ps5-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN_DIR"
git rev-parse HEAD > "$RUN_DIR/revision.txt"
sudo "$(command -v python3)" -u tools/host.py --ip IP_DA_MAQUINA --verbose \
  --no-watch --no-heartbeat --beacon-log "$RUN_DIR/beacons.jsonl" \
  2>&1 | tee "$RUN_DIR/host-stdout.log"
```

São usadas **UDP 53** (DNS) e **TCP 443** (HTTPS). Permita essas portas no
firewall da máquina para a rede local. Portas ocupadas ou sem permissão aparecem
no terminal; resolva isso antes de prosseguir. O comando usa privilégios elevados
para abrir as portas padrão. Não é necessário encaminhar portas no roteador.

O servidor responde pelo domínio `manuals.playstation.net` e responde NXDOMAIN
para os demais nomes. Isso não é um firewall e não impede tráfego por IP ou
outros resolvedores. O teste de conexão à Internet/PSN pode falhar nessa rede
mesmo quando o host de pesquisa está acessível.

## 4. Abrir o diagnóstico no console

1. Em **Configurações → Rede → Configurações → Configurar conexão à Internet**,
   abra as opções avançadas da conexão ativa.
2. Selecione DNS manual e informe o IP da máquina de teste. Use o mesmo host nos
   campos de DNS que o console exigir; um resolvedor público como alternativa
   pode contornar o redirecionamento desta sessão.
3. Abra **Configurações → Guia do usuário, saúde e segurança e outras
   informações → Guia do usuário**.
4. Confirme a página **PS5 baseline** e **Beacon HTTP 204**.
5. No host, confira os eventos DNS, handshake TLS, GET da página e
   `/beacon/BASELINE`. Confira também o arquivo de beacons da sessão.

O host usa um certificado autoassinado de teste. A aceitação pelo webview do seu
console ainda exige validação real. Se houver erro de certificado ou handshake,
registre o erro e pare nesta etapa: isso não é resultado do exploit. O host não
instala um certificado confiável no PS5.

As instruções oficiais da Sony explicam a
[configuração de rede](https://www.playstation.com/pt-br/support/connectivity/internet-connect-playstation/)
e o [acesso ao Guia do usuário](https://www.playstation.com/pt-br/support/hardware/ps5-console-users-guide/).
Os nomes dos menus podem variar com o idioma e a versão do sistema.

## 5. Executar um probe por tentativa

Os links da página inicial abrem diretamente os probes. Não existe
redirecionamento automático para uma exploração.

| Etapa | Página | Evidência a guardar |
|---|---|---|
| Acesso e coleta | `/index.html` | BASELINE, `run_id`, User-Agent, HTTP 204 e entrada gravada no disco |
| Reclaim/alias | `/probes/canvas-uaf/v573-reclaim-diagnostic.html` | Sequência BOOT/PRE-UAF/POST-UAF, READ, RECLAIM, WRITE, ALIAS e término, quando presentes |
| APIs pelo alias | `/probes/canvas-uaf/v630.html` | Todas as linhas V630, valores retornados, exceções e última etapa observada |

Comece pelo V573 com seus parâmetros padrão. Os probes foram preservados: este
fork não recalibra sprays, tamanhos ou offsets. Não troque parâmetros no meio
de uma comparação. Registre qualquer alteração junto da URL completa.

Quando uma tentativa terminar ou o navegador encerrar, guarde o log e abra uma
nova sessão antes da próxima. Não há repetição automática. Se for necessário
reiniciar o console para recuperar o navegador, anote a reinicialização.

Um marcador isolado, `WRITE ok` ou um travamento não confirmam uma primitiva.
Analise conjuntamente a correspondência entre contextos, a leitura do marcador
e a alteração vista pelo outro contexto. Uma confirmação de pesquisa também
requer repetições e controle sem o trigger; esse controle não está implementado
nos probes históricos deste fork. Relate primeiro o resultado observado de
cada tentativa, sem transformar ausência de beacon em prova de corrupção.

O loader legado em `/loader.html` usa a lista de firmwares 7.00–13.60 e rejeita
14.20. Ter uma tabela não demonstra que um firmware seja explorável. Os probes
Canvas acima funcionam como páginas independentes e não usam esse filtro.
O instalador ELF pressupõe um console já explorado e não faz parte deste
procedimento de teste via navegador.

## 6. Guardar e compartilhar resultados

Preencha [TEST_RESULT_TEMPLATE.md](TEST_RESULT_TEMPLATE.md) para cada sessão.
Guarde a revisão do fork, versão real do console, User-Agent, URL/parâmetros,
horário, resultado visual e logs completos. Fotografe a tela se o navegador
encerrar antes de registrar o resultado final.

Os arquivos locais ficam em `.local/`, ignorado pelo Git. Logs contêm IPs,
User-Agent e dados enviados pelos probes; revise e remova dados privados antes
de compartilhar. O host recusa acesso HTTP a arquivos ocultos, logs, chaves e
links simbólicos que escapem da raiz servida.

Ao terminar, encerre o host com `Ctrl+C` e restaure o DNS automático no PS5.

## Copiar apenas um arquivo para outra máquina

Em uma máquina com o clone, Python e OpenSSL:

```sh
python3 tools/build_host.py
```

Copie `webkit-remote-loader-host.py` para uma pasta gravável na outra máquina.
O arquivo contém o diagnóstico, loader, probes, assets, binários já fornecidos
pelo upstream e um certificado de teste. Não precisa de clone, Node ou OpenSSL
na máquina de destino para iniciar o HTTPS com o certificado embutido.

```sh
# macOS/Linux: troque IP_DA_MAQUINA pelo IPv4 da máquina de destino
sudo python3 webkit-remote-loader-host.py --ip IP_DA_MAQUINA --verbose
```

No Windows, use Python 3.10+ e `py -3 webkit-remote-loader-host.py --ip
IP_DA_MAQUINA --verbose` no PowerShell, liberando as portas no firewall e
resolvendo conflitos com serviços de DNS existentes. Esse caminho ainda não
foi validado no Windows. As etapas de configuração no PS5 são as mesmas.
Para extrair os arquivos do pacote, use `python3 webkit-remote-loader-host.py
--extract remote-loader`.

## Diagnóstico de falhas

| Sintoma | Conferência |
|---|---|
| Nenhuma consulta DNS no host | DNS configurado, IP da interface, UDP 53, isolamento da rede |
| DNS recebido, sem HTTPS | TCP 443, firewall, URL/domínio solicitado pelo Guia do usuário |
| Handshake TLS falha | Erro completo do terminal, certificado e comportamento do webview; exploração ainda não começou |
| HTTP 404 | Confirme a revisão e use `tools/host.py` do fork; não copie só o script fonte para outra pasta |
| Beacon HTTP 500 | O host não conseguiu registrar o evento; confira permissões e diretório do log |
| Página carrega, beacon falha | Requisição `/beacon/BASELINE`, erro HTTP e log do host |
| Probes não aparecem no pacote | Gere novamente o arquivo com `tools/build_host.py` deste fork |
| Navegador encerra num probe | Registre última etapa e tentativa; o encerramento sozinho não comprova exploração |

## Limites conhecidos

Os testes automatizados verificam infraestrutura e comportamento simulado.
A aceitação TLS, os resultados V573/V630, a calibração do heap e qualquer
execução de código ou acesso ao kernel continuam dependentes de PS5 real.
O V674/APNG foi relatado pelo upstream, mas seu probe e resultados brutos não
estão no checkout; a derrota de ASLR permanece não verificada neste fork.
