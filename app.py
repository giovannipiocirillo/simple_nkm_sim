import streamlit as st
import numpy as np
import subprocess
import glob
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.io import loadmat

st.set_page_config(page_title="Simple NKM DSGE Simulator", layout="wide")

# --- INIEZIONE CSS PER LA BARRA LATERALE A TUTTO SCHERMO ---
st.markdown("""
    <style>
        /* Forza la barra laterale ad allungarsi per tutta l'altezza della finestra (100vh) */
        [data-testid="stSidebar"] {
            height: 100vh !important;
            min-width: 350px !important; /* La rende un po' più larga per i testi lunghi */
        }
        
        /* Assicura che il contenuto interno sia scrollabile se supera l'altezza */
        [data-testid="stSidebarUserContent"] {
            height: 100% !important;
            overflow-y: auto !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Simulatore NKM DSGE")
st.markdown("Imposta i parametri, scegli lo shock e clicca su **Aggiungi scenario** per stimare l'impatto di uno shock macroeconomico")

# --- INIZIALIZZAZIONE DELLA MEMORIA (SESSION STATE) ---
if 'scenari' not in st.session_state:
    st.session_state.scenari = []

nomi_variabili = {
    'y': 'Output (y)', 'pi': 'Inflazione (π)', 'r': 'Tasso di Interesse (r)', 
    'w': 'Salario (w)', 'mc': 'Costo Marginale (mc)', 'l': 'Lavoro (l)', 
    'c': 'Consumo (c)', 'a': 'Produttività (a)', 'is': 'Shock Monetario (is)'
}

# --- LINK ALLA TEORIA ---
url_pdf = "https://github.com/giovannipiocirillo/simple_nkm_sim/blob/main/nkm_theory_ita.pdf"
st.sidebar.markdown(
    f"""
    <a href="{url_pdf}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #d1d5db; margin-bottom: 15px; margin-top: 10px;">
            📖 <b>Spiegazione del modello (PDF)</b>
        </div>
    </a>
    """, 
    unsafe_allow_html=True
)

# --- BARRA LATERALE: FORM DI INSERIMENTO ---
with st.sidebar.form("pannello_controllo"):
    st.subheader("1. Impostazioni Shock e Grafici")
    tipo_shock = st.selectbox("Tipo di Shock:", ["Shock Tecnologico (eps)", "Shock Monetario (ms)"])
    intensita_shock = st.number_input("Intensità dello shock:", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    trimestri = st.slider("Orizzonte temporale (trimestri):", min_value=10, max_value=100, value=40, step=5)

    variabili_scelte = st.multiselect(
        "Variabili da osservare:",
        options=list(nomi_variabili.keys()),
        default=['a', 'mc', 'w', 'pi', 'r', 'c', 'y'],
        format_func=lambda x: nomi_variabili[x]
    )

    st.divider()
    st.subheader("2. Parametri strutturali")
    beta = st.slider(
        "β - Fattore di sconto del consumo", 
        min_value=0.90, max_value=0.99, value=0.99, step=0.01,
        help="Esprime la preferenza della famiglie per il consumo futuro (“pazienza” delle famiglie)."
    )
    
    gamma = st.slider(
        "γ - Inverso della Frisch elasticity", 
        min_value=0.1, max_value=3.0, value=1.0, step=0.1,
        help="Misura la variazione dell’offerta di lavoro al variare del salario. Pertanto, maggiore è la propensione delle famiglie nell’offrire lavoro all’aumentare del salario, maggiore è la Frisch Elasticity e minore è γ."
    )
    
    omega = st.slider(
        "ω - Stickiness parameter", 
        min_value=0.01, max_value=1.0, value=0.75, step=0.01,
        help="Il parametro ω (stickiness parameter) può essere interpretato anche come la probabilità che la generica impresa in ogni periodo t sia caratterizzata da prezzi vischiosi: questa ipotesi è la fonte delle rigidità nominali nel modello NKM.\n\nPer determinare l’indice aggregato dei prezzi nell’economia si può introdurre una semplice regola di Calvo (Calvo, 1983), per la quale le imprese che non riescono ad ottimizzare i prezzi al tempo t applicheranno il prezzo aggregato del periodo precedente t-1."
    )
    
    rhoa = st.slider(
        "ρ_a - Persistenza shock TFP", 
        min_value=0.01, max_value=0.99, value=0.7, step=0.01
    )
    
    phip = st.slider(
        "φ_π - Taylor parameter", 
        min_value=1.01, max_value=3.0, value=1.5, step=0.1,
        help="Sintetizza il peso assegnato dalla banca centrale all’obiettivo di stabilità dell’inflazione nel proprio mandato. Secondo il principio di Taylor, il valore del Taylor parameter dovrebbe essere maggiore di uno (φ_π > 1), in quanto è opportuno che la banca centrale risponda in modo più che proporzionale agli scostamenti dell’inflazione dal suo livello obiettivo."
    )
    
    rhom = st.slider(
        "ρ_m - Persistenza shock monetario", 
        min_value=0.01, max_value=0.95, value=0.5, step=0.01
    )

    btn_aggiungi = st.form_submit_button("➕ Aggiungi scenario", type="primary", use_container_width=True)

# --- BARRA LATERALE: GESTIONE SCENARI ---
st.sidebar.subheader("3. Scenari salvati")

if len(st.session_state.scenari) > 0:
    for i, scenario in enumerate(st.session_state.scenari):
        col_nome, col_elimina = st.sidebar.columns([5, 1])
        col_nome.markdown(f"<span style='font-size:0.9em;'>{scenario['nome']}</span>", unsafe_allow_html=True)
        
        if col_elimina.button("❌", key=f"elimina_{i}", help="Rimuovi questo scenario"):
            st.session_state.scenari.pop(i)
            st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("🗑️ Rimuovi tutti gli scenari", use_container_width=True):
        st.session_state.scenari = []
        st.rerun()
else:
    st.sidebar.info("Nessuno scenario attualmente salvato.")

# --- ESECUZIONE MODELLO ---
if btn_aggiungi:
    var_eps = intensita_shock if "Tecnologico" in tipo_shock else 0.0
    var_ms = intensita_shock if "Monetario" in tipo_shock else 0.0

    mod_content = f"""
    % NKM Linearizzato
    var lambda c w l r pi mc a y is;
    varexo eps ms;
    parameters GAMMA OMEGA BETA KAPPA PHIP RHOA RHOM;
    
    GAMMA = {gamma};
    OMEGA = {omega};
    BETA = {beta};
    KAPPA = (1-OMEGA)*(1-(BETA*OMEGA))/(OMEGA);
    PHIP = {phip};
    RHOA = {rhoa};
    RHOM = {rhom};

    model(linear);
    lambda = -c;
    w = (GAMMA*l) - lambda;
    lambda = lambda(+1) + r - pi(+1);
    w = mc + a;
    y = a + l;
    y = c;
    a = RHOA*a(-1) + eps;
    r = (PHIP*pi) + is;
    is = (RHOM*is(-1)) + ms;
    pi = (KAPPA*mc) + (BETA*pi(+1));
    end;

    steady; check;

    shocks;
    var eps = {var_eps};
    var ms = {var_ms};
    end;

    stoch_simul(irf={trimestri}, noprint, nograph);
    """
    
    with open("NKM_lin.mod", "w") as f:
        f.write(mod_content)

    with st.spinner("Calcolo con Dynare in corso..."):
        comando_octave = "addpath('/usr/lib/dynare/matlab'); dynare NKM_lin.mod;"
        process = subprocess.run(["octave", "--no-gui", "--eval", comando_octave], capture_output=True, text=True)
        
    try:
        file_risultati = glob.glob("**/NKM_lin_results.mat", recursive=True)
        if not file_risultati:
            raise FileNotFoundError("Il file NKM_lin_results non è stato trovato!")
            
        mat_data = loadmat(file_risultati[0])
        irfs = mat_data['oo_'][0, 0]['irfs'][0, 0]
        
        irf_dict = {}
        for campo in irfs.dtype.names:
            irf_dict[campo] = np.round(irfs[campo].flatten(), 4)
            
        num_scenari_totali = len(st.session_state.scenari) + 1
        
        # MODIFICA 1: Ora inseriamo TUTTI i parametri nella stringa del nome, abbreviando "Scen." in "S" per salvare spazio
        nome_scenario = f"S{num_scenari_totali}: {tipo_shock[:8]} (β={beta}, γ={gamma}, ω={omega}, ρ_a={rhoa}, φ_π={phip}, ρ_m={rhom})"
        
        st.session_state.scenari.append({
            'nome': nome_scenario,
            'dati': irf_dict,
            'tempo': np.arange(trimestri),
            'suffisso': '_ms' if "Monetario" in tipo_shock else '_eps'
        })
        
        st.rerun()
        
    except Exception as e:
        st.error(f"Errore durante l'estrazione dei dati: {e}")
        st.code(process.stdout)

# --- VISUALIZZAZIONE GRAFICI INTERATTIVI (PLOTLY) E DOWNLOAD DATI ---
if len(st.session_state.scenari) > 0 and len(variabili_scelte) > 0:
    st.subheader(f"Confronto Scenari ({trimestri} trimestri)")
    
    num_vars = len(variabili_scelte)
    cols_count = min(3, num_vars)
    rows_count = ((num_vars - 1) // 3) + 1
    
    titoli_subplot = [nomi_variabili[v] for v in variabili_scelte]
    fig = make_subplots(rows=rows_count, cols=cols_count, subplot_titles=titoli_subplot)
    
    colori = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for idx, var in enumerate(variabili_scelte):
        riga = (idx // 3) + 1
        colonna = (idx % 3) + 1
        
        for j, scenario in enumerate(st.session_state.scenari):
            chiave_irf = f"{var}{scenario['suffisso']}"
            if chiave_irf in scenario['dati']:
                mostra_legenda = True if idx == 0 else False
                
                fig.add_trace(go.Scatter(
                    x=scenario['tempo'],
                    y=scenario['dati'][chiave_irf],
                    mode='lines+markers',
                    name=scenario['nome'],
                    legendgroup=scenario['nome'],
                    showlegend=mostra_legenda,
                    line=dict(color=colori[j % len(colori)]),
                    marker=dict(size=6)
                ), row=riga, col=colonna)
        
        fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1, row=riga, col=colonna)
        fig.update_xaxes(title_text="Trimestri", row=riga, col=colonna)

    altezza_totale = max(400, 300 * rows_count)
    fig.update_layout(
        height=altezza_totale, 
        margin=dict(t=50, l=20, r=20, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 2. GENERAZIONE TABELLA DATI PER IL DOWNLOAD
    st.divider()
    st.markdown("### 📥 Esporta Dati")
    
    df_lista = []
    for scenario in st.session_state.scenari:
        df_temp = pd.DataFrame({'Trimestre': scenario['tempo']})
        
        # MODIFICA 2: Aggiunto il rimpiazzo per TUTTE le nuove lettere greche usate nella stringa
        nome_csv_pulito = scenario['nome'].replace("ω", "omega").replace("φ_π", "phi_pi").replace("π", "pi")\
                                          .replace("β", "beta").replace("γ", "gamma").replace("ρ_a", "rho_a").replace("ρ_m", "rho_m")
        
        for var in variabili_scelte:
            chiave_irf = f"{var}{scenario['suffisso']}"
            if chiave_irf in scenario['dati']:
                nome_colonna = f"[{nome_csv_pulito}] {var}"
                df_temp[nome_colonna] = scenario['dati'][chiave_irf]
                
        df_temp = df_temp.set_index('Trimestre')
        df_lista.append(df_temp)
        
    if df_lista:
        df_finale = pd.concat(df_lista, axis=1)
        
        csv = df_finale.to_csv().encode('utf-8')
        
        st.download_button(
            label="Scarica Dati in CSV",
            data=csv,
            file_name="simulazione_NKM_DSGE.csv",
            mime="text/csv",
        )

elif len(st.session_state.scenari) == 0:
    st.info("👈 Imposta i parametri nel form laterale e clicca su 'Aggiungi Scenario' per iniziare la simulazione.")
elif len(variabili_scelte) == 0:
    st.warning("👈 Seleziona almeno una variabile da osservare nel menu a tendina.")
