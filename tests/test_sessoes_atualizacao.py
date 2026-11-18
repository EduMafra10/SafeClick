"""Consultas automáticas não contam como interação para o prazo da sessão."""
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from flask import session

from safeclick import create_app
from safeclick.sessoes import carregar_usuario


@pytest.mark.parametrize('rota,cabecalhos,automatica', [
    ('/administracao/visao-geral/dados', {}, True),
    ('/administracao/avaliacoes/pendentes', {}, True),
    ('/administracao/visao-geral/dados?automatico=0', {}, True),
    ('/administracao/visao-geral/dados', {'X-SafeClick-Interacao': '1'}, False),
    ('/administracao/', {}, False),
    ('/conta/', {}, False),
])
def test_origem_da_consulta_controla_renovacao_sem_mudar_autorizacao(monkeypatch, rota, cabecalhos, automatica):
    monkeypatch.setenv('SECRET_KEY', 'chave-isolada-para-os-testes-de-sessao')
    app = create_app()
    conexao = Mock()
    conexao.execute.return_value.fetchone.return_value = {
        'id': 7, 'nome': 'Conta de teste', 'email': 'teste@example.test', 'perfil': 'administrador',
    }
    monkeypatch.setattr('safeclick.sessoes.conectar_banco', lambda: nullcontext(conexao))
    with app.test_request_context(rota, headers=cabecalhos):
        session['sessao_token'] = 'a' * 43
        assert carregar_usuario('7').id == 7
    assert conexao.execute.call_args.args[1][0] is automatica
    assert conexao.execute.call_args.args[1][-1] == 7


def test_atualizacao_manual_nao_reativa_sessao_rejeitada(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'chave-isolada-para-os-testes-de-sessao')
    app = create_app()
    conexao = Mock()
    conexao.execute.return_value.fetchone.return_value = None
    monkeypatch.setattr('safeclick.sessoes.conectar_banco', lambda: nullcontext(conexao))
    with app.test_request_context('/administracao/visao-geral/dados', headers={'X-SafeClick-Interacao': '1'}):
        session['sessao_token'] = 'a' * 43
        assert carregar_usuario('7') is None
