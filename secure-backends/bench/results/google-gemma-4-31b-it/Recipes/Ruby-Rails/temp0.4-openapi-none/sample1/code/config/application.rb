require_relative "boot"

require "rails/all"

module RecipeSharingApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure we can render HTML even though it is an API app
    config.middleware.use Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end