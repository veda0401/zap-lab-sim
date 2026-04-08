// ==============================
// Global constants
// ==============================
const PLANCK = 6.626e-34;
const LIGHT_SPEED = 299792458;
const AVOGADRO = 6.022e23;

// ==============================
// File reading helpers
// ==============================
async function readExcelFile(file) {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });

  // Keep only rows with at least 2 columns and numeric first two values
  const cleanRows = rows
    .filter(row => row.length >= 2)
    .map(row => [Number(row[0]), Number(row[1])])
    .filter(row => !Number.isNaN(row[0]) && !Number.isNaN(row[1]));

  return cleanRows;
}

// ==============================
// Math helpers
// ==============================
function trapz(x, y) {
  let area = 0;
  for (let i = 1; i < x.length; i++) {
    area += 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1]);
  }
  return area;
}

function gaussian(x, a, b, c) {
  return a * Math.exp(-((x - b) / c) ** 2);
}

// Simple multi-gaussian approximation.
// This is a starter approximation, not a full optimizer.
function buildGaussianFit(xVals, yVals, nGaussians) {
  const maxY = Math.max(...yVals);
  const minX = xVals[0];
  const maxX = xVals[xVals.length - 1];
  const width = (maxX - minX) / (2 * nGaussians);

  const centers = [];
  for (let i = 0; i < nGaussians; i++) {
    centers.push(minX + ((i + 1) * (maxX - minX)) / (nGaussians + 1));
  }

  return xVals.map(x => {
    let sum = 0;
    for (let i = 0; i < centers.length; i++) {
      sum += gaussian(x, maxY / nGaussians, centers[i], width);
    }
    return sum;
  });
}

// ==============================
// Main calculation
// ==============================
function runCalculation(absData, ledData, inputs) {
  const wavelengths = absData.map(r => r[0]);
  const absorbance = absData.map(r => r[1]);

  const ledWavelengths = ledData.map(r => r[0]);
  const rawLED = ledData.map(r => r[1]);

  // Extinction
  const extinction = absorbance.map(a => a / (inputs.l1 * inputs.c1));

  // New absorbance
  const newAbs = extinction.map(e => e * inputs.l2 * inputs.c2);

  // Baselined LED
  const ledMin = Math.min(...rawLED);
  const baseLED = rawLED.map(v => v - ledMin);

  // Normalize LED area to intensity
  const ledIntegral = trapz(ledWavelengths, baseLED);
  const conversionFactor = ledIntegral / inputs.intensity;
  const ledAreaNorm = baseLED.map(v => v / conversionFactor);

  // Simple gaussian approximation
  const gaussLEDOnLEDGrid = buildGaussianFit(
    ledWavelengths,
    ledAreaNorm,
    inputs.nGaussians
  );

  // Interpolate LED fit onto absorbance wavelength grid
  const gaussLED = wavelengths.map(w => interpolate(ledWavelengths, gaussLEDOnLEDGrid, w));

  // Photon energy
  const NRG = wavelengths.map(w => PLANCK * LIGHT_SPEED / (w * 1e-9));

  // Number of photons
  const NP = gaussLED.map((g, i) => (g / 1000) / NRG[i]);

  // Fractions
  const FPT = newAbs.map(a => 10 ** (-a));
  const FPA = FPT.map(v => 1 - v);

  // Absorbed photons
  const AP = NP.map((n, i) => n * FPA[i]);
  const totalAbsorbed = trapz(wavelengths, AP);
  const totalLED = trapz(wavelengths, NP);
  const efficiency = (totalAbsorbed / totalLED) * 100;

  // Molecules converted per second
  const moleculesConverted =
    inputs.rateFTIR * inputs.l2 * inputs.monomerConc * AVOGADRO / 1000;

  // Simple QY estimates
  const externalQY = moleculesConverted / totalLED;
  const internalQY = moleculesConverted / totalAbsorbed;

  return {
    wavelengths,
    ledWavelengths,
    extinction,
    newAbs,
    rawLED,
    baseLED,
    ledAreaNorm,
    gaussLEDOnLEDGrid,
    gaussLED,
    NRG,
    NP,
    FPT,
    FPA,
    totalAbsorbed,
    totalLED,
    efficiency,
    externalQY,
    internalQY
  };
}

