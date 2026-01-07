// API Flow Page Logic
class ApiFlowPage {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
    }


    bindEvents() {
        // Wait a bit for DOM to be ready, then bind events
        setTimeout(() => {
            this.bindEventsNow();
        }, 500);
    }

    bindEventsNow() {
        // Use event delegation for dynamic content
        const container = document.getElementById('apiflow-content');
        if (container) {
            // Remove existing listener to avoid duplicates
            const newContainer = container.cloneNode(true);
            container.parentNode.replaceChild(newContainer, container);

            // Now bind to the new container
            newContainer.addEventListener('click', (e) => {
                // Handle endpoint head clicks
                if (e.target.closest('.endpoint-head')) {
                    e.preventDefault();
                    e.stopPropagation();

                    const endpointItem = e.target.closest('.endpoint-item');
                    if (endpointItem) {
                        this.toggleEndpoint(endpointItem);
                    }
                    return;
                }

                // Handle send request button clicks
                if (e.target.closest('.btn-send-request')) {
                    const button = e.target.closest('.btn-send-request');
                    const endpointItem = button.closest('.endpoint-item');
                    const endpointPath = endpointItem.querySelector('.endpoint-path').textContent;
                    this.sendLiveRequest(endpointItem, endpointPath);
                    return;
                }

                // Handle copy button clicks
                if (e.target.closest('.btn-copy')) {
                    const button = e.target.closest('.btn-copy');
                    const codeSnippet = button.closest('.code-snippet-box').querySelector('pre').textContent;
                    this.copyToClipboard(codeSnippet, button);
                    return;
                }
            });
        }

        // Also try direct binding as fallback
        this.bindDirectEvents();
    }

    bindDirectEvents() {
        // Bind endpoint toggle events (expand/collapse) - direct binding
        const endpointHeads = document.querySelectorAll('.endpoint-head');

        endpointHeads.forEach((head) => {
            head.style.cursor = 'pointer'; // Visual feedback
            head.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const endpointItem = head.closest('.endpoint-item');
                if (endpointItem) {
                    this.toggleEndpoint(endpointItem);
                }
            });
        });

        // Bind "Send Request" button events
        const sendRequestButtons = document.querySelectorAll('.btn-send-request');
        sendRequestButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const endpointItem = e.target.closest('.endpoint-item');
                const endpointPath = endpointItem.querySelector('.endpoint-path').textContent;
                this.sendLiveRequest(endpointItem, endpointPath);
            });
        });

        // Bind "Copy" button events
        const copyButtons = document.querySelectorAll('.btn-copy');
        copyButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const codeSnippet = e.target.closest('.code-snippet-box').querySelector('pre').textContent;
                this.copyToClipboard(codeSnippet, button);
            });
        });
    }

    toggleEndpoint(endpointItem) {
        const endpointBody = endpointItem.querySelector('.endpoint-body');
        const arrow = endpointItem.querySelector('.endpoint-arrow');

        if (endpointBody.classList.contains('hidden')) {
            endpointBody.classList.remove('hidden');
            arrow.textContent = '▲';
            endpointBody.style.display = 'block'; // Force show
        } else {
            endpointBody.classList.add('hidden');
            arrow.textContent = '▼';
            endpointBody.style.display = 'none'; // Force hide
        }
    }

    async tryEndpoint(endpoint) {
        const button = event.target;
        const originalText = button.textContent;

        // Update button state
        button.textContent = '⏳ Testing...';
        button.disabled = true;

        try {
            let result;

            // Use appropriate API service method based on endpoint
            switch (endpoint) {
                case '/get-token':
                    result = await window.apiService.getTokenInfo();
                    break;
                case '/balance':
                    result = await window.apiService.getBalance();
                    break;
                case '/token-aval':
                    result = await window.apiService.getTokenAvailability();
                    break;
                case '/solve':
                    result = await window.apiService.solveCaptcha({ test: true, type: 'recaptcha' });
                    break;
                default:
                    // Generic request for other endpoints
                    result = await window.apiService.get(endpoint);
            }

            this.showResult(button, result.success, result.data);

        } catch (error) {
            this.showResult(button, false, {
                error: error.message,
                details: error.data
            });
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    showResult(button, success, data) {
        // Remove previous result
        const existingResult = button.parentElement.querySelector('.api-result');
        if (existingResult) {
            existingResult.remove();
        }

        // Create result element
        const resultDiv = document.createElement('div');
        resultDiv.className = 'api-result';
        resultDiv.style.cssText = `
            margin-top: 15px;
            padding: 10px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            background: ${success ? '#00ff88' : '#ff6b6b'};
            color: ${success ? '#000' : '#fff'};
        `;

        if (success) {
            resultDiv.innerHTML = `<strong>✅ Success:</strong><br>${JSON.stringify(data, null, 2)}`;
        } else {
            resultDiv.innerHTML = `<strong>❌ Error:</strong><br>${JSON.stringify(data, null, 2)}`;
        }

        button.parentElement.appendChild(resultDiv);

        // Auto-hide result after 10 seconds
        setTimeout(() => {
            if (resultDiv.parentElement) {
                resultDiv.remove();
            }
        }, 10000);
    }

    async sendLiveRequest(endpointItem, endpoint) {
        const button = endpointItem.querySelector('.btn-send-request');
        const consoleOutput = endpointItem.querySelector('.console-output');
        const placeholder = consoleOutput.querySelector('.console-placeholder');
        const consoleData = consoleOutput.querySelector('.console-data');

        // Update button state
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="icon-play">⏳</span> Đang gửi...';
        button.disabled = true;

        try {
            let result;

            // Use appropriate API service method based on endpoint
            switch (endpoint) {
                case '/get-token':
                    result = await window.apiService.getTokenInfo();
                    break;
                case '/balance':
                    result = await window.apiService.getBalance();
                    break;
                case '/token-aval':
                    result = await window.apiService.getTokenAvailability();
                    break;
                case '/solve':
                    result = await window.apiService.solveCaptcha({ test: true, type: 'recaptcha' });
                    break;
                default:
                    result = await window.apiService.get(endpoint);
            }

            // Hide placeholder and show data
            placeholder.classList.add('hidden');
            consoleData.classList.remove('hidden');
            consoleData.textContent = JSON.stringify(result.data, null, 2);

            // Add status indicator
            consoleData.style.color = result.success ? '#00ff88' : '#ff6b6b';

        } catch (error) {
            // Show error in console
            placeholder.classList.add('hidden');
            consoleData.classList.remove('hidden');
            consoleData.textContent = `Error: ${error.message}\n${JSON.stringify(error.data || {}, null, 2)}`;
            consoleData.style.color = '#ff6b6b';
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            button.style.background = '#00ff88';
            button.style.color = '#000';

            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '';
                button.style.color = '';
            }, 2000);
        } catch (error) {
            console.error('Failed to copy:', error);
            button.textContent = '❌ Failed';
            button.style.background = '#ff6b6b';

            setTimeout(() => {
                button.textContent = 'Copy';
                button.style.background = '';
            }, 2000);
        }
    }
}

// Make globally available
window.ApiFlowPage = ApiFlowPage;
