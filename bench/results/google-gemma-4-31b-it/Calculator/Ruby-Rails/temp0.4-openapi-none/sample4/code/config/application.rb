require_relative "boot"

require "rails/all"

# Require the rails engine for Active Storage if needed, though not used in this specific API
require "active_storage/engine"

Module MyCalculator
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Configure CORS to allow requests from any origin
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end