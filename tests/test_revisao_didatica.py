import json
import os
import re
import unittest
from contextlib import ExitStack, nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from flask import url_for
from markupsafe import escape

from safeclick import create_app
from safeclick.catalogo_validacao import validar, validar_lote_quizzes
from safeclick.sessoes import Usuario
from scripts import aplicar_revisao_didatica as revisao


PASTA = Path(__file__).resolve().parents[1] / 'dados/revisao_didatica'


def ler(nome):
    return json.loads((PASTA / nome).read_text(encoding='utf-8'))


def materializar(quiz):
    questoes, alternativas, gabarito = [], [], []
    for numero, pergunta in enumerate(quiz['questoes'], 1):
        opcoes = [a | {'id': numero * 10 + i, 'ordem': i, 'questao_id': numero}
                  for i, a in enumerate(pergunta['alternativas'], 1)]
        questoes.append(pergunta | {'id': numero, 'ordem': numero, 'alternativas': opcoes})
        alternativas.extend(opcoes)
        correta = next(a for a in opcoes if a['correta'])
        gabarito.append({'questao_id': numero, 'alternativa_id': correta['id'],
                         'texto_correto': correta['texto'], 'explicacao': pergunta['explicacao']})
    return questoes, alternativas, gabarito


class BancoDidaticoTeste(unittest.TestCase):
    def test_lotes_sao_importaveis_e_todas_as_alternativas_tem_feedback(self):
        titulos = set()
        for arquivo, formato in (('01_quizzes.json', 'perguntas'), ('02_oficinas.json', 'oficina')):
            bruto = (PASTA / arquivo).read_text(encoding='utf-8')
            self.assertLess(len(bruto.encode('utf-8')), 512 * 1024)
            for quiz in validar_lote_quizzes(bruto):
                with self.subTest(quiz=quiz['titulo']):
                    self.assertEqual(quiz['formato'], formato)
                    self.assertNotIn(quiz['titulo'].casefold(), titulos)
                    titulos.add(quiz['titulo'].casefold())
                    enunciados = [q['enunciado'] for q in quiz['questoes']]
                    self.assertEqual(len(enunciados), len(set(enunciados)))
                    for pergunta in quiz['questoes']:
                        self.assertTrue(pergunta['explicacao'])
                        self.assertTrue(all(a['explicacao'] for a in pergunta['alternativas']))
                        self.assertEqual(sum(a['correta'] for a in pergunta['alternativas']), 1)
                        textos = [a['texto'].casefold() for a in pergunta['alternativas']]
                        self.assertEqual(len(textos), len(set(textos)))

    def test_oficinas_tem_cartao_excedente_e_gabaritos_em_posicoes_variadas(self):
        for quiz in ler('02_oficinas.json'):
            with self.subTest(quiz=quiz['titulo']):
                banco = {a['texto'] for a in quiz['questoes'][0]['alternativas']}
                corretos = {a['texto'] for q in quiz['questoes'] for a in q['alternativas'] if a['correta']}
                self.assertGreater(len(banco), len(quiz['questoes']))
                self.assertEqual(len(corretos), len(quiz['questoes']))
                self.assertTrue(banco - corretos)
                posicoes = {next(i for i, a in enumerate(q['alternativas']) if a['correta'])
                            for q in quiz['questoes']}
                self.assertGreater(len(posicoes), 1)

    def test_matriz_cobre_todos_os_materiais_com_secao_e_objetivo(self):
        matriz = ler('matriz.json')
        fontes_esperadas = {
            'phishing', 'protecao-de-senhas', 'golpes-por-mensagem', 'falso-conhecido-e-pix',
            'compras-online-seguras', 'verificacao-em-duas-etapas', 'vazamento-de-dados',
            'privacidade-e-dados-pessoais', 'codigos-maliciosos-e-atualizacoes', 'laboratorio',
        }
        self.assertEqual(set(matriz['fontes']), fontes_esperadas)
        cobertura = set()
        referencias = set()
        for atividade in matriz['atividades']:
            quiz = ler(atividade['arquivo'])[atividade['indice']]
            self.assertEqual(atividade['titulo'], quiz['titulo'])
            if quiz['formato'] == 'oficina':
                extra = atividade['cartao_excedente']
                self.assertIn(extra['fonte'], fontes_esperadas)
                self.assertTrue(extra['secao'])
                for pergunta in quiz['questoes']:
                    cartao = next(a for a in pergunta['alternativas'] if a['texto'] == extra['texto'])
                    self.assertFalse(cartao['correta'])
            referencias.add((atividade['arquivo'], atividade['indice']))
            self.assertEqual([q['numero'] for q in atividade['questoes']], list(range(1, len(quiz['questoes']) + 1)))
            for questao in atividade['questoes']:
                self.assertTrue(questao['objetivo'])
                self.assertIn(questao['nivel'], {'compreensao', 'aplicacao'})
                for fonte in questao['fontes']:
                    self.assertIn(fonte['fonte'], fontes_esperadas)
                    self.assertTrue(fonte['secao'])
                    cobertura.add(fonte['fonte'])
        self.assertEqual(cobertura, fontes_esperadas)
        self.assertEqual(len(referencias), sum(len(ler(nome)) for nome in ('01_quizzes.json', '02_oficinas.json')))

    def test_correcao_do_ensino_preserva_slugs_e_limites_do_editor(self):
        for item in ler('conteudos_revisados.json'):
            with self.subTest(slug=item['slug']):
                self.assertEqual(validar('conteudos', item, publicar=True)['corpo'], item['corpo'])
                self.assertNotIn('Apenas um teste', item['corpo'])
                if item['slug'] == 'privacidade-e-dados-pessoais':
                    self.assertIn('Agência Nacional de Proteção de Dados', item['corpo'])
                    self.assertNotIn('Autoridade Nacional de Proteção de Dados', item['corpo'])
        alvos = revisao.carregar_revisao()
        self.assertEqual(len(alvos), 20)
        self.assertEqual(sum(bool(a.get('sha256_anterior')) for a in alvos), 17)


