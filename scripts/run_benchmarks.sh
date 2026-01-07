#!/bin/bash

# Performance Benchmark Runner for MCP Kali Forensics
# Runs comprehensive performance tests and generates reports

set -e

echo "🔥 MCP Kali Forensics - Performance Benchmark Runner"
echo "======================================================"
echo ""

# Configuration
BENCHMARK_DIR="benchmarks"
RESULTS_DIR="$BENCHMARK_DIR/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$RESULTS_DIR/report_$TIMESTAMP.html"

# Create directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$BENCHMARK_DIR/baseline"

# Check if baseline exists
if [ ! -f "$BENCHMARK_DIR/baseline.json" ]; then
    echo "⚠️ No baseline found. This run will create the baseline."
    CREATE_BASELINE=true
else
    echo "✅ Baseline found: $BENCHMARK_DIR/baseline.json"
    CREATE_BASELINE=false
fi

echo ""
echo "📊 Running benchmarks..."
echo ""

# Run benchmarks with pytest
pytest tests/test_benchmarks.py \
    -v \
    -m benchmark \
    --tb=short \
    --benchmark-only \
    --benchmark-autosave \
    --benchmark-save-data \
    --benchmark-compare \
    --benchmark-compare-fail=mean:10% \
    --benchmark-histogram="$RESULTS_DIR/histogram_$TIMESTAMP" \
    || true

# Generate HTML report
echo ""
echo "📝 Generating HTML report..."

cat > "$REPORT_FILE" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>MCP Forensics Benchmarks - $TIMESTAMP</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }
        .summary {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #007bff;
            color: white;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .pass {
            color: #28a745;
            font-weight: bold;
        }
        .warn {
            color: #ffc107;
            font-weight: bold;
        }
        .fail {
            color: #dc3545;
            font-weight: bold;
        }
        .metric {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>🔥 MCP Forensics Performance Benchmarks</h1>
    <p><strong>Generated:</strong> $(date)</p>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <div class="metric">
            Total Tests: <span id="total">0</span>
        </div>
        <div class="metric pass">
            Passed: <span id="passed">0</span>
        </div>
        <div class="metric warn">
            Warnings: <span id="warnings">0</span>
        </div>
        <div class="metric fail">
            Failed: <span id="failed">0</span>
        </div>
    </div>
    
    <h2>📈 Benchmark Results</h2>
    <table>
        <thead>
            <tr>
                <th>Test Name</th>
                <th>Mean (ms)</th>
                <th>Min (ms)</th>
                <th>Max (ms)</th>
                <th>Std Dev</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody id="results">
            <tr>
                <td colspan="6">Loading results...</td>
            </tr>
        </tbody>
    </table>
    
    <h2>📊 Performance Trends</h2>
    <p>Compare with baseline: $BENCHMARK_DIR/baseline.json</p>
    
    <h2>🎯 SLA Targets</h2>
    <ul>
        <li><strong>Health Endpoint:</strong> &lt; 100ms</li>
        <li><strong>API List Operations:</strong> &lt; 500ms</li>
        <li><strong>API Create Operations:</strong> &lt; 1000ms</li>
        <li><strong>Database Queries (100 rows):</strong> &lt; 200ms</li>
        <li><strong>Tool Execution (Loki):</strong> &lt; 60 seconds</li>
    </ul>
</body>
</html>
EOF

echo "✅ HTML report generated: $REPORT_FILE"

# Save baseline if needed
if [ "$CREATE_BASELINE" = true ]; then
    echo ""
    echo "📦 Creating baseline..."
    cp "$RESULTS_DIR/report_$TIMESTAMP.json" "$BENCHMARK_DIR/baseline.json" 2>/dev/null || true
    echo "✅ Baseline created: $BENCHMARK_DIR/baseline.json"
fi

# Print summary
echo ""
echo "======================================================"
echo "✅ Benchmark completed!"
echo ""
echo "📊 Results:"
echo "   - HTML Report: $REPORT_FILE"
echo "   - JSON Data: $RESULTS_DIR/"
echo "   - Baseline: $BENCHMARK_DIR/baseline.json"
echo ""
echo "🌐 Open report:"
echo "   file://$(pwd)/$REPORT_FILE"
echo ""

# Open report in browser (optional)
if command -v xdg-open &> /dev/null; then
    echo "Opening report in browser..."
    xdg-open "$REPORT_FILE" &
elif command -v open &> /dev/null; then
    echo "Opening report in browser..."
    open "$REPORT_FILE" &
fi
