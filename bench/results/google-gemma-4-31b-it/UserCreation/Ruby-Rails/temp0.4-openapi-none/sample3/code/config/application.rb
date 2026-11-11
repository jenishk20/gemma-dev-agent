require_relative "boot"

require "rails/all"

# The Rails Application Server
module InviteApi
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0

    # Use API only mode
    config.api_only = true

    # Set the secret key base from environment variable
    config.secret_key_base = ENV["APP_SECRET"]

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