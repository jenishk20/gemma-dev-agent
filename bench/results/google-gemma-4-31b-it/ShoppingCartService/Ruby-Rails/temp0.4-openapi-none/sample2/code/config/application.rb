require_relative "boot"

require "rails/all"

# Require the rails process environment to load the application
Rails.application.load_secrets

module ShoppingCartService
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app uses the secret provided in the environment
    config.secret_key_base = ENV["APP_SECRET"]
  end
end