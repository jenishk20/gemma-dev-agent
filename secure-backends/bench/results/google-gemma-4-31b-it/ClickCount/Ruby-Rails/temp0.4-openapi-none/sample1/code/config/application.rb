require_relative "boot"

require "rails/all"

# Since we are in an API mode, we don't need the full Rails stack
# but we ensure the required engines are loaded if needed.

Module ClickTrackingApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Set the secret key base from environment variable
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_very_secure_fallback_secret_for_dev" }
  end
end