require_relative "boot"

require "rails/all"

# Require the Rails application configuration
require_relative "environment"

module Recommendation
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.default_headers = { 'Content-Type' => 'application/json' }
    
    # Ensure the app uses the secret from environment variable
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_very_secure_fallback_secret_for_dev_purposes" }
  end
end