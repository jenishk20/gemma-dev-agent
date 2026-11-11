require_relative "boot"

require "rails/all"

# Require the Rails engines
require "active_storage/engine"

module SongDownloader
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Configure the app to be an API-only application
    config.api_only = true

    # Set the server to bind to 0.0.0.0 and port 5000 as requested
    config.run_options = { port: 5000, bind: '0.0.0.0' }

    # Ensure we can handle CORS if needed for a webapp API
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :options]
      end
    end
  end
end