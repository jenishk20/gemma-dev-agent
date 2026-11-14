require_relative "boot"

require "rails/all"

# The Base Rails application class:
module InviteApi
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_fallback_secret_for_dev"

    # Configure the application for API mode
    config.api_only = true

    # Ensure CORS is handled if needed, though not explicitly requested, 
    # it's standard for APIs.
    config.middleware.use Rack::Cors do
      allow do
        origins '*'
        resource '*',
          headers: :any,
          methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end