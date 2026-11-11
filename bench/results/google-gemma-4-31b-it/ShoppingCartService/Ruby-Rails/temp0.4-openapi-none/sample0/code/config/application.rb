require_relative "boot"

require "rails/all"

# Require the engines that are optional in API-only apps but might be needed
require "active_storage/engine"

module ShoppingCartService
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Use the APP_SECRET env variable if provided
    config.secret_key_base = ENV['APP_SECRET'] || 'default_secret_for_dev'
  end
end