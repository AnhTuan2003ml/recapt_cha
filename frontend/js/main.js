// Page modules will be loaded dynamically

// HTML content functions for components
// Function to get HTML content for components
function getComponentHtml(componentName) {
    switch (componentName) {
        case 'apiflow':
            return getApiflowHtml();
        case 'pricing':
            return getPricingHtml();
        default:
            return `<div class="container"><p>Component "${componentName}" not found.</p></div>`;
    }
}

function getApiflowHtml() {
    return `
    <div class="container">
        <div class="api-header-center">
            <h2>API <span class="text-yellow">Console</span></h2>
            <p>Tài liệu tích hợp và công cụ kiểm thử trực tiếp cho Developer.</p>
        </div>

        <div class="api-config-area">
            <div class="config-box">
                <span class="label-tag">BASE URL</span>
                <span class="config-value url-text">https://flow-api.nanoai.pics/api/fix</span>
            </div>

            <div class="config-box">
                <span class="label-tag">YOUR TOKEN</span>
                <div class="token-display">
                    <span class="lock-icon">🔒</span>
                    <span class="config-value">eyJhbGciOiJIUzI1NiIs...</span>
                    <span class="status-dot online"></span>
                </div>
            </div>
        </div>

        <div class="endpoint-list">
            
            <div class="endpoint-item">
                <div class="endpoint-head">
                    <div class="method-badge get">GET</div>
                    <div class="endpoint-path">/get-token</div>
                    <div class="endpoint-desc">Lấy thông tin Token mới & Key</div>
                    <div class="endpoint-arrow">▼</div>
                </div>
                <div class="endpoint-body hidden">
                    <div class="api-details-grid">

                        <div class="col-request">

                            <div class="param-section">
                                <h4 class="section-label">HEADERS REQUIRED</h4>
                                <div class="param-row">
                                    <span class="param-key text-yellow">Authorization</span>
                                    <span class="badge-required">required</span>
                                    <span class="param-desc">Bearer eyJhbGciOiJIUz...</span>
                                </div>
                            </div>

                            <div class="code-section">
                                <h4 class="section-label">EXAMPLE CODE (CURL)</h4>
                                <div class="code-snippet-box">
                                    <button class="btn-copy">Copy</button>
                                    <pre>curl -X GET "https://flow-api.nanoai.pics/api/fix/get-token" \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjcwOTk..."</pre>
                                </div>
                            </div>
                        </div>

                        <div class="col-response">

                            <div class="response-header">
                                <h4 class="section-label">LIVE RESPONSE</h4>
                                <button class="btn-send-request">
                                    <span class="icon-play">▶</span> Gửi Request
                                </button>
                            </div>

                            <div class="console-output">
                                <div class="console-placeholder">
                                    <div class="console-icon">›_</div>
                                    <p>Nhấn nút "Gửi Request" để kiểm tra kết nối.</p>
                                </div>
                                <pre class="console-data hidden"></pre>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div class="endpoint-item">
                <div class="endpoint-head">
                    <div class="method-badge get">GET</div>
                    <div class="endpoint-path">/balance</div>
                    <div class="endpoint-desc">Kiểm tra số dư tài khoản</div>
                    <div class="endpoint-arrow">▼</div>
                </div>
                <div class="endpoint-body hidden">
                    <div class="api-details-grid">

                        <div class="col-request">

                            <div class="param-section">
                                <h4 class="section-label">HEADERS REQUIRED</h4>
                                <div class="param-row">
                                    <span class="param-key text-yellow">Authorization</span>
                                    <span class="badge-required">required</span>
                                    <span class="param-desc">Bearer eyJhbGciOiJIUz...</span>
                                </div>
                            </div>

                            <div class="code-section">
                                <h4 class="section-label">EXAMPLE CODE (CURL)</h4>
                                <div class="code-snippet-box">
                                    <button class="btn-copy">Copy</button>
                                    <pre>curl -X GET "https://flow-api.nanoai.pics/api/fix/balance" \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjcwOTk..."</pre>
                                </div>
                            </div>
                        </div>

                        <div class="col-response">

                            <div class="response-header">
                                <h4 class="section-label">LIVE RESPONSE</h4>
                                <button class="btn-send-request">
                                    <span class="icon-play">▶</span> Gửi Request
                                </button>
                            </div>

                            <div class="console-output">
                                <div class="console-placeholder">
                                    <div class="console-icon">›_</div>
                                    <p>Nhấn nút "Gửi Request" để kiểm tra kết nối.</p>
                                </div>
                                <pre class="console-data hidden"></pre>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div class="endpoint-item">
                <div class="endpoint-head">
                    <div class="method-badge get">GET</div>
                    <div class="endpoint-path">/token-aval</div>
                    <div class="endpoint-desc">Kiểm tra số lượng Token khả dụng</div>
                    <div class="endpoint-arrow">▼</div>
                </div>
                <div class="endpoint-body hidden">
                    <div class="api-details-grid">

                        <div class="col-request">

                            <div class="param-section">
                                <h4 class="section-label">HEADERS REQUIRED</h4>
                                <div class="param-row">
                                    <span class="param-key text-yellow">Authorization</span>
                                    <span class="badge-required">required</span>
                                    <span class="param-desc">Bearer eyJhbGciOiJIUz...</span>
                                </div>
                            </div>

                            <div class="code-section">
                                <h4 class="section-label">EXAMPLE CODE (CURL)</h4>
                                <div class="code-snippet-box">
                                    <button class="btn-copy">Copy</button>
                                    <pre>curl -X GET "https://flow-api.nanoai.pics/api/fix/token-aval" \\
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjcwOTk..."</pre>
                                </div>
                            </div>
                        </div>

                        <div class="col-response">

                            <div class="response-header">
                                <h4 class="section-label">LIVE RESPONSE</h4>
                                <button class="btn-send-request">
                                    <span class="icon-play">▶</span> Gửi Request
                                </button>
                            </div>

                            <div class="console-output">
                                <div class="console-placeholder">
                                    <div class="console-icon">›_</div>
                                    <p>Nhấn nút "Gửi Request" để kiểm tra kết nối.</p>
                                </div>
                                <pre class="console-data hidden"></pre>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

        </div>
    </div>
`;
}

