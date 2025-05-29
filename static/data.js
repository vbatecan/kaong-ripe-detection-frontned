document.addEventListener('DOMContentLoaded', () => {
    // Initialize the data display
    loadData();
    
    // Add filter button click handlers
    document.querySelectorAll('.filter-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            // Remove active class from all buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            e.target.classList.add('active');
            
            // Apply the filter
            const filter = e.target.dataset.filter;
            filterData(filter);
        });
    });
});

async function loadData() {
    try {
        const response = await fetch('/get_assessment_data');
        const data = await response.json();
        
        if (response.ok) {
            displayData(data);
            updateStatistics(data);
        } else {
            console.error('Failed to load data:', data.error);
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

function displayData(data) {
    const grid = document.querySelector('.data-grid');
    const template = document.getElementById('data-item-template');
    
    // Clear existing items
    grid.innerHTML = '';
    
    data.forEach(item => {
        const clone = template.content.cloneNode(true);
        
        // Set image
        const img = clone.querySelector('img');
        img.src = item.image_url;
        
        // Set assessment label
        const label = clone.querySelector('.assessment-label');
        label.textContent = item.assessment;
        label.dataset.status = getStatusClass(item.assessment);
        
        // Set details
        const details = clone.querySelectorAll('.item-details p');
        details[0].textContent = new Date(item.timestamp).toLocaleString();
        details[1].textContent = `Confidence: ${(item.confidence * 100).toFixed(1)}%`;
        details[2].textContent = `Source: ${item.source}`;
        
        // Add data attributes for filtering
        const dataItem = clone.querySelector('.data-item');
        dataItem.dataset.status = getStatusClass(item.assessment);
        
        grid.appendChild(clone);
    });
}

function updateStatistics(data) {
    // Update total count
    document.getElementById('totalScanned').textContent = data.length;
    
    // Group images by scan session (images taken within 5 seconds of each other)
    const scanSessions = groupByScanSession(data);
    const totalScanSessions = Object.keys(scanSessions).length;
    
    // Count by status
    const counts = data.reduce((acc, item) => {
        const status = getStatusClass(item.assessment);
        acc[status] = (acc[status] || 0) + 1;
        return acc;
    }, {});
    
    // Update individual counts
    document.getElementById('readyCount').textContent = counts.ready || 0;
    document.getElementById('notReadyCount').textContent = counts['not-ready'] || 0;
    document.getElementById('rottenCount').textContent = counts.rotten || 0;
    
    // Add scan session statistics
    const scanSessionStats = document.createElement('div');
    scanSessionStats.className = 'stat-box';
    scanSessionStats.innerHTML = `
        <h3>Total Scan Sessions</h3>
        <p>${totalScanSessions}</p>
    `;
    
    // Add average kaong per session
    const avgKaongPerSession = data.length / totalScanSessions;
    const avgKaongStats = document.createElement('div');
    avgKaongStats.className = 'stat-box';
    avgKaongStats.innerHTML = `
        <h3>Average Kaong per Session</h3>
        <p>${avgKaongPerSession.toFixed(1)}</p>
    `;
    
    // Add to statistics container
    const statsContainer = document.querySelector('.statistics');
    statsContainer.appendChild(scanSessionStats);
    statsContainer.appendChild(avgKaongStats);
}

function groupByScanSession(data) {
    const sessions = {};
    const TIME_THRESHOLD = 5000; // 5 seconds in milliseconds
    
    // Sort data by timestamp
    const sortedData = [...data].sort((a, b) => 
        new Date(a.timestamp) - new Date(b.timestamp)
    );
    
    let currentSession = null;
    let sessionStartTime = null;
    
    sortedData.forEach(item => {
        const timestamp = new Date(item.timestamp).getTime();
        
        if (!currentSession || timestamp - sessionStartTime > TIME_THRESHOLD) {
            // Start new session
            currentSession = timestamp.toString();
            sessionStartTime = timestamp;
            sessions[currentSession] = [];
        }
        
        sessions[currentSession].push(item);
    });
    
    return sessions;
}

function filterData(filter) {
    const items = document.querySelectorAll('.data-item');
    
    items.forEach(item => {
        if (filter === 'all' || item.dataset.status === filter) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function getStatusClass(assessment) {
    switch (assessment.toLowerCase()) {
        case 'ready for harvesting':
            return 'ready';
        case 'not ready for harvesting':
            return 'not-ready';
        case 'rotten':
            return 'rotten';
        default:
            return 'unknown';
    }
} 