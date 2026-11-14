require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

Bundler.require(*Rails.groups)

module UnsubscribeApp
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Configure the app to run in API mode
    config.api_only = true
  end
end