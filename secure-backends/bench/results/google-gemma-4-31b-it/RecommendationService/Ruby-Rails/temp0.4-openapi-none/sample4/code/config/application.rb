require_relative "boot"

require "rails/all"

Module RecommendationApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.default_host = "0.0.0.0"
    
    # Ensure the app can handle the API requirements
    config.middleware.insert_after Rails::Rack::Cors, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :options]
      end
    end
  end
end