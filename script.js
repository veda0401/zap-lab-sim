const PLANCK = 6.626e-34;
const LIGHT_SPEED = 299792458;
const AVOGADRO = 6.022e23;

function setStatus(message, type = "info") {
  const status = document.getElementById("status");
  if (status) {
    status.textContent = message;
    status.className = `status ${type}`;
  }
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

  if (!Number.isInteger(inputs.nGaussians) || inputs.nGaussians < 1 || inputs.nGaussians > 5) {
    throw new Error("Number of Gaussian components must be an integer from 1 to 5.");
  }

  return inputs;
}

function trapz(x, y) {
  if (x.length !== y.length || x.length < 2) {
    throw new Error("trapz requires x and y arrays of the same length.");
  }

  let area = 0;
  for (let i = 1; i < x.length; i++) {
    area += 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1]);
  }
  return area;
}

function buildGaussianFit(xVals, yVals) {
  const maxY = Math.max(...yVals);

  if (!Number.isFinite(maxY) || maxY <= 0) {
    return [...yVals];
  }

  const maxIndex = yVals.indexOf(maxY);
  const peakX = xVals[maxIndex];

  const halfMax = maxY / 2;
  const aboveHalf = xVals.filter((x, i) => yVals[i] >= halfMax);

  const fwhm =
    aboveHalf.length > 1
      ? aboveHalf[aboveHalf.length - 1] - aboveHalf[0]
      : (xVals[xVals.length - 1] - xVals[0]) / 6;

  const sigma = Math.max(fwhm / 2.355, 1);

  let fitted = xVals.map((x) =>
    maxY * Math.exp(-0.5 * ((x - peakX) / sigma) ** 2)
  );

  const originalArea = trapz(xVals, yVals);
  const fitArea = trapz(xVals, fitted);

  if (fitArea > 0) {
    const scale = originalArea / fitArea;
    fitted = fitted.map((v) => v * scale);
  }

  return fitted;
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

  const gaussLEDOnLEDGrid = buildGaussianFit(ledWavelengths, ledAreaNorm);

  const newAbsOnLEDGrid = ledWavelengths.map((w) =>
    interpolate(wavelengths, newAbs, w)
  );

  const NRG = ledWavelengths.map((w) => PLANCK * LIGHT_SPEED / (w * 1e-9));
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

function baseLayout(plotNumber, xLabel, yLabel, options = {}) {
  return {
    annotations: [
      {
        text: `<b>${plotNumber}</b>`,
        xref: "paper",
        yref: "paper",
        x: 0,
        y: 1.12,
        showarrow: false,
        font: { size: 20 }
      }
    ],
    xaxis: {
      title: { text: xLabel, font: { size: 18 } },
      tickfont: { size: 14 },
      automargin: true
    },
    yaxis: {
      title: { text: yLabel, font: { size: 18 } },
      tickfont: { size: 14 },
      automargin: true,
      ...(options.scientificY ? { tickformat: ".2e" } : {})
    },
    margin: { t: 55, r: 40, b: 95, l: 120 },
    showlegend: options.showLegend ?? true,
    legend: { font: { size: 14 } },
    paper_bgcolor: "white",
    plot_bgcolor: "white"
  };
}

function plotLine(divId, x, y, plotNumber, xLabel, yLabel, name = "Data", options = {}) {
  Plotly.newPlot(
    divId,
    [{ x, y, mode: "lines", name }],
    baseLayout(plotNumber, xLabel, yLabel, options),
    { responsive: true }
  );
}

function plotTwoLines(divId, traces, plotNumber, xLabel, yLabel, options = {}) {
  Plotly.newPlot(
    divId,
    traces.map((trace) => ({
      x: trace.x,
      y: trace.y,
      mode: "lines",
      name: trace.name
    })),
    baseLayout(plotNumber, xLabel, yLabel, options),
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

  const maxAbs = Math.max(...result.newAbsOnLEDGrid);
  const maxLED = Math.max(...result.ledAreaNorm);

  const normAbs = result.newAbsOnLEDGrid.map((v) => (maxAbs > 0 ? v / maxAbs : 0));
  const normLED = result.ledAreaNorm.map((v) => (maxLED > 0 ? v / maxLED : 0));

  plotLine(
    "plotExtinction",
    result.wavelengths,
    result.extinction,
    "1",
    "Wavelength (nm)",
    "Calculated Extinction (M-1 cm-1)",
    "Data",
    { scientificY: true, showLegend: false }
  );

  plotTwoLines(
    "plotLEDGaussian",
    [
      { x: result.ledWavelengths, y: result.ledAreaNorm, name: "Raw LED" },
      { x: result.ledWavelengths, y: result.gaussLEDOnLEDGrid, name: "Gaussian Fit" }
    ],
    "2",
    "Wavelength (nm)",
    "mW cm-2 nm-1"
  );

  plotTwoLines(
    "plotOverlap",
    [
      { x: result.ledWavelengths, y: normAbs, name: "Sample" },
      { x: result.ledWavelengths, y: normLED, name: "LED" }
    ],
    "3",
    "Wavelength (nm)",
    "Normalized Intensity"
  );

  plotLine(
    "plotPhotonsEmitted",
    result.ledWavelengths,
    result.NP,
    "4",
    "Wavelength (nm)",
    "photons",
    "Data",
    { scientificY: true, showLegend: false }
  );

  plotLine(
    "plotFractionAbsorbed",
    result.ledWavelengths,
    result.FPA,
    "5",
    "Wavelength (nm)",
    "Fraction Absorbed",
    "Data",
    { showLegend: false }
  );

  plotTwoLines(
    "plotPhotonsAbsorbed",
    [
      { x: result.ledWavelengths, y: result.NP, name: "Photons Emitted" },
      { x: result.ledWavelengths, y: result.AP, name: "Photons Absorbed" }
    ],
    "6",
    "Wavelength (nm)",
    "photons",
    { scientificY: true }
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const runBtn = document.getElementById("runBtn");

  if (!runBtn) {
    console.error("Run button not found.");
    return;
  }

  runBtn.addEventListener("click", async () => {
    try {
      setStatus("Checking files and inputs...");

      const absFile = document.getElementById("absFile").files[0];
      const ledFile = document.getElementById("ledFile").files[0];

      if (!absFile || !ledFile) {
        throw new Error("Please upload both Excel files first.");
      }

      const inputs = getInputs();

      setStatus("Reading Excel files...");

      const absData = await readExcelFile(absFile);
      const ledData = await readExcelFile(ledFile);

      setStatus("Running calculations...");

      const result = calculateQuantumYield(absData, ledData, inputs);

      renderResults(result);

      setStatus("Calculation complete.", "success");
    } catch (error) {
      console.error(error);
      setStatus(error.message || "Something went wrong.", "error");
    }
  });
});
