import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from quantum_yield_utils import (
    load_absorbance_data,
    calculate_extinction,
    calculate_new_absorbance,
    load_led_data,
    baseline_led,
    normalize_led_area,
    interpolate_absorbance_to_led,
    gaussian_fit_led,
    validate_led_areas,
    calculate_photon_metrics,
    calculate_absorbed_photons,
    calculate_quantum_yields
)

# -----------------------------------------------------------------------------
# PAGE SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Quantum Yield Calculator", layout="wide")
st.title("User-Friendly Quantum Yield Calculator")
st.write("Calculate total absorbed photons and quantum yield from absorbance and LED emission data.")

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
defaults = {
    "raw_abs": None,
    "wavelengths_abs": None,
    "extinction": None,
    "l1": 1.0,
    "c1": 1.0,

    "new_abs": None,
    "l2": 1.0,
    "c2": 1.0,

    "raw_led": None,
    "led_wavelengths": None,
    "base_led": None,
    "led_area_norm": None,
    "conversion_factor": None,
    "intensity": 1.0,

    "gauss_led": None,
    "gaussian_fit_function": None,
    "new_abs_on_led": None,
    "area_validation": None,

    "photon_metrics": None,
    "total_absorbed": None,
    "total_led": None,
    "efficiency": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_downstream_from_absorbance():
    st.session_state.extinction = None
    st.session_state.new_abs = None
    reset_downstream_from_led()


def reset_downstream_from_led():
    st.session_state.raw_led = None
    st.session_state.led_wavelengths = None
    st.session_state.base_led = None
    st.session_state.led_area_norm = None
    st.session_state.conversion_factor = None
    st.session_state.gauss_led = None
    st.session_state.gaussian_fit_function = None
    st.session_state.new_abs_on_led = None
    st.session_state.area_validation = None
    st.session_state.photon_metrics = None
    st.session_state.total_absorbed = None
    st.session_state.total_led = None
    st.session_state.efficiency = None


# -----------------------------------------------------------------------------
# STEP 1: ABSORBANCE DATA
# -----------------------------------------------------------------------------
st.header("Step 1: Absorbance Data Processing")

col1, col2 = st.columns([2, 1])

with col1:
    abs_file = st.file_uploader(
        "Upload absorbance Excel file",
        type=["xls", "xlsx"],
        key="abs_file_uploader"
    )

with col2:
    if st.button("Load Absorbance Data", key="load_abs_btn"):
        if abs_file is None:
            st.error("Please upload an absorbance file first.")
        else:
            raw_abs, error = load_absorbance_data(abs_file)
            if error:
                st.error(error)
            else:
                st.session_state.raw_abs = raw_abs
                st.session_state.wavelengths_abs = raw_abs[:, 0].astype(float)
                reset_downstream_from_absorbance()
                st.success("✓ Absorbance data loaded successfully")

if st.session_state.raw_abs is not None:
    st.subheader("Absorbance Parameters")
    col1, col2 = st.columns(2)

    with col1:
        st.session_state.l1 = st.number_input(
            "Pathlength (cm)",
            value=st.session_state.l1,
            min_value=0.001,
            step=0.01,
            key="l1_input"
        )

    with col2:
        st.session_state.c1 = st.number_input(
            "Concentration (mol/L)",
            value=st.session_state.c1,
            min_value=0.001,
            step=0.001,
            key="c1_input"
        )

    if st.button("Calculate Extinction Coefficient", key="calc_extinction_btn"):
        wavelengths, extinction, error = calculate_extinction(
            st.session_state.raw_abs,
            st.session_state.l1,
            st.session_state.c1
        )
        if error:
            st.error(error)
        else:
            st.session_state.wavelengths_abs = wavelengths
            st.session_state.extinction = extinction
            st.session_state.new_abs = None
            reset_downstream_from_led()
            st.success("✓ Extinction coefficient calculated")

    if st.session_state.extinction is not None:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(st.session_state.wavelengths_abs, st.session_state.extinction, linewidth=2, color="steelblue")
        ax.set_title("Calculated Extinction Coefficient (M⁻¹ cm⁻¹)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Extinction Coefficient (M⁻¹ cm⁻¹)")
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        col1, col2, col3 = st.columns(3)
        col1.metric("Min", f"{np.min(st.session_state.extinction):.2e}")
        col2.metric("Max", f"{np.max(st.session_state.extinction):.2e}")
        col3.metric(
            "Peak Wavelength",
            f"{st.session_state.wavelengths_abs[np.argmax(st.session_state.extinction)]:.1f} nm"
        )


# -----------------------------------------------------------------------------
# STEP 2: NEW ABSORBANCE
# -----------------------------------------------------------------------------
if st.session_state.extinction is not None:
    st.header("Step 2: Scale to New Conditions")

    col1, col2 = st.columns(2)

    with col1:
        st.session_state.l2 = st.number_input(
            "FTIR Pathlength (cm)",
            value=st.session_state.l2,
            min_value=0.001,
            step=0.01,
            key="l2_input"
        )

    with col2:
        st.session_state.c2 = st.number_input(
            "FTIR Concentration (mol/L)",
            value=st.session_state.c2,
            min_value=0.001,
            step=0.001,
            key="c2_input"
        )

    if st.button("Calculate New Absorbance", key="calc_new_abs_btn"):
        new_abs, error = calculate_new_absorbance(
            st.session_state.extinction,
            st.session_state.l2,
            st.session_state.c2
        )
        if error:
            st.error(error)
        else:
            st.session_state.new_abs = new_abs
            reset_downstream_from_led()
            st.success("✓ New absorbance calculated")

    if st.session_state.new_abs is not None:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(st.session_state.wavelengths_abs, st.session_state.new_abs, linewidth=2, color="darkgreen")
        ax.set_title("New Absorbance Data", fontsize=12, fontweight="bold")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Absorbance")
        ax.grid(alpha=0.3)
        st.pyplot(fig)


# -----------------------------------------------------------------------------
# STEP 3: LED EMISSION DATA
# -----------------------------------------------------------------------------
if st.session_state.new_abs is not None:
    st.header("Step 3: LED Emission Data")

    col1, col2 = st.columns([2, 1])

    with col1:
        led_file = st.file_uploader(
            "Upload LED emission Excel file",
            type=["xls", "xlsx"],
            key="led_file_uploader"
        )

    with col2:
        if st.button("Load LED Data", key="load_led_btn"):
            if led_file is None:
                st.error("Please upload an LED file first.")
            else:
                raw_led, error = load_led_data(led_file)
                if error:
                    st.error(error)
                else:
                    st.session_state.raw_led = raw_led
                    st.session_state.led_wavelengths = raw_led[:, 0].astype(float)
                    st.session_state.base_led = None
                    st.session_state.led_area_norm = None
                    st.session_state.conversion_factor = None
                    st.session_state.gauss_led = None
                    st.session_state.gaussian_fit_function = None
                    st.session_state.new_abs_on_led = None
                    st.session_state.area_validation = None
                    st.session_state.photon_metrics = None
                    st.session_state.total_absorbed = None
                    st.session_state.total_led = None
                    st.session_state.efficiency = None
                    st.success("✓ LED data loaded")

    if st.session_state.raw_led is not None:
        if st.button("Baseline LED Data", key="baseline_led_btn"):
            base_led, led_min, error = baseline_led(st.session_state.raw_led)
            if error:
                st.error(error)
            else:
                st.session_state.base_led = base_led
                st.session_state.led_area_norm = None
                st.session_state.conversion_factor = None
                st.session_state.gauss_led = None
                st.session_state.gaussian_fit_function = None
                st.session_state.new_abs_on_led = None
                st.session_state.area_validation = None
                st.session_state.photon_metrics = None
                st.session_state.total_absorbed = None
                st.session_state.total_led = None
                st.session_state.efficiency = None
                st.success(f"✓ LED baselined (minimum value subtracted: {led_min:.4e})")

        if st.session_state.base_led is not None:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(
                st.session_state.led_wavelengths,
                st.session_state.raw_led[:, 1],
                label="Raw LED",
                linewidth=2,
                marker="o",
                markersize=3,
                alpha=0.6
            )
            ax.plot(
                st.session_state.led_wavelengths,
                st.session_state.base_led,
                label="Baselined LED",
                linewidth=2,
                marker="s",
                markersize=3,
                alpha=0.6
            )
            ax.set_title("Raw vs Baselined LED Emission Spectra", fontsize=12, fontweight="bold")
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Counts")
            ax.legend()
            ax.grid(alpha=0.3)
            st.pyplot(fig)

            st.session_state.intensity = st.number_input(
                "LED Intensity (mW/cm²)",
                value=st.session_state.intensity,
                min_value=0.001,
                step=0.1,
                key="intensity_input"
            )

            if st.button("Normalize LED Area", key="normalize_led_btn"):
                led_area_norm, conv_factor, error = normalize_led_area(
                    st.session_state.led_wavelengths,
                    st.session_state.base_led,
                    st.session_state.intensity
                )
                if error:
                    st.error(error)
                else:
                    st.session_state.led_area_norm = led_area_norm
                    st.session_state.conversion_factor = conv_factor
                    st.session_state.gauss_led = None
                    st.session_state.gaussian_fit_function = None
                    st.session_state.new_abs_on_led = None
                    st.session_state.area_validation = None
                    st.session_state.photon_metrics = None
                    st.session_state.total_absorbed = None
                    st.session_state.total_led = None
                    st.session_state.efficiency = None
                    st.success(f"✓ LED area normalized (Conversion Factor: {conv_factor:.4e})")

            if st.session_state.led_area_norm is not None:
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(
                    st.session_state.led_wavelengths,
                    st.session_state.base_led,
                    label="Baselined LED",
                    linewidth=2,
                    alpha=0.6
                )
                ax.plot(
                    st.session_state.led_wavelengths,
                    st.session_state.led_area_norm,
                    label="Area-Normalized LED",
                    linewidth=2,
                    alpha=0.8
                )
                ax.set_title("Baselined vs Area-Normalized LED", fontsize=12, fontweight="bold")
                ax.set_xlabel("Wavelength (nm)")
                ax.set_ylabel("Intensity")
                ax.legend()
                ax.grid(alpha=0.3)
                st.pyplot(fig)

                normalized_area_check = np.trapz(
                    st.session_state.led_area_norm,
                    st.session_state.led_wavelengths
                )

                col1, col2 = st.columns(2)
                col1.metric("Target Intensity", f"{st.session_state.intensity:.6f} mW/cm²")
                col2.metric("Integrated Normalized Area", f"{normalized_area_check:.6f} mW/cm²")


# -----------------------------------------------------------------------------
# STEP 4: GAUSSIAN FIT
# -----------------------------------------------------------------------------
if st.session_state.led_area_norm is not None:
    st.header("Step 4: Gaussian Fit for LED Emission")

    n_gaussians = st.slider("Number of Gaussian components", min_value=1, max_value=5, value=2)

    if st.button("Fit Gaussian to LED", key="fit_gaussian_btn"):
        fit_func, fitted_vals, error = gaussian_fit_led(
            st.session_state.led_wavelengths,
            st.session_state.led_area_norm,
            n_gaussians
        )

        if error:
            st.error(error)
        else:
            new_abs_on_led, interp_error = interpolate_absorbance_to_led(
                st.session_state.wavelengths_abs,
                st.session_state.new_abs,
                st.session_state.led_wavelengths
            )

            if interp_error:
                st.error(interp_error)
            else:
                st.session_state.gaussian_fit_function = fit_func
                st.session_state.gauss_led = fitted_vals
                st.session_state.new_abs_on_led = new_abs_on_led
                st.session_state.area_validation = validate_led_areas(
                    st.session_state.led_wavelengths,
                    st.session_state.led_area_norm,
                    st.session_state.gauss_led,
                    st.session_state.intensity
                )
                st.session_state.photon_metrics = None
                st.session_state.total_absorbed = None
                st.session_state.total_led = None
                st.session_state.efficiency = None
                st.success(f"✓ Gaussian fit completed ({n_gaussians} component(s))")

    if st.session_state.gauss_led is not None:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(
            st.session_state.led_wavelengths,
            st.session_state.led_area_norm,
            "o",
            label="Area-Normalized LED",
            markersize=4,
            alpha=0.6
        )
        ax.plot(
            st.session_state.led_wavelengths,
            st.session_state.gauss_led,
            "-",
            label="Gaussian Fit",
            linewidth=2.5
        )
        ax.set_title("Area-Normalized LED Emission with Gaussian Fit", fontsize=12, fontweight="bold")
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Intensity (mW/cm²/nm)")
        ax.legend()
        ax.grid(alpha=0.3)
        st.pyplot(fig)

        if st.session_state.area_validation and st.session_state.area_validation.get("error") is None:
            val = st.session_state.area_validation
            col1, col2, col3 = st.columns(3)
            col1.metric("Target Intensity", f"{val['target_intensity']:.6f}")
            col2.metric("Normalized LED Area", f"{val['normalized_area']:.6f}")
            col3.metric("Gaussian Fit Area", f"{val['fitted_area']:.6f}")


# -----------------------------------------------------------------------------
# STEP 5: PHOTON CALCULATIONS
# -----------------------------------------------------------------------------
if st.session_state.gauss_led is not None and st.session_state.new_abs_on_led is not None:
    st.header("Step 5: Photon Calculations")

    if st.button("Calculate Photon Metrics", key="calc_photons_btn"):
        metrics = calculate_photon_metrics(
            st.session_state.led_wavelengths,
            st.session_state.gauss_led,
            st.session_state.new_abs_on_led
        )

        if metrics.get("error"):
            st.error(metrics["error"])
        else:
            st.session_state.photon_metrics = metrics

            abs_result = calculate_absorbed_photons(
                st.session_state.led_wavelengths,
                metrics["NP"],
                metrics["FPA"]
            )

            if abs_result.get("error"):
                st.error(abs_result["error"])
            else:
                st.session_state.total_absorbed = abs_result["total_absorbed"]
                st.session_state.total_led = abs_result["total_led"]
                st.session_state.efficiency = abs_result["efficiency"]
                st.success("✓ Photon metrics calculated")

    if st.session_state.photon_metrics is not None:
        metrics = st.session_state.photon_metrics

        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(st.session_state.led_wavelengths, metrics["NP"], linewidth=2, color="purple")
            ax.set_title("Number of Photons vs Wavelength", fontsize=11, fontweight="bold")
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Photons")
            ax.grid(alpha=0.3)
            st.pyplot(fig)

        with col2:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(st.session_state.led_wavelengths, metrics["FPT"], linewidth=2, color="orange")
            ax.set_title("Fraction Photons Transmitted", fontsize=11, fontweight="bold")
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Fraction Transmitted")
            ax.grid(alpha=0.3)
            st.pyplot(fig)

        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(st.session_state.led_wavelengths, metrics["FPA"], linewidth=2, color="red")
            ax.set_title("Fraction Photons Absorbed", fontsize=11, fontweight="bold")
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Fraction Absorbed")
            ax.grid(alpha=0.3)
            st.pyplot(fig)

        with col2:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(st.session_state.led_wavelengths, metrics["NRG"], linewidth=2, color="brown")
            ax.set_title("Energy per Photon vs Wavelength", fontsize=11, fontweight="bold")
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Energy (J)")
            ax.grid(alpha=0.3)
            st.pyplot(fig)

        st.subheader("Photon Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total LED Photons", f"{st.session_state.total_led:.2e} photons/cm²/s")
        col2.metric("Total Absorbed Photons", f"{st.session_state.total_absorbed:.2e} photons/cm²/s")
        col3.metric("Absorption Efficiency", f"{st.session_state.efficiency:.2f}%")


# -----------------------------------------------------------------------------
# STEP 6: QUANTUM YIELD CALCULATION
# -----------------------------------------------------------------------------
if st.session_state.total_absorbed is not None:
    st.header("Step 6: Quantum Yield Calculation")

    col1, col2 = st.columns(2)

    with col1:
        rate_ftir = st.number_input(
            "FTIR Conversion Fraction (fraction/s)",
            value=1e-4,
            format="%.2e",
            min_value=1e-10,
            step=1e-5
        )

    with col2:
        monomer_conc = st.number_input(
            "Monomer Concentration (mol/L)",
            value=0.01,
            min_value=1e-6,
            step=0.001
        )

    if st.button("Calculate Quantum Yields", key="calc_qy_btn"):
        qy_result = calculate_quantum_yields(
            rate_ftir,
            st.session_state.l2,
            monomer_conc,
            st.session_state.total_led,
            st.session_state.total_absorbed
        )

        if qy_result.get("error"):
            st.error(qy_result["error"])
        else:
            st.success("✓ Quantum yields calculated")

            st.subheader("Results")
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "External Quantum Yield",
                f"{qy_result['external_qy']:.4f}",
                help="Molecules converted / incident photons"
            )
            col2.metric(
                "Internal Quantum Yield",
                f"{qy_result['internal_qy']:.4f}",
                help="Molecules converted / absorbed photons"
            )
            col3.metric(
                "Molecules Converted",
                f"{qy_result['rate_molecules']:.2e} molecules/cm²/s"
            )

            st.subheader("Summary Report")
            summary_data = {
                "Parameter": [
                    "Absorbance Pathlength (cm)",
                    "Absorbance Concentration (mol/L)",
                    "FTIR Pathlength (cm)",
                    "FTIR Concentration (mol/L)",
                    "LED Intensity (mW/cm²)",
                    "FTIR Conversion Rate (1/s)",
                    "Monomer Concentration (mol/L)",
                    "",
                    "Total LED Photons (photons/cm²/s)",
                    "Total Absorbed Photons (photons/cm²/s)",
                    "Absorption Efficiency (%)",
                    "External Quantum Yield",
                    "Internal Quantum Yield"
                ],
                "Value": [
                    f"{st.session_state.l1:.6f}",
                    f"{st.session_state.c1:.6f}",
                    f"{st.session_state.l2:.6f}",
                    f"{st.session_state.c2:.6f}",
                    f"{st.session_state.intensity:.6f}",
                    f"{rate_ftir:.2e}",
                    f"{monomer_conc:.6f}",
                    "",
                    f"{st.session_state.total_led:.4e}",
                    f"{st.session_state.total_absorbed:.4e}",
                    f"{st.session_state.efficiency:.2f}",
                    f"{qy_result['external_qy']:.6f}",
                    f"{qy_result['internal_qy']:.6f}"
                ]
            }

            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

