// Configuration
const brokerUrl = 'ws://157.173.101.159:9001';
const topic = 'sensor/temperature';

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const tempValue = document.getElementById('current-temp');
const lastUpdate = document.getElementById('last-update');
const candidateName = document.getElementById('candidate-name');
const tempCard = document.querySelector('.temp-card');

// Chart Setup
const ctx = document.getElementById('tempChart').getContext('2d');
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";

const gradientFill = ctx.createLinearGradient(0, 0, 0, 300);
gradientFill.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
gradientFill.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

const tempChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], // Timestamps
        datasets: [{
            label: 'Temperature (°C)',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: gradientFill,
            borderWidth: 2,
            pointBackgroundColor: '#0f172a',
            pointBorderColor: '#3b82f6',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: true,
            tension: 0.4 // Smooth curves
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(30, 41, 59, 0.9)',
                titleColor: '#f8fafc',
                bodyColor: '#f8fafc',
                borderColor: 'rgba(255,255,255,0.1)',
                borderWidth: 1,
                padding: 10,
                displayColors: false
            }
        },
        scales: {
            x: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                ticks: {
                    maxTicksLimit: 8
                }
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)',
                    drawBorder: false
                },
                suggestedMin: 15,
                suggestedMax: 35
            }
        },
        animation: {
            duration: 400,
            easing: 'easeOutQuart'
        }
    }
});

// MQTT Connection
console.log(`Attempting to connect to ${brokerUrl}...`);
const client = mqtt.connect(brokerUrl);

client.on('connect', () => {
    console.log('Connected to MQTT Broker via WebSockets!');
    
    // Update UI Status
    statusDot.classList.remove('disconnected');
    statusDot.classList.add('connected');
    statusText.textContent = 'Connected';
    
    // Subscribe to topic
    client.subscribe(topic, (err) => {
        if (!err) {
            console.log(`Successfully subscribed to topic: ${topic}`);
        } else {
            console.error('Subscription error:', err);
        }
    });
});

client.on('message', (receivedTopic, message) => {
    try {
        const payload = JSON.parse(message.toString());
        console.log('Received payload:', payload);
        
        // Extract data
        const temp = parseFloat(payload.temperature);
        const cand = payload.candidate || 'Unknown';
        
        // Format time (HH:MM:SS)
        const dateObj = new Date(payload.timestamp || Date.now());
        const timeStr = dateObj.toLocaleTimeString([], { hour12: false });
        
        // Update DOM
        tempValue.textContent = temp.toFixed(1);
        lastUpdate.textContent = timeStr;
        candidateName.textContent = cand;
        
        // Dynamic colors based on temperature
        tempCard.classList.remove('temp-hot', 'temp-cold');
        if (temp >= 28) {
            tempCard.classList.add('temp-hot'); // Red glow for hot
        } else if (temp <= 20) {
            tempCard.classList.add('temp-cold'); // Blue glow for cold
        }

        // Update Chart
        updateChart(timeStr, temp);

    } catch (e) {
        console.error('Failed to parse MQTT message:', e);
    }
});

client.on('error', (err) => {
    console.error('MQTT Connection Error:', err);
    statusDot.classList.remove('connected');
    statusDot.classList.add('disconnected');
    statusText.textContent = 'Connection Error';
});

client.on('close', () => {
    console.log('MQTT Connection Closed');
    statusDot.classList.remove('connected');
    statusDot.classList.add('disconnected');
    statusText.textContent = 'Disconnected';
});

// Helper function to update the chart dynamically
const MAX_DATA_POINTS = 20;

function updateChart(timeLabel, temperature) {
    const data = tempChart.data.datasets[0].data;
    const labels = tempChart.data.labels;

    labels.push(timeLabel);
    data.push(temperature);

    // Keep only the latest N points
    if (labels.length > MAX_DATA_POINTS) {
        labels.shift();
        data.shift();
    }

    // Auto-adjust Y axis dynamically if temps go out of bounds
    const minTemp = Math.min(...data);
    const maxTemp = Math.max(...data);
    tempChart.options.scales.y.suggestedMin = Math.floor(minTemp - 2);
    tempChart.options.scales.y.suggestedMax = Math.ceil(maxTemp + 2);

    tempChart.update();
}
