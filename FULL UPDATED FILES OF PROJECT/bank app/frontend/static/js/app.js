/**
 * CENT Face Banking System - Frontend JavaScript
 * This file contains all client-side functionality for the CENT banking application
 * including face recognition, user authentication, and banking operations.
 */

// Global variables for application state management
let videoStream = null;        // Stores the current video stream for face recognition
let currentUser = null;        // Stores the authenticated user information
let capturedImages = [];       // Array to store captured face images during recognition
let faceDetectionTimer = null; // Timer for face detection loop
let faceDetectionAttempts = 0; // Counter for face detection attempts

// DOM Elements - References to important UI components
const loginModal = document.getElementById('loginModal');           // Login modal with face recognition
const registerModal = document.getElementById('registerModal');     // User registration modal
const dashboardModal = document.getElementById('dashboardModal');   // Main banking dashboard
const transactionModal = document.getElementById('transactionModal'); // Transaction operations modal
const loadingSpinner = document.getElementById('loadingSpinner');   // Loading indicator
const notification = document.getElementById('notification');       // Notification display

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing app...');
    initializeApp();
    console.log('App initialized successfully');
});

/**
 * Initialize the application
 * Sets up all event listeners and prepares the application for user interaction
 */
function initializeApp() {
    // Ensure loading spinner is hidden on page load
    if (loadingSpinner) {
        loadingSpinner.classList.remove('show');
        console.log('Loading spinner hidden');
    }
    
    // Mobile menu toggle functionality
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Form submission handlers
    const registerForm = document.getElementById('registerForm');
    registerForm.addEventListener('submit', handleRegister);

    // Direct login functionality has been removed for security reasons

    // Banking operation handlers
    const transactionForm = document.getElementById('transactionForm');
    transactionForm.addEventListener('submit', handleTransaction);

    // Modal behavior - close when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            closeAllModals();
        }
    });
}

// Modal functions
function showLoginModal() {
    closeAllModals();
    loginModal.style.display = 'block';
    showStep(1);
    
    // Automatically start face recognition
    setTimeout(() => {
        startFaceRecognition();
    }, 500); // Short delay to ensure modal is fully displayed
}

function showRegisterModal() {
    closeAllModals();
    registerModal.style.display = 'block';
}

// Direct login modal function has been removed for security reasons

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
    stopVideoStream();
}

/**
 * Navigate between multi-step form sections
 * @param {number} stepNumber - The step number to display
 */
function showStep(stepNumber) {
    const steps = document.querySelectorAll('.step');
    steps.forEach(step => step.classList.remove('active')); // Hide all steps
    document.getElementById(`step${stepNumber}`).classList.add('active'); // Show requested step
}

/**
 * Face Recognition System
 * Initializes the camera and starts the face detection process
 */
async function startFaceRecognition() {
    try {
        showLoading('Starting camera...'); // Show loading indicator while camera initializes
        
        const video = document.getElementById('video'); // Video element for camera feed
        const canvas = document.getElementById('canvas'); // Canvas for capturing frames
        
        // Request access to user's camera with specific dimensions
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: 300, 
                height: 300,
                facingMode: 'user' // Use front-facing camera when available
            } 
        });
        
        // Connect camera stream to video element
        video.srcObject = videoStream;
        
        // Update UI status indicator
        const statusIndicator = document.querySelector('.status-indicator p');
        if (statusIndicator) {
            statusIndicator.textContent = 'Camera active, detecting face...';
        }
        
        hideLoading(); // Hide loading indicator once camera is ready
        
        // Start face detection once video is fully loaded
        video.onloadedmetadata = () => {
            startFaceDetectionLoop(); // Begin continuous face detection
        };
        
    } catch (error) {
        // Handle camera access errors
        hideLoading();
        showNotification('Camera access denied. Please allow camera access.', 'error');
        console.error('Camera error:', error);
    }
}

/**
 * Face detection loop with retry mechanism
 * Manages the continuous process of detecting and recognizing faces
 * with appropriate feedback and retry logic
 */
