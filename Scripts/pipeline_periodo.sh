#!/usr/bin/env bash
# Roda o pipeline completo em um período, dia a dia, via container `app` (docker compose):
# raspagem, doe_bruto → publicação, publicação → ato e auditoria. O padrão é de 3 meses.
# Pode ser repetido: datas já coletadas não são raspadas de novo. Termina com código 1
# se alguma etapa falhar; basta rodar outra vez para refazer só o que faltou.
#
# A saída é só a dos comandos da CLI, sem filtros nem mensagens próprias do script (além
# dos erros de uso, antes de qualquer execução).
#
# Uso (de qualquer diretório):
#   Scripts/pipeline_periodo.sh                            # últimos 3 meses, até ontem
#   Scripts/pipeline_periodo.sh -i 01-07-2026              # 3 meses a partir da data
#   Scripts/pipeline_periodo.sh -i 01-07-2026 -m 1         # 1 mês a partir da data
#   Scripts/pipeline_periodo.sh -i 01-07-2026 -f 15-07-2026
#   Scripts/pipeline_periodo.sh -d 01-07-2026              # uma única data (sem -i, -f ou -m)

set -u

DATA=''
INICIO=''
FIM=''
MESES=''

erro() {
  echo "$1" >&2
  exit 1
}

# Converte DD-MM-YYYY em YYYY-MM-DD e rejeita datas inválidas
data_iso() {
  [[ "$1" =~ ^[0-9]{2}-[0-9]{2}-[0-9]{4}$ ]] || erro "Data inválida: $1 (use DD-MM-YYYY)"
  local iso="${1:6:4}-${1:3:2}-${1:0:2}"
  date -d "$iso" >/dev/null 2>&1 || erro "Data inválida: $1 (use DD-MM-YYYY)"
  echo "$iso"
}

# Executa um comando da CLI, sem o progresso do próprio docker compose. Sem terminal (saída
# redirecionada), o rich não sabe a largura e a saída ficaria espremida.
if [[ -t 0 && -t 1 ]]; then
  OPCOES_RUN=()
else
  OPCOES_RUN=(-T -e "COLUMNS=${COLUMNS:-180}")
fi

cli() {
  docker compose --progress quiet run --rm "${OPCOES_RUN[@]}" app "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d) [[ $# -ge 2 ]] || erro 'Falta a data de -d.'; DATA="$2"; shift 2 ;;
    -i) [[ $# -ge 2 ]] || erro 'Falta a data de -i.'; INICIO="$2"; shift 2 ;;
    -f) [[ $# -ge 2 ]] || erro 'Falta a data de -f.'; FIM="$2"; shift 2 ;;
    -m) [[ $# -ge 2 ]] || erro 'Falta o número de -m.'; MESES="$2"; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) erro "Opção desconhecida: $1 (use -h para ajuda)" ;;
  esac
done

if [[ -n "$DATA" ]]; then
  [[ -z "$INICIO$FIM$MESES" ]] || erro 'A opção -d não pode ser usada com -i, -f ou -m.'
  INICIO="$DATA"
  FIM="$DATA"
fi

MESES="${MESES:-3}"
[[ "$MESES" =~ ^[1-9][0-9]*$ ]] || erro "Número de meses inválido: $MESES"

# A edição de hoje pode não ter saído: gravada como inexistente, nunca seria refeita
ONTEM=$(date -d 'yesterday' +%F)

if [[ -n "$FIM" ]]; then
  FIM_ISO=$(data_iso "$FIM") || exit 1
fi
if [[ -n "$INICIO" ]]; then
  INICIO_ISO=$(data_iso "$INICIO") || exit 1
  [[ -n "$FIM" ]] || FIM_ISO=$(date -d "$INICIO_ISO + $MESES months - 1 day" +%F)
else
  [[ -n "$FIM" ]] || FIM_ISO="$ONTEM"
  INICIO_ISO=$(date -d "$FIM_ISO - $MESES months + 1 day" +%F)
fi
[[ "$FIM_ISO" > "$ONTEM" ]] && FIM_ISO="$ONTEM"
[[ "$INICIO_ISO" > "$FIM_ISO" ]] && erro "Período vazio: $INICIO_ISO a $FIM_ISO (o limite é ontem)."

DIAS=$(( ($(date -d "$FIM_ISO" +%s) - $(date -d "$INICIO_ISO" +%s)) / 86400 + 1 ))

# O docker compose procura o docker-compose.yaml a partir do diretório atual
cd "$(dirname "$0")/.." || exit 1

FALHOU=false

# As etapas rodam em sequência para cada data. Se uma falhar, as seguintes não rodam nessa
# data, e o laço passa para a próxima.
for ((I = 0; I < DIAS; I++)); do
  D=$(date -d "$INICIO_ISO + $I days" +%d-%m-%Y)

  # 1. Raspagem. A sessão do Selenium às vezes cai no meio: tenta uma segunda vez
  if ! cli raspar-doe-bruto "$D" && ! cli raspar-doe-bruto "$D"; then
    FALHOU=true
    continue
  fi

  # 2. doe_bruto → publicação
  if ! cli transformar-doe-bruto-publicacao "$D"; then
    FALHOU=true
    continue
  fi

  # 3. Publicação → ato: não recebe data, processa todas as pendentes
  if ! cli transformar-publicacao-ato; then
    FALHOU=true
    continue
  fi

  # 4. Auditoria: grava publicacao.auditoria e imprime, para cada link do dia, os atos e se
  # foi aprovada ou reprovada, com os achados
  cli auditar-publicacao-ato "$D" || FALHOU=true
done

$FALHOU && exit 1
exit 0
