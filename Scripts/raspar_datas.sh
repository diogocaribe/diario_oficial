#!/usr/bin/env bash
# Raspa o DOE-BA para as datas informadas, via container `app` (docker compose).
# Por padrão só imprime o resultado no terminal; com --salvar grava em doe_bruto.
#
# Uso (a partir da raiz do repositório):
#   Scripts/raspar_datas.sh 24-09-2022 17-02-2023 11-10-2023
#   Scripts/raspar_datas.sh -f datas.txt              # uma data DD-MM-YYYY por linha
#   Scripts/raspar_datas.sh -i 05-10-2026             # 30 dias a partir da data
#   Scripts/raspar_datas.sh -i 05-10-2026 -n 7        # 7 dias a partir da data
#   Scripts/raspar_datas.sh -i 05-10-2026 --salvar    # grava (pula datas já coletadas)

set -u

DATAS=()
INICIO=''
DIAS=30
OPCOES=(--no-save-db --forcar)

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f) mapfile -t -O "${#DATAS[@]}" DATAS < <(grep -oE '^[0-9]{2}-[0-9]{2}-[0-9]{4}' "$2"); shift 2 ;;
    -i) INICIO="$2"; shift 2 ;;
    -n) DIAS="$2"; shift 2 ;;
    --salvar) OPCOES=(); shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) DATAS+=("$1"); shift ;;
  esac
done

if [[ -n "$INICIO" ]]; then
  if ! [[ "$DIAS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Número de dias inválido: $DIAS" >&2
    exit 1
  fi
  INICIO_ISO="${INICIO:6:4}-${INICIO:3:2}-${INICIO:0:2}"
  if ! [[ "$INICIO" =~ ^[0-9]{2}-[0-9]{2}-[0-9]{4}$ ]] || ! date -d "$INICIO_ISO" >/dev/null 2>&1; then
    echo "Data inicial inválida: $INICIO (use DD-MM-YYYY)" >&2
    exit 1
  fi
  for ((I = 0; I < DIAS; I++)); do
    DATAS+=("$(date -d "$INICIO_ISO + $I days" +%d-%m-%Y)")
  done
fi

if [[ ${#DATAS[@]} -eq 0 ]]; then
  echo 'Informe ao menos uma data (DD-MM-YYYY). Use -h para ajuda.' >&2
  exit 1
fi

for D in "${DATAS[@]}"; do
  if ! [[ "$D" =~ ^[0-9]{2}-[0-9]{2}-[0-9]{4}$ ]]; then
    echo "Data inválida, ignorada: $D" >&2
    continue
  fi
  echo "Raspando $D..."
  # COLUMNS largo evita que o rich quebre as linhas do dict impresso
  COLUMNS=300 docker compose run --rm -e COLUMNS=300 \
    -e SELENIUM_ADDRESS=http://selenium \
    app raspar-doe-bruto "$D" "${OPCOES[@]}" 2>&1
done