function startFaceDetectionLoop() {
    // Clear any existing timer to prevent multiple loops
    if (faceDetectionTimer) {
        clearTimeout(faceDetectionTimer);
    }
    
    // Reset attempts counter after too many attempts
    if (faceDetectionAttempts > 10) {
        faceDetectionAttempts = 0;
    }
    
    // Update UI with appropriate status message
    updateFaceDetectionStatus();
    
    // Process current video frame for face recognition
    captureAndRecognizeFace();
    
    // Track number of detection attempts for UI feedback
    faceDetectionAttempts++;
}

/**
 * Update the face detection status message
 * Provides progressive feedback to guide the user through the face recognition process
 * based on the number of detection attempts made
 */
function updateFaceDetectionStatus() {
    const statusIndicator = document.querySelector('.status-indicator p');
    if (statusIndicator) {
        // Different messages based on how many attempts have been made
        if (faceDetectionAttempts === 0) {
            statusIndicator.textContent = 'Camera active, detecting face...';
        } else if (faceDetectionAttempts < 3) {
            statusIndicator.textContent = 'Looking for your face...';
        } else if (faceDetectionAttempts < 6) {
            statusIndicator.textContent = 'Please center your face in the frame...';
        } else {
            statusIndicator.textContent = 'Trying to recognize your face...';
        }
    }
}

/**
 * Capture video frame and process for face recognition
 * Takes a snapshot from the video feed, prepares it for processing,
 * and sends it to the backend for face recognition
 */
function captureAndRecognizeFace() {
    const video = document.getElementById('video'); // Video element with camera feed
    const canvas = document.getElementById('canvas'); // Canvas for frame capture
    const ctx = canvas.getContext('2d'); // Canvas drawing context
    
    // Ensure video is fully loaded and playing before capturing
    if (video.readyState !== 4) {
        console.log('Video not ready yet, retrying in 500ms');
        faceDetectionTimer = setTimeout(startFaceDetectionLoop, 500);
        return;
    }
    
    // Match canvas dimensions to video dimensions for accurate capture
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    
    // Send to backend for recognition
    recognizeFace(imageData);
}

async function recognizeFace(imageData) {
    try {
        // Don't show loading spinner for continuous detection
        // Just update the status indicator
        const statusIndicator = document.querySelector('.status-indicator p');
        if (statusIndicator) {
            statusIndicator.textContent = 'Processing face data...';
        }
        
        const response = await fetch('/api/face-verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ image: imageData })
        });
        
        const result = await response.json();
        
        console.log('Face recognition result:', result);
        
        if (result.success) {
            // Stop the face detection loop
            if (faceDetectionTimer) {
                clearTimeout(faceDetectionTimer);
                faceDetectionTimer = null;
            }
            
            // Update status indicator
            if (statusIndicator) {
                statusIndicator.textContent = 'Face recognized successfully!';
            }
            
            currentUser = result.user;
            
            // Ensure user has proper ID format
            if (currentUser && currentUser.unique_id) {
                // Store ID in both formats for compatibility
                currentUser.id = parseInt(currentUser.unique_id, 10);
            } else if (currentUser && currentUser.id) {
                // Ensure ID is stored as a number
                currentUser.id = parseInt(currentUser.id, 10);
            }
            
            // Update step 2 with recognized user info
            const step2 = document.getElementById('step2');
            if (step2 && result.recognized_user) {
                const userInfo = result.recognized_user;
                
                step2.querySelector('p').innerHTML = `
                    <strong>Recognized as: ${userInfo.name}</strong><br>
                    Account: ${userInfo.account_number}<br><br>
                    Enter your account password to complete login
                `;
            }
            
            showNotification(result.message, 'success');
            showStep(2);
        } else {
            // Continue face detection loop with a delay
            faceDetectionTimer = setTimeout(startFaceDetectionLoop, 1000);
            
            // Only show error notification after several failed attempts
            if (faceDetectionAttempts > 5 && faceDetectionAttempts % 3 === 0) {
                showNotification('Face not recognized. Please ensure good lighting and position your face clearly.', 'warning');
            }
        }
        
    } catch (error) {
        console.error('Recognition error:', error);
        
        // Continue face detection loop with a delay
        faceDetectionTimer = setTimeout(startFaceDetectionLoop, 1500);
        
        // Only show error notification after several failed attempts
        if (faceDetectionAttempts > 5 && faceDetectionAttempts % 3 === 0) {
            showNotification('Face recognition service error. Retrying...', 'error');
        }
    }
}

