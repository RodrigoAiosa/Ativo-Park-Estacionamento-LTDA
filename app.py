import streamlit as st
import fitz
import re
import gc
import tempfile
import os

CABECALHO = "Caixa;Transacao;T. Fiscais;Sessao;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lancado;Ticket;Forma PGTO"

def limpar_valor(v):
    return v.strip().replace("R$ ", "R$")

def eh_cabecalho_ou_rodape(linha):
    padroes = [
        r'^Emiss', r'^Per.odo', r'^Valores', r'^DETALHAMENTO',
        r'^RELAT', r'^P.gina\s*:', r'^Emitido', r'^Transa..es$',
        r'^T\.\s*Fiscais$', r'^Caixa$', r'^V\.\s*Lan.ado$',
        r'^Data$', r'^Tarifa$', r'^V\.\s*Estadia$', r'^Ticket$',
        r'^V\.\s*Abonado$', r'^Transa..o$', r'^Sess.o$',
        r'^Abono$', r'^Forma$', r'^PGTO$',
        r'^\d{2}/\d{2}/\d{4}$',  # so data sem hora
        r'^R\$\s*[\d.]+$',        # so valor monetario
        r'^[a-z]\s*$',            # letra solta
        r'^\d+$',                 # numero isolado
        r'^Rorigo', r'^Rodrigo',
    ]
    for p in padroes:
        if re.match(p, linha, re.IGNORECASE):
            return True
    return False

def agrupar_transacoes(linhas):
    """
    O PDF tem cada campo em linha separada.
    Uma transacao completa tem exatamente os campos:
    caixa, data+hora, sessao, t.fiscais, transacao(numero longo),
    v.lancado, v.estadia, v.abonado, ticket, forma(opcional)
    
    Estrategia: agrupa blocos entre datas (dd/mm/aa HH:MM:SS)
    """
    resultado = []
    bloco = []

    padrao_data = re.compile(r'^\d{2}/\d{2}/\d{2}$')
    padrao_hora = re.compile(r'^\d{2}:\d{2}:\d{2}$')
    padrao_valor = re.compile(r'^R\$\s*[\d.]+$')
    padrao_transacao = re.compile(r'^\d{9,}$')

    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()

        # Detecta inicio de nova transacao: linha com data dd/mm/aa
        # seguida de hora HH:MM:SS
        if padrao_data.match(linha) and i + 1 < len(linhas) and padrao_hora.match(linhas[i+1].strip()):
            if bloco:
                resultado.append(bloco)
            bloco = [linha + " " + linhas[i+1].strip()]  # junta data e hora
            i += 2
        else:
            if bloco is not None:
                bloco.append(linha)
            i += 1

    if bloco:
        resultado.append(bloco)

    return resultado

def montar_linha_csv(bloco):
    """
    Monta uma linha CSV a partir de um bloco de campos.
    Ordem esperada no bloco apos agrupar:
    [0] data+hora, depois campos variados
    Precisamos identificar cada campo pelo seu formato.
    """
    padrao_valor   = re.compile(r'^R\$\s*[\d.]+$')
    padrao_ticket  = re.compile(r'^\d{9,}$')
    padrao_numero  = re.compile(r'^\d{1,4}$')
    padrao_datahora = re.compile(r'^\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}$')

    data     = ""
    caixa    = ""
    sessao   = ""
    t_fisc   = ""
    transacao = ""
    valores  = []
    forma    = ""
    ticket   = ""

    for campo in bloco:
        campo = campo.strip()
        if not campo or campo.upper() == 'PGTO':
            continue
        if padrao_datahora.match(campo):
            data = campo
        elif padrao_ticket.match(campo):
            ticket = campo
        elif padrao_valor.match(campo):
            valores.append(limpar_valor(campo))
        elif padrao_numero.match(campo):
            if not sessao:
                sessao = campo
            elif not t_fisc:
                t_fisc = campo
        elif re.match(r'^(Dinheiro|Porto|Nota|Cart|PIX|debito|credito)', campo, re.IGNORECASE):
            forma = campo
        elif re.match(r'^caixa\s+', campo, re.IGNORECASE) or 'buzios' in campo.lower() or 'caixa' in campo.lower():
            caixa = campo
        else:
            if not caixa:
                caixa = campo

    # valores: [v_lancado, v_estadia, v_abonado] — ordem que aparece no PDF
    v_lancado = valores[0] if len(valores) > 0 else ""
    v_estadia = valores[1] if len(valores) > 1 else ""
    v_abonado = valores[2] if len(valores) > 2 else ""

    if not data:
        return None

    return ";".join([caixa, ticket, t_fisc, sessao, data, "PORTO",
                     v_estadia, "", v_abonado, v_lancado, ticket, forma])

def processar_pdf(caminho_pdf):
    progress         = st.progress(0)
    status           = st.empty()
    total_transacoes = 0
    linhas_resultado = [CABECALHO]

    doc   = fitz.open(caminho_pdf)
    total = len(doc)

    todas_linhas = []

    for i in range(total):
        status.info(f"Lendo pagina {i + 1} de {total}...")
        try:
            conteudo = doc[i].get_text("text")
        except Exception:
            conteudo = None

        if conteudo:
            for linha in conteudo.split('\n'):
                l = linha.strip()
                if l and not eh_cabecalho_ou_rodape(l):
                    todas_linhas.append(l)

        if i % 50 == 0:
            gc.collect()

        progress.progress(int(((i + 1) / total) * 100))

    doc.close()
    gc.collect()

    status.info("Montando transacoes...")

    blocos = agrupar_transacoes(todas_linhas)

    for bloco in blocos:
        linha_csv = montar_linha_csv(bloco)
        if linha_csv:
            linhas_resultado.append(linha_csv)
            total_transacoes += 1

    status.success(f"Concluido! {total} paginas | {total_transacoes} transacoes.")
    return "\n".join(linhas_resultado)


def main():
    st.set_page_config(page_title="Extrator de Dados PDF", page_icon="📄")
    st.title("Extrator de Dados - Limpeza de Relatorio")
    st.write("Gere um arquivo .txt limpo, sem cabecalhos e paginacao.")

    if 'texto_final' not in st.session_state:
        st.session_state.texto_final = None
    if 'nome_arquivo' not in st.session_state:
        st.session_state.nome_arquivo = None

    arquivo_carregado = st.file_uploader("Escolha o arquivo PDF", type="pdf")

    if arquivo_carregado:
        st.success(f"Arquivo '{arquivo_carregado.name}' carregado!")

        if st.button("Processar e Extrair Dados"):
            tmp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp_pdf.write(arquivo_carregado.read())
            tmp_pdf.close()

            try:
                resultado = processar_pdf(tmp_pdf.name)
                if resultado:
                    st.session_state.texto_final = resultado
                    st.session_state.nome_arquivo = arquivo_carregado.name.replace(".pdf", "_extraido.txt")
            finally:
                os.unlink(tmp_pdf.name)

    if st.session_state.texto_final:
        total_linhas = len(st.session_state.texto_final.splitlines()) - 1
        st.info(f"{total_linhas} transacoes prontas para download.")
        st.text_area("Previa (primeiras linhas):",
                     "\n".join(st.session_state.texto_final.splitlines()[:20]),
                     height=200)

        st.download_button(
            label="Baixar arquivo .txt",
            data=st.session_state.texto_final.encode("utf-8"),
            file_name=st.session_state.nome_arquivo,
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
