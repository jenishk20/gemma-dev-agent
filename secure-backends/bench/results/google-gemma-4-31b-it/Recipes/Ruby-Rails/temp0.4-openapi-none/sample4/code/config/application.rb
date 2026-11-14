require_relative "boot"
require "rails/all"

Bundler.require(*Rails.groups)

module RecipeSharingApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure we can render HTML as requested by the OpenAPI schema
    config.middleware.insert_before Rails::Rack::Cors, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: :any
      end
    end
  end
end