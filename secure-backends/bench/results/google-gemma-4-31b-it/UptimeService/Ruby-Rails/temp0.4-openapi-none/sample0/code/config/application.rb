require_relative "boot"

require "rails/all"

# Require the rails process environment to load the application
Rails.application.load_secrets

# Initialize configuration defaults
Rails.application.configure do
  # Formats supported by the app
  config.load_defaults 8.0
  config.server.static.enabled = false

  # Set the secret key base from environment variable
  config.secret_key_base = ENV["APP_SECRET"]

  # Use API only mode
  config.api_only = true
end