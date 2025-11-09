(function(){
    let bars = document.querySelectorAll('.eq-bar');
    let currentVibe = "Energetic and Upbeat"; // Default vibe
    let animationInterval;
    
    // Vibe configurations
    const vibeConfigs = {
    "Energetic and Upbeat": {
        minHeight: 50,
        maxHeight: 95,
        speed: 300,
        variance: 0.9
    },
    "Calm and Mellow": {
        minHeight: 20,
        maxHeight: 45,
        speed: 800,
        variance: 0.3
    },
    "Rising Energy": {
        minHeight: 30,
        maxHeight: 85,
        speed: 400,
        variance: 0.7,
        trend: 'rising'
    },
    "Slowing Down": {
        minHeight: 25,
        maxHeight: 60,
        speed: 600,
        variance: 0.5,
        trend: 'falling'
    }
    };
    
    function animateBars() {
    // Re-query bars in case DOM was updated
    bars = document.querySelectorAll('.eq-bar');
    const config = vibeConfigs[currentVibe] || vibeConfigs["Energetic and Upbeat"];
    const range = config.maxHeight - config.minHeight;
    
    bars.forEach((bar, index) => {
        let targetHeight;
        
        if (config.trend === 'rising') {
        // Bars gradually increase from left to right
        const progression = index / (bars.length - 1);
        const biasedRandom = Math.random() * (0.3 + progression * 0.7);
        targetHeight = config.minHeight + biasedRandom * range;
        } else if (config.trend === 'falling') {
        // Bars gradually decrease from left to right
        const progression = 1 - (index / (bars.length - 1));
        const biasedRandom = Math.random() * (0.3 + progression * 0.7);
        targetHeight = config.minHeight + biasedRandom * range;
        } else {
        // Random heights with variance
        const baseRandom = Math.random();
        const variance = (Math.random() - 0.5) * 2 * config.variance;
        const adjustedRandom = Math.max(0, Math.min(1, baseRandom + variance * 0.3));
        targetHeight = config.minHeight + adjustedRandom * range;
        }
        
        bar.style.height = targetHeight + '%';
    });
    }
    
    // Function to update vibe (can be called from outside)
    window.setVibe = function(vibeString) {
    if (vibeConfigs[vibeString]) {
        currentVibe = vibeString;
        
        // Update vibe label in UI
        const vibeLabel = document.querySelector('.vibe-right h3');
        if (vibeLabel) {
        vibeLabel.textContent = vibeString;
        }
        
        // Clear existing interval and restart with new speed
        if (animationInterval) {
        clearInterval(animationInterval);
        }
        
        const config = vibeConfigs[currentVibe];
        animateBars();
        animationInterval = setInterval(animateBars, config.speed);
        
        console.log('Vibe updated to:', vibeString);
    } else {
        console.warn('Unknown vibe:', vibeString, '- Available vibes:', Object.keys(vibeConfigs));
    }
    };
    
    // Initial animation
    const config = vibeConfigs[currentVibe];
    animateBars();
    animationInterval = setInterval(animateBars, config.speed);
    
    // Example: To change vibe, call: window.setVibe("Calm and Mellow");
    // You can also test different vibes in console:
    console.log('Available vibes:', Object.keys(vibeConfigs));
    console.log('Current vibe:', currentVibe);
    console.log('To change vibe, use: window.setVibe("Calm and Mellow")');

    // Expose function to check vibe
    window.checkVibe = function() {
        startVibeCheck();
    };

    // Auto-check vibe every 30 seconds
    setInterval(function() {
        startVibeCheck();
    }, 30000);

    function startVibeCheck() {
        // Get references to vibe elements
        const vibeCard = document.querySelector('.vibe .card');
        const vibeLeft = vibeCard.querySelector('.vibe-left');
        const vibeRight = vibeCard.querySelector('.vibe-right');
        
        // Store original content
        const originalLeftContent = vibeLeft.innerHTML;
        const originalRightContent = vibeRight.innerHTML;
        
        // Clear existing animation
        if (animationInterval) {
            clearInterval(animationInterval);
        }
        
        // Replace with "Checking the Vibe" animation
        vibeLeft.innerHTML = `
            <div class="checking-vibe-spinner">
                <div class="spinner-ring"></div>
                <div class="spinner-ring"></div>
                <div class="spinner-ring"></div>
            </div>
        `;
        
        vibeRight.innerHTML = `
            <h3 class="checking-vibe-text">Checking the Vibe...</h3>
            <p>Analyzing the crowd's energy and preferences to recommend the perfect next tracks.</p>
            <div class="checking-progress-bar">
                <div class="checking-progress-fill"></div>
            </div>
        `;
        
        // Start indeterminate progress animation
        const progressFill = vibeCard.querySelector('.checking-progress-fill');
        progressFill.style.transition = 'none';
        progressFill.style.width = '0%';
        progressFill.offsetHeight; // Force reflow
        
        // Use pulsing animation instead of fixed duration
        progressFill.style.animation = 'progressPulse 2s ease-in-out infinite';
        
        // Call API and update when it returns
        fetchNextVibeAndSongs().then(result => {
            console.log('Fetched vibe and songs:', result);
            console.log('Songs count:', result.songs ? result.songs.length : 0);
            
            // Restore original content with new vibe
            vibeLeft.innerHTML = originalLeftContent;
            vibeRight.innerHTML = originalRightContent;
            
            // Re-query bars after DOM update
            bars = document.querySelectorAll('.eq-bar');
            
            // Update vibe
            window.setVibe(result.vibe);
            
            // Update queue with new songs
            if (result.songs && result.songs.length > 0) {
                currentQueue = result.songs;
                console.log('Updated currentQueue:', currentQueue);
                updateQueueDisplay();
                showNotification(`✅ Queue updated: ${result.songs.length} songs | Vibe: ${result.vibe}`);
            } else {
                console.warn('No songs in result, keeping current queue');
                showNotification(`⚠️ Vibe updated to: ${result.vibe} (queue unchanged)`);
            }
            
            console.log('Vibe check complete:', result);
        }).catch(error => {
            console.error('Error in vibe check:', error);
            
            // Restore original content even on error
            vibeLeft.innerHTML = originalLeftContent;
            vibeRight.innerHTML = originalRightContent;
            
            // Re-query bars after DOM update
            bars = document.querySelectorAll('.eq-bar');
            
            // Restart animation with current vibe
            const config = vibeConfigs[currentVibe];
            animateBars();
            animationInterval = setInterval(animateBars, config.speed);
            
            showNotification('❌ Vibe check failed, trying again soon...');
        });
    }
})();

