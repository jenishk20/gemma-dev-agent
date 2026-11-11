require_relative "boot"

require "rails/all"

# Require the Rails engine for API mode
require "active_storage/engine"

Bundler.require(*Rails.groups)

module LoginAPI
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app listens on 0.0.0.0
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end