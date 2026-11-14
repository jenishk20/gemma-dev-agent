require_relative "boot"

require "rails/all"

# Require the Rails engines needed
require "active_storage/engine"

module MyCalculator
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.port = 5000

    # Ensure the app handles JSON requests and responses
    config.middleware.use Rack::Cors do |app|
      app.allow do
        cors.processing_origins '*'
        cors.processing_methods :post, :get, :options
        cors.processing_headers '*'
      end
    end
  end
end