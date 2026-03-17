import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import glob
from scipy.io import loadmat

st.set_page_config(page_title="NKM DSGE con Dynare", layout="wide")

st.title("Simulatore NKM DSGE (Multiscenario)")
st.markdown("Imposta i parametri, scegli lo shock e clicca su **Aggiungi Scenario**. Puoi lanciare più simulazioni di fila per vederle sovrapposte!")

# --- INIZIALIZZAZIONE DELLA MEMORIA (SESSION STATE) ---
if 'scenari' not in st.session_state:
    st.session_state.scenari = []

nomi_variabili = {
    'y': 'Output (y)', 'pi': 'Inflazione (π)', 'r': 'Tasso di Interesse (r)', 
    'w': 'Salario (w)', 'mc': 'Costo Marginale (mc)', 'l': 'Lavoro (l)', 
    'c': 'Consumo (c)', 'a': 'Produttività (a)', 'is': 'Shock Monetario (is)'
}

# --- BARRA LATERALE: FORM DI INSERIMENTO ---
with st.sidebar.form("pannello_controllo"):
    st.subheader("1. Impostazioni Shock e Grafici")
    tipo_shock = st.selectbox("Tipo di Shock:", ["Shock Monetario (ms)", "Shock Tecnologico (eps)"])
    intensita_shock = st.number_input("Intensità dello shock:", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    trimestri = st.slider("Orizzonte temporale (trimestri):", min_value=10, max_value=100, value=40, step=5)

    variabili_scelte = st.multiselect(
        "Variabili da osservare:",
        options=list(nomi_variabili.keys()),
        default=['y', 'pi', 'r'],
        format_func=lambda x: nomi_variabili[x]
    )

    st.divider()
    st.subheader("2. Parametri Strutturali")
    beta = st.slider("β - Fattore di sconto", min_value=0.90, max_value=0.99, value=0.99, step=0.01)
    gamma = st.slider("γ - Inverso Frisch elasticity", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
    omega = st.slider("ω - Stickiness parameter", min_value=0.01, max_value=1.0, value=0.75, step=0.01)
    rhoa = st.slider("ρ_a - Persistenza shock TFP", min_value=0.01, max_value=0.99, value=0.7, step=0.01)
    phip = st.slider("φ_π - Taylor parameter", min_value=1.01, max_value=3.0, value=1.5, step=0.1)
    rhom = st.slider("ρ_m - Persistenza shock monetario", min_value=0.01, max_value=0.99, value=0.5, step=0.01)

    # Pulsante per confermare e lanciare Dynare
    btn_aggiungi = st.form_submit_button("➕ Aggiungi Scenario", type="primary", use_container_width=True)

# --- BARRA LATERALE: GESTIONE SCENARI ---
st.sidebar.subheader("3. Scenari Salvati")

# Se ci sono scenari in memoria, creiamo la lista con i pulsanti di eliminazione
if len(st.session_state.scenari) > 0:
    for i, scenario in enumerate(st.session_state.scenari):
        # Dividiamo la riga in due colonne: una larga (5) per il nome, una stretta (1) per la "X"
        col_nome, col_elimina = st.sidebar.columns([5, 1])
        
        col_nome.markdown(f"<span style='font-size:0.9em;'>{scenario['nome']}</span>", unsafe_allow_html=True)
        
        # Se si clicca la 'X', eliminiamo quello specifico scenario dalla lista e ricarichiamo la pagina
        if col_elimina.button("❌", key=f"elimina_{i}", help="Rimuovi questo scenario"):
            st.session_state.scenari.pop(i)
            st.rerun()

    st.sidebar.divider()
    # Pulsante per svuotare tutto in un colpo solo
    if st.sidebar.button("🗑️ Svuota Tutti gli Scenari", use_container_width=True):
        st.session_state.scenari = []
        st.rerun()
else:
    st.sidebar.info("Nessun scenario attualmente salvato.")

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
            irf_dict[campo] = irfs[campo].flatten()
            
        # Per distinguere meglio, usiamo il numero reale basato sulla cronologia
        # anche se eliminiamo quelli in mezzo
        num_scenari_totali = len(st.session_state.scenari) + 1
        nome_scenario = f"Scen. {num_scenari_totali}: {tipo_shock[:8]} (ω={omega}, φ_π={phip})"
        
        st.session_state.scenari.append({
            'nome': nome_scenario,
            'dati': irf_dict,
            'tempo': np.arange(trimestri),
            'suffisso': '_ms' if "Monetario" in tipo_shock else '_eps'
        })
        
        # Forza un ricaricamento della pagina in modo che la nuova voce compaia subito nella barra laterale
        st.rerun()
        
    except Exception as e:
        st.error(f"Errore durante l'estrazione dei dati: {e}")
        st.code(process.stdout)

# --- VISUALIZZAZIONE GRAFICI ---
if len(st.session_state.scenari) > 0 and len(variabili_scelte) > 0:
    st.subheader(f"Confronto Scenari ({trimestri} trimestri)")
    
    colori = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']
    cols = st.columns(3) 
    
    for idx, var in enumerate(variabili_scelte):
        col_attuale = cols[idx % 3] 
        
        with col_attuale:
            fig, ax = plt.subplots(figsize=(5, 4))
            
            for j, scenario in enumerate(st.session_state.scenari):
                chiave_irf = f"{var}{scenario['suffisso']}"
                if chiave_irf in scenario['dati']:
                    ax.plot(scenario['tempo'], scenario['dati'][chiave_irf], 
                            color=colori[j % len(colori)], marker='.', label=scenario['nome'])
            
            ax.set_title(nomi_variabili[var], fontweight='bold')
            ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Trimestri")
            
            if idx == 0:
                ax.legend(fontsize='small', loc='best')
                
            st.pyplot(fig)
            plt.close(fig)

elif len(st.session_state.scenari) == 0:
    st.info("👈 Imposta i parametri nel form laterale e clicca su 'Aggiungi Scenario' per iniziare la simulazione.")
elif len(variabili_scelte) == 0:
    st.warning("👈 Seleziona almeno una variabile da osservare nel menu a tendina.")
