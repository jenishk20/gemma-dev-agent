require_relative "boot"

require "rails/all"

# Use the APP_SECRET env variable for secret_key_base
ENV["SECRET_KEY_BASE"] = ENV["APP_SECRET"]

module SecretStorage
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Configure CORS to allow all origins for the API
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