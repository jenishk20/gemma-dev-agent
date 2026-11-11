require_relative "boot"

require "rails/all"

# Require the application components
require "active_storage/engine"

module LoggingAPI
  class Application < Rails::Application
    # Initialize configuration constants
    config.load_defaults 8.0
    
    # Configure the app to be an API-only application
    config.api_only = true
  end
end