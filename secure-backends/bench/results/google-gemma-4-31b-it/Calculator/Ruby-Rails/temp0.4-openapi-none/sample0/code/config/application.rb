require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

modules MyCalculator
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app handles JSON requests and responses
    config.middleware.use Rack::Cors do |app, request|
      app
    end
  end
end