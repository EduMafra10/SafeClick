"""Exporta os indicadores da Visão geral em uma planilha do Excel (.xlsx)."""
import io
from datetime import timedelta

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

_TITULO = Font(bold=True, size=16, color="173B45")
_SECAO = Font(bold=True, size=12, color="27684F")
_CABECALHO = Font(bold=True, color="FFFFFF")
_FUNDO_CABECALHO = PatternFill("solid", fgColor="27684F")
_FUNDO_TOTAL = PatternFill("solid", fgColor="EAF3ED")
_NOTA = Font(italic=True, color="586D72")
_LINHA = Border(bottom=Side(style="thin", color="DCE5E3"))

PORCENTAGEM = "0%"
MEDIA = "0.0"
DATA = "dd/mm/yyyy"


def _fracao(percentual):
    return None if percentual is None else percentual / 100


class _Aba:
    def __init__(self, aba, titulo, larguras):
        self.aba = aba
        self.aba.title = titulo
        self.linha = 1
        for coluna, largura in larguras.items():
            aba.column_dimensions[coluna].width = largura
        # na impressão, a tabela cabe na largura da folha
        aba.sheet_properties.pageSetUpPr.fitToPage = True
        aba.page_setup.fitToWidth = 1
        aba.page_setup.fitToHeight = 0

    def celula(self, coluna, valor, formato=None):
        celula = self.aba.cell(row=self.linha, column=coluna, value=valor)
        # texto que começa com "=" seria lido como fórmula pelo Excel
        if isinstance(valor, str) and valor.startswith("="):
            celula.data_type = "s"
        if formato:
            celula.number_format = formato
        return celula

    def texto(self, valor, fonte=None):
        celula = self.celula(1, valor)
        if fonte:
            celula.font = fonte
        self.linha += 1

    def tabela(self, titulo, colunas, linhas, formatos=(), vazio="Nenhum registro no período."):
        if titulo:
            self.linha += 1
            self.texto(titulo, _SECAO)
        primeira = linhas[0] if linhas else ()
        for n, nome in enumerate(colunas, start=1):
            celula = self.celula(n, nome)
            celula.font = _CABECALHO
            celula.fill = _FUNDO_CABECALHO
            texto = n == 1 or (n <= len(primeira) and isinstance(primeira[n - 1], str))
            celula.alignment = Alignment(horizontal="left" if texto else "right")
        self.linha += 1
        if not linhas:
            self.texto(vazio, _NOTA)
        for valores in linhas:
            for n, valor in enumerate(valores, start=1):
                formato = formatos[n - 1] if n <= len(formatos) else None
                self.celula(n, valor, formato).border = _LINHA
            self.linha += 1


def gerar_planilha(dados, rotulos_atividade, secoes, avaliacoes, gerado_em):
    inicio = dados["inicio"]
    fim = inicio + timedelta(days=dados["dias"] - 1)
    contas = dados["contas"]
    atividades = dados["atividades"]
    seguranca = dados["seguranca"]

    planilha = Workbook()
    planilha.properties.creator = "SafeClick"

    resumo = _Aba(planilha.active, "Resumo", {"A": 52, "B": 14, "C": 18, "D": 12})
    resumo.texto("SafeClick - Visão geral", _TITULO)
    resumo.texto(f"Período: últimos {dados['dias']} dias ({inicio:%d/%m/%Y} a {fim:%d/%m/%Y})")
    resumo.texto(f"Gerado em {gerado_em:%d/%m/%Y} às {gerado_em:%H:%M} (horário de Brasília)")
    resumo.texto("Indicadores agregados, sem dados pessoais. Administradores não entram na contagem.", _NOTA)

    resumo.tabela("Resumo do período", ("Indicador", "Total", "% dos usuários"), [
        ("Usuários cadastrados", contas["total"], None),
        ("Novos usuários no período", contas["novas"], None),
        ("Usuários ativos no período", contas["ativas"], _fracao(contas["percentual_ativas"])),
        ("Contas com autenticador ativo", contas["autenticador_ativo"], _fracao(contas["percentual_autenticador"])),
        ("QR Code gerado e não ativado", contas["autenticador_pendente"], None),
        ("Atividades concluídas no período", atividades["total"], None),
        *[(f"   {rotulo}", atividades["por_tipo"][tipo], None) for tipo, rotulo in rotulos_atividade.items()],
    ], (None, None, PORCENTAGEM))

    resumo.tabela(
        "Simulações - escolhas seguras na primeira tentativa",
        ("Simulação", "Pessoas", "Escolhas seguras"),
        [(c["titulo"], c["pessoas"], _fracao(c["percentual_seguras"])) for c in dados["simulacoes"]],
        (None, None, PORCENTAGEM),
    )
    resumo.tabela(
        "Quizzes com menor média",
        ("Quiz", "Tentativas", "Acertos"),
        [(q["titulo"], q["tentativas"], _fracao(q["percentual_acertos"])) for q in dados["quizzes"]],
        (None, None, PORCENTAGEM),
    )
    resumo.tabela("Conteúdo publicado", ("Seção", "Publicados", "Rascunhos"), [
        (rotulo, item["publicados"], item["rascunhos"])
        for chave, rotulo in secoes.items()
        for item in [dados["catalogo"].get(chave, {"publicados": 0, "rascunhos": 0})]
    ])
    resumo.tabela("Segurança nas últimas 24 horas", ("Indicador", "Total"), [
        ("Falhas de login", seguranca["falhas_login"]),
        ("Acessos negados", seguranca["acessos_negados"]),
        ("Autenticadores redefinidos", seguranca["autenticadores_redefinidos"]),
    ])
    if avaliacoes is not None:
        resumo.tabela(
            "Menores notas (avaliações de 1 a 5)",
            ("Atividade", "Tipo", "Avaliações", "Média"),
            [(item["titulo"], item["tipo"], item["total"], float(item["media"])) for item in avaliacoes],
            (None, None, None, MEDIA),
            vazio="Nenhuma atividade foi avaliada ainda.",
        )

    por_dia = _Aba(planilha.create_sheet(), "Atividades por dia",
                   {"A": 14, "B": 22, "C": 22, "D": 20, "E": 20, "F": 10})
    series = atividades["por_dia"]["series"]
    linhas = []
    for n in range(len(atividades["por_dia"]["dias"])):
        valores = [series[tipo][n] for tipo in rotulos_atividade]
        linhas.append((inicio + timedelta(days=n), *valores, sum(valores)))
    por_dia.tabela(None, ("Dia", *rotulos_atividade.values(), "Total"), linhas, (DATA,))
    totais = ["Total", *(atividades["por_tipo"][tipo] for tipo in rotulos_atividade), atividades["total"]]
    for n, valor in enumerate(totais, start=1):
        celula = por_dia.celula(n, valor)
        celula.font = Font(bold=True)
        celula.fill = _FUNDO_TOTAL
    por_dia.aba.freeze_panes = "A2"

    saida = io.BytesIO()
    planilha.save(saida)
    return saida.getvalue()