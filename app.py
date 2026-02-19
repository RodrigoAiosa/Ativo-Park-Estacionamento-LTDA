import streamlit as st
import pdfplumber
import re

CABECALHO = "Caixa;Transação;T. Fiscais;Sessão;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lançado;Ticket;Forma PGTO"

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
    else:
        return None  # ✅ Retorna None para linhas que não parsearem (serão descartadas)

def extrair_texto_pdf(arquivo_pdf):
    try:
        texto_acumulado = ""

        padrao_emissao      = r"Emissão Período.*?Valores Lançados"
        padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕES.*?RELATÓRIO DE TRANSAÇÕES"
        padrao_pagina       = r"Página:\s*\d+\s*de\s*\d+"
        cabecalho_colunas   = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

        with pdfplumber.open(arquivo_pdf) as pdf:
            total = len(pdf.pages)
            progress = st.progress(0)
            status   = st.empty()  # ✅ Placeholder para mostrar página atual

            for i, pagina in enumerate(pdf.pages):
                # ✅ Atualiza o status com a página sendo processada
                status.info(f"🔄 Processando página **{i + 1}** de **{total}**...")

                conteudo = pagina.extract_text()

                if conteudo:
                    conteudo = re.sub(padrao_emissao, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                    conteudo = re.sub(padrao_detalhamento, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                    conteudo = re.sub(padrao_pagina, "", conteudo, flags=re.IGNORECASE)
                    conteudo = conteudo.replace(cabecalho_colunas, "")
                    conteudo = re.sub(r'\bPGTO\b', '', conteudo)
                    texto_acumulado += conteudo + "\n"

                percent = int(((i + 1) / total) * 100)
                progress.progress(percent)

            status.success(f"✅ Concluído! {total} páginas processadas.")

        # ✅ Filtra linhas que contêm "PGTO" e as descarta
        linhas_brutas = [
            l.strip() for l in texto_acumulado.split('\n')
            if l.strip() and 'PGTO' not in l.upper()
        ]

        linhas_processadas = [CABECALHO]  # ✅ Cabeçalho na primeira linha

        for linha in linhas_brutas:
            resultado = parsear_linha(linha)
            if resultado:  # ✅ Só adiciona se o parse foi bem-sucedido
                linhas_processadas.append(resultado)

        return "\n".join(linhas_processadas)

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
                st.success(f"✅ {len(resultado.splitlines()) - 1} transações extraídas!")

    if st.session_state.texto_final:
        st.text_area("Prévia dos dados limpos:", st.session_state.texto_final, height=250)

        st.download_button(
            label="📥 Baixar arquivo .txt",
            data=st.session_state.texto_final.encode("utf-8"),
            file_name=st.session_state.nome_arquivo,
            mime="text/plain"
        )


if __name__ == "__main__":
    main()
