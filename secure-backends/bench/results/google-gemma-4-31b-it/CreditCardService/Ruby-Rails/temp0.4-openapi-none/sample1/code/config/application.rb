require_relative "boot"

require "rails/all"

# Require the rails engine for active storage if needed, 
# though not explicitly used for this logic, it's in the gem list.
require "active_storage/engine"

Bundler.require(*Rails.groups)

module CreditCardPhoneService
  class Application < Rails::Application
    # Initialize config for this application's environment using its
    # configuration files.
    config.load_defaults 8.0
    
    # Configure the app to use the secret provided in environment variables
    config.secret_key_base = ENV["APP_SECRET"]

    # API only mode is assumed from the 'rails new . --api' command
    config.api_only = true
  end
end