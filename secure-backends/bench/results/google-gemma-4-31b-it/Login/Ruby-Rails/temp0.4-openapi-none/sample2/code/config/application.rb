require_relative "boot"

require "rails/all"

# Require the Rails engines that are needed
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.server.binding = "0.0.0.0"
  config.server.port = 5000

  # Configure CORS for API access
  config.middleware.insert_before 0, Rack::Cors do
    allow do
      origins '*'
      resource '*',
        headers: :any,
        methods: [:get, :post, :put, :patch, :delete, :options, :head]
    end
  end

  # Set the secret key base from environment variable
  config.secret_key_base = ENV.fetch("APP_SECRET") { "development_secret_key_12345" }
end