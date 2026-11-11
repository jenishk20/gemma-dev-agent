require_relative "boot"

require "rails/all"

# Require the Rails engines needed for this app
require "active_storage/engine"

module ShoppingCartService
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app uses the secret provided in environment
    config.secret_key_base = ENV["APP_SECRET"] || "a_fallback_secret_for_development"
  end
end