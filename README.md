# diario_oficial
Raspar dados do Diário Oficial do Estado da Bahia

# Configurando o projeto (sem docker)

### Clonando o projeto

## Instalar o poetry

## Contruindo o ambiente virtual do projeto

```
poetry install
```

##### Inicializando o alembic

alembic init <nome da pasta onde o versionamento ficará>

```
alembic init migrations
```

As configurações que faremos é para um único banco

alembic.ini --> configurações gerais do alembic

script_location = migrations -> onde estão os scripts do alembic
prepend_sys_path = . -> diretorio onde encontramos a pasta migrations (na raiz)
sqlalchemy.url = driver://user:pass@localhost/dbname -> endereço do banco de dados

## Criando a migração autogerada para versionamento do banco

```
alembic revision --autogenerate -m "comentario sobre a versão"

alembic upgrade head
```

## Criando o banco para iniciar a coleta de dados
```bash
poetry install # para criar o virtualenv do projeto
source $(poetry env info --path)/bin/activate # ativando o ambiente virtual no servidor debian sem o plugin do poetry
alembic upgrade head
```