async function verifyPassword() {
    const passwordInput = document.getElementById('password');
    const password = passwordInput.value.trim();
    
    if (!password) {
        showNotification('Please enter your password', 'error');
        return;
    }
    
    if (!currentUser || !currentUser.id) {
        showNotification('User information is missing. Please try again.', 'error');
        return;
    }
    
    try {
        showLoading('Verifying password...');
        
        // Ensure user_id is sent as an integer
        const userId = parseInt(currentUser.id, 10);
        console.log('Sending user_id as:', userId, 'Type:', typeof userId);
        
        const response = await fetch('/api/verify-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                user_id: userId,
                password: password
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        console.log('Password verification result:', result);
        
        if (result.success) {
            showNotification('Login successful!', 'success');
            closeAllModals();
            showDashboard();
        } else {
            showNotification(result.message || 'Invalid password. Please try again.', 'error');
            // Log detailed error information
            console.error('Password verification failed:', result.message);
        }
        
    } catch (error) {
        hideLoading();
        showNotification('Password verification failed. Please try again.', 'error');
        console.error('Password verification error:', error);
    }
}

// Direct login function has been removed for security reasons

// Registration functions
async function handleRegister(event) {
    event.preventDefault();
    
    const name = document.getElementById('regName').value;
    const password = document.getElementById('regPassword').value;
    const confirmPassword = document.getElementById('regConfirmPassword').value;
    
    if (!name || !password || !confirmPassword) {
        showNotification('Please fill in all fields', 'error');
        return;
    }
    
    if (password !== confirmPassword) {
        showNotification('Passwords do not match', 'error');
        return;
    }
    
    if (password.length < 8) {
        showNotification('Password must be at least 8 characters', 'error');
        return;
    }
    
    try {
        showLoading('Creating account...');
        
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ name, password })
        });
        
        const result = await response.json();
        hideLoading();
        
        console.log('Registration result:', result);
        
        if (result.success) {
            // Store user data properly
            currentUser = result.user;
            
            // Ensure user has unique_id property
            if (currentUser && currentUser.unique_id) {
                // Store ID in both formats for compatibility
                currentUser.id = parseInt(currentUser.unique_id, 10);
            } else if (currentUser && currentUser.id) {
                // Ensure ID is stored as a number
                currentUser.id = parseInt(currentUser.id, 10);
            }
            
            console.log('New user created with ID:', currentUser.id, 'Type:', typeof currentUser.id);
            
            showNotification('Account created successfully!', 'success');
            closeAllModals();
            showFaceCaptureModal();
        } else {
            showNotification(result.message || 'Registration failed', 'error');
        }
        
    } catch (error) {
        hideLoading();
        showNotification('Registration failed. Please try again.', 'error');
        console.error('Registration error:', error);
    }
}

function showFaceCaptureModal() {
    // Create face capture modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'faceCaptureModal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Face Registration</h2>
                <span class="close" onclick="closeModal('faceCaptureModal')">&times;</span>
            </div>
            <div class="modal-body">
                <div class="face-capture-container">
                    <h3>Capture Your Face</h3>
                    <p>We need to capture 5 clear images of your face for security. Follow these steps:</p>
                    <ul style="text-align: left; margin: 1rem 0; color: #666;">
                        <li>Position your face in the center of the camera view</li>
                        <li>Ensure good lighting on your face</li>
                        <li>Look directly at the camera</li>
                        <li>Images will be captured automatically every 2 seconds</li>
                        <li>Move your head slightly between captures for variety</li>
                    </ul>
                    <div class="camera-container">
                        <video id="captureVideo" autoplay muted></video>
                        <canvas id="captureCanvas" style="display: none;"></canvas>
                        <div class="camera-overlay">
                            <div class="face-outline"></div>
                            <div class="capture-instructions">
                                <p>Auto-capturing in <span id="countdown">3</span> seconds...</p>
                            </div>
                        </div>
                    </div>
                    <div class="capture-info">
                        <p>Images captured: <span id="captureCount">0</span>/5</p>
                        <div class="capture-progress">
                            <div class="progress-bar" id="progressBar"></div>
                        </div>
                        <p style="font-size: 0.9rem; color: #666;">Images will be captured automatically every 2 seconds</p>
                    </div>
                    <button class="btn btn-secondary" onclick="finishFaceCapture()" id="finishBtn" style="display: none; color: white; background-color: #4CAF50; padding: 10px 20px; border-radius: 5px; font-weight: bold;">
                        <i class="fas fa-check"></i>
                        Finish Registration
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'block';
    
    // Start automatic face capture after a short delay
    setTimeout(() => {
        startFaceCapture();
    }, 1000);
}

