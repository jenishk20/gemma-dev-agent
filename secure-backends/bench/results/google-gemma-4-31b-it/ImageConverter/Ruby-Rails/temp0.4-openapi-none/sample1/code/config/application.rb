require_relative "boot"

require "rails/all"

# Require Active Storage engine for handling file uploads
require "active_storage/engine"

Bundler.require(*Rails.groups)

module GifCreator
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Handle CORS for API access
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*',
          headers: :any,
          methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end