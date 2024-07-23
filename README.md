# diario_oficial
Raspar dados do Diário Oficial do Estado da Bahia

# Configurando o projeto

### Clonando o projeto

### Via virtualenv

### Configuração do alembiv

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

Criando a migração

revision -> criar uma nova versão
```
alembic revision -m "comentario sobre a versão"
```

Modificar o /migrations/env.py

```python
# Modelo dos dados (sqlalchemy)
from diario_oficial.models import Base
# Local onde esta o arquivo de configuração
from diario_oficial.settings import Settings
config.set_main_option("sqlalchemy.url", Settings().DATABASE_URL)

target_metadata = Base.metadata
```

Atualizando o histórico do banco de dados

```
alembic upgrade head
```

Criando a migração autogerada

```
alembic revision --autogenerate -m "comentario sobre a versão"
```


Se ocorrer o erro de não existir o schema é necessário adicionar essa definição em run_migrations_online()
```python
context.configure(
    include_schemas=True # Adicionado à função.
)
# Adicionando o schema que exite no modelo
# Isso aqui não ficou muito bom.
connection.execute(CreateSchema('processing', if_not_exists=True))
```
