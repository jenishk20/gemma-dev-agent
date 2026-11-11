require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

Bundler.require(*Rails.groups)

module MyCalculator
  class Application < Rails::Application
    config.load_defaults 8.0.1

    # Configure the app to be an API
    config.api_only = true

    # Ensure the app handles CORS for potential frontend integration
    config.middleware.use Rack::Cors do |app|
      app.allow do
        origins :all
        resource '*',
          headers: :all,
          methods: [:get, :post, :put, :patch, :delete, :options, :head]
      end
    end
  end
end