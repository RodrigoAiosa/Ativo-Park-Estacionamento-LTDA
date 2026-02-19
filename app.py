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

def limpar_conteudo(conteudo):
    conteudo = re.sub(r'Emiss.o\s+Per.odo.*?Valores\s+Lan.ados', '', conteudo, flags=re.DOTALL | re.IGNORECASE)
    conteudo = re.sub(r'DETALHAMENTO\s+DAS\s+TRANSA..ES.*?RELAT.RIO\s+DE\s+TRANSA..ES', '', conteudo, flags=re.DOTALL | re.IGNORECASE)
    conteudo = re.sub(r'P.gina:\s*\d+\s*de\s*\d+', '', conteudo, flags=re.IGNORECASE)
    conteudo = re.sub(r'Caixa\s+V\.\s*Lan.ado\s+Data\s+Tarifa.*?Abono\s+Forma', '', conteudo, flags=re.DOTALL | re.IGNORECASE)
    conteudo = re.sub(r'^\s*PGTO\s*$', '', conteudo, flags=re.MULTILINE)
    return conteudo

def processar_pdf(caminho_pdf):
    progress         = st.progress(0)
    status           = st.empty()
    total_transacoes = 0
    linhas_resultado = [CABECALHO]

    doc   = fitz.open(caminho_pdf)
    total = len(doc)

    for i in range(total):
        status.info(f"Processando pagina {i + 1} de {total}...")

        try:
            conteudo = doc[i].get_text("text")
        except Exception:
            conteudo = None

        if conteudo:
            conteudo = limpar_conteudo(conteudo)

            for linha in conteudo.split('\n'):
                linha = linha.strip()
                if not linha or linha.upper() == 'PGTO':
                    continue
                resultado = parsear_linha(linha)
                if resultado:
                    linhas_resultado.append(resultado)
                    total_transacoes += 1

        if i % 50 == 0:
            gc.collect()

        progress.progress(int(((i + 1) / total) * 100))

    doc.close()
    gc.collect()

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