if st.button("Reset All Data", key="reset_btn"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# import streamlit as st
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# from quantum_yield_utils import (
#     load_absorbance_data, calculate_extinction, calculate_new_absorbance,
#     load_led_data, baseline_led, normalize_led_area, gaussian_fit_led, calculate_photon_metrics,
#     calculate_absorbed_photons, calculate_quantum_yields
# )

# # Configure page
# st.set_page_config(page_title="Quantum Yield Calculator", layout="wide")
# st.title("User-Friendly Quantum Yield Calculator")
# st.write("Calculate total absorbed photons and quantum yield from absorbance and LED emission data.")

# # Initialize session state
# if 'step' not in st.session_state:
#     st.session_state.step = 1

# if 'raw_abs' not in st.session_state:
#     st.session_state.raw_abs = None
#     st.session_state.wavelengths = None
#     st.session_state.extinction = None
#     st.session_state.l1 = 1.0
#     st.session_state.c1 = 1.0

# if 'raw_led' not in st.session_state:
#     st.session_state.raw_led = None
#     st.session_state.base_led = None
#     st.session_state.led_area_norm = None
#     st.session_state.conversion_factor = None
#     st.session_state.gauss_led = None
#     st.session_state.led_wavelengths = None
#     st.session_state.intensity = 1.0

# if 'new_abs' not in st.session_state:
#     st.session_state.new_abs = None
#     st.session_state.l2 = 1.0
#     st.session_state.c2 = 1.0

# if 'photon_metrics' not in st.session_state:
#     st.session_state.photon_metrics = None
#     st.session_state.total_absorbed = None
#     st.session_state.total_led = None
#     st.session_state.efficiency = None


# # ============================================================================
# # STEP 1: ABSORBANCE DATA
# # ============================================================================
# st.header(" Step 1: Absorbance Data Processing")

# col1, col2 = st.columns([2, 1])
# with col1:
#     abs_file = st.file_uploader("Upload absorbance Excel file", type=['xls', 'xlsx'], key='abs_file_uploader')
    
# with col2:
#     if st.button("Load Absorbance Data", key='load_abs_btn'):
#         if abs_file:
#             raw_abs, error = load_absorbance_data(abs_file)
#             if error:
#                 st.error(error)
#             else:
#                 st.session_state.raw_abs = raw_abs
#                 st.session_state.wavelengths = raw_abs[:, 0].astype(float)
#                 st.success("✓ Data loaded successfully")

# if st.session_state.raw_abs is not None:
#     st.subheader("Absorbance Parameters")
#     col1, col2 = st.columns(2)
#     with col1:
#         st.session_state.l1 = st.number_input(
#             "Pathlength (cm)", value=st.session_state.l1, min_value=0.001, step=0.01, key='l1_input'
#         )
#     with col2:
#         st.session_state.c1 = st.number_input(
#             "Concentration (mol/L)", value=st.session_state.c1, min_value=0.001, step=0.001, key='c1_input'
#         )
    
#     if st.button("Calculate Extinction Coefficient", key='calc_extinction_btn'):
#         wavelengths, extinction, error = calculate_extinction(
#             st.session_state.raw_abs, st.session_state.l1, st.session_state.c1
#         )
#         if error:
#             st.error(error)
#         else:
#             st.session_state.extinction = extinction
#             st.success("✓ Extinction coefficient calculated")
    
#     if st.session_state.extinction is not None:
#         # Plot extinction
#         fig, ax = plt.subplots(figsize=(10, 4))
#         ax.plot(st.session_state.wavelengths, st.session_state.extinction, linewidth=2, color='steelblue')
#         ax.set_title('Calculated Extinction Coefficient (M⁻¹ cm⁻¹)', fontsize=12, fontweight='bold')
#         ax.set_xlabel('Wavelength (nm)', fontsize=11)
#         ax.set_ylabel('Extinction Coefficient (M⁻¹ cm⁻¹)', fontsize=11)
#         ax.grid(alpha=0.3)
#         st.pyplot(fig)
        
#         # Show statistics
#         col1, col2, col3 = st.columns(3)
#         col1.metric("Min", f"{np.min(st.session_state.extinction):.2e}")
#         col2.metric("Max", f"{np.max(st.session_state.extinction):.2e}")
#         col3.metric("Peak Wavelength", f"{st.session_state.wavelengths[np.argmax(st.session_state.extinction)]:.1f} nm")


# # ============================================================================
# # STEP 2: NEW ABSORBANCE
# # ============================================================================
# if st.session_state.extinction is not None:
#     st.header("📈 Step 2: Scale to New Conditions")
    
#     col1, col2 = st.columns(2)
#     with col1:
#         st.session_state.l2 = st.number_input(
#             "FTIR Pathlength (cm)", value=st.session_state.l2, min_value=0.001, step=0.01, key='l2_input'
#         )
#     with col2:
#         st.session_state.c2 = st.number_input(
#             "FTIR Concentration (mol/L)", value=st.session_state.c2, min_value=0.001, step=0.001, key='c2_input'
#         )
    
#     if st.button("Calculate New Absorbance", key='calc_new_abs_btn'):
#         new_abs, error = calculate_new_absorbance(st.session_state.extinction, st.session_state.l2, st.session_state.c2)
#         if error:
#             st.error(error)
#         else:
#             st.session_state.new_abs = new_abs
#             st.success("✓ New absorbance calculated")
    
#     if st.session_state.new_abs is not None:
#         # Plot new absorbance
#         fig, ax = plt.subplots(figsize=(10, 4))
#         ax.plot(st.session_state.wavelengths, st.session_state.new_abs, linewidth=2, color='darkgreen')
#         ax.set_title('New Absorbance Data', fontsize=12, fontweight='bold')
#         ax.set_xlabel('Wavelength (nm)', fontsize=11)
#         ax.set_ylabel('Absorbance', fontsize=11)
#         ax.grid(alpha=0.3)
#         st.pyplot(fig)


# # ============================================================================
# # STEP 3: LED EMISSION DATA
# # ============================================================================
# if st.session_state.new_abs is not None:
#     st.header("💡 Step 3: LED Emission Data")
    
#     col1, col2 = st.columns([2, 1])
#     with col1:
#         led_file = st.file_uploader("Upload LED emission Excel file", type=['xls', 'xlsx'], key='led_file_uploader')
    
#     with col2:
#         if st.button("Load LED Data", key='load_led_btn'):
#             if led_file:
#                 raw_led, error = load_led_data(led_file)
#                 if error:
#                     st.error(error)
#                 else:
#                     st.session_state.raw_led = raw_led
#                     st.session_state.led_wavelengths = raw_led[:, 0].astype(float)
#                     st.success("✓ LED data loaded")
    
#     if st.session_state.raw_led is not None:
#         # Baseline LED
#         if st.button("Baseline LED Data", key='baseline_led_btn'):
#             base_led, led_min, error = baseline_led(st.session_state.raw_led)
#             if error:
#                 st.error(error)
#             else:
#                 st.session_state.base_led = base_led
#                 st.success(f"✓ LED baselined (minimum value: {led_min:.2e})")
        
#         if st.session_state.base_led is not None:
#             # Plot raw vs baselined LED
#             fig, ax = plt.subplots(figsize=(10, 4))
#             ax.plot(st.session_state.led_wavelengths, st.session_state.raw_led[:, 1], 
#                    label='Raw LED', linewidth=2, marker='o', markersize=3, alpha=0.6)
#             ax.plot(st.session_state.led_wavelengths, st.session_state.base_led, 
#                    label='Baselined LED', linewidth=2, marker='s', markersize=3, alpha=0.6)
#             ax.set_title('Raw vs Baselined LED Emission Spectra', fontsize=12, fontweight='bold')
#             ax.set_xlabel('Wavelength (nm)', fontsize=11)
#             ax.set_ylabel('Counts', fontsize=11)
#             ax.legend()
#             ax.grid(alpha=0.3)
#             st.pyplot(fig)
            
#             # LED intensity input
#             st.session_state.intensity = st.number_input(
#                 "LED Intensity (mW/cm²)", value=st.session_state.intensity, min_value=0.001, step=0.1, key='intensity_input'
#             )
            
#             # Normalize LED area
#             if st.button("Normalize LED Area", key='normalize_led_btn'):
#                 led_area_norm, conv_factor, error = normalize_led_area(
#                     st.session_state.led_wavelengths, st.session_state.base_led, st.session_state.intensity
#                 )
#                 if error:
#                     st.error(error)
#                 else:
#                     st.session_state.led_area_norm = led_area_norm
#                     st.session_state.conversion_factor = conv_factor
#                     st.success(f"✓ LED area normalized (Conversion Factor: {conv_factor:.4e})")
            
#             if st.session_state.led_area_norm is not None:
#                 # Plot comparison
#                 fig, ax = plt.subplots(figsize=(10, 4))
#                 ax.plot(st.session_state.led_wavelengths, st.session_state.base_led, 
#                        label='Baselined LED', linewidth=2, alpha=0.6)
#                 ax.plot(st.session_state.led_wavelengths, st.session_state.led_area_norm, 
#                        label='Area-Normalized LED', linewidth=2, alpha=0.6)
#                 ax.set_title('Baselined vs Area-Normalized LED', fontsize=12, fontweight='bold')
#                 ax.set_xlabel('Wavelength (nm)', fontsize=11)
#                 ax.set_ylabel('Intensity (area-normalized to intensity)', fontsize=11)
#                 ax.legend()
#                 ax.grid(alpha=0.3)
#                 st.pyplot(fig)


# # ============================================================================
# # STEP 4: GAUSSIAN FIT FOR LED
# # ============================================================================
# if st.session_state.led_area_norm is not None:
#     st.header("🔧 Step 4: Gaussian Fit for LED Emission")
    
#     n_gaussians = st.slider("Number of Gaussian components", min_value=1, max_value=5, value=2)
    
#     if st.button("Fit Gaussian to LED", key='fit_gaussian_btn'):
#         fit_func, fitted_vals, error = gaussian_fit_led(
#             st.session_state.led_wavelengths, st.session_state.led_area_norm, n_gaussians
#         )
#         if error:
#             st.error(error)
#         else:
#             # Interpolate fitted values to wavelengths from absorbance data
#             st.session_state.gauss_led = fit_func(st.session_state.wavelengths)
#             st.success(f"✓ Gaussian fit completed ({n_gaussians} component(s))")
    
#     if st.session_state.gauss_led is not None:
#         # Plot fit
#         fit_func, fitted_vals, _ = gaussian_fit_led(
#             st.session_state.led_wavelengths, st.session_state.led_area_norm, n_gaussians
#         )
        
#         fig, ax = plt.subplots(figsize=(10, 4))
#         ax.plot(st.session_state.led_wavelengths, st.session_state.led_area_norm, 
#                'o', label='Area-Normalized LED', markersize=4, alpha=0.6)
#         ax.plot(st.session_state.led_wavelengths, fitted_vals, 
#                '-', label='Gaussian Fit', linewidth=2.5)
#         ax.set_title('Area-Normalized LED Emission with Gaussian Fit', fontsize=12, fontweight='bold')
#         ax.set_xlabel('Wavelength (nm)', fontsize=11)
#         ax.set_ylabel('Intensity (mW/cm²/nm)', fontsize=11)
#         ax.legend()
#         ax.grid(alpha=0.3)
#         st.pyplot(fig)


# # ============================================================================
# # STEP 5: PHOTON CALCULATIONS
# # ============================================================================
# if st.session_state.gauss_led is not None:
#     st.header("⚛️ Step 5: Photon Calculations")
    
#     if st.button("Calculate Photon Metrics", key='calc_photons_btn'):
#         metrics = calculate_photon_metrics(
#             st.session_state.wavelengths, 
#             st.session_state.gauss_led, 
#             st.session_state.new_abs
#         )
        
#         if metrics.get('error'):
#             st.error(metrics['error'])
#         else:
#             st.session_state.photon_metrics = metrics
            
#             # Calculate totals
#             abs_result = calculate_absorbed_photons(
#                 st.session_state.wavelengths,
#                 metrics['NP'],
#                 metrics['FPA']
#             )
            
#             if abs_result.get('error'):
#                 st.error(abs_result['error'])
#             else:
#                 st.session_state.total_absorbed = abs_result['total_absorbed']
#                 st.session_state.total_led = abs_result['total_led']
#                 st.session_state.efficiency = abs_result['efficiency']
#                 st.success("✓ Photon metrics calculated")
    
#     if st.session_state.photon_metrics is not None:
#         metrics = st.session_state.photon_metrics
        
#         # Display 4 plots in 2x2 grid
#         col1, col2 = st.columns(2)
        
#         with col1:
#             fig, ax = plt.subplots(figsize=(8, 4))
#             ax.plot(st.session_state.wavelengths, metrics['NP'], linewidth=2, color='purple')
#             ax.set_title('Number of Photons vs Wavelength', fontsize=11, fontweight='bold')
#             ax.set_xlabel('Wavelength (nm)', fontsize=10)
#             ax.set_ylabel('Photons', fontsize=10)
#             ax.grid(alpha=0.3)
#             st.pyplot(fig)
        
#         with col2:
#             fig, ax = plt.subplots(figsize=(8, 4))
#             ax.plot(st.session_state.wavelengths, metrics['FPT'], linewidth=2, color='orange')
#             ax.set_title('Fraction Photons Transmitted', fontsize=11, fontweight='bold')
#             ax.set_xlabel('Wavelength (nm)', fontsize=10)
#             ax.set_ylabel('Fraction Transmitted', fontsize=10)
#             ax.grid(alpha=0.3)
#             st.pyplot(fig)
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             fig, ax = plt.subplots(figsize=(8, 4))
#             ax.plot(st.session_state.wavelengths, metrics['FPA'], linewidth=2, color='red')
#             ax.set_title('Fraction Photons Absorbed', fontsize=11, fontweight='bold')
#             ax.set_xlabel('Wavelength (nm)', fontsize=10)
#             ax.set_ylabel('Fraction Absorbed', fontsize=10)
#             ax.grid(alpha=0.3)
#             st.pyplot(fig)
        
#         with col2:
#             fig, ax = plt.subplots(figsize=(8, 4))
#             ax.plot(st.session_state.wavelengths, metrics['NRG'], linewidth=2, color='brown')
#             ax.set_title('Energy per Photon vs Wavelength', fontsize=11, fontweight='bold')
#             ax.set_xlabel('Wavelength (nm)', fontsize=10)
#             ax.set_ylabel('Energy (J)', fontsize=10)
#             ax.grid(alpha=0.3)
#             st.pyplot(fig)
        
#         # Display summary metrics
#         st.subheader("Photon Summary")
#         col1, col2, col3 = st.columns(3)
#         col1.metric("Total LED Photons", f"{st.session_state.total_led:.2e} photons/cm²/s")
#         col2.metric("Total Absorbed Photons", f"{st.session_state.total_absorbed:.2e} photons/cm²/s")
#         col3.metric("Absorption Efficiency", f"{st.session_state.efficiency:.2f}%")


# # ============================================================================
# # STEP 6: QUANTUM YIELD CALCULATION
# # ============================================================================
# if st.session_state.total_absorbed is not None:
#     st.header("🎯 Step 6: Quantum Yield Calculation")
    
#     col1, col2 = st.columns(2)
#     with col1:
#         rate_ftir = st.number_input(
#             "FTIR Conversion Fraction (fraction/s)", value=1e-4, format="%.2e", min_value=1e-10, step=1e-5
#         )
#     with col2:
#         monomer_conc = st.number_input(
#             "Monomer Concentration (mol/L)", value=0.01, min_value=1e-6, step=0.001
#         )
    
#     if st.button("Calculate Quantum Yields", key='calc_qy_btn'):
#         qy_result = calculate_quantum_yields(
#             rate_ftir,
#             st.session_state.l2,
#             monomer_conc,
#             st.session_state.total_led,
#             st.session_state.total_absorbed
#         )
        
#         if qy_result.get('error'):
#             st.error(qy_result['error'])
#         else:
#             st.success("✓ Quantum yields calculated")
            
#             # Display results
#             st.subheader("Results")
#             col1, col2, col3 = st.columns(3)
#             col1.metric(
#                 "External Quantum Yield",
#                 f"{qy_result['external_qy']:.4f}",
#                 help="Molecules converted / incident photons"
#             )
#             col2.metric(
#                 "Internal Quantum Yield",
#                 f"{qy_result['internal_qy']:.4f}",
#                 help="Molecules converted / absorbed photons"
#             )
#             col3.metric(
#                 "Molecules Converted",
#                 f"{qy_result['rate_molecules']:.2e} molecules/cm²/s"
#             )
            
#             # Summary table
#             st.subheader("Summary Report")
#             summary_data = {
#                 'Parameter': [
#                     'Absorbance Pathlength (cm)',
#                     'Absorbance Concentration (mol/L)',
#                     'FTIR Pathlength (cm)',
#                     'FTIR Concentration (mol/L)',
#                     'LED Intensity (mW/cm²)',
#                     'FTIR Conversion Rate (1/s)',
#                     'Monomer Concentration (mol/L)',
#                     '',
#                     'Total LED Photons (photons/cm²/s)',
#                     'Total Absorbed Photons (photons/cm²/s)',
#                     'Absorption Efficiency (%)',
#                     'External Quantum Yield',
#                     'Internal Quantum Yield'
#                 ],
#                 'Value': [
#                     f"{st.session_state.l1:.6f}",
#                     f"{st.session_state.c1:.6f}",
#                     f"{st.session_state.l2:.6f}",
#                     f"{st.session_state.c2:.6f}",
#                     f"{st.session_state.intensity:.6f}",
#                     f"{rate_ftir:.2e}",
#                     f"{monomer_conc:.6f}",
#                     '',
#                     f"{st.session_state.total_led:.4e}",
#                     f"{st.session_state.total_absorbed:.4e}",
#                     f"{st.session_state.efficiency:.2f}",
#                     f"{qy_result['external_qy']:.6f}",
#                     f"{qy_result['internal_qy']:.6f}"
#                 ]
#             }
#             summary_df = pd.DataFrame(summary_data)
#             st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
#     # Reset button
#     if st.button("Reset All Data", key='reset_btn'):
#         for key in st.session_state.keys():
#             del st.session_state[key]
#         st.rerun()
