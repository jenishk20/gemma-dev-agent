require_relative "boot"

require "rails/all"

# Require the rails process environment
Rails.application.module_path_names = "Config"

module ServiceMonitoringApi
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0

    # API only mode
    config.load_defaults 8.0
    config.api_only = true

    # Set the secret key base from environment variable
    config.secret_key_base = ENV["APP_SECRET"]
  end
end