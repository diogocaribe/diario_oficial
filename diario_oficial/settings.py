import re

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )

    DATABASE: str
    USER_DB: str
    PASSWORD_DB: str
    HOST: str
    PORT: int

    DATABASE_URL: str

    # Selenium address
    SELENIUM_ADDRESS: str
    SELENIUM_PORT: int

    # LLM local (Ollama) da extração de autos de infração
    OLLAMA_BASE_URL: str = 'http://localhost:11434'
    OLLAMA_MODELO: str = 'qwen3:14b'

    @model_validator(mode='after')
    def expandir_variaveis_da_url(self):
        """Troca os ${VAR} do DATABASE_URL pelos campos de mesmo nome.

        O .env lido pelo pydantic-settings já vem expandido, mas o terminal do VS Code
        (python.terminal.useEnvFile) injeta o .env no ambiente sem expandir, e a variável
        de ambiente tem prioridade sobre o arquivo.
        """
        self.DATABASE_URL = re.sub(
            r'\$\{(\w+)\}',
            lambda achado: str(getattr(self, achado.group(1), achado.group(0))),
            self.DATABASE_URL,
        )
        return self