class FluxosMaterialRevisadoTeste(unittest.TestCase):
    def setUp(self):
        ajustes = ExitStack()
        self.addCleanup(ajustes.close)
        ajustes.enter_context(patch.dict(os.environ, {'SECRET_KEY': 'chave-local-dos-testes'}, clear=True))
        ajustes.enter_context(patch('psycopg.connect', side_effect=AssertionError('Banco real proibido')))
        self.app = create_app()
        self.app.config.update(TESTING=True, AVALIACOES_ATIVAS=True)
        usuario = Usuario({'id': 77, 'nome': 'Pessoa de teste', 'email': 'teste@example.test', 'perfil': 'usuario'})
        ajustes.enter_context(patch.object(self.app.login_manager, '_user_callback', return_value=usuario))
        ajustes.enter_context(patch('safeclick.aceite_termos.usuario_aceitou_termos_atuais', return_value=True))
        self.conexao = Mock()
        ajustes.enter_context(patch('safeclick.quizzes.conectar_banco', return_value=nullcontext(self.conexao)))
        self.auditar = ajustes.enter_context(patch('safeclick.quizzes.registrar_evento'))
        self.cliente = self.app.test_client()
        with self.cliente.session_transaction() as sessao:
            sessao['_user_id'] = '77'
            sessao['_fresh'] = True

    def test_todos_os_gabaritos_passam_pelo_formulario_correcao_gravacao_e_resultado(self):
        for dados in ler('01_quizzes.json') + ler('02_oficinas.json'):
            for acertar in (True, False):
                with self.subTest(quiz=dados['titulo'], acertar=acertar):
                    self.auditar.reset_mock()
                    questoes, alternativas, gabarito = materializar(dados)
                    quiz = dados | {'id': 33, 'versao_id': 333, 'proxima_referencia': 34}
                    consultas = lambda: [Mock(fetchone=Mock(return_value=quiz)),
                                        Mock(fetchall=Mock(return_value=questoes)),
                                        Mock(fetchall=Mock(return_value=alternativas))]
                    self.conexao.execute.side_effect = consultas()
                    resposta = self.cliente.get('/quizzes/33')
                    self.assertEqual(resposta.status_code, 200)
                    token = re.search(r'name="token_envio" value="([^"]+)"', resposta.text)[1]
                    if dados['formato'] == 'oficina':
                        self.assertIn('Pode haver cartões que ficam sem uso', resposta.text)
                        self.assertEqual(resposta.text.count('data-oficina-encaixe required'), len(questoes))
                    else:
                        self.assertEqual(resposta.text.count('type="radio"'), len(alternativas))
                    envio = {'token_envio': token}
                    detalhes = []
                    for i, pergunta in enumerate(questoes):
                        if acertar:
                            escolha = next(a for a in pergunta['alternativas'] if a['correta'])
                        elif dados['formato'] == 'oficina':
                            seguinte = gabarito[(i + 1) % len(gabarito)]['texto_correto']
                            escolha = next(a for a in pergunta['alternativas'] if a['texto'] == seguinte)
                        else:
                            escolha = next(a for a in pergunta['alternativas'] if not a['correta'])
                        envio[f'questao_{pergunta["id"]}'] = str(escolha['id'])
                        detalhes.append({'ordem': pergunta['ordem'], 'enunciado': pergunta['enunciado'],
                                         'resposta_escolhida': escolha['texto'], 'resposta_correta': gabarito[i]['texto_correto'],
                                         'explicacao': pergunta['explicacao'], 'acertou': acertar,
                                         'alternativas_comentadas': pergunta['alternativas']})
                    self.conexao.execute.side_effect = [*consultas(), Mock(fetchall=Mock(return_value=gabarito)),
                                                        Mock(fetchone=Mock(return_value={'id': 99, 'catalogo_id': 33})),
                                                        *[Mock() for _ in questoes]]
                    resposta = self.cliente.post('/quizzes/33', data=envio)
                    self.assertEqual(resposta.status_code, 303)
                    gravacoes = self.conexao.execute.call_args_list[-len(questoes)-1:]
                    pontos = len(questoes) if acertar else 0
                    self.assertEqual(gravacoes[0].args[1][2:4], (pontos, len(questoes)))
                    self.auditar.assert_called_once()
                    self.assertEqual(self.auditar.call_args.kwargs['evento'], 'quiz.concluido')
                    resultado = quiz | {'id': 99, 'quiz_id': 333, 'catalogo_id': 33, 'pontuacao': pontos,
                                        'total_questoes': len(questoes), 'pode_repetir': True}
                    self.conexao.execute.side_effect = [Mock(fetchone=Mock(return_value=resultado)),
                                                        Mock(fetchall=Mock(return_value=detalhes))]
                    resposta = self.cliente.get('/quizzes/resultado/99')
                    self.assertEqual(resposta.status_code, 200)
                    self.assertIn(f'{pontos} de {len(questoes)}', resposta.text)
                    for pergunta in questoes:
                        self.assertIn(str(escape(pergunta['explicacao'])), resposta.text)
                        for alternativa in pergunta['alternativas']:
                            self.assertIn(str(escape(alternativa['explicacao'])), resposta.text)

    def test_referencias_de_fontes_usam_os_enderecos_publicos_do_projeto(self):
        with self.app.test_request_context():
            for chave, fonte in ler('matriz.json')['fontes'].items():
                esperado = (url_for('senhas.pagina') if chave == 'laboratorio'
                            else url_for('conteudos.detalhe', slug=chave))
                self.assertEqual(fonte['url'], esperado)