let captureInterval;
let countdownInterval;

async function startFaceCapture() {
    try {
        const video = document.getElementById('captureVideo');
        const canvas = document.getElementById('captureCanvas');
        
        // Get user media with better quality
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: 640, 
                height: 480,
                facingMode: 'user'
            } 
        });
        
        video.srcObject = videoStream;
        
        // Show countdown and start auto-capture
        startCountdown();
        
    } catch (error) {
        showNotification('Camera access denied. Please allow camera access.', 'error');
        console.error('Camera error:', error);
    }
}

function startCountdown() {
    let countdown = 3;
    const countdownElement = document.getElementById('countdown');
    
    countdownInterval = setInterval(() => {
        countdownElement.textContent = countdown;
        countdown--;
        
        if (countdown < 0) {
            clearInterval(countdownInterval);
            startAutoCapture();
        }
    }, 1000);
}

function startAutoCapture() {
    const countdownElement = document.getElementById('countdown');
    countdownElement.textContent = 'Capturing...';
    
    // Start automatic capture every 2 seconds
    captureInterval = setInterval(() => {
        if (capturedImages.length < 5) {
            try {
                captureFaceImage();
            } catch (error) {
                console.error('Auto capture error:', error);
                showNotification('Capture error, retrying...', 'error');
            }
        } else {
            clearInterval(captureInterval);
            finishAutoCapture();
        }
    }, 2000);
}

function finishAutoCapture() {
    const countdownElement = document.getElementById('countdown');
    countdownElement.textContent = 'Complete!';
    
    const finishBtn = document.getElementById('finishBtn');
    finishBtn.style.display = 'inline-block';
    finishBtn.disabled = false;
}

function handleSpacebarCapture(event) {
    if (event.code === 'Space' && capturedImages.length < 5) {
        event.preventDefault();
        captureFaceImage();
    }
}

function captureFaceImage() {
    try {
        const video = document.getElementById('captureVideo');
        const canvas = document.getElementById('captureCanvas');
        
        if (!video || !canvas) {
            console.error('Video or canvas element not found');
            return;
        }
        
        if (video.videoWidth === 0 || video.videoHeight === 0) {
            console.error('Video not ready');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert to base64
        const imageData = canvas.toDataURL('image/jpeg', 0.9); // Higher quality
        capturedImages.push(imageData);
        
        // Update counter
        const captureCountElement = document.getElementById('captureCount');
        if (captureCountElement) {
            captureCountElement.textContent = capturedImages.length;
        }
        
        // Update progress bar
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            const progress = (capturedImages.length / 5) * 100;
            progressBar.style.width = `${progress}%`;
        }
        
        // Show capture feedback
        showNotification(`Image ${capturedImages.length} captured!`, 'success');
        
        if (capturedImages.length >= 5) {
            showNotification('Face capture completed! Click Finish Registration.', 'success');
            const finishBtn = document.getElementById('finishBtn');
            if (finishBtn) {
                finishBtn.style.display = 'inline-flex';
            }
        }
    } catch (error) {
        console.error('Error capturing face image:', error);
        showNotification('Error capturing image, retrying...', 'error');
    }
}

