import streamlit as st
import numpy as np
import subprocess
import glob
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.io import loadmat

# Import external translations dictionary
from translations import texts

st.set_page_config(page_title="Simple NKM DSGE Simulator", layout="wide")

# --- CSS INJECTION FOR FULL-SCREEN SIDEBAR ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            height: 100vh !important;
            min-width: 350px !important; 
        }
        [data-testid="stSidebarUserContent"] {
            height: 100% !important;
            overflow-y: auto !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- LANGUAGE SELECTION ---
selected_language = st.sidebar.radio("🌐 Lingua / Language:", ["Italiano", "English"], horizontal=True)
lang = texts[selected_language]

st.title(lang['title'])
st.markdown(lang['subtitle'])

# --- SESSION STATE INITIALIZATION ---
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = []

# --- THEORY LINK ---
st.sidebar.markdown(
    f"""
    <a href="{lang['theory_url']}" target="_blank" style="text-decoration: none;">
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #d1d5db; margin-bottom: 15px; margin-top: 10px;">
            {lang['theory_btn']}
        </div>
    </a>
    """, 
    unsafe_allow_html=True
)

# --- SIDEBAR: CONTROL PANEL FORM ---
with st.sidebar.form("control_panel"):
    st.subheader(lang['header_1'])
    shock_type = st.selectbox(lang['shock_type'], [lang['shock_tech'], lang['shock_mon']])
    shock_intensity = st.number_input(lang['shock_intensity'], min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    quarters = st.slider(lang['horizon'], min_value=10, max_value=100, value=40, step=5)

    selected_vars = st.multiselect(
        lang['var_observe'],
        options=list(lang['vars'].keys()),
        default=['a', 'mc', 'w', 'pi', 'r', 'c', 'y'],
        format_func=lambda x: lang['vars'][x]
    )

    st.divider()
    st.subheader(lang['header_2'])
    
    # PARAMETERS WITH DYNAMIC LABELS AND HELP TEXTS
    beta = st.slider(lang['params']['beta_label'], min_value=0.90, max_value=0.99, value=0.99, step=0.01, help=lang['params']['beta_help'])
    gamma = st.slider(lang['params']['gamma_label'], min_value=0.1, max_value=3.0, value=1.0, step=0.1, help=lang['params']['gamma_help'])
    omega = st.slider(lang['params']['omega_label'], min_value=0.01, max_value=1.0, value=0.75, step=0.01, help=lang['params']['omega_help'])
    rhoa = st.slider(lang['params']['rhoa_label'], min_value=0.01, max_value=0.99, value=0.7, step=0.01, help=lang['params']['rhoa_help'])
    phip = st.slider(lang['params']['phip_label'], min_value=1.01, max_value=3.0, value=1.5, step=0.1, help=lang['params']['phip_help'])
    rhom = st.slider(lang['params']['rhom_label'], min_value=0.01, max_value=0.99, value=0.5, step=0.01, help=lang['params']['rhom_help'])

    btn_add = st.form_submit_button(lang['btn_add'], type="primary", use_container_width=True)

# --- SIDEBAR: SCENARIO MANAGEMENT ---
st.sidebar.subheader(lang['header_3'])

if len(st.session_state.scenarios) > 0:
    for i, scenario in enumerate(st.session_state.scenarios):
        col_name, col_delete = st.sidebar.columns([5, 1])
        col_name.markdown(f"<span style='font-size:0.9em;'>{scenario['name']}</span>", unsafe_allow_html=True)
        
        if col_delete.button("❌", key=f"delete_{i}"):
            st.session_state.scenarios.pop(i)
            st.rerun()

    st.sidebar.divider()
    if st.sidebar.button(lang['btn_remove_all'], use_container_width=True):
        st.session_state.scenarios = []
        st.rerun()
else:
    st.sidebar.info(lang['no_scenarios'])

# --- MODEL EXECUTION ---
if btn_add:
    var_eps = shock_intensity if "eps" in shock_type else 0.0
    var_ms = shock_intensity if "ms" in shock_type else 0.0

    mod_content = f"""
    % Linearized NKM
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

    stoch_simul(irf={quarters}, noprint, nograph);
    """
    
    with open("NKM_lin.mod", "w") as f:
        f.write(mod_content)

    with st.spinner(lang['calc_spinner']):
        octave_command = "addpath('/usr/lib/dynare/matlab'); dynare NKM_lin.mod;"
        process = subprocess.run(["octave", "--no-gui", "--eval", octave_command], capture_output=True, text=True)
        
    try:
        result_files = glob.glob("**/NKM_lin_results.mat", recursive=True)
        if not result_files:
            raise FileNotFoundError("The file NKM_lin_results was not found!")
            
        mat_data = loadmat(result_files[0])
        irfs = mat_data['oo_'][0, 0]['irfs'][0, 0]
        
        irf_dict = {}
        for field in irfs.dtype.names:
            irf_dict[field] = np.round(irfs[field].flatten(), 4)
            
        total_scenarios = len(st.session_state.scenarios) + 1
        scenario_name = f"S{total_scenarios}: {shock_type[:8]}... (β={beta}, γ={gamma}, ω={omega}, ρ_a={rhoa}, φ_π={phip}, ρ_m={rhom})"
        
        st.session_state.scenarios.append({
            'name': scenario_name,
            'data': irf_dict,
            'time': np.arange(quarters),
            'suffix': '_ms' if "ms" in shock_type else '_eps'
        })
        
        st.rerun()
        
    except Exception as e:
        st.error(f"Error: {e}")
        st.code(process.stdout)

# --- INTERACTIVE PLOTS (PLOTLY) & DATA EXPORT ---
if len(st.session_state.scenarios) > 0 and len(selected_vars) > 0:
    st.subheader(lang['chart_title'].format(quarters=quarters))
    
    num_vars = len(selected_vars)
    cols_count = min(3, num_vars)
    rows_count = ((num_vars - 1) // 3) + 1
    
    # Use dynamically translated variable names for subplots
    subplot_titles = [lang['vars'][v] for v in selected_vars]
    fig = make_subplots(rows=rows_count, cols=cols_count, subplot_titles=subplot_titles)
    
    colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    for idx, var in enumerate(selected_vars):
        row = (idx // 3) + 1
        col = (idx % 3) + 1
        
        for j, scenario in enumerate(st.session_state.scenarios):
            irf_key = f"{var}{scenario['suffix']}"
            if irf_key in scenario['data']:
                show_legend = True if idx == 0 else False
                
                fig.add_trace(go.Scatter(
                    x=scenario['time'],
                    y=scenario['data'][irf_key],
                    mode='lines+markers',
                    name=scenario['name'],
                    legendgroup=scenario['name'],
                    showlegend=show_legend,
                    line=dict(color=colors[j % len(colors)]),
                    marker=dict(size=6)
                ), row=row, col=col)
        
        fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1, row=row, col=col)
        fig.update_xaxes(title_text=lang['x_axis'], row=row, col=col)

    total_height = max(400, 300 * rows_count)
    fig.update_layout(
        height=total_height, 
        margin=dict(t=50, l=20, r=20, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 2. GENERATE DATA TABLE FOR DOWNLOAD
    st.divider()
    st.markdown(lang['export_header'])
    
    df_list = []
    for scenario in st.session_state.scenarios:
        df_temp = pd.DataFrame({lang['time_col']: scenario['time']})
        
        clean_csv_name = scenario['name'].replace("ω", "omega").replace("φ_π", "phi_pi").replace("π", "pi")\
                                         .replace("β", "beta").replace("γ", "gamma").replace("ρ_a", "rho_a").replace("ρ_m", "rho_m")
        
        for var in selected_vars:
            irf_key = f"{var}{scenario['suffix']}"
            if irf_key in scenario['data']:
                # Dynamically translate headers in the exported CSV
                column_name = f"[{clean_csv_name}] {lang['vars'][var]}"
                df_temp[column_name] = scenario['data'][irf_key]
                
        df_temp = df_temp.set_index(lang['time_col'])
        df_list.append(df_temp)
        
    if df_list:
        df_final = pd.concat(df_list, axis=1)
        csv_data = df_final.to_csv().encode('utf-8')
        
        st.download_button(
            label=lang['btn_download'],
            data=csv_data,
            file_name="NKM_DSGE_simulation.csv",
            mime="text/csv",
        )

elif len(st.session_state.scenarios) == 0:
    st.info(lang['info_start'])
elif len(selected_vars) == 0:
    st.warning(lang['warn_vars'])
