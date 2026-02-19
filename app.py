import streamlit as st
import pdfplumber
import re

CABECALHO = "Caixa;Transação;T. Fiscais;Sessão;Data;Tarifa;V. Estadia;Abono;V. Abonado;V. Lançado;Ticket;Forma PGTO"

def limpar_valor(v):
    """Remove R$, espaços extras e normaliza o valor."""
    return v.strip().replace("R$ ", "R$")

def parsear_linha(linha):
    """
    Tenta quebrar a linha extraída do PDF nas 12 colunas esperadas.
    Formato identificado na prévia:
    PORTO 09/06/25 17:13:33 caixa buzios 1 3 100516061973 R$ 30.00 R$ 30.00 Porto R$ 0.00
    Caixa | Data | Hora(junto à data) | Sessão | T.Fiscais | Transação | V.Lançado | V.Estadia | V.Abonado | Ticket | Forma | Tarifa
    """
    # Remove "PGTO" solto no início ou fim
    linha = re.sub(r'\bPGTO\b', '', linha).strip()

    # Padrão para capturar os campos
    padrao = re.compile(
        r'^(\S+)\s+'                        # Caixa
        r'(\d{2}/\d{2}/\d{2})\s+'          # Data
        r'(\d{2}:\d{2}:\d{2})\s+'          # Hora (será juntada à data)
        r'(.+?)\s+'                         # Sessão (texto livre)
        r'(\d+)\s+'                         # T. Fiscais
        r'(\d+)\s+'                         # Abono
        r'(\d{9,})\s+'                      # Transação (número longo)
        r'(R\$\s*[\d.]+)\s+'               # V. Lançado
        r'(R\$\s*[\d.]+)\s+'               # V. Estadia
        r'(\S+)\s+'                         # Forma PGTO
        r'(R\$\s*[\d.]+)$'                 # Tarifa
    )

    m = padrao.match(linha)
    if m:
        caixa       = m.group(1)
        data        = m.group(2) + " " + m.group(3)
        sessao      = m.group(4)
        t_fiscais   = m.group(5)
        abono       = m.group(6)
        transacao   = m.group(7)
        v_lancado   = limpar_valor(m.group(8))
        v_estadia   = limpar_valor(m.group(9))
        forma_pgto  = m.group(10)
        tarifa      = limpar_valor(m.group(11))
        v_abonado   = "R$0.00"  # campo não visível na linha, colocar vazio ou padrão

        return ";".join([caixa, transacao, t_fiscais, sessao, data, tarifa,
                         v_estadia, abono, v_abonado, v_lancado, "", forma_pgto])
    else:
        # Retorna a linha original se não conseguir parsear
        return linha

def extrair_texto_pdf(arquivo_pdf):
    try:
        texto_acumulado = ""

        padrao_emissao      = r"Emissão Período.*?Valores Lançados"
        padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕES.*?RELATÓRIO DE TRANSAÇÕES"
        padrao_pagina       = r"Página:\s*\d+\s*de\s*\d+"
        cabecalho_colunas   = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

        with pdfplumber.open(arquivo_pdf) as pdf:
            total = len(pdf.pages)
            progress = st.progress(0, text="Iniciando extração...")

            for i, pagina in enumerate(pdf.pages):
                conteudo = pagina.extract_text()

                if conteudo:
                    conteudo = re.sub(padrao_emissao, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                    conteudo = re.sub(padrao_detalhamento, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                    conteudo = re.sub(padrao_pagina, "", conteudo, flags=re.IGNORECASE)
                    conteudo = conteudo.replace(cabecalho_colunas, "")
                    conteudo = re.sub(r'\bPGTO\b', '', conteudo)
                    texto_acumulado += conteudo + "\n"

                percent = int(((i + 1) / total) * 100)
                progress.progress(percent, text=f"Processando página {i+1} de {total}...")

            progress.progress(100, text="Extração concluída!")

        # Processa linha a linha
        linhas_brutas = [l.strip() for l in texto_acumulado.split('\n') if l.strip()]
        linhas_processadas = [CABECALHO]

        for linha in linhas_brutas:
            linhas_processadas.append(parsear_linha(linha))

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
                st.success(f"✅ Processamento concluído! {len(resultado.splitlines())} linhas extraídas.")

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
