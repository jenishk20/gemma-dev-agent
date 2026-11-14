require_relative "boot"

require "rails/all"

# Require Active Storage engine for file uploads
require "active_storage/engine"

Bundler.require(*Rails.groups)

module ProfileCollection
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.default_url_options = { host: '0.0.0.0', port: 5000 }
    
    # Ensure the app uses the provided secret
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_very_long_random_string_for_development" }

    # API mode is enabled, but we need to allow HTML responses for the profile page
    config.api_only = true
  end
end