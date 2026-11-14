require_relative "boot"

require "rails/all"

# Require active_storage/engine as requested
require "active_storage/engine"

module MyForum
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Configure the app to use the provided secret
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_long_random_string_for_development"

    # Set the application to be an API but allow HTML responses for the specific requirement
    config.api_only = true
  end
end