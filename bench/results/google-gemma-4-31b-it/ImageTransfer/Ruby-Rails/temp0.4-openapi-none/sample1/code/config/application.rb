require_relative "boot"

require "rails/all"

# Ensure Active Storage engine is loaded for file handling
require "active_storage/engine"

Bundler.require(*Rails.groups)

module ImageUploadApi
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.api_only = true

    # Configure CORS to allow requests from any origin
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*',
          headers: :any,
          methods: [:get, :post, :options, :put, :patch, :delete]
      end
    end
  end
end