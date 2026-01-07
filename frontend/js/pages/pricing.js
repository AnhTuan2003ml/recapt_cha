// Pricing Page Logic
class PricingPage {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // Pricing specific event handlers
        const pricingButtons = document.querySelectorAll('#view-pricing .btn-primary, #view-pricing .btn-secondary');

        pricingButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const buttonText = e.target.textContent;
                if (buttonText.includes('Nhận ngay') || buttonText.includes('Mua ngay')) {
                    this.handlePricingAction(e.target);
                } else if (buttonText.includes('Liên hệ')) {
                    this.handleContactAction();
                }
            });
        });
    }

    handlePricingAction(button) {
        const card = button.closest('.price-card');
        const planName = card.querySelector('.plan-name').textContent;

        alert(`Bạn đã chọn gói: ${planName}\n\nVui lòng liên hệ admin để kích hoạt!`);
    }

    handleContactAction() {
        alert('Liên hệ Admin:\n📧 Email: admin@nanoai.pics\n💬 Telegram: @nanoai_support\n📱 Phone: +84 xxx xxx xxx');
    }
}

// Make globally available
window.PricingPage = PricingPage;
