
// generates array of wavelength vals depending on n
function getWavelengths(n) {
  const start = 450;
  const end = 650;
  const wavelengths = [];
  for (let i = 0; i < n; i++) {

    // allow for even spacing
    wavelengths.push(start + (end - start) * i / (n - 1));
  }
  return wavelengths;
}

// calculates attenuation coefficient for given wl
function attenuationCoefficient(baseK, wavelength) {
  // replace with actual math -> scaled by 100 so value makes sense
  const shift = (wavelength - 550) / 100;
  return baseK * (1 + 0.3 * shift * shift);
}

// reads user input, computes curves, plots via plotly
function runSimulation() {

  //parseFloat converts the string input into a decimal #
  const i0 = parseFloat(document.getElementById("i0").value);
  const baseK = parseFloat(document.getElementById("k").value);
  const L = parseFloat(document.getElementById("L").value);
  const nWaves = parseInt(document.getElementById("nWaves").value, 10);

  const wavelengths = getWavelengths(nWaves);

  // x-vals for graoh
  const x = [];
  for (let i = 0; i <= 100; i++) {
    // divide interval from 0 to L into 100 equal pieces
    x.push((L * i) / 100);
  }

  // generate one curve for plot
  const traces = wavelengths.map((wavelength) => {
    const k = attenuationCoefficient(baseK, wavelength);
    const y = x.map(distance => i0 * Math.exp(-k * distance));

    // plotly trace object for this wavelength
    return {
      x,
      y,
      mode: "lines",
      name: `${Math.round(wavelength)} nm`
    };
  });

  const layout = {
    title: "Intensity vs. Path Length",
    xaxis: { title: "Path Length" },
    yaxis: { title: "Intensity" }
  };
  
  // draw graph inside HTML element id = plot
  Plotly.newPlot("plot", traces, layout, { responsive: true });
}

// event listener: when user clcks button, runSimulation() executes
document.getElementById("updateBtn").addEventListener("click", runSimulation);

// see graph right away w/o click
runSimulation();
