from safeclick.auditoria_db import registrar_evento
from safeclick.db import conectar_banco


def salvar_desafio_senha(usuario_id, acertos, total_rodadas, token_partida):
    
    with conectar_banco() as conexao:
        registro = conexao.execute(
            """
            INSERT INTO public.desafios_senha
                (usuario_id, acertos, total_rodadas, token_partida)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (token_partida) DO NOTHING
            RETURNING id
            """,
            (usuario_id, acertos, total_rodadas, token_partida),
        ).fetchone()

        if registro is None:
            return False

        registrar_evento(
            usuario_id=usuario_id,
            evento="desafio_senha.concluido",
            resultado="sucesso",
            recurso_tipo="desafio_senha",
            recurso_id=registro["id"],
            detalhes={"acertos": acertos, "total": total_rodadas},
            conexao=conexao,
        )

        return True