// Function to fetch next vibe and songs from Flask APIs
async function fetchNextVibeAndSongs() {
    try {
        // First, get the current party state
        const stateResponse = await fetch('http://127.0.0.1:5000/party-state');
        
        if (!stateResponse.ok) {
            throw new Error(`Party state API returned ${stateResponse.status}`);
        }
        
        const stateData = await stateResponse.json();
        console.log('Party state:', stateData);
        
        // Determine vibe from current trend and score
        let vibe = "Energetic and Upbeat"; // Default
        const currentScore = stateData.current_score || 0;
        const trend = stateData.current_trend || 'stable';
        
        if (trend === 'rising') {
            vibe = "Rising Energy";
        } else if (trend === 'falling') {
            vibe = "Slowing Down";
        } else if (currentScore > 0.5) {
            vibe = "Energetic and Upbeat";
        } else if (currentScore < 0) {
            vibe = "Calm and Mellow";
        }
        
        // Get songs from playlist
        let songs = [];
        if (stateData.playlist && stateData.playlist.length > 0) {
            songs = stateData.playlist.map(song => ({
                title: song.title,
                artist: song.artist
            }));
            console.log(`Found ${songs.length} songs in current playlist`);
        } else {
            console.log('Playlist is empty');
        }
        
        // Try to call Gemini if enough time has passed (won't fail if too soon)
        let geminiCalled = false;
        try {
            const geminiResponse = await fetch('http://127.0.0.1:5000/gemini-recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (geminiResponse.ok) {
                const geminiData = await geminiResponse.json();
                console.log('✅ Gemini recommendations received:', geminiData);
                geminiCalled = true;
                
                // Update vibe based on Gemini recommendation if available
                if (geminiData.recommendation && geminiData.recommendation.action) {
                    const action = geminiData.recommendation.action.recommendation;
                    if (action === "increase_energy") {
                        vibe = "Rising Energy";
                    } else if (action === "wind_down") {
                        vibe = "Slowing Down";
                    } else if (action === "maintain_energy") {
                        vibe = currentScore > 0.5 ? "Energetic and Upbeat" : "Calm and Mellow";
                    }
                    console.log(`Vibe updated from Gemini: ${vibe}`);
                }
                
                // Get fresh playlist after Gemini added songs
                const newStateResponse = await fetch('http://127.0.0.1:5000/party-state');
                if (newStateResponse.ok) {
                    const newStateData = await newStateResponse.json();
                    if (newStateData.playlist && newStateData.playlist.length > 0) {
                        songs = newStateData.playlist.map(song => ({
                            title: song.title,
                            artist: song.artist
                        }));
                        console.log(`✅ Updated playlist: ${songs.length} songs total`);
                    }
                }
                
                showNotification(`🤖 Gemini added ${geminiData.songs_added || 0} new songs!`);
            } else if (geminiResponse.status === 429) {
                // Too soon to call Gemini - that's fine
                console.log('⏰ Gemini cooldown active, using current playlist');
            } else {
                console.log(`Gemini response status: ${geminiResponse.status}`);
            }
        } catch (geminiError) {
            console.log('Gemini call skipped:', geminiError.message);
        }
        
        // Fallback to seed songs if playlist is empty
        if (songs.length === 0) {
            songs = [
                { title: "O Saathi", artist: "Atif Aslam" },
                { title: "Samjhawan", artist: "Jawad Ahmad" },
                { title: "Duniyaa", artist: "Akhil" },
                { title: "Haule Haule", artist: "Salim–Sulaiman" },
                { title: "Bolna", artist: "Tanishk Bagchi" }
            ];
        }
        
        return {
            vibe: vibe,
            songs: songs.slice(0, 10) // Show top 10 songs
        };
        
    } catch (error) {
        console.error('Error fetching vibe and songs:', error);
        
        // Fallback to demo data on error
        const vibes = ["Energetic and Upbeat", "Calm and Mellow", "Rising Energy", "Slowing Down"];
        const randomVibe = vibes[Math.floor(Math.random() * vibes.length)];
        
        const dummySongs = [
            { title: "O Saathi", artist: "Atif Aslam" },
            { title: "Samjhawan", artist: "Jawad Ahmad" },
            { title: "Duniyaa", artist: "Akhil" },
            { title: "Haule Haule", artist: "Salim–Sulaiman" },
            { title: "Bolna", artist: "Tanishk Bagchi" }
        ];
        
        showNotification('⚠️ Using offline mode with seed songs');
        
        return {
            vibe: randomVibe,
            songs: dummySongs
        };
    }
}

