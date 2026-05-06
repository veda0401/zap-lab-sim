const PLANCK = 6.626e-34;
const LIGHT_SPEED = 299792458;
const AVOGADRO = 6.022e23;

function setStatus(message, type = "info") {
  const status = document.getElementById("status");
  status.textContent = message;
  status.className = `status ${type}`;
}

function formatExp(value, digits = 4) {
  if (!Number.isFinite(value)) return "—";
  return value.toExponential(digits);
}

function formatFixed(value, digits = 3) {
  if (!Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

async function readExcelFile(file) {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });

  const cleanRows = rows
    .filter((row) => row.length >= 2)
    .map((row) => [Number(row[0]), Number(row[1])])
    .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y))
    .sort((a, b) => a[0] - b[0]);

  if (cleanRows.length < 2) {
    throw new Error("File must contain at least 2 numeric rows.");
  }

  return cleanRows;
}

function getInputs() {
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

  for (const key of ["l1", "c1", "l2", "c2", "intensity", "rateFTIR", "monomerConc"]) {
    if (!Number.isFinite(inputs[key]) || inputs[key] <= 0) {
      throw new Error(`${key} must be a positive number.`);
    }
  }

  return inputs;
}

function trapz(x, y) {
  let area = 0;
  for (let i = 1; i < x.length; i++) {
    area += 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1]);
  }
  return area;
}

function gaussian(x, a, b, c) {
  return a * Math.exp(-(((x - b) / c) ** 2));
}

function buildGaussianFit(xVals, yVals, nGaussians) {
  const maxY = Math.max(...yVals);
  const minX = xVals[0];
  const maxX = xVals[xVals.length - 1];
  const span = maxX - minX;
  const width = Math.max(span / (3 * nGaussians), 1);

  const centers = [];
  for (let i = 0; i < nGaussians; i++) {
    centers.push(minX + ((i + 1) * span) / (nGaussians + 1));
  }

  const fitted = xVals.map((x) => {
    let sum = 0;
    for (const center of centers) {
      sum += gaussian(x, maxY / nGaussians, center, width);
    }
    return sum;
  });

  const originalArea = trapz(xVals, yVals);
  const fitArea = trapz(xVals, fitted);

  if (fitArea <= 0) return [...yVals];

  const scale = originalArea / fitArea;
  return fitted.map((v) => v * scale);
}

function interpolate(x, y, x0) {
  if (x0 <= x[0]) return y[0];
  if (x0 >= x[x.length - 1]) return y[y.length - 1];

  for (let i = 1; i < x.length; i++) {
    if (x[i] >= x0) {
      const t = (x0 - x[i - 1]) / (x[i] - x[i - 1]);
      return y[i - 1] + t * (y[i] - y[i - 1]);
    }
  }

  return y[y.length - 1];
}

function calculateQuantumYield(absData, ledData, inputs) {
  const wavelengths = absData.map((r) => r[0]);
  const absorbance = absData.map((r) => r[1]);

  const ledWavelengths = ledData.map((r) => r[0]);
  const rawLED = ledData.map((r) => r[1]);

  const extinction = absorbance.map((a) => a / (inputs.l1 * inputs.c1));
  const newAbs = extinction.map((e) => e * inputs.l2 * inputs.c2);

  const ledMin = Math.min(...rawLED);
  const baseLED = rawLED.map((v) => v - ledMin);

  const ledIntegral = trapz(ledWavelengths, baseLED);
  if (ledIntegral === 0) {
    throw new Error("LED integral is zero after baselining.");
  }

  const conversionFactor = ledIntegral / inputs.intensity;
  const ledAreaNorm = baseLED.map((v) => v / conversionFactor);

  const gaussLEDOnLEDGrid = buildGaussianFit(
    ledWavelengths,
    ledAreaNorm,
    inputs.nGaussians
  );

  const newAbsOnLEDGrid = ledWavelengths.map((w) =>
    interpolate(wavelengths, newAbs, w)
  );

  const NRG = ledWavelengths.map(
    (w) => PLANCK * LIGHT_SPEED / (w * 1e-9)
  );

  const NP = ledAreaNorm.map((g, i) => (g / 1000) / NRG[i]);

  const FPT = newAbsOnLEDGrid.map((a) => 10 ** (-a));
  const FPA = FPT.map((v) => 1 - v);

  const AP = NP.map((n, i) => n * FPA[i]);

  const totalAbsorbed = trapz(ledWavelengths, AP);
  const totalLED = trapz(ledWavelengths, NP);

  const efficiency = (totalAbsorbed / totalLED) * 100;

  const moleculesConverted =
    (inputs.rateFTIR * inputs.l2 * inputs.monomerConc * AVOGADRO) / 1000;

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
    newAbsOnLEDGrid,
    NP,
    FPA,
    AP,
    totalAbsorbed,
    totalLED,
    efficiency,
    moleculesConverted,
    externalQY,
    internalQY
  };
}

