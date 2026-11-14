require_relative "boot"

require "rails/all"

# Require the Rails application.
require_relative "application"

module InviteApi
  class Application < Rails::Application
    # Initialize config for this application.
    config.load_defaults 8.0
    config.api_only = true

    # Ensure the app uses the secret from environment variable
    config.secret_key_base = ENV.fetch("APP_SECRET") { "default_secret_for_dev_only" }
  end
end