// Add Song functionality
// Mock song database (replace with actual API call)
const songDatabase = [  
    { id: 1, title: "Neon Lights", artist: "Cyber Dreams" },
    { id: 2, title: "Digital Horizon", artist: "Pixel Wave" },
    { id: 3, title: "Retro Nights", artist: "80s Revival" },
    { id: 4, title: "Crystal Rain", artist: "Ambient Flow" },
    { id: 5, title: "Tokyo Drift", artist: "Street Racers" },
    { id: 6, title: "Cosmic Journey", artist: "Space Odyssey" },
    { id: 7, title: "Summer Vibes", artist: "Beach Boys Collective" },
    { id: 8, title: "Northern Lights", artist: "Aurora Borealis Band" },
    { id: 9, title: "Desert Wind", artist: "Nomadic Souls" },
    { id: 10, title: "Mountain Echo", artist: "Alpine Sounds" },
    { id: 11, title: "River Flow", artist: "Nature's Symphony" },
    { id: 12, title: "City Pulse", artist: "Urban Legends" },
    { id: 13, title: "Moonlight Serenade", artist: "Jazz Collective" },
    { id: 14, title: "Thunder Storm", artist: "Electric Ensemble" },
    { id: 15, title: "Peaceful Mind", artist: "Meditation Masters" }
];

let currentQueue = [
    { title: "Electric Dreams", artist: "Synthwave Collective" },
    { title: "Midnight Runner", artist: "Neon Pulse" },
    { title: "Ocean Breeze", artist: "Coastal Vibes" },
    { title: "Starlight Symphony", artist: "Aurora Sound" },
    { title: "Urban Nights", artist: "City Beats" }
];

function searchSongs() {
    const searchTerm = document.getElementById('songSearch').value.toLowerCase();
    const resultsContainer = document.getElementById('searchResults');
    
    if (!searchTerm.trim()) {
    resultsContainer.classList.remove('active');
    return;
    }

    const results = songDatabase.filter(song => 
    song.title.toLowerCase().includes(searchTerm) || 
    song.artist.toLowerCase().includes(searchTerm)
    );

    if (results.length === 0) {
    resultsContainer.innerHTML = '<div style="padding:16px; color:var(--muted); text-align:center;">No songs found</div>';
    resultsContainer.classList.add('active');
    return;
    }

    resultsContainer.innerHTML = results.map(song => `
    <div class="search-result-item" data-song-id="${song.id}">
        <div class="search-result-meta">
        <div class="title">${song.title}</div>
        <div class="artist">${song.artist}</div>
        </div>
        <button class="add-btn" onclick="addToQueue(${song.id})">+</button>
    </div>
    `).join('');
    
    resultsContainer.classList.add('active');
}