function baseLayout(title, xLabel, yLabel) {
  return {
    title: {
      text: title,
      font: {
        size: 22
      }
    },

    xaxis: {
      title: {
        text: xLabel,
        font: {
          size: 18
        }
      },
      tickfont: {
        size: 14
      },
      automargin: true
    },

    yaxis: {
      title: {
        text: yLabel,
        font: {
          size: 18
        }
      },
      tickfont: {
        size: 14
      },
      automargin: true
    },

    margin: {
      t: 80,
      r: 40,
      b: 90,
      l: 110
    },

    showlegend: true,

    legend: {
      font: {
        size: 14
      }
    },

    paper_bgcolor: "white",
    plot_bgcolor: "white"
  };
}

function plotLine(divId, x, y, title, xLabel, yLabel, name = "Data") {
  Plotly.newPlot(
    divId,
    [
      {
        x,
        y,
        mode: "lines",
        name
      }
    ],
    baseLayout(title, xLabel, yLabel),
    { responsive: true }
  );
}

function plotTwoLines(divId, traces, title, xLabel, yLabel) {
  Plotly.newPlot(
    divId,
    traces.map((trace) => ({
      x: trace.x,
      y: trace.y,
      mode: "lines",
      name: trace.name
    })),
    baseLayout(title, xLabel, yLabel),
    { responsive: true }
  );
}

function renderResults(result) {
  document.getElementById("results").innerHTML = `
    <div class="results-grid">
      <div class="metric-card">
        <span class="metric-label">Total LED Photons</span>
        <span class="metric-value">${formatExp(result.totalLED)}</span>
      </div>

      <div class="metric-card">
        <span class="metric-label">Total Absorbed Photons</span>
        <span class="metric-value">${formatExp(result.totalAbsorbed)}</span>
      </div>

      <div class="metric-card">
        <span class="metric-label">Absorption Efficiency</span>
        <span class="metric-value">${formatFixed(result.efficiency)}%</span>
      </div>

      <div class="metric-card">
        <span class="metric-label">Molecules Converted</span>
        <span class="metric-value">${formatExp(result.moleculesConverted)}</span>
      </div>

      <div class="metric-card">
        <span class="metric-label">External Quantum Yield</span>
        <span class="metric-value">${formatExp(result.externalQY)}</span>
      </div>

      <div class="metric-card">
        <span class="metric-label">Internal Quantum Yield</span>
        <span class="metric-value">${formatExp(result.internalQY)}</span>
      </div>
    </div>
  `;

  plotLine(
    "plotExtinction",
    result.wavelengths,
    result.extinction,
    "Calculated Extinction Coefficient",
    "Wavelength (nm)",
    "Extinction Coefficient (L·mol⁻¹·cm⁻¹)"
  );

  plotTwoLines(
    "plotLEDGaussian",
    [
      {
        x: result.ledWavelengths,
        y: result.ledAreaNorm,
        name: "Raw LED"
      },
      {
        x: result.ledWavelengths,
        y: result.gaussLEDOnLEDGrid,
        name: "Gaussian Fit"
      }
    ],
    "Raw LED and Gaussian Fit",
    "Wavelength (nm)",
    "LED Intensity (mW·cm⁻²·nm⁻¹)"
  );

  const maxAbs = Math.max(...result.newAbsOnLEDGrid);
  const maxLED = Math.max(...result.ledAreaNorm);

  const normAbs = result.newAbsOnLEDGrid.map((v) =>
    maxAbs > 0 ? v / maxAbs : 0
  );

  const normLED = result.ledAreaNorm.map((v) =>
    maxLED > 0 ? v / maxLED : 0
  );

  plotTwoLines(
    "plotOverlap",
    [
      {
        x: result.ledWavelengths,
        y: normAbs,
        name: "Sample"
      },
      {
        x: result.ledWavelengths,
        y: normLED,
        name: "LED"
      }
    ],
    "Normalized Absorbance and LED Overlap",
    "Wavelength (nm)",
    "Normalized Intensity"
  );

  plotLine(
    "plotPhotonsEmitted",
    result.ledWavelengths,
    result.NP,
    "LED Photons Emitted",
    "Wavelength (nm)",
    "Photon Flux (photons·s⁻¹·nm⁻¹)"
  );

  plotLine(
    "plotFractionAbsorbed",
    result.ledWavelengths,
    result.FPA,
    "Fraction Photons Absorbed",
    "Wavelength (nm)",
    "Fraction Absorbed"
  );

  plotTwoLines(
    "plotPhotonsAbsorbed",
    [
      {
        x: result.ledWavelengths,
        y: result.NP,
        name: "Photons Emitted"
      },
      {
        x: result.ledWavelengths,
        y: result.AP,
        name: "Photons Absorbed"
      }
    ],
    "Photons Emitted and Absorbed",
    "Wavelength (nm)",
    "Photon Flux (photons·s⁻¹·nm⁻¹)"
  );
}
