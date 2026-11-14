require_relative "boot"

require "rails/all"

# Require active_storage/engine if needed, though not explicitly used for this API
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
  
  # Ensure the app uses the secret provided in environment
  config.secret_key_base = ENV["APP_SECRET"] || "a_fallback_secret_for_development_12345"
end