import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import glob
from scipy.io import loadmat

st.set_page_config(page_title="NKM DSGE con Dynare", layout="wide")

st.title("Simulatore NKM DSGE Multiscenario")
st.markdown("Imposta i parametri, scegli lo shock e clicca su **Aggiungi Scenario**. Puoi aggiungere più scenari per confrontarli sugli stessi grafici!")

# --- INIZIALIZZAZIONE DELLA MEMORIA (SESSION STATE) ---
# Qui diciamo a Streamlit di creare un "cassetto" per salvare gli scenari, se non esiste già
if 'scenari' not in st.session_state:
    st.session_state.scenari = []

# Dizionario per tradurre le variabili nei grafici
nomi_variabili = {
    'y': 'Output (y)', 'pi': 'Inflazione (π)', 'r': 'Tasso (r)', 
    'w': 'Salario (w)', 'mc': 'Costo Marg. (mc)', 'l': 'Lavoro (l)', 
    'c': 'Consumo (c)', 'a': 'Produttività (a)', 'is': 'Shock Mon. (is)'
}

# --- BARRA LATERALE: CONTROLLI ---
st.sidebar.header("1. Impostazioni Shock e Grafici")

# Scelta del tipo di shock e intensità
tipo_shock = st.sidebar.radio("Tipo di Shock:", ["Monetario (ms)", "Tecnologico (eps)"])
intensita_shock = st.sidebar.number_input("Intensità dello Shock (Varianza):", min_value=0.01, max_value=10.0, value=1.00, step=0.1)

# Scelta dell'orizzonte temporale
trimestri = st.sidebar.slider("Orizzonte temporale (Trimestri):", min_value=10, max_value=100, value=40, step=5)

# Scelta delle variabili da mostrare
variabili_scelte = st.sidebar.multiselect(
    "Variabili da osservare:",
    options=list(nomi_variabili.keys()),
    default=['y', 'pi', 'r'],
    format_func=lambda x: nomi_variabili[x]
)

st.sidebar.divider()
st.sidebar.header("2. Parametri del Modello")

beta = st.sidebar.slider("β - Fattore di sconto", min_value=0.90, max_value=0.99, value=0.99, step=0.01)
gamma = st.sidebar.slider("γ - Inverso Frisch elasticity", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
omega = st.sidebar.slider("ω - Stickiness parameter", min_value=0.01, max_value=1.0, value=0.75, step=0.01)
rhoa = st.sidebar.slider("ρ_a - Persistenza shock TFP", min_value=0.01, max_value=0.99, value=0.7, step=0.01)
phip = st.sidebar.slider("φ_π - Taylor parameter", min_value=1.01, max_value=3.0, value=1.5, step=0.1)
rhom = st.sidebar.slider("ρ_m - Persistenza shock monetario", min_value=0.01, max_value=0.99, value=0.5, step=0.01)

st.sidebar.divider()

# Bottoni per gestire le simulazioni
col_btn1, col_btn2 = st.sidebar.columns(2)
aggiungi_btn = col_btn1.button("➕ Aggiungi Scenario", type="primary", use_container_width=True)
cancella_btn = col_btn2.button("🗑️ Pulisci", use_container_width=True)

if cancella_btn:
    st.session_state.scenari = []
    st.rerun()

# --- LOGICA DI ESECUZIONE ---
if aggiungi_btn:
    
    # Impostiamo le varianze in base alla scelta dell'utente
    var_eps = intensita_shock if tipo_shock == "Tecnologico (eps)" else 0
    var_ms = intensita_shock if tipo_shock == "Monetario (ms)" else 0
    
    # Generiamo il file .mod dinamicamente
    mod_content = f"""
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
            raise FileNotFoundError("File dei risultati non trovato.")
            
        mat_data = loadmat(file_risultati[0])
        irfs = mat_data['oo_'][0, 0]['irfs'][0, 0]
        
        # Estraiamo tutte le IRF disponibili e le salviamo in un dizionario Python pulito
        irf_dict = {}
        for campo in irfs.dtype.names:
            irf_dict[campo] = irfs[campo].flatten()
            
        # Creiamo un nome per identificare lo scenario
        nome_scenario = f"Scen. {len(st.session_state.scenari)+1}: {tipo_shock[:4]} (Int:{intensita_shock}, ω:{omega}, φ_π:{phip})"
        
        # Salviamo tutto nel "cassetto" della session_state
        nuovo_scenario = {
            'nome': nome_scenario,
            'dati': irf_dict,
            'tempo': np.arange(trimestri),
            'suffisso_shock': '_ms' if tipo_shock == "Monetario (ms)" else '_eps'
        }
        st.session_state.scenari.append(nuovo_scenario)

    except Exception as e:
        st.error(f"Errore durante l'estrazione: {e}")
        st.code(process.stdout)

# --- VISUALIZZAZIONE GRAFICI ---
if len(st.session_state.scenari) > 0 and len(variabili_scelte) > 0:
    st.subheader(f"Confronto Scenari ({trimestri} trimestri)")
    
    # Calcoliamo righe e colonne per avere una griglia bella da vedere (max 3 grafici per riga)
    colonne_griglia = 3
    righe_griglia = (len(variabili_scelte) + colonne_griglia - 1) // colonne_griglia
    
    fig, axes = plt.subplots(righe_griglia, colonne_griglia, figsize=(15, 4 * righe_griglia))
    
    # Trasformiamo axes in un array 1D per iterarci facilmente, anche se c'è un solo grafico
    if type(axes) is not np.ndarray:
        axes = [axes]
    else:
        axes = axes.flatten()
        
    colori = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    # Disegniamo ogni variabile selezionata
    for i, var in enumerate(variabili_scelte):
        ax = axes[i]
        
        # Sovrapponiamo tutti gli scenari salvati
        for j, scenario in enumerate(st.session_state.scenari):
            chiave_irf = f"{var}{scenario['suffisso_shock']}"
            
            # Controlla se Dynare ha generato la IRF per questa variabile e questo shock
            if chiave_irf in scenario['dati']:
                ax.plot(scenario['tempo'], scenario['dati'][chiave_irf], 
                        color=colori[j % len(colori)], marker='.', label=scenario['nome'])
                
        ax.set_title(nomi_variabili[var], fontweight='bold')
        ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Trimestri")
        if i == 0: # Mettiamo la legenda solo nel primo grafico per non ingombrare
            ax.legend(fontsize='small', loc='best')

    # Nascondiamo i grafici vuoti (se l'utente ha scelto es. 4 variabili, abbiamo 2 spazi vuoti nella griglia 2x3)
    for i in range(len(variabili_scelte), len(axes)):
        fig.delaxes(axes[i])
        
    st.pyplot(fig)
    plt.close(fig)

elif len(st.session_state.scenari) == 0:
    st.info("👈 Imposta i parametri e clicca su 'Aggiungi Scenario' per iniziare.")
elif len(variabili_scelte) == 0:
    st.warning("👈 Seleziona almeno una variabile da osservare nel menu laterale.")