// ==============================
// Interpolation helper
// ==============================
function interpolate(x, y, x0) {
  if (x0 <= x[0]) return y[0];
  if (x0 >= x[x.length - 1]) return y[y.length - 1];

  for (let i = 1; i < x.length; i++) {
    if (x0 <= x[i]) {
      const t = (x0 - x[i - 1]) / (x[i] - x[i - 1]);
      return y[i - 1] + t * (y[i] - y[i - 1]);
    }
  }
  return y[y.length - 1];
}

// ==============================
// Plot helpers
// ==============================
function plotLine(divId, x, y, title, xLabel, yLabel, name = "Data") {
  Plotly.newPlot(divId, [{
    x,
    y,
    mode: "lines",
    name
  }], {
    title,
    xaxis: { title: xLabel },
    yaxis: { title: yLabel }
  }, { responsive: true });
}

function plotTwoLines(divId, x1, y1, name1, x2, y2, name2, title, xLabel, yLabel) {
  Plotly.newPlot(divId, [
    { x: x1, y: y1, mode: "lines", name: name1 },
    { x: x2, y: y2, mode: "lines", name: name2 }
  ], {
    title,
    xaxis: { title: xLabel },
    yaxis: { title: yLabel }
  }, { responsive: true });
}

// ==============================
// Render results
// ==============================
function renderResults(result) {
  document.getElementById("results").innerHTML = `
    <div class="metric"><strong>Total LED Photons:</strong> ${result.totalLED.toExponential(4)}</div>
    <div class="metric"><strong>Total Absorbed Photons:</strong> ${result.totalAbsorbed.toExponential(4)}</div>
    <div class="metric"><strong>Absorption Efficiency (%):</strong> ${result.efficiency.toFixed(3)}</div>
    <div class="metric"><strong>External Quantum Yield:</strong> ${result.externalQY.toExponential(4)}</div>
    <div class="metric"><strong>Internal Quantum Yield:</strong> ${result.internalQY.toExponential(4)}</div>
  `;

  plotLine(
    "plotExtinction",
    result.wavelengths,
    result.extinction,
    "Extinction Coefficient",
    "Wavelength (nm)",
    "Extinction"
  );

  plotLine(
    "plotNewAbs",
    result.wavelengths,
    result.newAbs,
    "New Absorbance",
    "Wavelength (nm)",
    "Absorbance"
  );

  plotTwoLines(
    "plotLED",
    result.ledWavelengths,
    result.baseLED,
    "Baselined LED",
    result.ledWavelengths,
    result.ledAreaNorm,
    "Area-Normalized LED",
    "LED Spectra",
    "Wavelength (nm)",
    "Intensity"
  );

  plotLine(
    "plotPhoton",
    result.wavelengths,
    result.NP,
    "Photon Count vs Wavelength",
    "Wavelength (nm)",
    "Photons"
  );

  plotTwoLines(
    "plotFractions",
    result.wavelengths,
    result.FPT,
    "Fraction Transmitted",
    result.wavelengths,
    result.FPA,
    "Fraction Absorbed",
    "Photon Fractions",
    "Wavelength (nm)",
    "Fraction"
  );
}

// ==============================
// Button click handler
// ==============================
document.getElementById("runBtn").addEventListener("click", async () => {
  const status = document.getElementById("status");

  try {
    const absFile = document.getElementById("absFile").files[0];
    const ledFile = document.getElementById("ledFile").files[0];

    if (!absFile || !ledFile) {
      status.textContent = "Please upload both Excel files first.";
      return;
    }

    status.textContent = "Reading files...";

    const absData = await readExcelFile(absFile);
    const ledData = await readExcelFile(ledFile);

    const inputs = {
      l1: Number(document.getElementById("l1").value),
      c1: Number(document.getElementById("c1").value),
      l2: Number(document.getElementById("l2").value),
      c2: Number(document.getElementById("c2").value),
      intensity: Number(document.getElementById("intensity").value),
      rateFTIR: Number(document.getElementById("rateFTIR").value),
      monomerConc: Number(document.getElementById("monomerConc").value),
      nGaussians: Number(document.getElementById("nGaussians").value)
    };

    status.textContent = "Running calculations...";

    const result = runCalculation(absData, ledData, inputs);
    renderResults(result);

    status.textContent = "Calculation complete.";
  } catch (error) {
    console.error(error);
    status.textContent = "Something went wrong. Check the browser console.";
  }
});
