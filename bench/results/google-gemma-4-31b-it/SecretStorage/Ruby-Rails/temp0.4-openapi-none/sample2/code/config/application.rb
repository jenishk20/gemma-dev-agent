require_relative "boot"

require "rails/all"

Bundler.require(*Rails.groups)

module SecretStorage
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app uses the APP_SECRET env var for JWT
    config.middleware.use Rack::Cors do |app|
      app.defaults: {
        origins: "*",
        resource_class: Rack::Cors::Defaults::Resource
      }
    end
  end
end