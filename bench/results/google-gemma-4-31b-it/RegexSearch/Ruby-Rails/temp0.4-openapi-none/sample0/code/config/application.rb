require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

module FileSearchApi
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.port = 5000
    config.server.binding = "0.0.0.0"

    # Configure CORS to allow API access
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end