---
title: Simple NKM DSGE Simulator
emoji: 📊
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
---

# Simple NKM DSGE Simulator 📈

An interactive web application built with **Python**, **Streamlit** and **Dynare/Octave** to simulate and visualize a basic **New Keynesian DSGE Model**. 

This platform allows students, researchers, and economics enthusiasts to easily interact with macroeconomic structural parameters, apply technological or monetary shocks, and immediately visualize the Impulse Response Functions (IRFs) across multiple comparative scenarios.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![GNU Octave](https://img.shields.io/badge/GNU_Octave-025590?style=for-the-badge&logo=gnu-octave&logoColor=white)

## ✨ Key Features
* **Multi-Scenario comparison**: run multiple simulations with different parameters (e.g., varying the Calvo stickiness parameter $\omega$ or the Taylor rule weight $\phi_\pi$) and overlay the IRFs on the same interactive graphs.
* **Interactive Plotly charts**: zoom, pan, hover for exact values, and toggle specific scenarios on/off directly from the legend.
* **Data export**: download the simulated IRF data as a cleanly formatted CSV file.
* **Dynamic Mod-file generation**: the Python backend writes the `.mod` file on the fly and runs Dynare in the background seamlessly.

## 🧮 The Macroeconomic Model
The simulator solves a linearized New Keynesian Model consisting of:
1. **Dynamic IS Curve** (Demand side / Euler equation)
2. **New Keynesian Phillips Curve** (Supply side / Calvo pricing)
3. **Taylor Rule** (Monetary policy)

Users can tweak structural parameters such as the discount factor ($\beta$), inverse Frisch elasticity ($\gamma$), price stickiness ($\omega$), and the persistence of TFP ($\rho_a$) and monetary ($\rho_m$) shocks.

## 📂 Project Structure
* `app.py`: The main Streamlit application handling the UI, dynamic `.mod` generation, and Plotly visualizations.
* `translations.py`: Contains the dictionaries for the dual-language support (variables, interface text, and parameter tooltips).
* `Dockerfile`: Custom Docker configuration to install GNU Octave and Dynare alongside Python for cloud deployment.
* `.github/workflows/sync_to_hf.yml`: The CI/CD pipeline script to synchronize the repo with Hugging Face Spaces.

---

## 🚀 Deployment on Hugging Face Spaces
This app is designed to be hosted on **Hugging Face Spaces** using a custom Docker environment. 