function getPricingHtml() {
    return `
        <div class="container" style="text-align: center;">
            <h2 style="font-size: 36px; margin-bottom: 10px;">Bảng giá Veo3 Solver</h2>
            <p style="color: #cbd5e1; margin-bottom: 40px;">Giải pháp vượt Captcha tự động, tốc độ cao và chi phí tối ưu nhất.</p>

            <div class="pricing-grid">
                <div class="price-card">
                    <h3 class="plan-title">BẮT ĐẦU</h3>
                    <h2 class="plan-name">Miễn phí</h2>
                    <div class="price">0đ <span style="font-size: 16px; color: #cbd5e1;">/trọn đời</span></div>
                    <ul>
                        <li>🎁 Tặng 100 Captcha</li>
                        <li>✅ Full tính năng API</li>
                        <li>📩 Nhắn tin Page: KM [ID]</li>
                        <li>👉 Gửi: NanoAI Page</li>
                        <li>🔑 Xem ID tài khoản của bạn lại</li>
                    </ul>
                    <button class="btn-secondary" style="width: 100%; margin-top: 20px;">Nhận ngay</button>
                </div>

                <div class="price-card highlight-card">
                    <span class="label-highlight">KHUYÊN DÙNG</span>
                    <h3 class="plan-title" style="color: #00d2ff;">TIÊU CHUẨN</h3>
                    <h2 class="plan-name">Tiêu chuẩn</h2>
                    <div class="price" style="color: #00d2ff;">30đ <span style="font-size: 16px; color: #cbd5e1;">/request</span></div>

                    <div style="background: rgba(0, 210, 255, 0.1); padding: 10px; border-radius: 6px; margin-bottom: 20px; font-weight: bold; color: #00d2ff;">
                        ⚡ Nạp 1tr nhận thêm 50k
                    </div>

                    <ul>
                        <li style="color: white;">⚡ Ưu tiên xử lý siêu tốc</li>
                        <li style="color: white;">✅ Đa luồng không giới hạn</li>
                        <li style="color: white;">🛠️ Hỗ trợ kỹ thuật 24/7</li>
                        <li style="color: white;">⚠️ Không Refund vui lòng cân nhắc</li>
                    </ul>
                    <button class="btn-primary" style="width: 100%; margin-top: 20px; background: linear-gradient(90deg, #00d2ff, #007bff);">Nạp tiền ngay</button>
                </div>

                <div class="price-card">
                    <h3 class="plan-title">ƯU TIÊN</h3>
                    <h2 class="plan-name">Doanh nghiệp</h2>
                    <div class="price" style="font-size: 24px;">Thỏa thuận</div>
                    <ul>
                        <li>✔️ Giá đại lý cực tốt</li>
                        <li>✔️ Server riêng (Private)</li>
                    </ul>
                    <button class="btn-secondary" style="width: 100%; margin-top: 65px;">Liên hệ Admin</button>
                </div>
            </div>
        </div>`;
}

