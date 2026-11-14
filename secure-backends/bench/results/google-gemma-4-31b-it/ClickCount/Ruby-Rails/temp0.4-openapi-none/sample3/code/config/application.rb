require_relative "boot"

require "rails/all"

# The requested Rails version is 8.0.1
module ClickTrackingApi
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.default_url_options = { host: 'localhost', port: 5000 }
    
    # Ensure the app secret is set from environment
    config.secret_key_base = ENV["APP_SECRET"] || "a_fallback_secret_for_development_12345"

    # Configure CORS for API access
    config.middleware.insert_before 0, Rack::Cors do
      allow do |options|
        options.default_headers = {
          'Access-Control-Allow-Origin' => '*',
          'Access-Control-Allow-Methods' => 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers' => 'Content-Type, Authorization'
        }
      end
    end
  end
end