async function finishFaceCapture() {
    try {
        showLoading('Training face recognition model...');
        
        // Ensure we have the correct user ID format
        const userId = currentUser.unique_id || currentUser.id;
        console.log('[DEBUG] Using user ID for face capture:', userId);
        
        const response = await fetch('/api/capture-face', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ 
                user_id: userId,
                images: capturedImages 
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showNotification('Registration completed successfully!', 'success');
            closeAllModals();
            // Reload the page to ensure proper session state
            window.location.reload();
        } else {
            showNotification('Face registration failed. Please try again.', 'error');
        }
        
    } catch (error) {
        hideLoading();
        showNotification('Face registration failed. Please try again.', 'error');
        console.error('Face capture error:', error);
    }
}

// Dashboard functions
async function showDashboard() {
    try {
        console.log('[DEBUG] Loading dashboard...');
        showLoading('Loading your account...');
        
        // Check if session is valid first
        const sessionResponse = await fetch('/api/user-profile', { credentials: 'include' });
        if (sessionResponse.status !== 200) {
            console.error('[ERROR] Session invalid or expired');
            hideLoading();
            showNotification('Your session has expired. Please login again.', 'error');
            return;
        }
        
        // Load user balance and profile
        const [balanceResponse, profileResponse] = await Promise.all([
            fetch('/api/balance', { credentials: 'include' }),
            fetch('/api/user-profile', { credentials: 'include' })
        ]);
        
        console.log('[DEBUG] Balance response status:', balanceResponse.status);
        console.log('[DEBUG] Profile response status:', profileResponse.status);
        
        const balanceResult = await balanceResponse.json();
        const profileResult = await profileResponse.json();
        
        console.log('[DEBUG] Balance result:', balanceResult);
        console.log('[DEBUG] Profile result:', profileResult);
        
        hideLoading();
        
        if (balanceResult.success) {
            const balanceEl = document.getElementById('accountBalance');
            if (balanceEl) {
                balanceEl.textContent = `$${balanceResult.balance.toFixed(2)}`;
            } else {
                console.warn('[WARN] accountBalance element not found');
            }
        } else {
            console.error('[ERROR] Balance API failed:', balanceResult.message);
            showNotification('Failed to load balance: ' + (balanceResult.message || 'Unknown error'), 'error');
        }
        
        if (profileResult.success) {
            const profile = profileResult.profile;
            const userNameEl = document.getElementById('userName');
            const accountNumberEl = document.getElementById('accountNumber');
            
            if (userNameEl) {
                userNameEl.textContent = profile.name;
            } else {
                console.warn('[WARN] userName element not found');
            }
            
            if (accountNumberEl) {
                accountNumberEl.textContent = profile.account_number;
            } else {
                console.warn('[WARN] accountNumber element not found');
            }
        } else {
            console.error('[ERROR] Profile API failed:', profileResult.message);
            showNotification('Failed to load profile: ' + (profileResult.message || 'Unknown error'), 'error');
        }
        
        console.log('[DEBUG] Showing dashboard modal');
        const dashboardModal = document.getElementById('dashboardModal');
        if (dashboardModal) {
            dashboardModal.style.display = 'block';
            console.log('[SUCCESS] Dashboard modal displayed');
        } else {
            console.error('[ERROR] Dashboard modal not found!');
            showNotification('Dashboard interface not found', 'error');
        }
        
    } catch (error) {
        console.error('[ERROR] Dashboard error:', error);
        showNotification('Failed to load dashboard: ' + error.message, 'error');
    }
}

