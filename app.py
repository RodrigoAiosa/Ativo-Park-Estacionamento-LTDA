import streamlit as st
import fitz
import re
import gc
import tempfile
import os

CABECALHO = "Caixa;Transacao;T. Fiscais;Sessao;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lancado;Ticket;Forma PGTO"

IGNORAR = {
    'caixa', 'v. lancado', 'v. lançado', 'data', 'tarifa', 'v. estadia',
    'ticket', 'v. abonado', 'transacao', 'transação', 't. fiscais',
    'sessao', 'sessão', 'abono', 'forma', 'pgto', 'forma pgto',
    'detalhamento das transacoes', 'detalhamento das transações',
    'relatorio de transacoes', 'relatório de transações',
    'valores lancados', 'valores lançados',
}

def eh_ignorar(linha):
    return linha.lower().strip() in IGNORAR

def eh_data_hora(linha):
    return bool(re.match(r'^\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}$', linha))

def eh_data(linha):
    return bool(re.match(r'^\d{2}/\d{2}/\d{2}$', linha))

def eh_hora(linha):
    return bool(re.match(r'^\d{2}:\d{2}:\d{2}$', linha))

def eh_valor(linha):
    return bool(re.match(r'^R\$\s*[\d.]+$', linha))

def eh_numero_longo(linha):
    return bool(re.match(r'^\d{9,}$', linha))

def eh_numero_curto(linha):
    return bool(re.match(r'^\d{1,6}$', linha))

def limpar_valor(v):
    return v.strip().replace("R$ ", "R$")

def montar_csv(bloco):
    """
    Estrutura do bloco baseada no diagnóstico:
    PORTO (tarifa)
    10/06/25 14:15:19 (data hora)
    caixa buzios (caixa)
    15 (transacao sequencial)
    6 (sessao)
    100516151111 (ticket/transacao longa)
    R$ 30.00 (v. lancado)
    R$ 30.00 (v. estadia)
    Porto (abono/forma)
    R$ 0.00 (v. abonado)
    """
    tarifa    = ""
    data      = ""
    caixa     = ""
    trans_seq = ""
    sessao    = ""
    ticket    = ""
    valores   = []
    forma     = ""

    idx = 0
    while idx < len(bloco):
        item = bloco[idx].strip()

        if not item or eh_ignorar(item):
            idx += 1
            continue

        if eh_data_hora(item):
            data = item
        elif eh_data(item):
            # Tenta juntar com próxima linha que seja hora
            if idx + 1 < len(bloco) and eh_hora(bloco[idx+1].strip()):
                data = item + " " + bloco[idx+1].strip()
                idx += 1
            else:
                data = item
        elif eh_numero_longo(item):
            ticket = item
        elif eh_valor(item):
            valores.append(limpar_valor(item))
        elif eh_numero_curto(item):
            if not trans_seq:
                trans_seq = item
            elif not sessao:
                sessao = item
        elif re.match(r'^(Dinheiro|Porto|Nota|Cart|PIX|pix|debito|credito|Débito|Crédito)', item, re.IGNORECASE):
            forma = item
        elif re.match(r'^(PORTO|BUZIOS|ARRAIAL)', item, re.IGNORECASE) and not data:
            tarifa = item
        elif re.match(r'^caixa\s+', item, re.IGNORECASE) or 'buzios' in item.lower():
            caixa = item
        else:
            if not tarifa and not data:
                tarifa = item
            elif not caixa and data:
                caixa = item

        idx += 1

    if not data:
        return None

    v_lancado = valores[0] if len(valores) > 0 else "R$0.00"
    v_estadia = valores[1] if len(valores) > 1 else "R$0.00"
    v_abonado = valores[2] if len(valores) > 2 else "R$0.00"

    return ";".join([
        caixa, ticket, trans_seq, sessao, data,
        tarifa, v_estadia, forma, v_abonado, v_lancado, ticket, forma
    ])

def processar_pdf(caminho_pdf):
    progress = st.progress(0)
    status   = st.empty()

    doc   = fitz.open(caminho_pdf)
    total = len(doc)

    todas_linhas = []

    for i in range(total):
        status.info(f"Lendo pagina {i + 1} de {total}...")
        try:
            blocks = doc[i].get_text("blocks")
            for b in blocks:
                for l in b[4].split('\n'):
                    l = l.strip()
                    if l:
                        todas_linhas.append(l)
        except Exception:
            pass

        if i % 50 == 0:
            gc.collect()
        progress.progress(int(((i + 1) / total) * 100))

    doc.close()
    gc.collect()

    status.info("Montando transacoes...")

    # Agrupa blocos: cada bloco começa com PORTO (tarifa) antes de uma data
    # Detecta inicio pelo padrão: linha com PORTO seguida de data/hora
    blocos = []
    bloco_atual = []
    i = 0

    while i < len(todas_linhas):
        linha = todas_linhas[i].strip()

        # Início de transação: data/hora ou data seguida de hora
        if eh_data_hora(linha) or (eh_data(linha) and i+1 < len(todas_linhas) and eh_hora(todas_linhas[i+1].strip())):
            if bloco_atual:
                blocos.append(bloco_atual)
            # Inclui a linha anterior (tarifa/tipo) no bloco
            bloco_atual = []
            if blocos and len(blocos) > 0:
                pass
            bloco_atual.append(linha)
        else:
            bloco_atual.append(linha)
        i += 1

    if bloco_atual:
        blocos.append(bloco_atual)

    linhas_resultado = [CABECALHO]
    total_transacoes = 0

    for bloco in blocos:
        csv = montar_csv(bloco)
        if csv:
            linhas_resultado.append(csv)
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
                if os.path.exists(tmp_pdf.name):
                    os.unlink(tmp_pdf.name)

    if st.session_state.texto_final:
        total_linhas = len(st.session_state.texto_final.splitlines()) - 1
        st.info(f"{total_linhas} transacoes prontas para download.")
        st.text_area("Previa:",
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
