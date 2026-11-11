require_relative "boot"

require "rails/all"

# Require the Rails engines that are needed
require "active_storage/engine"

module ClickTrackingApi
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0

    # Use the APP_SECRET env variable if provided
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_secure_fallback_secret_for_dev" }

    # Configure the app for API mode
    config.api_only = true
  end
end