// Navigation logic for SPA (Single Page Application)
class NanoAIApp {
    constructor() {
        this.currentView = 'home';
        this.pages = {}; // Store page instances
        this.init();
    }

    init() {
        this.bindNavigationEvents();
        this.showView('view-home');
    }

    bindNavigationEvents() {
        // Navigation links
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetView = e.target.id.replace('btn-', 'view-');
                this.showView(targetView);
            });
        });

        // Hero explore button
        const heroExploreBtn = document.getElementById('btn-hero-explore');
        if (heroExploreBtn) {
            heroExploreBtn.addEventListener('click', () => {
                this.showView('view-apiflow');
            });
        }
    }

    // Inject content into page container
    injectPageContent(pageName, html) {
        const container = document.getElementById(`${pageName}-content`);

        if (container) {
            container.innerHTML = html;

            // Load page-specific JavaScript if available
            setTimeout(() => {
                this.initPageScript(pageName);
            }, 100);

            this.pages[pageName] = true; // Mark as loaded
        }
    }

    // Load page content from component function
    loadPageContent(pageName) {
        console.log(`🔄 Loading page content for: ${pageName}`);

        if (!this.pages[pageName]) {
            try {
                const html = getComponentHtml(pageName);
                this.injectPageContent(pageName, html);
            } catch (error) {
                console.error(`❌ Failed to load page ${pageName} content:`, error);
            }
        } else {
            console.log(`📋 Page ${pageName} already loaded`);
        }
    }

    // Initialize page-specific JavaScript
    initPageScript(pageName) {
        switch (pageName) {
            case 'apiflow':
                if (window.ApiFlowPage) {
                    new window.ApiFlowPage();
                }
                break;
            case 'pricing':
                if (window.PricingPage) {
                    new window.PricingPage();
                }
                break;
        }
    }

    showView(viewId) {
        // Hide all views
        const views = document.querySelectorAll('.view-section');
        views.forEach(view => {
            view.classList.add('hidden');
        });

        // Show target view
        const targetView = document.getElementById(viewId);
        if (targetView) {
            targetView.classList.remove('hidden');
        }

        // Load page content if needed
        const pageName = viewId.replace('view-', '');
        if (pageName !== 'home') {
            this.loadPageContent(pageName);
        }

        // Update active navigation link
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
        });

        const navId = viewId.replace('view-', 'btn-');
        const activeLink = document.getElementById(navId);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        this.currentView = viewId;
    }

}

// Fallback: Load page scripts traditionally if ES6 modules fail
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function loadPageModules() {
    try {
        console.log('📦 Loading page modules...');

        // Load API service first
        await loadScript('api/apiService.js');

        // Load page scripts
        await loadScript('js/pages/apiflow.js');
        await loadScript('js/pages/pricing.js');

        console.log('✅ Page modules loaded successfully');
        return true;
    } catch (error) {
        console.error('❌ Failed to load page modules:', error);
        return false;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Load page modules first
    loadPageModules().then(() => {
        // Initialize main app
        const app = new NanoAIApp();
        app.init();
    }).catch(() => {
        // Fallback to basic functionality
        const app = new NanoAIApp();
        app.init();
    });
});
