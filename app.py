import streamlit as st
import fitz
import re
import gc
import tempfile
import os

CABECALHO = "Caixa;Transacao;T. Fiscais;Sessao;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lancado;Ticket;Forma PGTO"

def limpar_valor(v):
    return v.strip().replace("R$ ", "R$")

def parsear_linha(linha):
    linha = re.sub(r'\bPGTO\b', '', linha).strip()
    padrao = re.compile(
        r'^(\S.*?)\s+'
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
        return ";".join([
            m.group(1),
            m.group(7),
            m.group(5),
            m.group(4),
            m.group(2) + " " + m.group(3),
            limpar_valor(m.group(11)),
            limpar_valor(m.group(9)),
            m.group(6),
            "R$0.00",
            limpar_valor(m.group(8)),
            "",
            m.group(10),
        ])
    return None

def processar_pdf(caminho_pdf):
    progress = st.progress(0)
    status   = st.empty()
    total_transacoes = 0

    tmp_saida = tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                            encoding='utf-8', delete=False)
    tmp_saida.write(CABECALHO + "\n")

    # Guarda amostra das primeiras linhas brutas para debug
    amostra_pg2 = []

    try:
        doc   = fitz.open(caminho_pdf)
        total = len(doc)

        for i in range(total):
            status.info(f"Pagina {i + 1} de {total}...")

            try:
                # Tenta extrair como "words" para reconstruir linhas com coordenadas
                page = doc[i]
                blocks = page.get_text("blocks")
                linhas_pagina = []
                for b in blocks:
                    texto_bloco = b[4].strip()
                    if texto_bloco:
                        # Cada bloco pode ter multiplas linhas
                        for l in texto_bloco.split('\n'):
                            l = l.strip()
                            if l:
                                linhas_pagina.append(l)

            except Exception:
                linhas_pagina = []

            # Captura pagina 2 para debug (pagina 1 é cabecalho)
            if i == 1 and not amostra_pg2:
                amostra_pg2 = linhas_pagina[:30]

            for linha in linhas_pagina:
                if not linha:
                    continue
                resultado = parsear_linha(linha)
                if resultado:
                    tmp_saida.write(resultado + "\n")
                    total_transacoes += 1

            if i % 50 == 0:
                gc.collect()

            progress.progress(int(((i + 1) / total) * 100))

        doc.close()
        tmp_saida.close()
        status.success(f"Concluido! {total} paginas | {total_transacoes} transacoes.")

        # Se 0 transacoes, mostra diagnostico
        if total_transacoes == 0:
            st.warning("0 transacoes encontradas. Amostra das linhas brutas da pagina 2:")
            st.code("\n".join(amostra_pg2))
            return None

        with open(tmp_saida.name, 'r', encoding='utf-8') as f:
            return f.read()

    except Exception as e:
        st.error(f"Erro: {e}")
        return None
    finally:
        try:
            tmp_saida.close()
        except Exception:
            pass
        if os.path.exists(tmp_saida.name):
            os.unlink(tmp_saida.name)


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
