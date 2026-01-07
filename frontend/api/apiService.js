// API Service for NanoAI
class ApiService {
    constructor() {
        this.baseUrl = 'https://flow-api.nanoai.pics/api/fix';
        this.defaultToken = 'eyJhbGciOiJIUzI1NiIs...'; // Default token
    }

    /**
     * Set authorization token
     * @param {string} token - Bearer token
     */
    setToken(token) {
        this.token = token;
    }

    /**
     * Get authorization token (use default if not set)
     * @returns {string} Bearer token
     */
    getToken() {
        return this.token || this.defaultToken;
    }

    /**
     * Make API request
     * @param {string} endpoint - API endpoint (e.g., '/get-token')
     * @param {string} method - HTTP method (GET, POST, etc.)
     * @param {object} data - Request body data
     * @returns {Promise<object>} Response data
     */
    async request(endpoint, method = 'GET', data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = this.getToken();

        const config = {
            method: method,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        };

        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, config);

            // Try to parse JSON response
            let responseData;
            const contentType = response.headers.get('content-type');

            if (contentType && contentType.includes('application/json')) {
                responseData = await response.json();
            } else {
                responseData = await response.text();
            }

            if (!response.ok) {
                throw new ApiError(
                    `HTTP ${response.status}: ${response.statusText}`,
                    response.status,
                    responseData
                );
            }

            return {
                success: true,
                status: response.status,
                data: responseData
            };

        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }

            // Network or other errors
            throw new ApiError(
                `Network error: ${error.message}`,
                0,
                { error: error.message }
            );
        }
    }

    /**
     * GET request
     * @param {string} endpoint - API endpoint
     * @returns {Promise<object>} Response data
     */
    async get(endpoint) {
        return this.request(endpoint, 'GET');
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body
     * @returns {Promise<object>} Response data
     */
    async post(endpoint, data) {
        return this.request(endpoint, 'POST', data);
    }

    /**
     * PUT request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body
     * @returns {Promise<object>} Response data
     */
    async put(endpoint, data) {
        return this.request(endpoint, 'PUT', data);
    }

    /**
     * DELETE request
     * @param {string} endpoint - API endpoint
     * @returns {Promise<object>} Response data
     */
    async delete(endpoint) {
        return this.request(endpoint, 'DELETE');
    }

    /**
     * Test connection to API
     * @returns {Promise<object>} Connection test result
     */
    async testConnection() {
        try {
            const result = await this.get('/get-token');
            return {
                connected: true,
                message: 'Connection successful',
                data: result.data
            };
        } catch (error) {
            return {
                connected: false,
                message: error.message,
                error: error.data
            };
        }
    }

    /**
     * Get token info
     * @returns {Promise<object>} Token information
     */
    async getTokenInfo() {
        return this.get('/get-token');
    }

    /**
     * Get balance
     * @returns {Promise<object>} Balance information
     */
    async getBalance() {
        return this.get('/balance');
    }

    /**
     * Get token availability
     * @returns {Promise<object>} Token availability info
     */
    async getTokenAvailability() {
        return this.get('/token-aval');
    }

    /**
     * Solve captcha
     * @param {object} captchaData - Captcha data
     * @returns {Promise<object>} Solve result
     */
    async solveCaptcha(captchaData) {
        return this.post('/solve', captchaData);
    }
}

// Custom API Error class
class ApiError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

// Create and expose singleton instance globally
const apiService = new ApiService();
window.apiService = apiService;
window.ApiService = ApiService;
window.ApiError = ApiError;