function addToQueue(songId) {
    const song = songDatabase.find(s => s.id === songId);
    if (!song) return;

    // Add to queue array
    currentQueue.push({ title: song.title, artist: song.artist });

    // Update the UI
    updateQueueDisplay();

    // Clear search
    document.getElementById('songSearch').value = '';
    document.getElementById('searchResults').classList.remove('active');

    // Show feedback
    showNotification(`Added "${song.title}" to queue!`);
}

function updateQueueDisplay() {
    const queueList = document.getElementById('queueList');
    
    if (!currentQueue || currentQueue.length === 0) {
        console.warn('⚠️ currentQueue is empty, cannot update display');
        queueList.innerHTML = `
        <div style="padding:20px; text-align:center; color:var(--muted);">
            <p>🎵 Queue is empty</p>
            <p style="font-size:14px; margin-top:8px;">Waiting for recommendations...</p>
        </div>
        `;
        return;
    }
    
    console.log(`📝 Updating queue display with ${currentQueue.length} songs`);
    
    queueList.innerHTML = currentQueue.map((song, index) => `
    <div class="queue-item" role="listitem">
        <div class="idx">${index + 1}.</div>
        <div class="song">
        <div class="meta">
            <div class="title">${song.title || 'Unknown'}</div>
            <div class="artist">${song.artist || 'Unknown Artist'}</div>
        </div>
        </div>
    </div>
    `).join('');
    
    console.log('✅ Queue display updated successfully');
}

function showNotification(message) {
    // Simple notification (you can enhance this with a better UI)
    const notification = document.createElement('div');
    notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: linear-gradient(135deg, rgba(97,175,239,0.95), rgba(198,120,221,0.95));
    color: #ffffff;
    padding: 16px 24px;
    border-radius: 8px;
    font-weight: 700;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    z-index: 1000;
    animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => notification.remove(), 300);
    }, 2000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
    from { transform: translateX(400px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
    from { transform: translateX(0); opacity: 1; }
    to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Allow search on Enter key
document.getElementById('songSearch').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
    searchSongs();
    }
});

// End Party functionality
function endParty() {
    // Show confirmation dialog
    const confirmEnd = confirm('Are you sure you want to end the party? This will close the session for all participants.');
    
    if (confirmEnd) {
        // Show ending notification
        showNotification('Ending party session...');
        
        // Call reset endpoint
        fetch('http://127.0.0.1:5000/reset-party', {
            method: 'POST'
        }).then(() => {
            // Redirect to home page
            window.location.href = '/';
        }).catch(err => {
            console.error('Error ending party:', err);
            window.location.href = '/';
        });
    }
}

// Initialize party on page load
async function initializeParty() {
    console.log('Initializing party...');
    
    // Add seed songs to playlist if empty
    try {
        const stateResponse = await fetch('http://127.0.0.1:5000/party-state');
        const stateData = await stateResponse.json();
        
        // If playlist is empty, add seed songs
        if (!stateData.playlist || stateData.playlist.length === 0) {
            console.log('Playlist empty, adding seed songs...');
            
            const seedSongs = [
                { title: "O Saathi", artist: "Atif Aslam", genre: "bollywood", source: "seed" },
                { title: "Samjhawan", artist: "Jawad Ahmad", genre: "bollywood", source: "seed" },
                { title: "Duniyaa", artist: "Akhil", genre: "punjabi pop", source: "seed" },
                { title: "Haule Haule", artist: "Salim–Sulaiman", genre: "bollywood", source: "seed" },
                { title: "Bolna", artist: "Tanishk Bagchi", genre: "bollywood", source: "seed" }
            ];
            
            await fetch('http://127.0.0.1:5000/add-to-playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ songs: seedSongs })
            });
            
            console.log('Seed songs added to playlist');
        }
        
        // Trigger first vibe check immediately
        setTimeout(() => {
            startVibeCheck();
        }, 1000);
        
    } catch (error) {
        console.error('Error initializing party:', error);
        // Still show the UI with fallback data
        updateQueueDisplay();
    }
}

// Call initialization when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeParty();
});