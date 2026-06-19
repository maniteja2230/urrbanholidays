/**
 * Urban Holidays – Razorpay Payment Integration
 * Handles payment initialization, callback, and error states
 */

class UrbanHolidaysPayment {
  constructor(config) {
    this.config = config;
    this.razorpayInstance = null;
  }

  getCSRFToken() {
    const name = 'csrftoken';
    if (document.cookie && document.cookie !== '') {
      for (const cookie of document.cookie.split(';')) {
        const [k, v] = cookie.trim().split('=');
        if (k === name) return decodeURIComponent(v);
      }
    }
    return '';
  }

  async initiateOrder() {
    const response = await fetch('/payments/initiate/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken(),
      },
    });
    if (!response.ok) throw new Error('Failed to create order');
    return await response.json();
  }

  async verifyPayment(paymentData) {
    const response = await fetch('/payments/callback/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken(),
      },
      body: JSON.stringify(paymentData),
    });
    return await response.json();
  }

  openCheckout(orderData) {
    const options = {
      key: this.config.key,
      amount: orderData.amount,
      currency: orderData.currency || 'INR',
      name: 'Urban Holidays',
      description: 'Mega Ticket Gift Voucher',
      image: '/static/images/logo.png',
      order_id: orderData.order_id,
      prefill: this.config.prefill || {},
      theme: { color: '#0A2463' },
      modal: {
        ondismiss: () => {
          this.config.onDismiss && this.config.onDismiss();
          showToast('Payment cancelled. You can try again anytime.', 'info');
        },
      },
      handler: async (response) => {
        try {
          showToast('Verifying payment...', 'info');
          const result = await this.verifyPayment({
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
          if (result.status === 'success') {
            showToast('Payment successful! Redirecting...', 'success');
            setTimeout(() => {
              window.location.href = result.redirect_url;
            }, 1000);
          } else {
            showToast('Payment verification failed. Contact support.', 'error');
            this.config.onError && this.config.onError(result);
          }
        } catch (err) {
          console.error('Verification error:', err);
          showToast('Network error during verification. Contact support.', 'error');
        }
      },
    };
    this.razorpayInstance = new Razorpay(options);
    this.razorpayInstance.on('payment.failed', (response) => {
      console.error('Payment failed:', response.error);
      showToast(`Payment failed: ${response.error.description}`, 'error');
      this.config.onError && this.config.onError(response.error);
    });
    this.razorpayInstance.open();
  }

  async pay() {
    try {
      const orderData = await this.initiateOrder();
      this.openCheckout(orderData);
    } catch (err) {
      console.error('Payment initialization error:', err);
      showToast('Failed to initialize payment. Please try again.', 'error');
    }
  }
}

// Global helper for simple payment trigger
window.startVoucherPayment = function (config) {
  const payment = new UrbanHolidaysPayment(config);
  payment.pay();
};
