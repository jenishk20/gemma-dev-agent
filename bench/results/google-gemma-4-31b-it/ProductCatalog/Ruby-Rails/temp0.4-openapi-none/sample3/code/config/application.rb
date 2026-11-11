require_relative "boot"

require "rails/all"

# Require the engines
require "active_storage/engine"

module ProductCatalog
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app secret is set from environment
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_long_random_string_for_development"
  end
end