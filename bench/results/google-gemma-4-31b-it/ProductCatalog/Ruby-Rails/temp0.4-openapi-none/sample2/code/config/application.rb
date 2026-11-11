require_relative "boot"

require "rails/all"

# Require the Rails application
module ProductCatalog
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0
    
    # Configure the app to use the provided secret
    config.secret_key_base = ENV["APP_SECRET"] || "a_secure_fallback_secret_for_development"

    # API mode configuration
    config.api_only = true
  end
end