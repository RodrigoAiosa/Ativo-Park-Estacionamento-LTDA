import streamlit as st
import PyPDF2
import re

def extrair_texto_pdf(arquivo_pdf):
    try:
        leitor = PyPDF2.PdfReader(arquivo_pdf)
        texto_acumulado = ""
        
        # Padrões para limpeza
        padrao_emissao = r"Emissão Período.*Valores Lançados"
        padrao_detalhamento = r"DETALHAMENTO DAS TRANSAÇÕESRELATÓRIO DE TRANSAÇÕES"
        padrao_pagina = r"Página:\s*\d+\s*de\s*\d+"
        cabecalho_colunas = "Caixa V. Lançado Data Tarifa V. Estadia Ticket V. Abonado Transação T. Fiscais Sessão Abono Forma"

        for i in range(len(leitor.pages)):
            pagina = leitor.pages[i]
            conteudo = pagina.extract_text()
            
            if conteudo:
                # 1. Remove blocos de cabeçalho de emissão (usando flags para multilinhas)
                conteudo = re.sub(padrao_emissao, "", conteudo, flags=re.DOTALL | re.IGNORECASE)
                
                # 2. Remove títulos do relatório
                conteudo = re.sub(padrao_detalhamento, "", conteudo, flags=re.IGNORECASE)
                
                # 3. Remove "Página: X de Y"
                conteudo = re.sub(padrao_pagina, "", conteudo, flags=re.IGNORECASE)
                
                # 4. Remove o cabeçalho das colunas
                conteudo = conteudo.replace(cabecalho_colunas, "")
                
                texto_acumulado += conteudo + "\n"

        # Limpeza final: remove linhas em branco extras e espaços inúteis
        linhas = [linha.strip() for linha in texto_acumulado.split('\n') if linha.strip()]
        return "\n".join(linhas)

    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        return None

def main():
    st.set_page_config(page_title="Extrator de Dados PDF", page_icon="📄")
    
    st.title("📄 Extrator de Dados (Limpeza de Relatório)")
    st.write("Upload do PDF para gerar um arquivo .txt limpo, sem cabeçalhos e paginação.")

    arquivo_carregado = st.file_uploader("Escolha o arquivo PDF", type="pdf")

    if arquivo_carregado is not None:
        st.success(f"Arquivo '{arquivo_carregado.name}' carregado!")
        
        if st.button("Processar e Extrair Dados"):
            with st.spinner('Limpando e extraindo...'):
                texto_limpo = extrair_texto_pdf(arquivo_carregado)
                
                if texto_limpo:
                    st.text_area("Visualização dos dados extraídos:", texto_limpo, height=300)
                    
                    nome_txt = arquivo_carregado.name.replace(".pdf", "_dados_limpos.txt")
                    
                    st.download_button(
                        label="📥 Baixar arquivo .txt final",
                        data=texto_limpo,
                        file_name=nome_txt,
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()
