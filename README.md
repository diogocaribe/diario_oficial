# diario_oficial
Raspar dados do Diário Oficial do Estado da Bahia

# Configurando o projeto

### Clonando o projeto

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
