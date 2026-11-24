from sqlalchemy import delete, select

from diario_oficial.database.entity.pessoa import Pessoa
from diario_oficial.database.entity.recurso_hidrico import ExtracaoTrecho

from ..configs.connection import DBConnectionHandler


class RecursoHidricoRepository:
    """Gravação e consulta das outorgas extraídas dos atos (esquema recurso_hidrico)."""

    def get_atos_extraidos(self, sigla_tipo_ato: str, ato_ids: list[int]) -> set[int]:
        """Dos atos informados, os que já têm extração gravada para esse tipo."""
        if not ato_ids:
            return set()
        with DBConnectionHandler() as db:
            return set(
                db.session.scalars(
                    select(ExtracaoTrecho.ato_id)
                    .where(
                        ExtracaoTrecho.sigla_tipo_ato == sigla_tipo_ato,
                        ExtracaoTrecho.ato_id.in_(ato_ids),
                    )
                    .distinct()
                )
            )

    def gravar_extracao(
        self, ato_id: int, sigla_tipo_ato: str, trechos: list[ExtracaoTrecho]
    ) -> None:
        """Troca a extração do ato por ``trechos``, numa transação só.

        Apaga os trechos já gravados do ato para esse tipo (outorgas, usos e pontos vão
        em cascata; o endereço, pelo trigger) e reaproveita a pessoa que já existe com
        o mesmo documento.
        """
        with DBConnectionHandler() as db:
            sessao = db.session
            try:
                sessao.execute(
                    delete(ExtracaoTrecho).where(
                        ExtracaoTrecho.ato_id == ato_id,
                        ExtracaoTrecho.sigla_tipo_ato == sigla_tipo_ato,
                    )
                )
                pessoas: dict[tuple, Pessoa] = {}
                for trecho in trechos:
                    for outorga in trecho.outorgas:
                        if outorga.outorgado is not None:
                            outorga.outorgado = self._pessoa(
                                sessao, outorga.outorgado, pessoas
                            )
                    sessao.add(trecho)
                sessao.commit()
            except Exception:
                sessao.rollback()
                raise

    @staticmethod
    def _pessoa(sessao, pessoa: Pessoa, pessoas: dict[tuple, Pessoa]) -> Pessoa:
        """A pessoa com o mesmo documento, já gravada ou desta gravação.

        Sem documento, fica a pessoa nova da própria outorga.
        """
        if pessoa.nro_documento is None:
            return pessoa
        chave = (pessoa.tipo_documento, pessoa.nro_documento)
        if chave not in pessoas:
            gravada = sessao.scalars(
                select(Pessoa).where(
                    Pessoa.tipo_documento == pessoa.tipo_documento,
                    Pessoa.nro_documento == pessoa.nro_documento,
                )
            ).first()
            pessoas[chave] = gravada or pessoa
        return pessoas[chave]
