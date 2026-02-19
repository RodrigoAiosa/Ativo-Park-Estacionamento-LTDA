import streamlit as st
import pdfplumber
import re
import gc
import tempfile
import os

CABECALHO = "Caixa;Transação;T. Fiscais;Sessão;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lançado;Ticket;Forma PGTO"
TAMANHO_LOTE = 20

def limpar_valor(v):
    return v.strip().replace("R$ ", "R$")

def parsear_linha(linha):
    linha = re.sub(r'\bPGTO\b', '', linha).strip()

    padrao = re.compile(
        r'^(\S+)\s+'
        r'(\d{2}/\d{2}/\d{2})\s+'
        r'(\d{2}:\d{2}:\d{2})\s+'
        r'(.+?)\s+'
        r'(\d+)\s+'
        r'(\d+)\s+'
        r'(\d{9,})\s+'
        r'(R\$\s*[\d.]+)\s+'
        r'(R\$\s*[\d.]+)\s+'
        r'(\S+)\s+'
        r'(R\$\s*[\d.]+)$'
    )

    m = padrao.match(linha)
    if m:
        caixa      = m.group(1)
        data       = m.group(2) + " " + m.group(3)
        sessao     = m.group(4)
        t_fiscais  = m.group(5)
        abono      = m.group(6)
        transacao  = m.group(7)
        v_lancado  = limpar_valor(m.group(8))
        v_estadia  = limpar_valor(m.group(9))
        forma_pgto = m.group(10)
        tarifa     = limpar_valor(m.group(11))

        return ";".join([caixa, transacao, t_fiscais, sessao, data, tarifa,
                         v_estadia, abono, "R$0.00", v_lancado, "", forma_pgto])
    return None

def extrair_texto_pdf(caminho_pdf_disco):
    """Recebe o CAMINHO no disco, não o objeto em memória."""
    padrao_emissao      = r"Emissão Período.*?Valores Lançados"
    padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕES.*?RELATÓRIO DE TRANSAÇÕES"
    padrao_pagina       = r"Página:\s*\d+\s*de\s*\d+"
    cabecalho_colunas   = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

    progress = st.progress(0)
    status   = st.empty()
    total_transacoes = 0

    # Arquivo de saída também no disco
    tmp_saida = tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                            encoding='utf-8', delete=False)
    tmp_saida.write(CABECALHO + "\n")

    try:
        with pdfplumber.open(caminho_pdf_disco) as pdf:
            total = len(pdf.pages)

            for lote_inicio in range(0, total, TAMANHO_LOTE):
                lote_fim = min(lote_inicio + TAMANHO_LOTE, total)

                for i in range(lote_inicio, lote_fim):
                    status.info(f"🔄 Página **{i + 1}** de **{total}**...")

                    try:
                        conteudo = pdf.pages[i].extract_text()
                    except Exception:
                        conteudo = None

                    if conteudo:
                        conteudo = re.sub(padrao_emissao, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                        conteudo = re.sub(padrao_detalhamento, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                        conteudo = re.sub(padrao_pagina, "", conteudo, flags=re.IGNORECASE)
                        conteudo = conteudo.replace(cabecalho_colunas, "")
                        conteudo = re.sub(r'\bPGTO\b', '', conteudo)

                        # ✅ Processa e grava linha por linha, sem acumular
                        for linha in conteudo.split('\n'):
                            linha = linha.strip()
                            if not linha or 'PGTO' in linha.upper():
                                continue
                            resultado = parsear_linha(linha)
                            if resultado:
                                tmp_saida.write(resultado + "\n")
                                total_transacoes += 1

                    progress.progress(int(((i + 1) / total) * 100))

                gc.collect()  # libera memória a cada lote

        tmp_saida.close()
        status.success(f"✅ Concluído! {total} páginas | {total_transacoes} transações.")

        # Lê só para retornar — arquivo pequeno (só dados parseados)
        with open(tmp_saida.name, 'r', encoding='utf-8') as f:
            conteudo_final = f.read()

        return conteudo_final

    except Exception as e:
        st.error(f"Erro: {e}")
        return None
    finally:
        tmp_saida.close()
        if os.path.exists(tmp_saida.name):
            os.unlink(tmp_saida.name)


def main():
    st.set_page_config(page_title="Extrator de Dados PDF", page_icon="📄")
    st.title("📄 Extrator de Dados (Limpeza de Relatório)")
    st.write("Gere um arquivo .txt limpo, sem cabeçalhos e paginação.")

    if 'texto_final' not in st.session_state:
        st.session_state.texto_final = None
    if 'nome_arquivo' not in st.session_state:
        st.session_state.nome_arquivo = None

    arquivo_carregado = st.file_uploader("Escolha o arquivo PDF", type="pdf")

    if arquivo_carregado:
        st.success(f"Arquivo '{arquivo_carregado.name}' carregado!")

        if st.button("Processar e Extrair Dados"):

            # ✅ Salva o PDF no disco antes de processar
            tmp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp_pdf.write(arquivo_carregado.read())
            tmp_pdf.close()

            try:
                resultado = extrair_texto_pdf(tmp_pdf.name)
                if resultado:
                    st.session_state.texto_final = resultado
                    st.session_state.nome_arquivo = arquivo_carregado.name.replace(".pdf", "_extraido.txt")
            finally:
                # ✅ Remove o PDF temporário do disco
                if os.path.exists(tmp_pdf.name):
                    os.unlink(tmp_pdf.name)

    if st.session_state.texto_final:
        total_linhas = len(st.session_state.texto_final.splitlines()) - 1
        st.info(f"📊 {total_linhas} transações prontas para download.")
        st.text_area("Prévia:", st.session_state.texto_final[:3000], height=200)

        st.download_button(
            label="📥 Baixar arquivo .txt",
            data=st.session_state.texto_final.encode("utf-8"),
            file_name=st.session_state.nome_arquivo,
            mime="text/plain"
        )

if __name__ == "__main__":
    main()
