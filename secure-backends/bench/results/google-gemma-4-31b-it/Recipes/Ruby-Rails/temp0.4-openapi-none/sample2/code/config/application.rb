require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Bundler.require(*Rails.groups)

module RecipeSharingApp
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0

    # Configure API mode
    config.api_only = true

    # Enable CORS for API access
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end