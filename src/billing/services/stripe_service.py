"""
Thin wrapper around the Stripe SDK (test mode only):
- create_checkout_session(tenant, plan) -> Checkout Session URL
- verify_and_parse_webhook(payload, sig_header) -> stripe.Event
  (raises on bad signature -> caller returns 400)
"""

# TODO: implement using `stripe` package + settings.stripe_secret_key
