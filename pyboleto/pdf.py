# -*- coding: utf-8 -*-
"""
    pyboleto.pdf
    ~~~~~~~~~~~~

    Classe Responsável por fazer o output do boleto em pdf usando Reportlab.

    :copyright: © 2011 - 2012 by Eduardo Cereto Carvalho
    :license: BSD, see LICENSE for more details.

"""
import os

from reportlab.graphics.barcode.common import I2of5
from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4, landscape as pagesize_landscape
from reportlab.lib.units import mm, cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


class BoletoPDF(object):
    """Geração do Boleto em PDF

    Esta classe é responsável por imprimir o boleto em PDF.
    Outras classes podem ser implementadas no futuro com a mesma interface,
    para fazer output em HTML, LaTeX, ...

    Esta classe pode imprimir boletos em formato de carnê (2 boletos por
    página) ou em formato de folha cheia.

    :param file_descr: Um arquivo ou *file-like* class.
    :param landscape: Formato da folha. Usar ``True`` para boleto
        tipo carnê.

    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, file_descr, landscape=False):
        self.width = 190 * mm
        self.width_canhoto = 70 * mm
        self.height_line = 6.5 * mm
        self.space = 2
        self.font_size_title = 6
        self.font_size_value = 9
        self.delta_title = self.height_line - (self.font_size_title + 1)
        self.delta_font = self.font_size_value + 1

        if landscape:
            pagesize = pagesize_landscape(A4)
        else:
            pagesize = A4

        self.pdf_canvas = canvas.Canvas(file_descr, pagesize=pagesize)
        self.pdf_canvas.setStrokeColor(black)

    def _draw_recibo_sacado_canhoto(self, boleto_dados, x, y,
                                    mostrar_rotulo_inferior=True):
        """Imprime o Recibo do Sacado para modelo de carnê

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        :param x: Current X coordinate
        :param y: Current Y coordinate

        """

        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        linha_inicial = 12

        # Horizontal Lines
        if mostrar_rotulo_inferior:
            # Borda inferior do canhoto. Omitida no carnê empilhado, onde o
            # código de barras full-width ocupa esta faixa.
            self.pdf_canvas.setLineWidth(2)
            self.__horizontalLine(0, 0, self.width_canhoto)

        self.pdf_canvas.setLineWidth(1)
        self.__horizontalLine(0,
                              (linha_inicial + 0) * self.height_line,
                              self.width_canhoto)
        self.__horizontalLine(0,
                              (linha_inicial + 1) * self.height_line,
                              self.width_canhoto)

        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0,
                              (linha_inicial + 2) * self.height_line,
                              self.width_canhoto)

        # Vertical Lines
        self.pdf_canvas.setLineWidth(1)
        self.__verticalLine(self.width_canhoto - (35 * mm),
                            (linha_inicial + 0) * self.height_line,
                            self.height_line)
        self.__verticalLine(self.width_canhoto - (35 * mm),
                            (linha_inicial + 1) * self.height_line,
                            self.height_line)

        self.pdf_canvas.setFont('Helvetica-Bold', 6)
        if mostrar_rotulo_inferior:
            # Posição padrão: na base do canhoto.
            self.pdf_canvas.drawRightString(self.width_canhoto,
                                            0 * self.height_line + 3,
                                            'Recibo do Pagador')
        else:
            # No carnê empilhado o código de barras full-width cruza a base;
            # move o rótulo para cima da última linha, fora da faixa do código.
            self.pdf_canvas.drawRightString(
                self.width_canhoto,
                (linha_inicial + 2) * self.height_line + 3,
                'Recibo do Pagador')

        # Titles
        self.pdf_canvas.setFont('Helvetica', 6)
        self.delta_title = self.height_line - (6 + 1)

        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Nosso Número'
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Vencimento'
        )
        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Agência/Código Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Valor Documento'
        )

        # Values
        self.pdf_canvas.setFont('Helvetica', 9)
        heigh_font = 9 + 1

        valor_documento = self._formataValorParaExibir(
            boleto_dados.valor_documento
        )

        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            boleto_dados.format_nosso_numero()
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            boleto_dados.data_vencimento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.agencia_conta_cedente
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            valor_documento
        )

        demonstrativo = boleto_dados.demonstrativo[0:12]
        for index, value in enumerate(demonstrativo):
            self.pdf_canvas.drawString(
                2 * self.space,
                (linha_inicial - 1) * self.height_line - (index * heigh_font),
                value[0:55]
            )

        self.pdf_canvas.restoreState()

        return (self.width_canhoto,
                ((linha_inicial + 2) * self.height_line))

    def _drawReciboSacado(self, boleto_dados, x, y):
        """Imprime o Recibo do Sacado para modelo de página inteira

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`

        """

        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        linha_inicial = 15

        # Horizontal Lines
        self.pdf_canvas.setLineWidth(1)
        self.__horizontalLine(0,
                              (linha_inicial + 0) * self.height_line,
                              self.width)
        self.__horizontalLine(0,
                              (linha_inicial + 1) * self.height_line,
                              self.width)
        self.__horizontalLine(0,
                              (linha_inicial + 2) * self.height_line,
                              self.width)

        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0,
                              (linha_inicial + 3) * self.height_line,
                              self.width)

        # Vertical Lines
        self.pdf_canvas.setLineWidth(1)
        self.__verticalLine(
            self.width - (30 * mm),
            (linha_inicial + 0) * self.height_line,
            3 * self.height_line
        )
        self.__verticalLine(
            self.width - (30 * mm) - (35 * mm),
            (linha_inicial + 1) * self.height_line,
            2 * self.height_line
        )
        self.__verticalLine(
            self.width - (30 * mm) - (35 * mm) - (40 * mm),
            (linha_inicial + 1) * self.height_line,
            2 * self.height_line
        )

        # Head
        self.pdf_canvas.setLineWidth(2)
        self.__verticalLine(40 * mm,
                            (linha_inicial + 3) * self.height_line,
                            self.height_line)
        self.__verticalLine(60 * mm,
                            (linha_inicial + 3) * self.height_line,
                            self.height_line)

        if boleto_dados.logo_image:
            logo_image_path = load_image(boleto_dados.logo_image)
            self.pdf_canvas.drawImage(
                logo_image_path,
                0, (linha_inicial + 3) * self.height_line + 3,
                40 * mm,
                self.height_line,
                preserveAspectRatio=True,
                anchor='sw'
            )
        self.pdf_canvas.setFont('Helvetica-Bold', 18)
        self.pdf_canvas.drawCentredString(
            50 * mm,
            (linha_inicial + 3) * self.height_line + 3,
            boleto_dados.codigo_dv_banco
        )
        self.pdf_canvas.setFont('Helvetica-Bold', 11.5)
        self.pdf_canvas.drawRightString(
            self.width,
            (linha_inicial + 3) * self.height_line + 3,
            'Recibo do Pagador'
        )

        # Titles
        self.pdf_canvas.setFont('Helvetica', 6)
        self.delta_title = self.height_line - (6 + 1)

        self.pdf_canvas.drawRightString(
            self.width,
            self.height_line,
            'Autenticação Mecânica'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'Agência/Código Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'CPF/CNPJ Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'Vencimento'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Pagador')
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Nosso Número')
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'N. do documento')
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Data Documento'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Endereço Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Valor Documento'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 0) * self.height_line - 3 * cm)) +
            self.delta_title,
            'Demonstrativo'
        )

        # Values
        self.pdf_canvas.setFont('Helvetica', 9)
        heigh_font = 9 + 1

        self.pdf_canvas.drawString(
            0 + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.cedente
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.agencia_conta_cedente
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.cedente_documento
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.data_vencimento.strftime('%d/%m/%Y')
        )

        # Take care of long field
        sacado0 = boleto_dados.sacado[0]
        while (stringWidth(sacado0,
                           self.pdf_canvas._fontname,
                           self.pdf_canvas._fontsize
                           ) > 8.4 * cm):

            # sacado0 = sacado0[:-2] + u'\u2026'
            sacado0 = sacado0[:-4] + '...'

        self.pdf_canvas.drawString(
            0 + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            sacado0
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.format_nosso_numero()
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.numero_documento
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.data_documento.strftime('%d/%m/%Y')
        )

        valor_documento = self._formataValorParaExibir(
            boleto_dados.valor_documento
        )

        self.pdf_canvas.drawString(
            0 + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            boleto_dados.cedente_endereco
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            valor_documento
        )

        self.pdf_canvas.setFont('Courier', 9)
        demonstrativo = boleto_dados.demonstrativo[0:25]
        for i in range(len(demonstrativo)):
            self.pdf_canvas.drawString(
                2 * self.space,
                (-3 * cm + ((linha_inicial + 0) * self.height_line)) -
                (i * heigh_font),
                demonstrativo[i])

        self.pdf_canvas.setFont('Helvetica', 9)

        self.pdf_canvas.restoreState()

        return (self.width, ((linha_inicial + 3) * self.height_line))

    def _drawHorizontalCorteLine(self, x, y, width):
        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        self.pdf_canvas.setLineWidth(1)
        self.pdf_canvas.setDash(1, 2)
        self.__horizontalLine(0, 0, width)

        self.pdf_canvas.restoreState()

    def _drawVerticalCorteLine(self, x, y, height):
        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        self.pdf_canvas.setLineWidth(1)
        self.pdf_canvas.setDash(1, 2)
        self.__verticalLine(0, 0, height)

        self.pdf_canvas.restoreState()

    def _drawReciboCaixa(self, boleto_dados, x, y, barcode=True,
                         compensacao_barcode=1.0, altura_barcode=13 * mm):
        """Imprime o Recibo do Caixa

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        :param compensacao_barcode: Fator para ampliar o código de barras no
            frame local, compensando uma escala aplicada ao canvas para que
            ele saia no tamanho físico correto (padrão Febraban). Use
            ``1 / escala`` quando o boleto é desenhado dentro de um canvas
            reduzido; ``1.0`` (padrão) para tamanho normal.
        :param altura_barcode: Altura das barras no frame local (padrão 13mm).
            Num canvas reduzido, aumente-a para que a altura física fique
            legível na impressão.

        """
        self.pdf_canvas.saveState()

        self.pdf_canvas.translate(x, y)

        # De baixo para cima posicao 0,0 esta no canto inferior esquerdo
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        y = 1.5 * self.height_line
        if barcode:
            # Posição padrão: na base, logo acima do código de barras.
            self.pdf_canvas.drawRightString(
                self.width,
                (1.5 * self.height_line) + self.delta_title - 1,
                'Autenticação Mecânica / Ficha de Compensação'
            )
        else:
            # No carnê empilhado o código full-width ocupa a base; move o
            # rótulo para cima da faixa do código.
            self.pdf_canvas.drawRightString(
                self.width,
                (2.5 * self.height_line) + self.delta_title - 1,
                'Autenticação Mecânica / Ficha de Compensação'
            )

        # Primeira linha depois do codigo de barra
        y += self.height_line
        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.space, 'Código de baixa'
        )
        self.pdf_canvas.drawString(0, y + self.space, 'Sacador / Avalista')

        y += self.height_line
        self.pdf_canvas.drawString(0, y + self.delta_title, 'Pagador')
        sacado = boleto_dados.sacado

        # Linha grossa dividindo o Sacado
        y += self.height_line
        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        for i in range(len(sacado)):
            self.pdf_canvas.drawString(
                15 * mm,
                (y - 10) - (i * self.delta_font),
                sacado[i]
            )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha vertical limitando todos os campos da direita
        self.pdf_canvas.setLineWidth(1)
        self.__verticalLine(self.width - (45 * mm), y, 9.5 * self.height_line)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(=) Valor cobrado'
        )

        # Campos da direita
        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(+) Outros acréscimos'
        )

        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(+) Mora/Multa'
        )

        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(-) Outras deduções'
        )

        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(-) Descontos/Abatimentos'
        )
        self.pdf_canvas.drawString(
            0,
            y + self.delta_title,
            'Instruções'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        instrucoes = boleto_dados.instrucoes
        for i in range(len(instrucoes)):
            self.pdf_canvas.drawString(
                2 * self.space,
                y - (i * self.delta_font),
                instrucoes[i]
            )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Uso do Banco
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(0, y + self.delta_title, 'Uso do banco')

        self.__verticalLine((30) * mm, y, 2 * self.height_line)
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.delta_title,
            'Carteira'
        )

        self.__verticalLine((30 + 20) * mm, y, self.height_line)
        self.pdf_canvas.drawString(
            ((30 + 20) * mm) + self.space,
            y + self.delta_title,
            'Espécie'
        )

        self.__verticalLine(
            (30 + 20 + 20) * mm,
            y,
            2 * self.height_line
        )
        self.pdf_canvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.delta_title,
            'Quantidade'
        )

        self.__verticalLine(
            (30 + 20 + 20 + 20 + 20) * mm, y, 2 * self.height_line)
        self.pdf_canvas.drawString(
            ((30 + 40 + 40) * mm) + self.space, y + self.delta_title, 'Valor')

        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(=) Valor documento'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.space,
            boleto_dados.carteira
        )
        self.pdf_canvas.drawString(
            ((30 + 20) * mm) + self.space,
            y + self.space,
            boleto_dados.especie
        )
        self.pdf_canvas.drawString(
            ((30 + 20 + 20) * mm) + self.space,
            y + self.space,
            boleto_dados.quantidade
        )
        valor = ''
        if boleto_dados.valor != '0.00':
            valor = self._formataValorParaExibir(boleto_dados.valor)
        self.pdf_canvas.drawString(
            ((30 + 20 + 20 + 20 + 20) * mm) + self.space,
            y + self.space,
            valor
        )
        valor_documento = self._formataValorParaExibir(
            boleto_dados.valor_documento
        )
        valor_desconto = self._formataValorParaExibir(
            boleto_dados.valor_desconto
        )
        valor_cobrado = self._formataValorParaExibir(
            boleto_dados.valor_cobrado
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            valor_documento
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space - 18,
            valor_desconto
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space - 90,
            valor_cobrado
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Data documento
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(
            0,
            y + self.delta_title,
            'Data do documento'
        )
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.delta_title,
            'N. do documento'
        )
        self.pdf_canvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.delta_title,
            'Espécie doc'
        )
        self.__verticalLine(
            (30 + 20 + 20 + 20) * mm,
            y,
            self.height_line
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 20) * mm) + self.space,
            y + self.delta_title,
            'Aceite'
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 40) * mm) + self.space,
            y + self.delta_title,
            'Data processamento'
        )
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            'Nosso número'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        self.pdf_canvas.drawString(
            0,
            y + self.space,
            boleto_dados.data_documento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.space,
            boleto_dados.numero_documento
        )
        self.pdf_canvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.space,
            boleto_dados.especie_documento
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 20) * mm) + self.space,
            y + self.space,
            boleto_dados.aceite
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 40) * mm) + self.space,
            y + self.space,
            boleto_dados.data_processamento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boleto_dados.format_nosso_numero()
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Cedente
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(0, y + self.delta_title + 10,
                                   'Beneficiário')
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title + 10,
            boleto_dados.label_cedente
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        beneficiario = '{} - CPF/CNPJ: {}'.format(
            boleto_dados.cedente, boleto_dados.cedente_documento)
        self.pdf_canvas.drawString(0, y + self.space + 10, beneficiario)
        self.pdf_canvas.drawString(0, y + self.space,
                                   boleto_dados.cedente_endereco)
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boleto_dados.agencia_conta_cedente
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Local de Pagamento
        y += self.height_line + 10
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(
            0,
            y + self.delta_title,
            'Local de pagamento'
        )
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            'Vencimento'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        self.pdf_canvas.drawString(
            0,
            y + self.space,
            boleto_dados.local_pagamento
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boleto_dados.data_vencimento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha grossa com primeiro campo logo tipo do banco
        self.pdf_canvas.setLineWidth(3)
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.setLineWidth(2)
        self.__verticalLine(40 * mm, y, self.height_line)  # Logo Tipo
        self.__verticalLine(60 * mm, y, self.height_line)  # Numero do Banco

        if boleto_dados.logo_image:
            logo_image_path = load_image(boleto_dados.logo_image)
            self.pdf_canvas.drawImage(
                logo_image_path,
                0,
                y + self.space + 1,
                40 * mm,
                self.height_line,
                preserveAspectRatio=True,
                anchor='sw'
            )
        self.pdf_canvas.setFont('Helvetica-Bold', 18)
        self.pdf_canvas.drawCentredString(
            50 * mm,
            y + 2 * self.space,
            boleto_dados.codigo_dv_banco
        )
        self.pdf_canvas.setFont('Helvetica-Bold', 11.5)
        self.pdf_canvas.drawRightString(
            self.width,
            y + 2 * self.space,
            boleto_dados.linha_digitavel
        )

        # Codigo de barras. No tamanho normal usa 103mm (padrão Febraban).
        # Quando o canvas está reduzido por escala (compensacao > 1), o código
        # é esticado para ocupar toda a largura útil da ficha, sem sobrar
        # espaço; as barras ficam mais largas, o que só ajuda a leitura. A
        # ALTURA (altura_barcode) controla a altura física das barras.
        if barcode:
            if compensacao_barcode > 1:
                comprimento = self.width - 4 * self.space
            else:
                comprimento = 103 * mm
            self._codigoBarraI25(
                boleto_dados.barcode, 2 * self.space, 0,
                altura=altura_barcode,
                comprimento=comprimento)

        self.pdf_canvas.restoreState()

        return self.width, (y + self.height_line)

    def drawBoletoCarneDuplo(self, boletoDados1, boletoDados2=None, y=-1 * mm):
        """Imprime um boleto tipo carnê com 2 boletos por página.

        :param boletoDados1: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :param boletoDados2: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados1: :class:`pyboleto.data.BoletoData`
        :type boletoDados2: :class:`pyboleto.data.BoletoData`

        """
        d = self.drawBoletoCarne(boletoDados1, y)
        y += d[1] + 6 * mm
        # self._drawHorizontalCorteLine(0, y, d[0])
        y += 7 * mm
        if boletoDados2:
            self.drawBoletoCarne(boletoDados2, y)

    def drawBoletoCarneTriplo(self, boletoDados1, boletoDados2=None,
                              boletoDados3=None):
        """Imprime um boleto tipo carnê com 3 boletos por página.

        Atalho para :meth:`drawBoletoCarneEmpilhado` com 3 vias.
        ``boletoDados2`` e ``boletoDados3`` são opcionais, permitindo uma
        última página com 1 ou 2 boletos.

        :param boletoDados1: Objeto com os dados do 1º boleto.
        :param boletoDados2: Objeto com os dados do 2º boleto.
        :param boletoDados3: Objeto com os dados do 3º boleto.
        :type boletoDados1: :class:`pyboleto.data.BoletoData`
        :type boletoDados2: :class:`pyboleto.data.BoletoData`
        :type boletoDados3: :class:`pyboleto.data.BoletoData`

        """
        return self.drawBoletoCarneEmpilhado(
            [boletoDados1, boletoDados2, boletoDados3])

    def drawBoletoCarneQuadruplo(self, boletoDados1, boletoDados2=None,
                                 boletoDados3=None, boletoDados4=None):
        """Imprime um boleto tipo carnê com 4 boletos por página.

        Atalho para :meth:`drawBoletoCarneEmpilhado` com 4 vias. Os boletos
        além do 1º são opcionais, permitindo uma última página incompleta.

        :param boletoDados1: Objeto com os dados do 1º boleto.
        :param boletoDados2: Objeto com os dados do 2º boleto.
        :param boletoDados3: Objeto com os dados do 3º boleto.
        :param boletoDados4: Objeto com os dados do 4º boleto.
        :type boletoDados1: :class:`pyboleto.data.BoletoData`
        :type boletoDados2: :class:`pyboleto.data.BoletoData`
        :type boletoDados3: :class:`pyboleto.data.BoletoData`
        :type boletoDados4: :class:`pyboleto.data.BoletoData`

        """
        return self.drawBoletoCarneEmpilhado(
            [boletoDados1, boletoDados2, boletoDados3, boletoDados4])

    def drawBoletoCarneEmpilhado(self, boletos):
        """Empilha vários boletos tipo carnê numa folha A4 retrato.

        O carnê (canhoto + ficha lado a lado) tem ~291mm de largura, então
        só cabe inteiro em folha *landscape*. Para empilhar vários numa folha
        A4 em modo retrato (portrait), cada carnê é reduzido por um fator de
        escala para caber na largura útil da página; a altura reduzida
        permite empilhá-los sem cortar nenhum campo. Construa o ``BoletoPDF``
        com ``landscape=False`` (padrão) para este formato.

        Os boletos são desenhados de cima para baixo na ordem da lista (o
        primeiro no topo). Valores ``None`` são ignorados, permitindo uma
        última página incompleta. Linhas de corte tracejadas são desenhadas
        apenas *entre* os carnês, no meio de cada folga; as margens do topo e
        da base valem metade da folga entre carnês, de modo que a distância
        livre até cada linha de corte seja visualmente uniforme na folha.

        :param boletos: Lista de objetos com os dados de cada boleto
            (subclasses de :class:`pyboleto.data.BoletoData`); ``None`` é
            ignorado.
        """
        page_width, page_height = A4

        boletos = [b for b in boletos if b]
        if not boletos:
            return (page_width, page_height)

        # O drawBoletoCarne começa a desenhar em x = offset_interno; esse
        # deslocamento NÃO faz parte do conteúdo, então é descontado para o
        # carnê preencher a largura de forma simétrica (sem sobrar espaço à
        # esquerda). A largura útil é canhoto + corte + ficha.
        offset_interno = 15 * mm
        largura_carne = self.width_canhoto + 16 * mm + self.width
        altura_nativa = self._alturaCarne()

        n = len(boletos)

        # A escala é limitada por dois lados: encher a largura (deixando uma
        # margem lateral mínima) e caber na altura preservando um espaçamento
        # vertical mínimo entre os carnês. Usa-se a menor das duas, então as
        # laterais ficam o mais justas possível sem que os carnês estourem a
        # altura nem colem uns nos outros.
        margem_lateral_min = 3 * mm
        espaco_min = 6 * mm
        escala_largura = (page_width - 2 * margem_lateral_min) / largura_carne
        escala_altura = (page_height - n * espaco_min) / (n * altura_nativa)
        escala = min(escala_largura, escala_altura)

        altura_carne = altura_nativa * escala

        # Espaçamento visualmente uniforme. A linha de corte fica no meio de
        # cada folga entre carnês, então de cada carnê até a linha há
        # ``espaco_entre_vias / 2``; as margens do topo e da base valem o
        # mesmo, deixando a folga uniforme na folha.
        espaco_entre_vias = (page_height - n * altura_carne) / n
        margem_topo_base = espaco_entre_vias / 2

        # Margem lateral resultante (>= mínima): centraliza o bloco na largura.
        margem_lateral = (page_width - escala * largura_carne) / 2

        largura_corte = escala * largura_carne

        # Código de barras alinhado à largura do boleto (não à da página),
        # para não ultrapassar as bordas do carnê. Ainda fica bem largo
        # (~190mm), com barras grossas (~0,46mm) — leitura robusta em qualquer
        # impressora. Como cruza a faixa do canhoto, os rótulos daquela faixa
        # (Recibo do Pagador, Autenticação Mecânica) são omitidos.
        altura_barcode_pagina = 9.5 * mm

        # Translada de forma que o conteúdo (que começa em offset_interno no
        # frame do carnê) fique alinhado à margem esquerda, preenchendo a
        # largura útil de forma simétrica.
        translate_x = margem_lateral - offset_interno * escala

        # Desenha de baixo para cima; assim o 1º da lista fica no topo.
        y = margem_topo_base
        for indice, boleto_dados in enumerate(reversed(boletos)):
            self.pdf_canvas.saveState()
            self.pdf_canvas.translate(translate_x, y)
            self.pdf_canvas.scale(escala, escala)
            # Ficha sem o código de barras (e sem os rótulos da faixa do
            # código, que seriam cobertos por ele).
            self.drawBoletoCarne(boleto_dados, 0, barcode=False)
            self.pdf_canvas.restoreState()

            # Código de barras full-width na faixa do rodapé (a ficha reserva
            # ~13mm ali; usamos essa altura, sem acrescentar espaço).
            self._codigoBarraI25(
                boleto_dados.barcode, margem_lateral, y - 1 * mm,
                altura=altura_barcode_pagina,
                comprimento=largura_corte)

            y += altura_carne + espaco_entre_vias

            # Linha de corte tracejada no meio do espaço até o próximo carnê.
            # Não desenha após o último (a folga do topo já é margem_topo_base).
            if indice < n - 1:
                self._drawHorizontalCorteLine(
                    margem_lateral, y - espaco_entre_vias / 2, largura_corte)

        title = "%s - %s" % (boletos[0].sacado[0],
                             boletos[0].numero_documento)
        self.pdf_canvas.setTitle(title)

        return (page_width, page_height)

    def _alturaCarne(self):
        """Altura nativa (sem escala) de um carnê, igual à altura da ficha de
        compensação (:meth:`_drawReciboCaixa`). A ficha cresce em passos de
        ``height_line``: 14.5 linhas mais um acréscimo fixo de 10pt embutido
        no layout. Depende só de ``height_line``, não dos dados do boleto."""
        return 14.5 * self.height_line + 10

    def drawBoletoCarne(self, boleto_dados, y, compensacao_barcode=1.0,
                        altura_barcode=13 * mm, barcode=True):
        """Imprime apenas dos boletos do carnê.

        Esta função não deve ser chamada diretamente, ao invés disso use a
        drawBoletoCarneDuplo.

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        :param compensacao_barcode: Repassado a :meth:`_drawReciboCaixa` para
            manter o código de barras no tamanho físico correto quando o
            carnê é desenhado dentro de um canvas reduzido por escala.
        :param altura_barcode: Altura das barras (frame local) repassada a
            :meth:`_drawReciboCaixa`.
        :param barcode: Quando ``False``, a ficha é desenhada sem o código de
            barras e sem os rótulos da faixa do código (Recibo do Pagador,
            Autenticação Mecânica), pois o código é plotado por fora,
            full-width (ver :meth:`drawBoletoCarneEmpilhado`).
        """
        x = 15 * mm
        d = self._draw_recibo_sacado_canhoto(
            boleto_dados, x, y, mostrar_rotulo_inferior=barcode)
        x += d[0] + 8 * mm
        if barcode:
            self._drawVerticalCorteLine(x, y, d[1])
        else:
            # Carnê empilhado: o código de barras full-width ocupa a base;
            # a linha de corte vertical começa acima dele para não cruzá-lo.
            base_barcode = 18 * mm
            self._drawVerticalCorteLine(x, y + base_barcode,
                                        d[1] - base_barcode)
        x += 8 * mm
        d = self._drawReciboCaixa(boleto_dados, x, y,
                                  barcode=barcode,
                                  compensacao_barcode=compensacao_barcode,
                                  altura_barcode=altura_barcode)
        x += d[0]
        return x, d[1]

    def drawBoleto(self, boleto_dados):
        """Imprime Boleto Convencional

        Você pode chamar este método diversas vezes para criar um arquivo com
        várias páginas, uma por boleto.

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        """
        x = 9 * mm  # margem esquerda
        y = 10 * mm  # margem inferior

        self._drawHorizontalCorteLine(x, y, self.width)
        y += 4 * mm  # distancia entre linha de corte e barcode

        d = self._drawReciboCaixa(boleto_dados, x, y)
        y += d[1] + (12 * mm)  # distancia entre Recibo caixa e linha de corte

        self._drawHorizontalCorteLine(x, y, self.width)

        y += 20 * mm
        d = self._drawReciboSacado(boleto_dados, x, y)
        y += d[1]

        title = "%s - %s" % (boleto_dados.sacado_nome,
                             boleto_dados.numero_documento)
        self.pdf_canvas.setTitle(title)
        return (self.width, y)
    
    def drawBoletoDuasVias(self, boleto_dados):
        """
        Imprime DUAS VIAS do boleto na mesma página A4 (uma em cima da outra),
        separadas por linha de corte horizontal tracejada.
        """
        _, page_height = A4

        # Margens
        margem_esquerda = 9 * mm
        margem_superior_primeira_via = 100 * mm   # distância do topo da página até a 1ª via
        espaco_entre_vias = 15 * mm              # espaço + linha de corte

        # ============================
        # PRIMEIRA VIA (parte de cima)
        # ============================
        y = page_height - margem_superior_primeira_via

        # Desce um pouco para começar o conteúdo
        y -= 10 * mm

        # Desenha a Ficha de Compensação completa (logo + linha digitável + código de barras)
        _, altura_usada = self._drawReciboCaixa(boleto_dados, margem_esquerda, y, barcode=False)

        y += 5 * mm

        self._drawHorizontalCorteLine(margem_esquerda, y, self.width)

        y_segunda_via = y - altura_usada - espaco_entre_vias

        y_segunda_via += 5 * mm

        self._drawReciboCaixa(boleto_dados, margem_esquerda, y_segunda_via)

        # Título do PDF
        title = f"{boleto_dados.sacado[0]} - {boleto_dados.numero_documento}"
        self.pdf_canvas.setTitle(title)

        return (self.width, page_height)

    def nextPage(self):
        """Força início de nova página"""

        self.pdf_canvas.showPage()

    def save(self):
        """Fecha boleto e constroi o arquivo"""

        self.pdf_canvas.save()

    def __horizontalLine(self, x, y, width):
        self.pdf_canvas.line(x, y, x + width, y)

    def __verticalLine(self, x, y, width):
        self.pdf_canvas.line(x, y, x, y + width)

    def _formataValorParaExibir(self, nfloat):
        if nfloat:
            txt = nfloat
            txt = txt.replace('.', ',')
        else:
            txt = ""
        return txt

    def _codigoBarraI25(self, num, x, y, altura=13 * mm, comprimento=103 * mm):
        """Imprime Código de barras otimizado para boletos

        O código de barras é otmizado para que o comprimento seja sempre o
        estipulado pela Febraban de 103mm.

        :param altura: Altura das barras (padrão 13mm).
        :param comprimento: Comprimento total do código (padrão 103mm).

        """
        # http://en.wikipedia.org/wiki/Interleaved_2_of_5

        thin_bar = 0.254320987654 * mm  # Tamanho correto aproximado

        bc = I2of5(num,
                   barWidth=thin_bar,
                   ratio=3,
                   barHeight=altura,
                   bearers=0,
                   quiet=0,
                   checksum=0)

        # Recalcula o tamanho do thin_bar para que o cod de barras tenha o
        # comprimento correto
        thin_bar = (thin_bar * comprimento) / bc.width
        bc.__init__(num, barWidth=thin_bar)

        bc.drawOn(self.pdf_canvas, x, y)


def load_image(logo_image):
    """Load Bank Image"""
    pyboleto_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(pyboleto_dir, 'media', logo_image)
    return image_path
