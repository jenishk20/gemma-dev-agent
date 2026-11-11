require_relative "boot"

require "rails/all"

# The application.rb file for the Click Tracking API
module ClickTrackingApi
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Use the secret provided in environment variable
    config.secret_key_base = ENV["APP_SECRET"]

    # Configure the app to be an API
    config.api_only = true
  end
end