class PublicacaoRevisaoTeste(unittest.TestCase):
    def setUp(self):
        self.alvo = revisao.carregar_revisao()[0]
        self.anterior = {'titulo': 'Versão anterior', 'corpo': 'Texto anterior.'}
        self.alvo['sha256_anterior'] = revisao.resumo(self.anterior)
        self.item = {'id': 2, 'revisao': 5, 'estado': 'publicada', 'rascunho': None}

    def test_identifica_revisao_e_reexecucao_sem_criar_outra_versao(self):
        self.assertEqual(revisao.decidir(self.alvo, self.item, self.anterior), 'revisar')
        self.assertEqual(revisao.decidir(self.alvo, self.item, self.alvo['dados']), 'inalterado')

    def test_impede_sobrescrever_rascunho_ou_versao_alterada_pela_equipe(self):
        alterado = self.alvo['dados'] | {'corpo': 'Alteração da equipe.'}
        for item, publicado in ((self.item | {'rascunho': alterado}, self.anterior),
                                (self.item, alterado), (self.item | {'estado': 'arquivada'}, self.anterior)):
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    revisao.decidir(self.alvo, item, publicado)

    def test_retoma_apenas_rascunho_identico_apos_interrupcao(self):
        self.assertEqual(revisao.decidir(self.alvo, self.item | {'rascunho': self.alvo['dados']}, self.anterior), 'publicar')
        novo = {'dados': revisao.carregar_revisao()[-1]['dados'], 'secao': 'quizzes'}
        item = self.item | {'estado': 'rascunho', 'rascunho': novo['dados']}
        self.assertEqual(revisao.decidir(novo, item, None), 'publicar')
        with self.assertRaises(ValueError):
            revisao.decidir(novo, item | {'rascunho': self.alvo['dados']}, None)

    def test_publicacao_usa_servico_existente_com_revisao_e_autoria(self):
        plano = [self.alvo | {'id': 2, 'revisao': 5, 'acao': 'revisar'}]
        with patch.object(revisao, 'conectar_banco', return_value=nullcontext(Mock())), \
             patch.object(revisao.catalogo, '_exigir_administrador') as autorizar, \
             patch.object(revisao.catalogo, 'obter_item', side_effect=[self.item, self.item | {'rascunho': self.alvo['dados'], 'revisao': 6}]), \
             patch.object(revisao.catalogo, 'salvar_rascunho', return_value=2) as salvar, \
             patch.object(revisao.catalogo, 'alterar_publicacao') as publicar:
            self.assertEqual(revisao.aplicar(plano, 15), 1)
            autorizar.assert_called_once()
            salvar.assert_called_once_with(15, 'conteudos', self.alvo['dados'], item_id=2, revisao=5)
            publicar.assert_called_once_with(15, 'conteudos', 2, 6, 'publicar')

    def test_conta_sem_permissao_nao_grava_nada(self):
        with patch.object(revisao, 'conectar_banco', return_value=nullcontext(Mock())), \
             patch.object(revisao.catalogo, '_exigir_administrador', side_effect=PermissionError), \
             patch.object(revisao.catalogo, 'salvar_rascunho') as salvar, \
             patch.object(revisao.catalogo, 'alterar_publicacao') as publicar:
            with self.assertRaises(PermissionError):
                revisao.aplicar([self.alvo | {'acao': 'revisar'}], 77)
            salvar.assert_not_called()
            publicar.assert_not_called()

    def test_conflito_de_revisao_interrompe_antes_de_alterar(self):
        with patch.object(revisao, 'conectar_banco', return_value=nullcontext(Mock())), \
             patch.object(revisao.catalogo, '_exigir_administrador'), \
             patch.object(revisao.catalogo, 'obter_item', return_value=self.item | {'revisao': 9}), \
             patch.object(revisao.catalogo, 'salvar_rascunho') as salvar:
            with self.assertRaises(revisao.catalogo.EdicaoConflitante):
                revisao.aplicar([self.alvo | {'id': 2, 'revisao': 5, 'acao': 'revisar'}], 15)
            salvar.assert_not_called()
