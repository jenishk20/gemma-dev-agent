require_relative "boot"
require "rails/all"

Bundler.require(*Rails.groups)

module ShoppingCartService
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Use the provided secret
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_fallback_secret_12345"
  end
end