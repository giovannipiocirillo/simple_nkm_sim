import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import os
from scipy.io import loadmat

st.set_page_config(page_title="NKM DSGE con Dynare", layout="wide")

st.title("Simulatore NKM DSGE (Dynare/Octave)")
st.markdown("Modifica i parametri e clicca su **Simula**. L'app scriverà il file `.mod`, farà girare Dynare in background e leggerà i risultati.")

# --- BARRA LATERALE: PARAMETRI ---
st.sidebar.header("Parametri del Modello")

gamma = st.sidebar.slider("GAMMA", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
omega = st.sidebar.slider("OMEGA", min_value=0.1, max_value=0.99, value=0.75, step=0.05)
beta = st.sidebar.slider("BETA", min_value=0.90, max_value=0.99, value=0.99, step=0.01)
phip = st.sidebar.slider("PHIP", min_value=1.1, max_value=3.0, value=1.5, step=0.1)
rhoa = st.sidebar.slider("RHOA", min_value=0.0, max_value=0.99, value=0.7, step=0.05)
rhom = st.sidebar.slider("RHOM", min_value=0.0, max_value=0.99, value=0.5, step=0.05)

if st.sidebar.button("Simula Modello con Dynare", type="primary"):
    
    # 1. GENERAZIONE DEL FILE .mod
    # Inseriamo i parametri direttamente nel codice testuale del modello
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

    steady;
    check;

    shocks;
    var eps = 1;
    var ms = 1;
    end;

    % noprint evita di intasare i log di sistema
    stoch_simul(irf=40, noprint);
    """
    
    with open("NKM_lin.mod", "w") as f:
        f.write(mod_content)

# 2. ESECUZIONE DI DYNARE
    with st.spinner("Esecuzione di Dynare in corso (può richiedere qualche secondo)..."):
        # Diciamo a Octave esattamente dove trovare Dynare su Linux Debian e poi lanciamo il modello
        comando_octave = "addpath('/usr/lib/dynare/matlab'); dynare NKM_lin.mod;"
        process = subprocess.run(["octave", "--no-gui", "--eval", comando_octave], capture_output=True, text=True)
        
# 3. LETTURA DEI RISULTATI (.mat) E GESTIONE ERRORI
    try:
        import glob
        # Dynare 6 salva i risultati in una sottocartella (es. NKM_lin/Output/)
        # glob cerca il file ovunque si trovi all'interno del progetto
        file_risultati = glob.glob("**/NKM_lin_results.mat", recursive=True)
        
        if not file_risultati:
            raise FileNotFoundError("Il file NKM_lin_results.mat non è stato trovato!")
            
        # Carica il primo file trovato
        mat_data = loadmat(file_risultati[0])
        irfs = mat_data['oo_'][0, 0]['irfs'][0, 0]
        
        y_ms = irfs['y_ms'].flatten()
        pi_ms = irfs['pi_ms'].flatten()
        r_ms = irfs['r_ms'].flatten()
        
        y_eps = irfs['y_eps'].flatten()
        pi_eps = irfs['pi_eps'].flatten()
        r_eps = irfs['r_eps'].flatten()
        
        t = np.arange(len(y_ms))

        # --- GRAFICI ---
        st.subheader("Impulse Response Functions (IRF)")
        
        st.markdown("#### Shock Monetario Espansivo ($ms$)")
        fig1, axs1 = plt.subplots(1, 3, figsize=(15, 4))
        axs1[0].plot(t, y_ms, color='blue', marker='.')
        axs1[0].set_title("Output ($y$)")
        axs1[1].plot(t, pi_ms, color='red', marker='.')
        axs1[1].set_title("Inflazione ($\pi$)")
        axs1[2].plot(t, r_ms, color='green', marker='.')
        axs1[2].set_title("Tasso di Interesse ($r$)")
        
        for ax in axs1:
            ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Trimestri")
        st.pyplot(fig1)

        st.markdown("#### Shock Tecnologico ($eps$)")
        fig2, axs2 = plt.subplots(1, 3, figsize=(15, 4))
        axs2[0].plot(t, y_eps, color='blue', marker='.')
        axs2[0].set_title("Output ($y$)")
        axs2[1].plot(t, pi_eps, color='red', marker='.')
        axs2[1].set_title("Inflazione ($\pi$)")
        axs2[2].plot(t, r_eps, color='green', marker='.')
        axs2[2].set_title("Tasso di Interesse ($r$)")
        
        for ax in axs2:
            ax.axhline(0, color='black', linestyle='--', linewidth=0.8)
            ax.grid(True, alpha=0.3)
            ax.set_xlabel("Trimestri")
        st.pyplot(fig2)

    except Exception as e:
        st.error(f"Ops! Qualcosa è andato storto: {e}")
        st.code(process.stdout)
