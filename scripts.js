// Define versions for dynamic content
const version1 = "7.2.6";
const version2 = "unstable";

// Update the title dynamically
document.addEventListener('DOMContentLoaded', () => {
    document.title = `Valkey ${version1.substring(0, 7)} vs ${version2.substring(0, 7)} Benchmark Results Comparison`;
});

// Function to fetch and parse CSV data
async function fetchCsvData(filePath) {
    try {
        const response = await fetch(filePath);
        const csvText = await response.text();
        return csvText.split("\n").map(row => row.split(","));
    } catch (error) {
        console.error(`Error fetching CSV data from ${filePath}:`, error);
        return [];
    }
}

// Function to calculate averages for each unique combination of Command, Pipeline, and Data Size
function calculateAverages(data) {
    const averages = {};

    data.slice(1).forEach(row => {
        if (row.length < 8) return;

        const key = `${row[3]}_${row[4]}_${row[5]}`;
        const rps = parseFloat(row[6]);
        const avgLatency = parseFloat(row[7]);

        if (!averages[key]) {
            averages[key] = { count: 0, totalRps: 0, totalLatency: 0 };
        }
        averages[key].count += 1;
        averages[key].totalRps += rps;
        averages[key].totalLatency += avgLatency;
    });

    const averagedData = {};

    Object.keys(averages).forEach(key => {
        const avgRps = (averages[key].totalRps / averages[key].count).toFixed(2);
        const avgLatency = (averages[key].totalLatency / averages[key].count).toFixed(2);

        averagedData[key] = { avgRps, avgLatency };
    });

    return averagedData;
}

// Function to compare the averages between two versions
function compareAverages(version1Data, version2Data) {
    const comparisonData = [];

    Object.keys(version1Data).forEach(key => {
        if (version2Data[key]) {
            const version1 = version1Data[key];
            const version2 = version2Data[key];

            const rpsGain = (((version2.avgRps - version1.avgRps) / version1.avgRps) * 100).toFixed(2);
            const latencyGain = (((version1.avgLatency - version2.avgLatency) / version1.avgLatency) * 100).toFixed(2);

            comparisonData.push({
                key,
                version1Rps: version1.avgRps,
                version2Rps: version2.avgRps,
                rpsGain,
                version1Latency: version1.avgLatency,
                version2Latency: version2.avgLatency,
                latencyGain,
            });
        }
    });

    return comparisonData;
}

// Function to create a table to display the comparison results
function createComparisonTable(data, version1, version2) {
    const table = document.createElement("table");

    const headerRow = document.createElement("tr");
    const headers = [
        "Command",
        "Pipeline",
        "Data Size",
        `RPS - ${version1.substring(0, 7)}`,
        `RPS - ${version2.substring(0, 7)}`,
        "RPS Gain (%)",
        `${version1.substring(0, 7)} Latency (ms)`,
        `${version2.substring(0, 7)} Latency (ms)`,
        "Latency Gain (%)"
    ];

    headers.forEach(header => {
        const th = document.createElement("th");
        th.innerText = header;
        headerRow.appendChild(th);
    });

    table.appendChild(headerRow);

    data.forEach(row => {
        const tr = document.createElement("tr");

        const [command, pipeline, dataSize] = row.key.split("_");
        const values = [
            command,
            pipeline,
            dataSize,
            row.version1Rps,
            row.version2Rps,
            row.rpsGain,
            row.version1Latency,
            row.version2Latency,
            row.latencyGain,
        ];

        values.forEach((value, index) => {
            const td = document.createElement("td");
            td.innerText = value;

            if (index === 5 || index === 8) {
                td.className = value >= 0 ? "positive" : "negative";
            }

            tr.appendChild(td);
        });

        table.appendChild(tr);
    });

    return table;
}

// Function to load, process, compare, and display CSV data
async function loadAndDisplayComparison(version1File, version2File, version1, version2, elementId) {
    const version1Data = await fetchCsvData(version1File);
    const version2Data = await fetchCsvData(version2File);

    const version1Averages = calculateAverages(version1Data);
    const version2Averages = calculateAverages(version2Data);

    const comparisonData = compareAverages(version1Averages, version2Averages);

    const comparisonTable = createComparisonTable(comparisonData, version1, version2);

    document.getElementById(elementId).appendChild(comparisonTable);
}

function generateFilePaths(version) {
    return {
        noCluster: `${version}_cluster_no_valkey_benchmark_results.csv`,
        tlsNoCluster: `${version}_cluster_no_tls_valkey_benchmark_results.csv`,
        yesCluster: `${version}_cluster_yes_valkey_benchmark_results.csv`,
        yesTlsCluster: `${version}_cluster_yes_tls_valkey_benchmark_results.csv`
    };
}

// Generate the file paths
const version1Files = generateFilePaths(version1);
const version2Files = generateFilePaths(version2);

// Call the function to load, process, compare, and display CSV data for each mode
loadAndDisplayComparison(version1Files.noCluster, version2Files.noCluster, version1, version2, "comparison-table-no");
loadAndDisplayComparison(version1Files.yesCluster, version2Files.yesCluster, version1, version2, "comparison-table-yes");
loadAndDisplayComparison(version1Files.tlsNoCluster, version2Files.tlsNoCluster, version1, version2, "comparison-table-no-tls");
loadAndDisplayComparison(version1Files.yesTlsCluster, version2Files.yesTlsCluster, version1, version2, "comparison-table-yes-tls");
