require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling if needed, 
# although we will use Tempfiles for the conversion process.
require "active_storage/engine"

Bundler.require(*Rails.groups)

module GifCreator
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.api_only = true

    # Configure CORS to allow requests from any origin
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*',
          headers: :all,
          methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end