// Transaction functions
function showTransactionModal(type) {
    const modal = transactionModal;
    const title = document.getElementById('transactionTitle');
    const content = document.getElementById('transactionContent');
    const submitBtn = document.getElementById('transactionSubmit');
    
    let titleText = '';
    let contentHTML = '';
    
    switch (type) {
        case 'deposit':
            titleText = 'Deposit Money';
            contentHTML = `
                <div class="transaction-input">
                    <label for="depositAmount">Amount to Deposit</label>
                    <input type="number" id="depositAmount" placeholder="Enter amount" min="0.01" step="0.01" required>
                </div>
            `;
            break;
        case 'withdraw':
            titleText = 'Withdraw Money';
            contentHTML = `
                <div class="transaction-input">
                    <label for="withdrawAmount">Amount to Withdraw</label>
                    <input type="number" id="withdrawAmount" placeholder="Enter amount" min="0.01" step="0.01" required>
                </div>
            `;
            break;
        case 'transfer':
            titleText = 'Transfer Money';
            contentHTML = `
                <div class="transaction-input">
                    <label for="transferAccount">Recipient Account Number</label>
                    <input type="number" id="transferAccount" placeholder="Enter account number" required>
                </div>
                <div class="transaction-input">
                    <label for="transferAmount">Amount to Transfer</label>
                    <input type="number" id="transferAmount" placeholder="Enter amount" min="0.01" step="0.01" required>
                </div>
            `;
            break;
        case 'balance':
            titleText = 'Account Balance';
            contentHTML = `
                <div class="balance-display">
                    <h3>Current Balance</h3>
                    <p class="balance-amount" id="currentBalance">Loading...</p>
                </div>
            `;
            break;
    }
    
    title.textContent = titleText;
    content.innerHTML = contentHTML;
    submitBtn.textContent = type === 'balance' ? 'Close' : 'Process';
    
    // Store transaction type
    submitBtn.setAttribute('data-type', type);
    
    modal.style.display = 'block';
    
    // Load balance for balance inquiry
    if (type === 'balance') {
        loadCurrentBalance();
    }
}

async function handleTransaction(event) {
    event.preventDefault();
    
    const submitBtn = document.getElementById('transactionSubmit');
    const type = submitBtn.getAttribute('data-type');
    
    if (type === 'balance') {
        closeModal('transactionModal');
        return;
    }
    
    let amount, toAccount;
    
    switch (type) {
        case 'deposit':
            amount = parseFloat(document.getElementById('depositAmount').value);
            break;
        case 'withdraw':
            amount = parseFloat(document.getElementById('withdrawAmount').value);
            break;
        case 'transfer':
            amount = parseFloat(document.getElementById('transferAmount').value);
            toAccount = parseInt(document.getElementById('transferAccount').value);
            break;
    }
    
    if (!amount || amount <= 0) {
        showNotification('Please enter a valid amount', 'error');
        return;
    }
    
    try {
        showLoading('Processing transaction...');
        
        let response;
        switch (type) {
            case 'deposit':
                response = await fetch('/api/deposit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount })
                });
                break;
            case 'withdraw':
                response = await fetch('/api/withdraw', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount })
                });
                break;
            case 'transfer':
                response = await fetch('/api/transfer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount, to_account: toAccount })
                });
                break;
        }
        
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('transactionModal');
            // Refresh dashboard
            showDashboard();
        } else {
            showNotification(result.message, 'error');
        }
        
    } catch (error) {
        hideLoading();
        showNotification('Transaction failed. Please try again.', 'error');
        console.error('Transaction error:', error);
    }
}

async function loadCurrentBalance() {
    try {
        const response = await fetch('/api/balance', { credentials: 'include' });
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('currentBalance').textContent = `$${result.balance.toFixed(2)}`;
        }
    } catch (error) {
        document.getElementById('currentBalance').textContent = 'Error loading balance';
    }
}

// Utility functions
function showLoading(message = 'Loading...') {
    if (loadingSpinner) {
        loadingSpinner.classList.add('show');
        const messageEl = loadingSpinner.querySelector('p');
        if (messageEl) {
            messageEl.textContent = message;
        }
    }
}

function hideLoading() {
    if (loadingSpinner) {
        loadingSpinner.classList.remove('show');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    const messageEl = document.getElementById('notificationMessage');
    
    messageEl.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function stopVideoStream() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
}

async function logout() {
    try {
        await fetch('/api/logout', { credentials: 'include' });
        currentUser = null;
        closeAllModals();
        showNotification('Logged out successfully', 'success');
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Profile functions
async function showProfileModal() {
    try {
        const response = await fetch('/api/user-profile', { credentials: 'include' });
        const result = await response.json();
        
        if (result.success) {
            const profile = result.profile;
            document.getElementById('profileName').textContent = profile.name;
            document.getElementById('profileAccountNumber').textContent = profile.account_number;
            document.getElementById('profileBank').textContent = profile.bank;
        }
        
        document.getElementById('profileModal').style.display = 'block';
    } catch (error) {
        showNotification('Failed to load profile', 'error');
        console.error('Profile error:', error);
    }
}

// Settings functions
function showSettingsModal() {
    // Load current profile data
    loadProfileData();
    document.getElementById('settingsModal').style.display = 'block';
}

async function loadProfileData() {
    try {
        const response = await fetch('/api/user-profile', { credentials: 'include' });
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('settingsName').value = result.profile.name;
        }
    } catch (error) {
        console.error('Error loading profile data:', error);
    }
}

function showSettingsTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + 'Tab').classList.add('active');
    event.target.classList.add('active');
}

