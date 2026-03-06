import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# Configuração da página
st.set_page_config(page_title="Calculadora de Reconciliação", page_icon="logo.svg", layout="wide")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Se não tiver o ficheiro logo.svg na mesma pasta, pode comentar a linha abaixo
    st.image("logo.svg", use_container_width=True)

st.title("Otimização de Reconciliação")
st.write("A aplicação irá processar os dois conjuntos (Amarelos e Cor-de-Rosa) em simultâneo e identificar os movimentos não utilizados na soma máxima.")

# Função auxiliar para limpar e preparar os dados de um bloco (3 colunas)
def preparar_dados(df, col_data, col_desc, col_valor):
    # Extrair as 3 colunas baseadas nos índices físicos
    df_subset = df.iloc[:, [col_data, col_desc, col_valor]].copy()
    df_subset.columns = ['Diário/Data', 'Descrição', 'ValorOriginal']
    
    # O TRITURADOR PT-PT: substitui vírgula por ponto para a matemática, mantendo a linha original
    df_subset['ValorNum'] = pd.to_numeric(df_subset['ValorOriginal'].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Remove as linhas onde o valor não é um número válido (ignora os cabeçalhos vazios)
    df_limpo = df_subset.dropna(subset=['ValorNum']).reset_index(drop=True)
    return df_limpo

# Função principal do motor matemático
def otimizar_conjunto(df_lista1, df_lista2):
    A_vals = df_lista1['ValorNum'].tolist()
    B_vals = df_lista2['ValorNum'].tolist()

    A_ints = np.array([int(round(x * 100)) for x in A_vals])
    B_ints = np.array([int(round(x * 100)) for x in B_vals])

    n = len(A_ints)
    m = len(B_ints)

    if n == 0 or m == 0:
        return False, 0, n, m, pd.DataFrame()

    # Configuração da otimização
    c = np.zeros(n + m)
    c[:n] = -A_ints

    A_eq = np.zeros((1, n + m))
    A_eq[0, :n] = A_ints
    A_eq[0, n:] = -B_ints

    bounds = Bounds(np.zeros(n + m), np.ones(n + m))
    integrality = np.ones(n + m)
    constraints = LinearConstraint(A_eq, 0, 0)

    # Executa o cálculo
    res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)

    if res.success:
        x_res = np.round(res.x[:n])
        y_res = np.round(res.x[n:])
        
        # Calcula a soma máxima para apresentar no ecrã
        selected_A = [A_vals[i] for i in range(n) if x_res[i] == 1]
        soma_max = sum(selected_A)
        
        # --- A GRANDE MUDANÇA: EXTRAIR OS NÃO USADOS ---
        # Filtra as linhas onde a variável de decisão é 0 (ficou de fora da soma)
        nao_usados_A = df_lista1.loc[x_res == 0, ['ValorOriginal', 'Diário/Data', 'Descrição']].copy()
        nao_usados_B = df_lista2.loc[y_res == 0, ['ValorOriginal', 'Diário/Data', 'Descrição']].copy()
        
        # Renomeia a coluna do valor para ficar exata ao seu pedido
        nao_usados_A.rename(columns={'ValorOriginal': 'Valor'}, inplace=True)
        nao_usados_B.rename(columns={'ValorOriginal': 'Valor'}, inplace=True)
        
        # Junta os não usados de ambas as listas num só ficheiro final estruturado
        df_final_nao_usados = pd.concat([nao_usados_A, nao_usados_B], ignore_index=True)
        
        return True, soma_max, n, m, df_final_nao_usados
    else:
        return False, 0, n, m, pd.DataFrame()

ficheiro_carregado = st.file_uploader("Escolha o ficheiro Excel gerado pela macro", type=["csv", "xlsx", "xls", "xlsm"])

if ficheiro_carregado is not None:
    try:
        # Lê o ficheiro em modo bruto para respeitar a estrutura física das colunas
        if ficheiro_carregado.name.endswith('.csv'):
            df = pd.read_csv(ficheiro_carregado, header=None)
        else:
            df = pd.read_excel(ficheiro_carregado, header=None)
            
        # Verifica se o ficheiro tem a largura suficiente para as 40 colunas (até AO)
        if df.shape[1] < 41:
            st.error("Atenção: O ficheiro carregado não possui colunas suficientes. Certifique-se de que usou a nova Macro VBA que extrai até à coluna AO.")
        else:
            st.success("Ficheiro validado! A iniciar o cálculo matemático para ambos os conjuntos...")
            
            with st.spinner("A processar a otimização dupla..."):
                
                # PREPARAÇÃO CONJUNTO 1 (Amarelos: A vs B)
                # A -> Data: AA(26), Desc: AB(27), Valor: AC(28)
                # B -> Data: AE(30), Desc: AF(31), Valor: AG(32)
                df_A = preparar_dados(df, 26, 27, 28)
                df_B = preparar_dados(df, 30, 31, 32)
                
                # PREPARAÇÃO CONJUNTO 2 (Cor-de-Rosa: A1 vs B1)
                # A1 -> Data: AI(34), Desc: AJ(35), Valor: AK(36)
                # B1 -> Data: AM(38), Desc: AN(39), Valor: AO(40)
                df_A1 = preparar_dados(df, 34, 35, 36)
                df_B1 = preparar_dados(df, 38, 39, 40)
                
                # EXECUÇÃO DA MATEMÁTICA
                sucesso_1, soma_1, n_A, n_B, df_nao_usados_1 = otimizar_conjunto(df_A, df_B)
                sucesso_2, soma_2, n_A1, n_B1, df_nao_usados_2 = otimizar_conjunto(df_A1, df_B1)
                
                # --- APRESENTAÇÃO DOS RESULTADOS NO ECRÃ ---
                st.write("---")
                col_esq, col_dir = st.columns(2)
                
                # PAINEL ESQUERDO: Conjunto 1 (Amarelos)
                with col_esq:
                    st.subheader("🟡 Conjunto 1 (A vs B)")
                    if sucesso_1:
                        st.write(f"**Maior Soma Encontrada:** {soma_1:.2f}")
                        st.write(f"**Total de elementos analisados:** {n_A} (Lista A) e {n_B} (Lista B)")
                        st.write(f"**Elementos NÃO USADOS (expurgados):** {len(df_nao_usados_1)}")
                        
                        csv_1 = df_nao_usados_1.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descarregar Não Usados - Conj. 1",
                            data=csv_1,
                            file_name="Nao_Usados_Conjunto1.csv",
                            mime="text/csv",
                            key="btn_conj1"
                        )
                    else:
                        st.warning("Não foi possível otimizar este conjunto ou faltam dados.")
                
                # PAINEL DIREITO: Conjunto 2 (Cor-de-Rosa)
                with col_dir:
                    st.subheader("🟣 Conjunto 2 (A1 vs B1)")
                    if sucesso_2:
                        st.write(f"**Maior Soma Encontrada:** {soma_2:.2f}")
                        st.write(f"**Total de elementos analisados:** {n_A1} (Lista A1) e {n_B1} (Lista B1)")
                        st.write(f"**Elementos NÃO USADOS (expurgados):** {len(df_nao_usados_2)}")
                        
                        csv_2 = df_nao_usados_2.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descarregar Não Usados - Conj. 2",
                            data=csv_2,
                            file_name="Nao_Usados_Conjunto2.csv",
                            mime="text/csv",
                            key="btn_conj2"
                        )
                    else:
                        st.warning("Não foi possível otimizar este conjunto ou faltam dados.")

    except Exception as e:
        st.error(f"Ocorreu um erro catastrófico ao ler o ficheiro. Detalhe técnico: {e}")
