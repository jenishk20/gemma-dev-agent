require_relative "boot"

require "rails/all"

# Require Active Storage engine for file uploads
require "active_storage/engine"

Bundler.require(*Rails.groups)

module ProfileCollection
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.default_host = "0.0.0.0"
    
    # Ensure the app uses the secret provided in environment
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_default_secret_for_dev"
  end
end