// Profile form submission
document.addEventListener('DOMContentLoaded', function() {
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const name = document.getElementById('settingsName').value;
            
            try {
                showLoading('Updating profile...');
                
                const response = await fetch('/api/update-profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name })
                });
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {
                    showNotification('Profile updated successfully!', 'success');
                    currentUser.name = name;
                    document.getElementById('userName').textContent = name;
                } else {
                    showNotification(result.message, 'error');
                }
            } catch (error) {
                hideLoading();
                showNotification('Failed to update profile', 'error');
                console.error('Profile update error:', error);
            }
        });
    }
    
    // Password form submission
    const passwordForm = document.getElementById('passwordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            if (newPassword !== confirmPassword) {
                showNotification('New passwords do not match', 'error');
                return;
            }
            
            if (newPassword.length < 8) {
                showNotification('New password must be at least 8 characters', 'error');
                return;
            }
            
            try {
                showLoading('Changing password...');
                
                const response = await fetch('/api/change-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
                });
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {
                    showNotification('Password changed successfully!', 'success');
                    passwordForm.reset();
                } else {
                    showNotification(result.message, 'error');
                }
            } catch (error) {
                hideLoading();
                showNotification('Failed to change password', 'error');
                console.error('Password change error:', error);
            }
        });
    }
});

// Transaction History functions
async function showTransactionHistory() {
    try {
        showLoading('Loading transaction history...');
        
        const response = await fetch('/api/transaction-history', { credentials: 'include' });
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            displayTransactions(result.transactions);
            document.getElementById('historyModal').style.display = 'block';
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Failed to load transaction history', 'error');
        console.error('Transaction history error:', error);
    }
}

function displayTransactions(transactions) {
    const container = document.getElementById('transactionList');
    
    if (transactions.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 2rem;">No transactions found</p>';
        return;
    }
    
    container.innerHTML = transactions.map(transaction => `
        <div class="transaction-item">
            <div class="transaction-info">
                <div class="transaction-type">${transaction.type}</div>
                <div class="transaction-description">${transaction.description}</div>
                <div class="transaction-date">${transaction.date}</div>
            </div>
            <div class="transaction-amount ${transaction.type === 'deposit' ? 'positive' : 'negative'}">
                ${transaction.type === 'deposit' ? '+' : '-'}$${transaction.amount.toFixed(2)}
            </div>
        </div>
    `).join('');
}

// Admin Panel functions
async function showAdminPanel() {
    try {
        showLoading('Loading admin data...');
        
        const response = await fetch('/api/admin/users', { credentials: 'include' });
        const result = await response.json();
        hideLoading();
        
        if (result.success) {
            displayAdminData(result.users);
            document.getElementById('adminModal').style.display = 'block';
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Failed to load admin data', 'error');
        console.error('Admin panel error:', error);
    }
}

function displayAdminData(users) {
    // Update stats
    document.getElementById('totalUsers').textContent = users.length;
    document.getElementById('activeAccounts').textContent = users.filter(u => u.account_balance > 0).length;
    
    const totalDeposits = users.reduce((sum, user) => sum + parseFloat(user.account_balance || 0), 0);
    document.getElementById('totalDeposits').textContent = `$${totalDeposits.toFixed(2)}`;
    
    // Update users table
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.unique_id}</td>
            <td>${user.name}</td>
            <td>${user.account_number}</td>
            <td>$${parseFloat(user.account_balance || 0).toFixed(2)}</td>
            <td>${user.bank}</td>
        </tr>
    `).join('');
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    stopVideoStream();
});
