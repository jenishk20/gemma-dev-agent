require_relative "boot"
require "rails/all"

Bundler.require(*Rails.groups)

module ClickTrackingApi
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_secure_fallback_secret_for_development" }
    
    # Ensure the app is configured as an API
    config.api_only = true
  end
end