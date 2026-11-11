require_relative "boot"

require "rails/all"

# Require active storage engine as requested
require "active_storage/engine"

module WikiApp
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0
    config. autoload_paths = %#[\n]
    
    # Ensure the app can serve HTML as requested by the OpenAPI schema
    config.mime_enabled = true
  end
end