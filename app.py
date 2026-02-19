import streamlit as st
import pdfplumber
import re

def extrair_texto_pdf(arquivo_pdf):
    try:
        texto_acumulado = ""
        
        padrao_emissao = r"Emissão Período.*?Valores Lançados"
        padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕES.*?RELATÓRIO DE TRANSAÇÕES"
        padrao_pagina = r"Página:\s*\d+\s*de\s*\d+"
        cabecalho_colunas = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

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
                    texto_acumulado += conteudo + "\n"

                percent = int(((i + 1) / total) * 100)
                progress.progress(percent, text=f"Processando página {i+1} de {total}...")

            progress.progress(100, text="Extração concluída!")

        linhas = [linha.strip() for linha in texto_acumulado.split('\n') if linha.strip()]
        return "\n".join(linhas)

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
```

Você precisa instalar o pdfplumber no seu ambiente Streamlit. No arquivo `requirements.txt` do seu projeto, substitua ou adicione:
```
pdfplumber
