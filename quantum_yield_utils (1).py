"""
Quantum Yield Calculator Utilities
Calculation functions for photon absorption and quantum yield analysis
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import streamlit as st


def load_absorbance_data(uploaded_file):
    """
    Load absorbance data from Excel file.
    Expected format: Column 1 = wavelengths, Column 2 = absorbance values
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Returns:
        tuple: (RawABS array, error message or None)
    """
    try:
        if uploaded_file is None:
            return None, "No file uploaded"
        
        df = pd.read_excel(uploaded_file, header=None)
        if df.shape[1] < 2:
            return None, "File must have at least 2 columns (wavelength, absorbance)"
        
        data = df.values
        
        # Validate data
        if len(data) < 2:
            return None, "File must have at least 2 data rows"
        
        # Check for numeric data
        try:
            wavelengths = pd.to_numeric(data[:, 0])
            absorbance = pd.to_numeric(data[:, 1])
        except:
            return None, "Columns must contain numeric values"
        
        # Check wavelength ordering
        if not np.all(np.diff(wavelengths) > 0):
            return None, "Wavelengths must be in increasing order"
        
        return data, None
    except Exception as e:
        return None, f"Error loading file: {str(e)}"


def calculate_extinction(raw_abs, L1, C1):
    """
    Calculate extinction coefficient from raw absorbance data.
    Formula: Extinction = Absorbance / (pathlength * concentration)
    
    Args:
        raw_abs: 2D array with wavelengths (col 0) and absorbance (col 1)
        L1: Pathlength in cm
        C1: Concentration in mol/L
        
    Returns:
        tuple: (wavelengths array, extinction array, error message or None)
    """
    try:
        if L1 <= 0 or C1 <= 0:
            return None, None, "Pathlength and concentration must be positive"
        
        wavelengths = raw_abs[:, 0].astype(float)
        absorbance = raw_abs[:, 1].astype(float)
        
        extinction = absorbance / (L1 * C1)
        
        return wavelengths, extinction, None
    except Exception as e:
        return None, None, f"Error calculating extinction: {str(e)}"


def calculate_new_absorbance(extinction, L2, C2):
    """
    Scale extinction coefficient to new pathlength and concentration.
    Formula: NewABS = Extinction * L2 * C2
    
    Args:
        extinction: Extinction coefficient array
        L2: New pathlength in cm
        C2: New concentration in mol/L
        
    Returns:
        tuple: (new_abs array, error message or None)
    """
    try:
        if L2 <= 0 or C2 <= 0:
            return None, "Pathlength and concentration must be positive"
        
        new_abs = extinction * L2 * C2
        return new_abs, None
    except Exception as e:
        return None, f"Error calculating new absorbance: {str(e)}"


def load_led_data(uploaded_file):
    """
    Load LED emission data from Excel file.
    Expected format: Column 1 = wavelengths, Column 2 = emission intensity
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Returns:
        tuple: (RawLED array, error message or None)
    """
    try:
        if uploaded_file is None:
            return None, "No file uploaded"
        
        df = pd.read_excel(uploaded_file, header=None)
        if df.shape[1] < 2:
            return None, "File must have at least 2 columns (wavelength, emission)"
        
        data = df.values
        
        if len(data) < 2:
            return None, "File must have at least 2 data rows"
        
        try:
            wavelengths = pd.to_numeric(data[:, 0])
            emission = pd.to_numeric(data[:, 1])
        except:
            return None, "Columns must contain numeric values"
        
        if not np.all(np.diff(wavelengths) > 0):
            return None, "Wavelengths must be in increasing order"
        
        return data, None
    except Exception as e:
        return None, f"Error loading LED file: {str(e)}"


def baseline_led(raw_led):
    """
    Baseline LED emission by subtracting minimum value.
    Formula: BaseLED = RawLED(:,2) - min(RawLED(:,2))
    
    Args:
        raw_led: 2D array with wavelengths (col 0) and emission (col 1)
        
    Returns:
        tuple: (baselED array, LEDmin value, error message or None)
    """
    try:
        led_emission = raw_led[:, 1].astype(float)
        led_min = np.min(led_emission)
        base_led = led_emission - led_min
        
        return base_led, led_min, None
    except Exception as e:
        return None, None, f"Error baselining LED: {str(e)}"


def normalize_led_area(wavelengths, base_led, intensity):
    """
    Normalize LED by integrating area under curve to equal intensity.
    Formula: LEDAreaNorm = BaseLED / ConversionFactor
    where ConversionFactor = LEDIntegral / Intensity
    
    This matches MATLAB implementation step at line 69-76.
    
    Args:
        wavelengths: LED wavelength array
        base_led: Baselined LED emission array
        intensity: Target intensity for normalization (mW/cm²)
        
    Returns:
        tuple: (normalized_led array, conversion_factor, error message or None)
    """
    try:
        if intensity <= 0:
            return None, None, "Intensity must be positive"
        
        # Calculate integral of baselined LED spectrum
        led_integral = np.trapz(base_led, wavelengths)
        
        if led_integral == 0:
            return None, None, "LED integral is zero"
        
        # Calculate conversion factor
        conversion_factor = led_integral / intensity
        
        # Normalize LED so area under curve equals intensity
        led_area_norm = base_led / conversion_factor
        
        return led_area_norm, conversion_factor, None
    except Exception as e:
        return None, None, f"Error normalizing LED area: {str(e)}"


def normalize_led_area(wavelengths, base_led, intensity):
    """
    Normalize LED by integrating area under curve to equal intensity.
    Formula: LEDAreaNorm = BaseLED / ConversionFactor
    where ConversionFactor = LEDIntegral / Intensity
    
    This matches MATLAB implementation step at line 69-76.
    
    Args:
        wavelengths: LED wavelength array
        base_led: Baselined LED emission array
        intensity: Target intensity for normalization (mW/cm²)
        
    Returns:
        tuple: (normalized_led array, conversion_factor, error message or None)
    """
    try:
        if intensity <= 0:
            return None, None, "Intensity must be positive"
        
        # Calculate integral of baselined LED spectrum
        led_integral = np.trapz(base_led, wavelengths)
        
        if led_integral == 0:
            return None, None, "LED integral is zero"
        
        # Calculate conversion factor
        conversion_factor = led_integral / intensity
        
        # Normalize LED so area under curve equals intensity
        led_area_norm = base_led / conversion_factor
        
        return led_area_norm, conversion_factor, None
    except Exception as e:
        return None, None, f"Error normalizing LED area: {str(e)}"


def gaussian_fit_led(wavelengths, emission, n_gaussians=2):
    """
    Fit Gaussian curve(s) to LED emission spectrum.
    
    Args:
        wavelengths: Wavelength array from LED data
        emission: Area-normalized LED emission array
        n_gaussians: Number of Gaussian components (default 2)
        
    Returns:
        tuple: (fit_function, fitted_values at original wavelengths, error message or None)
    """
    try:
        # Define multi-Gaussian function
        def multi_gaussian(x, *params):
            result = np.zeros_like(x, dtype=float)
            n_params = len(params) // 3
            for i in range(n_params):
                a = params[3*i]
                b = params[3*i + 1]
                c = params[3*i + 2]
                result += a * np.exp(-((x - b) / c)**2)
            return result
        
        # Initial parameter guess
        p0 = []
        step = len(wavelengths) // (n_gaussians + 1)
        for i in range(n_gaussians):
            idx = (i + 1) * step
            p0.extend([
                np.max(emission) / n_gaussians,  # amplitude
                wavelengths[idx],                 # center
                10                                # width
            ])
        
        # Fit curve
        popt, _ = curve_fit(multi_gaussian, wavelengths, emission, p0=p0, maxfev=10000)
        
        # Get fitted values at original wavelengths
        fitted_values = multi_gaussian(wavelengths, *popt)
        
        return lambda x: multi_gaussian(x, *popt), fitted_values, None
    except Exception as e:
        return None, None, f"Error fitting Gaussian to LED: {str(e)}"


def calculate_photon_metrics(wavelengths, gauss_led, new_abs):
    """
    Calculate photon-related metrics: energy, photon count, transmission/absorption fractions.
    
    Args:
        wavelengths: Wavelength array (nm)
        gauss_led: Gaussian-fitted LED emission (mW/cm²/nm)
        new_abs: New absorbance values
        
    Returns:
        dict with keys: 'NRG', 'NP', 'FPT', 'FPA', 'error' (if any)
    """
    try:
        # Physical constants
        h = 6.626e-34  # Planck constant (J·s)
        c = 299792458  # Speed of light (m/s)
        
        # Energy per photon (J)
        wavelengths_m = wavelengths * 1e-9  # Convert nm to m
        NRG = h * c / wavelengths_m
        
        # Number of photons (photons/(cm²·s))
        NP = gauss_led / 1000 / NRG  # Divide by 1000 to convert mW to W
        
        # Fraction of photons transmitted
        FPT = 10 ** (-new_abs)
        
        # Fraction of photons absorbed
        FPA = 1 - FPT
        
        return {
            'NRG': NRG,
            'NP': NP,
            'FPT': FPT,
            'FPA': FPA,
            'error': None
        }
    except Exception as e:
        return {'error': f"Error calculating photon metrics: {str(e)}"}


def calculate_absorbed_photons(wavelengths, np_array, fpa_array):
    """
    Calculate total absorbed photons and total LED photons via integration.
    
    Args:
        wavelengths: Wavelength array
        np_array: Number of photons array
        fpa_array: Fraction of photons absorbed array
        
    Returns:
        dict with keys: 'total_absorbed', 'total_led', 'efficiency', 'error' (if any)
    """
    try:
        # Photons absorbed per wavelength
        ap = np_array * fpa_array
        
        # Integration using trapezoidal rule
        total_absorbed = np.trapz(ap, wavelengths)
        total_led = np.trapz(np_array, wavelengths)
        
        if total_led == 0:
            return {'error': "Total LED photons is zero"}
        
        efficiency = (total_absorbed / total_led) * 100
        
        return {
            'total_absorbed': total_absorbed,
            'total_led': total_led,
            'efficiency': efficiency,
            'error': None
        }
    except Exception as e:
        return {'error': f"Error calculating absorbed photons: {str(e)}"}


def calculate_quantum_yields(rate_ftir, l2, monomer_conc, total_led_photons, total_absorbed_photons):
    """
    Calculate external and internal quantum yields.
    
    Args:
        rate_ftir: Conversion fraction per second from FTIR (1/s)
        l2: Pathlength for FTIR (cm)
        monomer_conc: Monomer concentration (mol/L)
        total_led_photons: Total number of LED photons (photons/cm²/s)
        total_absorbed_photons: Total number of absorbed photons (photons/cm²/s)
        
    Returns:
        dict with keys: 'external_qy', 'internal_qy', 'error' (if any)
    """
    try:
        if rate_ftir <= 0 or l2 <= 0 or monomer_conc <= 0:
            return {'error': "All inputs must be positive"}
        
        if total_led_photons == 0:
            return {'error': "Total LED photons cannot be zero"}
        
        Avogadro = 6.022e23
        
        # Rate of molecules converted (molecules/cm²/s)
        rate_molecules_converted = rate_ftir * l2 * monomer_conc * Avogadro * (1/1000)
        
        # External quantum yield (molecules converted / photons incident)
        external_qy = rate_molecules_converted / total_led_photons
        
        # Internal quantum yield (molecules converted / photons absorbed)
        if total_absorbed_photons == 0:
            return {'error': "Total absorbed photons cannot be zero"}
        
        internal_qy = rate_molecules_converted / total_absorbed_photons
        
        return {
            'external_qy': external_qy,
            'internal_qy': internal_qy,
            'rate_molecules': rate_molecules_converted,
            'error': None
        }
    except Exception as e:
        return {'error': f"Error calculating quantum yields: {str(e)}"}
