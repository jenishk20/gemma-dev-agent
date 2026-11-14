require_relative "boot"

require "rails/all"

# Require the Rails process environment.
Rails.application.load_secrets

# Put your application configuration here!
module ProductCatalog
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0

    # Use API only mode
    config.api_only = true

    # Set the secret key base from environment variable
    config.secret_key_base = ENV["APP_SECRET"] || "default_secret_for_development"

    # Configure the app to run on 0.0.0.0:5000
    config.server.binding = "0.0.0.0"
    config.server.port = 5000
  end
end