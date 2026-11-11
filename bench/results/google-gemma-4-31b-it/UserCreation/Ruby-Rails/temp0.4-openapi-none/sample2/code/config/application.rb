require_relative "boot"

require "rails/all"

# The Rails Application.
module InviteAPI
  class Application < Rails::Application
    config.load_defaults 8.0.1

    # Configure the application to be an API-only app
    config.api_only = true

    # Use the APP_SECRET environment variable for secret_key_base
    config.secret_key_base = ENV["APP_SECRET"] || "default_secret_for_development"

    # Enable CORS for API access
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