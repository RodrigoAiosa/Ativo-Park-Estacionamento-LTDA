import streamlit as st
import pdfplumber
import re
import gc
import tempfile
import os

CABECALHO = "Caixa;Transação;T. Fiscais;Sessão;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lançado;Ticket;Forma PGTO"
TAMANHO_LOTE = 30

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
        v_abonado  = "R$0.00"

        return ";".join([caixa, transacao, t_fiscais, sessao, data, tarifa,
                         v_estadia, abono, v_abonado, v_lancado, "", forma_pgto])
    return None

def extrair_texto_pdf(arquivo_pdf):
    try:
        padrao_emissao      = r"Emissão Período.*?Valores Lançados"
        padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕES.*?RELATÓRIO DE TRANSAÇÕES"
        padrao_pagina       = r"Página:\s*\d+\s*de\s*\d+"
        cabecalho_colunas   = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

        progress = st.progress(0)
        status   = st.empty()
        total_transacoes = 0

        # ✅ Grava direto em arquivo temporário no disco — não usa RAM
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                          encoding='utf-8', delete=False)
        tmp.write(CABECALHO + "\n")

        with pdfplumber.open(arquivo_pdf) as pdf:
            total = len(pdf.pages)

            for lote_inicio in range(0, total, TAMANHO_LOTE):
                lote_fim   = min(lote_inicio + TAMANHO_LOTE, total)
                texto_lote = ""

                for i in range(lote_inicio, lote_fim):
                    status.info(f"🔄 Processando página **{i + 1}** de **{total}**...")

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
                        texto_lote += conteudo + "\n"

                    progress.progress(int(((i + 1) / total) * 100))

                # ✅ Processa lote e grava no disco imediatamente
                for linha in texto_lote.split('\n'):
                    linha = linha.strip()
                    if not linha or 'PGTO' in linha.upper():
                        continue
                    resultado = parsear_linha(linha)
                    if resultado:
                        tmp.write(resultado + "\n")
                        total_transacoes += 1

                # ✅ Libera memória do lote
                del texto_lote
                gc.collect()

        tmp.close()
        status.success(f"✅ Concluído! {total} páginas | {total_transacoes} transações extraídas.")

        # ✅ Lê o arquivo do disco só no final para o download
        with open(tmp.name, 'r', encoding='utf-8') as f:
            conteudo_final = f.read()

        os.unlink(tmp.name)  # apaga o arquivo temporário
        return conteudo_final

    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return None


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
            resultado = extrair_texto_pdf(arquivo_carregado)
            if resultado:
                st.session_state.texto_final = resultado
                st.session_state.nome_arquivo = arquivo_carregado.name.replace(".pdf", "_extraido.txt")

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
