import hashlib
import json
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from psycopg import Error

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from safeclick import create_app
from safeclick import catalogo_admin_db as catalogo
from safeclick.catalogo_validacao import validar, validar_lote_quizzes
from safeclick.db import conectar_banco

PASTA = RAIZ / 'dados/revisao_didatica'


def resumo(dados):
    texto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


def carregar_revisao():
    def ler(nome):
        return json.loads((PASTA / nome).read_text(encoding='utf-8'))

    matriz = ler('matriz.json')
    alvos = []
    originais = {item['slug']: item['sha256_anterior'] for item in matriz['conteudos']}
    for item in ler('conteudos_revisados.json'):
        alvos.append({'secao': 'conteudos', 'slug': item['slug'],
                      'dados': validar('conteudos', item, publicar=True),
                      'sha256_anterior': originais[item['slug']]})
    lotes = {nome: validar_lote_quizzes((PASTA / nome).read_text(encoding='utf-8'))
             for nome in ('01_quizzes.json', '02_oficinas.json')}
    for item in matriz['atividades']:
        dados = lotes[item['arquivo']][item['indice']]
        if dados['titulo'] != item['titulo']:
            raise ValueError('O título do lote não corresponde à matriz de revisão.')
        alvos.append({'secao': 'quizzes', 'dados': dados,
                      'id_anterior': item['catalogo_id_anterior'],
                      'sha256_anterior': item.get('sha256_anterior')})
    return alvos


def decidir(alvo, item, publicado):
    dados = alvo['dados']
    if publicado is None and not alvo.get('sha256_anterior') and item['estado'] == 'rascunho':
        if item['rascunho'] == dados:
            return 'publicar'
        raise ValueError('Já existe um novo rascunho diferente. Revise pela gestão.')
    if item['estado'] != 'publicada':
        raise ValueError(f'O item “{dados["titulo"]}” deixou de estar publicado. Revise pela gestão.')
    rascunho = item['rascunho']
    if rascunho and validar(alvo['secao'], rascunho, publicar=True) != dados:
        raise ValueError(f'Há outro rascunho em “{dados["titulo"]}”. Revise pela gestão.')
    if publicado == dados:
        if rascunho:
            raise ValueError(f'Há um rascunho pendente em “{dados["titulo"]}”. Revise pela gestão.')
        return 'inalterado'
    if resumo(publicado) != alvo.get('sha256_anterior'):
        raise ValueError(f'O material “{dados["titulo"]}” mudou após a análise. Revise pela gestão.')
    return 'publicar' if rascunho else 'revisar'


def planejar(alvos):
    plano = []
    with conectar_banco() as conexao:
        for alvo in alvos:
            if alvo['secao'] == 'conteudos':
                ids = conexao.execute(
                    "SELECT id FROM public.conteudos WHERE secao = 'conteudos' AND slug = %s",
                    (alvo['slug'],),
                ).fetchall()
            elif alvo.get('id_anterior'):
                ids = [{'id': alvo['id_anterior']}]
            else:
                ids = conexao.execute(
                    """SELECT c.id FROM public.catalogo_quizzes c
                       LEFT JOIN public.quizzes q ON q.id = c.versao_publicada_id
                       WHERE lower(q.titulo) = lower(%s)
                          OR lower(c.rascunho->>'titulo') = lower(%s)""",
                    (alvo['dados']['titulo'], alvo['dados']['titulo']),
                ).fetchall()
            if len(ids) > 1:
                raise ValueError('Há títulos duplicados. Resolva pela gestão antes de aplicar a revisão.')
            if not ids:
                if alvo['secao'] != 'quizzes' or alvo.get('id_anterior'):
                    raise ValueError('Um conteúdo analisado não foi localizado neste banco.')
                plano.append(alvo | {'acao': 'criar', 'id': None, 'revisao': None})
                continue
            item = catalogo._buscar(conexao, alvo['secao'], ids[0]['id'])
            publicado = (validar(alvo['secao'], catalogo._dados_publicados(conexao, alvo['secao'], item), publicar=True)
                         if item['versao'] else None)
            acao = decidir(alvo, item, publicado)
            plano.append(alvo | {'acao': acao, 'id': item['id'], 'revisao': item['revisao']})
    return plano


def aplicar(plano, administrador_id):
    with conectar_banco() as conexao:
        catalogo._exigir_administrador(conexao, administrador_id)
    total = 0
    for item in plano:
        if item['acao'] == 'inalterado':
            continue
        item_id = item['id']
        if item_id is not None:
            atual = catalogo.obter_item(item['secao'], item_id)
            if atual['revisao'] != item['revisao']:
                raise catalogo.EdicaoConflitante('O catálogo mudou durante a aplicação. Confira a gestão.')
        if item['acao'] != 'publicar':
            item_id = catalogo.salvar_rascunho(
                administrador_id, item['secao'], item['dados'],
                item_id=item_id, revisao=item['revisao'],
            )
        salvo = catalogo.obter_item(item['secao'], item_id)
        if salvo['rascunho'] != item['dados']:
            raise catalogo.EdicaoConflitante('O rascunho mudou antes de publicar. Confira a gestão.')
        catalogo.alterar_publicacao(administrador_id, item['secao'], item_id, salvo['revisao'], 'publicar')
        total += 1
    return total


@click.command(help="Sem --aplicar, mostra o plano e não grava nada.")
@click.option('--aplicar', 'gravar', is_flag=True, help='Salvar e publicar pelo serviço de gestão.')
@click.option('--administrador-id', type=click.IntRange(min=1), help='Conta responsável pelas ações de gestão.')
def main(gravar, administrador_id):
    if gravar and administrador_id is None:
        raise click.UsageError('Informe --administrador-id para registrar o responsável na auditoria.')
    load_dotenv(RAIZ / '.env')
    try:
        with create_app().app_context():
            plano = planejar(carregar_revisao())
            for item in plano:
                click.echo(f'{item["acao"]}: {item["secao"]} / {item["dados"]["titulo"]}')
            if gravar:
                total = aplicar(plano, administrador_id)
                click.echo(f'Concluído. {total} itens publicados; os históricos anteriores foram preservados.')
            else:
                click.echo('Conferência concluída. Use --aplicar e --administrador-id para publicar.')
    except Error:
        raise click.ClickException('Falha de banco. Confira a conexão e os rascunhos na gestão antes de repetir.') from None
    except (ValueError, PermissionError, catalogo.ItemNaoEncontrado) as erro:
        raise click.ClickException(str(erro) or 'Item do catálogo não encontrado.') from None


if __name__ == '__main__':
    main()
