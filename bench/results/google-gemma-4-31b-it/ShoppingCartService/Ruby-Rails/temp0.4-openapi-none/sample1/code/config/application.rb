require_relative "boot"

require "rails/all"

# Require the Rails application.
require_relative "src/environment"

module ShoppingCartService
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0.1
    config.api_only = true
    
    # Set secret key base from environment variable
    config.secret_key_base = ENV["APP_SECRET"]
  end
end