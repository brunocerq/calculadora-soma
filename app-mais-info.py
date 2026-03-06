import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

# Configuração da página
st.set_page_config(page_title="Calculadora de Reconciliação", page_icon="logo.svg", layout="wide")

# Logo alinhado à esquerda e com largura bloqueada a 250 pixeis
st.image("logo.svg", width=250)

st.title("Otimização de Reconciliação")
st.write("A aplicação irá processar os dois conjuntos (Amarelos e Cor-de-Rosa) em simultâneo e extrair os elementos NÃO USADOS em duas tabelas lado a lado.")

# Função auxiliar para limpar e preparar os dados
def preparar_dados(df, col_data, col_desc, col_valor):
    df_subset = df.iloc[:, [col_data, col_desc, col_valor]].copy()
    df_subset.columns = ['Diário/Data', 'Descrição', 'ValorOriginal']
    
    # Forçar a coluna de data/diário e descrição a serem SEMPRE tratadas como texto puro
    df_subset['Diário/Data'] = df_subset['Diário/Data'].astype(str).replace('nan', '')
    df_subset['Descrição'] = df_subset['Descrição'].astype(str).replace('nan', '')
    
    # O TRITURADOR PT-PT
    df_subset['ValorNum'] = pd.to_numeric(df_subset['ValorOriginal'].astype(str).str.replace(',', '.'), errors='coerce')
    
    df_limpo = df_subset.dropna(subset=['ValorNum']).reset_index(drop=True)
    return df_limpo

# Função principal do motor matemático com junção Lado a Lado
def otimizar_conjunto(df_lista1, df_lista2, nome_lado1, nome_lado2):
    A_vals = df_lista1['ValorNum'].tolist()
    B_vals = df_lista2['ValorNum'].tolist()

    A_ints = np.array([int(round(x * 100)) for x in A_vals])
    B_ints = np.array([int(round(x * 100)) for x in B_vals])

    n = len(A_ints)
    m = len(B_ints)

    if n == 0 or m == 0:
        return False, 0, n, m, pd.DataFrame()

    c = np.zeros(n + m)
    c[:n] = -A_ints

    A_eq = np.zeros((1, n + m))
    A_eq[0, :n] = A_ints
    A_eq[0, n:] = -B_ints

    bounds = Bounds(np.zeros(n + m), np.ones(n + m))
    integrality = np.ones(n + m)
    constraints = LinearConstraint(A_eq, 0, 0)

    res = milp(c=c, constraints=constraints, integrality=integrality, bounds=bounds)

    if res.success:
        x_res = np.round(res.x[:n])
        y_res = np.round(res.x[n:])
        
        selected_A = [A_vals[i] for i in range(n) if x_res[i] == 1]
        soma_max = sum(selected_A)
        
        # Isolar os NÃO USADOS
        nao_usados_A = df_lista1.loc[x_res == 0, ['ValorOriginal', 'Diário/Data', 'Descrição']].copy()
        nao_usados_B = df_lista2.loc[y_res == 0, ['ValorOriginal', 'Diário/Data', 'Descrição']].copy()
        
        # Renomear colunas para ter a distinção de quem é quem (Ex: Valor A, Data A, etc.)
        nao_usados_A.columns = [f'Valor {nome_lado1}', f'Diário/Data {nome_lado1}', f'Descrição {nome_lado1}']
        nao_usados_B.columns = [f'Valor {nome_lado2}', f'Diário/Data {nome_lado2}', f'Descrição {nome_lado2}']
        
        # Resetar o índice para que as duas listas comecem na linha 0 e fiquem perfeitamente alinhadas
        nao_usados_A.reset_index(drop=True, inplace=True)
        nao_usados_B.reset_index(drop=True, inplace=True)
        
        # Juntar Lado a Lado (axis=1) em vez de empilhar
        df_final_nao_usados = pd.concat([nao_usados_A, nao_usados_B], axis=1)
        
        # Limpar os campos vazios gerados por diferenças de tamanho nas listas
        df_final_nao_usados.fillna('', inplace=True)
        
        return True, soma_max, n, m, df_final_nao_usados
    else:
        return False, 0, n, m, pd.DataFrame()

ficheiro_carregado = st.file_uploader("Escolha o ficheiro Excel gerado pela macro", type=["csv", "xlsx", "xls", "xlsm"])

if ficheiro_carregado is not None:
    try:
        if ficheiro_carregado.name.endswith('.csv'):
            df = pd.read_csv(ficheiro_carregado, header=None)
        else:
            df = pd.read_excel(ficheiro_carregado, header=None)
            
        if df.shape[1] < 41:
            st.error("Atenção: O ficheiro carregado não possui colunas suficientes. Certifique-se de que usou a nova Macro VBA que extrai até à coluna AO.")
        else:
            st.success("Ficheiro validado! A iniciar o cálculo matemático para ambos os conjuntos...")
            
            with st.spinner("A processar a otimização dupla..."):
                
                # PREPARAÇÃO
                df_A = preparar_dados(df, 26, 27, 28)
                df_B = preparar_dados(df, 30, 31, 32)
                
                df_A1 = preparar_dados(df, 34, 35, 36)
                df_B1 = preparar_dados(df, 38, 39, 40)
                
                # EXECUÇÃO DA MATEMÁTICA (Enviamos os nomes para o cabeçalho)
                sucesso_1, soma_1, n_A, n_B, df_nao_usados_1 = otimizar_conjunto(df_A, df_B, "A", "B")
                sucesso_2, soma_2, n_A1, n_B1, df_nao_usados_2 = otimizar_conjunto(df_A1, df_B1, "A1", "B1")
                
                st.write("---")
                col_esq, col_dir = st.columns(2)
                
                # PAINEL ESQUERDO: Conjunto 1
                with col_esq:
                    st.subheader("🟡 Conjunto 1 (A vs B)")
                    if sucesso_1:
                        st.write(f"**Maior Soma Encontrada:** {soma_1:.2f}")
                        st.write(f"**Total de elementos analisados:** {n_A} (Lista A) e {n_B} (Lista B)")
                        st.write("**Descarregue o ficheiro para ver os elementos NÃO USADOS (expurgados).**")
                        
                        csv_1 = df_nao_usados_1.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descarregar CSV (A e B)",
                            data=csv_1,
                            file_name="Nao_Usados_Conjunto1_Amarelos.csv",
                            mime="text/csv",
                            key="btn_conj1"
                        )
                    else:
                        st.warning("Não foi possível otimizar este conjunto.")
                
                # PAINEL DIREITO: Conjunto 2
                with col_dir:
                    st.subheader("🟣 Conjunto 2 (A1 vs B1)")
                    if sucesso_2:
                        st.write(f"**Maior Soma Encontrada:** {soma_2:.2f}")
                        st.write(f"**Total de elementos analisados:** {n_A1} (Lista A1) e {n_B1} (Lista B1)")
                        st.write("**Descarregue o ficheiro para ver os elementos NÃO USADOS (expurgados).**")
                        
                        csv_2 = df_nao_usados_2.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descarregar CSV (A1 e B1)",
                            data=csv_2,
                            file_name="Nao_Usados_Conjunto2_Cor_de_Rosa.csv",
                            mime="text/csv",
                            key="btn_conj2"
                        )
                    else:
                        st.warning("Não foi possível otimizar este conjunto.")

    except Exception as e:
        st.error(f"Ocorreu um erro técnico ao ler o ficheiro: {e}")
