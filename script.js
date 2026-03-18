function getWavelengths(n) {
  const start = 450;
  const end = 650;
  const wavelengths = [];
  for (let i = 0; i < n; i++) {
    wavelengths.push(start + (end - start) * i / (n - 1));
  }
  return wavelengths;
}

function attenuationCoefficient(baseK, wavelength) {
  // Placeholder example.
  // Replace this with your real math later.
  const shift = (wavelength - 550) / 100;
  return baseK * (1 + 0.3 * shift * shift);
}

function runSimulation() {
  const i0 = parseFloat(document.getElementById("i0").value);
  const baseK = parseFloat(document.getElementById("k").value);
  const L = parseFloat(document.getElementById("L").value);
  const nWaves = parseInt(document.getElementById("nWaves").value, 10);

  const wavelengths = getWavelengths(nWaves);
  const x = [];
  for (let i = 0; i <= 100; i++) {
    x.push((L * i) / 100);
  }

  const traces = wavelengths.map((wavelength) => {
    const k = attenuationCoefficient(baseK, wavelength);
    const y = x.map(distance => i0 * Math.exp(-k * distance));

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

  Plotly.newPlot("plot", traces, layout, { responsive: true });
}

document.getElementById("updateBtn").addEventListener("click", runSimulation);
runSimulation();
